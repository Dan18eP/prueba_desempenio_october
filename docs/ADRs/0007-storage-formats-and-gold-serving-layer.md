# ADR 0007: Estrategia de Formatos de Almacenamiento (JSON vs Parquet) y Proyección de Gold al Serving Layer

## Estado
Aprobado

## Contexto
Durante el refinamiento de la arquitectura Lakehouse Medallón surgieron dos interrogantes técnicas clave:
1. ¿Es un desperdicio o redundancia almacenar en formato Parquet en las capas Silver y Gold si el dato original de USGS proviene en formato JSON?
2. ¿Debe persistirse la capa Gold en MinIO también, o almacenarla directamente en PostgreSQL es suficiente sin incurrir en redundancia o desvío de los principios de un Medallón Puro?

## Decisión

### 1. Justificación de Formatos por Capa (JSON en Bronze vs. Parquet en Silver/Gold)
- **Capa Bronze (`raw`):** Se mantiene estrictamente en **formato JSON crudo**.
  - *Motivo:* Bronze debe ser inmutable y preservar la fidelidad exacta del feed emitido por la API de USGS. No se aplican transformaciones ni tipados forzados en este punto (schema-on-read).
- **Capa Silver (`staging`):** Se almacena obligatoriamente en **formato Parquet con compresión Snappy**.
  - *No es desperdicio:* El JSON es un formato de texto plano anidado y verboso. Parquet aporta:
    1. **Tipado Estricto:** Convierte arrays genéricos como `coordinates[0,1,2]` en columnas numéricas tipadas (`DOUBLE`, `TIMESTAMP`, `BOOLEAN`).
    2. **Compresión:** Reduce el tamaño en almacenamiento entre un 75% y 85% gracias a compresión Snappy y codificación por diccionario.
    3. **Projection Pushdown:** Permite a PySpark y motores analíticos leer únicamente las columnas requeridas (ej. solo `magnitude` y `event_time_utc`), omitiendo el escaneo de texto del archivo completo.

### 2. Capa Gold en MinIO y Proyección Idempotente a PostgreSQL (Serving Layer)
Para cumplir con la definición rigurosa de un **Lakehouse Medallón Puro** sin sacrificar rendimiento web:
- **Gold en MinIO (`s3://sismowatch-lake/gold/`):**
  - PySpark persiste las tablas analíticas agregadas (`gold_earthquakes`, `gold_hourly_kpis`, `gold_anomalies`) en formato Parquet en MinIO.
  - Esto garantiza que el Data Lakehouse sea **100% autónomo y recuperable ante desastres**: si PostgreSQL se reinicia, corrompe o borra, todo el histórico empresarial reside intacto en el Object Storage.
- **PostgreSQL (`curated`):**
  - Actúa como el **Serving Layer / Reverse ETL / Data Mart** de baja latencia.
  - La sincronización se realiza mediante inserciones idempotentes (`INSERT ... ON CONFLICT (id) DO UPDATE`).
  - FastAPI y el Agente Conversacional (Qwen 2.5) consultan PostgreSQL con índices B-Tree, obteniendo tiempos de respuesta sub-15ms, evitando el costo de latencia de escanear archivos Parquet sobre S3 en cada petición web.

## Consecuencias
- **Positivas:**
  - Arquitectura Medallón pura de extremo a extremo en MinIO (Bronze JSON $\to$ Silver Parquet $\to$ Gold Parquet).
  - Serving Layer en PostgreSQL optimizado para alta concurrencia y consultas instantáneas del frontend y LLM.
  - Resiliencia y capacidad de disaster recovery total desde el almacenamiento de objetos.
- **Negativas:**
  - Requiere mantener sincronizada la proyección entre MinIO Gold y PostgreSQL Curated durante el job de Spark (resuelto mediante 2 instrucciones de PySpark en el mismo DAG).
