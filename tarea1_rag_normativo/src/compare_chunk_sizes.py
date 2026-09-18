"""Comparación de configuraciones de chunking con evidencia (Fase 2).

No es la evaluación completa de la Fase 4 (eso corre contra el índice real
en ChromaDB con las 20 preguntas definitivas). Aquí se usa el eval set
provisional (eval/preguntas.csv, solo las in_domain) para decidir tamaño de
chunk/overlap ANTES de construir el índice, comparando Recall@1/@3/@5 con
similitud coseno pura en memoria (numpy), sin Chroma ni LLM de por medio.
"""
import csv
from pathlib import Path

import numpy as np

from chunk import build_chunks, load_pages
from documents import PROCESSED_DIR
from embeddings import LocalEmbeddings

EVAL_PATH = Path(__file__).resolve().parent.parent / "eval" / "preguntas.csv"


def load_eval_questions():
    with EVAL_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["tipo"] == "in_domain"]


def recall_at_k(fragments, embeddings, model, questions, ks=(1, 3, 5)):
    query_vecs = np.array(model.embed_queries([q["pregunta"] for q in questions]))
    frag_matrix = np.array(embeddings)
    sims = query_vecs @ frag_matrix.T  # normalizados -> producto punto = coseno

    hits = {k: 0 for k in ks}
    for i, q in enumerate(questions):
        expected_pages = {int(p) for p in q["paginas_esperadas"].split(",") if p}
        order = np.argsort(-sims[i])
        for k in ks:
            top_k = order[:k]
            if any(fragments[j]["pagina"] in expected_pages for j in top_k):
                hits[k] += 1
    n = len(questions)
    return {k: hits[k] / n for k in ks}


def evaluate_config(pages, model, size, overlap, questions):
    fragments = build_chunks(pages, size, overlap)
    passages = [f["texto"] for f in fragments]
    embeddings = model.embed_passages(passages)
    lengths = [len(f["texto"]) for f in fragments]
    token_counts = [model.count_tokens(p) for p in passages]
    recall = recall_at_k(fragments, embeddings, model, questions)
    return {
        "size": size,
        "overlap": overlap,
        "n_fragmentos": len(fragments),
        "long_prom_chars": sum(lengths) / len(lengths),
        "tokens_max": max(token_counts),
        "tokens_prom": sum(token_counts) / len(token_counts),
        "excede_512_tokens": sum(1 for t in token_counts if t > 512),
        "recall": recall,
    }


def main():
    pages = load_pages()
    questions = load_eval_questions()
    model = LocalEmbeddings()

    configs = [(800, 100), (1200, 150), (1800, 250)]
    results = [evaluate_config(pages, model, s, o, questions) for s, o in configs]

    lines = ["# Comparación de tamaño de chunk (evidencia, Fase 2)\n"]
    lines.append(f"Eval set provisional: {len(questions)} preguntas in-domain (`eval/preguntas.csv`).\n")
    lines.append("| size | overlap | # fragmentos | long. prom (chars) | tokens prom | tokens máx | >512 tokens | Recall@1 | Recall@3 | Recall@5 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        rec = r["recall"]
        lines.append(
            f"| {r['size']} | {r['overlap']} | {r['n_fragmentos']} | {r['long_prom_chars']:.0f} | "
            f"{r['tokens_prom']:.0f} | {r['tokens_max']} | {r['excede_512_tokens']} | "
            f"{rec[1]:.2f} | {rec[3]:.2f} | {rec[5]:.2f} |"
        )

    out_path = PROCESSED_DIR / "chunk_size_comparison.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nGuardado: {out_path}")


if __name__ == "__main__":
    main()
