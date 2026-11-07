"""Particion de los datos y validacion cruzada, aleatorias o por grupos."""

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.model_selection import (
    GroupKFold,
    GroupShuffleSplit,
    KFold,
    cross_validate,
    train_test_split,
)

from src import config
from src.features import collection_ids

SPLIT_STRATEGIES = ("random", "group")


def _validate_strategy(strategy: str) -> None:
    if strategy not in SPLIT_STRATEGIES:
        raise ValueError(
            f"Estrategia invalida: {strategy!r}. Opciones: {', '.join(SPLIT_STRATEGIES)}"
        )


def make_groups(df: pd.DataFrame) -> pd.Series:
    """Asigna un grupo a cada pelicula.

    El grupo es la coleccion. Una pelicula sin coleccion es su propio grupo; los
    prefijos evitan que el id de una pelicula choque con el de una coleccion.
    """
    ids = collection_ids(df)
    has_collection = ids.notna()
    groups = "pelicula_" + df[config.ID_COLUMN].astype(str)
    groups[has_collection] = "coleccion_" + ids[has_collection].astype(str)
    return groups


def split_data(
    df: pd.DataFrame,
    strategy: str = config.SPLIT_STRATEGY,
    test_size: float = config.TEST_SIZE,
    seed: int = config.SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (train, test).

    "random" reproduce la particion de la Fase 1. "group" nunca deja una
    coleccion en ambos lados, pero test_size se aplica a los grupos, no a las
    filas, asi que la proporcion real de filas puede variar un poco.
    """
    _validate_strategy(strategy)
    if strategy == "random":
        return train_test_split(df, test_size=test_size, random_state=seed)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_rows, test_rows = next(splitter.split(df, groups=make_groups(df)))
    return df.iloc[train_rows], df.iloc[test_rows]


def make_cv(
    strategy: str = config.SPLIT_STRATEGY, seed: int = config.SEED
) -> KFold | GroupKFold:
    """Devuelve el divisor de CV de la estrategia."""
    _validate_strategy(strategy)
    if strategy == "random":
        return KFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=seed)
    return GroupKFold(n_splits=config.CV_FOLDS)


def cross_validate_model(
    estimator: BaseEstimator,
    train_df: pd.DataFrame,
    strategy: str = config.SPLIT_STRATEGY,
    feature_names: Iterable[str] = config.FEATURE_NAMES,
    seed: int = config.SEED,
    target: str = config.TARGET,
) -> dict[str, float]:
    """Hace CV solo con train y devuelve MAE, RMSE, su desviacion y R2."""
    result = cross_validate(
        estimator,
        train_df[list(feature_names)],
        train_df[target],
        groups=make_groups(train_df) if strategy == "group" else None,
        cv=make_cv(strategy, seed),
        scoring={
            "MAE": "neg_mean_absolute_error",
            "RMSE": "neg_root_mean_squared_error",
            "R2": "r2",
        },
    )
    return {
        "MAE": float(-np.mean(result["test_MAE"])),
        "RMSE": float(-np.mean(result["test_RMSE"])),
        "RMSE_desv": float(np.std(result["test_RMSE"])),
        "R2": float(np.mean(result["test_R2"])),
    }
