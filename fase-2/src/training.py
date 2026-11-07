"""Entrenamiento completo: datos, particion, CV, evaluacion y guardado."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline

from src import config, data, features, pipeline, splitting, versioning

METRICS = ("MAE", "RMSE", "R2")


class TrainingError(Exception):
    """Error previsible en las opciones o en la preparacion del entrenamiento."""


@dataclass(frozen=True)
class TrainingOptions:
    """Opciones de un entrenamiento."""

    data_path: str | Path
    version: str
    target: str = config.TARGET
    output_dir: str | Path = "models"
    seed: int = config.SEED
    test_size: float = config.TEST_SIZE
    min_votes: int = config.MIN_VOTES
    split_strategy: str = config.SPLIT_STRATEGY
    sixth_feature: str = config.SIXTH_FEATURE


@dataclass(frozen=True)
class TrainingResult:
    """Lo que produjo un entrenamiento."""

    version_dir: Path
    metrics: dict
    metadata: dict


def _check_version_is_available(version: str, output_dir: str | Path) -> None:
    """Falla antes de entrenar. save_version vuelve a comprobarlo al guardar."""
    if not versioning.VERSION_PATTERN.fullmatch(version):
        raise TrainingError(
            f"Version invalida: {version!r}. Usa letras, numeros, punto, guion o guion bajo."
        )
    target = Path(output_dir) / version
    if target.exists():
        raise versioning.VersionExistsError(f"La version ya existe: {target}")


def _prepare_target(df: pd.DataFrame, target: str, feature_names: tuple[str, ...]) -> pd.DataFrame:
    """Comprueba que el objetivo sea numerico, completo y distinto de las predictoras."""
    if target in feature_names:
        raise TrainingError(f"El objetivo {target!r} no puede ser una predictora.")
    values = pd.to_numeric(df[target], errors="coerce")
    if values.isna().any():
        raise TrainingError(f"El objetivo {target!r} tiene valores nulos o no numericos.")
    return df.assign(**{target: values})


def load_model_data(options: TrainingOptions) -> tuple[pd.DataFrame, dict]:
    """Lee, valida, limpia, filtra y deriva. Devuelve los datos y su descripcion."""
    raw = data.read_raw_csv(options.data_path)
    data.validate_columns(raw, [options.target])
    try:
        clean = features.add_sequel_feature(data.clean_data(raw))
        filtered = data.apply_filters(clean, options.min_votes)
        df = features.derive_features(filtered)
    except (ValueError, SyntaxError, TypeError, KeyError) as error:
        raise data.DataError(f"El CSV tiene valores que no se pueden procesar: {error}") from error
    if df.empty:
        raise data.DataError(
            f"No quedan peliculas tras los filtros (min_votes={options.min_votes})."
        )
    feature_names = config.get_feature_names(options.sixth_feature)
    df = _prepare_target(df, options.target, feature_names)
    data_info = data.describe_dataset(
        options.data_path, len(raw), len(clean), len(filtered), options.min_votes
    )
    return df, data_info


def _split(df: pd.DataFrame, options: TrainingOptions) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        train, test = splitting.split_data(
            df, options.split_strategy, options.test_size, options.seed
        )
    except ValueError as error:
        raise TrainingError(f"No se pudo partir los datos: {error}") from error
    units = splitting.make_groups(train).nunique() if options.split_strategy == "group" else len(train)
    if units < config.CV_FOLDS:
        raise TrainingError(
            f"Entrenamiento con {units} unidades: la CV necesita al menos {config.CV_FOLDS}."
        )
    return train, test


def describe_partition(
    df: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame, options: TrainingOptions
) -> dict:
    """Arma la seccion "particion" de metadata.json."""
    train_groups = set(splitting.make_groups(train))
    test_groups = set(splitting.make_groups(test))
    return {
        "estrategia": options.split_strategy,
        "test_size": options.test_size,
        "n_train": len(train),
        "n_test": len(test),
        "n_grupos": int(splitting.make_groups(df).nunique()),
        "n_grupos_train": len(train_groups),
        "n_grupos_test": len(test_groups),
        "grupos_compartidos": len(train_groups & test_groups),
        "cv": {
            "tipo": type(splitting.make_cv(options.split_strategy, options.seed)).__name__,
            "folds": config.CV_FOLDS,
        },
    }


def _test_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(root_mean_squared_error(y_true, y_pred)),
        "R2": float(r2_score(y_true, y_pred)),
    }


def _evaluate(
    estimator: Pipeline,
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_names: list[str],
    options: TrainingOptions,
) -> dict:
    """Hace la CV sobre train, ajusta estimator con train y evalua en prueba."""
    cv = splitting.cross_validate_model(
        estimator, train, options.split_strategy, feature_names, options.seed, options.target
    )
    estimator.fit(train[feature_names], train[options.target])
    return {
        "algoritmo": type(estimator.named_steps["modelo"]).__name__,
        "prueba": _test_metrics(test[options.target], estimator.predict(test[feature_names])),
        "cv": {
            metric: {"media": cv[metric], "desviacion": cv[f"{metric}_desv"]}
            for metric in METRICS
        },
    }


def train_model(options: TrainingOptions) -> TrainingResult:
    """Ejecuta el proceso completo y guarda una version nueva."""
    _check_version_is_available(options.version, options.output_dir)
    feature_names = list(config.get_feature_names(options.sixth_feature))

    df, data_info = load_model_data(options)
    train, test = _split(df, options)

    model = pipeline.build_pipeline(options.seed, options.sixth_feature)
    baseline = pipeline.build_baseline(options.sixth_feature)
    metrics = {
        "modelo": _evaluate(model, train, test, feature_names, options),
        "baseline": _evaluate(baseline, train, test, feature_names, options),
    }

    partition = describe_partition(df, train, test, options)
    metadata = versioning.build_metadata(
        options.version, model, options.seed, data_info, partition, options.target
    )
    version_dir = versioning.save_version(
        model, metrics, metadata, options.output_dir, options.version
    )
    return TrainingResult(version_dir, metrics, metadata)


def format_summary(result: TrainingResult) -> str:
    """Devuelve el resumen que se muestra al terminar."""
    partition = result.metadata["particion"]
    lines = [
        f"Version {result.metadata['version']} guardada.",
        f"Particion {partition['estrategia']}: {partition['n_train']} filas de entrenamiento, "
        f"{partition['n_test']} de prueba, {partition['grupos_compartidos']} grupos compartidos.",
        f"Sexta predictora: {result.metadata['sexta_predictora']}.",
        "",
        f"{'':<10}{'CV MAE':>9}{'CV RMSE':>9}{'CV R2':>9}{'MAE':>9}{'RMSE':>9}{'R2':>9}",
    ]
    for name, key in (("Modelo", "modelo"), ("Baseline", "baseline")):
        values = result.metrics[key]
        cv = [values["cv"][metric]["media"] for metric in METRICS]
        test = [values["prueba"][metric] for metric in METRICS]
        lines.append(f"{name:<10}" + "".join(f"{value:>9.4f}" for value in cv + test))
    lines += ["", "Archivos generados:"]
    file_names = (versioning.MODEL_FILE, versioning.METRICS_FILE, versioning.METADATA_FILE)
    lines += [f"  {result.version_dir / file_name}" for file_name in file_names]
    return "\n".join(lines)
