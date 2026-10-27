# ADR 0011: Erradicación del Concepto de Cuarentena en Favor del Linaje Puro y Preservación Total

## Estado
Aceptado y Aplicado.

## Fecha
27 de Octubre de 2026

## Contexto y Planteamiento del Problema
El enunciado del proyecto mencionaba mecanismos de control y auditoría de calidad ante datos erróneos o anómalos. En etapas preliminares de diseño, se exploró el uso de "cuarentenas" para aislar registros con advertencias de calidad.

Sin embargo, el Tech Lead y las reglas fundamentales del proyecto fijaron de forma tajante e inviolable:
1. **Linaje Puro:** Nace en Bronze y fluye sin capas intermedias ni tablas huérfanas segregadas.
2. **Invariante de Balance ("20 in -> 20 out"):** Todo sismo recibido desde el catálogo USGS debe ser procesado, preservado y puesto a disposición del usuario. El descarte o segregación de datos viola la fidelidad operativa requerida en un centro de mando sísmico.
3. La existencia de terminología o vistas de "Cuarentena" en la interfaz de usuario inducía a confusión sobre el estado y disponibilidad real de los datos.

## Decisión Arquitectónica
Se acuerda de manera formal y definitiva:
1. **Erradicar el concepto y la nomenclatura de "Cuarentena":** No existirá ninguna tabla, vista, componente de frontend ni endpoint destinado a aislar o poner datos en cuarentena.
2. **Etiquetado No Destructivo en Base de Datos:** Los registros que presenten advertencias según las 7 reglas Pandera (ISO/IEC 25012) o anomalías estadísticas (Z-Score > 2.5) son promovidos a Gold marcados con el estado `FLAGGED` y acompañados de su motivo analítico (`anomaly_explanation`, `quality_reasons`), pero **permanecen 100% visibles e interactivos** en el catálogo operacional y en los gráficos geoespaciales.
3. **Reconciliación Estricta de Lotes:** La auditoría de conciliación en `audit.batch_reconciliation` compara lote contra lote de forma atómica (`raw_count == silver_count == gold_count`), garantizando matemáticamente una tasa de pérdida del $0.00\%$ y una fidelidad del $100.0\%$.

## Consecuencias
### Positivas:
- **Cero Pérdida de Información:** No existen datos invisibles ni "perdidos" para los analistas ni para el agente de IA.
- **Claridad de Gobernanza:** El panel de gobernanza se enfoca en la Matriz de Calidad Pandera y en la trazabilidad OpenMetadata, eliminando la ambigüedad conceptual.
- **Cumplimiento Normativo:** Alineado 100% a la especificación de calidad ISO/IEC 25012 sobre completitud y consistencia de datos.

### Negativas / Mitigaciones:
- Los consumidores deben filtrar por `quality_status` si desean evaluar únicamente registros con calificación pura (`VALID`), lo cual está soportado de forma nativa en los parámetros de la API REST (`/api/events?quality_status=VALID`).
