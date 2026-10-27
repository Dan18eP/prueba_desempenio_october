# ADR 0002: Procesamiento Distribuido con PySpark y Fidelidad de Datos (20 In -> 20 Out)

## Estado
Aprobado

## Contexto
El feed GeoJSON de USGS contiene datos jerárquicos (coordenadas en arrays `[lon, lat, depth]` y propiedades anidadas). Además, eventos anteriores pueden ser actualizados por el USGS (cambios en magnitud o estado de revisión). El TL ha establecido la directriz no negociable de **calidad y fidelidad absoluta**: "si me llegaron 20, mostré 20", prohibiendo cuarentenas que aíslen y eliminen registros de la visualización del usuario, pero cumpliendo a su vez con la rúbrica del PDF que exige auditoría de calidad y endpoints de cuarentena para el Admin.

## Decisión
1. **Adopción de PySpark en Modo Local:**
   - Se utiliza PySpark ejecutado en modo local (`local[*]`) orquestado por Airflow. Aprovecha los 12 núcleos de CPU sin requerir un cluster distribuido standalone que consuma RAM ociosa.
2. **Desanidación y Tipado:**
   - Extracción de columnas escalares: `longitude`, `latitude`, `depth_km`, `magnitude`, `place`, `time_utc`, `updated_utc`, `tsunami`, `sig`.
3. **Manejo de Actualizaciones e Idempotencia:**
   - Deduplicación lógica mediante funciones de ventana:
     $$\text{ROW\_NUMBER}() \text{ OVER (PARTITION BY id ORDER BY updated DESC)}$$
     Asegura que siempre prevalezca la versión más reciente emitida por USGS.
4. **Regla de Fidelidad (20 In -> 20 Out) y Cuarentena de Auditoría:**
   - Todos los registros recibidos se procesan a través de Silver y Gold.
   - Si un registro incumple reglas de validación (por ejemplo, coordenadas atípicas o magnitud faltante), se le asigna un tag de auditoría: `quality_flag = 'FLAGGED'` con `rejection_reason`.
   - Estos registros se registran en la tabla de auditoría para alimentar el endpoint administrativo `GET /api/quality/quarantine`, pero **no se eliminan del flujo**, preservando la integridad del volumen reportado.

## Consecuencias
- **Positivas:**
  - Garantiza balance y trazabilidad perfecta entre lo extraído y lo presentado.
  - Satisface tanto la regla de no-descarte del TL como el requerimiento de evaluación del PDF.
  - Rendimiento óptimo en Snappy Parquet.
- **Negativas:**
  - El esquema debe soportar campos nulos controlados o marcas de calidad sin abortar el job.
