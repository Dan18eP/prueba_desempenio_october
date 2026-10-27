import logging
import traceback
from datetime import datetime, timezone

logger = logging.getLogger("airflow.task.callback")

def on_failure_alert(context):
    """
    Centralized failure callback required by PDF (Pág. 4).
    Logs the error details and writes to audit.pipeline_alerts without raising exceptions.
    """
    try:
        dag_id = context.get("dag").dag_id if context.get("dag") else "unknown_dag"
        task_id = context.get("task_instance").task_id if context.get("task_instance") else "unknown_task"
        execution_date = context.get("logical_date") or datetime.now(timezone.utc)
        exception = context.get("exception")
        error_msg = f"Task {task_id} failed in DAG {dag_id}: {str(exception)}"
        
        logger.error(f"[SISMO_ALERT] FAILURE in DAG: {dag_id} | Task: {task_id}")
        logger.error(f"[SISMO_ALERT] Details: {error_msg}")
        
        # Write to audit.pipeline_alerts
        from airflow.include.config import get_db_connection
        conn = get_db_connection(role="transform")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit.pipeline_alerts (dag_id, task_id, execution_date, error_message, alert_channel)
                VALUES (%s, %s, %s, %s, %s)
            """, (dag_id, task_id, execution_date, error_msg[:1000], "INTERNAL_AUDIT"))
            conn.commit()
        conn.close()
        logger.info("[SISMO_ALERT] Successfully registered incident in audit.pipeline_alerts")
    except Exception as e:
        logger.error(f"[SISMO_ALERT] Failed to persist failure alert to DB: {e}")
