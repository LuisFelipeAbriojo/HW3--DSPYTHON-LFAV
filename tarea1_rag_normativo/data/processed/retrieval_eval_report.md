# Evaluación de recuperación (sin LLM) — Fase 4

## Recall@k sobre 15 preguntas in-domain

| k | Recall@k |
|---|---|
| 1 | 0.40 |
| 3 | 0.67 |
| 5 | 0.80 |

### Detalle por pregunta

| id | categoría | rank del fragmento correcto | similitud top-1 |
|---|---|---|---|
| q01 | version | 5 | 0.864 |
| q02 | estandar | 1 | 0.889 |
| q03 | mype_phrasing | 1 | 0.845 |
| q04 | estandar | no encontrado en top-5 | 0.841 |
| q05 | estandar | no encontrado en top-5 | 0.864 |
| q06 | mype_phrasing | no encontrado en top-5 | 0.854 |
| q07 | estandar | 2 | 0.862 |
| q08 | version | 1 | 0.825 |
| q11 | version | 4 | 0.832 |
| q12 | mype_phrasing | 1 | 0.856 |
| q13 | mype_phrasing | 2 | 0.856 |
| q14 | estandar | 3 | 0.861 |
| q15 | estandar | 1 | 0.874 |
| q16 | mype_phrasing | 1 | 0.863 |
| q17 | estandar | 3 | 0.848 |

## Similitud top-1 por pregunta (todas, para el sweep de umbral)

| id | tipo | similitud top-1 |
|---|---|---|
| q01 | in_domain | 0.864 |
| q02 | in_domain | 0.889 |
| q03 | in_domain | 0.845 |
| q04 | in_domain | 0.841 |
| q05 | in_domain | 0.864 |
| q06 | in_domain | 0.854 |
| q07 | in_domain | 0.862 |
| q08 | in_domain | 0.825 |
| q11 | in_domain | 0.832 |
| q12 | in_domain | 0.856 |
| q13 | in_domain | 0.856 |
| q14 | in_domain | 0.861 |
| q15 | in_domain | 0.874 |
| q16 | in_domain | 0.863 |
| q17 | in_domain | 0.848 |
| q09 | out_domain | 0.763 |
| q10 | out_domain | 0.867 |
| q18 | out_domain | 0.857 |
| q19 | out_domain | 0.855 |
| q20 | out_domain | 0.847 |

## Sweep de umbral de abstención

| umbral | abstenciones correctas (de 5 fuera de dominio) | abstenciones incorrectas (de 15 in-domain) | fuera de dominio que SÍ pasaría al LLM |
|---|---|---|---|
| 0.30 | 0 | 0 | 5 |
| 0.35 | 0 | 0 | 5 |
| 0.40 | 0 | 0 | 5 |
| 0.45 | 0 | 0 | 5 |
| 0.50 | 0 | 0 | 5 |
| 0.55 | 0 | 0 | 5 |
| 0.60 | 0 | 0 | 5 |
| 0.65 | 0 | 0 | 5 |
| 0.70 | 0 | 0 | 5 |
| 0.75 | 0 | 0 | 5 |
| 0.76 | 0 | 0 | 5 |
| 0.77 | 1 | 0 | 4 |
| 0.78 | 1 | 0 | 4 |
| 0.79 | 1 | 0 | 4 |
| 0.80 | 1 | 0 | 4 |
| 0.81 | 1 | 0 | 4 |
| 0.82 | 1 | 0 | 4 |
| 0.83 | 1 | 1 | 4 |
| 0.84 | 1 | 2 | 4 |
| 0.85 | 2 | 5 | 3 |
| 0.86 | 4 | 8 | 1 |
| 0.87 | 5 | 13 | 0 |
| 0.88 | 5 | 14 | 0 |
| 0.89 | 5 | 15 | 0 |
| 0.90 | 5 | 15 | 0 |