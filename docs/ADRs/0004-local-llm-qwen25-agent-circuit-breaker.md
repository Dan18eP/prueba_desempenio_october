# ADR 0004: Agente Conversacional Local con Qwen 2.5 (1.5B) y Circuit Breaker Anti-Caídas

## Estado
Aprobado

## Contexto
El sistema debe incluir capacidades de Inteligencia Artificial para el análisis de sismos, generación de reportes y un agente conversacional para interactuar con los datos. La directriz del usuario exige:
- Modelo de IA ejecutándose **en local** (sin depender de API keys externas costosas o inestables).
- Máxima calidad y rapidez.
- Cero caídas ("que no se caiga nunca").
- Conexión directa a la capa Gold.

El hardware local cuenta con 12 núcleos de CPU y sin GPU dedicada.

## Decisión
1. **Selección del Modelo Local:**
   - Se selecciona **Qwen 2.5 (1.5B)** servido localmente a través de Ollama.
   - *Justificación:* Ofrece uno de los rendimientos más altos del estado del arte en razonamiento matemático y generación de SQL estructurado en su categoría de peso, con una latencia de 1 a 2 segundos en CPU y un consumo de memoria inferior a 1.3 GB de RAM.
2. **Conexión Exclusiva a la Capa Gold (`curated`):**
   - El agente recibe en su system prompt únicamente el esquema de las tablas Gold de PostgreSQL (`curated.gold_earthquakes`, `curated.gold_hourly_kpis`, `curated.gold_anomalies`).
   - El agente opera bajo un rol de base de datos con permisos estrictos de solo lectura (`SELECT`).
3. **Mecanismo Anti-Alucinación (Cifras Calculadas por Código):**
   - Las cifras clave (conteo de sismos, magnitud máxima, promedios) se calculan mediante consultas SQL parametrizadas antes o durante la generación de texto. El LLM solo redacta el texto descriptivo.
4. **Resiliencia Extrema: Circuit Breaker y Fallback Determinístico:**
   - Se establece un timeout estricto de 6 segundos para la llamada al LLM.
   - Si Ollama no está disponible, se satura o excede el timeout, se activa inmediatamente el **Fallback Determinístico Basado en Reglas**:
     - Analiza la intención del usuario mediante coincidencia semántica / palabras clave (ej: "sismo más fuerte", "últimas 24 horas", "tsunami").
     - Ejecuta la consulta SQL analítica directa en PostgreSQL Gold.
     - Devuelve una respuesta precisa estructurada en lenguaje natural al usuario.
   - El usuario final nunca experimenta un error 500, timeout ni pantalla en blanco.

## Consecuencias
- **Positivas:**
  - 100% de disponibilidad garantizada del agente conversacional.
  - Cero costos de API externa y total privacidad de datos.
  - Protección robusta contra inyección de prompts y alucinaciones.
- **Negativas:**
  - En momentos de activación del fallback, las respuestas tienen un tono más estructurado/plantilla que conversacional libre, pero los datos son 100% exactos y confiables.
