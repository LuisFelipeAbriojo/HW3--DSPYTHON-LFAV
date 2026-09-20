"""Extrae condiciones NUMÉRICAS y TERRITORIALES de una pregunta en lenguaje
natural para aplicarlas como FILTROS de metadata (Fase 3), no como texto
que se vectoriza.

Por qué filtros y no embeddings: un embedding semántico captura de qué
TRATA el texto (agua, saneamiento, salud), pero no entiende aritmética ni
nombres propios de lugares de forma confiable -- "más de un millón" y
"menos de un millón" son casi el mismo vector semántico pese a tener
significados opuestos, y "Cusco" puede aparecer en la descripción de un
proceso ejecutado en otro departamento. Filtrar por metadata estructurada
(monto_pen, departamento) es exacto; dejarle esa parte al embedding no lo
es.
"""
import re

from territory import CANONICAL_DEPARTMENTS, PROVINCE_LOOKUP, _key

_MULTIPLIERS = {"mil": 1_000, "millon": 1_000_000, "millones": 1_000_000}
_WORD_NUMBERS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "medio": 0.5,
    "veinte": 20, "cincuenta": 50, "cien": 100, "doscientos": 200,
    "trescientos": 300, "quinientos": 500,
}


def _contains_word(haystack: str, needle: str) -> bool:
    """Coincidencia por palabra completa (\\b), no substring: "PIURA" no debe
    matchear dentro de "BASICA" solo porque termina en "ICA"."""
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None


def extract_department(question: str) -> str | None:
    q = _key(question)
    for dept in CANONICAL_DEPARTMENTS:
        if _contains_word(q, _key(dept)):
            return dept
    for prov_key, dept in PROVINCE_LOOKUP.items():
        if len(prov_key) > 3 and _contains_word(q, prov_key):
            return dept
    return None


def extract_amount_filter(question: str) -> tuple[str, float] | None:
    """Devuelve (operador, monto_en_soles) donde operador es 'gte' o 'lte'.
    `q` se trabaja sin tildes (vía `_key`) para que "millón"/"millon" y
    "más"/"mas" se traten igual."""
    q = _key(question).lower()

    number_pattern = r"(\d[\d,.']*)\s*(mil|millon(?:es)?)?"
    match = None
    for m in re.finditer(number_pattern, q):
        if m.group(0).strip():
            match = m
            break

    value = None
    if match:
        raw_num = match.group(1).replace(",", "").replace("'", "")
        try:
            value = float(raw_num)
        except ValueError:
            value = None
        unit = match.group(2)
        if value is not None and unit:
            value *= _MULTIPLIERS[unit.replace("es", "")] if unit != "mil" else 1_000

    if value is None:
        # números escritos en palabras: "un millon", "diez millones", "medio millon"
        word_pattern = r"\b(" + "|".join(_WORD_NUMBERS) + r")\s+(mil|millon(?:es)?)\b"
        m = re.search(word_pattern, q)
        if m:
            value = _WORD_NUMBERS[m.group(1)] * (
                1_000 if m.group(2) == "mil" else 1_000_000
            )

    if value is None:
        return None

    if any(w in q for w in ["menos de", "inferior a", "por debajo de", "hasta"]):
        return ("lte", value)
    return ("gte", value)  # "mas de", "mayor a", "superior a", "por encima de" -> y default


def parse(question: str) -> dict:
    return {
        "departamento": extract_department(question),
        "monto": extract_amount_filter(question),
    }
