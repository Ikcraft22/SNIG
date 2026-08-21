import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ============== CONFIGURACIÓN DE BASE DE DATOS ==============
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "inventario_medicamentos")

SQLITE_FILE = os.getenv("SQLITE_FILE", "inventario.db")
SQLITE_PATH = Path(SQLITE_FILE)

if not DATABASE_URL:
    if DB_ENGINE == "mysql":
        DATABASE_URL = (
            f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        )
    else:
        sqlite_path = SQLITE_PATH.resolve()
        sqlite_url_path = sqlite_path.as_posix()
        if sqlite_url_path.startswith("/") and len(sqlite_url_path) > 2 and sqlite_url_path[2] == ":":
            sqlite_url_path = sqlite_url_path[1:]
        DATABASE_URL = f"sqlite:///{sqlite_url_path}"

# ============== CONFIGURACIÓN DE APIs ==============
# Google Custom Search API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

# OpenFoodFacts API (no requiere key)
OPENFOODFACTS_API_URL = "https://world.openfoodfacts.org/api/v0"

# ============== CONFIGURACIÓN DE RUTAS ==============
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_FILE = os.path.join(DATA_DIR, "CÓDIGO_ÚNICO_DE_MEDICAMENTOS_VIGENTES_20250922.csv")

# ============== CONFIGURACIÓN DE APLICACIÓN ==============
DEBUG = os.getenv("DEBUG", "True") == "True"
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")

# ============== PRESENTACIONES DE PRODUCTOS ==============
PRESENTACIONES = {
    "unidad": {"nombre": "Unidad", "codigo": "UND"},
    "bolsa": {"nombre": "Bolsa", "codigo": "BOL"},
    "botella": {"nombre": "Botella", "codigo": "BOT"},
}

# ============== CONFIGURACIÓN DE MONEDA ==============
MONEDA = os.getenv("MONEDA", "$")
IDIOMA = os.getenv("IDIOMA", "es")
