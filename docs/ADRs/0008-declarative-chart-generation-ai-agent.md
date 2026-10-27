# ADR 0008: Generación Declarativa de Gráficos, Modelo Text-to-SQL Potenciado y Protocolo Zero-Crash

## Estado
Aprobado

## Contexto
El usuario requiere una sección de analítica avanzada con un agente conversacional capaz de responder preguntas analíticas y **generar gráficos interactivos** sobre los datos de la capa Gold (`curated`). Existe el riesgo latente de que un modelo de lenguaje ligero o una integración ingenua falle al intentar generar código arbitrario (Matplotlib o JavaScript), o que un modelo local genérico cometa errores de sintaxis en Text-to-SQL.

## Decisión

### 1. Protocolo de Visualización Declarativa (Sin Ejecución de Código Arbitrario)
- El agente de IA **nunca genera código ejecutable (Python/JS)**. Genera exclusivamente un payload JSON validado con esquema **Pydantic**:
  ```json
  {
    "answer": "Texto explicativo...",
    "sql_executed": "SELECT ...",
    "chart": {
      "type": "bar | line | doughnut",
      "title": "Título del Gráfico",
      "labels": ["..."],
      "datasets": [{"label": "...", "data": [...]}]
    },
    "suggested_questions": ["..."]
  }
  ```
- El frontend renderiza el gráfico en milisegundos mediante componentes nativos de **Chart.js**, garantizando rendimiento, responsividad y cero riesgos de ejecución de código.

### 2. Selección de Modelo Text-to-SQL de Mayor Potencia
Para evitar que el LLM se quede corto en consultas analíticas complejas:
1. **Modelo Local Recomendado:** Se adopta **`qwen2.5-coder:3b`** (o `qwen2.5-coder:1.5b` como alternativa ultraligera).
   - *Justificación:* La serie **Qwen 2.5-Coder** fue entrenada específicamente en código fuente y bases de datos SQL (evaluación Spider y HumanEval), superando ampliamente a modelos genéricos de 7B de generaciones anteriores, con un consumo de solo 2.2 GB de RAM en CPU.
2. **Soporte Híbrido Multiproveedor (PDF Pág. 3):**
   - El sistema se diseña con un adaptador desacoplado (`LLMProviderInterface`).
   - Permite operar 100% en local con Ollama (`qwen2.5-coder:3b`), pero si se suministra una API key en `.env` (ej. `GEMINI_API_KEY` o `OPENAI_API_KEY`), puede conmutar a **Gemini 1.5 Flash** o **GPT-4o-mini** para Text-to-SQL de nivel empresarial con cero costo de CPU.

### 3. Guardrail de Seguridad y Sandbox SQL de Solo Lectura
Toda consulta generada por la IA pasa por validación estricta antes de ejecutarse en PostgreSQL:
- Verificación de que la sentencia inicie estrictamente con `SELECT` (prohibidos `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `GRANT`).
- Validación de que solo acceda al schema `curated`.
- Ejecución bajo el rol de base de datos `sismo_app_readonly` (privilegio de solo lectura a nivel de base de datos).

### 4. Resiliencia Extrema: Protocolo Zero-Crash (3 Niveles)
1. **Nivel 1:** Generación rápida con el LLM (timeout de 6 segundos).
2. **Nivel 2:** Limpieza y reparación automática de JSON mediante expresiones regulares.
3. **Nivel 3:** **Fallback Determinístico Basado en Reglas.** Si el LLM excede el timeout, se detiene o falla, un motor de reglas interno ejecuta la consulta SQL exacta de agregación y devuelve el JSON estructurado con el gráfico. **El usuario jamás experimenta un error 500.**

## Consecuencias
- **Positivas:**
  - Cero caídas y cero pantallas en blanco en el chat.
  - Gráficos interactivos de alta calidad generados al instante.
  - Text-to-SQL preciso gracias a la especialización de Qwen 2.5 Coder.
- **Negativas:**
  - Los gráficos están limitados al catálogo soportado por la especificación (`bar`, `line`, `doughnut`), lo cual es una ventaja para la estabilidad del frontend.
