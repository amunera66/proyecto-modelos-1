"""App de fase-3 con el registro de predicciones en CSV.

Ejecutar desde fase-4/:  uvicorn registro.app:app

| Variable  | Por defecto                          |
|-----------|--------------------------------------|
| LOG_PATH  | fase-4/registros/predicciones.csv    |

LOG_PATH se lee con registro.config. MODEL_VERSION y MODELS_DIR son las de
fase-3. Importar este modulo crea la app y carga el modelo: las pruebas usan
create_app y RegistroCSV, y el script de monitoreo, registro.config.
"""

from registro.config import log_path_from_env  # importa fase-3 a traves de registro._fase3
from api.main import create_app
from registro.csv_logger import RegistroCSV

LOG_PATH = log_path_from_env()
app = create_app(observer=RegistroCSV(LOG_PATH))
