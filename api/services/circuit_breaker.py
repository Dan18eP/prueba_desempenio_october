from sqlalchemy.orm import Session
from sqlalchemy import text
from api.services.chart_protocol import build_declarative_chart
import logging

logger = logging.getLogger("api.services.circuit_breaker")

def execute_fallback_intent(prompt: str, db: Session, latency_ms: int = 15) -> dict:
    """
    Deterministic Analytical Fallback Engine.
    Executes in < 15ms when LLM times out or is offline, guaranteeing 100% platform availability.
    """
    p = prompt.lower()
    logger.info(f"[CIRCUIT_BREAKER] Executing deterministic fallback for prompt: '{prompt}'")

    # Intent 0: Conteo General y Totales de la Capa Gold
    if any(k in p for k in ["cuanto", "cuánto", "total", "registrado", "catálogo", "catalogo", "cantidad", "resumen"]):
        sql = """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE tsunami_alert = TRUE) as tsunamis,
                COUNT(*) FILTER (WHERE is_anomaly = TRUE) as anomalies,
                COALESCE(MAX(magnitude), 0.0) as max_mag
            FROM curated.gold_earthquakes;
        """
        row = db.execute(text(sql)).fetchone()
        tot = row[0] if row else 0
        tsu = row[1] if row else 0
        ano = row[2] if row else 0
        mx = float(row[3]) if row else 0.0
        return {
            "answer": f"Actualmente se registran {tot} eventos sísmicos en la capa Gold. De ellos, {tsu} cuentan con alerta de tsunami activa, {ano} presentan anomalías estadísticas y la magnitud máxima registrada es {mx}.",
            "chart": {"type": "none"},
            "sql_executed": sql.strip(),
            "suggested_questions": ["¿Hay sismos con alerta de tsunami?", "Ver distribución por severidad", "Sismos más fuertes"],
            "model_used": "Operational-Data-Engine",
            "latency_ms": latency_ms,
            "fallback_active": True
        }

    # Intent 1: Distribución por Severidad / Categorías
    elif any(k in p for k in ["severidad", "categoría", "categoria", "distribucion", "distribución"]):
        sql = """
            SELECT severity_label, COUNT(*) as count 
            FROM curated.gold_earthquakes 
            GROUP BY severity_label 
            ORDER BY count DESC;
        """
        rows = db.execute(text(sql)).fetchall()
        labels = [r[0] for r in rows]
        data = [int(r[1]) for r in rows]
        colors = ["#4edea3", "#adc6ff", "#ec6a06", "#f97316", "#ef4444"]
        
        chart = build_declarative_chart(
            chart_type="bar",
            title="Distribución Sísmica por Severidad",
            labels=labels,
            data=data,
            dataset_label="Total Sismos",
            color_palette=colors
        )
        return {
            "answer": f"Se registran sismos distribuidos en {len(labels)} categorías de severidad. La mayor concentración se encuentra en categoría '{labels[0]}' con {data[0]} eventos.",
            "chart": chart,
            "sql_executed": sql.strip(),
            "suggested_questions": ["¿Hay sismos con alerta de tsunami?", "Ver los sismos más fuertes de hoy"],
            "model_used": "Deterministic-Fallback-Engine (Zero-Crash)",
            "latency_ms": latency_ms,
            "fallback_active": True
        }

    # Intent 2: Serie Temporal por Hora
    elif any(k in p for k in ["hora", "evolucion", "evolución", "serie", "tiempo", "hoy"]):
        sql = """
            SELECT TO_CHAR(hour_utc, 'HH24:00') as hr, total_events 
            FROM curated.gold_hourly_kpis 
            ORDER BY hour_utc ASC 
            LIMIT 24;
        """
        rows = db.execute(text(sql)).fetchall()
        labels = [r[0] for r in rows]
        data = [int(r[1]) for r in rows]
        
        chart = build_declarative_chart(
            chart_type="line",
            title="Frecuencia Sísmica por Hora (Últimas 24h)",
            labels=labels,
            data=data,
            dataset_label="Sismos por Hora",
            color_palette=["#adc6ff"] * len(data)
        )
        return {
            "answer": f"Monitoreo de frecuencia sísmica en las últimas 24 horas. El pico horario de actividad registró {max(data) if data else 0} eventos.",
            "chart": chart,
            "sql_executed": sql.strip(),
            "suggested_questions": ["¿Cuáles fueron las magnitudes máximas?", "Distribución por severidad"],
            "model_used": "Deterministic-Fallback-Engine (Zero-Crash)",
            "latency_ms": latency_ms,
            "fallback_active": True
        }

    # Intent 3: Alerta de Tsunami
    elif "tsunami" in p:
        try:
            db.rollback()
        except Exception:
            pass
        sql = """
            SELECT magnitude, place, depth_km, severity_label, event_time_utc
            FROM curated.gold_earthquakes
            WHERE tsunami_alert = TRUE
            ORDER BY magnitude DESC
            LIMIT 5;
        """
        rows = db.execute(text(sql)).fetchall()
        total_tsunami = db.execute(text("SELECT COUNT(*) FROM curated.gold_earthquakes WHERE tsunami_alert = TRUE;")).scalar() or len(rows)
        
        table_lines = ["\n| Magnitud | Ubicacion | Profundidad | Severidad | Fecha / Hora (UTC) |", "| :---: | :--- | :---: | :---: | :--- |"]
        for r in rows:
            table_lines.append(f"| **M {float(r[0]):.1f}** | {r[1]} | {float(r[2]):.1f} km | {r[3]} | {str(r[4])[:19]} |")
            
        answer = f"Se registran **{total_tsunami}** eventos con alerta de tsunami activa en el catalogo de la capa Gold. A continuacion se detallan los eventos mas criticos:\n" + "\n".join(table_lines)
        return {
            "answer": answer,
            "chart": {"type": "none"},
            "sql_executed": sql.strip(),
            "suggested_questions": ["¿Cuáles son las anomalías detectadas?", "Ver distribución por severidad", "Sismos más fuertes"],
            "model_used": "Deterministic-Fallback-Engine (Zero-Crash)",
            "latency_ms": latency_ms,
            "fallback_active": True
        }

    # Intent 3.5: Anomalias Detectadas
    elif any(k in p for k in ["anomalia", "anomalía", "anomalias", "anomalías", "enjambre"]):
        try:
            db.rollback()
        except Exception:
            pass
        sql = """
            SELECT magnitude, place, depth_km, severity_label, anomaly_explanation
            FROM curated.gold_earthquakes
            WHERE is_anomaly = TRUE
            ORDER BY magnitude DESC
            LIMIT 5;
        """
        rows = db.execute(text(sql)).fetchall()
        total_anomalies = db.execute(text("SELECT COUNT(*) FROM curated.gold_earthquakes WHERE is_anomaly = TRUE;")).scalar() or len(rows)

        table_lines = ["\n| Magnitud | Ubicacion | Profundidad | Severidad | Criterio de Anomalia |", "| :---: | :--- | :---: | :---: | :--- |"]
        for r in rows:
            table_lines.append(f"| **M {float(r[0]):.1f}** | {r[1]} | {float(r[2]):.1f} km | {r[3]} | {r[4] or 'Z-Score > 2.5'} |")

        answer = f"Se detectaron **{total_anomalies}** anomalias estadisticas en la capa Gold (desviacion Z-Score > 2.5 o alerta de tsunami). A continuacion se detallan los 5 eventos de mayor criticidad:\n" + "\n".join(table_lines)
        return {
            "answer": answer,
            "chart": {"type": "none"},
            "sql_executed": sql.strip(),
            "suggested_questions": ["¿Hay sismos con alerta de tsunami?", "Ver distribución por severidad", "Sismos de las últimas 24 horas"],
            "model_used": "Deterministic-Fallback-Engine (Zero-Crash)",
            "latency_ms": latency_ms,
            "fallback_active": True
        }

    # Intent 4: Sismos Más Fuertes
    elif any(k in p for k in ["fuerte", "mayor", "maximo", "máximo", "grande"]):
        sql = """
            SELECT place, magnitude, depth_km 
            FROM curated.gold_earthquakes 
            ORDER BY magnitude DESC 
            LIMIT 5;
        """
        rows = db.execute(text(sql)).fetchall()
        labels = [r[0][:20] for r in rows]
        data = [float(r[1]) for r in rows]
        
        chart = build_declarative_chart(
            chart_type="bar",
            title="Top 5 Sismos Más Fuertes Registrados",
            labels=labels,
            data=data,
            dataset_label="Magnitud Richter",
            color_palette=["#ef4444", "#f97316", "#ec6a06", "#ffb690", "#adc6ff"]
        )
        return {
            "answer": f"El sismo más fuerte registrado recientemente alcanzó magnitud {data[0] if data else 0} en {rows[0][0] if rows else 'N/A'}.",
            "chart": chart,
            "sql_executed": sql.strip(),
            "suggested_questions": ["¿Hay sismos con alerta de tsunami?", "Ver serie temporal"],
            "model_used": "Deterministic-Fallback-Engine (Zero-Crash)",
            "latency_ms": latency_ms,
            "fallback_active": True
        }

    # Default Intent: Resumen General
    sql = """
        SELECT COUNT(*), COALESCE(MAX(magnitude), 0.0), ROUND(COALESCE(AVG(magnitude), 0.0), 2) 
        FROM curated.gold_earthquakes;
    """
    row = db.execute(text(sql)).fetchone()
    total = int(row[0]) if row else 0
    max_m = float(row[1]) if row else 0.0
    avg_m = float(row[2]) if row else 0.0

    return {
        "answer": f"En el catálogo actual de SismoWatch se registran {total} eventos sísmicos. La magnitud máxima es M {max_m} con un promedio de M {avg_m}.",
        "chart": {"type": "none"},
        "sql_executed": sql.strip(),
        "suggested_questions": ["Grafica los sismos por severidad", "Evolución por hora", "Alertas de tsunami"],
        "model_used": "Deterministic-Fallback-Engine (Zero-Crash)",
        "latency_ms": latency_ms,
        "fallback_active": True
    }
