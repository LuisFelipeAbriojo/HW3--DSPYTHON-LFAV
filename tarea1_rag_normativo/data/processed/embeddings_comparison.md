# Comparación de embeddings: local vs. API (Fase 4)

Mismo corpus (347 fragmentos), mismas 20 preguntas del eval set.

| Modelo | Dimensión | Tiempo de indexación (s) | Costo (USD) | Latencia prom. por consulta (s) | Recall@1 | Recall@3 | Recall@5 |
|---|---|---|---|---|---|---|---|
| Local (intfloat/multilingual-e5-base) | 768 | 120.4 | 0.00000 | 0.044 | 0.40 | 0.67 | 0.80 |
| API (text-embedding-3-small) | 1536 | 13.7 | 0.00207 | 0.372 | 0.40 | 0.80 | 0.87 |