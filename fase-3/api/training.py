"""Logica de POST /train. El entrenamiento es el de fase-2/src/training.py.

Entrena con la configuracion de la Fase 2: el CSV de DATA_PATH, objetivo
vote_average, semilla 42 y los demas defaults de TrainingOptions, igual que
train.py sin argumentos opcionales. Guarda en MODELS_DIR con el siguiente
identificador libre (v3, v4, ...) y nunca sobrescribe: save_version lo impide.
No cambia la version que sirve /predict.
"""

import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from api._fase2 import REPO_ROOT  # debe ir antes de importar src
from api.config import Settings, display_path, hide_root
from src import config as fase2_config
from src import training, versioning
from src.data import DataError

logger = logging.getLogger("api")

# Solo cuentan las carpetas vN: v-test o v1-copia no afectan la numeracion
NUMBERED_VERSION = re.compile(r"v([0-9]+)")

# Identificadores reservados por entrenamientos en curso, por carpeta de destino.
# El lock evita que dos /train simultaneos elijan el mismo identificador. Vale
# dentro de un proceso; entre procesos, save_version sigue sin sobrescribir.
_lock = threading.Lock()
_reserved: set[Path] = set()


class TrainingFailure(Exception):
    """Error previsible de /train, con el codigo HTTP y el cuerpo de la respuesta."""

    def __init__(self, status: int, content: dict):
        super().__init__(content.get("error"))
        self.status = status
        self.content = content


@dataclass(frozen=True)
class TrainingResponse:
    version: str
    content: dict


def _version_path(models_dir: Path, version: str) -> str:
    """Ruta de la version para la respuesta, sin rutas locales fuera del repo."""
    folder = models_dir / version
    try:
        return folder.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return f"MODELS_DIR/{version}"


def next_version(models_dir: Path, reserved: set[str] = frozenset()) -> str:
    """Devuelve v<N+1>, donde N es el mayor numero entre las vN existentes y las reservadas.

    Cuenta cualquier entrada llamada vN, sea carpeta o archivo. Sin versiones, v1.
    """
    names = set(reserved)
    if models_dir.is_dir():
        names.update(path.name for path in models_dir.iterdir())
    numbers = [
        int(match.group(1)) for name in names if (match := NUMBERED_VERSION.fullmatch(name))
    ]
    return f"v{max(numbers, default=0) + 1}"


def _reserve(models_dir: Path) -> tuple[str, Path]:
    with _lock:
        reserved = {path.name for path in _reserved if path.parent == models_dir}
        version = next_version(models_dir, reserved)
        target = models_dir / version
        _reserved.add(target)
    return version, target


def _release(target: Path) -> None:
    with _lock:
        _reserved.discard(target)


def _summary(metrics: dict) -> dict:
    """Metricas principales: modelo en prueba y en CV (media), y baseline en prueba."""
    model = metrics["modelo"]
    return {
        "modelo": {
            "prueba": model["prueba"],
            "cv_media": {name: values["media"] for name, values in model["cv"].items()},
        },
        "baseline": {"prueba": metrics["baseline"]["prueba"]},
    }


def train_new_version(
    settings: Settings,
    active_version: str,
    train: Callable[[training.TrainingOptions], training.TrainingResult] | None = None,
) -> TrainingResponse:
    """Entrena y guarda una version nueva. Lanza TrainingFailure si algo previsible falla.

    train permite reemplazar training.train_model en las pruebas; por defecto es esa funcion.
    """
    train = train or training.train_model
    data_path = settings.data_path
    if not data_path.is_file():
        raise TrainingFailure(503, {
            "error": "Datos de entrenamiento no disponibles",
            "detalle": (
                f"No se encontro el archivo de datos {display_path(data_path)}. "
                "Revisa DATA_PATH o el montaje de los datos y vuelve a intentar."
            ),
        })

    models_dir = settings.models_dir.resolve()
    version, target = _reserve(models_dir)
    options = training.TrainingOptions(
        data_path=data_path, version=version, output_dir=models_dir
    )
    logger.info("Entrenando la version %s con %s", version, display_path(data_path))
    try:
        result = train(options)
    except versioning.VersionExistsError as error:
        raise TrainingFailure(409, {
            "error": "La version ya existe",
            "version": version,
            "detalle": (
                f"{hide_root(str(error))}. Otro proceso guardo esa version mientras se "
                "entrenaba; no se sobrescribio. Vuelve a llamar a /train."
            ),
        }) from error
    except (DataError, training.TrainingError) as error:
        raise TrainingFailure(500, {
            "error": "Datos de entrenamiento invalidos",
            "detalle": f"{display_path(data_path)}: {hide_root(str(error))}",
        }) from error
    except (versioning.VersionError, OSError) as error:
        logger.exception("No se pudo guardar la version %s", version)
        raise TrainingFailure(500, {
            "error": "No se pudo guardar la version",
            "version": version,
            "detalle": (
                f"No se pudo escribir en {display_path(models_dir)}. Revisa que MODELS_DIR "
                "exista y tenga permiso de escritura. El detalle quedo en el log del servidor."
            ),
        }) from error
    finally:
        _release(target)

    logger.info("Version %s guardada en %s", version, display_path(result.version_dir))
    return TrainingResponse(version, {
        "version": version,
        "ruta": _version_path(models_dir, version),
        "metrica_principal": fase2_config.PRIMARY_METRIC,
        "metricas": _summary(result.metrics),
        "version_activa": active_version,
        "detalle": (
            f"Version {version} guardada. La API sigue sirviendo {active_version}: para usar "
            f"{version}, cambia MODEL_VERSION y reinicia el servidor."
        ),
    })
