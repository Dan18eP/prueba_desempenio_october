# Documentación Técnica - Fase 6: Pruebas Automatizadas, Auditoría de Seguridad & Empaquetado

## 1. Alcance de la Fase
En esta fase final se implementó la suite completa de pruebas automatizadas con `pytest`, se ejecutaron las auditorías de seguridad estática con `bandit` y de dependencias con `pip-audit`, se consolidó el `README.md` exhaustivo y se preparó el archivo empaquetado para la entrega oficial.

---

## 2. Componentes Entregados

### A. Suite de Pruebas Automatizadas (`tests/`)
- `tests/conftest.py`: Fixtures de FastAPI TestClient, generación de tokens JWT firmados para roles `admin` y `viewer`, y payload simulado de 20 eventos GeoJSON.
- `tests/test_transformations.py`:
  - Clasificación de severidad Richter (Micro, Menor, Moderado, Fuerte, Mayor).
  - Matriz de riesgo de tsunami ($M \ge 6.8 \land \text{prof} \le 100\text{ km}$).
  - Verificación matemática de la invariante: 20 features de entrada producen exactamente 20 registros procesados en Silver (100% fidelidad, 0 pérdidas).
- `tests/test_dag_integrity.py`:
  - Existencia y análisis sintáctico por AST de los 4 DAGs de Airflow (`dag_usgs_ingest`, `dag_pyspark_medallion`, `dag_daily_ai_report`, `dag_historical_backfill`).
  - Validación de periodicidades y nombres canónicos de tareas.
- `tests/test_quality_rules.py`:
  - Evaluación de las 7 reglas de calidad de datos Pandera (rango de magnitud, profundidad, coordenadas geográficas, frescura máxima de 120 min, etc.).
  - Verificación de la cuarentena no destructiva: los registros anómalos se marcan como `FLAGGED` pero no se descartan silenciosamente.
- `tests/test_api_endpoints.py`:
  - Pruebas de salud (`/health` y `/`).
  - Verificación estricta de seguridad RBAC: peticiones sin token devuelven HTTP 401 Unauthorized; peticiones de rol `viewer` hacia endpoints administrativos (`/api/quality/quarantine`, `/api/admin/backfill`, etc.) devuelven HTTP 403 Forbidden.
  - Validación de blindajes OWASP: interceptación de prompt injection (LLM01) y bloqueo de comandos destructivos/mutacionales o fuera del esquema `curated` (LLM06).
  - Validación de la estructura del protocolo declarativo de gráficos para Chart.js.

### B. Auditoría de Seguridad Estática (`bandit`)
- Ejecutado sobre el código fuente de backend y pipelines:
  `.venv/bin/bandit -r api/ airflow/ -f txt -o docs/security_audit.txt`
- **Resultados de Severidad:**
  - **Vulnerabilidades de Severidad Alta (High): 0**
  - **Vulnerabilidades Indefinidas: 0**
  - Líneas de código escaneadas: 2,725 líneas.
  - Observaciones menores (Low) debidamente analizadas y mitigadas mediante configuración de entornos.

### C. Auditoría de Dependencias (`pip-audit`)
- Ejecutado sobre el árbol de librerías del proyecto y guardado en `docs/dependency_audit.txt`.
- Análisis de la observación de `python-jose`: mitigada a nivel de código forzando la lista estricta `algorithms=[settings.JWT_ALGORITHM]` en `api/core/security.py`, eliminando cualquier ambigüedad en la inicialización de claves HMAC.

### D. Manual Maestro del Proyecto (`README.md`)
- Guía de inicio rápido con 1 comando (`docker compose up -d`).
- Diagrama de arquitectura de datos y componentes (Mermaid).
- Matriz completa de puertos y credenciales de acceso para la mesa evaluadora.
- Explicación de la garantía de fidelidad "Me llegaron 20, mostré 20" y las 7 reglas Pandera.
- Instrucciones para la ejecución de pruebas unitarias.

---

## 3. Verificación de la Fase
- Ejecución de pruebas: `.venv/bin/pytest -v tests/` $\to$ **22 passed in 0.05s (100% Passed)**.
- Compilación de Frontend: `npm --prefix web run build` $\to$ 1580 módulos transformados, 0 errores.
- Empaquetado final: Creación de archivo `.zip` limpio y verificable.
