"""Comparación obligatoria de embeddings (Fase 4): mismo corpus de 347
fragmentos, dos índices ChromaDB independientes (uno por modelo), mismas 20
preguntas del eval set. Reporta Recall@k, tiempo de indexación, costo y
latencia promedio de consulta para cada uno.
"""
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from build_index import build_index, get_collection  # noqa: E402
from chunk import build_chunks, load_pages  # noqa: E402
from costs import EMBEDDING_PRICING  # noqa: E402
from documents import DOCS, PROCESSED_DIR  # noqa: E402
from embeddings import LocalEmbeddings, OpenAIEmbeddings  # noqa: E402

EVAL_PATH = Path(__file__).resolve().parent / "preguntas.csv"
DOC_ID_TO_NAME = {d["doc_id"]: d["documento"] for d in DOCS}


def load_questions():
    with EVAL_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expected_pairs(row) -> set[tuple[str, int]]:
    if not row["documento_esperado"]:
        return set()
    doc_ids = row["documento_esperado"].split(";")
    page_groups = row["paginas_esperadas"].split(";")
    pairs = set()
    for doc_id, pages in zip(doc_ids, page_groups):
        name = DOC_ID_TO_NAME[doc_id]
        for p in pages.split(","):
            pairs.add((name, int(p)))
    return pairs


def recall_at_k(collection, model, in_domain_rows, ks=(1, 3, 5)):
    hits = {k: 0 for k in ks}
    for row in in_domain_rows:
        expected = expected_pairs(row)
        vec = model.embed_queries([row["pregunta"]])[0]
        res = collection.query(query_embeddings=[vec], n_results=5)
        pairs = [(m["documento"], m["pagina"]) for m in res["metadatas"][0]]
        rank = next((i + 1 for i, p in enumerate(pairs) if p in expected), None)
        for k in ks:
            if rank is not None and rank <= k:
                hits[k] += 1
    n = len(in_domain_rows)
    return {k: hits[k] / n for k in ks}


def avg_query_latency(model, questions, n_results=5, collection=None):
    times = []
    for row in questions:
        t0 = time.perf_counter()
        vec = model.embed_queries([row["pregunta"]])[0]
        if collection is not None:
            collection.query(query_embeddings=[vec], n_results=n_results)
        times.append(time.perf_counter() - t0)
    return sum(times) / len(times)


def evaluate(name: str, model, collection_name: str, fragments, rows):
    print(f"\n=== {name} ===")
    t0 = time.perf_counter()
    collection = build_index(fragments, model, collection_name=collection_name)
    indexing_time = time.perf_counter() - t0

    in_domain = [r for r in rows if r["tipo"] == "in_domain"]
    recall = recall_at_k(collection, model, in_domain)
    latency = avg_query_latency(model, rows, collection=collection)

    if isinstance(model, OpenAIEmbeddings):
        cost = model.total_tokens_used / 1_000_000 * EMBEDDING_PRICING[model.name]
    else:
        cost = 0.0

    return {
        "modelo": name,
        "dimension": model.dimension,
        "tiempo_indexacion_s": indexing_time,
        "costo_usd": cost,
        "latencia_prom_query_s": latency,
        "recall": recall,
    }


def main():
    pages = load_pages()
    fragments = build_chunks(pages, size=1200, overlap=150)
    rows = load_questions()

    local_model = LocalEmbeddings()
    openai_model = OpenAIEmbeddings()

    results = [
        evaluate("Local (intfloat/multilingual-e5-base)", local_model, "ley_contrataciones_cmp_local", fragments, rows),
        evaluate("API (text-embedding-3-small)", openai_model, "ley_contrataciones_cmp_openai", fragments, rows),
    ]

    lines = ["# Comparación de embeddings: local vs. API (Fase 4)\n"]
    lines.append(f"Mismo corpus ({len(fragments)} fragmentos), mismas 20 preguntas del eval set.\n")
    lines.append("| Modelo | Dimensión | Tiempo de indexación (s) | Costo (USD) | Latencia prom. por consulta (s) | Recall@1 | Recall@3 | Recall@5 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in results:
        rec = r["recall"]
        lines.append(
            f"| {r['modelo']} | {r['dimension']} | {r['tiempo_indexacion_s']:.1f} | "
            f"{r['costo_usd']:.5f} | {r['latencia_prom_query_s']:.3f} | "
            f"{rec[1]:.2f} | {rec[3]:.2f} | {rec[5]:.2f} |"
        )

    out_path = PROCESSED_DIR / "embeddings_comparison.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nGuardado: {out_path}")


if __name__ == "__main__":
    main()
