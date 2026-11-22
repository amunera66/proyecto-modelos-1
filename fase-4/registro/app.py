"""App de fase-3 con el registro de predicciones en CSV.

Ejecutar desde fase-4/:  uvicorn registro.app:app

| Variable  | Por defecto                          |
|-----------|--------------------------------------|
| LOG_PATH  | fase-4/registros/predicciones.csv    |

LOG_PATH relativa se resuelve desde la raiz del repositorio, como las demas
rutas del proyecto. MODEL_VERSION y MODELS_DIR son las de fase-3. Importar este
modulo crea la app y carga el modelo; las pruebas usan create_app y RegistroCSV.
"""

import os
from pathlib import Path

from registro import _fase3  # noqa: F401  (debe ir antes de importar api)
from api.config import resolve_path
from api.main import create_app
from registro.csv_logger import RegistroCSV

DEFAULT_LOG_PATH = "fase-4/registros/predicciones.csv"


def log_path_from_env() -> Path:
    """LOG_PATH, o el valor por defecto si no esta definida o esta vacia."""
    return resolve_path(os.environ.get("LOG_PATH", "").strip() or DEFAULT_LOG_PATH)


LOG_PATH = log_path_from_env()
app = create_app(observer=RegistroCSV(LOG_PATH))
