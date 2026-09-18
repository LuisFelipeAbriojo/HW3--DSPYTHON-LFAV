"""Interfaz común de embeddings con dos implementaciones (Fase 2 / Fase 4).

Cambiar de modelo es un cambio de configuración (config.yaml), no de código:
ambas clases exponen el mismo contrato `embed_queries` / `embed_passages`.

Modelo local elegido: intfloat/multilingual-e5-base.
- Documentación del modelo: requiere anteponer "query: " a las preguntas y
  "passage: " a los fragmentos indexados (asimetría query/passage), y trunca
  a 512 tokens de entrada.
- Por eso el tamaño de chunk (Fase 2) se elige en caracteres pero se valida
  contra ese límite de tokens (ver compare_chunk_sizes.py): ~1200 caracteres
  de texto legal en español ronda 250-320 tokens con el tokenizer de este
  modelo, con margen holgado bajo 512.
"""
from abc import ABC, abstractmethod


class EmbeddingModel(ABC):
    name: str
    dimension: int

    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        ...


class LocalEmbeddings(EmbeddingModel):
    """sentence-transformers, corre en CPU. Requiere prefijos query:/passage:
    y trunca a max_seq_length tokens (ambos documentados por el modelo)."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_embedding_dimension()
        self.max_seq_length = self._model.max_seq_length

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"query: {t}" for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {t}" for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True).tolist()

    def count_tokens(self, text: str) -> int:
        return len(self._model.tokenizer.encode(text))


class OpenAIEmbeddings(EmbeddingModel):
    """text-embedding-3-small, usada solo para la comparación obligatoria
    de la Fase 4. No lleva prefijos especiales de query/passage (a
    diferencia del modelo local): se documenta explícitamente porque es
    justo el tipo de diferencia entre familias de modelos que la Fase 2
    pide revisar."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        import os
        from openai import OpenAI

        self.name = model_name
        self.dimension = 1536
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def _embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self.name, input=texts)
        return [d.embedding for d in resp.data]

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)
