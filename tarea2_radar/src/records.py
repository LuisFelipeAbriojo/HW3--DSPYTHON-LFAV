"""Carga de los archivos mensuales de OECE y reducción a una fila por
proceso de contratación (Fase 1, parte de "un registro por ocid").

`records.csv` dentro de cada .zip mensual YA es la vista "compilada" de
OCDS: una fila por `ocid`, con el `compiledRelease` (la fusión de todas las
`releases` de ese proceso hasta la fecha del corte). Por eso una `release`
es un evento (se publica una por cada etapa: convocatoria, buena pro,
contrato...) mientras que un `record` es el acumulado de todas las
releases de un mismo `ocid` -- es la unidad correcta para "una fila por
proceso".
"""
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

RECORD_COLUMNS = {
    "ocid": "ocid",
    "compiledRelease/date": "fecha_compilacion",
    "compiledRelease/buyer/name": "comprador",
    "compiledRelease/tender/title": "titulo",
    "compiledRelease/tender/description": "descripcion",
    "compiledRelease/tender/mainProcurementCategory": "categoria",
    "compiledRelease/tender/procurementMethod": "metodo_contratacion",
    "compiledRelease/tender/procurementMethodDetails": "procedimiento",
    "compiledRelease/tender/value/amount": "monto",
    "compiledRelease/tender/value/currency": "moneda",
    "compiledRelease/tender/value/amount_PEN": "monto_pen",
    "compiledRelease/tender/datePublished": "fecha_publicacion",
    "compiledRelease/tender/numberOfTenderers": "num_postores",
}

PARTY_COLUMNS = {
    "ocid": "ocid",
    "compiledRelease/parties/0/address/department": "departamento_raw",
    "compiledRelease/parties/0/roles": "roles",
}


def _read_csv_from_zip(zip_path: Path, member: str, columns: dict) -> pd.DataFrame:
    with ZipFile(zip_path) as z, z.open(member) as f:
        df = pd.read_csv(f, usecols=list(columns.keys()))
    return df.rename(columns=columns)


def load_month(zip_path: Path) -> pd.DataFrame:
    records = _read_csv_from_zip(zip_path, "records.csv", RECORD_COLUMNS)
    parties = _read_csv_from_zip(zip_path, "com_parties.csv", PARTY_COLUMNS)

    buyers = parties[parties["roles"].astype(str).str.contains("buyer", na=False)]
    buyers = buyers.drop_duplicates(subset="ocid", keep="first")[["ocid", "departamento_raw"]]

    merged = records.merge(buyers, on="ocid", how="left")
    merged["mes_origen"] = zip_path.stem[:7]  # "2026-08"
    return merged


def load_all_months(months: list[str], year: str = "2026", source: str = "seace_v3") -> pd.DataFrame:
    frames = []
    for m in months:
        zip_path = RAW_DIR / f"{year}-{m}_{source}_csv.zip"
        if not zip_path.exists():
            raise FileNotFoundError(f"Falta {zip_path} — correr src/acquire.py primero")
        frames.append(load_month(zip_path))
    return pd.concat(frames, ignore_index=True)
