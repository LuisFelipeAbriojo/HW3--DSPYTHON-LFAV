"""Construcción del índice (proceso OFFLINE, Fase 2).

Idempotente y resumible:
- IDs de fragmento estables y deterministas (doc_id + página + índice, ver
  chunk.py) -> `collection.upsert(ids=...)` sobrescribe en vez de duplicar
  si se vuelve a correr sobre los mismos fragmentos.
- Resumible: antes de embeber, se consultan los IDs que ya existen en la
  colección y solo se calculan embeddings para los que faltan. Si el
  proceso se corta a la mitad, la siguiente corrida retoma donde quedó en
  vez de recalcular todo.
- Agregar un documento nuevo no toca los fragmentos de los demás: cada
  fragmento se identifica por su propio doc_id, nunca se reescribe la
  colección completa.
"""
import chromadb

from chunk import main as build_chunks_file, load_pages
from documents import PROCESSED_DIR
from embeddings import LocalEmbeddings

CHROMA_DIR = str(PROCESSED_DIR.parent / "chroma_db")
COLLECTION_NAME = "ley_contrataciones"


def get_collection(name: str = COLLECTION_NAME):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def build_index(fragments: list[dict], model, collection_name: str = COLLECTION_NAME, batch_size: int = 64):
    """`model` es cualquier implementación de `EmbeddingModel` (local o API)
    -- ver embeddings.py. Cambiar de modelo es pasar otra instancia y otro
    `collection_name`, no tocar esta función (Fase 4: comparación local vs
    OpenAI usa exactamente esta misma función con `OpenAIEmbeddings`)."""
    collection = get_collection(collection_name)

    existing_ids = set(collection.get(ids=[f["id"] for f in fragments])["ids"])
    pending = [f for f in fragments if f["id"] not in existing_ids]
    print(f"Fragmentos totales: {len(fragments)} — ya indexados: {len(existing_ids)} — pendientes: {len(pending)}")

    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        vectors = model.embed_passages([f["texto"] for f in batch])
        collection.upsert(
            ids=[f["id"] for f in batch],
            embeddings=vectors,
            documents=[f["texto"] for f in batch],
            metadatas=[
                {
                    "documento": f["documento"],
                    "version": f["version"],
                    "fuente": f["fuente"],
                    "pagina": f["pagina"],
                }
                for f in batch
            ],
        )
        print(f"  indexados {min(i + batch_size, len(pending))}/{len(pending)}")

    print(f"Colección '{collection_name}' -> {collection.count()} fragmentos totales")
    return collection


def main(size: int = 1200, overlap: int = 150):
    pages = load_pages()
    from chunk import build_chunks

    fragments = build_chunks(pages, size, overlap)
    model = LocalEmbeddings()
    build_index(fragments, model)


if __name__ == "__main__":
    main()
