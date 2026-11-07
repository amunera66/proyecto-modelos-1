"""Configuracion compartida: columnas, filtros, contrato de entrada y defaults."""

from dataclasses import dataclass

# --- Defaults de ejecucion ---
SEED = 42
TEST_SIZE = 0.2
MIN_VOTES = 10
CV_FOLDS = 5
SPLIT_STRATEGY = "group"

# --- Dataset ---
DATASET_SOURCE = "The Movies Dataset (Rounak Banik), Kaggle"
DATASET_URL = "https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset"
DATASET_FILE = "movies_metadata.csv"

# --- Columnas del CSV crudo ---
ID_COLUMN = "id"
TARGET = "vote_average"
VOTE_COUNT_COLUMN = "vote_count"
STATUS_COLUMN = "status"
RAW_COLUMNS = (
    ID_COLUMN,
    "budget",
    "runtime",
    "release_date",
    "belongs_to_collection",
    "genres",
    "original_language",
    STATUS_COLUMN,
    VOTE_COUNT_COLUMN,
    TARGET,
)

# --- Filtros fijos de poblacion ---
# Se conserva solo STATUS_RELEASED y vote_count estrictamente mayor que min_votes.
STATUS_RELEASED = "Released"

# --- Columnas en las que 0 significa "dato no reportado" ---
ZERO_AS_MISSING_COLUMNS = ("budget", "runtime")


@dataclass(frozen=True)
class Feature:
    """Una predictora del contrato de entrada."""

    name: str
    kind: str  # "numerica", "binaria" o "categorica"
    nullable: bool
    valid_values: tuple | None = None


# --- Sexta predictora ---
# Cambiar SIXTH_FEATURE solo cambia lo que se entrene despues: cada Pipeline
# guarda su propia opcion, asi que las versiones ya guardadas no se afectan.
SIXTH_FEATURE_OPTIONS = ("es_franquicia", "es_secuela")
SIXTH_FEATURE = "es_secuela"
# Solo la usan los modelos guardados sin su opcion (los del Paso 1), que siempre
# se entrenaron con esta variable. No debe cambiar aunque cambie SIXTH_FEATURE.
LEGACY_SIXTH_FEATURE = "es_franquicia"


def get_features(sixth_feature: str = SIXTH_FEATURE) -> tuple[Feature, ...]:
    """Devuelve las 6 predictoras, en el orden del contrato."""
    if sixth_feature not in SIXTH_FEATURE_OPTIONS:
        raise ValueError(
            f"Sexta predictora invalida: {sixth_feature!r}. "
            f"Opciones: {', '.join(SIXTH_FEATURE_OPTIONS)}"
        )
    return (
        Feature("budget", "numerica", nullable=True),
        Feature("runtime", "numerica", nullable=True),
        Feature("release_year", "numerica", nullable=True),
        Feature(sixth_feature, "binaria", nullable=False, valid_values=(0, 1)),
        Feature("genero_principal", "categorica", nullable=True),
        Feature("original_language", "categorica", nullable=True),
    )


def get_feature_names(sixth_feature: str = SIXTH_FEATURE) -> tuple[str, ...]:
    """Devuelve los nombres de las 6 predictoras, en el orden del contrato."""
    return tuple(feature.name for feature in get_features(sixth_feature))


FEATURES = get_features()
FEATURE_NAMES = get_feature_names()
NUMERIC_FEATURES = tuple(f.name for f in FEATURES if f.kind == "numerica")
BINARY_FEATURES = tuple(f.name for f in FEATURES if f.kind == "binaria")
CATEGORICAL_FEATURES = tuple(f.name for f in FEATURES if f.kind == "categorica")

# --- Valores de las predictoras y del preprocesamiento ---
NO_GENRE = "sin_genero"
MIN_CATEGORY_FREQUENCY = 0.01

# --- Metadatos ---
PROBLEM_TYPE = "regresion"
PRIMARY_METRIC = "RMSE"
TARGET_HORIZON = (
    "no verificada: vote_average es el promedio acumulado hasta una fecha de descarga "
    "desconocida; el dataset cubre estrenos hasta julio de 2017, segun replicas de su "
    "descripcion (ver docs/decisiones.md)"
)
REQUIREMENTS_FILE = "requirements.txt"


def input_contract(sixth_feature: str = SIXTH_FEATURE) -> list[dict]:
    """Devuelve el contrato de entrada en un formato que se puede guardar en JSON."""
    return [
        {
            "nombre": feature.name,
            "tipo": feature.kind,
            "nulos_permitidos": feature.nullable,
            "valores_validos": (
                None if feature.valid_values is None else list(feature.valid_values)
            ),
        }
        for feature in get_features(sixth_feature)
    ]
