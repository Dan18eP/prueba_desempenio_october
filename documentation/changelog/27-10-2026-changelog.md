# Registro de Cambios - 27/10/2026

- [Martes]-[27/10/2026]-[06:38] : Inicialización del repositorio git local y creación de estructura base de documentación, changelog y análisis arquitectónico inicial.
- [Martes]-[27/10/2026]-[06:40] : Discusión arquitectónica sobre inclusión de MinIO, prevención de sobreingeniería y estrategia de Lakehouse Medallion con Spark y OpenMetadata.
- [Martes]-[27/10/2026]-[06:45] : Definición de estándares de almacenamiento, particionado e idempotencia para Lakehouse Medallion con MinIO y Qwen 2.5 local.
- [Martes]-[27/10/2026]-[06:50] : Creación y formalización de ADRs en docs/ADRs/, data_lineage.md, architecture.md y business_logic.md.
- [Martes]-[27/10/2026]-[06:53] : Definición de reglas de cero mocks y orquestación pura en rules.md, y auditoría forense completa del PDF del enunciado.
- [Martes]-[27/10/2026]-[06:55] : Formalización de arquitectura de autenticación JWT y control de acceso por roles (RBAC) en ADR 0006.
- [Martes]-[27/10/2026]-[07:00] : Creación de docs/requirements_compliance.md documentando los 7 requerimientos críticos del PDF y plan de acción de auditoría.
- [Martes]-[27/10/2026]-[07:02] : Creación y formalización de la especificación de diseño visual y de experiencia de usuario en docs/design.md y design.md.
- [Martes]-[27/10/2026]-[07:07] : Formalización de ADR 0007 sobre formatos de almacenamiento y Serving Layer, y depuración de documentos duplicados en el repositorio.
- [Martes]-[27/10/2026]-[07:14] : Formalización de ADR 0008 sobre el protocolo de gráficos declarativos y arquitectura anti-fallos en 3 capas para el agente conversacional.
- [Martes]-[27/10/2026]-[07:18] : Formalización de ADR 0009 sobre el Motor Dual de IA (Qwen 2.5-Coder / Gemini) y cumplimiento de controles de seguridad OWASP.
- [Martes]-[27/10/2026]-[07:22] : Reescritura histórica de autoría de commits a Daniel Echeverria y vinculación del repositorio remoto de GitHub.
- [Martes]-[27/10/2026]-[07:26] : Elaboración del plan maestro de implementación integral con roadmap de 6 fases y verificación de criterios de aceptación.
- [Martes]-[27/10/2026]-[07:31] : Actualización del plan maestro integrando Frontend en React JS y OpenMetadata en puerto :8585.
- [Martes]-[27/10/2026]-[07:33] : Creación y formalización de roadmap.md con checklist exhaustivo de las 6 fases de implementación y criterios de aceptación.
- [Martes]-[27/10/2026]-[07:43] : Culminación de Fase 1 (Infraestructura base, scripts SQL de base de datos con roles de mínimo privilegio, docker-compose.yml y documentación tech-doc-f1.md).
- [Martes]-[27/10/2026]-[07:48] : Culminación de Fase 2 (DAGs de ingesta, transformación Medallón con PySpark, backfill histórico, calidad de datos y tech-doc-f2.md).
- [Martes]-[27/10/2026]-[07:50] : Culminación de Fase 3 (ML de anomalías Z-Score, prompt versionado, DAG de reporte diario con IA y tech-doc-f3.md).
- [Martes]-[27/10/2026]-[07:54] : Culminación de Fase 4 (Motor Dual Text-to-SQL, protocolo de gráficos declarativos para Chart.js, Circuit Breaker y tech-doc-f4.md).
- [Martes]-[27/10/2026]-[08:05] : Culminación de Fase 5 (FastAPI routers con JWT RBAC, Server-Sent Events, frontend React.js con Vite, Chart.js, Leaflet, vistas de Centro de Control, Linaje, Agente IA y Gobernanza, y tech-doc-f5.md).
- [Martes]-[27/10/2026]-[08:16] : Culminación de Fase 6 (Suite de 22 pruebas automatizadas con pytest al 100% passed, escaneo estático Bandit con 0 vulnerabilidades altas, pip-audit, README.md maestro y tech-doc-f6.md).
- [Martes]-[27/10/2026]-[09:00] : Formalización de ADR 0010 (Selección del motor de procesamiento Medallón con Python Nativo y Pandera tras benchmarking empírico), y renombrado canónico de DAG a dag_medallion_processing.py.
- [Martes]-[27/10/2026]-[09:14] : Remediaciones quirúrgicas alineadas a la especificación oficial USGS FDSN: manejo de HTTP 204 No Content, pre-flight check con método /count en endpoint admin, recuperación automática CDC por updatedafter en downtime mayor a 60 min, actualización de ADR 0005 y nueva prueba unitaria pasando al 100% (23/23).
- [Martes]-[27/10/2026]-[09:16] : Configuración de requerimientos adicionales de Python (_PIP_ADDITIONAL_REQUIREMENTS) en docker-compose.yml para Airflow y alineación de airflow/requirements.txt con Pandas y Pandera.


















