from datetime import datetime, timezone, timedelta
import json
import logging
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.include.config import (
    USGS_REALTIME_FEED_URL,
    USGS_HISTORICAL_QUERY_URL,
    MINIO_BUCKET,
    get_s3_client,
    get_db_connection
)
from airflow.include.callbacks import on_failure_alert
from airflow.include.openmetadata_lineage import emit_openlineage_event

logger = logging.getLogger("airflow.dag.usgs_ingest")

DOC_MD = """
### DAG: dag_usgs_ingest
**Propósito:** Ingesta continua en tiempo casi real del feed global de sismos desde USGS Earthquake Catalog hacia la capa Bronze de MinIO.

#### Principios de Arquitectura:
- **Periodicidad:** Cada 5 minutos (`*/5 * * * *`).
- **Sin capa landing intermedia:** El payload GeoJSON entra directamente a MinIO Bronze en formato inmutable append-only.
- **Resiliencia:** Reintentos exponenciales automáticos, timeout de 15s en llamadas HTTP y `on_failure_callback` centralizado.
- **Gatillado Reactivo:** Al culminar exitosamente, dispara automáticamente `dag_medallion_processing`.
"""

default_args = {
    "owner": "Daniel Echeverria",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": on_failure_alert
}

def fetch_and_store_bronze(**context):
    """
    Downloads GeoJSON from USGS, persists raw payload directly into MinIO Bronze,
    and logs batch reconciliation metadata to PostgreSQL raw schema.
    """
    now_utc = datetime.now(timezone.utc)
    batch_id = f"batch_{now_utc.strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"[INGEST] Starting USGS fetch for batch {batch_id} from {USGS_REALTIME_FEED_URL}")
    
    # 1. Fetch from USGS with defensive timeout
    try:
        response = requests.get(USGS_REALTIME_FEED_URL, timeout=15)
        response.raise_for_status()
        geojson_data = response.json()
    except requests.RequestException as e:
        logger.error(f"[INGEST] Network or HTTP error connecting to USGS: {e}")
        raise e
        
    features = geojson_data.get("features", [])

    # 1.1 CDC Downtime Recovery check (>60 min gap since last raw batch)
    try:
        conn = get_db_connection(role="ingest")
        with conn.cursor() as cur:
            cur.execute("SELECT ingested_at FROM raw.earthquakes_raw_batches ORDER BY ingested_at DESC LIMIT 1;")
            row = cur.fetchone()
            if row and row.get("ingested_at"):
                last_ingested = row["ingested_at"]
                if last_ingested.tzinfo is None:
                    last_ingested = last_ingested.replace(tzinfo=timezone.utc)
                gap_minutes = (now_utc - last_ingested).total_seconds() / 60.0
                if gap_minutes > 60:
                    logger.warning(f"[INGEST CDC] Detected downtime gap of {gap_minutes:.1f} mins since last batch ({last_ingested.isoformat()}). Triggering CDC recovery with updatedafter.")
                    cdc_resp = requests.get(
                        USGS_HISTORICAL_QUERY_URL,
                        params={
                            "format": "geojson",
                            "updatedafter": last_ingested.isoformat(),
                            "eventtype": "earthquake",
                            "limit": 20000
                        },
                        timeout=30
                    )
                    if cdc_resp.status_code == 200:
                        cdc_geojson = cdc_resp.json()
                        cdc_features = cdc_geojson.get("features", [])
                        if cdc_features:
                            merged_dict = {f["id"]: f for f in features}
                            for f in cdc_features:
                                merged_dict[f["id"]] = f
                            features = list(merged_dict.values())
                            geojson_data["features"] = features
                            logger.info(f"[INGEST CDC] Recovered and merged {len(cdc_features)} events missed during downtime.")
                    elif cdc_resp.status_code == 204:
                        logger.info("[INGEST CDC] No events updated during downtime window (204 No Content).")
        conn.close()
    except Exception as cdc_err:
        logger.warning(f"[INGEST CDC] Could not evaluate or run CDC downtime check: {cdc_err}")

    count = len(features)
    logger.info(f"[INGEST] Received/reconciled {count} seismic events from USGS.")
    
    # 2. Write raw JSON directly to MinIO Bronze (No landing layer)
    s3_key = f"bronze/year={now_utc.year}/month={now_utc.month:02d}/day={now_utc.day:02d}/feed_{int(now_utc.timestamp())}.json"
    s3_client = get_s3_client()
    
    try:
        s3_client.put_object(
            Bucket=MINIO_BUCKET,
            Key=s3_key,
            Body=json.dumps(geojson_data).encode("utf-8"),
            ContentType="application/json",
            Metadata={"batch_id": batch_id, "features_count": str(count)}
        )
        logger.info(f"[INGEST] Successfully written Bronze raw JSON to s3://{MINIO_BUCKET}/{s3_key}")
    except Exception as e:
        logger.error(f"[INGEST] Error uploading to MinIO Bronze: {e}")
        raise e

    # 3. Log raw batch to PostgreSQL raw.earthquakes_raw_batches
    try:
        conn = get_db_connection(role="ingest")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw.earthquakes_raw_batches (batch_id, feed_url, raw_payload, features_count, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (batch_id) DO NOTHING
            """, (batch_id, USGS_REALTIME_FEED_URL, json.dumps(geojson_data), count, "INGESTED"))
            conn.commit()
        conn.close()
        logger.info(f"[INGEST] Batch {batch_id} logged to raw.earthquakes_raw_batches.")
    except Exception as e:
        logger.error(f"[INGEST] Failed to log batch to DB raw schema: {e}")
        # Non-fatal if MinIO write succeeded

    # 4. Emit OpenLineage Event
    emit_openlineage_event(
        job_name="dag_usgs_ingest",
        inputs=[USGS_REALTIME_FEED_URL],
        outputs=[f"minio://{MINIO_BUCKET}/{s3_key}"],
        row_count=count
    )

    # Pass batch metadata to downstream via XCom (only strings/counts, no large payload)
    context["ti"].xcom_push(key="batch_id", value=batch_id)
    context["ti"].xcom_push(key="s3_key", value=s3_key)
    context["ti"].xcom_push(key="features_count", value=count)
    return batch_id

with DAG(
    dag_id="dag_usgs_ingest",
    default_args=default_args,
    description="[Capa Bronze] Ingesta continua cada 5 min de sismos USGS hacia MinIO Bronze",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    tags=["capa-bronze", "ingesta-cruda", "minio-s3", "raw-schema"],
    doc_md=DOC_MD
) as dag:

    ingest_task = PythonOperator(
        task_id="bronze__fetch_and_store_raw",
        python_callable=fetch_and_store_bronze,
        provide_context=True
    )

    trigger_transform_task = TriggerDagRunOperator(
        task_id="trigger_medallion_processing",
        trigger_dag_id="dag_medallion_processing",
        wait_for_completion=False,
        conf={"batch_id": "{{ ti.xcom_pull(task_ids='bronze__fetch_and_store_raw', key='batch_id') }}"}
    )

    ingest_task >> trigger_transform_task
