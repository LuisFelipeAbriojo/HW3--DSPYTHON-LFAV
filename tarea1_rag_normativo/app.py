"""Interfaz Streamlit de la Tarea 1 (Fase 5).

Esta es la ÚNICA capa que sabe de Streamlit en todo el proyecto: solo llama
a `engine.answer()` y pinta el resultado. No contiene lógica de RAG, no
recalcula embeddings ni reconstruye el índice al iniciar (usa el que ya
existe en chroma_db/, creado por build_index.py).
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import engine  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

st.set_page_config(page_title="Asistente de Contrataciones Públicas", page_icon="⚖️", layout="wide")


@st.cache_resource
def get_engine_ready():
    # Instancia el motor una sola vez por sesión del servidor (carga el
    # modelo de embeddings + la colección persistente existente, nunca
    # reconstruye el índice). No usamos engine.answer() aquí para no gastar
    # una llamada real al LLM solo por precalentar la app.
    engine._engine = engine.Engine()
    return True


def read_report(name: str) -> str:
    path = PROCESSED_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else f"*(no encontrado: {name})*"


tab_chat, tab_calidad = st.tabs(["Preguntar", "Calidad y evaluación"])

with tab_chat:
    st.title("⚖️ Asistente de Contrataciones Públicas del Perú")
    st.caption(
        "Responde solo con lo que dicen los documentos indexados (Ley N.° 32069, "
        "D.S. N.° 001-2026-EF y DL N.° 1715) y se abstiene cuando la respuesta no está en el corpus."
    )

    get_engine_ready()

    question = st.text_input("Tu pregunta", placeholder="Ej: ¿En qué porcentaje puedo pedir un adelanto de contrato?")

    if st.button("Preguntar", type="primary") and question:
        with st.spinner("Buscando en el corpus y consultando al modelo..."):
            result = engine.answer(question)

        if result.error:
            st.error(result.error)
        elif result.abstained:
            st.warning(result.answer)
        else:
            st.success(result.answer)

        if result.sources:
            st.subheader("Fragmentos recuperados")
            st.dataframe(
                [
                    {"Documento": s.documento, "Página": s.pagina, "Similitud": s.similitud}
                    for s in result.sources
                ],
                use_container_width=True,
                hide_index=True,
            )

        cols = st.columns(4)
        cols[0].metric("¿Se abstuvo?", "Sí" if result.abstained else "No")
        cols[1].metric("Tokens entrada", result.tokens_in)
        cols[2].metric("Tokens salida", result.tokens_out)
        cols[3].metric("Costo (USD)", f"${result.cost_usd:.5f}")

with tab_calidad:
    st.header("Reporte de calidad de extracción (Fase 1)")
    st.markdown(read_report("extraction_quality_report.md"))

    st.header("Chequeo de fuentes (Fase 1)")
    st.markdown(read_report("source_check_report.md"))

    st.header("Comparación de tamaño de chunk (Fase 2)")
    st.markdown(read_report("chunk_size_comparison.md"))

    st.header("Evaluación de recuperación y umbral (Fase 4)")
    st.markdown(read_report("retrieval_eval_report.md"))

    st.header("Comparación de embeddings: local vs. API (Fase 4)")
    st.markdown(read_report("embeddings_comparison.md"))
