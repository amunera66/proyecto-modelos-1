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


def prepare_model_input(
    X: pd.DataFrame, sixth_feature: str = config.LEGACY_SIXTH_FEATURE
) -> pd.DataFrame:
    """Primera etapa del Pipeline: ordena las 6 predictoras y convierte los ceros.

    Debe ser una funcion con nombre a nivel de modulo, porque el .joblib la
    guarda por referencia. Ademas debe devolver las columnas en el orden del
    contrato: con feature_names_out="one-to-one", FunctionTransformer renombra
    por posicion una salida en otro orden, y las predicciones saldrian mal sin
    ningun error. sixth_feature llega por kw_args, asi que cada Pipeline guarda
    la suya y no depende del default de config al cargarse. Su valor por defecto
    es para los modelos guardados sin kw_args: no lo cambies por SIXTH_FEATURE.
    """
    names = config.get_feature_names(sixth_feature)
    validate_columns(X, names)
    return zeros_to_nan(X[list(names)])


def first_genre(genres_text: str) -> str:
    """Devuelve el primer genero de la lista de TMDB, o NO_GENRE si esta vacia."""
    genres = ast.literal_eval(genres_text)
    return genres[0]["name"] if genres else config.NO_GENRE


def collection_ids(df: pd.DataFrame) -> pd.Series:
    """Devuelve el id de la coleccion de cada fila, o nulo si no tiene coleccion."""
    collections = df["belongs_to_collection"].dropna()
    ids = collections.apply(lambda text: ast.literal_eval(text)["id"])
    return ids.reindex(df.index).astype("Int64")


def add_sequel_feature(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega es_secuela a una copia de df. Debe recibir el dataset limpio.

    Va ANTES de los filtros de status y votos: una precuela con pocos votos
    sigue siendo precuela.

    es_secuela es 1 si en la coleccion de la pelicula existe otra con
    release_date estrictamente anterior. Es 0 en estos casos:
    - la pelicula no tiene coleccion;
    - es la primera de su coleccion; si varias empatan en la primera fecha,
      todas valen 0, porque ninguna es estrictamente anterior;
    - su release_date es nula o invalida: no se puede afirmar que sea secuela.
    Las fechas nulas de las demas peliculas de la coleccion no cuentan.
    """
    dates = pd.to_datetime(df["release_date"], errors="coerce")
    first_date = dates.groupby(collection_ids(df)).transform("min")
    result = df.copy()
    result["es_secuela"] = (dates > first_date).astype(int)
    return result


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las predictoras a una copia de df, fila por fila, igual que la Fase 1."""
    result = zeros_to_nan(df)
    result["release_year"] = pd.to_datetime(result["release_date"], errors="coerce").dt.year
    result["es_franquicia"] = result["belongs_to_collection"].notna().astype(int)
    result["genero_principal"] = result["genres"].apply(first_genre)
    return result
