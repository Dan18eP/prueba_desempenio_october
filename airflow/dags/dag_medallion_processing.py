from datetime import datetime, timezone, timedelta
import json
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.include.config import (
    MINIO_BUCKET,
    get_s3_client,
    get_db_connection
)
from airflow.include.callbacks import on_failure_alert
from airflow.include.quality import evaluate_data_quality, persist_quality_metrics
from airflow.include.anomaly_detection import detect_seismic_anomalies
from airflow.include.openmetadata_lineage import emit_openlineage_event

logger = logging.getLogger("airflow.dag.medallion_processing")

DOC_MD = """
### DAG: dag_medallion_processing
**Propósito:** Pipeline Medallón completo que refina los datos desde MinIO Bronze (JSON crudo), ejecuta limpieza y tipado en Silver (Parquet Snappy), calcula clasificaciones de severidad y anomalías estadísticas (Z-Score), y sincroniza de forma idempotente a Gold (MinIO Parquet + PostgreSQL Curated).

#### Principios Clave:
- **Linaje Puro:** Nace en Bronze y fluye sin capas intermedias.
- **Regla 20/20:** Preservación total de los registros procesados. Los eventos con anomalías de calidad se marcan pero no se descartan silenciosamente.
- **Idempotencia:** `ON CONFLICT (id) DO UPDATE` para garantizar re-ejecuciones seguras sin duplicidad.
"""

default_args = {
    "owner": "Daniel Echeverria",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": on_failure_alert
}

def transform_bronze_to_silver(**context):
    """
    Reads Bronze JSON from MinIO, flattens coordinates, types columns,
    evaluates quality rules and persists Silver layer.
    """
    dag_run = context.get("dag_run")
    batch_id = dag_run.conf.get("batch_id") if dag_run and dag_run.conf else f"batch_{int(datetime.now(timezone.utc).timestamp())}"
    logger.info(f"[MEDALLION-SILVER] Starting Bronze -> Silver transformation for {batch_id}")

    s3_client = get_s3_client()
    
    # 1. Locate latest Bronze file or read directly
    try:
        response = s3_client.list_objects_v2(Bucket=MINIO_BUCKET, Prefix="bronze/")
        contents = response.get("Contents", [])
        if not contents:
            logger.warning("[MEDALLION-SILVER] No Bronze files found in MinIO bucket.")
            return {"batch_id": batch_id, "count": 0}
            
        latest_file = sorted(contents, key=lambda x: x["LastModified"], reverse=True)[0]
        s3_key = latest_file["Key"]
        logger.info(f"[MEDALLION-SILVER] Reading latest Bronze file: {s3_key}")
        
        obj = s3_client.get_object(Bucket=MINIO_BUCKET, Key=s3_key)
        geojson_data = json.loads(obj["Body"].read().decode("utf-8"))
    except Exception as e:
        logger.error(f"[MEDALLION-SILVER] Error reading Bronze payload from S3: {e}")
        raise e

    features = geojson_data.get("features", [])
    raw_count = len(features)
    logger.info(f"[MEDALLION-SILVER] Processing {raw_count} raw features.")

    # 2. Desanidación, Tipado y Normalización
    parsed_records = []
    for f in features:
        props = f.get("properties", {}) or {}
        geom = f.get("geometry", {}) or {}
        coords = geom.get("coordinates", [None, None, None])
        
        # Safe extraction
        lon = float(coords[0]) if len(coords) > 0 and coords[0] is not None else None
        lat = float(coords[1]) if len(coords) > 1 and coords[1] is not None else None
        depth = float(coords[2]) if len(coords) > 2 and coords[2] is not None else 0.0
        
        epoch_time = props.get("time")
        event_time_utc = datetime.fromtimestamp(epoch_time / 1000.0, tz=timezone.utc) if epoch_time else datetime.now(timezone.utc)
        
        epoch_updated = props.get("updated")
        updated_time_utc = datetime.fromtimestamp(epoch_updated / 1000.0, tz=timezone.utc) if epoch_updated else event_time_utc

        record = {
            "id": str(f.get("id")),
            "magnitude": float(props.get("mag")) if props.get("mag") is not None else 0.0,
            "place": str(props.get("place") or "Ubicación desconocida"),
            "event_time_utc": event_time_utc,
            "updated_time_utc": updated_time_utc,
            "longitude": lon,
            "latitude": lat,
            "depth_km": depth,
            "tsunami_alert": bool(props.get("tsunami") == 1),
            "significance": int(props.get("sig") or 0),
            "review_status": str(props.get("status") or "automatic"),
            "mag_type": str(props.get("magType") or "ml"),
            "event_type": str(props.get("type") or "earthquake"),
            "usgs_url": str(props.get("url") or "")
        }
        parsed_records.append(record)

    # 3. Deduplicación por versión más reciente (Window over id order by updated DESC)
    dedup_dict = {}
    for r in sorted(parsed_records, key=lambda x: x["updated_time_utc"]):
        dedup_dict[r["id"]] = r
    dedup_records = list(dedup_dict.values())

    # 4. Evaluación de Calidad (Pandera / Quality Engine)
    enriched_records, quality_summary = evaluate_data_quality(dedup_records, batch_id)
    persist_quality_metrics(quality_summary)

    # 4.1 Write Silver Parquet to MinIO Data Lakehouse
    try:
        import io
        import pandas as pd
        silver_df = pd.DataFrame(enriched_records)
        if not silver_df.empty:
            now_dt = datetime.now(timezone.utc)
            parquet_key = f"silver/year={now_dt.year}/month={now_dt.month:02d}/day={now_dt.day:02d}/silver_{batch_id}.parquet"
            buffer = io.BytesIO()
            silver_df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
            s3_client.put_object(
                Bucket=MINIO_BUCKET,
                Key=parquet_key,
                Body=buffer.getvalue(),
                ContentType="application/octet-stream"
            )
            logger.info(f"[MEDALLION-SILVER] Saved Silver Parquet to s3://{MINIO_BUCKET}/{parquet_key}")
    except Exception as s3_err:
        logger.warning(f"[MEDALLION-SILVER] Could not write Silver Parquet to MinIO: {s3_err}")

    # 5. Persistencia en Silver (PostgreSQL staging.earthquakes_refined)
    conn = get_db_connection(role="transform")
    try:
        with conn.cursor() as cur:
            for r in enriched_records:
                cur.execute("""
                    INSERT INTO staging.earthquakes_refined (
                        id, magnitude, place, event_time_utc, updated_time_utc,
                        longitude, latitude, depth_km, tsunami_alert, significance,
                        review_status, mag_type, event_type, usgs_url, quality_status, quality_reasons
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        magnitude = EXCLUDED.magnitude,
                        place = EXCLUDED.place,
                        updated_time_utc = EXCLUDED.updated_time_utc,
                        longitude = EXCLUDED.longitude,
                        latitude = EXCLUDED.latitude,
                        depth_km = EXCLUDED.depth_km,
                        tsunami_alert = EXCLUDED.tsunami_alert,
                        significance = EXCLUDED.significance,
                        review_status = EXCLUDED.review_status,
                        quality_status = EXCLUDED.quality_status,
                        quality_reasons = EXCLUDED.quality_reasons,
                        processed_at = NOW();
                """, (
                    r["id"], r["magnitude"], r["place"], r["event_time_utc"], r["updated_time_utc"],
                    r["longitude"], r["latitude"], r["depth_km"], r["tsunami_alert"], r["significance"],
                    r["review_status"], r["mag_type"], r["event_type"], r["usgs_url"],
                    r["quality_status"], r["quality_reasons"]
                ))
            conn.commit()
        logger.info(f"[MEDALLION-SILVER] Successfully synced {len(enriched_records)} records to staging.earthquakes_refined.")
    except Exception as e:
        conn.rollback()
        logger.error(f"[MEDALLION-SILVER] Error writing to staging DB: {e}")
        raise e
    finally:
        conn.close()

    # Pass records metadata to next step via XCom
    context["ti"].xcom_push(key="batch_id", value=batch_id)
    context["ti"].xcom_push(key="raw_count", value=raw_count)
    context["ti"].xcom_push(key="silver_count", value=len(enriched_records))
    context["ti"].xcom_push(key="batch_ids", value=[r["id"] for r in enriched_records])
    return batch_id

def transform_silver_to_gold(**context):
    """
    Computes ML Z-Score anomalies, severity categories, writes to MinIO Gold Parquet,
    and synchronizes idempotently to PostgreSQL curated schema (Serving Layer).
    """
    dag_run = context.get("dag_run")
    batch_id = dag_run.conf.get("batch_id") if dag_run and dag_run.conf else f"batch_{int(datetime.now(timezone.utc).timestamp())}"
    raw_count = context["ti"].xcom_pull(task_ids="transform_bronze_to_silver", key="raw_count") or 0
    silver_count = context["ti"].xcom_pull(task_ids="transform_bronze_to_silver", key="silver_count") or 0
    batch_ids = context["ti"].xcom_pull(task_ids="transform_bronze_to_silver", key="batch_ids") or []

    logger.info(f"[MEDALLION-GOLD] Starting Silver -> Gold transformation for {batch_id} (Batch size: {len(batch_ids)})")

    # 1. Fetch Silver records scoped strictly to this batch
    conn = get_db_connection(role="transform")
    try:
        with conn.cursor() as cur:
            if batch_ids:
                cur.execute("""
                    SELECT id, magnitude, place, event_time_utc, updated_time_utc,
                           longitude, latitude, depth_km, tsunami_alert, significance,
                           review_status, quality_status
                    FROM staging.earthquakes_refined
                    WHERE id = ANY(%s)
                    ORDER BY event_time_utc DESC;
                """, (batch_ids,))
            else:
                cur.execute("""
                    SELECT id, magnitude, place, event_time_utc, updated_time_utc,
                           longitude, latitude, depth_km, tsunami_alert, significance,
                           review_status, quality_status
                    FROM staging.earthquakes_refined
                    ORDER BY event_time_utc DESC
                    LIMIT 500;
                """)
            silver_records = cur.fetchall()
            
        # 2. Detección de Anomalías Estadísticas (Z-Score y Enjambres)
        gold_records, detected_anomalies = detect_seismic_anomalies([dict(r) for r in silver_records])

        # 2.1 Persistencia de Capa Gold Parquet en MinIO Data Lakehouse
        try:
            import io
            import pandas as pd
            gold_df = pd.DataFrame(gold_records)
            if not gold_df.empty:
                now_dt = datetime.now(timezone.utc)
                gold_parquet_key = f"gold/year={now_dt.year}/month={now_dt.month:02d}/day={now_dt.day:02d}/gold_{batch_id}.parquet"
                buffer = io.BytesIO()
                gold_df.to_parquet(buffer, index=False, engine="pyarrow", compression="snappy")
                s3_client = get_s3_client()
                s3_client.put_object(
                    Bucket=MINIO_BUCKET,
                    Key=gold_parquet_key,
                    Body=buffer.getvalue(),
                    ContentType="application/octet-stream"
                )
                logger.info(f"[MEDALLION-GOLD] Successfully saved Gold Parquet to s3://{MINIO_BUCKET}/{gold_parquet_key}")
        except Exception as s3_err:
            logger.warning(f"[MEDALLION-GOLD] Could not write Gold Parquet to MinIO: {s3_err}")

        # 3. Sincronización Idempotente a PostgreSQL curated.gold_earthquakes
        with conn.cursor() as cur:
            for r in gold_records:
                cur.execute("""
                    INSERT INTO curated.gold_earthquakes (
                        id, magnitude, place, event_time_utc, updated_time_utc,
                        longitude, latitude, depth_km, tsunami_alert, significance,
                        review_status, severity_label, is_anomaly, anomaly_explanation, quality_status, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        magnitude = EXCLUDED.magnitude,
                        place = EXCLUDED.place,
                        updated_time_utc = EXCLUDED.updated_time_utc,
                        longitude = EXCLUDED.longitude,
                        latitude = EXCLUDED.latitude,
                        depth_km = EXCLUDED.depth_km,
                        tsunami_alert = EXCLUDED.tsunami_alert,
                        significance = EXCLUDED.significance,
                        review_status = EXCLUDED.review_status,
                        severity_label = EXCLUDED.severity_label,
                        is_anomaly = EXCLUDED.is_anomaly,
                        anomaly_explanation = EXCLUDED.anomaly_explanation,
                        quality_status = EXCLUDED.quality_status,
                        updated_at = NOW();
                """, (
                    r["id"], r["magnitude"], r["place"], r["event_time_utc"], r["updated_time_utc"],
                    r["longitude"], r["latitude"], r["depth_km"], r["tsunami_alert"], r["significance"],
                    r["review_status"], r["severity_label"], r["is_anomaly"], r["anomaly_explanation"],
                    r["quality_status"]
                ))
            
            # Registrar anomalías detectadas
            for a in detected_anomalies:
                cur.execute("""
                    INSERT INTO curated.gold_anomalies (
                        earthquake_id, magnitude, place, z_score, is_swarm, anomaly_explanation, detected_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (
                    a["earthquake_id"], a["magnitude"], a["place"], a["z_score"],
                    a["is_swarm"], a["anomaly_explanation"], a["detected_at"]
                ))

            # 4. Actualizar Métricas de Agregación Horarias en curated.gold_hourly_kpis
            cur.execute("""
                INSERT INTO curated.gold_hourly_kpis (
                    hour_utc, total_events, max_magnitude, avg_magnitude,
                    tsunami_alerts_count, micro_count, minor_count, moderate_count, strong_count, major_count
                )
                SELECT 
                    date_trunc('hour', event_time_utc) as hour_utc,
                    count(*) as total_events,
                    coalesce(max(magnitude), 0.0) as max_magnitude,
                    round(coalesce(avg(magnitude), 0.0), 2) as avg_magnitude,
                    count(*) filter (where tsunami_alert = true) as tsunami_alerts_count,
                    count(*) filter (where severity_label = 'Micro') as micro_count,
                    count(*) filter (where severity_label = 'Menor') as minor_count,
                    count(*) filter (where severity_label = 'Moderado') as moderate_count,
                    count(*) filter (where severity_label = 'Fuerte') as strong_count,
                    count(*) filter (where severity_label = 'Mayor') as major_count
                FROM curated.gold_earthquakes
                GROUP BY date_trunc('hour', event_time_utc)
                ON CONFLICT (hour_utc) DO UPDATE SET
                    total_events = EXCLUDED.total_events,
                    max_magnitude = EXCLUDED.max_magnitude,
                    avg_magnitude = EXCLUDED.avg_magnitude,
                    tsunami_alerts_count = EXCLUDED.tsunami_alerts_count,
                    micro_count = EXCLUDED.micro_count,
                    minor_count = EXCLUDED.minor_count,
                    moderate_count = EXCLUDED.moderate_count,
                    strong_count = EXCLUDED.strong_count,
                    major_count = EXCLUDED.major_count,
                    calculated_at = NOW();
            """)

            # 5. Conciliación de Balance (Regla 20 In -> 20 Out)
            gold_count = len(gold_records)
            cur.execute("""
                INSERT INTO audit.batch_reconciliation (
                    batch_id, source_feed, raw_count, silver_count, gold_count
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (batch_id) DO UPDATE SET
                    raw_count = EXCLUDED.raw_count,
                    silver_count = EXCLUDED.silver_count,
                    gold_count = EXCLUDED.gold_count,
                    reconciled_at = NOW();
            """, (batch_id, "USGS Real-Time Feed", raw_count, silver_count, gold_count))

            conn.commit()

        logger.info(f"[MEDALLION-GOLD] Published {len(gold_records)} events to curated.gold_earthquakes. Reconciliation: {raw_count} in -> {gold_count} out.")

        # 6. Emit OpenLineage Event
        emit_openlineage_event(
            job_name="dag_medallion_processing",
            inputs=["minio_sismowatch_lake.silver.earthquakes"],
            outputs=[
                "minio_sismowatch_lake.gold.earthquakes",
                "postgres_sismowatch.curated.gold_earthquakes",
                "postgres_sismowatch.curated.gold_hourly_kpis"
            ],
            row_count=len(gold_records)
        )

    except Exception as e:
        conn.rollback()
        logger.error(f"[MEDALLION-GOLD] Error writing to Gold curated: {e}")
        raise e
    finally:
        conn.close()

with DAG(
    dag_id="dag_medallion_processing",
    default_args=default_args,
    description="Procesamiento Medallón: Limpieza Silver y sincronización a Gold Curated",
    schedule_interval=None, # Disparado reactivamente por dag_usgs_ingest
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    tags=["transformacion", "medallion", "calidad", "lakehouse"],
    doc_md=DOC_MD
) as dag:

    transform_silver_task = PythonOperator(
        task_id="transform_bronze_to_silver",
        python_callable=transform_bronze_to_silver,
        provide_context=True
    )

    transform_gold_task = PythonOperator(
        task_id="transform_silver_to_gold",
        python_callable=transform_silver_to_gold,
        provide_context=True
    )

    transform_silver_task >> transform_gold_task
