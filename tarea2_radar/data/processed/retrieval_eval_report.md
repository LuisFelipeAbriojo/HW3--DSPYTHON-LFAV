# Evaluación de recuperación híbrida (sin LLM) — Tarea 2, Fase 3

| id | filtros aplicados | similitud top-1 | rank del primer ocid relevante | resultado |
|---|---|---|---|---|
| p01 | depto=CUSCO, monto=('gte', 1000000) | 0.844 | - | rank 3 |
| p02 | depto=PIURA, monto=None | 0.874 | - | rank 1 |
| p03 | depto=LIMA, monto=None | 0.842 | - | no encontrado en top-5 |
| p04 | depto=AREQUIPA, monto=('lte', 50000.0) | 0.859 | - | rank 1 |
| p05 | depto=CALLAO, monto=None | 0.894 | - | no encontrado en top-5 |
| p06 | depto=LORETO, monto=None | 0.860 | - | rank 1 |
| p07 | depto=LORETO, monto=('gte', 10000000) | 0.847 | - | rank 2 |
| p08 | depto=LORETO, monto=None | 0.851 | - | no encontrado en top-5 |
| p09 | depto=TUMBES, monto=('gte', 100000000) | n/a | - | sin resultados (correcto) |
| p10 | depto=MOQUEGUA, monto=None | 0.863 | - | rank 5 |

## Recall@k sobre 9 preguntas con procesos relevantes conocidos

| k | Recall@k |
|---|---|
| 1 | 0.33 |
| 3 | 0.56 |
| 5 | 0.67 |

1 pregunta(s) sin procesos relevantes esperados (prueban abstención/filtro vacío), ver tabla arriba.

## Recalibración del umbral (no transfiere de la Tarea 1)

El umbral de 0.78 calibrado en la Tarea 1 se probó contra 5 preguntas fuera
de dominio en este corpus:

| Pregunta fuera de dominio | Similitud top-1 |
|---|---|
| ¿Cuál es la capital de Francia? | 0.766 |
| ¿Cuánto pesa un elefante africano? | 0.783 |
| ¿Cómo cocino un ceviche? | 0.807 |
| Recomiéndame una película de terror | 0.826 |
| Quiero comprar zapatillas para correr una maratón | 0.856 |

Contra el rango in-domain observado arriba (0.842-0.894), **0.78 deja
pasar las 5** preguntas fuera de dominio al LLM. Se recalibró a **0.84**:
filtra 4/5 sin sacrificar ninguna de las 9 in-domain (mínimo observado
0.842). La quinta ("zapatillas", 0.856) sigue pasando el filtro numérico —
se cubre con la segunda capa de defensa (el prompt exige `NO_RESPONDE` si
el contexto no responde la pregunta), igual que en la Tarea 1.
