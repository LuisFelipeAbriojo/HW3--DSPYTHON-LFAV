# Reporte de chequeo de fuentes — Tarea 1, Fase 1

| Documento | Obligatorio | Páginas | Prom. caracteres/página | Páginas sin texto | Páginas a 2 columnas | ¿Usable? | ¿Orden de lectura OK? |
|---|---|---|---|---|---|---|---|
| Ley N.° 32069, Ley General de Contrataciones Públicas | Sí | 63 | 3402.8 | 0 | 63 | Sí | NO — requiere extracción por columna |
| Decreto Supremo N.° 001-2026-EF | Sí | 16 | 6908.1 | 0 | 16 | Sí | NO — requiere extracción por columna |
| Decreto Legislativo N.° 1715 (modifica art. 85.1.e de la Ley 32069) | No (opcional) | 2 | 6518.0 | 0 | 2 | Sí | NO — requiere extracción por columna |

**Nota de orden de lectura:** los documentos publicados por El Peruano (D.S. 001-2026-EF y DL 1715) usan diagramación a dos columnas. `page.extract_text()` de pdfplumber agrupa palabras por altura (`top`) en toda la página, por lo que intercala fragmentos de ambas columnas en una misma línea. La Ley 32069 (fuente gob.pe) es a una sola columna y no presenta este problema. Ver ejemplo antes/después en la Fase 1 de limpieza (`clean.py`), donde se extrae cada columna por separado antes de concatenar.

## Muestra de texto (página intermedia) por documento

### Ley N.° 32069, Ley General de Contrataciones Públicas

```
Artículo 66. Adelantos
66.1. La entidad contratante puede entregar adelantos al contratista con la finalidad de otorgarle
financiamiento o liquidez para la ejecución del contrato en las condiciones establecidas y
fundamentadas en la estrategia de contratación.
66.2. El adelanto puede ser:
a) Directo.
b) Para materiales e insumos, equipamiento y mobiliario.
c) Otros que sean establecidos en el reglamento.
66.3. Los documentos del procedimiento de selección pueden establecer adelantos directos al
contratista, los que en ningún caso exceden en conjunto del 30 % del monto del contrato original.
66
```

### Decreto Supremo N.° 001-2026-EF

```
El Peruano / Jueves 8 de enero de 2026 NORMAS LEGALES 41
“Artículo 194. Prestaciones adicionales de obra la obra, no siendo necesario apercibimiento alguno al
bajo el sistema de entrega solo construcción contratista de obra.”
(…)
194.3. No corresponde suscribir una adenda al contrato “Artículo 211. Valorización de la supervisión de la
por la aprobación de la prestación adicional, bastando obra
con su publicación en la Pladicop para que surta todos Las valorizaciones se realizan mensualmente y
sus efectos. Se encuentra prohibida la aprobación de son consideradas pagos a cuenta. Las bases pueden
```

### Decreto Legislativo N.° 1715 (modifica art. 85.1.e de la Ley 32069)

```
El Peruano / Miércoles 4 de febrero de 2026 NORMAS LEGALES 17
ejecución de obras en salud, educación, infraestructura DECRETO LEGISLATIVO QUE MODIFICA EL
hidráulica, infraestructura vial y saneamiento, y la
DECRETO LEGISLATIVO Nº 813,
gestión y conservación por niveles de servicio para el
mantenimiento vial”. LEY PENAL TRIBUTARIA
Artículo 4.- Refrendo
Artículo 1.- Objeto y finalidad
El presente Decreto Legislativo es refrendado por El presente Decreto Legislativo tiene por objeto
el Presidente del Consejo de Ministros y la Ministra de
modificar el Decreto Legislativo N° 813, Decreto
Economía y
```