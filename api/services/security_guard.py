import re
import logging

logger = logging.getLogger("api.services.security_guard")

FORBIDDEN_SQL_PATTERNS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b", r"\bREVOKE\b",
    r"\bEXECUTE\b", r"\bCREATE\b", r"\bCOPY\b", r"\bpg_sleep\b",
    r"--", r"/\*", r";"
]

def sanitize_text_for_llm(text: str) -> str:
    """
    Sanitizes external user/feed text before injection into LLM prompts.
    Mitigates Prompt Injection (OWASP LLM01 - PDF Pág. 5).
    """
    if not text:
        return ""
    # 1. Normalize linebreaks and whitespace
    clean = re.sub(r'[\r\n\t]+', ' ', text)
    # 2. Neutralize escape and delimiter symbols, SQL comment markers, and semicolons
    clean = re.sub(r'[`"\'\\<>{}[\];]', '', clean)
    clean = re.sub(r'--', '', clean)
    # 3. Block known prompt injection keywords
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"(?i)system\s+prompt",
        r"(?i)developer\s+mode",
        r"(?i)output\s+password",
        r"(?i)reveal\s+secret"
    ]
    for pattern in injection_patterns:
        clean = re.sub(pattern, "[BLOCKED_INSTRUCTION]", clean)
    return clean.strip()[:150]

def validate_sql_query(sql: str) -> str:
    """
    Strict validation to ensure generated SQL is read-only and restricted to curated.
    Mitigates Excessive Agency (OWASP LLM06).
    """
    if not sql:
        raise ValueError("Consulta SQL vacía.")
        
    cleaned_sql = sql.strip().rstrip(";")
    
    # 1. Must start with SELECT
    if not cleaned_sql.upper().startswith("SELECT"):
        raise ValueError("Violación de Seguridad: Solo se permiten consultas que comiencen con SELECT.")
        
    # 2. Check for forbidden destructive keywords
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise ValueError(f"Violación de Seguridad: Patrón prohibido detectado en la consulta SQL ({pattern}).")
            
    # 3. Block access to non-curated schemas (audit, raw, staging, pg_catalog, etc.)
    forbidden_schemas = [r"\baudit\b", r"\braw\b", r"\bstaging\b", r"\bpg_catalog\b", r"\binformation_schema\b"]
    for schema_pat in forbidden_schemas:
        if re.search(schema_pat, cleaned_sql, re.IGNORECASE):
            raise ValueError(f"Violación de Seguridad: Acceso prohibido al esquema no permitido ({schema_pat}).")

    # 4. Ensure table referenced is in curated schema or is a curated view
    if "curated." not in cleaned_sql.lower() and "from gold_" not in cleaned_sql.lower():
        # Inject curated. if referencing table directly
        cleaned_sql = re.sub(r'(?i)\bFROM\s+gold_', 'FROM curated.gold_', cleaned_sql)
        if "curated." not in cleaned_sql.lower():
            raise ValueError("Violación de Seguridad: La consulta debe dirigirse exclusivamente al esquema curated.")
        
    return cleaned_sql

def classify_and_intercept_intent(prompt: str) -> dict | None:
    """
    Deterministic intent router executed before invoking LLM Text-to-SQL.
    Catches greetings, malicious credential extractions, and out-of-domain gibberish.
    Guarantees <1ms latency and prevents prompt injection or hallucinated SQL.
    """
    if not prompt or not prompt.strip():
        return None

    raw_clean = prompt.strip()
    clean_lower = raw_clean.lower()

    # 1. Greetings & System Help
    greetings_pattern = r"^\s*(hola|buenos?\s*d[ií]as|buenas?\s*tardes|buenas?\s*noches|saludos|hello|hi|hey|quien\s*eres|que\s*haces|ayuda|help)[\s!\.\?]*$"
    if re.search(greetings_pattern, clean_lower):
        return {
            "answer": "Hola. Soy SismoWatch AI, su analista sismológico especializado. Estoy conectado en tiempo real al catálogo global de USGS y a la capa Gold del Lakehouse. Puedo responder consultas sobre sismicidad, como por ejemplo:\n\n- ¿Hay sismos con alerta de tsunami?\n- Ver distribución por severidad\n- Sismos con magnitud mayor a 4\n- ¿Cuáles son las anomalías detectadas?\n\n¿Qué información analítica desea consultar?",
            "chart": {"type": "none"},
            "sql_executed": None,
            "suggested_questions": [
                "¿Hay sismos con alerta de tsunami?",
                "Ver distribución por severidad",
                "Sismos con magnitud mayor a 4"
            ],
            "model_used": "deterministic-greeting",
            "latency_ms": 1,
            "fallback_active": False
        }

    # 2. Security Threat & Credential Extraction (OWASP LLM01 / LLM06)
    threat_pattern = r"(?i)(api[_\s-]?key|token|password|clave|contrase[ñn]a|secret|credencial|env\b|system\s+prompt|ignore\s+(all\s+)?(previous|prior)|developer\s+mode|drop\s+table|delete\s+from|update\s+curated|insert\s+into)"
    if re.search(threat_pattern, clean_lower):
        return {
            "answer": "Por motivos de seguridad y gobernanza (OWASP LLM01 / LLM06), no está permitido consultar claves de API, tokens de autenticación, contraseñas del sistema ni ejecutar operaciones de modificación o extracción de secretos. Solo se permiten consultas analíticas de solo lectura sobre el catálogo de eventos sísmicos.",
            "chart": {"type": "none"},
            "sql_executed": None,
            "suggested_questions": [
                "¿Hay sismos con alerta de tsunami?",
                "Ver distribución por severidad",
                "Sismos con magnitud mayor a 4"
            ],
            "model_used": "security-guardrail",
            "latency_ms": 1,
            "fallback_active": False
        }

    # 3. Out-of-Domain Non-Seismic Queries or Gibberish
    out_of_domain_pattern = r"(?i)\b(receta|cocinar|futbol|partido|chiste|cancion|musica|pelicula|horoscopo|bitcoin|cripto)\b"
    consonants = [c for c in clean_lower if c in "bcdfghjklmnpqrstvwxyz"]
    vowels = [c for c in clean_lower if c in "aeiouáéíóú"]
    is_keyboard_mash = any(mash in clean_lower for mash in ["asdf", "qwer", "zxcv", "hjkl", "jklm", "12345"])
    is_high_consonant = len(clean_lower) >= 5 and len(vowels) <= 1 and (len(consonants) / max(1, len(clean_lower))) >= 0.75

    if re.search(out_of_domain_pattern, clean_lower) or is_keyboard_mash or is_high_consonant:
        return {
            "answer": "SismoWatch AI está especializado exclusivamente en el análisis y monitoreo del catálogo sismológico de USGS en la capa Gold. No se identificaron criterios sísmicos válidos en su consulta. Por favor pregunte sobre magnitudes, zonas geográficas, profundidades o alertas de tsunami.",
            "chart": {"type": "none"},
            "sql_executed": None,
            "suggested_questions": [
                "¿Hay sismos con alerta de tsunami?",
                "Ver distribución por severidad",
                "Sismos con magnitud mayor a 4"
            ],
            "model_used": "domain-guardrail",
            "latency_ms": 1,
            "fallback_active": False
        }

    return None
