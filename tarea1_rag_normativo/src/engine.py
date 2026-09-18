"""Motor RAG de la Tarea 1 (Fase 3).

Una sola función pública, `answer(pregunta)`, que devuelve un `RAGResult`
estructurado. Este módulo NO importa Streamlit ni ninguna librería de
interfaz (verificable con `grep -n "^import\\|^from" engine.py` — ver
README). Cualquier interfaz (Streamlit, Telegram, CLI) solo llama a esta
función.

Dos líneas de defensa contra respuestas incorrectas:
1. Umbral de similitud (config.yaml: retrieval.similarity_threshold,
   calibrado con evidencia en eval/run_retrieval_eval.py): si el mejor
   fragmento recuperado no supera el umbral, se abstiene SIN llamar al LLM.
2. Instrucción del prompt: aun si el umbral se supera, el modelo debe
   responder "NO_RESPONDE" si el contexto no alcanza para responder con
   certeza (necesario porque, como muestra el sweep de umbral, la similitud
   coseno de este modelo no separa limpiamente preguntas fuera de dominio
   que son temáticamente cercanas al corpus).
"""
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

from build_index import get_collection
from costs import CallLog, compute_cost, log_call, now_iso, Timer
from embeddings import LocalEmbeddings

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

load_dotenv(ENV_PATH)


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@dataclass
class Source:
    documento: str
    pagina: int
    similitud: float


@dataclass
class RAGResult:
    answer: str | None
    sources: list[Source] = field(default_factory=list)
    abstained: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str | None = None


class Engine:
    """Se instancia una vez (carga config + modelo + índice) y se reusa
    entre preguntas — recomendado para la app Streamlit vía
    @st.cache_resource, evitando recargar el modelo de embeddings en cada
    pregunta."""

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

    def _retrieve(self, question: str):
        vec = self.model.embed_queries([question])[0]
        res = self.collection.query(query_embeddings=[vec], n_results=self.top_k)
        metas = res["metadatas"][0]
        docs = res["documents"][0]
        sims = [1 - d for d in res["distances"][0]]
        return docs, metas, sims

    def _build_prompt(self, question: str, docs: list[str], metas: list[dict]) -> str:
        context_blocks = []
        for text, meta in zip(docs, metas):
            context_blocks.append(
                f"[{meta['documento']}, página {meta['pagina']}]\n{text}"
            )
        context = "\n\n---\n\n".join(context_blocks)
        return f"CONTEXTO:\n\n{context}\n\nPREGUNTA: {question}"

    def answer(self, question: str) -> RAGResult:
        docs, metas, sims = self._retrieve(question)
        sources = [
            Source(documento=m["documento"], pagina=m["pagina"], similitud=round(s, 4))
            for m, s in zip(metas, sims)
        ]

        if not sims or sims[0] < self.threshold:
            return RAGResult(answer=self.abstention_msg, sources=sources, abstained=True)

        user_prompt = self._build_prompt(question, docs, metas)

        with Timer() as t:
            try:
                resp = self._client.messages.create(
                    model=self.llm_model,
                    max_tokens=700,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
            except Exception as e:  # nunca se presenta como respuesta normal
                log_call(
                    CallLog(
                        timestamp=now_iso(), model=self.llm_model, tokens_in=0,
                        tokens_out=0, latency_s=0.0, cost_usd=0.0,
                        success=False, error=str(e),
                    )
                )
                return RAGResult(
                    answer=None, sources=sources, abstained=False,
                    error=f"{self.api_error_msg} ({e})",
                )

        text = resp.content[0].text.strip()
        tokens_in = resp.usage.input_tokens
        tokens_out = resp.usage.output_tokens
        cost = compute_cost(self.llm_model, tokens_in, tokens_out, when=date.today())

        log_call(
            CallLog(
                timestamp=now_iso(), model=self.llm_model, tokens_in=tokens_in,
                tokens_out=tokens_out, latency_s=t.elapsed, cost_usd=cost,
                success=True, error=None,
            )
        )

        if text.startswith("NO_RESPONDE"):
            return RAGResult(
                answer=self.abstention_msg, sources=sources, abstained=True,
                tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
            )

        return RAGResult(
            answer=text, sources=sources, abstained=False,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
        )


_engine: Engine | None = None


def answer(question: str) -> RAGResult:
    """Punto de entrada único del motor. Perezoso: la primera llamada carga
    modelo + índice; las siguientes reusan la misma instancia."""
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine.answer(question)
