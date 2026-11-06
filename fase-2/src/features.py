"""Derivacion de las 6 predictoras desde las columnas crudas."""

import ast

import numpy as np
import pandas as pd

from src import config
from src.data import validate_columns


def zeros_to_nan(X: pd.DataFrame) -> pd.DataFrame:
    """Convierte en NaN los 0 de budget y runtime, que significan "no reportado"."""
    result = X.copy()
    for column in config.ZERO_AS_MISSING_COLUMNS:
        result[column] = result[column].replace(0, np.nan)
    return result


def prepare_model_input(X: pd.DataFrame) -> pd.DataFrame:
    """Primera etapa del Pipeline: ordena las 6 predictoras y convierte los ceros.

    Debe ser una funcion con nombre a nivel de modulo, porque el .joblib la
    guarda por referencia. Ademas debe devolver las columnas en el orden del
    contrato: con feature_names_out="one-to-one", FunctionTransformer renombra
    por posicion una salida en otro orden, y las predicciones saldrian mal sin
    ningun error.
    """
    validate_columns(X, config.FEATURE_NAMES)
    return zeros_to_nan(X[list(config.FEATURE_NAMES)])


def first_genre(genres_text: str) -> str:
    """Devuelve el primer genero de la lista de TMDB, o NO_GENRE si esta vacia."""
    genres = ast.literal_eval(genres_text)
    return genres[0]["name"] if genres else config.NO_GENRE


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las predictoras a una copia de df, fila por fila, igual que la Fase 1."""
    result = zeros_to_nan(df)
    result["release_year"] = pd.to_datetime(result["release_date"], errors="coerce").dt.year
    result["es_franquicia"] = result["belongs_to_collection"].notna().astype(int)
    result["genero_principal"] = result["genres"].apply(first_genre)
    return result
