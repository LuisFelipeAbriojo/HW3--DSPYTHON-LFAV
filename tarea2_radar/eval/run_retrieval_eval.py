"""Evaluación de recuperación del RAG híbrido (Fase 3), sin llamar al LLM.

Mide Recall@k sobre las preguntas con procesos relevantes conocidos, y
valida por separado el caso sin resultados esperados (el filtro estructurado
no debe devolver nada, o el umbral debe llevar a abstención).

También reporta si el umbral de 0.78 heredado de la Tarea 1 transfiere bien
a este corpus (según el enunciado, hay que comprobarlo y recalibrar si no).
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tarea1_rag_normativo" / "src"))

from embeddings import LocalEmbeddings  # noqa: E402
from index import get_collection  # noqa: E402
from query_parser import parse as parse_query  # noqa: E402

EVAL_PATH = Path(__file__).resolve().parent / "preguntas.csv"


def load_questions():
    with EVAL_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_where(filtros: dict) -> dict | None:
    clauses = []
    if filtros.get("departamento"):
        clauses.append({"departamento": {"$eq": filtros["departamento"]}})
    if filtros.get("monto"):
        op, value = filtros["monto"]
        clauses.append({"monto_pen": {"$gte" if op == "gte" else "$lte": value}})
        clauses.append({"monto_valido": {"$eq": True}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def main():
    rows = load_questions()
    collection = get_collection()
    model = LocalEmbeddings()

    ks = (1, 3, 5)
    hits = {k: 0 for k in ks}
    lines = ["# Evaluación de recuperación híbrida (sin LLM) — Tarea 2, Fase 3\n"]
    lines.append("| id | filtros aplicados | similitud top-1 | rank del primer ocid relevante | resultado |")
    lines.append("|---|---|---|---|---|")

    con_relevantes = [r for r in rows if r["ocids_relevantes"]]
    sin_relevantes = [r for r in rows if not r["ocids_relevantes"]]

    for row in rows:
        filtros = parse_query(row["pregunta"])
        where = build_where(filtros)
        vec = model.embed_queries([row["pregunta"]])[0]
        res = collection.query(query_embeddings=[vec], n_results=5, where=where)
        ocids_retrieved = [m["ocid"] for m in res["metadatas"][0]]
        sims = [1 - d for d in res["distances"][0]]
        top1 = sims[0] if sims else None

        if row["ocids_relevantes"]:
            expected = set(row["ocids_relevantes"].split(";"))
            rank = next((i + 1 for i, o in enumerate(ocids_retrieved) if o in expected), None)
            for k in ks:
                if rank is not None and rank <= k:
                    hits[k] += 1
            resultado = f"rank {rank}" if rank else "no encontrado en top-5"
        else:
            resultado = "sin resultados (correcto)" if not ocids_retrieved else f"{len(ocids_retrieved)} resultados inesperados"

        top1_str = f"{top1:.3f}" if top1 is not None else "n/a"
        lines.append(
            f"| {row['id']} | depto={filtros['departamento']}, monto={filtros['monto']} | "
            f"{top1_str} | - | {resultado} |"
        )

    n = len(con_relevantes)
    lines.append(f"\n## Recall@k sobre {n} preguntas con procesos relevantes conocidos\n")
    lines.append("| k | Recall@k |")
    lines.append("|---|---|")
    for k in ks:
        lines.append(f"| {k} | {hits[k]/n:.2f} |")

    lines.append(f"\n{len(sin_relevantes)} pregunta(s) sin procesos relevantes esperados (prueban abstención/filtro vacío), ver tabla arriba.\n")

    out_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "retrieval_eval_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nGuardado: {out_path}")


if __name__ == "__main__":
    main()
