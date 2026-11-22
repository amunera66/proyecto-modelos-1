"""Pruebas de registro.config: ubicar el registro sin crear la app."""

import os
import subprocess
import sys
from pathlib import Path

from registro._fase3 import REPO_ROOT
from registro.config import DEFAULT_LOG_PATH, log_path_from_env

FASE4_DIR = Path(__file__).resolve().parents[1]

# Se corre en un proceso aparte: en esta sesion conftest ya importo api.main
CHECK = """
import sys
import registro.config
from registro._fase3 import REPO_ROOT
cargados = [m for m in ("registro.app", "api.main", "api.schema", "sklearn", "joblib", "pandas")
            if m in sys.modules]
print("cargados:", cargados)
print("ruta:", registro.config.log_path_from_env().relative_to(REPO_ROOT).as_posix())
"""


def test_importar_config_no_crea_la_app_ni_carga_el_modelo():
    env = {k: v for k, v in os.environ.items() if k != "LOG_PATH"}
    env["MODEL_VERSION"] = "v9"  # si se cargara el modelo, escribiria un error en el log
    result = subprocess.run(
        [sys.executable, "-c", CHECK],
        cwd=FASE4_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "cargados: []" in result.stdout
    assert "ruta: fase-4/registros/predicciones.csv" in result.stdout


def test_log_path_por_defecto_y_vacio(monkeypatch):
    monkeypatch.delenv("LOG_PATH", raising=False)
    assert log_path_from_env() == REPO_ROOT / DEFAULT_LOG_PATH
    monkeypatch.setenv("LOG_PATH", "  ")
    assert log_path_from_env() == REPO_ROOT / DEFAULT_LOG_PATH


def test_log_path_relativo_se_resuelve_desde_la_raiz(monkeypatch, tmp_path):
    monkeypatch.setenv("LOG_PATH", "fase-4/registros/otro.csv")
    assert log_path_from_env() == REPO_ROOT / "fase-4" / "registros" / "otro.csv"
    monkeypatch.setenv("LOG_PATH", str(tmp_path / "x.csv"))
    assert log_path_from_env() == tmp_path / "x.csv"
