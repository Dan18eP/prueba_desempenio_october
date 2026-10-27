import json
import logging
import os
import re
import time
import requests
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.core.config import settings
from api.core.database import engine_admin
from api.services.security_guard import sanitize_text_for_llm, validate_sql_query
from api.services.chart_protocol import build_declarative_chart
from api.services.circuit_breaker import execute_fallback_intent

logger = logging.getLogger("api.services.llm_client")

GOLD_SCHEMA_CONTEXT = """
Tablas disponibles en esquema curated (PostgreSQL):
1. curated.gold_earthquakes (
    id VARCHAR(64) PRIMARY KEY,
    magnitude NUMERIC(4,2),
    place VARCHAR(255),
    event_time_utc TIMESTAMP WITH TIME ZONE,
    longitude NUMERIC(9,6),
    latitude NUMERIC(9,6),
    depth_km NUMERIC(6,2),
    tsunami_alert BOOLEAN,
    severity_label VARCHAR(16) ['Micro', 'Menor', 'Moderado', 'Fuerte', 'Mayor'],
    is_anomaly BOOLEAN,
    anomaly_explanation TEXT
)
2. curated.gold_hourly_kpis (
    hour_utc TIMESTAMP WITH TIME ZONE,
    total_events INT,
    max_magnitude NUMERIC(4,2),
    avg_magnitude NUMERIC(4,2),
    tsunami_alerts_count INT,
    micro_count INT, minor_count INT, moderate_count INT, strong_count INT, major_count INT
)
"""

# nosec B608
SYSTEM_PROMPT = f"""
Eres SismoWatch AI, asistente de inteligencia sismológica y Text-to-SQL.
Tu tarea es convertir la pregunta del usuario en una consulta SQL de solo lectura (SELECT) sobre las tablas del esquema curated.

{GOLD_SCHEMA_CONTEXT}

REGLAS DE SEGURIDAD ESTRICTAS:
1. Solo genera consultas SELECT. Jamás uses INSERT, UPDATE, DELETE, DROP ni ALTER.
2. Todas las consultas deben ejecutarse contra las tablas curated.gold_earthquakes o curated.gold_hourly_kpis.
3. Responde ÚNICAMENTE con un JSON válido con este formato:
{{
  "sql_query": "SELECT severity_label, COUNT(*) FROM curated.gold_earthquakes GROUP BY severity_label ORDER BY count DESC;",
  "chart_type": "bar", // Opciones: "bar", "line", "doughnut", "none"
  "chart_title": "Distribución por Severidad",
  "explanation": "Breve explicación en español de lo que responderá la consulta."
}}
"""

def query_dual_engine(user_prompt: str, db: Session) -> dict:
    """
    Executes conversational query using Dual-Engine architecture (Local Ollama / Gemini API)
    with strict security validation, read-only SQL execution, and deterministic fallback.
    """
    clean_prompt = sanitize_text_for_llm(user_prompt)
    if not clean_prompt:
        return execute_fallback_intent("resumen", db)
        
    start_time = time.time()
    model_name = settings.OLLAMA_MODEL
    prompt_tokens = 0
    completion_tokens = 0
    ai_status = "SUCCESS"
    sql_executed = None
    
    try:
        # A. Intentar con Gemini si existe API Key
        if settings.GEMINI_API_KEY and settings.LLM_PROVIDER == "gemini":
            logger.info("[LLM_DUAL] Querying Gemini 1.5 Flash Cloud...")
            model_name = "gemini-1.5-flash"
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\nPregunta: {clean_prompt}\nJSON:"}]}
                ],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
            }
            res = requests.post(gemini_url, json=payload, timeout=5)
            res.raise_for_status()
            res_json = res.json()
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            
        # B. Por defecto: Ollama Local (qwen2.5-coder:3b)
        else:
            logger.info(f"[LLM_DUAL] Querying Ollama Local ({model_name}) at {settings.OLLAMA_BASE_URL}...")
            ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": model_name,
                "prompt": f"{SYSTEM_PROMPT}\n\nPregunta: {clean_prompt}\nJSON:",
                "stream": False,
                "format": "json"
            }
            res = requests.post(ollama_url, json=payload, timeout=30)
            res.raise_for_status()
            res_data = res.json()
            raw_response = res_data.get("response", "")
            parsed = json.loads(raw_response)
            prompt_tokens = res_data.get("prompt_eval_count", 0)
            completion_tokens = res_data.get("eval_count", 0)

        # 1. Validar SQL generado
        sql_candidate = parsed.get("sql_query", "")
        validated_sql = validate_sql_query(sql_candidate)
        sql_executed = validated_sql
        logger.info(f"[LLM_DUAL] Validated SQL: {validated_sql}")

        # 2. Ejecutar SQL en modo Solo Lectura
        rows = db.execute(text(validated_sql)).fetchall()
        
        # 3. Construir Gráfico Declarativo si aplica
        chart_type = parsed.get("chart_type", "none").lower()
        chart_title = parsed.get("chart_title", "Visualización Sísmica")
        
        chart_obj = {"type": "none"}
        if chart_type != "none" and rows and len(rows[0]) >= 2:
            labels = [str(r[0]) for r in rows]
            data = [float(r[1]) if isinstance(r[1], (int, float)) else str(r[1]) for r in rows]
            chart_obj = build_declarative_chart(
                chart_type=chart_type,
                title=chart_title,
                labels=labels,
                data=data
            )

        explanation = parsed.get("explanation") or f"Consulta ejecutada con éxito. Se obtuvieron {len(rows)} registros."
        
        # Inyectar datos numéricos concretos de la base de datos para máxima interactividad
        if len(rows) == 1 and len(rows[0]) == 1:
            val = rows[0][0]
            explanation = f"Se registran **{val}** en la base de datos (capa Gold). {explanation}"
        elif rows and len(rows) <= 8 and len(rows[0]) >= 2:
            summary_bullets = "\n".join([f"- **{r[0]}**: {r[1]}" for r in rows])
            explanation = f"{explanation}\n\nDatos obtenidos en Capa Gold:\n{summary_bullets}"
        elif rows:
            explanation = f"{explanation}\n\nSe encontraron {len(rows)} registros coincidentes en la capa Gold."
        latency_ms = int((time.time() - start_time) * 1000)

        # 4. Registrar en audit.ai_executions
        record_ai_execution(
            task_name="text_to_sql_chat",
            prompt_version="v1.0",
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status="SUCCESS",
            db=db
        )

        return {
            "answer": explanation,
            "chart": chart_obj,
            "sql_executed": sql_executed,
            "suggested_questions": ["¿Hay sismos con alerta de tsunami?", "Ver distribución por severidad", "Sismos más fuertes"],
            "model_used": model_name,
            "latency_ms": latency_ms,
            "fallback_active": False
        }

    except Exception as e:
        logger.warning(f"[LLM_DUAL] LLM generation or execution failed ({e}). Switching to Circuit Breaker Fallback.")
        latency_ms = int((time.time() - start_time) * 1000)
        
        record_ai_execution(
            task_name="text_to_sql_chat",
            prompt_version="v1.0",
            model_name=f"{model_name}-fallback",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency_ms,
            status="FALLBACK",
            db=db
        )
        return execute_fallback_intent(clean_prompt, db, latency_ms=latency_ms)

def record_ai_execution(task_name: str, prompt_version: str, model_name: str, prompt_tokens: int, completion_tokens: int, latency_ms: int, status: str, db: Session = None):
    """Logs LLM interaction metrics into audit.ai_executions (PDF Pág. 5) using admin connection."""
    try:
        with engine_admin.connect() as conn:
            conn.execute(text("""
                INSERT INTO audit.ai_executions (
                    task_name, prompt_version, model_name,
                    prompt_tokens, completion_tokens, latency_ms,
                    estimated_cost_usd, status
                ) VALUES (:task, :ver, :model, :p_tok, :c_tok, :lat, 0.0, :stat)
            """), {
                "task": task_name,
                "ver": prompt_version,
                "model": model_name,
                "p_tok": prompt_tokens,
                "c_tok": completion_tokens,
                "lat": latency_ms,
                "stat": status
            })
            conn.commit()
    except Exception as e:
        logger.error(f"[LLM_DUAL] Error writing AI execution log: {e}")
        db.rollback()
