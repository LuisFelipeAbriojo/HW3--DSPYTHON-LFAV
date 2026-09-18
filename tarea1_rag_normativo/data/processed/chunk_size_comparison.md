# Comparación de tamaño de chunk (evidencia, Fase 2)

Eval set provisional: 8 preguntas in-domain (`eval/preguntas.csv`).

| size | overlap | # fragmentos | long. prom (chars) | tokens prom | tokens máx | >512 tokens | Recall@1 | Recall@3 | Recall@5 |
|---|---|---|---|---|---|---|---|---|---|
| 800 | 100 | 513 | 741 | 163 | 228 | 0 | 0.38 | 0.50 | 0.62 |
| 1200 | 150 | 347 | 1086 | 237 | 340 | 0 | 0.38 | 0.50 | 0.62 |
| 1800 | 250 | 246 | 1537 | 335 | 494 | 0 | 0.25 | 0.50 | 0.50 |