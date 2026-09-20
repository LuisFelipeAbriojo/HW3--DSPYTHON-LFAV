"""Índice del RAG híbrido (Fase 3): embeddings semánticos de la DESCRIPCIÓN
del proceso + metadata estructurada (departamento, monto, fecha, categoría,
comprador, ocid) para filtrar.

Reusa el mismo modelo de embeddings de la Tarea 1 (`LocalEmbeddings`) en
vez de duplicar el código -- se importa directamente desde
`tarea1_rag_normativo/src`, que es justamente el "engine" que el enunciado
pide reutilizar para la Tarea 2.
"""
import sys
from pathlib import Path

import chromadb
import pandas as pd

TAREA1_SRC = Path(__file__).resolve().parent.parent.parent / "tarea1_rag_normativo" / "src"
sys.path.insert(0, str(TAREA1_SRC))

from embeddings import LocalEmbeddings  # noqa: E402

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
CHROMA_DIR = str(Path(__file__).resolve().parent.parent / "chroma_db")
COLLECTION_NAME = "procesos_contratacion"


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def build_index(df: pd.DataFrame, model: LocalEmbeddings, batch_size: int = 64):
    """IDs = ocid (único por definición, ver Fase 1) -> upsert es
    idempotente igual que en la Tarea 1."""
    collection = get_collection()

    df = df[df["descripcion_valida"]].copy()
    existing_ids = set(collection.get(ids=df["ocid"].tolist())["ids"])
    pending = df[~df["ocid"].isin(existing_ids)]
    print(f"Procesos con descripción válida: {len(df)} — ya indexados: {len(existing_ids)} — pendientes: {len(pending)}")

    for i in range(0, len(pending), batch_size):
        batch = pending.iloc[i : i + batch_size]
        vectors = model.embed_passages(batch["descripcion"].tolist())
        metadatas = []
        for _, row in batch.iterrows():
            metadatas.append(
                {
                    "ocid": row["ocid"],
                    "comprador": str(row["comprador"]),
                    "departamento": str(row["departamento"]) if pd.notna(row["departamento"]) else "SIN_UBICAR",
                    "categoria": str(row["categoria"]),
                    "monto_pen": float(row["monto_pen"]) if pd.notna(row["monto_pen"]) else 0.0,
                    "monto_valido": bool(row["monto_valido"]),
                    "fecha_publicacion": str(row["fecha_publicacion"]),
                    "mes_origen": str(row["mes_origen"]),
                }
            )
        collection.upsert(
            ids=batch["ocid"].tolist(),
            embeddings=vectors,
            documents=batch["descripcion"].tolist(),
            metadatas=metadatas,
        )
        print(f"  indexados {min(i + batch_size, len(pending))}/{len(pending)}")

    print(f"Colección '{COLLECTION_NAME}' -> {collection.count()} procesos totales")
    return collection


def main():
    df = pd.read_csv(PROCESSED_DIR / "procesos.csv")
    model = LocalEmbeddings()
    build_index(df, model)


if __name__ == "__main__":
    main()
