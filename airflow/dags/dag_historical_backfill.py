from datetime import datetime, timezone, timedelta
import json
import logging
import requests
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator
from airflow.include.config import (
    USGS_HISTORICAL_QUERY_URL,
    MINIO_BUCKET,
    get_s3_client,
    get_db_connection
)
from airflow.include.callbacks import on_failure_alert
from airflow.include.quality import evaluate_data_quality, persist_quality_metrics
from airflow.include.anomaly_detection import detect_seismic_anomalies
from airflow.include.openmetadata_lineage import emit_openlineage_event

logger = logging.getLogger("airflow.dag.historical_backfill")

DOC_MD = """
### DAG: dag_historical_backfill
**Propósito:** Ingesta y reprocesamiento histórico parametrizado de los últimos 30 días desde el endpoint oficial de consulta de USGS.

#### Parámetros de Ejecución:
- `start_date`: Fecha de inicio en formato `YYYY-MM-DD` (por defecto hace 30 días).
- `end_date`: Fecha de fin en formato `YYYY-MM-DD` (por defecto hoy).
- `min_magnitude`: Magnitud mínima (por defecto `2.5`).

#### Idempotencia:
Las inserciones utilizan `ON CONFLICT (id) DO UPDATE`, garantizando que ejecutar dos veces el mismo intervalo no genere registros duplicados.
"""

default_args = {
    "owner": "Daniel Echeverria",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=45),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=15),
    "on_failure_callback": on_failure_alert
}

def execute_backfill(**context):
    params = context.get("params", {})
    
    # Calculate default 30 days back if not provided
    now = datetime.now(timezone.utc)
    default_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    default_end = now.strftime("%Y-%m-%d")
    
    start_date = params.get("start_date") or default_start
    end_date = params.get("end_date") or default_end
    min_mag = float(params.get("min_magnitude", 2.5))
    
    batch_id = f"backfill_{start_date}_to_{end_date}_m{min_mag}"
    logger.info(f"[BACKFILL] Starting historical backfill: {start_date} to {end_date} (min_mag={min_mag})")

    # 1. Fetch from USGS Query API
    query_params = {
        "format": "geojson",
        "starttime": start_date,
        "endtime": end_date,
        "minmagnitude": min_mag,
        "eventtype": "earthquake",
        "limit": 20000,
        "orderby": "time"
    }
    
    try:
        response = requests.get(USGS_HISTORICAL_QUERY_URL, params=query_params, timeout=60)
        if response.status_code == 204:
            logger.info("[BACKFILL] USGS returned 204 No Content (0 earthquakes found in range).")
            geojson_data = {"type": "FeatureCollection", "features": []}
        else:
            response.raise_for_status()
            geojson_data = response.json()
    except Exception as e:
        logger.error(f"[BACKFILL] Network error querying USGS historical API: {e}")
        raise e

    features = geojson_data.get("features", [])
    raw_count = len(features)
    logger.info(f"[BACKFILL] Retrieved {raw_count} historical seismic events.")

    # 2. Write to MinIO Bronze Lakehouse
    s3_key = f"bronze/historical/backfill_{start_date}_{end_date}.json"
    s3_client = get_s3_client()
    try:
        s3_client.put_object(
            Bucket=MINIO_BUCKET,
            Key=s3_key,
            Body=json.dumps(geojson_data).encode("utf-8"),
            ContentType="application/json"
        )
        logger.info(f"[BACKFILL] Stored historical batch in s3://{MINIO_BUCKET}/{s3_key}")
    except Exception as e:
        logger.error(f"[BACKFILL] Error persisting historical batch in MinIO: {e}")
        raise e

    # 3. Transform and Normalize
    parsed_records = []
    for f in features:
        props = f.get("properties", {}) or {}
        geom = f.get("geometry", {}) or {}
        coords = geom.get("coordinates", [None, None, None])
        
        lon = float(coords[0]) if len(coords) > 0 and coords[0] is not None else None
        lat = float(coords[1]) if len(coords) > 1 and coords[1] is not None else None
        depth = float(coords[2]) if len(coords) > 2 and coords[2] is not None else 0.0
        
        epoch_time = props.get("time")
        event_time_utc = datetime.fromtimestamp(epoch_time / 1000.0, tz=timezone.utc) if epoch_time else now
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
            "review_status": str(props.get("status") or "reviewed"),
            "mag_type": str(props.get("magType") or "ml"),
            "event_type": str(props.get("type") or "earthquake"),
            "usgs_url": str(props.get("url") or "")
        }
        parsed_records.append(record)

    # 4. Deduplicate and Quality Check
    dedup_dict = {r["id"]: r for r in sorted(parsed_records, key=lambda x: x["updated_time_utc"])}
    dedup_records = list(dedup_dict.values())
    enriched_records, quality_summary = evaluate_data_quality(dedup_records, batch_id)
    persist_quality_metrics(quality_summary)

    # 5. Detección de Anomalías y Clasificación
    gold_records, detected_anomalies = detect_seismic_anomalies(enriched_records)

    # 6. Idempotent Upsert into PostgreSQL
    conn = get_db_connection(role="transform")
    try:
        with conn.cursor() as cur:
            # Sync Staging
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
            
            # Sync Gold
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

            # Sync KPIs
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

            # Reconciliation record
            cur.execute("""
                INSERT INTO audit.batch_reconciliation (
                    batch_id, source_feed, raw_count, silver_count, gold_count
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (batch_id) DO UPDATE SET
                    raw_count = EXCLUDED.raw_count,
                    silver_count = EXCLUDED.silver_count,
                    gold_count = EXCLUDED.gold_count,
                    reconciled_at = NOW();
            """, (batch_id, f"USGS Historical ({start_date} to {end_date})", raw_count, len(enriched_records), len(gold_records)))

            conn.commit()
        logger.info(f"[BACKFILL] Completed backfill. Loaded {len(gold_records)} historical events without duplicates.")

        emit_openlineage_event(
            job_name="dag_historical_backfill",
            inputs=[f"https://earthquake.usgs.gov/fdsnws/event/1/query?starttime={start_date}&endtime={end_date}"],
            outputs=["postgres_sismowatch.curated.gold_earthquakes"],
            row_count=len(gold_records)
        )
    except Exception as e:
        conn.rollback()
        logger.error(f"[BACKFILL] Failed persisting historical backfill to DB: {e}")
        raise e
    finally:
        conn.close()

    return batch_id

with DAG(
    dag_id="dag_historical_backfill",
    default_args=default_args,
    description="[Medallion Completo] Backfill histórico parametrizado de los últimos 30 días desde USGS",
    schedule_interval=None,
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    tags=["medallion-full", "backfill-historico", "capa-bronze-silver-gold", "usgs"],
    params={
        "start_date": Param("", type=["null", "string"], description="Fecha inicio YYYY-MM-DD (por defecto hace 30 días)"),
        "end_date": Param("", type=["null", "string"], description="Fecha fin YYYY-MM-DD (por defecto hoy)"),
        "min_magnitude": Param(2.5, type="number", description="Magnitud mínima (por defecto 2.5)")
    },
    doc_md=DOC_MD
) as dag:

    backfill_task = PythonOperator(
        task_id="medallion__execute_backfill",
        python_callable=execute_backfill,
        provide_context=True
    )
