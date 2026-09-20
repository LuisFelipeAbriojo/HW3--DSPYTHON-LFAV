"""Dashboard Streamlit de la Tarea 2 (Fase 4).

Solo lee artefactos precomputados (`data/processed/`) — nunca descarga
archivos de OECE ni reconstruye el índice al cargar. La única lógica de
RAG que toca es `engine.answer()`.

Innovación: conecta las dos tareas. Un proceso recuperado por el RAG
híbrido de la Tarea 2 trae su `procedimiento` de selección (p.ej.
"Licitación Pública Abreviada"); con un clic, se le pregunta al motor de
la Tarea 1 qué dice la Ley N.° 32069 sobre ese procedimiento -- el mismo
`engine.answer()` de la Tarea 1, sin duplicar una sola línea de su lógica.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import engine  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TAREA1_SRC = BASE_DIR.parent / "tarea1_rag_normativo" / "src"
sys.path.insert(0, str(TAREA1_SRC))


def _load_tarea1_engine():
    """Carga tarea1_rag_normativo/src/engine.py bajo un nombre propio
    (`engine_tarea1`) para no chocar con el módulo `engine` de esta misma
    Tarea 2 -- ambos archivos se llaman igual pero son motores distintos."""
    spec = importlib.util.spec_from_file_location("engine_tarea1", TAREA1_SRC / "engine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine_tarea1 = _load_tarea1_engine()

st.set_page_config(page_title="RAG Radar — Contrataciones Públicas", page_icon="🗺️", layout="wide")

CATEGORIA_ES = {"goods": "Bienes", "services": "Servicios", "works": "Obras"}


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "procesos.csv", parse_dates=["fecha_publicacion"])
    # las fechas vienen con offset (-05:00); se normalizan a tz-naive para
    # poder compararlas con los rangos de fecha del sidebar (que sí lo son).
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"], utc=True).dt.tz_localize(None)
    df["categoria_es"] = df["categoria"].map(CATEGORIA_ES).fillna(df["categoria"])
    return df


@st.cache_data
def load_geojson() -> dict:
    return json.loads((PROCESSED_DIR / "geo" / "peru_departamentos.geojson").read_text(encoding="utf-8"))


@st.cache_data
def load_report(name: str) -> str:
    path = PROCESSED_DIR / name
    return path.read_text(encoding="utf-8") if path.exists() else f"*(no encontrado: {name})*"


@st.cache_resource
def get_engine_ready():
    engine._engine = engine.Engine()
    return True


@st.cache_resource
def get_tarea1_engine_ready():
    engine_tarea1._engine = engine_tarea1.Engine()
    return True


df_all = load_data()
geojson = load_geojson()

st.sidebar.header("Filtros")
departamentos = sorted(df_all["departamento"].dropna().unique())
sel_deptos = st.sidebar.multiselect("Departamento", departamentos, default=[])
categorias = sorted(df_all["categoria_es"].dropna().unique())
sel_categorias = st.sidebar.multiselect("Categoría", categorias, default=[])

monto_min, monto_max = float(df_all["monto_pen"].min()), float(df_all["monto_pen"].max())
sel_monto = st.sidebar.slider(
    "Rango de monto (S/)", min_value=0.0, max_value=monto_max, value=(0.0, monto_max)
)

fecha_min, fecha_max = df_all["fecha_publicacion"].min(), df_all["fecha_publicacion"].max()
sel_fechas = st.sidebar.date_input(
    "Rango de fecha de publicación", value=(fecha_min.date(), fecha_max.date()),
    min_value=fecha_min.date(), max_value=fecha_max.date(),
)

sel_umbral = st.sidebar.slider("Umbral de similitud (pregunta al RAG)", 0.5, 0.95, 0.84, 0.01)

# --- aplicar filtros ---
df = df_all.copy()
if sel_deptos:
    df = df[df["departamento"].isin(sel_deptos)]
if sel_categorias:
    df = df[df["categoria_es"].isin(sel_categorias)]
df = df[(df["monto_pen"] >= sel_monto[0]) & (df["monto_pen"] <= sel_monto[1])]
if isinstance(sel_fechas, tuple) and len(sel_fechas) == 2:
    d0, d1 = pd.Timestamp(sel_fechas[0]), pd.Timestamp(sel_fechas[1])
    df = df[(df["fecha_publicacion"] >= d0) & (df["fecha_publicacion"] <= d1)]

st.title("🗺️ RAG Radar — ¿Qué está comprando el Estado, y dónde?")

if df.empty:
    st.warning("No hay procesos que cumplan estos filtros. Ajusta los filtros del panel lateral.")
else:
    # --- KPIs ---
    adjudicados = df[df["adjudicado"] & df["num_postores"].notna()]
    pct_postor_unico = (adjudicados["num_postores"] == 1).mean() if len(adjudicados) else float("nan")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Procesos", f"{len(df):,}")
    c2.metric("Monto total (S/)", f"{df.loc[df['monto_valido'], 'monto_pen'].sum():,.0f}")
    c3.metric("Departamentos", df["departamento"].nunique())
    c4.metric(
        "% postor único (adjudicados)",
        f"{pct_postor_unico:.1%}" if pct_postor_unico == pct_postor_unico else "s/d",
    )

    tab_mapa, tab_pregunta, tab_tabla, tab_dist, tab_calidad = st.tabs(
        ["Mapa", "Preguntar", "Tabla", "Distribución", "Calidad de datos"]
    )

    with tab_mapa:
        por_depto = df.groupby("departamento").agg(procesos=("ocid", "count"), monto=("monto_pen", "sum")).reset_index()
        metrica = st.radio("Colorear por", ["procesos", "monto"], horizontal=True)
        fig = px.choropleth(
            por_depto, geojson=geojson, locations="departamento",
            featureidkey="properties.NOMBDEP", color=metrica,
            color_continuous_scale="Reds", scope=None,
            hover_data={"departamento": True, "procesos": True, "monto": ":,.0f"},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tab_pregunta:
        get_engine_ready()
        engine._engine.threshold = sel_umbral
        pregunta = st.text_input(
            "Pregunta", placeholder='Ej: "obras de agua y saneamiento en Cusco por encima de un millón de soles"'
        )
        if st.button("Preguntar", type="primary") and pregunta:
            with st.spinner("Filtrando y buscando..."):
                st.session_state["t2_result"] = engine.answer(pregunta)

        result = st.session_state.get("t2_result")
        if result is not None:
            st.caption(f"Filtros detectados: {result.filtros_aplicados}")
            if result.error:
                st.error(result.error)
            elif result.abstained:
                st.warning(result.answer)
            else:
                st.success(result.answer)
            if result.sources:
                st.dataframe(
                    [
                        {"ocid": s.ocid, "Comprador": s.comprador, "Departamento": s.departamento,
                         "Monto (S/)": s.monto_pen, "Similitud": s.similitud}
                        for s in result.sources
                    ],
                    use_container_width=True, hide_index=True,
                )
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Tokens", f"{result.tokens_in}+{result.tokens_out}")
            mc2.metric("Costo (USD)", f"${result.cost_usd:.5f}")

            if result.sources:
                st.divider()
                st.subheader("🔗 Vínculo con la Tarea 1: ¿qué dice la norma?")
                st.caption(
                    "Elige uno de los procesos de arriba para preguntarle al "
                    "asistente normativo de la Tarea 1 qué dice la Ley N.° 32069 "
                    "sobre su procedimiento de selección."
                )
                opciones = {s.ocid: s for s in result.sources}
                ocid_elegido = st.selectbox("Proceso", list(opciones.keys()))
                fila = df_all[df_all["ocid"] == ocid_elegido]
                procedimiento = fila["procedimiento"].iloc[0] if not fila.empty else None

                if procedimiento and st.button("Explicar la norma aplicable"):
                    get_tarea1_engine_ready()
                    pregunta_t1 = (
                        f"¿Qué es el procedimiento de selección \"{procedimiento}\" y "
                        "qué reglas lo rigen según la Ley N.° 32069?"
                    )
                    with st.spinner(f"Preguntando al motor de la Tarea 1 sobre «{procedimiento}»..."):
                        r1 = engine_tarea1.answer(pregunta_t1)
                    st.info(f"**Procedimiento del proceso {ocid_elegido}:** {procedimiento}")
                    if r1.abstained:
                        st.warning(r1.answer)
                    else:
                        st.success(r1.answer)
                    if r1.sources:
                        st.caption(
                            "Fuente (Tarea 1): "
                            + "; ".join(f"{s.documento}, p. {s.pagina}" for s in r1.sources[:3])
                        )
            mc3.metric("¿Abstención?", "Sí" if result.abstained else "No")

    with tab_tabla:
        cols = ["ocid", "comprador", "departamento", "categoria_es", "monto_pen", "fecha_publicacion", "num_postores", "adjudicado"]
        st.dataframe(df[cols].sort_values("monto_pen", ascending=False), use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar CSV filtrado", df[cols].to_csv(index=False).encode("utf-8"),
            file_name="procesos_filtrados.csv", mime="text/csv",
        )

    with tab_dist:
        col_a, col_b = st.columns(2)
        with col_a:
            por_cat = df.groupby("categoria_es")["monto_pen"].sum().reset_index()
            st.plotly_chart(px.bar(por_cat, x="categoria_es", y="monto_pen", title="Monto total por categoría"), use_container_width=True)
        with col_b:
            df["mes"] = df["fecha_publicacion"].dt.to_period("M").astype(str)
            por_mes = df.groupby("mes")["ocid"].count().reset_index(name="procesos")
            st.plotly_chart(px.bar(por_mes, x="mes", y="procesos", title="Procesos por mes"), use_container_width=True)

    with tab_calidad:
        st.markdown(load_report("data_quality_report.md"))
        st.markdown(load_report("risk_report.md"))
        st.markdown(load_report("retrieval_eval_report.md"))
