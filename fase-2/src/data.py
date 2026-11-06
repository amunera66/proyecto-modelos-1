"""Lectura, validacion, limpieza y filtrado del CSV crudo de la Fase 1."""

import hashlib
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from src import config


class DataError(Exception):
    """Error previsible al leer o validar los datos."""


class MissingColumnsError(DataError):
    """Faltan columnas requeridas en el CSV."""

    def __init__(self, missing: Iterable[str]):
        self.missing = sorted(missing)
        super().__init__(f"Faltan columnas requeridas: {', '.join(self.missing)}")


def validate_columns(df: pd.DataFrame, required: Iterable[str] = config.RAW_COLUMNS) -> None:
    """Lanza MissingColumnsError si alguna columna requerida no esta en df."""
    missing = set(required) - set(df.columns)
    if missing:
        raise MissingColumnsError(missing)


def read_raw_csv(path: str | Path) -> pd.DataFrame:
    """Lee el CSV crudo y valida que tenga las columnas requeridas."""
    path = Path(path)
    if not path.is_file():
        raise DataError(f"No se encontro el archivo de datos: {path}")
    try:
        df = pd.read_csv(path, low_memory=False)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise DataError(f"No se pudo leer el CSV {path}: {error}") from error
    validate_columns(df)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica la limpieza de la Fase 1, en el mismo orden.

    1. Quita las filas con id no numerico (filas corruptas por parsing).
    2. Quita las filas sin vote_average (primera mitad de las lineas partidas).
    3. Convierte id, budget y popularity (si existe) a tipo numerico.
    4. Quita los duplicados por id y conserva la primera aparicion.
    """
    id_numeric = pd.to_numeric(df[config.ID_COLUMN], errors="coerce")
    clean = df[id_numeric.notna()].copy()
    clean = clean.drop(index=clean[clean[config.TARGET].isna()].index)

    clean[config.ID_COLUMN] = clean[config.ID_COLUMN].astype("int64")
    clean["budget"] = pd.to_numeric(clean["budget"], errors="raise")
    if "popularity" in clean.columns:
        clean["popularity"] = pd.to_numeric(clean["popularity"], errors="raise")

    return clean.drop_duplicates(subset=config.ID_COLUMN, keep="first").reset_index(drop=True)


def apply_filters(df: pd.DataFrame, min_votes: int = config.MIN_VOTES) -> pd.DataFrame:
    """Conserva las peliculas estrenadas con mas de min_votes votos."""
    released = df[config.STATUS_COLUMN] == config.STATUS_RELEASED
    enough_votes = df[config.VOTE_COUNT_COLUMN] > min_votes
    return df[released & enough_votes].copy()


def describe_dataset(
    path: str | Path,
    rows_raw: int,
    rows_clean: int,
    rows_filtered: int,
    min_votes: int = config.MIN_VOTES,
) -> dict:
    """Arma la seccion "datos" de metadata.json. Solo guarda el nombre del archivo."""
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "fuente": config.DATASET_SOURCE,
        "url": config.DATASET_URL,
        "archivo": path.name,
        "tamano_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "filas_antes_limpieza": rows_raw,
        "filas_despues_limpieza": rows_clean,
        "filas_tras_filtros": rows_filtered,
        "filtros": {
            "status": config.STATUS_RELEASED,
            "vote_count_minimo_exclusivo": min_votes,
        },
    }
