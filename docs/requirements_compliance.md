# Matriz de Cumplimiento Normativo y Hallazgos de Auditoría (Requirements Compliance)

Este documento detalla los 7 hallazgos técnicos y operativos identificados tras la auditoría exhaustiva del enunciado oficial de la prueba de desempeño de SuperApp (**SismoWatch**), garantizando que ningún criterio de evaluación sea omitido.

---

## 1. Mapeo de Hallazgos y Acciones de Implementación

| # | Requisito del PDF | Referencia PDF | Acción Técnica Obligatoria | Estado de Diseño |
| :-: | :--- | :--- | :--- | :-: |
| **1** | **Mínimo Privilegio en Base de Datos:** Roles independientes para ingesta, transformación y lectura. | Página 5 | Crear roles PostgreSQL reales (`sismo_ingest`, `sismo_transform`, `sismo_app_readonly`). La API solo tiene permiso `SELECT` sobre `curated`. | Documentado en ADR 0001, ADR 0006 y `db/init/` |
| **2** | **DAG de Backfill Histórico Parametrizado:** Carga de los últimos 30 días sin duplicados. | Páginas 4 y 7 | Configurar `dag_historical_backfill` con `params` en Airflow UI (`start_date`, `end_date`, `min_magnitude`) y exponer endpoint `POST /api/admin/backfill`. | Documentado en ADR 0005 y `business_logic.md` |
| **3** | **Buenas Prácticas Estrictas de Airflow:** Sin lógica pesada en DAGs, sin datos en XCom, `doc_md` y `tags`. | Página 4 | Código desacoplado en `airflow/include/`, uso de TaskFlow API, documentación Markdown en cada DAG y paso exclusivo de metadatos en XCom. | Documentado en ADR 0005 y `rules.md` |
| **4** | **Gatillado Reactivo entre DAGs:** Disparo automático al terminar ingesta. | Página 4 | Uso de `Dataset` de Airflow (`minio://sismowatch-lake/bronze/feed`) o `TriggerDagRunOperator`. No usar crons desincronizados. | Documentado en `data_lineage.md` y `architecture.md` |
| **5** | **Mitigación de Prompt Injection (OWASP LLM01):** Sanitización de textos no confiables antes de enviarlos al LLM. | Página 5 | Implementación del módulo `sanitize_text_for_llm(place)` con regex para neutralizar inyecciones en el campo `place` de USGS. | Documentado en ADR 0004 y `business_logic.md` |
| **6** | **Controles de Frescura y Volumen:** Reglas de latencia máxima y rango de eventos esperados. | Página 5 | Reglas en PySpark/Pandera que alerten si la frescura supera 120 min o si el volumen por hora es 0 o excede el umbral de avalancha. | Documentado en `business_logic.md` y `data_lineage.md` |
| **7** | **Evidencia de Escaneo de Seguridad:** Escaneo documentado en README. | Páginas 3 y 7 | Ejecución de `bandit -r api/ airflow/` y `pip-audit`, exportando los resultados a `docs/security_audit.txt` e insertando la evidencia en `README.md`. | Documentado en ADR 0006 y `rules.md` |

---

## 2. Detalle de los 7 Requerimientos Críticos

### Requisito 1: Roles de Mínimo Privilegio en PostgreSQL
Para que la solución sea empresarialmente rigurosa y cumpla el criterio de seguridad de la página 5, el script `db/init/01_schemas_and_roles.sql` debe definir:
```sql
-- 1. Rol de Ingesta (solo metadatos de control)
CREATE ROLE sismo_ingest WITH LOGIN PASSWORD 'ingest_secret_pass';
GRANT USAGE ON SCHEMA raw, audit TO sismo_ingest;
GRANT INSERT, SELECT, UPDATE ON ALL TABLES IN SCHEMA raw, audit TO sismo_ingest;

-- 2. Rol de Transformación (PySpark/Airflow)
CREATE ROLE sismo_transform WITH LOGIN PASSWORD 'transform_secret_pass';
GRANT USAGE ON SCHEMA raw, staging, curated, audit TO sismo_transform;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw, staging, curated, audit TO sismo_transform;

-- 3. Rol de Consumo (FastAPI Backend)
CREATE ROLE sismo_app_readonly WITH LOGIN PASSWORD 'readonly_secret_pass';
GRANT USAGE ON SCHEMA curated, audit TO sismo_app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA curated TO sismo_app_readonly;
GRANT SELECT ON TABLE audit.quality_metrics, audit.pipeline_alerts TO sismo_app_readonly;
```

### Requisito 2: DAG de Backfill Parametrizado
El DAG `dag_historical_backfill` permite rehidratar el lago de datos sin duplicar registros:
* **Parámetros configurables en UI:**
  * `start_date`: Fecha de inicio (por defecto `{{ macros.ds_add(ds, -30) }}`).
  * `end_date`: Fecha de fin (por defecto `{{ ds }}`).
  * `min_magnitude`: Umbral mínimo de magnitud (por defecto `2.5`).
* **Endpoint de Disparo:**
  `POST /api/admin/backfill` (protegido por JWT, rol `admin`), que utiliza el cliente REST de Airflow (`/api/v1/dags/dag_historical_backfill/dagRuns`) para disparar la ejecución.

### Requisito 3: Estándar de Código en DAGs
* **Documentación Embebida:** Cada DAG contiene:
  ```python
  dag.doc_md = """
  ### Propósito del DAG
  Ingesta periódica cada 5 minutos del feed oficial de USGS GeoJSON hacia MinIO Bronze.
  ### Políticas de Resiliencia
  - Reintentos: 3 con backoff exponencial.
  - Timeout: 5 minutos.
  - Idempotencia: Escribe claves determinísticas en MinIO.
  """
  ```
* **Tags para Filtrado:** `tags=['ingesta', 'usgs', 'tiempo-real', 'minio']`.
* **Zero Heavy Logic:** Los archivos `dags/*.py` solo instancian operadores. Las funciones Python residen en `airflow/include/`.

### Requisito 4: Gatillado por Eventos (Data-Driven Orchestration)
El DAG de transformación hacia Silver y Gold no usa un schedule ciego; se define mediante:
```python
@dag(
    schedule=[Dataset("minio://sismowatch-lake/bronze/earthquakes")],
    ...
)
def dag_pyspark_medallion():
    ...
```
O mediante `TriggerDagRunOperator(task_id="trigger_medallion", trigger_dag_id="dag_pyspark_medallion")`.

### Requisito 5: Sanitización contra Prompt Injection (OWASP LLM01)
El campo `place` recibido de la API pública de USGS se procesa antes de ser inyectado en el prompt de Qwen 2.5:
```python
import re

def sanitize_text_for_llm(text: str) -> str:
    if not text:
        return "Ubicación no especificada"
    # Eliminar saltos de línea y retornos de carro
    clean = re.sub(r'[\r\n\t]+', ' ', text)
    # Neutralizar caracteres de escape o delimitadores de prompt
    clean = re.sub(r'[`"\'\\<>{}[\]]', '', clean)
    # Limitar longitud máxima razonable
    return clean.strip()[:120]
```

### Requisito 6: Controles de Calidad de Frescura y Volumen
En `airflow/include/quality.py`, se evalúan:
* **Freshness Check:** $\text{MAX}(event\_time\_utc) \ge \text{NOW}() - \text{INTERVAL '120 MIN'}$. Si no se cumple, se genera un flag `WARNING: Stale Data Feed`.
* **Volume Anomaly Check:** $N_{batch} > 0$ y $N_{batch} \le 500$. Si $N_{batch} == 0$, flag `ERROR: Empty Batch Feed`. Si $N_{batch} > 500$, flag `WARNING: Abnormal Spike Volume`.

### Requisito 7: Auditoría y Escaneo de Seguridad Automatizado
Se ejecuta el escaneo estático de vulnerabilidades:
1. `bandit -r api/ airflow/ -f txt -o docs/security_audit.txt` (Detección de inyecciones SQL, uso de secrets quemados, funciones inseguras).
2. `pip-audit -r api/requirements.txt` (Auditoría de vulnerabilidades conocidas CVEs en librerías).
3. La evidencia textual limpia se incrusta en una sección dedicada del `README.md`.
