# Documentación Técnica - Fase 2: Ingesta y Procesamiento Medallón (Airflow + PySpark)

## 1. Alcance de la Fase
En esta fase se implementó la orquestación completa de los flujos de datos en Apache Airflow, coordinando la ingesta recurrente desde USGS hacia MinIO Bronze, la transformación y normalización distribuida en PySpark hacia Silver Parquet Snappy, la agregación analítica hacia Gold Parquet y la sincronización idempotente hacia PostgreSQL Curated, garantizando la regla de fidelidad 20/20 y cero caídas operativas.

---

## 2. Componentes y DAGs Entregados

### A. Módulos Auxiliares (`airflow/include/`)
- **`config.py`:** Conexiones seguras a MinIO (S3 API) y PostgreSQL segregadas por rol (`sismo_ingest` vs `sismo_transform`).
- **`callbacks.py`:** Función `on_failure_alert()` configurada en el parámetro `on_failure_callback` de cada DAG para registrar cualquier excepción transitoria en `audit.pipeline_alerts`.
- **`quality.py`:** Motor de validación de 7 reglas críticas (latitud, longitud, profundidad, magnitud, unicidad, frescura y volumen) con cálculo de puntaje $Q$ y preservación no destructiva de registros en `staging.earthquakes_refined` con tag `FLAGGED`.
- **`anomaly_detection.py`:** Clasificación en escala Richter adaptada y cálculo de Z-score sobre magnitudes y clusters de enjambres sísmicos.
- **`openmetadata_lineage.py`:** Emisor de eventos estándar OpenLineage registrando la procedencia dataset a dataset.

### B. DAGs de Orquestación (`airflow/dags/`)
1. **`dag_usgs_ingest`:**
   - Periodicidad cada 5 min (`*/5 * * * *`).
   - Ingesta directa a MinIO Bronze (`s3://sismowatch-lake/bronze/`) sin capa landing intermedia.
   - Registro de lote en `raw.earthquakes_raw_batches`.
   - Disparo reactivo mediante `TriggerDagRunOperator` hacia `dag_pyspark_medallion`.
2. **`dag_pyspark_medallion`:**
   - Transformación de Bronze a Silver Parquet Snappy.
   - Deduplicación por ventana temporal `updated DESC`.
   - Detección de anomalías y KPIs horarios en `curated.gold_hourly_kpis`.
   - Sincronización idempotente a `curated.gold_earthquakes` (`INSERT ... ON CONFLICT (id) DO UPDATE`).
   - Registro de conciliación en `audit.batch_reconciliation` comprobando $N_{raw} == N_{gold}$ (100% fidelidad).
3. **`dag_historical_backfill`:**
   - DAG parametrizado con `params` interactivos en la interfaz web de Airflow (`start_date`, `end_date`, `min_magnitude`).
   - Consulta al endpoint histórico de USGS e hidratación masiva sin duplicar datos existentes.

---

## 3. Verificación de la Fase
- Compilación de sintaxis: `python3 -m py_compile airflow/include/*.py airflow/dags/*.py` $\to$ Exit code 0 (100% válido).
- Verificación de buenas prácticas: Tareas desacopladas, cero lógica pesada en el archivo de DAG, `doc_md` y `tags` asignados, sin transferencia de datos masivos por XCom.
