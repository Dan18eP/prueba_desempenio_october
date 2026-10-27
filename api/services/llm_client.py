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
from api.services.security_guard import sanitize_text_for_llm, validate_sql_query, classify_and_intercept_intent
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
Eres SismoWatch AI, asistente analítico y especialista en Text-to-SQL sismológico para operaciones críticas.
Tu tarea es convertir la pregunta del usuario en una consulta SQL de solo lectura (SELECT) precisa y segura sobre las tablas del esquema curated.

{GOLD_SCHEMA_CONTEXT}

REGLAS DE GENERACIÓN SQL ESTRICTAS:
1. Solo genera consultas SELECT. Jamás uses INSERT, UPDATE, DELETE, DROP ni ALTER.
2. Todas las consultas deben ejecutarse contra las tablas curated.gold_earthquakes o curated.gold_hourly_kpis.
3. FILTROS DE TIEMPO INTELIGENTES:
   - Si el usuario menciona "hoy", "últimas 24 horas", "recientes" o "en curso":
     Agrega: WHERE event_time_utc >= NOW() - INTERVAL '24 hours'
   - Si menciona "última semana" o "7 días":
     Agrega: WHERE event_time_utc >= NOW() - INTERVAL '7 days'
   - Si menciona "mes", "últimos 30 días", "histórico", "total" o no especifica tiempo:
     Consulta sin límite de fecha para abarcar el catálogo completo.
4. REGLAS DE CONDICIONES ESPECIALES:
   - "tsunami": WHERE tsunami_alert = TRUE
   - "anomalía", "anomalías", "enjambre": WHERE is_anomaly = TRUE
5. ORDENAMIENTO Y LÍMITES EN LISTADOS:
   - Cuando el usuario pida ver sismos, anomalías o listados ("cuáles son", "muestra", "top", "más fuertes"):
     Selecciona columnas clave: magnitude, place, depth_km, severity_label, anomaly_explanation, event_time_utc
     Ordena siempre: ORDER BY magnitude DESC (o event_time_utc DESC si pide recientes)
     Limita siempre: LIMIT 5 o LIMIT 10 (nunca devuelvas miles de filas sin límite).
6. SELECCIÓN DE GRÁFICO (chart_type):
   - Series por hora o tendencia temporal -> "line"
   - Comparación de categorías, regiones o severidades -> "bar"
   - Proporciones o distribución porcentual -> "doughnut" o "pie"
   - Respuestas puntuales, escalares o tablas de sismos específicos -> "none"

Responde ÚNICAMENTE con un JSON válido con este formato (opciones para chart_type: "bar", "line", "doughnut", "pie", "none"):
{{
  "sql_query": "SELECT severity_label, COUNT(*) FROM curated.gold_earthquakes GROUP BY severity_label ORDER BY count DESC;",
  "chart_type": "bar",
  "chart_title": "Distribución por Severidad",
  "explanation": "Interpretación analítica concisa del resultado como experto sismólogo."
}}
"""

def query_dual_engine(user_prompt: str, db: Session) -> dict:
    """
    Executes conversational query using Dual-Engine architecture (Local Ollama / Gemini API)
    with strict security validation, read-only SQL execution, and deterministic fallback.
    """
    # Interceptar determinísticamente saludos, amenazas o mensajes fuera de dominio
    intercepted = classify_and_intercept_intent(user_prompt)
    if intercepted:
        return intercepted

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
            clean_json_str = re.sub(r'//.*', '', raw_response)
            parsed = json.loads(clean_json_str)
            prompt_tokens = res_data.get("prompt_eval_count", 0)
            completion_tokens = res_data.get("eval_count", 0)

        # 1. Validar SQL generado
        sql_candidate = parsed.get("sql_query", "")
        validated_sql = validate_sql_query(sql_candidate)
        sql_executed = validated_sql
        logger.info(f"[LLM_DUAL] Validated SQL: {validated_sql}")

        # 2. Ejecutar SQL en modo Solo Lectura
        sql_res = db.execute(text(validated_sql))
        cols = list(sql_res.keys())
        rows = sql_res.fetchall()
        
        # 3. Construir Gráfico Declarativo si aplica
        chart_type = parsed.get("chart_type", "none").lower()
        chart_title = parsed.get("chart_title", "Visualización Sísmica")
        
        chart_obj = {"type": "none"}
        if chart_type != "none" and rows and len(rows[0]) >= 2:
            # Seleccionar columnas de etiqueta y métrica inteligentemente
            lbl_idx = 0
            val_idx = 1
            if len(cols) >= 2:
                for idx, c in enumerate(cols):
                    if c in ("place", "severity_label", "hour_utc", "id"):
                        lbl_idx = idx
                        break
                for idx, c in enumerate(cols):
                    if idx != lbl_idx and (c in ("count", "magnitude", "total_events", "max_magnitude", "depth_km") or isinstance(rows[0][idx], (int, float))):
                        val_idx = idx
                        break

            labels = [str(r[lbl_idx]) for r in rows[:15]]
            data = [float(r[val_idx]) if isinstance(r[val_idx], (int, float)) else str(r[val_idx]) for r in rows[:15]]
            chart_obj = build_declarative_chart(
                chart_type=chart_type,
                title=chart_title,
                labels=labels,
                data=data
            )

        raw_expl = str(parsed.get("explanation") or "").strip()
        # Sanitizar meta-comentarios sobre ausencia de graficos o ecos del prompt
        meta_chart_phrases = [
            r"(?i)este\s+gr[aá]fico\s+no\s+est[aá]\s+disponible[^\.\n]*\.?",
            r"(?i)no\s+se\s+muestra\s+ning[uú]n\s+gr[aá]fico[^\.\n]*\.?",
            r"(?i)debido\s+a\s+que\s+la\s+pregunta\s+no\s+especifica\s+una\s+solicitud\s+de\s+gr[aá]fico[^\.\n]*\.?",
            r"(?i)esta\s+consulta\s+no\s+requiere\s+gr[aá]fico[^\.\n]*\.?",
            r"(?i)no\s+se\s+gener[oó]\s+gr[aá]fico[^\.\n]*\.?",
            r"(?i)interpretaci[oó]n\s+anal[ií]tica\s+concisa[^\.\n]*\.?",
            r"(?i)nterpretaci[oó]n\s+anal[ií]tica[^\.\n]*\.?"
        ]
        for pat in meta_chart_phrases:
            raw_expl = re.sub(pat, "", raw_expl).strip()

        # Limpiar texto de plantilla repetido o caracteres iniciales truncados
        if not raw_expl or len(raw_expl) < 5 or raw_expl.lower().startswith("interpretación") or raw_expl.lower().startswith("nterpretación"):
            if "tsunami" in clean_prompt.lower():
                explanation = "Sismos con protocolo de alerta de tsunami activo registrados en la capa Gold:"
            elif "mayor" in clean_prompt.lower() or "magnitud" in clean_prompt.lower():
                explanation = "Eventos sísmicos registrados con magnitudes superiores al umbral consultado (capa Gold):"
            elif "anomal" in clean_prompt.lower():
                explanation = "Eventos sísmicos clasificados como anomalías estadísticas (Z-Score > 2.5 o enjambres):"
            elif "severidad" in clean_prompt.lower():
                explanation = "Distribución de sismos en la capa Gold clasificados por nivel de severidad:"
            else:
                explanation = f"Consulta analítica ejecutada exitosamente sobre la capa Gold ({len(rows)} registros obtenidos):"
        else:
            explanation = raw_expl
        
        # Inyectar datos numéricos concretos y tablas Markdown enriquecidas
        if len(rows) == 1 and len(rows[0]) == 1:
            val = rows[0][0]
            explanation = f"Se registran **{val}** en la base de datos (capa Gold). {explanation}"
        elif rows and len(rows) <= 10 and len(rows[0]) == 2 and not isinstance(rows[0][1], str):
            summary_bullets = "\n".join([f"- **{r[0]}**: {r[1]}" for r in rows])
            explanation = f"{explanation}\n\nDatos obtenidos en Capa Gold:\n{summary_bullets}"
        elif rows:
            top_rows = rows[:5]
            # Mapeo y proyección estricta a máximo 5 columnas para legibilidad humana
            KEY_COLUMNS = [
                ("magnitude", "Magnitud"),
                ("place", "Ubicación"),
                ("depth_km", "Profundidad (km)"),
                ("event_time_utc", "Hora Bogotá (COT)"),
                ("severity_label", "Severidad"),
                ("anomaly_explanation", "Detalle Criterio"),
                ("tsunami_alert", "Alerta Tsunami")
            ]
            
            projected_indices = []
            projected_headers = []
            for col_key, col_header in KEY_COLUMNS:
                if col_key in cols:
                    projected_indices.append(cols.index(col_key))
                    projected_headers.append(col_header)

            # Si no coincide con las columnas estándar, proyectar máximo las primeras 4 columnas
            if not projected_indices:
                projected_indices = list(range(min(4, len(cols))))
                projected_headers = [cols[i].replace('_', ' ').capitalize() for i in projected_indices]

            table_lines = [
                "\n| " + " | ".join(projected_headers) + " |",
                "| " + " | ".join([":---:" if "mag" in h.lower() or "prof" in h.lower() else ":---" for h in projected_headers]) + " |"
            ]

            for r in top_rows:
                row_vals = []
                for idx in projected_indices:
                    val = r[idx]
                    col_name = cols[idx]
                    if col_name == "event_time_utc" and val:
                        # Convertir a formato legible en hora Bogotá si es timestamp
                        ts_str = str(val).split(".")[0].replace("T", " ")
                        row_vals.append(ts_str)
                    elif col_name == "magnitude" and isinstance(val, (int, float)):
                        row_vals.append(f"**M {float(val):.1f}**")
                    elif isinstance(val, float):
                        row_vals.append(f"{val:.2f}")
                    elif val is None:
                        row_vals.append("--")
                    else:
                        row_vals.append(str(val))
                table_lines.append("| " + " | ".join(row_vals) + " |")

            explanation = f"{explanation}\n\nSe identificaron **{len(rows)}** registros coincidentes en la capa Gold:\n" + "\n".join(table_lines)

        # Generar gráfico declarativo si la consulta es sobre tsunamis y el modelo no generó uno
        if "tsunami" in clean_prompt.lower() and chart_obj["type"] == "none" and rows and "magnitude" in cols:
            p_idx = cols.index("place") if "place" in cols else 0
            m_idx = cols.index("magnitude")
            t_labels = [str(r[p_idx])[:25] for r in rows[:6]]
            t_data = [float(r[m_idx]) for r in rows[:6]]
            chart_obj = build_declarative_chart(
                chart_type="bar",
                title="Sismos con Alerta de Tsunami (Magnitud por Región)",
                labels=t_labels,
                data=t_data,
                dataset_label="Magnitud M",
                color_palette=["#ef4444"] * len(t_data)
            )

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
        
        # Anti-Crash Guarantee: Reset aborted PostgreSQL transaction before running fallback
        try:
            db.rollback()
        except Exception as rb_err:
            logger.warning(f"[LLM_DUAL] db.rollback() caught: {rb_err}")

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
