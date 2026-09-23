# Guion del video (12 min) — leer en voz alta, tipo teleprompter

> Instrucciones de uso: cada bloque de texto en **negrita cursiva** es lo
> que se muestra en pantalla; el texto normal es lo que dices, palabra por
> palabra o como guía muy cercana. Los tiempos son acumulados (mm:ss).
> Practica una vez antes de grabar — vas a hablar más rápido de lo que
> crees al leer.

---

## 0:00–1:00 — El problema y el usuario

***[Pantalla: slide con el título del proyecto y una foto/ícono de una MYPE]***

Imagina una micro o pequeña empresa peruana que quiere venderle al
Estado. Tiene dos problemas al mismo tiempo.

Primero, no entiende las reglas. Las normas de contrataciones públicas son
largas, técnicas, y cambian seguido. Contratar un abogado para cada
consulta cuesta más que muchos de los contratos a los que podría postular.

Segundo, no ve las oportunidades. Cada mes se publican miles de procesos
de contratación. Nadie los lee todos, y los que le sirven a esta empresa
están escondidos entre los que no.

Este proyecto construye las dos herramientas que esa empresa necesita.
La Tarea 1 responde "¿qué dice la ley?" con un asistente que solo usa lo
que está en los documentos indexados, cita página y documento en cada
respuesta, y se abstiene cuando no sabe. La Tarea 2 responde "¿qué está
comprando el Estado, y dónde?" combinando datos abiertos de
contrataciones con ese mismo motor de búsqueda semántica.

Un sistema que responde con confianza y se equivoca es peor que un
sistema que no responde. Esa idea guía todas las decisiones que van a
ver en este video.

---

## 1:00–3:00 — Pipeline de la Tarea 1 (offline y online)

***[Pantalla: solo el diagrama Mermaid de la Tarea 1, docs/pipeline.md — nada de código]***

El motor de la Tarea 1 tiene dos procesos separados. Uno offline, que se
corre una sola vez, y uno online, que se corre en cada pregunta. El
proceso online nunca vuelve a leer los PDFs.

El proceso offline arranca con tres documentos oficiales: la Ley N.°
32069, Ley General de Contrataciones Públicas, en su versión consolidada
de gob.pe; el Decreto Supremo N.° 001-2026-EF, que modifica el Reglamento
de esa ley; y, como documento opcional, el Decreto Legislativo N.° 1715,
que modifica un artículo específico de la propia ley. Entre los tres
suman 81 páginas.

Cada página se extrae por separado, y el número de página se guarda como
metadata desde ese primer paso — nunca se junta todo el documento en un
solo texto para trocearlo después, porque eso es exactamente lo que
pierde la trazabilidad de las citas.

Encontramos algo interesante en la extracción: los PDFs de El Peruano
están armados a dos columnas, y una extracción ingenua mezcla ambas
columnas línea por línea, generando texto sin sentido. Lo resolvimos
recortando geométricamente la cabecera de cada página y extrayendo cada
columna por separado antes de concatenar.

El texto limpio se trocea en fragmentos de 1200 caracteres con 150 de
traslape — elegido comparando tres tamaños distintos contra un set de
preguntas, no por default. Cada fragmento se embebe con un modelo local
multilingüe, intfloat/multilingual-e5-base, y se guarda en una colección
de ChromaDB junto con su documento, versión y página.

En el proceso online, la pregunta se convierte en un vector, se busca en
ChromaDB, y aquí pasa lo más importante: si el fragmento más parecido no
supera un umbral de similitud, el sistema se abstiene sin llamar al
modelo generador. Esa decisión — contestar o no — se toma antes de gastar
un solo centavo. Solo si se supera el umbral se arma un prompt con el
contexto recuperado y se llama a Claude, que debe citar documento y
página en cada afirmación.

---

## 3:00–4:30 — Pipeline de la Tarea 2

***[Pantalla: solo el diagrama Mermaid de la Tarea 2 — nada de código]***

La Tarea 2 reutiliza el mismo motor, pero sobre datos abiertos de
contrataciones. El proceso empieza descargando archivos mensuales
masivos de OECE — no la API paginada, que reservamos para actualizaciones
recientes, sino el endpoint de descarga masiva por mes, que es la fuente
correcta para construir un corpus histórico.

Cada archivo mensual ya viene como la vista "record" del estándar OCDS:
una fila por proceso de contratación, con el estado acumulado de todas
sus "releases" — convocatoria, buena pro, contrato — hasta la fecha del
corte. Una release es un evento; un record es el estado consolidado. Por
eso records.csv, y no las releases sueltas, es la fuente correcta para
"una fila por proceso".

Después viene la validación: se revisan duplicados, montos en cero,
descripciones vacías, y se normaliza la ubicación del comprador a los 25
departamentos del Perú, incluyendo Callao.

El índice híbrido guarda dos cosas por proceso: un embedding semántico de
la descripción, y metadata estructurada — departamento, monto, fecha,
categoría, comprador, y el identificador ocid. Cuando alguien pregunta
"obras de agua en Cusco por más de un millón de soles", el departamento y
el monto se convierten en un filtro exacto sobre esa metadata, y solo la
parte descriptiva se compara por significado. El motor reutiliza la misma
lógica de abstención y de costo de la Tarea 1 — literalmente el mismo
archivo de código, no una copia.

El resultado final se sirve en un dashboard: mapa, tabla, gráficos de
distribución, y un indicador de riesgo de postor único, que van a ver en
la demo.

---

## 4:30–6:30 — Decisiones técnicas, con números

***[Pantalla: tablas — chunk_size_comparison.md, retrieval_eval_report.md, embeddings_comparison.md, data_quality_report.md]***

Cuatro decisiones que quiero defender con evidencia, no con intuición.

Primero, el tamaño de fragmento. Comparamos 800, 1200 y 1800 caracteres
contra un set de preguntas. 800 y 1200 empataron en recall, pero 1200 usa
la mitad de fragmentos y dejó más contexto completo por cita — por eso lo
elegimos.

Segundo, el umbral de abstención. Con nuestro modelo local, las
similitudes de coseno de preguntas dentro y fuera de dominio caen todas
entre 0.76 y 0.89 — no hay un corte limpio. Una pregunta como "¿cómo
cocino un ceviche?" saca 0.76, casi lo mismo que una pregunta real sobre
la ley. Por eso no confiamos solo en el número: agregamos una segunda
capa, una instrucción en el prompt que obliga al modelo a decir
"NO_RESPONDE" si el contexto no alcanza, aunque haya pasado el filtro.

Tercero, embeddings local versus API. Comparamos nuestro modelo local
contra text-embedding-3-small de OpenAI, mismo corpus, mismas preguntas.
La API tiene mejor recall — 0.87 contra 0.80 en Recall arroba 5 — e
indexa más rápido. Pero el modelo local responde casi ocho veces más
rápido por consulta, cuesta cero, y no depende de que haya red. Elegimos
local para producción: el costo no es el argumento, la latencia por
consulta sí lo es.

Cuarto, en la Tarea 2 encontramos que el campo "región" de los datos
abiertos de OECE en realidad trae la provincia, no la región, en más de
la mitad de los registros. Usamos el campo "departamento" en su lugar, y
normalizamos con una tabla de las 196 provincias del Perú, logrando cero
procesos sin ubicar.

Y algo que no esperábamos: el umbral que calibramos en la Tarea 1 no
transfirió a la Tarea 2. Tuvimos que recalibrarlo con evidencia nueva,
subiéndolo de 0.78 a 0.84.

---

## 6:30–9:30 — Demo en vivo de ambas apps

***[Pantalla: apps corriendo — seguir este guión de clics]***

**Tarea 1** *(≈90 s)*

Abro la app de la Tarea 1. Primero, una pregunta que el corpus sí puede
responder con matices de versión: "¿qué reglas rigen las medidas
cautelares del artículo 85, y qué cambió una modificación reciente?" —
[ejecutar] — la respuesta cita la Ley 32069 en la página 42, y también el
Decreto Legislativo 1715, explicando que ese decreto agregó
"infraestructura hidráulica" al artículo. Dos documentos, una sola
respuesta coherente.

Ahora una pregunta que el corpus NO puede responder bien: "¿cuál es el
plazo para que la Entidad apruebe el expediente técnico, según el
Reglamento?" — [ejecutar] — el sistema se abstiene y dice explícitamente
que esa respuesta puede estar en el Reglamento, que no está indexado. No
inventa un plazo.

Reviso la pestaña de calidad: ahí están los reportes de extracción, el
umbral calibrado, y la comparación de embeddings que acabo de explicar.

**Tarea 2** *(≈90 s)*

Cambio al dashboard de la Tarea 2. En el mapa, Lima concentra la mayor
cantidad de procesos. Voy a la pestaña de preguntas y escribo la
pregunta del propio enunciado: "obras de agua y saneamiento en Cusco por
encima de un millón de soles" — [ejecutar] — el sistema detecta el filtro
de departamento y de monto, y la respuesta cita seis procesos reales por
su ocid, con sus montos exactos.

Ahora la parte de innovación: elijo uno de esos procesos y le pregunto al
asistente de la Tarea 1 qué dice la ley sobre su procedimiento de
selección — [ejecutar] — y aquí pasa algo honesto: el asistente se
abstiene, porque el detalle operativo de ese procedimiento específico
vive en el Reglamento, no en la Ley. La conexión entre las dos tareas no
rompe la disciplina de abstención, la hereda.

Cierro con la pestaña de calidad de datos, donde está el indicador de
riesgo de postor único que voy a explicar en un momento.

---

## 9:30–10:30 — Código: solo lo que sostiene las decisiones

***[Pantalla: editor — abrir solo estos archivos, en este orden]***

Tres fragmentos, nada más.

Primero, `engine.py` de la Tarea 1: esta es la función `answer`, la única
puerta de entrada al motor. Recibe una pregunta, devuelve un resultado
con la respuesta, las fuentes, si se abstuvo, los tokens y el costo. Este
archivo no importa Streamlit en ninguna línea — lo pueden verificar
ustedes mismos con un grep, está documentado en el README.

Segundo, `query_parser.py` de la Tarea 2: esta función busca condiciones
de departamento y de monto en la pregunta, con coincidencia de palabra
completa — tuvimos un bug real acá, "Piura" se detectaba como "Ica"
porque la palabra "básica" termina en esas tres letras. Ya corregido.

Tercero, `costs.py`: esta tabla de precios, con fecha de verificación, y
esta función que calcula el costo exacto de cada llamada según el modelo
y la fecha — así es como sabemos, en tiempo real, cuánto cuesta cada
pregunta.

---

## 10:30–12:00 — Hallazgos, límites y costo real

***[Pantalla: slide o terminal con el resumen final]***

Para cerrar, tres cosas que aprendimos y que no sabíamos al empezar.

Primero, un hallazgo de datos: en la Tarea 2, entre los procesos que sí
llegaron a tener buena pro, el 13.1 por ciento tuvo un solo postor. Un
comprador destacó: el Organismo de Evaluación y Fiscalización Ambiental,
con 174 procesos adjudicados y 95.4 por ciento de postor único. Quiero
ser explícito: esto es una señal para mirar más de cerca, no una
acusación. Puede deberse a un mercado con pocos proveedores
especializados. No publicamos nombres de personas, solo de entidades
públicas.

Segundo, los límites de nuestro corpus. La Tarea 1 no indexa el
Reglamento completo — lo dejamos fuera a propósito, y el sistema lo
reconoce cuando corresponde, como mostramos en la demo. En la Tarea 2, en
departamentos muy grandes como Lima, con más de cinco mil procesos nuestra
búsqueda semántica a veces trae un proceso parecido pero no el exacto que
uno buscaba — es un límite real de recall a escala, no un error del
código.

Tercero, el costo real. Todas las llamadas al modelo generador quedan
registradas con fecha, modelo, tokens y costo en dólares. Durante todo el
desarrollo de este proyecto, probando ambos motores en vivo varias veces,
gastamos en total menos de seis centavos de dólar. La mayoría de las
preguntas fuera de dominio, como la del ceviche, cuestan literalmente
cero, porque el sistema decide no llamar al modelo antes de gastar nada.

Como innovación adicional, conectamos las dos tareas — ya lo vieron en la
demo — y montamos un chequeo automático en GitHub Actions que corre la
evaluación de recuperación en cada cambio al código y falla si el
Recall arroba 3 cae por debajo de 0.55. Ese chequeo no cuesta nada,
porque nunca llama al modelo generador.

Eso es todo. Gracias.

---

## Checklist antes de grabar

- [ ] Practicar una vez en voz alta con cronómetro; ajustar ritmo si te
      pasas de 12 minutos.
- [ ] Tener ambas apps corriendo ANTES de empezar a grabar (`streamlit
      run tarea1_rag_normativo/app.py` y `streamlit run
      tarea2_radar/app.py` en puertos distintos).
- [ ] Tener `docs/pipeline.md` abierto y renderizado (Mermaid) para la
      sección 1:00–4:30.
- [ ] Tener abiertos de antemano, en pestañas: `chunk_size_comparison.md`,
      `retrieval_eval_report.md` (Tarea 1 y Tarea 2),
      `embeddings_comparison.md`, `data_quality_report.md`,
      `risk_report.md`.
- [ ] Verificar que las dos preguntas de ejemplo de la Tarea 1 y la
      pregunta de la Tarea 2 den los resultados descritos aquí (los
      montos/ocids son reales de tus datos, pero confírmalos por si
      cambiaste algo).
- [ ] Tener los tres archivos de código de la sección 9:30–10:30 abiertos
      en pestañas del editor, en el orden indicado.
