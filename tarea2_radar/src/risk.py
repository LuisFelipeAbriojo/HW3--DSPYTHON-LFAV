"""Indicador de riesgo: postor único entre procesos adjudicados (Fase 5).

Un proceso está "adjudicado" si tiene al menos una buena pro registrada
(existe en com_awards.csv de algún mes) -- records.csv por sí solo no trae
un campo de estado utilizable (`compiledRelease/tag` es siempre "compiled",
el tag genérico de un record OCDS, no la etapa del proceso).

Este es un indicador de la literatura de integridad en contrataciones
(ver Open Contracting Partnership, "Red Flags in Public Procurement", 2024;
Ojo Público, "Funes, un algoritmo contra la corrupción"): un solo postor en
un proceso competitivo reduce la presión competitiva sobre el precio y
puede señalar direccionamiento, pero por sí solo NO es evidencia de
irregularidad -- puede deberse a mercados con pocos proveedores
especializados, montos poco atractivos, plazos cortos, etc. Es una señal
para mirar más de cerca, no una acusación. No se publican nombres de
personas individuales (los "compradores" aquí son entidades públicas, no
personas).
"""
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

MIN_PROCESOS_ADJUDICADOS_POR_COMPRADOR = 5
# Justificación: con menos de 5 procesos adjudicados, un comprador con 1/1
# postor único ya muestra 100% de la métrica -- ruido estadístico, no señal.
# 5 es el mínimo que usamos para que el ranking no esté dominado por
# compradores con muy poca actividad.


def load_awarded_ocids(months: list[str], year: str = "2026", source: str = "seace_v3") -> set[str]:
    ocids = set()
    for m in months:
        zip_path = RAW_DIR / f"{year}-{m}_{source}_csv.zip"
        with ZipFile(zip_path) as z, z.open("com_awards.csv") as f:
            df = pd.read_csv(f, usecols=["ocid"])
        ocids.update(df["ocid"])
    return ocids


def compute_risk(df: pd.DataFrame, awarded_ocids: set[str]) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["adjudicado"] = df["ocid"].isin(awarded_ocids)
    adjudicados = df[df["adjudicado"] & df["num_postores"].notna()].copy()
    adjudicados["postor_unico"] = adjudicados["num_postores"] == 1

    por_departamento = (
        adjudicados.groupby("departamento")["postor_unico"]
        .agg(procesos_adjudicados="count", pct_postor_unico="mean")
        .reset_index()
        .sort_values("pct_postor_unico", ascending=False)
    )

    por_comprador = (
        adjudicados.groupby("comprador")["postor_unico"]
        .agg(procesos_adjudicados="count", pct_postor_unico="mean")
        .reset_index()
    )
    por_comprador = por_comprador[
        por_comprador["procesos_adjudicados"] >= MIN_PROCESOS_ADJUDICADOS_POR_COMPRADOR
    ].sort_values("pct_postor_unico", ascending=False)

    resumen = {
        "total_adjudicados": len(adjudicados),
        "pct_postor_unico_global": adjudicados["postor_unico"].mean(),
    }
    return df, {"por_departamento": por_departamento, "por_comprador": por_comprador, "resumen": resumen}


def main():
    df = pd.read_csv(PROCESSED_DIR / "procesos.csv")
    awarded = load_awarded_ocids(months=["06", "07", "08"])
    df, tables = compute_risk(df, awarded)

    df.to_csv(PROCESSED_DIR / "procesos.csv", index=False)  # agrega columna 'adjudicado'
    tables["por_departamento"].to_csv(PROCESSED_DIR / "riesgo_por_departamento.csv", index=False)
    tables["por_comprador"].head(10).to_csv(PROCESSED_DIR / "riesgo_top10_compradores.csv", index=False)

    lines = ["# Indicador de riesgo: postor único (Fase 5)\n"]
    lines.append(
        "**Un solo postor es una señal para mirar más de cerca, no evidencia de "
        "irregularidad.** Puede deberse a mercados con pocos proveedores "
        "especializados, montos poco atractivos, o plazos cortos. No se "
        "publican nombres de personas individuales — los compradores aquí "
        "son entidades públicas.\n"
    )
    r = tables["resumen"]
    lines.append(f"- Procesos adjudicados (con postores registrados): **{r['total_adjudicados']}**")
    lines.append(f"- % con postor único (global): **{r['pct_postor_unico_global']:.1%}**\n")

    lines.append(f"## Top 10 compradores por % de postor único (mínimo {MIN_PROCESOS_ADJUDICADOS_POR_COMPRADOR} procesos adjudicados)\n")
    lines.append("| Comprador | Procesos adjudicados | % postor único |")
    lines.append("|---|---|---|")
    for _, row in tables["por_comprador"].head(10).iterrows():
        lines.append(f"| {row['comprador']} | {row['procesos_adjudicados']} | {row['pct_postor_unico']:.1%} |")

    lines.append("\n## Por departamento\n")
    lines.append("| Departamento | Procesos adjudicados | % postor único |")
    lines.append("|---|---|---|")
    for _, row in tables["por_departamento"].iterrows():
        lines.append(f"| {row['departamento']} | {row['procesos_adjudicados']} | {row['pct_postor_unico']:.1%} |")

    (PROCESSED_DIR / "risk_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:20]))
    print(f"\nGuardado: {PROCESSED_DIR / 'risk_report.md'}")


if __name__ == "__main__":
    main()
