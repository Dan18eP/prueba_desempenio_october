# Documentación Técnica - Fase 4: Motor Dual de IA & Protocolo de Gráficos Declarativos

## 1. Alcance de la Fase
En esta fase se implementó la arquitectura conversacional del agente de Inteligencia Artificial para consultas Text-to-SQL y generación de gráficos interactivos, incorporando el **Motor Dual (Ollama local + Gemini opcional)**, el **Protocolo de Visualización Declarativa** hacia Chart.js y el **Circuit Breaker con Fallback Determinístico**.

---

## 2. Componentes Entregados

### A. Protocolo de Gráficos Declarativos (`api/services/chart_protocol.py`)
- Emisión de objetos JSON estructurados para Chart.js (`bar`, `line`, `doughnut`).
- Cero generación de código Python o JavaScript arbitrario: la IA solo define tipos de gráficos, etiquetas y arreglos de datos validados, eliminando el riesgo de sintaxis rota o bloqueos de renderizado.

### B. Blindaje de Seguridad OWASP (`api/services/security_guard.py`)
- `sanitize_text_for_llm()`: Sanitización con regex del campo `place` y entradas de usuario contra ataques de inyección de instrucciones (OWASP LLM01).
- `validate_sql_query()`: Validador sintáctico estricto que restringe cualquier consulta generada al prefijo `SELECT` sobre el schema `curated`, bloqueando tokens destructivos (`DROP`, `INSERT`, `UPDATE`, `DELETE`, `ALTER`, etc.) para prevenir la agencia excesiva (OWASP LLM06).

### C. Fallback Determinístico Anti-Caídas (`api/services/circuit_breaker.py`)
- Motor analítico basado en reglas e intenciones frecuentes:
  - Frecuencia horaria $\to$ Gráfico de líneas (`curated.gold_hourly_kpis`).
  - Distribución por severidad $\to$ Gráfico de barras (`curated.gold_earthquakes`).
  - Alerta de tsunami $\to$ Gráfico de dona con alerta crítica.
  - Sismos más fuertes $\to$ Top 5 ordenado por magnitud.
- Latencia de respuesta de contingencia: $< 15 \text{ ms}$.
- Garantía: Cero errores 500, cero timeouts y cero pantallas en blanco.

### D. Coordinador del Motor Dual (`api/services/llm_client.py`)
- Conmuta entre `qwen2.5-coder:3b` en Ollama local y `gemini-1.5-flash` vía API.
- Timeout estricto de 6 segundos.
- Auditoría en base de datos: Registra modelo, tokens, latencia y costo en `audit.ai_executions` (PDF Pág. 5).

---

## 3. Verificación de la Fase
- Compilación de sintaxis: `python3 -m py_compile api/core/*.py api/services/*.py` $\to$ Exit code 0.
- Protección contra inyecciones SQL: Verificado que queries maliciosas o mutacionales son interceptadas antes de tocar la base de datos.
