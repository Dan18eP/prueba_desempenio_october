# ADR 0005: Diseño Resiliente de DAGs en Airflow (Try-Catch, Idempotencia y Cero Caídas Bobas)

## Estado
Aprobado

## Contexto
Uno de los principales motivos de pérdida de puntos en pruebas de orquestación son las "caídas bobas" en pipelines: fallos de conexión hacia la API pública (USGS), errores por duplicación de claves primarias al reejecutar tareas, o DAGs que se quedan bloqueados consumiendo workers concurrentemente. El requerimiento establece explícitamente:
- "que el pipeline no se caiga con un error bobo"
- "tener try catch todos los dags"
- "cargas idempotentes: ejecutar dos veces el mismo intervalo no duplica registros"

## Decisión
1. **Defensa en Profundidad con Try-Catch Granular:**
   - Cada tarea en los DAGs de Airflow (construidos preferentemente con TaskFlow API y TaskGroups) implementa un bloque defensivo `try-except` con logging estructurado.
   - En caso de fallo transitorio en la API de USGS, la tarea registra una advertencia detallada, activa la política de reintentos con backoff exponencial y no aborta silenciosamente el scheduler.
2. **Políticas de Concurrencia y Timeouts:**
   - Se fija `max_active_runs = 1` en todos los DAGs para evitar condiciones de carrera entre ejecuciones concurrentes.
   - Se establece `execution_timeout = timedelta(minutes=5)` en cada tarea para evitar procesos zombi.
   - Reintentos automáticos: `retries = 3`, `retry_delay = timedelta(seconds=30)`, `retry_exponential_backoff = True`.
3. **Idempotencia Estricta por Llave Primaria:**
   - La ingesta en MinIO utiliza nombres de clave determinísticos (`feed_<timestamp>.json` o particionado por hora).
   - La sincronización a PostgreSQL utiliza `INSERT INTO ... ON CONFLICT (id) DO UPDATE SET ...`, asegurando que si un sismo ya existe, se actualicen sus campos (`mag`, `updated`, `status`, etc.) sin generar violación de clave primaria (`UNIQUE_VIOLATION`).
4. **Alertas Centralizadas con on_failure_callback:**
   - Cada DAG cuenta con un callback de fallo configurado para registrar auditoría de incidentes y notificar sin bloquear el sistema.
5. **Manejo Específico del Protocolo FDSN USGS:**
   - **Manejo de HTTP 204 No Content:** Cuando un intervalo o filtro de backfill no contiene sismos, USGS responde legítimamente con código 204 y cuerpo vacío. El pipeline intercepta el código 204 y genera una colección vacía sin provocar fallos de deserialización JSON.
   - **Pre-flight Check con `/count`:** El endpoint de backfill administrativo consulta previamente el método `/count` de USGS para estimar la carga y alertar al operador si el volumen excede el límite permitido (`limit=20000`).
   - **Recuperación CDC de Caídas con `updatedafter`:** Si el DAG de ingesta detecta un lapso de inactividad mayor a 60 minutos (downtime o reinicio de infraestructura), consulta automáticamente los sismos modificados con el parámetro `updatedafter`, cerrando la brecha histórica sin pérdida de eventos y sin duplicar inserciones.

## Consecuencias
- **Positivas:**
  - Tolerancia total a intermitencias de red con el feed de USGS y a respuestas vacías (204).
  - Re-ejecuciones manuales o automáticas completamente seguras sin duplicidad de datos.
  - Recuperación automática ante caídas de servicio prolongadas (CDC por `updatedafter`).
  - Monitoreo claro de fallos mediante logs limpios sin secretos expuestos.
