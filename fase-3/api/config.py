"""Configuracion de la API por variables de entorno.

| Variable        | Por defecto                       |
|-----------------|-----------------------------------|
| MODEL_VERSION   | v1                                |
| MODELS_DIR      | fase-2/models                     |
| DATA_PATH       | fase-2/data/movies_metadata.csv   |

Las rutas relativas se resuelven desde la raiz del repositorio, no desde la
carpeta actual. La configuracion se lee al crear la app: para cambiar de
version hay que cambiar MODEL_VERSION y reiniciar el servidor.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from api._fase2 import REPO_ROOT

DEFAULT_MODEL_VERSION = "v1"
DEFAULT_MODELS_DIR = "fase-2/models"
DEFAULT_DATA_PATH = "fase-2/data/movies_metadata.csv"


def resolve_path(value: str | Path) -> Path:
    """Devuelve la ruta tal cual si es absoluta; si no, relativa a la raiz del repo."""
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _env(name: str, default: str) -> str:
    """Lee una variable de entorno; vacia o ausente equivale al valor por defecto."""
    return os.environ.get(name, "").strip() or default


@dataclass(frozen=True)
class Settings:
    """Configuracion de una instancia de la API."""

    model_version: str = DEFAULT_MODEL_VERSION
    models_dir: Path = resolve_path(DEFAULT_MODELS_DIR)
    data_path: Path = resolve_path(DEFAULT_DATA_PATH)

    @property
    def model_path(self) -> Path:
        return self.models_dir / self.model_version

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_version=_env("MODEL_VERSION", DEFAULT_MODEL_VERSION),
            models_dir=resolve_path(_env("MODELS_DIR", DEFAULT_MODELS_DIR)),
            data_path=resolve_path(_env("DATA_PATH", DEFAULT_DATA_PATH)),
        )
