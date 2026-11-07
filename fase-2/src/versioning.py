"""Guardado y carga de versiones del modelo.

Cada version es una carpeta <output_dir>/<version>/ con tres archivos:
modelo.joblib, metrics.json y metadata.json. Las claves de metadata.json estan
en METADATA_KEYS y su detalle en docs/decisiones.md.
"""

import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline

from src import config

MODEL_FILE = "modelo.joblib"
METRICS_FILE = "metrics.json"
METADATA_FILE = "metadata.json"
GIT_NOT_AVAILABLE = "no disponible"

METADATA_KEYS = (
    "version",
    "fecha",
    "tipo_problema",
    "objetivo",
    "algoritmo",
    "contrato_entrada",
    "sexta_predictora",
    "hiperparametros",
    "semilla",
    "datos",
    "horizonte_objetivo",
    "particion",
    "metrica_principal",
    "entorno",
    "git_commit",
)
LIBRARIES = ("scikit-learn", "pandas", "numpy", "joblib", "scipy")
VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class VersionError(Exception):
    """Error previsible al guardar o cargar una version."""


class VersionExistsError(VersionError):
    """La version ya existe y no se puede sobrescribir."""


class VersionNotFoundError(VersionError):
    """La version o alguno de sus archivos no existe."""


class VersionLoadError(VersionError):
    """Un archivo de la version existe, pero no se puede leer."""


def get_git_commit() -> str:
    """Devuelve el commit de git, o GIT_COMMIT, o "no disponible"."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return os.environ.get("GIT_COMMIT", "").strip() or GIT_NOT_AVAILABLE


def build_metadata(
    version: str,
    pipeline: Pipeline,
    seed: int,
    data_info: dict,
    partition: dict,
    target: str = config.TARGET,
) -> dict:
    """Arma metadata.json. data_info viene de data.describe_dataset.

    partition debe traer al menos: estrategia, test_size, n_train y n_test.
    """
    model = pipeline.named_steps["modelo"]
    sixth_feature = pipeline.named_steps["ceros_a_nan"].kw_args["sixth_feature"]
    return {
        "version": version,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tipo_problema": config.PROBLEM_TYPE,
        "objetivo": target,
        "algoritmo": type(model).__name__,
        "contrato_entrada": config.input_contract(sixth_feature),
        "sexta_predictora": sixth_feature,
        "hiperparametros": model.get_params(),
        "semilla": seed,
        "datos": data_info,
        "horizonte_objetivo": config.TARGET_HORIZON,
        "particion": partition,
        "metrica_principal": config.PRIMARY_METRIC,
        "entorno": {
            "python": platform.python_version(),
            "librerias": {
                name: importlib.metadata.version(name) for name in LIBRARIES
            },
            "requirements": config.REQUIREMENTS_FILE,
        },
        "git_commit": get_git_commit(),
    }


def _to_json(value: Any) -> Any:
    """Convierte los escalares de numpy, que json no sabe escribir."""
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Valor no serializable en JSON: {value!r}")


def _write_json(path: Path, content: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(content, file, ensure_ascii=False, indent=2, default=_to_json)
        file.write("\n")


def save_version(
    pipeline: Pipeline,
    metrics: dict,
    metadata: dict,
    output_dir: str | Path,
    version: str,
) -> Path:
    """Guarda una version nueva y devuelve su carpeta. Nunca sobrescribe.

    Escribe en una carpeta temporal dentro de output_dir y la renombra al
    final, asi que un fallo no deja una version a medias.
    """
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(
            f"Version invalida: {version!r}. Usa letras, numeros, punto, guion o guion bajo."
        )
    missing = [key for key in METADATA_KEYS if key not in metadata]
    if missing:
        raise ValueError(f"Faltan claves en metadata: {', '.join(missing)}")
    if metadata["version"] != version:
        raise ValueError(
            f"metadata dice version {metadata['version']!r}, pero se pidio {version!r}"
        )

    output_dir = Path(output_dir)
    target = output_dir / version
    if target.exists():
        raise VersionExistsError(f"La version ya existe: {target}")

    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = output_dir / f".tmp-{version}-{uuid.uuid4().hex}"
    temporary.mkdir()
    try:
        joblib.dump(pipeline, temporary / MODEL_FILE)
        _write_json(temporary / METRICS_FILE, metrics)
        _write_json(temporary / METADATA_FILE, metadata)
        if target.exists():
            raise VersionExistsError(f"La version ya existe: {target}")
        try:
            temporary.rename(target)
        except OSError as error:
            if target.exists():
                raise VersionExistsError(f"La version ya existe: {target}") from error
            raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return target


def load_version(path: str | Path) -> tuple[Pipeline, dict]:
    """Carga (pipeline, metadata) desde la carpeta o desde su modelo.joblib.

    Requiere que src sea importable, porque el Pipeline guarda una referencia a
    src.features.prepare_model_input. Carga solo modelos de confianza: joblib usa pickle.
    """
    path = Path(path)
    if path.is_dir():
        folder = path
    elif path.is_file() and path.name == MODEL_FILE:
        folder = path.parent
    else:
        raise VersionNotFoundError(f"No se encontro la version del modelo: {path}")

    model_path = folder / MODEL_FILE
    metadata_path = folder / METADATA_FILE
    for required in (model_path, metadata_path):
        if not required.is_file():
            raise VersionNotFoundError(f"Falta el archivo de la version: {required}")

    try:
        pipeline = joblib.load(model_path)
    except Exception as error:  # pickle puede lanzar casi cualquier excepcion
        raise VersionLoadError(f"No se pudo cargar {model_path}: {error}") from error
    try:
        with metadata_path.open(encoding="utf-8") as file:
            metadata = json.load(file)
    except (OSError, ValueError) as error:
        raise VersionLoadError(f"No se pudo leer {metadata_path}: {error}") from error
    return pipeline, metadata
