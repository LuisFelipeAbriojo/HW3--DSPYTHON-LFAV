# Diagramas de arquitectura

> Borrador Día 1. Se ajusta a medida que avanzan las fases; estos son los
> diagramas que se muestran en el video antes de cualquier línea de código.

## Tarea 1 — RAG Normativo

Dos procesos separados: uno *offline* (se corre una vez, o cuando cambian los
documentos) y uno *online* (se corre por cada pregunta del usuario). El
proceso online nunca vuelve a leer los PDFs.

```mermaid
flowchart TD
    subgraph OFFLINE["Proceso OFFLINE — build_index.py"]
        A1[PDFs oficiales\ndata/raw/] --> A2[Extracción por página\npdfplumber, columna-aware]
        A2 --> A3[Limpieza\nquitar cabeceras/pies glued]
        A3 --> A4[Chunking\ntamaño+overlap con evidencia]
        A4 --> A5[Embeddings locales\nsentence-transformers multilingüe]
        A5 --> A6[(ChromaDB\npersistente)]
        A2 -.-> A7[Reporte de calidad\nde extracción]
    end

    subgraph ONLINE["Proceso ONLINE — engine.answer(pregunta)"]
        B1[Pregunta del usuario] --> B2[Embedding de la pregunta]
        B2 --> B3{Buscar en\nChromaDB}
        A6 --> B3
        B3 --> B4{¿Similitud del mejor\nfragmento ≥ umbral?}
        B4 -- No --> B5[Abstención\nsin llamar al LLM]
        B4 -- Sí --> B6[Prompt con contexto\n+ instrucción de citar\ndocumento/página]
        B6 --> B7[LLM generador\nAnthropic Claude]
        B7 --> B8[Log de costo\ntokens, latencia, USD]
        B5 --> B9[RAGResult\nanswer, sources, abstained,\ntokens, cost, error]
        B8 --> B9
    end

    B9 --> C1[Streamlit app.py]
    B9 --> C2["(futuro) otra interfaz"]
```

Puntos clave que se explican en el video:
- El número de página vive como **metadata** de cada fragmento desde la
  extracción (nunca se pierde al unir/dividir texto), no se infiere del texto.
- La decisión de **no llamar al LLM** ocurre en `B4`, antes de cualquier costo
  de generación — se calibra con el eval set (Fase 4).
- `engine.py` no importa Streamlit ni ninguna librería de interfaz — se
  verifica con `grep -rn "^import\|^from" src/engine.py`.

## Tarea 2 — RAG Radar

```mermaid
flowchart TD
    subgraph ACQ["Adquisición — acquire.py"]
        D1[OECE bulk mensual\n/api/v1/file/seace_v3/csv/AAAA/MM/] --> D2[data/raw/*.zip\nidempotente, no re-descarga]
        D3[OECE API paginada\nsolo actualizaciones recientes] -.-> D2
    end

    subgraph VAL["Validación y normalización — validate.py"]
        D2 --> E1[records.csv = 1 fila por ocid]
        E1 --> E2[Detección de duplicados,\nmontos en 0, sin descripción]
        E2 --> E3[Normalización territorial\na 25 departamentos]
        E3 --> E4[Reporte de calidad de datos]
    end

    subgraph IDX["Índice híbrido — index.py"]
        E4 --> F1[Embeddings locales\nmisma familia que Tarea 1]
        F1 --> F2[(ChromaDB\ndescripción + metadata:\ndepto, monto, fecha, categoría, ocid)]
    end

    subgraph QRY["Motor — engine.answer(pregunta)"]
        G1[Pregunta en lenguaje natural] --> G2[Extraer condiciones\nnuméricas/territoriales]
        G2 --> G3[Filtros de metadata\nChromaDB where=...]
        G1 --> G4[Embedding semántico\nsolo la parte descriptiva]
        G3 --> G5{Umbral de similitud\n calibrado en Tarea 1}
        G4 --> G5
        G5 -- No --> G6[Abstención]
        G5 -- Sí --> G7[LLM + cita por ocid]
    end

    F2 --> G3
    F2 --> G4
    G6 --> H1[Streamlit dashboard]
    G7 --> H1
    E4 --> H1
    E3 --> H2[Choropleth por departamento]
```

Puntos clave:
- El **departamento** vive como metadata estructurada, nunca como texto libre
  para el embedding — así "Cusco" no depende de que el modelo semántico
  entienda geografía.
- Condiciones numéricas y territoriales ("más de un millón", "en Cusco") son
  **filtros** aplicados antes/junto a la búsqueda vectorial, no texto que se
  vectoriza.
- El dashboard **nunca** descarga bulk ni reconstruye el índice al cargar;
  lee artefactos precomputados (`data/processed/`, `chroma_db/`).

## Documentos indexados en la Tarea 1 (decisión de diseño, Día 1)

| # | Documento | Rol | Fuente oficial |
|---|---|---|---|
| 1 | Ley N.° 32069 (versión consolidada, con modificatorias al 19-07-2026) | Norma base | gob.pe / OSCE (fuente base: SPIJ) |
| 2 | Decreto Supremo N.° 001-2026-EF | Modifica el **Reglamento** de la Ley 32069 (el Reglamento en sí no está indexado — límite explícito del corpus) | busquedas.elperuano.pe |
| 3 (opcional) | Decreto Legislativo N.° 1715 | Modifica el literal e) del numeral 85.1 del artículo 85 de la Ley 32069 | busquedas.elperuano.pe |

Por qué esta combinación: el documento 2 obliga al sistema a reconocer los
**límites de su corpus** (preguntas de Reglamento deben verse abstenidas, no
inventadas). El documento 3 (opcional) da un caso concreto y corto (2
páginas) de **atribución de versión**: el texto consolidado del documento 1
ya incorpora el cambio, pero el asistente debe poder citar qué norma
específica lo introdujo cuando se le pregunta.
