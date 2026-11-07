"""Construccion de los Pipelines del modelo y del baseline."""

from sklearn.base import RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src import config
from src.features import prepare_model_input

# Valores efectivos del modelo de la Fase 1. early_stopping="auto" activa la
# parada temprana solo cuando el entrenamiento tiene mas de 10.000 filas.
HGB_PARAMS = {
    "loss": "squared_error",
    "quantile": None,
    "learning_rate": 0.1,
    "max_iter": 100,
    "max_leaf_nodes": 31,
    "max_depth": None,
    "min_samples_leaf": 20,
    "l2_regularization": 0.0,
    "max_features": 1.0,
    "max_bins": 255,
    "categorical_features": "from_dtype",
    "monotonic_cst": None,
    "interaction_cst": None,
    "warm_start": False,
    "early_stopping": "auto",
    "scoring": "loss",
    "validation_fraction": 0.1,
    "n_iter_no_change": 10,
    "tol": 1e-7,
    "verbose": 0,
}


def _build_encoder() -> OneHotEncoder:
    return OneHotEncoder(
        min_frequency=config.MIN_CATEGORY_FREQUENCY,
        handle_unknown="infrequent_if_exist",
        sparse_output=False,
    )


def _build_preprocessor(sixth_feature: str) -> ColumnTransformer:
    numeric = Pipeline(steps=[
        ("imputar", SimpleImputer(strategy="median", add_indicator=True)),
        ("escalar", StandardScaler()),
    ])
    genre = Pipeline(steps=[
        ("imputar", SimpleImputer(strategy="constant", fill_value=config.NO_GENRE)),
        ("codificar", _build_encoder()),
    ])
    language = Pipeline(steps=[
        ("imputar", SimpleImputer(strategy="most_frequent")),
        ("codificar", _build_encoder()),
    ])
    return ColumnTransformer(transformers=[
        ("numericas", numeric, list(config.NUMERIC_FEATURES)),
        ("binarias", "passthrough", [sixth_feature]),
        ("genero", genre, ["genero_principal"]),
        ("idioma", language, ["original_language"]),
    ])


def _build(regressor: RegressorMixin, sixth_feature: str) -> Pipeline:
    config.get_features(sixth_feature)  # rechaza una opcion invalida al construir
    first_step = FunctionTransformer(
        prepare_model_input,
        feature_names_out="one-to-one",
        kw_args={"sixth_feature": sixth_feature},
    )
    return Pipeline(steps=[
        ("ceros_a_nan", first_step),
        ("preprocesamiento", _build_preprocessor(sixth_feature)),
        ("modelo", regressor),
    ])


def build_pipeline(
    seed: int = config.SEED, sixth_feature: str = config.SIXTH_FEATURE
) -> Pipeline:
    """Devuelve el Pipeline completo, sin ajustar, con HistGradientBoosting."""
    return _build(
        HistGradientBoostingRegressor(random_state=seed, **HGB_PARAMS), sixth_feature
    )


def build_baseline(sixth_feature: str = config.SIXTH_FEATURE) -> Pipeline:
    """Devuelve el baseline: el mismo preprocesamiento y DummyRegressor (media)."""
    return _build(DummyRegressor(strategy="mean"), sixth_feature)
