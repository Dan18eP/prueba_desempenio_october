# ADR 0008: Protocolo de Gráficos Declarativos y Estrategia del Agente Text-to-SQL

## Estado
Aprobado

## Contexto
El usuario y la evaluación exigen un agente conversacional conectado directamente a la capa Gold (`curated`) capaz no solo de responder preguntas analíticas, sino de **generar visualizaciones y gráficos dinámicos**. 
Sin embargo, los enfoques tradicionales donde un LLM genera código ejecutable libre (ej. scripts en Python con Matplotlib o scripts en JavaScript dinámico) presentan un alto riesgo de fallos en demostraciones en vivo: alucinación de librerías, sintaxis rota, bloqueos de seguridad y tiempos de respuesta elevados que pueden congelar la plataforma.

## Decisión

### 1. Protocolo de Visualización Declarativa (Declarative Chart Protocol)
- El agente conversacional **no genera código de ejecución**. En su lugar, emite un objeto **JSON estructurado** con especificación declarativa para componentes de frontend (Chart.js / Tailwind):
  ```json
  {
    "answer": "Explicación analítica en lenguaje natural...",
    "chart": {
      "type": "bar | line | doughnut | none",
      "title": "Título descriptivo del gráfico",
      "labels": ["Categoría A", "Categoría B"],
      "datasets": [{ "label": "Métrica", "data": [10, 25] }]
    },
    "sql_executed": "SELECT ... FROM curated.gold_earthquakes ...",
    "suggested_questions": ["Pregunta 1", "Pregunta 2"]
  }
  ```
- El frontend renderiza el `<canvas>` nativo al vuelo en milisegundos sin inyección de código arbitrario.

### 2. Blindaje Anti-Fallos en 3 Capas (Zero-Crash Architecture)
1. **Capa 1 (Inferencia Text-to-SQL Guiada):** Prompt de sistema con esquema denormalizado de la capa Gold (`curated.gold_earthquakes`, `curated.gold_hourly_kpis`, `curated.gold_anomalies`) y ejemplos *Few-Shot*.
2. **Capa 2 (Validador Pydantic con Regex Sanitizer):** Si el LLM emite texto explicativo previo al JSON, el backend extrae y limpia el bloque `{ ... }` automáticamente.
3. **Capa 3 (Circuit Breaker Determinístico con Templates SQL):**
   - Si el servicio del modelo local no responde en $\le 6 \text{ segundos}$ o se satura:
   - El motor de contingencia intercepta la consulta, mapea la intención a una plantilla SQL pre-optimizada en PostgreSQL y devuelve la respuesta junto con el gráfico correspondiente.
   - **Garantía:** Cero errores 500, cero tiempos de espera prolongados y cero pantallas en blanco.

## Consecuencias
- **Positivas:**
  - Gráficos y respuestas 100% confiables y determinísticas.
  - Integración fluida entre backend y frontend.
  - Mitigación absoluta de caídas en la sustentación.
- **Negativas:**
  - Los tipos de gráficos disponibles están acotados a los soportados por el protocolo (`bar`, `line`, `doughnut`, `scatter`).
