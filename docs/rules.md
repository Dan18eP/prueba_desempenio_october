# Reglas No Negociables del Proyecto - SismoWatch

## 1. Funcionalidad Real por Encima de la Estética desde el Minuto 0
- **Cero Datos Mockeados (No Mocks):**
  - Toda la información sísmica debe provenir de llamadas HTTP reales a los endpoints públicos del USGS (`all_hour.geojson` y endpoint de consultas históricas).
  - La persistencia en MinIO (Bronze/Silver/Gold) y PostgreSQL (`raw`, `staging`, `curated`, `audit`) debe ser 100% real.
  - La inferencia de IA debe ejecutarse de forma real en el modelo local Qwen 2.5 (1.5B) vía Ollama (con fallback determinístico únicamente como contingencia activa ante fallas de red/timeout, nunca como sustituto del modelo).
- **Cero Valores Hardcodeados (No Hardcoding):**
  - Todas las URLs, credenciales, puertos, nombres de buckets, claves secretas y parámetros de conexión deben inyectarse exclusivamente a través de variables de entorno (`.env`), Airflow Connections o configuración centralizada.
  - Prohibido dejar tokens JWT, contraseñas de base de datos o claves Fernet quemadas en el código fuente.

## 2. Orquestación Auténtica en Apache Airflow (Prohibido Scripts Sueltos de Python)
- **Airflow es el Orquestador Exclusivo:**
  - El flujo de datos no se ejecuta mediante un `main.py` suelto ni crons del sistema operativo.
  - Toda la ingesta periódica (cada 5 min), el disparo de la transformación de Spark hacia Silver/Gold, el backfill histórico y la generación diaria de reportes deben ser controlados, calendarizados y monitoreados por DAGs dentro del Scheduler de Airflow.
- **Estructura y Buenas Prácticas de DAGs:**
  - Implementación con TaskFlow API (`@dag`, `@task`) o tareas bien estructuradas con `TaskGroups`.
  - Disparo reactivo entre DAGs mediante Datasets/Assets de Airflow o `TriggerDagRunOperator`.
  - Documentación obligatoria `doc_md` y `tags` en cada DAG.
  - Cero lógica pesada en el archivo de definición del DAG: la lógica analítica, transformaciones y llamadas a APIs deben residir en paquetes modulares en `airflow/include/`.
  - Prohibido el paso de payloads de datos masivos a través de XCom (XCom solo maneja metadatos, conteos y estados de ejecución).

## 3. Calidad del Dato y Fidelidad Absoluta ("Me llegaron 20, mostré 20")
- **Preservación Total del Volumen:**
  - Si el feed de USGS entrega 20 eventos sísmicos, los 20 deben persistirse en Bronze, los 20 deben procesarse en Silver y los 20 deben ser contabilizados y expuestos en Gold.
  - Prohibido el descarte destructivo de registros o el envío a "limbos" donde los registros desaparezcan del balance general.
- **Auditoría No Destructiva de Cuarentena:**
  - Si un registro presenta advertencias de calidad (coordenadas atípicas, rangos no plausibles), se etiqueta con un flag de auditoría (`quality_flag: FLAGGED`, `rejection_reason`), pero continúa su trazabilidad en el pipeline.
  - El endpoint administrativo `GET /api/quality/quarantine` expone estos registros etiquetados para auditoría del Admin sin alterar el balance 20/20.

## 4. Resiliencia Operativa ("Zero Dumb Crashes")
- **Defensa con Try-Catch en Cada Tarea:**
  - Cada operador de Airflow y endpoint de la API debe estar blindado con bloques `try-except` para atrapar excepciones específicas y registrar logs contextuales estructurados.
- **Políticas de Red y Reintentos:**
  - Timeouts estrictos (máx. 15s) en peticiones a la API de USGS.
  - Reintentos automáticos con retroceso exponencial (`retries=3`, `retry_exponential_backoff=True`).
  - Límite de ejecuciones simultáneas: `max_active_runs = 1` en todos los DAGs.
  - Límite de tiempo de ejecución: `execution_timeout` en todas las tareas para evitar procesos zombi.
- **Idempotencia Estricta:**
  - Todo proceso de inserción hacia PostgreSQL debe utilizar `INSERT ... ON CONFLICT (id) DO UPDATE` para garantizar que re-ejecutar el mismo intervalo dos veces no genere duplicados ni errores de llave única.

## 5. Gobernanza y Linaje Puro
- Flujo continuo `USGS -> Bronze (MinIO) -> Silver (MinIO Parquet) -> Gold (PostgreSQL Curated)`.
- Sin capa landing intermedia ni carpetas temporales huérfanas.
- Compatibilidad con el estándar OpenLineage / OpenMetadata.

## 6. Seguridad y Mínimo Privilegio
- Autenticación obligatoria mediante JWT con expiración para acceder a cualquier dato.
- Control de Acceso Basado en Roles (RBAC): `viewer` vs `admin`.
- Endpoints administrativos (`/api/admin/*`, `/api/quality/quarantine`) estrictamente bloqueados para usuarios `viewer` con código HTTP 403 Forbidden.
- Mínimo privilegio en base de datos: la API solo posee permisos de solo lectura (`SELECT`) sobre el schema `curated`.
- Sanitización estricta de textos (`place`) antes de interactuar con el LLM para neutralizar inyecciones de instrucciones (OWASP LLM01).
