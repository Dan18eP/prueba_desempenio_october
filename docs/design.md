# Especificación de Diseño y Experiencia de Usuario (Design System & UI Spec) - SismoWatch

## 1. Filosofía Visual y Principios de Diseño
**SismoWatch** está concebido como un **Centro de Mando Táctico de Inteligencia Sísmica** (*Operational Seismic Intelligence*). Su diseño prioriza la legibilidad inmediata de eventos críticos, el contraste operativo para salas de control y la resiliencia absoluta contra fallos de renderizado.

### Principios Fundamentales:
1. **Funcionalidad y Confiabilidad por Encima de Complejidad Riesgosa:**
   - Se elimina la dependencia de motores pesados de mapas con WebGL propietario, capas vectoriales complejas o APIs de mapas externas que requieran tokens de terceros o puedan fallar por conectividad.
   - En su lugar, se implementa una **solución geoanalítica robusta**: un visor geoespacial ligero (basado en Leaflet nativo con fallback automático) combinado con gráficos analíticos de alto impacto (series temporales y distribución de magnitud).
2. **Claridad Operativa Inmediata:**
   - Semáforo de severidad sismológica unificado en toda la interfaz (Micro $\to$ Verde, Menor $\to$ Azul, Moderado $\to$ Amarillo, Fuerte $\to$ Naranja, Mayor/Crítico $\to$ Rojo).
3. **Cero Pantallas en Blanco (Zero Blank States):**
   - Cada tarjeta, gráfico y lista implementa formalmente los 3 estados: `LoadingState` (skeletons animados), `EmptyState` (icono y mensaje descriptivo de ausencia de datos) y `ErrorState` (banner con botón de reintento).
4. **Fidelidad y Gobernanza Visible:**
   - El usuario ve en todo momento la tasa de fidelidad ("20 de 20 eventos reflejados"), el estado de salud de los servicios (MinIO, Airflow, Postgres, Ollama) y el indicador "En Vivo" del stream SSE.

---

## 2. Sistema de Diseño (Design Tokens)

### Paleta de Colores Táctica (Dark Theme):
- **Superficies y Fondos:**
  - `background-lowest`: `#0a0e16` (Fondo general ultra-oscuro de bajo consumo visual)
  - `surface-container-low`: `#181c24` (Contenedores de tarjetas y paneles)
  - `surface-container`: `#1c2028` (Superficies estándar de elementos interactivos)
  - `surface-container-high`: `#262a33` (Barras de encabezado y badges)
- **Texto y Contrastes:**
  - `on-surface`: `#dfe2ee` (Texto primario de alto contraste)
  - `on-surface-variant`: `#c2c6d6` (Texto secundario y etiquetas)
  - `outline`: `#8c909f` (Líneas divisorias sutiles y metadatos)
- **Escala Cromática de Severidad Sísmica:**
  - **Micro ($< 2.5$):** Secundario Verde `#4edea3` (Sin alerta)
  - **Menor ($2.5 - 4.4$):** Primario Azul `#adc6ff` (Informativo)
  - **Moderado ($4.5 - 5.9$):** Terciario Naranja/Amarillo `#ffb690` / `#ec6a06` (Precaución)
  - **Fuerte ($6.0 - 6.9$):** Contenedor Naranja Intenso `#f97316` (Alerta media)
  - **Mayor ($\ge 7.0$):** Error/Crítico Rojo `#ffb4ab` con fondo `#93000a` (Emergencia crítica / Tsunami)

### Tipografía:
- **Textos de Interfaz y Encabezados:** `Inter`, sans-serif (pesos 400, 500, 600, 700).
- **Telemetría, Cifras Numéricas y Código:** `JetBrains Mono`, monospace (pesos 500, 600, 700) para coordenadas, tiempos UTC, magnitudes y KPIs.

---

## 3. Estructura y Navegación de la Plataforma (4 Vistas)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HEADER FIJO DE COMANDO                          │
│ [Logo] SismoWatch v2.4-prod | [●] SSE EN VIVO | MinIO/AF/PG | [User]   │
├────────────────────────────────────────────────────────────────────────┤
│ [ Centro de Control ]  [ Linaje de Datos ]  [ Agente IA ]  [ Auditoría]│
└────────────────────────────────────────────────────────────────────────┘
```

### Vista 1: Centro de Control (Command Center)
1. **Banner Dinámico de Alerta de Tsunami (Prioridad Nivel 1):**
   - Solo se despliega si existe un sismo con `tsunami_alert = true` o $M \ge 6.8$ con profundidad $\le 100\text{ km}$.
   - Muestra epicentro, magnitud, profundidad hipocentral y protocolo de evacuación.
2. **Barra de KPIs Operativos (5 Tarjetas):**
   - **Eventos 24h:** Total de sismos registrados en la última jornada.
   - **Magnitud Máxima:** Sismo más energético registrado con región y profundidad.
   - **Tasa de Fidelidad:** "100.0% Zero-Loss: 20 de 20 eventos reflejados".
   - **Calidad de Datos $Q$:** Porcentaje de cumplimiento de reglas Pandera (ej. $99.4\%$).
   - **Anomalías Sísmicas:** Número de enjambres o sismos con $Z\text{-Score} > 2.5$.
3. **Split View Táctico (Distribución 7:5):**
   - **Columna Izquierda (7 cols) - Análisis Geoespacial & Gráficos:**
     - *Visor de Distribución Geográfica:* Mapa interactivo ultraligero Leaflet (EPSG:4326 con pines por magnitud y radio proporcional) con alternativa visual por cuadrantes sísmicos.
     - *Gráfico de Serie Temporal:* Frecuencia horaria de eventos en las últimas 24h.
     - *Gráfico de Distribución por Magnitud:* Conteo por categorías (Micro, Menor, Moderado, Fuerte, Mayor).
     - *Filtros de Control:* Magnitud mínima ($M \ge 2.5$, $M \ge 4.5$, etc.), región y rango temporal.
   - **Columna Derecha (5 cols) - Live Feed de Ingesta (SSE Streaming):**
     - Conexión persistente a `/api/stream`.
     - Lista reactiva de sismos entrantes: magnitud en badge cromático, región, profundidad, coordenadas y timestamp UTC.
     - Botones de inspección rápida: ver registro Silver vs. ver registro Gold.
     - Botón de control: Pausar/Reanudar stream.

---

### Vista 2: Linaje de Datos & Gobernanza (OpenMetadata Spec)
1. **Grafo de Linaje Puro:**
   - Visualización esquemática del flujo de extremo a extremo:
     $$\text{USGS API} \longrightarrow \text{MinIO Bronze (JSON)} \longrightarrow \text{MinIO Silver (Parquet)} \longrightarrow \text{PostgreSQL Curated (Gold)}$$
2. **Tabla de Conciliación de Lotes (Batch Reconciliation):**
   - Columnas: `Batch ID`, `Timestamp Ingesta`, `Eventos Crudos Recibidos (Raw)`, `Eventos Procesados Silver`, `Eventos Sincronizados Gold`, `Tasa de Pérdida (0.0%)`.
3. **Catálogo de Metadatos:**
   - Diccionario de datos de cada tabla con tipos, descripciones, restricciones y reglas de calidad asociadas.

---

### Vista 3: Agente IA & Reportes (Qwen 2.5 Local)
1. **Consola Conversacional del Agente Sísmico:**
   - Interfaz de chat moderna para interactuar directamente con la capa Gold.
   - Consultas en lenguaje natural soportadas:
     - *"¿Cuál fue el sismo de mayor magnitud en las últimas 24 horas?"*
     - *"Muestra los sismos ocurridos en México con magnitud mayor a 4.0"*
     - *"¿Hay alguna alerta de tsunami activa en este momento?"*
   - Indicador de estado del modelo: `Qwen 2.5 (1.5B) Local CPU • Latencia ~1.2s • Conexión Gold (Read-Only)`.
   - Mecanismo visual de Fallback: Si el modelo se satura, un badge discreto indica *"Respuesta generada mediante Motor Analítico Determinístico"*.
2. **Visor del Reporte Ejecutivo Diario:**
   - Resumen ejecutivo diario en lenguaje natural con métricas verificadas.
   - Comparativa de cifras: verificación de que los números del texto coinciden con los calculados por SQL.
   - Barra de acciones: **Exportar CSV**, **Exportar PDF / HTML descargable** y botón **Regenerar con IA** (restringido a Admin).

---

### Vista 4: Gobernanza, Calidad & Administración (Admin View)
1. **Panel de Control de Calidad de Datos:**
   - Métricas detalladas de las 7 reglas evaluadas por PySpark / Pandera.
   - Puntuación general $Q$ y desglose de reglas aprobadas vs. rechazadas.
2. **Visor de Cuarentena de Auditoría (Exclusivo Admin):**
   - Lista de eventos que generaron advertencias de calidad (ej. profundidad atípica o coordenadas en el límite).
   - Motivo del flag (`rejection_reason`) y fecha de detección.
   - Confirmación de no-descarte: estos sismos siguen contabilizados en el balance general.
3. **Operaciones Administrativas:**
   - Botón interactivo: **Lanzar Backfill Histórico (30 Días)** con modal de confirmación y selección de parámetros.
   - Estado de salud de los DAGs de Airflow (`dag_usgs_ingest`, `dag_pyspark_medallion`, `dag_daily_ai_report`, `dag_historical_backfill`).

---

## 4. Modal de Autenticación y Control de Roles (RBAC)

- **Pantalla de Inicio de Sesión Limpia:**
  - Selector rápido para evaluación: botón de acceso con 1 clic como **Admin** o como **Viewer**, además de formulario tradicional (usuario y contraseña).
  - Almacenamiento seguro del token JWT.
  - Comportamiento reactivo:
    - Si el usuario es **Viewer**, los botones de *Backfill 30D*, *Regenerar con IA* y la pestaña de *Cuarentena* se ocultan visualmente y sus endpoints están bloqueados con código HTTP 403.
    - Si el usuario es **Admin**, todas las herramientas operativas están habilitadas con badges distintivos.
