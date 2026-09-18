"""Chequeo de fuentes (Fase 1): verifica que cada PDF tenga texto extraible
antes de construir el resto del pipeline.

Para cada documento reporta: numero de paginas, caracteres por pagina,
paginas sin texto extraible, y una muestra del texto para revisar el
orden de lectura. No modifica los PDFs originales (data/raw/ es solo lectura).

Uso:
    .venv/Scripts/python tarea1_rag_normativo/src/source_check.py
"""
import json

import pdfplumber

from documents import DOCS, RAW_DIR, PROCESSED_DIR as REPORT_DIR

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def detect_two_columns(page, gap_threshold: float = 50.0, line_ratio_threshold: float = 0.02) -> bool:
    """Heuristic: group words by their vertical position (`top`) the way
    pdfplumber's extract_text() does, then check the horizontal gap between
    consecutive words within each such "line". A single justified column
    never leaves a gap much bigger than normal word spacing (a few points).
    A page laid out in two columns, once both columns get merged into one
    line by top-alignment, shows a large gap where the first column ends and
    the second begins — that gap is the tell, not just "words appear on both
    halves of the page" (which is also true of any single wide column)."""
    words = page.extract_words()
    if len(words) < 20:
        return False

    lines: dict[int, list] = {}
    for w in words:
        lines.setdefault(round(w["top"]), []).append(w)

    flagged, total = 0, 0
    for ws in lines.values():
        if len(ws) < 2:
            continue
        ws = sorted(ws, key=lambda w: w["x0"])
        max_gap = max(b["x0"] - a["x1"] for a, b in zip(ws, ws[1:]))
        total += 1
        if max_gap > gap_threshold:
            flagged += 1

    return total > 0 and (flagged / total) > line_ratio_threshold


def check_pdf(meta: dict) -> dict:
    path = RAW_DIR / meta["archivo"]
    result = {**meta, "existe": path.exists()}
    if not path.exists():
        return result

    pages_report = []
    empty_pages = []
    two_col_pages = []
    with pdfplumber.open(path) as pdf:
        result["num_paginas"] = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            n_chars = len(text)
            pages_report.append({"pagina": i, "caracteres": n_chars})
            if n_chars < 20:
                empty_pages.append(i)
            if detect_two_columns(page):
                two_col_pages.append(i)

        mid = len(pdf.pages) // 2
        sample_text = (pdf.pages[mid].extract_text() or "")[:600]

    total_chars = sum(p["caracteres"] for p in pages_report)
    result["total_caracteres"] = total_chars
    result["promedio_caracteres_por_pagina"] = round(
        total_chars / max(1, len(pages_report)), 1
    )
    result["paginas_sin_texto"] = empty_pages
    result["paginas_dos_columnas"] = two_col_pages
    result["orden_lectura_ok"] = len(two_col_pages) == 0
    result["paginas_por_pagina"] = pages_report
    result["muestra_pagina_media"] = sample_text
    result["usable"] = len(empty_pages) < len(pages_report)
    return result


def main():
    report = [check_pdf(d) for d in DOCS]

    out_json = REPORT_DIR / "source_check_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Reporte de chequeo de fuentes — Tarea 1, Fase 1",
        "",
        "| Documento | Obligatorio | Páginas | Prom. caracteres/página | Páginas sin texto | Páginas a 2 columnas | ¿Usable? | ¿Orden de lectura OK? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in report:
        lines.append(
            f"| {r['documento']} | {'Sí' if r['obligatorio'] else 'No (opcional)'} | "
            f"{r.get('num_paginas', '-')} | {r.get('promedio_caracteres_por_pagina', '-')} | "
            f"{len(r.get('paginas_sin_texto', []))} | {len(r.get('paginas_dos_columnas', []))} | "
            f"{'Sí' if r.get('usable') else 'NO'} | {'Sí' if r.get('orden_lectura_ok') else 'NO — requiere extracción por columna'} |"
        )
    lines.append("")
    lines.append(
        "**Nota de orden de lectura:** los documentos publicados por El Peruano "
        "(D.S. 001-2026-EF y DL 1715) usan diagramación a dos columnas. "
        "`page.extract_text()` de pdfplumber agrupa palabras por altura (`top`) "
        "en toda la página, por lo que intercala fragmentos de ambas columnas en "
        "una misma línea. La Ley 32069 (fuente gob.pe) es a una sola columna y "
        "no presenta este problema. Ver ejemplo antes/después en la Fase 1 de "
        "limpieza (`clean.py`), donde se extrae cada columna por separado antes "
        "de concatenar."
    )

    lines.append("")
    lines.append("## Muestra de texto (página intermedia) por documento")
    for r in report:
        lines.append(f"\n### {r['documento']}\n")
        lines.append("```")
        lines.append(r.get("muestra_pagina_media", "(sin texto)"))
        lines.append("```")

    out_md = REPORT_DIR / "source_check_report.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines[:8]))
    print(f"\nReporte completo: {out_md}")


if __name__ == "__main__":
    main()
