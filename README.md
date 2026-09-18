# HW3 — RAG normativo y RAG Radar (Contrataciones Públicas, Perú)

Proyecto integrador de dos tareas que comparten un mismo motor RAG:

- **Tarea 1 — RAG Normativo** (`tarea1_rag_normativo/`): asistente que responde
  preguntas sobre la Ley N.° 32069 y normas conexas, citando documento y
  página, y que se abstiene cuando la pregunta no está en su corpus.
- **Tarea 2 — RAG Radar** (`tarea2_radar/`): dashboard sobre datos abiertos de
  contrataciones del Estado (OECE/OCDS), con mapa, filtros y un RAG híbrido
  (estructurado + semántico) que reutiliza el motor de la Tarea 1.

Diagramas de arquitectura (los que se muestran en el video antes de ver
código): [`docs/pipeline.md`](docs/pipeline.md).

## Estado del proyecto

Se trabaja siguiendo el cronograma sugerido del enunciado, día a día.

| Día | Fecha | Checkpoint | Estado |
|---|---|---|---|
| 1 | 2026-09-18 | Repo creado, diagrama borrador, chequeo de fuentes, 1 archivo OECE descargado | ✅ hecho |
| 2 | 2026-09-19 | Tarea 1: extracción y limpieza de texto, reporte de calidad, primer índice | ✅ hecho |
| 3 | 2026-09-20 | Tarea 1: eval set, umbral, estrategia de versiones/alcance | ✅ hecho |
| 4 | 2026-09-21 | Tarea 1: comparación de embeddings, app Streamlit | ✅ hecho |
| 5 | 2026-09-22 | Tarea 2: 3 meses descargados, 1 fila por proceso, validación, RAG híbrido | pendiente |
| 6 | 2026-09-23 | Tarea 2: dashboard, mapa, indicador de riesgo, README, costos, video | pendiente |

## Setup (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
copy .env.example .env
```

PyTorch se instala aparte, apuntando al índice CPU-only de PyTorch, para no
descargar los paquetes CUDA (varios GB) que no se usan en esta laptop.

Completa `.env` con tus propias claves (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
Nunca se commitea `.env` (está en `.gitignore`).

## Tarea 1 — Fase 1: chequeo de fuentes

Documentos indexados y por qué (detalle completo en
[`docs/pipeline.md`](docs/pipeline.md#documentos-indexados-en-la-tarea-1-decisión-de-diseño-día-1)):

1. Ley N.° 32069 (versión consolidada oficial, gob.pe/OSCE, fuente SPIJ).
2. Decreto Supremo N.° 001-2026-EF (modifica el Reglamento — el Reglamento
   en sí **no** está indexado; es un límite de corpus deliberado).
3. *(opcional)* Decreto Legislativo N.° 1715 (modifica el art. 85.1.e de la
   Ley 32069), para enriquecer el manejo de versiones de la Fase 3.

Los PDFs originales están en `tarea1_rag_normativo/data/raw/` y no se
modifican. Para correr el chequeo de fuentes:

```bash
.venv\Scripts\python tarea1_rag_normativo\src\source_check.py
```

Genera `tarea1_rag_normativo/data/processed/source_check_report.md` con:
páginas, caracteres/página, páginas sin texto y **páginas a dos columnas**
(hallazgo: los PDFs de El Peruano usan diagramación a dos columnas; la
extracción ingenua intercala ambas columnas en el orden equivocado — se
corrige en la Fase 1 de limpieza).

## Tarea 1 — Fase 1 (limpieza) y Fase 2 (chunking, embeddings, índice)

```bash
.venv\Scripts\python tarea1_rag_normativo\src\extract.py
.venv\Scripts\python tarea1_rag_normativo\src\compare_chunk_sizes.py
.venv\Scripts\python tarea1_rag_normativo\src\build_index.py
```

- **Limpieza**: `extract.py` recorta geométricamente la cabecera de El
  Peruano (banda superior de cada página) y extrae cada columna por
  separado en los documentos a dos columnas, en vez de dejar que
  `extract_text()` las intercale. Ejemplo antes/después:
  [`cleaning_before_after.md`](tarea1_rag_normativo/data/processed/cleaning_before_after.md).
  Reporte de calidad post-limpieza:
  [`extraction_quality_report.md`](tarea1_rag_normativo/data/processed/extraction_quality_report.md).
- **Chunking**: se trocea página por página (nunca documento completo
  concatenado) para no perder la trazabilidad de página. Se compararon 3
  configuraciones con un eval set provisional de 8 preguntas
  (`eval/preguntas.csv`) — resultado en
  [`chunk_size_comparison.md`](tarea1_rag_normativo/data/processed/chunk_size_comparison.md).
  Elegido: **1200 caracteres / 150 de overlap** (empata en Recall con 800/100
  pero con la mitad de fragmentos y más contexto completo por cita).
- **Embeddings locales**: `intfloat/multilingual-e5-base` (dim. 768, prefijos
  `query:`/`passage:` obligatorios según su documentación, máx. 512 tokens de
  entrada). Con chunks de 1200 caracteres el promedio es ~237 tokens y el
  máximo observado 340 — margen holgado.
- **Índice**: ChromaDB persistente en `tarea1_rag_normativo/chroma_db/`
  (347 fragmentos). `build_index.py` es idempotente (IDs deterministas
  `doc_id_pPAGINA_cN`, upsert) y resumible (solo embebe los IDs que faltan);
  verificado corriéndolo dos veces seguidas sin duplicar nada.

## Tarea 1 — Fase 3: motor RAG (umbral, versiones, alcance, costo)

```bash
.venv\Scripts\python tarea1_rag_normativo\eval\run_retrieval_eval.py   # Recall@k + sweep de umbral, sin LLM
```

- **Arquitectura**: `src/engine.py` expone una única función `answer(pregunta) -> RAGResult`
  (answer, sources con documento/página/similitud, abstained, tokens, cost, error).
  No importa Streamlit ni ninguna librería de interfaz — verificado con:
  ```bash
  grep -n "^import\|^from" tarea1_rag_normativo/src/engine.py
  ```
- **Umbral de abstención (evidencia)**: con `intfloat/multilingual-e5-base`, las
  similitudes coseno de las 20 preguntas del eval set (15 in-domain + 5 fuera
  de dominio) caen **todas entre 0.76 y 0.89** — no hay un umbral que separe
  limpiamente ambos grupos (mismo fenómeno que reporta el enunciado con el
  ejemplo del ceviche). Sweep completo:
  [`retrieval_eval_report.md`](tarea1_rag_normativo/data/processed/retrieval_eval_report.md).
  Elegido **0.78**: filtra el caso más obvio sin sacrificar ninguna pregunta
  in-domain. Las preguntas fuera de dominio pero temáticamente cercanas
  (tributario, Reglamento) sí pasan el filtro numérico — se cubren con una
  **segunda capa**: el prompt exige que el modelo responda `NO_RESPONDE` si
  el contexto no alcanza, aunque la similitud haya pasado el umbral.
- **Versiones (ejemplo real, funciona)**: la pregunta sobre el artículo 85
  (medidas cautelares) recupera fragmentos de la Ley 32069 (p. 42) y del
  Decreto Legislativo 1715 (p. 1), y la respuesta cita ambos y explica que
  "infraestructura hidráulica" fue incorporada por el DL 1715.
- **Alcance del corpus (ejemplo real, funciona)**: la pregunta sobre plazos
  del expediente técnico según el Reglamento pasa el umbral de similitud
  (0.867 > 0.78, hay fragmentos parecidos) pero el modelo responde
  `NO_RESPONDE` porque el contexto no cubre el Reglamento — el motor lo
  traduce a `abstained=True` con el mensaje configurado en `config.yaml`.
- **Costo**: cada llamada se registra en `logs/costs.log` (fecha, modelo,
  tokens in/out, latencia, costo, éxito/error). Precios de Anthropic
  verificados en claude.com/pricing el 2026-09-18: Sonnet 5 = $2/$10 por
  millón de tokens (input/output) — ver `src/costs.py`. A diferencia de
  DeepSeek, Anthropic no tiene descuento por horario; se documenta en vez
  de simularlo.

## Tarea 1 — Fase 4 (comparación de embeddings) y Fase 5 (app Streamlit)

```bash
.venv\Scripts\python tarea1_rag_normativo\eval\compare_embeddings.py
.venv\Scripts\python -m streamlit run tarea1_rag_normativo\app.py
```

Comparación con el **mismo corpus** (347 fragmentos) y las mismas 20
preguntas del eval set, dos colecciones ChromaDB independientes:

| Modelo | Dimensión | Tiempo indexación | Costo | Latencia/consulta | Recall@1 | Recall@3 | Recall@5 |
|---|---|---|---|---|---|---|---|
| Local (multilingual-e5-base) | 768 | 120.4 s (CPU) | $0 | 0.044 s | 0.40 | 0.67 | 0.80 |
| API (text-embedding-3-small) | 1536 | 13.7 s | $0.00207 | 0.372 s | 0.40 | 0.80 | 0.87 |

Precio de `text-embedding-3-small` verificado el 2026-09-18: OpenAI no
publica un $/MTok explícito para embeddings en su página de precios, se
derivó de su propia guía ("62,500 páginas por dólar" a ~800 tokens/página)
→ $0.02 por millón de tokens.

**¿Cuál elegimos?** El costo por sí solo no decide nada — $0.002 por
indexar todo el corpus es irrelevante incluso a 50x más contenido. Lo que sí
pesa: (1) el mandato del enunciado de que el modelo principal corra local;
(2) la **latencia por consulta**, que es la que sufre el usuario en cada
pregunta — el modelo local responde ~8x más rápido porque no depende de red;
(3) a cambio, la API tiene mejor Recall@3/@5 y indexa más rápido (paralelismo
en la nube vs. CPU de una laptop). Para este caso de uso (una MYPE haciendo
preguntas una a la vez, en una app que debe poder demostrarse sin depender
de que la red esté disponible) el modelo **local** es la elección correcta
para producción; la API queda documentada como techo de referencia de
calidad de recuperación.

- **App Streamlit**: `app.py` es la única capa que importa Streamlit en todo
  el proyecto; solo llama a `engine.answer()`. Carga el índice ya existente
  (`get_or_create_collection`, nunca reconstruye embeddings al iniciar).
  Pestaña "Preguntar" (respuesta, fragmentos citados con similitud,
  abstención, costo) y pestaña "Calidad y evaluación" (reportes de las
  Fases 1, 2 y 4 renderizados desde `data/processed/`).

## Tarea 2 — Fase 1: adquisición

La fuente de datos es la API de descargas masivas de OECE
(`/api/v1/file/{fuente}/{formato}/{año}/{mes}/`), no la API paginada de
procesos (esa se reserva para actualizaciones incrementales recientes, no
para construir el corpus histórico). El script es idempotente: si el `.zip`
del mes ya existe en `data/raw/`, no se vuelve a descargar.

```bash
.venv\Scripts\python tarea2_radar\src\acquire.py --year 2026 --months 08 --fmt csv
```

Log de descargas en `tarea2_radar/logs/acquire.log`.

## Estructura del repositorio

```
tarea1_rag_normativo/   config.yaml, src/, eval/, data/{raw,processed}/, logs/
tarea2_radar/           config.yaml, src/, eval/, data/{raw,processed,outputs}/, logs/
docs/pipeline.md        diagramas de arquitectura (Mermaid)
```
