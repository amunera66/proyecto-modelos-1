"""Fixtures del registro. Usan models/v1 de fase-2 solo para leer, y tmp_path para el CSV."""

import csv
from pathlib import Path

import pytest

from registro import _fase3  # noqa: F401  (debe ir antes de importar api)
from api.config import Settings
from api.main import create_app
from fastapi.testclient import TestClient
from registro.csv_logger import RegistroCSV

# Fila Dune de fase-2/data/ejemplo_prediccion.csv
DUNE = {
    "budget": 165000000,
    "runtime": 155,
    "release_year": 2021,
    "es_secuela": 0,
    "genero_principal": "Science Fiction",
    "original_language": "en",
}
# Fila Top Gun: Maverick del mismo archivo
TOP_GUN = {
    "budget": 170000000,
    "runtime": 131,
    "release_year": 2022,
    "es_secuela": 1,
    "genero_principal": "Action",
    "original_language": "en",
}


def read_log(path: Path) -> list[list[str]]:
    """Todas las lineas del CSV, encabezado incluido, como texto."""
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.reader(file))


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "registros" / "predicciones.csv"


@pytest.fixture
def make_client(log_path: Path):
    """Crea un TestClient con la app de fase-3 y el registro en log_path."""

    def make(version: str = "v1", path: Path | None = None) -> TestClient:
        app = create_app(Settings(model_version=version), observer=RegistroCSV(path or log_path))
        return TestClient(app)

    return make
