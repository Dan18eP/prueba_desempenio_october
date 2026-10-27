# ADR 0009: Arquitectura de Motor Dual para IA (Local/Cloud) y Blindaje de Seguridad OWASP

## Estado
Aprobado

## Contexto
Para garantizar máxima potencia y precisión en la generación de consultas Text-to-SQL y redacción analítica sin comprometer la memoria del servidor local ni el linaje de datos, se adopta un **Motor Dual Híbrido** que soporta tanto un modelo local de alta eficiencia (`qwen2.5-coder:3b` vía Ollama) como un modelo cloud de última generación (ej. Gemini 1.5 Flash vía API).
Esta decisión debe alinearse rigurosamente con los 6 requerimientos de seguridad del PDF de evaluación y las directrices de seguridad para aplicaciones con LLM (OWASP Top 10 for LLMs).

## Decisión

### 1. Cumplimiento Estricto de las Normas de Seguridad del PDF
1. **Gestión de Secretos (Zero Secrets in Repo):**
   - La clave `GEMINI_API_KEY` (si se utiliza) se inyecta exclusivamente mediante variables de entorno en tiempo de ejecución.
   - El archivo `.env` está estrictamente ignorado en `.gitignore`. En `.env.example` solo se expone `GEMINI_API_KEY=` como campo opcional vacío.
2. **Mitigación de Inyección de Instrucciones (OWASP LLM01 - Prompt Injection):**
   - El feed público de USGS contiene cadenas de texto abiertas como el campo `place` (ej. "12km SW of Volcano, Hawaii").
   - Todos los valores de texto se procesan mediante `sanitize_text_for_llm()` antes de ser concatenados al prompt, eliminando caracteres de escape, saltos de línea y patrones de inyección de comandos.
3. **Mínimo Privilegio y Prevención de Agencia Excesiva (OWASP LLM06):**
   - El agente conversacional utiliza exclusivamente la conexión de base de datos `sismo_app_readonly`.
   - Cualquier consulta SQL generada por el LLM se valida sintácticamente antes de ejecutarse: debe iniciar estrictamente con `SELECT` y no contener palabras clave destructivas (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `GRANT`, `TRUNCATE`).
   - Si una consulta intenta salir de `curated`, PostgreSQL devuelve un error de permisos inmediato.
4. **Comunicaciones Seguras y Timeouts:**
   - La comunicación con proveedores cloud se realiza mediante HTTPS cifrado TLS 1.3 con timeout estricto de 5 segundos.
5. **Auditoría de Ejecución y Monitoreo de Costos:**
   - Cada interacción (sea local o cloud) se registra en `audit.ai_executions` guardando modelo utilizado, tokens de entrada, tokens de salida, latencia en ms y costo estimado en USD (0.00 para local y conforme al tier para cloud).
6. **Logs Sanitizados:**
   - Queda prohibido escribir tokens JWT, API keys o el prompt crudo completo con datos sensibles en los logs del servidor.

## Consecuencias
- **Positivas:**
  - Máxima flexibilidad: opera 100% offline y gratuito con `qwen2.5-coder:3b`, o ultra-rápido en la nube con Gemini sin consumir RAM del host.
  - Cero riesgo de fuga de credenciales o inyección de código en base de datos.
  - Conformidad total con la rúbrica oficial de seguridad.
- **Negativas:**
  - Requiere mantener un cliente de inferencia unificado capaz de formatear el esquema para ambos proveedores (resuelto mediante interfaz abstracta en `api/services/llm_client.py`).
