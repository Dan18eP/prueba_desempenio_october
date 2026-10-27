# Roadmap de Implementación y Checklist de Validación - SismoWatch

Este documento sirve como el tablero de control de avance técnico para garantizar que el 100% de los requisitos del PDF y los principios no negociables acordados se cumplan sin excepciones.

---

## Estado Global del Proyecto
- **Fecha de Inicio:** 27 de Octubre de 2026
- **Hora Límite de Entrega:** 13:59 (Penalización de 10 puntos después de la hora)
- **Meta:** Solución lista de punta a punta, probada y empaquetada con 1 hora de anticipación.

---

## 📌 Checklist de Fases

### Fase 1: Infraestructura Base & Modelo Relacional
- [x] Crear plantilla de entorno segura [`.env.example`](file:///home/Coder/Documentos/DanielE/PRUEBA_DESEMPENIO_OCTUBRE/.env.example) con Fernet Key, secrets JWT y configuración sin secretos quemados.
- [x] Crear [`docker-compose.yml`](file:///home/Coder/Documentos/DanielE/PRUEBA_DESEMPENIO_OCTUBRE/docker-compose.yml) unificado con límites de memoria (`mem_limit`):
  - [x] Servicio `postgres:16-alpine` (puerto `5435:5432`) con persistencia.
  - [x] Servicio `minio` (puertos `9000:9000` y `9001:9001`) para Lakehouse.
  - [x] Servicio `minio-init` para crear bucket `sismowatch-lake`.
  - [x] Servicios Airflow (`airflow-init`, `airflow-webserver` `:8080`, `airflow-scheduler`).
  - [x] Servicio `openmetadata-viewer` (puerto `8585:8585`) con API `/api/v1/lineage` y visualizador.
  - [x] Servicio `api` (FastAPI en `8000:8000`).
  - [x] Servicio `web` (React JS en `3000:3000`).
- [x] Crear `docker-compose.openmetadata.yml` (stack empresarial OpenSearch + Java Server opcional).
- [x] Crear `db/init/01_schemas_and_roles.sql`:
  - [x] Schemas: `raw`, `staging`, `curated`, `audit`.
  - [x] Roles: `sismo_ingest`, `sismo_transform`, `sismo_app_readonly` (mínimo privilegio).
- [x] Crear `db/init/02_tables_and_indexes.sql`:
  - [x] `curated.gold_earthquakes` con índices B-Tree en `event_time_utc`, `magnitude`, `place`.
  - [x] `curated.gold_hourly_kpis` y `curated.gold_anomalies`.
  - [x] `curated.gold_ai_reports` y `audit.quality_metrics`.
  - [x] `audit.batch_reconciliation` (fidelidad 20/20) y `audit.ai_executions`.
  - [x] `audit.users` y `audit.pipeline_alerts`.
- [x] Crear `db/init/03_seed_users.sql` con usuarios `admin` y `viewer` hasheados con bcrypt.

---

### Fase 2: Ingesta & Procesamiento Medallón (Airflow + PySpark)
- [ ] Crear `airflow/include/config.py` con parámetros de conexión hacia MinIO y PostgreSQL.
- [ ] Crear `airflow/include/callbacks.py` con `on_failure_callback` estructurado.
- [ ] Crear `airflow/include/quality.py` con validaciones de calidad (Pandera / PySpark):
  - [ ] Reglas de rango (latitud, longitud, profundidad, magnitud).
  - [ ] Control de frescura ($\le 120\text{ min}$) y volumen ($0 < N \le 500$).
  - [ ] Tagging de auditoría (`quality_flag: FLAGGED`) sin pérdida de datos.
- [ ] Crear `airflow/include/openmetadata_lineage.py` con emisión de esquemas y eventos OpenLineage.
- [ ] Crear `airflow/dags/dag_usgs_ingest.py`:
  - [ ] Periodicidad cada 5 min (`*/5 * * * *`).
  - [ ] Try-catch en cada tarea, reintentos exponenciales y timeout.
  - [ ] Ingesta a MinIO Bronze (`s3://sismowatch-lake/bronze/`).
  - [ ] Disparo automático de transformación vía `TriggerDagRunOperator`.
- [ ] Crear `airflow/dags/dag_pyspark_medallion.py`:
  - [ ] PySpark local (`local[*]`), sin clúster ocioso.
  - [ ] Bronze JSON $\to$ Silver Parquet Snappy (`s3://sismowatch-lake/silver/earthquakes/`).
  - [ ] Deduplicación por ventana temporal de última revisión (`updated DESC`).
  - [ ] Silver $\to$ Gold Parquet Snappy (`s3://sismowatch-lake/gold/`).
  - [ ] Sincronización idempotente a PostgreSQL Curated (`INSERT ... ON CONFLICT (id) DO UPDATE`).
  - [ ] Conciliación de balance 20/20 en `audit.batch_reconciliation`.
- [ ] Crear `airflow/dags/dag_historical_backfill.py`:
  - [ ] Parámetros interactivos en Airflow UI (`start_date`, `end_date`, `min_magnitude`).
  - [ ] Consulta histórica al endpoint de USGS sin duplicar registros existentes.

---

### Fase 3: Machine Learning de Anomalías & Reporte Diario con IA
- [ ] Crear `airflow/include/anomaly_detection.py`:
  - [ ] Algoritmo Z-Score sobre magnitudes y tasa de frecuencia horaria ($Z > 2.5$).
  - [ ] Detección de enjambres sísmicos con explicación breve y determinística.
- [ ] Crear `airflow/include/prompts/daily_summary_v1.txt` (prompt versionado con esquema Pydantic).
- [ ] Crear `airflow/dags/dag_daily_ai_report.py`:
  - [ ] Ejecución diaria programada.
  - [ ] Cifras calculadas previamente con SQL en `curated.gold_hourly_kpis` (Ground Truth).
  - [ ] Inferencia con Motor Dual de IA.
  - [ ] Aserción matemática de coincidencia entre números del texto y SQL.
  - [ ] Registro en `audit.ai_executions` y persistencia en `curated.gold_ai_reports`.

---

### Fase 4: Motor Dual de IA & Protocolo de Gráficos Declarativos
- [ ] Crear `api/services/llm_client.py`:
  - [ ] Conector dual: Ollama local (`qwen2.5-coder:3b` / `1.5b`) y Gemini 1.5 Flash opcional.
  - [ ] Fallback determinístico anti-caídas (<6s).
- [ ] Crear `api/services/chart_protocol.py`:
  - [ ] Generador de payloads declarativos JSON para Chart.js (`bar`, `line`, `doughnut`).
- [ ] Crear `api/services/security_guard.py`:
  - [ ] Función `sanitize_text_for_llm(place)` (mitigación OWASP LLM01).
  - [ ] Validador de consultas SQL para permitir estrictamente sentencias `SELECT`.

---

### Fase 5: Backend FastAPI & Plataforma React JS
- [ ] Backend FastAPI (`api/`):
  - [ ] `api/core/security.py`: Tokens JWT (HS256), hashing passwords con bcrypt, RBAC (`viewer` vs `admin`).
  - [ ] `api/routers/auth.py`: `POST /auth/login`.
  - [ ] `api/routers/kpis.py`: `GET /api/kpis`, `GET /api/stats/timeseries`.
  - [ ] `api/routers/events.py`: `GET /api/events` (paginación, filtros de severidad y región).
  - [ ] `api/routers/stream.py`: `GET /api/stream` (SSE en tiempo real con reconexión).
  - [ ] `api/routers/reports.py`: `GET /api/reports`, `GET /api/reports/export` (CSV y PDF/HTML).
  - [ ] `api/routers/admin.py`: `GET /api/quality/quarantine` (Admin), `POST /api/admin/backfill`.
  - [ ] `api/routers/chat.py`: `POST /api/chat` (Consultas en lenguaje natural + gráficos Chart.js).
  - [ ] `api/routers/governance.py`: `GET /api/governance/lineage` (API OpenMetadata).
- [ ] Plataforma Frontend React JS (`web/`):
  - [ ] Dark Mode táctico inspirado en diseño de centro de comando.
  - [ ] `Header.jsx`: Indicador SSE "EN VIVO", telemetría de servicios (MinIO/AF/PG/OM :8585), botón Backfill Admin.
  - [ ] `TsunamiBanner.jsx`: Alerta crítica ($M \ge 6.8 \land \text{prof} \le 100\text{km}$).
  - [ ] `KpiBar.jsx`: 5 tarjetas operativas (24h, Máx Mag, Tasa 20/20, Calidad Q, Anomalías).
  - [ ] `ControlCenterView.jsx`: Split view 7:5 (Gráficos Chart.js y mapa ligero Leaflet + Feed SSE en vivo).
  - [ ] `LineageView.jsx`: Grafo de linaje OpenMetadata y tabla de conciliación 20/20.
  - [ ] `AiAgentView.jsx`: Consola conversacional con gráficos Chart.js en tiempo real y visor de reportes diarios.
  - [ ] `GovernanceView.jsx`: Tabla de 7 reglas de calidad, visor de cuarentena (Admin) y estado de DAGs.
  - [ ] `LoginModal.jsx`: Login rápido con 1 clic para Admin / Viewer.
- [ ] Servicio OpenMetadata Viewer en `:8585`:
  - [ ] Servir catálogo interactivo de linaje y API `/api/v1/lineage`.

---

### Fase 6: Pruebas Automatizadas, Seguridad & Empaquetado Moodle
- [ ] Implementar suite de pruebas automatizadas con `pytest`:
  - [ ] `tests/test_transformations.py`: Prueba de función de transformación GeoJSON a Silver.
  - [ ] `tests/test_dag_integrity.py`: Todos los DAGs de Airflow se importan sin errores.
  - [ ] `tests/test_quality_rules.py`: Caso válido aprueba y caso anómalo genera flag.
  - [ ] `tests/test_api_endpoints.py`: Verificación de RBAC (401 sin token, 403 Viewer en Admin, 200 Admin).
  - [ ] Ejecutar `pytest -v tests/` y verificar 100% passed.
- [ ] Escaneo de seguridad estático:
  - [ ] Ejecutar `bandit -r api/ airflow/` y guardar en `docs/security_audit.txt`.
  - [ ] Ejecutar `pip-audit` y guardar reporte.
- [ ] Documentación Final:
  - [ ] `README.md` exhaustivo con guía de despliegue con 1 comando (`docker compose up -d`), diagrama, decisiones y evidencia del escaneo.
  - [ ] `documentation/tech-doc-f1.md` al completar cada fase.
- [ ] Empaquetado Final:
  - [ ] Generar archivo `.zip` del proyecto excluyendo `.git`, `__pycache__` y `.env`.
  - [ ] Verificación final de entrega para Moodle.
