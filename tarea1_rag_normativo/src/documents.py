"""Metadata de los documentos del corpus de la Tarea 1. Única fuente de
verdad: source_check.py, extract.py y build_index.py importan de aquí para
no duplicar rutas/versión/fuente en varios lugares."""
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

DOCS = [
    {
        "doc_id": "ley_32069",
        "archivo": "Ley_32069_consolidada.pdf",
        "documento": "Ley N.° 32069, Ley General de Contrataciones Públicas",
        "tipo": "ley",
        "version": "Consolidada con modificaciones posteriores hasta el 19-07-2026",
        "fuente": "https://www.gob.pe/institucion/osce/colecciones/45029-ley-n-32069-ley-general-de-contrataciones-publicas",
        "fecha_descarga": "2026-09-18",
        "obligatorio": True,
        "dos_columnas": False,
    },
    {
        "doc_id": "ds_001_2026_ef",
        "archivo": "DS_001-2026-EF.pdf",
        "documento": "Decreto Supremo N.° 001-2026-EF",
        "tipo": "decreto_modificatorio_reglamento",
        "version": "Publicado 08-01-2026",
        "fuente": "https://busquedas.elperuano.pe/dispositivo/NL/2474920-3",
        "fecha_descarga": "2026-09-18",
        "obligatorio": True,
        "dos_columnas": True,
    },
    {
        "doc_id": "dl_1715",
        "archivo": "DL_1715.pdf",
        "documento": "Decreto Legislativo N.° 1715 (modifica art. 85.1.e de la Ley 32069)",
        "tipo": "decreto_legislativo_modificatorio_ley",
        "version": "Publicado 04-02-2026",
        "fuente": "https://busquedas.elperuano.pe/dispositivo/NL/2483559-7",
        "fecha_descarga": "2026-09-18",
        "obligatorio": False,
        "dos_columnas": True,
    },
]
