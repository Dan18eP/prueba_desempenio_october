# Documentación Técnica - Fase 3: Machine Learning de Anomalías & Reporte Diario con IA

## 1. Alcance de la Fase
En esta fase se implementaron los dos módulos analíticos de Inteligencia Artificial exigidos por la prueba (PDF Pág. 5):
1. **Detección analítica de anomalías y enjambres sísmicos (ML Estadístico).**
2. **Generación automática del reporte ejecutivo diario con IA Generativa (Motor Dual).**

---

## 2. Componentes Entregados

### A. Detección de Anomalías Sísmicas (`airflow/include/anomaly_detection.py`)
- **Algoritmo Z-Score:**
  Calcula para cada sismo entrante:
  $$Z = \frac{M - \mu_M}{\sigma_M}$$
  donde $\mu_M$ y $\sigma_M$ se obtienen de la distribución muestral de magnitudes.
- **Detección de Enjambres (Swarm Detection):**
  Monitorea la densidad de eventos agrupados por ventana horaria. Si una hora concentra $\ge 10$ sismos y la magnitud es significativa ($\ge 4.0$), se clasifica como enjambre sísmico.
- **Explicación Determinística:**
  Cada anomalía incluye una explicación concisa y sin ambigüedades en `anomaly_explanation` (ejemplo: *"Sismo de magnitud 5.8 supera en 2.87 desviaciones estándar el promedio regional (mu=3.10)"*).

### B. Prompt Versionado y Esquema Estructurado (`airflow/include/prompts/daily_summary_v1.txt`)
- Prompt de sistema versionado (`v1.0`) que prohíbe explícitamente al LLM inventar o alterar cualquier métrica.
- Salida forzada mediante esquema Pydantic / JSON estructurado (`title`, `period`, `executive_summary`, `verified_metrics`, `most_active_region`, `risk_assessment`).

### C. DAG Diario con IA (`airflow/dags/dag_daily_ai_report.py`)
- **Ground Truth Inviolable:** Las cifras se calculan primero en PostgreSQL mediante consultas SQL de agregación sobre `curated.gold_earthquakes`.
- **Motor Dual con Circuit Breaker:**
  - Intenta llamada con timeout a Ollama local (`qwen2.5-coder:3b`).
  - Si el servicio excede 8 segundos o falla, conmuta automáticamente al **Motor Determinístico de Contingencia**, generando la síntesis exacta sin romper el pipeline.
- **Validación Matemática:**
  - Verifica que las cifras de magnitud y conteo aparezcan en el texto generado.
  - Guarda el resultado en `curated.gold_ai_reports` con el flag `verified_match`.
- **Auditoría de IA (PDF Pág. 5):**
  - Cada ejecución registra en `audit.ai_executions`: `model_name`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `estimated_cost_usd` y `status`.
- **Emisión de Linaje:**
  - Emite evento OpenLineage conectando `gold_earthquakes` y `gold_hourly_kpis` con `gold_ai_reports`.

---

## 3. Verificación de la Fase
- Compilación de sintaxis: `python3 -m py_compile airflow/dags/dag_daily_ai_report.py` $\to$ Exit code 0.
- Validación de controles anti-alucinación: Respaldado por Ground Truth SQL antes de redactar.
