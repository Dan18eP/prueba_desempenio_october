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
