# ADR 0001: Arquitectura Medallón con MinIO y Linaje Puro (Sin Capa Landing)

## Estado
Aprobado

## Contexto
El monitoreo sísmico para SuperApp (SismoWatch) requiere procesar eventos en tiempo casi real desde el catálogo público USGS. La evaluación exige una arquitectura en capas (`raw`, `staging`, `curated`), pero existe la tentación de implementar capas intermedias volátiles de aterrizaje ("landing folders") o tablas de cuarentena que descarten datos de la vista de operaciones, violando la directriz del TL de "linaje puro" y la regla de conciliación de volumen ("si llegaron 20 registros, se muestran 20"). Adicionalmente, el almacenamiento en un sistema distribuido de objetos (Object Storage) representa la mejor práctica para desacoplar cómputo y almacenamiento en un Data Lakehouse moderno.

## Decisión
1. **Adopción de MinIO como Object Storage para el Lakehouse:**
   - Se despliega MinIO en el contenedor Docker local para gestionar los buckets del Lakehouse:
     - `s3://sismowatch-lake/bronze/`: Datos inmutables crudos.
     - `s3://sismowatch-lake/silver/`: Datos refinados en formato columnar Parquet (Snappy).
     - `s3://sismowatch-lake/gold/`: Agregaciones analíticas y métricas de negocio en Parquet.
2. **Eliminación explícita de la capa "Landing":**
   - El DAG de ingesta de Airflow descarga el feed de USGS y lo escribe **directamente en MinIO Bronze** particionado por fecha (`year=YYYY/month=MM/day=DD/feed_timestamp.json`).
   - No existen carpetas temporales ni zonas de aterrizaje fuera de la gobernanza de MinIO.
3. **Persistencia y Acceso Eficiente en PostgreSQL (Gold Curated):**
   - Para evitar sobreingeniería y latencia de escaneo de Parquet en peticiones HTTP, la capa Gold se replica/sincroniza en PostgreSQL en el schema `curated` mediante `INSERT ... ON CONFLICT (id) DO UPDATE`.
   - FastAPI y el Agente Conversacional leen directamente de PostgreSQL con índices optimizados.

## Consecuencias
- **Positivas:**
  - Desacoplamiento total entre cómputo (PySpark) y almacenamiento (MinIO/PostgreSQL).
  - Linaje 100% puro y continuo: `USGS -> Bronze (MinIO) -> Silver (MinIO) -> Gold (MinIO / PostgreSQL)`.
  - Consumo ultra-bajo de memoria (MinIO usa ~150 MB de RAM).
- **Negativas:**
  - Requiere configuración de credenciales S3 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`) en Airflow y PySpark.
