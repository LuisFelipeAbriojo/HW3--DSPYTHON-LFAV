"""Cálculo y logging de costo por llamada al LLM generador (Fase 3).

Precios verificados manualmente en https://claude.com/pricing el
2026-09-18 (USD por millón de tokens). A diferencia de proveedores como
DeepSeek, que sí publican descuentos por horario (pico/valle), Anthropic no
tiene tarificación diferenciada por hora del día — se deja documentado
explícitamente en vez de simularlo. La tabla sí queda indexada por modelo Y
por fecha de vigencia (`PRICING`), de modo que si el precio cambia entre el
día que se corrió el eval y el día del video, el cálculo usa el precio
vigente en la fecha de CADA llamada (`fecha_llamada`), no un valor fijo
importado una sola vez.
"""
import json
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

# lista de (fecha_desde, precios) por modelo; ordenada, se usa la última
# entrada con fecha_desde <= fecha de la llamada.
PRICING: dict[str, list[tuple[date, dict]]] = {
    "claude-sonnet-5": [
        (date(2026, 9, 18), {"input_per_mtok": 2.0, "output_per_mtok": 10.0}),
    ],
    "claude-opus-5": [
        (date(2026, 9, 18), {"input_per_mtok": 5.0, "output_per_mtok": 25.0}),
    ],
    "claude-haiku-4-5-20251001": [
        (date(2026, 9, 18), {"input_per_mtok": 1.0, "output_per_mtok": 5.0}),
    ],
}

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "costs.log"


def price_for(model: str, when: date) -> dict:
    entries = PRICING[model]
    applicable = [p for d, p in entries if d <= when]
    if not applicable:
        raise ValueError(f"Sin precio vigente para {model} en {when}")
    return applicable[-1]


def compute_cost(model: str, tokens_in: int, tokens_out: int, when: date | None = None) -> float:
    when = when or date.today()
    price = price_for(model, when)
    return (tokens_in / 1_000_000) * price["input_per_mtok"] + (
        tokens_out / 1_000_000
    ) * price["output_per_mtok"]


@dataclass
class CallLog:
    timestamp: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_s: float
    cost_usd: float
    success: bool
    error: str | None = None


def log_call(entry: CallLog):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


class Timer:
    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self._t0


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
