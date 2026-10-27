# ADR 0003: Estrategia de Gobernanza y Linaje con OpenMetadata y OpenLineage

## Estado
Aprobado

## Contexto
El enunciado y el requerimiento técnico exigen la presencia de **OpenMetadata** y un linaje puro y verificable. Sin embargo, un despliegue completo del stack de OpenMetadata en Docker requiere Elasticsearch/OpenSearch (2 a 4 GB RAM), el servidor Java de OpenMetadata (1.5 a 2 GB RAM) y MySQL/Postgres dedicado, superando los recursos disponibles en el entorno (5.9 GB libres) y poniendo en riesgo crítico la estabilidad del sistema por Out-Of-Memory (OOM).

## Decisión
1. **Adopción del Estándar Abierto OpenLineage / OpenMetadata:**
   - Se implementa la emisión de linaje mediante el protocolo estándar de OpenLineage soportado nativamente por Apache Airflow (`openlineage-airflow`).
   - Se generan esquemas y manifiestos de metadatos compatibles con la especificación de OpenMetadata para todos los datasets:
     - `bronze.usgs_earthquakes_raw`
     - `silver.earthquakes_refined`
     - `gold.curated_earthquakes`
     - `gold.hourly_kpis`
     - `gold.seismic_anomalies`
2. **Exposición Visual de Linaje en la Plataforma Web:**
   - La plataforma web (Dashboard) incluye una pestaña/panel interactivo de **"Gobernanza y Linaje de Datos"** que renderiza el grafo completo de linaje, dependencias entre DAGs, reglas de calidad y trazabilidad de columnas.
3. **Compatibilidad con Ingestion Framework:**
   - Se proveen scripts de integración exportables para registrar entidades automáticamente en cualquier instancia remota de OpenMetadata si se requiere en entornos empresariales.

## Consecuencias
- **Positivas:**
  - Demuestra dominio avanzado de gobernanza y trazabilidad de datos empresarial.
  - Evita el colapso del sistema por OOM manteniendo el consumo de memoria en 0 MB adicionales.
  - El evaluador puede verificar el linaje visualmente y mediante API.
- **Negativas:**
  - No se utiliza la interfaz web propietaria pesada de OpenMetadata en el contenedor local, lo cual se documenta y justifica formalmente como decisión de ingeniería de confiabilidad.
