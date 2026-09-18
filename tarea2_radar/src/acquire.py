"""Descarga de archivos mensuales de contrataciones abiertas (OECE).

Uso del acceso: el portal expone un endpoint de archivos masivos mensuales
(/api/v1/files, paginado) y un endpoint de descarga directa por mes/formato
(/api/v1/file/{fuente}/{formato}/{anio}/{mes}/). Usamos ESTE endpoint para el
corpus (necesitamos meses completos de 2026), no la API paginada de procesos
individuales, que está pensada para actualizaciones incrementales recientes
(ver Fase 1: "usa la API solo para lo que sirve: traer actualizaciones").

El script es re-ejecutable: si el .zip ya existe en data/raw/ no lo vuelve a
descargar (idempotente), y cada descarga se registra en logs/acquire.log.
"""
import argparse
import json
import logging
import time
from pathlib import Path

import requests

BASE = "https://contratacionesabiertas.oece.gob.pe/api/v1"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HW3-DSPYTHON-LFAV/1.0)"}

logging.basicConfig(
    filename=LOG_DIR / "acquire.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("acquire")


def download_month(year: str, month: str, fmt: str = "csv", source: str = "seace_v3") -> Path:
    """Descarga el .zip de un mes/formato si no existe ya localmente."""
    dest = RAW_DIR / f"{year}-{month}_{source}_{fmt}.zip"
    if dest.exists():
        logger.info("SKIP (ya existe) %s", dest.name)
        print(f"Ya existe, no se vuelve a descargar: {dest.name}")
        return dest

    url = f"{BASE}/file/{source}/{fmt}/{year}/{month}/"
    t0 = time.time()
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    elapsed = time.time() - t0

    logger.info(
        "OK %s -> %s bytes=%d elapsed=%.1fs status=%d",
        url, dest.name, len(resp.content), elapsed, resp.status_code,
    )
    print(f"Descargado {dest.name} ({len(resp.content):,} bytes, {elapsed:.1f}s)")
    return dest


def list_available_months(source: str = "seace_v3", max_pages: int = 3) -> list[dict]:
    """Lista los meses disponibles vía /api/v1/files (paginado)."""
    results = []
    page = 1
    while page <= max_pages:
        resp = requests.get(f"{BASE}/files", params={"page": page}, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        results.extend(r for r in data["results"] if r["source"] == source)
        if not data["pagination"]["has_next"]:
            break
        page += 1
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2026")
    parser.add_argument("--months", nargs="+", default=["08"], help="Meses a descargar, p.ej. 06 07 08")
    parser.add_argument("--fmt", default="csv", choices=["csv", "json", "xlsx"])
    args = parser.parse_args()

    for m in args.months:
        download_month(args.year, m, args.fmt)
