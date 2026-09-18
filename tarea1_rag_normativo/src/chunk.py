"""Chunking (Fase 2): trocea el texto ya limpio en fragmentos.

Decisión de diseño: se trocea PÁGINA POR PÁGINA, nunca a través de todo el
documento concatenado. Así cada fragmento hereda sin ambigüedad la página de
donde salió (dato que ya viene adjunto desde extract.py). El costo es que un
artículo que cruza un salto de página queda partido en dos fragmentos — se
documenta como limitación conocida; el overlap entre fragmentos de una misma
página mitiga la pérdida de contexto dentro de la página, no entre páginas.

IDs estables: `{doc_id}_p{pagina:04d}_c{indice_en_pagina}`. Son deterministas
(no dependen del orden de ejecución), por lo que reconstruir el índice con
`chromadb.upsert` es idempotente: mismos IDs se sobrescriben, no se duplican.
"""
import json
from pathlib import Path

from documents import PROCESSED_DIR


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    step = size - overlap
    while start < len(text):
        chunk = text[start : start + size]
        if chunk.strip():
            chunks.append(chunk)
        if start + size >= len(text):
            break
        start += step
    return chunks


def build_chunks(pages: list[dict], size: int, overlap: int) -> list[dict]:
    fragments = []
    for page in pages:
        pieces = chunk_text(page["texto"], size, overlap)
        for idx, piece in enumerate(pieces):
            fragments.append(
                {
                    "id": f"{page['doc_id']}_p{page['pagina']:04d}_c{idx}",
                    "documento": page["documento"],
                    "version": page["version"],
                    "fuente": page["fuente"],
                    "pagina": page["pagina"],
                    "texto": piece,
                }
            )
    return fragments


def load_pages() -> list[dict]:
    path = PROCESSED_DIR / "pages.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def main(size: int = 1200, overlap: int = 150, out_name: str = "chunks.jsonl"):
    pages = load_pages()
    fragments = build_chunks(pages, size, overlap)

    out_path = PROCESSED_DIR / out_name
    with out_path.open("w", encoding="utf-8") as f:
        for frag in fragments:
            f.write(json.dumps(frag, ensure_ascii=False) + "\n")

    lengths = [len(f["texto"]) for f in fragments]
    print(f"size={size} overlap={overlap} -> {len(fragments)} fragmentos")
    print(f"  longitud: min={min(lengths)} max={max(lengths)} prom={sum(lengths)/len(lengths):.0f}")
    by_doc: dict[str, int] = {}
    for f in fragments:
        by_doc[f["documento"]] = by_doc.get(f["documento"], 0) + 1
    for doc, n in by_doc.items():
        print(f"  {doc}: {n} fragmentos")
    print(f"Guardado: {out_path}")
    return fragments


if __name__ == "__main__":
    main()
