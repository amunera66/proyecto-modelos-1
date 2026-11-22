"""Ubicacion del registro. Importar este modulo no crea la app ni carga el modelo.

| Variable  | Por defecto                          |
|-----------|--------------------------------------|
| LOG_PATH  | fase-4/registros/predicciones.csv    |

LOG_PATH relativa se resuelve desde la raiz del repositorio con resolve_path de
fase-3 (api.config), que solo importa la configuracion: no carga pandas,
scikit-learn ni el modelo. Lo usan registro/app.py y el script de monitoreo.
"""

import os
from pathlib import Path

from registro import _fase3  # noqa: F401  (debe ir antes de importar api)
from api.config import resolve_path

DEFAULT_LOG_PATH = "fase-4/registros/predicciones.csv"


def log_path_from_env() -> Path:
    """LOG_PATH, o el valor por defecto si no esta definida o esta vacia."""
    return resolve_path(os.environ.get("LOG_PATH", "").strip() or DEFAULT_LOG_PATH)
