"""Validación y normalización territorial (Fase 2).

Por cada regla: cuántos registros se marcaron y qué se hizo (corregido,
descartado, o mantenido con advertencia) — nunca se descarta en silencio.
"""
from pathlib import Path

import pandas as pd

from records import load_all_months
from territory import normalize_department

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def validate_and_normalize(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    report = []
    n_before = len(df)

    # 1. Duplicados: mismo ocid repetido (dentro de un mes o entre meses).
    dup_mask = df.duplicated(subset="ocid", keep="first")
    n_dup = int(dup_mask.sum())
    report.append(
        {
            "regla": "Registros repetidos (mismo ocid)",
            "flagged": n_dup,
            "accion": "eliminado (se conserva la primera aparición)" if n_dup else "ninguno encontrado — los 3 archivos mensuales no se superponen (0 ocids en común entre meses) y cada records.csv ya es 1 fila por ocid",
        }
    )
    df = df[~dup_mask].copy()

    # 2. Monto faltante o en cero.
    monto_faltante = df["monto"].isna()
    monto_cero = (df["monto"] == 0) & ~monto_faltante
    df["monto_valido"] = ~(monto_faltante | monto_cero)
    report.append(
        {
            "regla": "Monto faltante",
            "flagged": int(monto_faltante.sum()),
            "accion": "mantenido con advertencia (monto_valido=False); se excluye de agregados monetarios en el dashboard",
        }
    )
    report.append(
        {
            "regla": "Monto en cero",
            "flagged": int(monto_cero.sum()),
            "accion": "mantenido con advertencia (monto_valido=False) — puede ser válido (p.ej. convenio marco sin monto referencial), pero se excluye de KPIs de monto",
        }
    )

    # 3. Descripción faltante.
    desc_vacia = df["descripcion"].isna() | (df["descripcion"].astype(str).str.strip() == "")
    df["descripcion_valida"] = ~desc_vacia
    df["descripcion"] = df["descripcion"].fillna(df["titulo"])
    report.append(
        {
            "regla": "Descripción faltante",
            "flagged": int(desc_vacia.sum()),
            "accion": "corregido: se usa el título del proceso como respaldo; marcado en descripcion_valida=False para no indexarlo como si fuera una descripción real en el RAG",
        }
    )

    # 4. Ubicación: el campo "region" del origen en realidad trae la
    # PROVINCIA en el 54% de los casos (verificado, ver README) -- por eso
    # se normaliza a partir de "departamento_raw", no de "region".
    df["departamento"] = df["departamento_raw"].apply(normalize_department)
    sin_ubicar = df["departamento"].isna()
    report.append(
        {
            "regla": "Departamento no identificable (ni coincide con departamento ni con provincia conocida)",
            "flagged": int(sin_ubicar.sum()),
            "accion": "mantenido con advertencia (departamento=NaN); excluido del choropleth pero visible en la tabla y el conteo total",
        }
    )

    # 5. Inconsistencias de acentos/mayúsculas en texto libre (comprador):
    # se reporta la cardinalidad antes/después de una normalización simple,
    # sin alterar el valor mostrado (es solo diagnóstico).
    variantes_antes = df["comprador"].nunique()
    normalizado = df["comprador"].astype(str).str.upper().str.strip()
    variantes_despues = normalizado.nunique()
    report.append(
        {
            "regla": "Variantes de mayúsculas/espacios en nombre del comprador",
            "flagged": int(variantes_antes - variantes_despues),
            "accion": f"diagnóstico ({variantes_antes} valores únicos crudos -> {variantes_despues} tras normalizar mayúsculas/espacios); no se sobrescribe el nombre mostrado, se usa solo para deduplicar el ranking de compradores en la Fase 5",
        }
    )

    n_after = len(df)
    report.append({"regla": "TOTAL", "flagged": f"{n_before} -> {n_after} filas", "accion": "una fila por ocid"})
    return df, report


def main():
    df = load_all_months(months=["06", "07", "08"])
    n_raw = len(df)
    df, report = validate_and_normalize(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = PROCESSED_DIR / "procesos.csv"
    df.to_csv(out_csv, index=False)

    lines = ["# Reporte de calidad de datos — Tarea 2, Fase 2\n"]
    lines.append(f"Filas crudas (unión de 3 meses, antes de deduplicar): **{n_raw}**")
    lines.append(f"Filas finales (una por proceso de contratación): **{len(df)}**\n")
    lines.append("| Regla | Registros marcados | Acción |")
    lines.append("|---|---|---|")
    for r in report:
        lines.append(f"| {r['regla']} | {r['flagged']} | {r['accion']} |")

    lines.append("\n## Distribución por departamento (tras normalizar)\n")
    counts = df["departamento"].value_counts(dropna=False)
    lines.append("| Departamento | Procesos |")
    lines.append("|---|---|")
    for dept, n in counts.items():
        lines.append(f"| {dept if pd.notna(dept) else '(sin ubicar)'} | {n} |")

    out_md = PROCESSED_DIR / "data_quality_report.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:20]))
    print(f"\nGuardado: {out_csv}")
    print(f"Guardado: {out_md}")


if __name__ == "__main__":
    main()
