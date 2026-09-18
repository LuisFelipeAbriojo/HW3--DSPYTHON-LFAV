"""Evaluación de recuperación (Fase 4, parte sin LLM).

Calcula Recall@1/3/5 y hace el sweep de umbral de abstención usando
ÚNICAMENTE el índice de ChromaDB y el modelo de embeddings local — nunca
llama al LLM generador. Por eso esta evaluación no cuesta nada y se puede
correr en cada cambio del pipeline (candidato natural para un check en CI).

Qué mide cada cosa:
- Recall@k: si el fragmento correcto (misma página del documento esperado)
  aparece entre los k mejores resultados. Evalúa la calidad de la
  RECUPERACIÓN (embeddings + índice), no la respuesta final del LLM.
- Tasa de abstención (correcta/incorrecta) a cada umbral: evalúa la
  DECISIÓN de cuándo no llamar al LLM. Un umbral demasiado bajo deja pasar
  preguntas fuera de dominio al generador (riesgo de alucinar con
  confianza); demasiado alto abstiene incluso en preguntas respondibles.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from build_index import get_collection  # noqa: E402
from documents import DOCS  # noqa: E402
from embeddings import LocalEmbeddings  # noqa: E402

EVAL_PATH = Path(__file__).resolve().parent / "preguntas.csv"
DOC_ID_TO_NAME = {d["doc_id"]: d["documento"] for d in DOCS}


def load_questions():
    with EVAL_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expected_pairs(row) -> set[tuple[str, int]]:
    """(documento, pagina) esperados; soporta múltiples documentos separados
    por ';' (caso de versiones, p.ej. q11: ley + decreto modificatorio)."""
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


def retrieve(collection, model, question: str, n_results: int = 5):
    vec = model.embed_queries([question])[0]
    res = collection.query(query_embeddings=[vec], n_results=n_results)
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    sims = [1 - d for d in dists]  # hnsw:space=cosine -> distancia = 1 - similitud
    return metas, sims


def recall_report(rows, collection, model):
    in_domain = [r for r in rows if r["tipo"] == "in_domain"]
    ks = (1, 3, 5)
    hits = {k: 0 for k in ks}
    per_question = []

    for row in in_domain:
        expected = expected_pairs(row)
        metas, sims = retrieve(collection, model, row["pregunta"], n_results=5)
        retrieved_pairs = [(m["documento"], m["pagina"]) for m in metas]
        first_hit_rank = next(
            (i + 1 for i, p in enumerate(retrieved_pairs) if p in expected), None
        )
        for k in ks:
            if first_hit_rank is not None and first_hit_rank <= k:
                hits[k] += 1
        per_question.append(
            {"id": row["id"], "categoria": row["categoria"], "rank": first_hit_rank, "top1_sim": sims[0]}
        )

    n = len(in_domain)
    recall = {k: hits[k] / n for k in ks}
    return recall, per_question


def threshold_sweep(rows, collection, model, thresholds):
    top1_sim = {}
    for row in rows:
        _, sims = retrieve(collection, model, row["pregunta"], n_results=1)
        top1_sim[row["id"]] = sims[0]

    in_domain_ids = {r["id"] for r in rows if r["tipo"] == "in_domain"}
    out_domain_ids = {r["id"] for r in rows if r["tipo"] == "out_domain"}

    sweep = []
    for t in thresholds:
        abstained = {qid for qid, s in top1_sim.items() if s < t}
        incorrect_abstentions = len(abstained & in_domain_ids)  # in-domain que no debería abstenerse
        correct_abstentions = len(abstained & out_domain_ids)  # out-of-domain correctamente abstenido
        false_positives = len(out_domain_ids) - correct_abstentions  # fuera de dominio que SÍ pasaría al LLM
        sweep.append(
            {
                "umbral": t,
                "abstenciones_correctas": correct_abstentions,
                "abstenciones_incorrectas": incorrect_abstentions,
                "fuera_dominio_sin_abstener": false_positives,
            }
        )
    return sweep, top1_sim


def main():
    rows = load_questions()
    collection = get_collection()
    model = LocalEmbeddings()

    recall, per_question = recall_report(rows, collection, model)

    thresholds = [round(x, 2) for x in np.arange(0.30, 0.76, 0.05)] + [
        round(x, 2) for x in np.arange(0.76, 0.90, 0.01)
    ]
    sweep, top1_sim = threshold_sweep(rows, collection, model, thresholds)

    lines = ["# Evaluación de recuperación (sin LLM) — Fase 4\n"]
    lines.append(f"## Recall@k sobre {sum(1 for r in rows if r['tipo']=='in_domain')} preguntas in-domain\n")
    lines.append("| k | Recall@k |")
    lines.append("|---|---|")
    for k, v in recall.items():
        lines.append(f"| {k} | {v:.2f} |")

    lines.append("\n### Detalle por pregunta\n")
    lines.append("| id | categoría | rank del fragmento correcto | similitud top-1 |")
    lines.append("|---|---|---|---|")
    for pq in per_question:
        lines.append(f"| {pq['id']} | {pq['categoria']} | {pq['rank'] or 'no encontrado en top-5'} | {pq['top1_sim']:.3f} |")

    lines.append("\n## Similitud top-1 por pregunta (todas, para el sweep de umbral)\n")
    lines.append("| id | tipo | similitud top-1 |")
    lines.append("|---|---|---|")
    for row in rows:
        lines.append(f"| {row['id']} | {row['tipo']} | {top1_sim[row['id']]:.3f} |")

    lines.append("\n## Sweep de umbral de abstención\n")
    lines.append("| umbral | abstenciones correctas (de 5 fuera de dominio) | abstenciones incorrectas (de 15 in-domain) | fuera de dominio que SÍ pasaría al LLM |")
    lines.append("|---|---|---|---|")
    for s in sweep:
        lines.append(
            f"| {s['umbral']:.2f} | {s['abstenciones_correctas']} | {s['abstenciones_incorrectas']} | {s['fuera_dominio_sin_abstener']} |"
        )

    out_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "retrieval_eval_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nGuardado: {out_path}")


if __name__ == "__main__":
    main()
