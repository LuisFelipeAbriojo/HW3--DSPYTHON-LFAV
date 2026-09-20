# Reporte de calidad de datos — Tarea 2, Fase 2

Filas crudas (unión de 3 meses, antes de deduplicar): **20422**
Filas finales (una por proceso de contratación): **20422**

| Regla | Registros marcados | Acción |
|---|---|---|
| Registros repetidos (mismo ocid) | 0 | ninguno encontrado — los 3 archivos mensuales no se superponen (0 ocids en común entre meses) y cada records.csv ya es 1 fila por ocid |
| Monto faltante | 0 | mantenido con advertencia (monto_valido=False); se excluye de agregados monetarios en el dashboard |
| Monto en cero | 2476 | mantenido con advertencia (monto_valido=False) — puede ser válido (p.ej. convenio marco sin monto referencial), pero se excluye de KPIs de monto |
| Descripción faltante | 0 | corregido: se usa el título del proceso como respaldo; marcado en descripcion_valida=False para no indexarlo como si fuera una descripción real en el RAG |
| Departamento no identificable (ni coincide con departamento ni con provincia conocida) | 0 | mantenido con advertencia (departamento=NaN); excluido del choropleth pero visible en la tabla y el conteo total |
| Variantes de mayúsculas/espacios en nombre del comprador | 0 | diagnóstico (2183 valores únicos crudos -> 2183 tras normalizar mayúsculas/espacios); no se sobrescribe el nombre mostrado, se usa solo para deduplicar el ranking de compradores en la Fase 5 |
| TOTAL | 20422 -> 20422 filas | una fila por ocid |

## Distribución por departamento (tras normalizar)

| Departamento | Procesos |
|---|---|
| LIMA | 5624 |
| CUSCO | 1681 |
| ÁNCASH | 1359 |
| PUNO | 1176 |
| JUNÍN | 958 |
| APURÍMAC | 865 |
| AREQUIPA | 847 |
| CAJAMARCA | 840 |
| LA LIBERTAD | 765 |
| HUÁNUCO | 615 |
| AYACUCHO | 599 |
| PIURA | 583 |
| LAMBAYEQUE | 472 |
| LORETO | 455 |
| MOQUEGUA | 427 |
| UCAYALI | 421 |
| HUANCAVELICA | 414 |
| TACNA | 391 |
| SAN MARTÍN | 359 |
| CALLAO | 357 |
| ICA | 353 |
| AMAZONAS | 266 |
| PASCO | 259 |
| MADRE DE DIOS | 194 |
| TUMBES | 142 |