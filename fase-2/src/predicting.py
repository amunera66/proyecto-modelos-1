"""Prediccion con una version guardada. Nunca entrena ni reajusta transformaciones."""

import csv
import uuid
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src import data, versioning

PREDICTION_COLUMN = "prediccion"
IDENTIFIER_COLUMNS = ("id", "title")
NUMERIC_KINDS = ("numerica", "binaria")
# Textos que cuentan como celda nula en las columnas del contrato
NULL_TEXTS = ("", "NA", "N/A", "NaN", "nan", "NULL", "null", "None", "<NA>")
MAX_EXAMPLES = 5


class PredictionError(Exception):
    """Error previsible en la entrada o en la prediccion."""


@dataclass(frozen=True)
class PredictionResult:
    """Lo que produjo una prediccion."""

    output_path: Path
    rows: int
    ignored_columns: tuple[str, ...]


def _reject_extra_fields(path: Path, columns: int) -> None:
    """Rechaza filas con datos de mas: index_col=False los descartaria sin avisar."""
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            extra = [cell for cell in row[columns:] if cell.strip()]
            if extra:
                raise PredictionError(
                    f"La linea {reader.line_num} del CSV {path} tiene mas campos que "
                    f"el encabezado: {extra!r}"
                )


def read_input(path: str | Path) -> pd.DataFrame:
    """Lee el CSV como texto, para validar cada celda y copiarla tal como vino.

    index_col=False evita que pandas use la primera columna como indice cuando
    las filas traen una coma final, lo que desplazaria las demas columnas.
    """
    path = Path(path)
    if not path.is_file():
        raise PredictionError(f"No se encontro el archivo de entrada: {path}")
    try:
        with warnings.catch_warnings():
            # El aviso de la coma final sobra: _reject_extra_fields cubre lo importante
            warnings.simplefilter("ignore", pd.errors.ParserWarning)
            df = pd.read_csv(path, dtype=str, keep_default_na=False, index_col=False)
        _reject_extra_fields(path, len(df.columns))
    except (ValueError, csv.Error) as error:  # incluye los errores de pandas y de UTF-8
        raise PredictionError(f"No se pudo leer el CSV {path}: {error}") from error
    if df.empty:
        raise PredictionError(f"El CSV de entrada no tiene filas: {path}")
    return df


def _read_contract(metadata: dict) -> list[dict]:
    contract = metadata.get("contrato_entrada")
    if not contract:
        raise PredictionError("El metadata.json del modelo no trae el contrato de entrada.")
    return contract


def _describe_cells(values: pd.Series, mask: pd.Series) -> str:
    """Describe las primeras celdas marcadas, con filas de datos contadas desde 1."""
    cells = values[mask]
    examples = ", ".join(
        f"fila {row + 1}: {value!r}" for row, value in cells.head(MAX_EXAMPLES).items()
    )
    remaining = len(cells) - MAX_EXAMPLES
    return examples + (f" y {remaining} mas" if remaining > 0 else "")


def _to_numeric(values: pd.Series, name: str, is_null: pd.Series) -> pd.Series:
    numbers = pd.to_numeric(values.where(~is_null), errors="coerce")
    invalid = ~is_null & (numbers.isna() | np.isinf(numbers))
    if invalid.any():
        raise PredictionError(
            f"La columna {name} tiene valores no numericos: {_describe_cells(values, invalid)}"
        )
    return numbers.astype(float)


def _validate_column(raw: pd.DataFrame, feature: dict) -> pd.Series:
    """Convierte una columna segun el contrato y valida nulos y valores permitidos."""
    name = feature["nombre"]
    values = raw[name]
    is_null = values.str.strip().isin(NULL_TEXTS)

    if not feature["nulos_permitidos"] and is_null.any():
        raise PredictionError(
            f"La columna {name} no admite nulos: {_describe_cells(values, is_null)}"
        )
    if feature["tipo"] not in NUMERIC_KINDS:
        return values.astype(object).where(~is_null, np.nan)

    numbers = _to_numeric(values, name, is_null)
    valid_values = feature.get("valores_validos")
    if valid_values is not None:
        not_valid = ~is_null & ~numbers.isin(valid_values)
        if not_valid.any():
            allowed = " o ".join(str(value) for value in valid_values)
            raise PredictionError(
                f"La columna {name} solo acepta {allowed}: {_describe_cells(values, not_valid)}"
            )
    return numbers


def prepare_input(raw: pd.DataFrame, contract: list[dict]) -> pd.DataFrame:
    """Devuelve las columnas del contrato, en su orden y con sus tipos."""
    names = [feature["nombre"] for feature in contract]
    data.validate_columns(raw, names)
    return pd.DataFrame({feature["nombre"]: _validate_column(raw, feature) for feature in contract})


def predict_rows(model: Pipeline, features: pd.DataFrame) -> np.ndarray:
    """Devuelve una prediccion por fila, en el orden de entrada."""
    try:
        predictions = model.predict(features)
    except (ValueError, TypeError) as error:
        raise PredictionError(f"El modelo no pudo predecir con esta entrada: {error}") from error
    return predictions


def _output_columns(raw: pd.DataFrame, contract: list[dict]) -> tuple[list[str], list[str]]:
    """Devuelve las columnas que se copian a la salida y las que se ignoran."""
    names = [feature["nombre"] for feature in contract]
    identifiers = [column for column in IDENTIFIER_COLUMNS if column in raw.columns]
    ignored = [column for column in raw.columns if column not in identifiers + names]
    return identifiers + names, ignored


def _write_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Escribe en un temporal de la misma carpeta y lo renombra al final."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.parent / f".{output_path.name}.{uuid.uuid4().hex}.tmp"
    try:
        df.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
        temporary.replace(output_path)
    finally:
        temporary.unlink(missing_ok=True)


def predict_file(
    model_path: str | Path, input_path: str | Path, output_path: str | Path
) -> PredictionResult:
    """Valida la entrada, predice y escribe la salida solo si todo salio bien."""
    output_path = Path(output_path)
    if output_path.exists() and output_path.resolve() == Path(input_path).resolve():
        raise PredictionError("La salida no puede ser el mismo archivo de entrada.")

    model, metadata = versioning.load_version(model_path)
    contract = _read_contract(metadata)
    raw = read_input(input_path)
    features = prepare_input(raw, contract)
    predictions = predict_rows(model, features)

    kept_columns, ignored = _output_columns(raw, contract)
    output = raw[kept_columns].assign(**{PREDICTION_COLUMN: predictions})
    _write_csv(output, output_path)
    return PredictionResult(output_path, len(output), tuple(ignored))
