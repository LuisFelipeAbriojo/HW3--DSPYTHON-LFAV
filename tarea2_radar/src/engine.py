"""Motor RAG híbrido de la Tarea 2 (Fase 3).

Misma forma de contrato que el motor de la Tarea 1 (una función `answer`,
resultado estructurado con fuentes/abstención/costo) y, de hecho, reusa
directamente `costs.py` de la Tarea 1 para el logging. La diferencia es
que las condiciones numéricas y territoriales de la pregunta se convierten
en un filtro `where` de ChromaDB ANTES de la búsqueda semántica -- no se
le pide al embedding que entienda "más de un millón" o "en Cusco".
"""
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

TAREA1_SRC = Path(__file__).resolve().parent.parent.parent / "tarea1_rag_normativo" / "src"
sys.path.insert(0, str(TAREA1_SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from costs import CallLog, compute_cost, log_call, now_iso, Timer  # noqa: E402
from embeddings import LocalEmbeddings  # noqa: E402

from index import get_collection  # noqa: E402
from query_parser import parse as parse_query  # noqa: E402

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

load_dotenv(ENV_PATH)


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@dataclass
class ProcessSource:
    ocid: str
    comprador: str
    departamento: str
    monto_pen: float
    similitud: float


@dataclass
class RAGResult:
    answer: str | None
    sources: list[ProcessSource] = field(default_factory=list)
    abstained: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    filtros_aplicados: dict = field(default_factory=dict)


class Engine:
    def __init__(self):
        self.config = load_config()
        self.model = LocalEmbeddings(self.config["embeddings"]["local_model"])
        self.collection = get_collection()
        self.llm_model = self.config["llm"]["model"]
        self.threshold = self.config["retrieval"]["similarity_threshold"]
        self.top_k = self.config["retrieval"]["top_k"]
        self.system_prompt = self.config["prompts"]["system"]
        self.abstention_msg = self.config["messages"]["abstention"]
        self.api_error_msg = self.config["messages"]["api_error"]
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def _build_where(self, filtros: dict) -> dict | None:
        clauses = []
        if filtros.get("departamento"):
            clauses.append({"departamento": {"$eq": filtros["departamento"]}})
        if filtros.get("monto"):
            op, value = filtros["monto"]
            clauses.append({"monto_pen": {"$gte" if op == "gte" else "$lte": value}})
            clauses.append({"monto_valido": {"$eq": True}})
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    def _retrieve(self, question: str, filtros: dict):
        vec = self.model.embed_queries([question])[0]
        where = self._build_where(filtros)
        res = self.collection.query(
            query_embeddings=[vec], n_results=self.top_k, where=where
        )
        metas = res["metadatas"][0]
        docs = res["documents"][0]
        sims = [1 - d for d in res["distances"][0]]
        return docs, metas, sims

    def _build_prompt(self, question: str, docs: list[str], metas: list[dict]) -> str:
        blocks = []
        for text, meta in zip(docs, metas):
            blocks.append(
                f"[ocid={meta['ocid']}, comprador={meta['comprador']}, "
                f"departamento={meta['departamento']}, monto_pen={meta['monto_pen']:.2f}, "
                f"categoria={meta['categoria']}]\n{text}"
            )
        context = "\n\n---\n\n".join(blocks)
        return f"PROCESOS RECUPERADOS:\n\n{context}\n\nPREGUNTA: {question}"

    def answer(self, question: str) -> RAGResult:
        filtros = parse_query(question)
        docs, metas, sims = self._retrieve(question, filtros)
        sources = [
            ProcessSource(
                ocid=m["ocid"], comprador=m["comprador"], departamento=m["departamento"],
                monto_pen=m["monto_pen"], similitud=round(s, 4),
            )
            for m, s in zip(metas, sims)
        ]

        if not sims or sims[0] < self.threshold:
            return RAGResult(answer=self.abstention_msg, sources=sources, abstained=True, filtros_aplicados=filtros)

        user_prompt = self._build_prompt(question, docs, metas)

        with Timer() as t:
            try:
                resp = self._client.messages.create(
                    model=self.llm_model,
                    max_tokens=700,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
            except Exception as e:
                log_call(CallLog(now_iso(), self.llm_model, 0, 0, 0.0, 0.0, False, str(e)))
                return RAGResult(
                    answer=None, sources=sources, abstained=False,
                    error=f"{self.api_error_msg} ({e})", filtros_aplicados=filtros,
                )

        # resp.content puede traer bloques de "thinking" antes del texto;
        # no asumir que el primer bloque es siempre el de texto.
        text_blocks = [b.text for b in resp.content if b.type == "text"]
        text = text_blocks[0].strip() if text_blocks else ""
        tokens_in, tokens_out = resp.usage.input_tokens, resp.usage.output_tokens
        cost = compute_cost(self.llm_model, tokens_in, tokens_out, when=date.today())
        log_call(CallLog(now_iso(), self.llm_model, tokens_in, tokens_out, t.elapsed, cost, True, None))

        if text.startswith("NO_RESPONDE"):
            return RAGResult(
                answer=self.abstention_msg, sources=sources, abstained=True,
                tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, filtros_aplicados=filtros,
            )

        return RAGResult(
            answer=text, sources=sources, abstained=False,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, filtros_aplicados=filtros,
        )


_engine: Engine | None = None


def answer(question: str) -> RAGResult:
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine.answer(question)
