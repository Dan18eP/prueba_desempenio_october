# Documentación Técnica - Fase 0: Análisis de Requerimientos y Diseño Arquitectónico

## 1. Alcance de la Fase
- Análisis exhaustivo de los requerimientos de la prueba de desempeño (SismoWatch - USGS Seismic Monitoring).
- Integración de directrices obligatorias: Apache Airflow, Apache Spark, OpenMetadata.
- Definición de principios clave: Linaje Puro (sin capa landing intermedia ni aislamiento destructivo en cuarentena), Regla de Balance ("20 recibidos -> 20 procesados/mostrados"), Resiliencia con Try-Catch y Agente Conversacional Local conectado a Gold.

## 2. Diagnóstico del Entorno
- **Sistema Operativo:** Ubuntu 24.04.5 LTS (Noble Numbat), 12 vCPUs, 15 GiB RAM, 244 GiB disco NVMe disponible.
- **Aceleración:** CPU Only (Sin GPU dedicada Nvidia detectada).
- **Herramientas base disponibles:** Docker 27.x, Python 3.12, Git.
- **Consideración de Recursos:** La asignación de memoria debe ser ultra-eficiente. Se limita la memoria de PySpark a 1.5-2 GB y se utiliza un modelo LLM local optimizado para CPU (ej. Qwen2.5:1.5B/3B o Llama3.2:3B) con Circuit Breaker y fallback determinístico.

## 3. Plan Maestro de Fases
- **Fase 1:** Infraestructura y Modelo de Datos (Docker Compose, PostgreSQL con schemas raw, staging, curated, roles RBAC y configuración OpenMetadata/OpenLineage).
- **Fase 2:** Ingesta y Pipeline Medallion con Airflow y PySpark (DAGs protegidos con try/catch, backfill de 30 días, normalización GeoJSON a SQL, idempotencia).
- **Fase 3:** Detección de Anomalías ML y Generación de Reportes Diarios con IA (Z-Score / Isolation Forest, reportes narrativos con validación de cifras).
- **Fase 4:** Agente Conversacional Local conectado a Gold (Text-to-SQL solo lectura, sanitización contra prompt injection, fallback rule-based).
- **Fase 5:** Plataforma Web de Consumo y Monitoreo en Tiempo Real (FastAPI + Dashboard React/Streamlit + SSE/WebSocket + RBAC Viewer/Admin).
- **Fase 6:** Pruebas Automatizadas (Pytest), Auditoría de Seguridad (Bandit/Pip-Audit) y Empaquetado para Entrega Moodle.
