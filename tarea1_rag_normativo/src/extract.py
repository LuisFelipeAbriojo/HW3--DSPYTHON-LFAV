"""Extracción y limpieza de texto (Fase 1, parte 2).

Cada página se extrae por separado y conserva su número de página desde
este primer paso (nunca se une todo el documento en un solo string antes de
trocear: eso es exactamente lo que perdería la trazabilidad de citas).

Reglas de limpieza documentadas (con ejemplo antes/después en el reporte
generado por `main()`):

1. Cabecera de El Peruano ("El Peruano / <fecha> NORMAS LEGALES <n>") pegada
   al cuerpo: se detectó (ver source_check.py) que ocupa siempre la franja
   superior de la página (top < HEADER_CUTOFF_PT), por encima de donde
   arranca el cuerpo en dos columnas. Se recorta geométricamente esa franja
   antes de extraer texto, en vez de intentar adivinarla con regex sobre el
   string ya mezclado.
2. Documentos a dos columnas (D.S. 001-2026-EF, DL 1715): extraer la página
   completa con pdfplumber concatena ambas columnas línea por línea según su
   altura (`top`), intercalando frases de columnas distintas. Se extrae cada
   columna por separado (recorte izquierdo/derecho a partir del punto medio
   del ancho de página) y se concatenan columna izquierda + columna derecha.
3. Espacios y saltos de línea múltiples se colapsan; no se reconstruyen
   palabras partidas por guion porque no se observó ese patrón en estos
   documentos (se revisó explícitamente, ver reporte).
"""
import json
import re

import pdfplumber

from documents import DOCS, RAW_DIR, PROCESSED_DIR

HEADER_CUTOFF_PT = 72.0  # ver documents.py / source_check_report: cabecera vive en top ~61-64


def _clean_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_single_column_page(page) -> str:
    return _clean_whitespace(page.extract_text() or "")


def extract_two_column_page(page) -> str:
    mid_x = page.width / 2
    left = page.crop((0, HEADER_CUTOFF_PT, mid_x, page.height))
    right = page.crop((mid_x, HEADER_CUTOFF_PT, page.width, page.height))
    left_text = left.extract_text() or ""
    right_text = right.extract_text() or ""
    return _clean_whitespace(left_text + "\n" + right_text)


def extract_document(meta: dict) -> list[dict]:
    path = RAW_DIR / meta["archivo"]
    pages_out = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            if meta["dos_columnas"]:
                texto = extract_two_column_page(page)
            else:
                texto = extract_single_column_page(page)
            pages_out.append(
                {
                    "doc_id": meta["doc_id"],
                    "documento": meta["documento"],
                    "version": meta["version"],
                    "fuente": meta["fuente"],
                    "pagina": i,
                    "texto": texto,
                }
            )
    return pages_out


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "pages.jsonl"

    before_after = []
    all_pages = []
    for meta in DOCS:
        pages = extract_document(meta)
        all_pages.extend(pages)

        if meta["dos_columnas"]:
            # ejemplo antes/después usando la primera página del documento
            with pdfplumber.open(RAW_DIR / meta["archivo"]) as pdf:
                naive = _clean_whitespace(pdf.pages[0].extract_text() or "")
            before_after.append(
                {
                    "documento": meta["documento"],
                    "antes_naive": naive[:500],
                    "despues_por_columna": pages[0]["texto"][:500],
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for row in all_pages:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report_lines = ["# Antes / después de la extracción por columna\n"]
    for ba in before_after:
        report_lines.append(f"## {ba['documento']}\n")
        report_lines.append("**Antes (extract_text ingenuo, columnas mezcladas):**\n")
        report_lines.append(f"```\n{ba['antes_naive']}\n```\n")
        report_lines.append("**Después (columna izquierda + columna derecha, en orden):**\n")
        report_lines.append(f"```\n{ba['despues_por_columna']}\n```\n")

    (PROCESSED_DIR / "cleaning_before_after.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    total_chars = sum(len(p["texto"]) for p in all_pages)
    print(f"Páginas extraídas: {len(all_pages)} — {total_chars:,} caracteres totales")
    print(f"Guardado: {out_path}")
    print(f"Reporte antes/después: {PROCESSED_DIR / 'cleaning_before_after.md'}")

    _write_quality_report(all_pages)


def _write_quality_report(all_pages: list[dict]):
    lines = ["# Reporte de calidad de extracción (post-limpieza) — Fase 1\n"]
    lines.append("| Documento | Páginas | Caracteres totales | Prom. caracteres/página |")
    lines.append("|---|---|---|---|")
    for meta in DOCS:
        pages = [p for p in all_pages if p["doc_id"] == meta["doc_id"]]
        chars = sum(len(p["texto"]) for p in pages)
        avg = round(chars / max(1, len(pages)), 1)
        lines.append(f"| {meta['documento']} | {len(pages)} | {chars:,} | {avg} |")
        descartadas = [p["pagina"] for p in pages if len(p["texto"]) < 20]
        if descartadas:
            lines.append(f"  - Páginas descartadas por falta de texto: {descartadas}")

    lines.append("\n## Muestra de página intermedia (post-limpieza)\n")
    for meta in DOCS:
        pages = [p for p in all_pages if p["doc_id"] == meta["doc_id"]]
        mid = pages[len(pages) // 2]
        lines.append(f"### {meta['documento']} (página {mid['pagina']})\n")
        lines.append(f"```\n{mid['texto'][:700]}\n```\n")

    (PROCESSED_DIR / "extraction_quality_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"Reporte de calidad: {PROCESSED_DIR / 'extraction_quality_report.md'}")


if __name__ == "__main__":
    main()
