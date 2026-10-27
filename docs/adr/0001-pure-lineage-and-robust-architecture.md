# ADR 0001: Arquitectura de Linaje Puro, Integración Spark/OpenMetadata y Resiliencia en DAGs

## Estado
Aprobado

## Contexto
La prueba de desempeño técnica "SismoWatch" exige una solución robusta de monitoreo sísmico con orquestación en Apache Airflow, controles estrictos de calidad, visualización en tiempo real y componentes de IA. Adicionalmente, el Technical Lead (TL) y el requerimiento operativo establecen directrices no negociables:
1. Inclusión obligatoria de **Apache Spark**, **Apache Airflow** y **OpenMetadata**.
2. **Linaje Puro:** Eliminar capas landing intermedias que desvíen datos a sistemas de archivos volátiles y evitar el descarte de registros mediante cuarentenas segregadas que rompan el balance de datos ("si llegaron 20, se procesan y muestran 20").
3. **Resiliencia Extrema:** Tareas protegidas con try-catch defensivos, timeouts, reintentos y tolerancia ante caídas de la API externa (USGS).
4. **Agente Conversacional Local:** Conexión a la capa Gold (curated) con alta disponibilidad y fallback garantizado frente a timeouts del modelo local.

## Decisiones

1. **Flujo de Linaje Puro Directo (API -> Bronze/Raw -> Silver/Staging -> Gold/Curated):**
   - No se utiliza directorio intermedio de landing (archivos sueltos en disco). La ingesta deposita directamente en el schema `raw` de PostgreSQL mediante transacciones idempotentes (`ON CONFLICT DO UPDATE`).
   - Todos los eventos recibidos se procesan a través de la cadena medallion. Para cumplir simultáneamente con la regla del TL ("20 recibidos, 20 mostrados") y el requisito de auditoría/calidad del PDF, los eventos con anomalías de calidad se marcan con flags de auditoría en la tabla de calidad sin ser suprimidos arbitrariamente del linaje.

2. **Procesamiento de Transformación y Calidad con PySpark:**
   - Se emplea PySpark en modo local (`local[*]`) optimizado para la memoria de la máquina (15GB RAM, sin GPU), ejecutando la limpieza, normalización de GeoJSON a tabular y validaciones de rango y tipos.

3. **Gobernanza y Linaje con OpenMetadata / OpenLineage:**
   - Se modela la emisión de linaje a nivel de datasets (`raw.usgs_feed -> staging.earthquakes -> curated.gold_earthquakes`) y pipelines de Airflow para trazabilidad completa.

4. **Agente Conversacional Local con Fallback Determinado:**
   - Modelo LLM local servido mediante Ollama / API local compatible (Qwen2.5/Llama3.2 en cuantización ligera CPU).
   - Generación de SQL restringido a modo solo lectura (`SELECT`) sobre el schema `curated`.
   - Implementación de un Circuit Breaker con fallback analítico basado en reglas para garantizar que el agente nunca genere pantallas de error si el modelo local se satura.

## Consecuencias
- **Positivas:** Linaje 100% auditable y visualizable; alta estabilidad sin bloqueos por OOM; cumplimiento del requisito de conciliación 20/20; experiencia de usuario impecable.
- **Riesgos Mitigados:** Caídas por latencia de API externa, desincronización de esquemas y fallos del LLM en entornos locales sin GPU.
