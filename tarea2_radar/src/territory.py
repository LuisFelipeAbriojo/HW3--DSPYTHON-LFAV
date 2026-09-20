"""Normalización territorial a los 25 departamentos del Perú (Fase 2).

Regla explícita y documentada:
1. Se limpia el valor crudo (mayúsculas, sin tildes, sin espacios extra).
2. Si coincide con uno de los 25 departamentos (o un alias conocido, p.ej.
   "LIMA METROPOLITANA" o "PROVINCIA CONSTITUCIONAL DEL CALLAO"), se usa
   directamente.
3. Si no, se busca como PROVINCIA en la tabla oficial de 196 provincias
   (fuente: Wikipedia "Anexo:Provincias del Perú", verificado 2026-09-18) y
   se traduce a su departamento. Esto resuelve el caso reportado por el
   enunciado de que el campo de ubicación a veces trae la provincia en vez
   del departamento.
4. Si tampoco coincide, se marca como NO LOCALIZADO -- no se inventa un
   departamento. Se cuenta y se reporta cuántos casos caen aquí y por qué
   (ver validate.py).
"""
import unicodedata

CANONICAL_DEPARTMENTS = [
    "AMAZONAS", "ÁNCASH", "APURÍMAC", "AREQUIPA", "AYACUCHO", "CAJAMARCA",
    "CALLAO", "CUSCO", "HUANCAVELICA", "HUÁNUCO", "ICA", "JUNÍN",
    "LA LIBERTAD", "LAMBAYEQUE", "LIMA", "LORETO", "MADRE DE DIOS",
    "MOQUEGUA", "PASCO", "PIURA", "PUNO", "SAN MARTÍN", "TACNA", "TUMBES",
    "UCAYALI",
]
assert len(CANONICAL_DEPARTMENTS) == 25

# provincia (sin tildes, mayúscula) -> departamento canónico
_PROVINCE_RAW = {
    "AMAZONAS": ["CHACHAPOYAS", "BAGUA", "BONGARA", "CONDORCANQUI", "LUYA", "RODRIGUEZ DE MENDOZA", "UTCUBAMBA"],
    "ÁNCASH": ["HUARAZ", "AIJA", "ANTONIO RAYMONDI", "ASUNCION", "BOLOGNESI", "CARHUAZ", "CARLOS FERMIN FITZCARRALD", "CASMA", "CORONGO", "HUARI", "HUARMEY", "HUAYLAS", "MARISCAL LUZURIAGA", "OCROS", "PALLASCA", "POMABAMBA", "RECUAY", "SANTA", "SIHUAS", "YUNGAY"],
    "APURÍMAC": ["ABANCAY", "ANDAHUAYLAS", "ANTABAMBA", "AYMARAES", "COTABAMBAS", "CHINCHEROS", "GRAU"],
    "AREQUIPA": ["AREQUIPA", "CAMANA", "CARAVELI", "CASTILLA", "CAYLLOMA", "CONDESUYOS", "ISLAY", "LA UNION"],
    "AYACUCHO": ["HUAMANGA", "CANGALLO", "HUANCA SANCOS", "HUANTA", "LA MAR", "LUCANAS", "PARINACOCHAS", "PAUCAR DEL SARA SARA", "SUCRE", "VICTOR FAJARDO", "VILCASHUAMAN"],
    "CAJAMARCA": ["CAJAMARCA", "CAJABAMBA", "CELENDIN", "CHOTA", "CONTUMAZA", "CUTERVO", "HUALGAYOC", "JAEN", "SAN IGNACIO", "SAN MARCOS", "SAN MIGUEL", "SAN PABLO", "SANTA CRUZ"],
    "CALLAO": ["CALLAO"],
    "CUSCO": ["CUSCO", "ACOMAYO", "ANTA", "CALCA", "CANAS", "CANCHIS", "CHUMBIVILCAS", "ESPINAR", "LA CONVENCION", "PARURO", "PAUCARTAMBO", "QUISPICANCHI", "URUBAMBA"],
    "HUANCAVELICA": ["HUANCAVELICA", "ACOBAMBA", "ANGARAES", "CASTROVIRREYNA", "CHURCAMPA", "HUAYTARA", "TAYACAJA"],
    "HUÁNUCO": ["HUANUCO", "AMBO", "DOS DE MAYO", "HUACAYBAMBA", "HUAMALIES", "LEONCIO PRADO", "MARAÑON", "PACHITEA", "PUERTO INCA", "LAURICOCHA", "YAROWILCA"],
    "ICA": ["ICA", "CHINCHA", "NAZCA", "PALPA", "PISCO"],
    "JUNÍN": ["HUANCAYO", "CONCEPCION", "CHANCHAMAYO", "JAUJA", "JUNIN", "SATIPO", "TARMA", "YAULI", "CHUPACA"],
    "LA LIBERTAD": ["TRUJILLO", "ASCOPE", "BOLIVAR", "CHEPEN", "JULCAN", "OTUZCO", "PACASMAYO", "PATAZ", "SANCHEZ CARRION", "SANTIAGO DE CHUCO", "GRAN CHIMU", "VIRU"],
    "LAMBAYEQUE": ["CHICLAYO", "FERREÑAFE", "LAMBAYEQUE"],
    "LIMA": ["LIMA", "BARRANCA", "CAJATAMBO", "CANTA", "CAÑETE", "HUARAL", "HUAROCHIRI", "HUAURA", "OYON", "YAUYOS"],
    "LORETO": ["MAYNAS", "ALTO AMAZONAS", "LORETO", "MARISCAL RAMON CASTILLA", "REQUENA", "UCAYALI", "DATEM DEL MARAÑON", "PUTUMAYO"],
    "MADRE DE DIOS": ["TAMBOPATA", "MANU", "TAHUAMANU"],
    "MOQUEGUA": ["MARISCAL NIETO", "GENERAL SANCHEZ CERRO", "ILO"],
    "PASCO": ["PASCO", "DANIEL ALCIDES CARRION", "OXAPAMPA"],
    "PIURA": ["PIURA", "AYABACA", "HUANCABAMBA", "MORROPON", "PAITA", "SULLANA", "TALARA", "SECHURA"],
    "PUNO": ["PUNO", "AZANGARO", "CARABAYA", "CHUCUITO", "EL COLLAO", "HUANCANE", "LAMPA", "MELGAR", "MOHO", "SAN ANTONIO DE PUTINA", "SAN ROMAN", "SANDIA", "YUNGUYO"],
    "SAN MARTÍN": ["MOYOBAMBA", "BELLAVISTA", "EL DORADO", "HUALLAGA", "LAMAS", "MARISCAL CACERES", "PICOTA", "RIOJA", "SAN MARTIN", "TOCACHE"],
    "TACNA": ["TACNA", "CANDARAVE", "JORGE BASADRE", "TARATA"],
    "TUMBES": ["TUMBES", "CONTRALMIRANTE VILLAR", "ZARUMILLA"],
    "UCAYALI": ["CORONEL PORTILLO", "ATALAYA", "PADRE ABAD", "PURUS"],
}
# nota: "Ucayali" aparece como provincia de Loreto Y como departamento propio
# (son entidades distintas con el mismo nombre) -- se resuelve dejando que
# el departamento (paso 2 de la regla) tenga prioridad sobre la provincia
# (paso 3), ver normalize_department().


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _key(s: str) -> str:
    return _strip_accents(s).upper().strip()


DEPARTMENT_LOOKUP = {_key(d): d for d in CANONICAL_DEPARTMENTS}
DEPARTMENT_LOOKUP.update(
    {
        _key("LIMA METROPOLITANA"): "LIMA",
        _key("PROVINCIA CONSTITUCIONAL DEL CALLAO"): "CALLAO",
        _key("PROV. CONST. DEL CALLAO"): "CALLAO",
        _key("REGION LIMA"): "LIMA",
        _key("LIMA REGION"): "LIMA",
    }
)

PROVINCE_LOOKUP: dict[str, str] = {}
for dept, provinces in _PROVINCE_RAW.items():
    for prov in provinces:
        PROVINCE_LOOKUP.setdefault(_key(prov), dept)


def normalize_department(raw: str | None) -> str | None:
    """Devuelve el departamento canónico o None si no se pudo ubicar."""
    if not raw or not str(raw).strip():
        return None
    key = _key(str(raw))
    if key in DEPARTMENT_LOOKUP:
        return DEPARTMENT_LOOKUP[key]
    if key in PROVINCE_LOOKUP:
        return PROVINCE_LOOKUP[key]
    return None
