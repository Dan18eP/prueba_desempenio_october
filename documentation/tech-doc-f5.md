# Documentación Técnica - Fase 5: API Serving Layer & Frontend Táctico React.js

## 1. Alcance de la Fase
En esta fase se construyeron e integraron la capa de servicios backend RESTful en FastAPI y la plataforma frontend táctica desarrollada en React.js (Vite + Tailwind CSS + Chart.js + Leaflet). Se garantizó la autenticación JWT con control de acceso basado en roles (RBAC), el canal de eventos Server-Sent Events (SSE) para ingesta en tiempo real, la consola analítica del agente IA y las vistas de linaje y gobernanza.

---

## 2. Componentes Entregados

### A. Capa de Seguridad y Autenticación RBAC (`api/core/security.py`, `api/routers/auth.py`)
- **Firma y Validación JWT:** Algoritmo `HS256`, tiempo de expiración configurable de 60 minutos.
- **Doble Extracción de Token:** Soporta tanto cabecera `Authorization: Bearer <token>` como parámetro de consulta `?token=<token>` (indispensable para la conexión nativa de `EventSource` en navegadores).
- **Protección RBAC:** Inyección de dependencia `require_admin` que bloquea a usuarios con rol `viewer` devolviendo estricto código HTTP 403 Forbidden en endpoints administrativos.
- **Hashing de Contraseñas:** Algoritmo bcrypt con salt rounds seguro contra ataques de fuerza bruta.

### B. Endpoints de la API Backend (`api/routers/`)
- `POST /auth/login` y `GET /auth/me`: Autenticación y perfil de usuario.
- `GET /api/kpis`: Telemetría operativa 24h, conteo de sismos, magnitud pico, alertas de tsunami activas, anomalías y tasa de fidelidad (20 in $\to$ 20 out).
- `GET /api/stats/timeseries` y `GET /api/stats/severity`: Agregaciones para los gráficos de Chart.js.
- `GET /api/events` y `GET /api/events/{id}`: Paginación, filtrado por magnitud, severidad y búsqueda geoespacial.
- `GET /api/stream`: Canal Server-Sent Events (SSE) con eventos `initial_batch`, `earthquake_update` y latidos `keepalive`.
- `GET /api/reports/latest`, `/history` y `/export`: Consulta y exportación en CSV, JSON y HTML para impresión/PDF.
- `GET /api/quality/quarantine`: Vista de auditoría de cuarentena protegida por rol `admin` (403 para `viewer`).
- `POST /api/admin/backfill` y `POST /api/admin/reports/regenerate`: Disparadores de tareas protegidos por rol `admin`.
- `POST /api/chat`: Consulta interactiva Text-to-SQL protegida con sanitización OWASP LLM01 y motor dual.
- `GET /api/governance/lineage` y `/quality-rules`: Grafo de linaje OpenMetadata y evaluación de las 7 reglas Pandera.

### C. Plataforma Frontend React.js (`web/src/`)
- **Arquitectura de Vistas Tácticas:**
  - `ControlCenterView.jsx`: Mapa táctico geoespacial Leaflet sin dependencias de tokens comerciales con marcadores codificados por magnitud y pulso en tsunamis. Gráficos Chart.js de actividad horaria y severidad. Panel de telemetría SSE en vivo con pausa/reanudación y filtrado rápido.
  - `LineageView.jsx`: Flujo visual de nodos del Lakehouse Medallion (Source $\to$ Bronze $\to$ Silver $\to$ Gold $\to$ Serving $\to$ AI) y tabla de conciliación de lotes demostrando la invariante de cero pérdida.
  - `AiAgentView.jsx`: Consola de chat con el agente IA, soporte para sugerencias rápidas, renderizado de consultas SQL de solo lectura y visualización declarativa dinámica con Chart.js. Sección del reporte ejecutivo con exportación en un clic (CSV / HTML).
  - `GovernanceView.jsx`: Matriz de las 7 reglas de calidad Pandera con sus estados, y vista de auditoría de cuarentena no destructiva con control RBAC visible en pantalla.
- **Componentes Transversales:**
  - `Header.jsx`: Barra superior con estado de conexión SSE en vivo, pestañas, acceso rápido a OpenMetadata (:8585) y perfil de usuario con control de sesión.
  - `TsunamiBanner.jsx`: Banner de alerta crítica activado ante la condición matriz de tsunami ($M \ge 6.8 \land \text{prof} \le 100\text{ km}$).
  - `KpiBar.jsx`: 5 tarjetas de telemetría de misión crítica, destacando el 100% de fidelidad de datos.
  - `LoginModal.jsx`: Modal de autenticación con botones de prueba de 1 clic para perfiles `admin` y `viewer`.

---

## 3. Verificación de la Fase
- Compilación de Python Backend: `python3 -m py_compile api/main.py api/routers/*.py api/services/*.py api/core/*.py` $\to$ Exit code 0.
- Compilación de Frontend Vite: `npm --prefix web run build` $\to$ Exit code 0 (1580 módulos transformados, bundle generado en `web/dist/`).
- Verificación RBAC: Comprobado aislamiento de permisos para usuarios `viewer` y `admin`.
