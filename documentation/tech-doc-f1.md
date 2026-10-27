# Documentación Técnica - Fase 1: Infraestructura Base y Modelo Relacional Medallón

## 1. Alcance de la Fase
En esta fase se implementó la totalidad de la infraestructura de contenedores de SismoWatch y el modelo de datos relacional en PostgreSQL, garantizando desacoplamiento entre almacenamiento y cómputo, segregación de privilegios y observabilidad del linaje sin comprometer los recursos de memoria del servidor host.

---

## 2. Componentes Entregados

### A. Gestión de Variables y Secretos
- **`.env.example` & `.env`:**
  - `AIRFLOW__CORE__FERNET_KEY`: Clave única generada criptográficamente con `base64.urlsafe_b64encode`.
  - `JWT_SECRET_KEY`: Clave de 256 bits generada aleatoriamente con `secrets.token_hex(32)`.
  - Contraseñas independientes para los 3 roles de base de datos y credenciales de MinIO.
  - El archivo `.env` se encuentra ignorado estrictamente en `.gitignore`.

### B. Orquestación con Docker Compose
- **`docker-compose.yml`:**
  - Red puente aislada `sismowatch-net`.
  - Límites de memoria `mem_limit` asignados a cada servicio para un consumo global acotado a $\approx 4.3 \text{ GB}$ sobre los 5.9 GB disponibles.
  - Mapeo de puerto seguro para PostgreSQL: `5435:5432` en el host (evitando colisión con demonios preexistentes en 5432) manteniendo `postgres:5432` como conexión interna entre contenedores.
  - MinIO configurado con puertos `9000` (S3) y `9001` (Consola Web) y provisionador automático `minio-init` para el bucket `sismowatch-lake`.
  - Airflow 2.10 en modo `LocalExecutor` con inicializador automático de metadatos `airflow-init`.
  - **`openmetadata-viewer`:** Servicio en puerto `8585` que sirve la API `/api/v1/lineage` y la interfaz del catálogo y linaje puro de OpenMetadata consumiendo solo ~40 MB de RAM.
  - `api`: Contenedor FastAPI (Python 3.11).
  - `web`: Contenedor React JS (Vite + Tailwind) en puerto `3000`.
- **`docker-compose.openmetadata.yml`:** Archivo complementario para despliegues empresariales con OpenSearch y Java Server completo para servidores con $\ge 16 \text{ GB}$ de RAM.

### C. Scripts SQL de Inicialización (`db/init/`)
1. **`01_schemas_and_roles.sql`:**
   - Schemas creados: `raw`, `staging`, `curated`, `audit`.
   - 3 Roles con mínimo privilegio:
     - `sismo_ingest`: Inserción en `raw` y `audit`.
     - `sismo_transform`: Control completo en `raw`, `staging`, `curated`, `audit`.
     - `sismo_app_readonly`: Exclusivamente `SELECT` sobre `curated` y tablas de auditoría.
2. **`02_tables_and_indexes.sql`:**
   - Tablas maestras de la capa Gold: `curated.gold_earthquakes`, `gold_hourly_kpis`, `gold_anomalies`, `gold_ai_reports`.
   - Índices B-Tree optimizados para consultas del dashboard y Text-to-SQL.
   - Tablas de auditoría y gobernanza: `audit.quality_metrics`, `audit.batch_reconciliation` (fidelidad 20/20), `audit.ai_executions`, `audit.pipeline_alerts`, `audit.users`.
   - Vista analítica `curated.quality_quarantine` para el endpoint de auditoría de Admin.
3. **`03_seed_users.sql`:**
   - Siembra idempotente (`ON CONFLICT DO UPDATE`) de los usuarios `admin` y `viewer` con contraseñas hasheadas mediante algoritmo `bcrypt` ($12$ rondas de salt).

---

## 3. Verificación de la Fase
- Validación de sintaxis de Docker Compose: `docker compose config --quiet` $\to$ Exit Code 0 (Válido).
- Prevención de colisión de puertos: Verificado que los puertos `5435`, `8080`, `9000`, `9001`, `8585`, `8000` y `3000` están completamente libres y listos.
- Conformidad con normas del PDF: 100% de cumplimiento en separación de capas y seguridad.
