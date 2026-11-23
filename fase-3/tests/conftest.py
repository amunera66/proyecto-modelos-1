"""Fixtures de las pruebas de la API. Ejecutar desde fase-3/:  python -m pytest

El modelo pequeno es fase-2/models/v1, que esta en el repositorio y pesa cerca
de 380 KB. Se usa en modo solo lectura: el fixture modelos_del_repo_intactos
falla si alguna prueba cambia algo en fase-2/models. Lo que se escribe queda en
las carpetas temporales de pytest.
"""

import hashlib
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api._fase2 import REPO_ROOT
from api.config import Settings
from api.main import create_app

MODELOS_REPO = REPO_ROOT / "fase-2" / "models"

# Fila Dune de fase-2/data/ejemplo_prediccion.csv (valores ilustrativos).
# Con v1 predice 6.758120437797601, igual que predict.py (Paso 1 de la Fase 3).
ENTRADA_VALIDA = {
    "budget": 165000000,
    "runtime": 155,
    "release_year": 2021,
    "es_secuela": 0,
    "genero_principal": "Science Fiction",
    "original_language": "en",
}
PREDICCION_V1 = 6.758120437797601


def hashes_de_carpeta(carpeta: Path) -> dict[str, str]:
    """Hash de cada archivo de la carpeta y sus subcarpetas, por ruta relativa."""
    return {
        archivo.relative_to(carpeta).as_posix(): hashlib.sha256(archivo.read_bytes()).hexdigest()
        for archivo in sorted(carpeta.rglob("*"))
        if archivo.is_file()
    }


@pytest.fixture(scope="session", autouse=True)
def modelos_del_repo_intactos():
    """Comprueba al final de la sesion que fase-2/models no cambio."""
    antes = hashes_de_carpeta(MODELOS_REPO)
    yield
    assert hashes_de_carpeta(MODELOS_REPO) == antes, "Las pruebas modificaron fase-2/models"


def settings_repo(version: str = "v1", **cambios) -> Settings:
    """Settings con los modelos del repositorio.

    DATA_PATH apunta a un archivo que no existe: si una prueba llamara a /train
    con estos settings, recibiria 503 sin escribir en fase-2/models.
    """
    valores = {
        "model_version": version,
        "models_dir": MODELOS_REPO,
        "data_path": REPO_ROOT / "fase-3" / "tests" / "no_existe.csv",
    }
    valores.update(cambios)
    return Settings(**valores)


@pytest.fixture(scope="session")
def cliente() -> TestClient:
    """Cliente con v1 del repositorio, compartido por las pruebas que no cambian la app."""
    return TestClient(create_app(settings_repo()))


@pytest.fixture
def copia_de_versiones(tmp_path) -> Path:
    """Carpeta temporal con copias de v1 y v2: las pruebas pueden escribir ahi."""
    destino = tmp_path / "models"
    for version in ("v1", "v2"):
        shutil.copytree(MODELOS_REPO / version, destino / version)
    return destino
