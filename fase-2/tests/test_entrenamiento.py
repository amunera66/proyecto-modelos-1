"""Entrenamiento y almacenamiento, datos sinteticos, filtros y particion."""

import json

import pandas as pd
import pytest

import conftest as ayuda
from src import config, data, features, splitting, training, versioning


@pytest.fixture(scope="module")
def datos_modelo(csv_crudo) -> pd.DataFrame:
    opciones = training.TrainingOptions(data_path=csv_crudo, version="sin-uso")
    return training.load_model_data(opciones)[0]


def _fila(df: pd.DataFrame, id_pelicula: int) -> pd.Series:
    return df.loc[df[config.ID_COLUMN] == id_pelicula].iloc[0]


def test_csv_sintetico_cubre_los_casos_pedidos(csv_crudo, datos_modelo):
    crudo = pd.read_csv(csv_crudo, low_memory=False)

    assert list(crudo.columns) == list(config.RAW_COLUMNS)
    assert len(crudo) == 200
    assert set(datos_modelo["es_secuela"]) == {0, 1}
    assert crudo["belongs_to_collection"].isna().any()
    assert crudo["belongs_to_collection"].notna().sum() >= 40
    assert crudo["budget"].isna().any() and (crudo["budget"] == "0.0").any()
    assert crudo["runtime"].isna().any() and (crudo["runtime"] == 0).any()
    assert (crudo["vote_count"] <= 10).any()
    assert (crudo["status"].dropna() != "Released").any()


def test_csv_sintetico_es_reproducible():
    pd.testing.assert_frame_equal(ayuda.generar_csv_crudo(), ayuda.generar_csv_crudo())


def test_guarda_los_tres_archivos_y_el_modelo_se_carga(entrenado):
    carpeta = entrenado.dir_version

    assert sorted(archivo.name for archivo in carpeta.iterdir()) == [
        "metadata.json",
        "metrics.json",
        "modelo.joblib",
    ]
    assert carpeta.parent == entrenado.dir_modelos
    assert not list(entrenado.dir_modelos.glob(".tmp-*"))

    for ruta in (carpeta, carpeta / versioning.MODEL_FILE):
        modelo, metadata = versioning.load_version(ruta)
        assert list(modelo.named_steps) == ["ceros_a_nan", "preprocesamiento", "modelo"]
        assert metadata["version"] == ayuda.VERSION_ENTRENADA


def test_metrics_trae_el_modelo_y_el_baseline(entrenado):
    metricas = json.loads((entrenado.dir_version / "metrics.json").read_text(encoding="utf-8"))

    assert set(metricas) == {"modelo", "baseline"}
    assert metricas["modelo"]["algoritmo"] == "HistGradientBoostingRegressor"
    assert metricas["baseline"]["algoritmo"] == "DummyRegressor"
    for bloque in metricas.values():
        assert set(bloque["prueba"]) == {"MAE", "RMSE", "R2"}
        assert set(bloque["cv"]) == {"MAE", "RMSE", "R2"}
        for valores in bloque["cv"].values():
            assert set(valores) == {"media", "desviacion"}
    # El modelo aprende la senal del CSV sintetico; el baseline no
    assert metricas["modelo"]["prueba"]["RMSE"] < metricas["baseline"]["prueba"]["RMSE"]


def test_metadata_cumple_el_esquema_y_el_contrato(entrenado, csv_crudo):
    metadata = json.loads((entrenado.dir_version / "metadata.json").read_text(encoding="utf-8"))

    assert set(metadata) == set(versioning.METADATA_KEYS)
    assert metadata["version"] == ayuda.VERSION_ENTRENADA
    assert metadata["tipo_problema"] == "regresion"
    assert metadata["objetivo"] == "vote_average"
    assert metadata["algoritmo"] == "HistGradientBoostingRegressor"
    assert metadata["metrica_principal"] == "RMSE"
    assert metadata["semilla"] == config.SEED
    assert metadata["sexta_predictora"] == "es_secuela"
    assert metadata["hiperparametros"]["early_stopping"] is False
    assert metadata["git_commit"]

    contrato = metadata["contrato_entrada"]
    assert [columna["nombre"] for columna in contrato] == [
        "budget",
        "runtime",
        "release_year",
        "es_secuela",
        "genero_principal",
        "original_language",
    ]
    secuela = contrato[3]
    assert secuela["tipo"] == "binaria"
    assert secuela["nulos_permitidos"] is False
    assert secuela["valores_validos"] == [0, 1]

    datos = metadata["datos"]
    assert set(datos) == {
        "fuente",
        "url",
        "archivo",
        "tamano_bytes",
        "sha256",
        "filas_antes_limpieza",
        "filas_despues_limpieza",
        "filas_tras_filtros",
        "filtros",
    }
    assert datos["archivo"] == csv_crudo.name  # solo el nombre, sin la ruta
    assert datos["filas_antes_limpieza"] == 200
    assert datos["filtros"] == {"status": "Released", "vote_count_minimo_exclusivo": 10}

    particion = metadata["particion"]
    assert particion["estrategia"] == "group"
    assert particion["grupos_compartidos"] == 0
    assert particion["n_train"] + particion["n_test"] == datos["filas_tras_filtros"]
    assert particion["cv"] == {"tipo": "GroupKFold", "folds": 5}


def test_limpieza_quita_filas_corruptas_y_duplicadas(csv_crudo):
    crudo = data.read_raw_csv(csv_crudo)
    limpio = data.clean_data(crudo)

    assert ayuda.ID_NO_NUMERICO in set(crudo[config.ID_COLUMN])
    assert len(limpio) == len(crudo) - 2  # la linea corrupta y un duplicado
    assert limpio[config.ID_COLUMN].is_unique
    assert pd.api.types.is_numeric_dtype(limpio["budget"])


def test_filtros_de_votos_y_status(datos_modelo):
    ids = set(datos_modelo[config.ID_COLUMN])

    assert (datos_modelo[config.VOTE_COUNT_COLUMN] > config.MIN_VOTES).all()
    assert (datos_modelo[config.STATUS_COLUMN] == config.STATUS_RELEASED).all()
    assert ayuda.ID_VOTOS_EN_EL_LIMITE not in ids
    assert ayuda.ID_VOTOS_SOBRE_EL_LIMITE in ids
    assert ayuda.ID_RUMORED not in ids
    assert ayuda.ID_STATUS_NULO not in ids
    assert ayuda.ID_PRECUELA_FILTRADA not in ids


def test_ceros_de_budget_y_runtime_quedan_como_nulos(datos_modelo):
    assert not (datos_modelo["budget"] == 0).any()
    assert not (datos_modelo["runtime"] == 0).any()
    assert datos_modelo["budget"].isna().any()
    assert datos_modelo["runtime"].isna().any()


def test_es_secuela_se_calcula_antes_de_los_filtros(csv_crudo, datos_modelo):
    limpio = data.clean_data(data.read_raw_csv(csv_crudo))
    calculada_despues = features.add_sequel_feature(data.apply_filters(limpio))

    # Calcularla despues perderia la precuela filtrada: la prueba si distingue
    assert _fila(calculada_despues, ayuda.ID_SECUELA_DE_FILTRADA)["es_secuela"] == 0
    assert _fila(datos_modelo, ayuda.ID_SECUELA_DE_FILTRADA)["es_secuela"] == 1


def test_es_secuela_en_empates_fechas_nulas_y_colecciones_unitarias(datos_modelo):
    for id_pelicula in ayuda.IDS_EMPATE_PRIMERA_FECHA:
        assert _fila(datos_modelo, id_pelicula)["es_secuela"] == 0
    assert _fila(datos_modelo, ayuda.ID_POSTERIOR_AL_EMPATE)["es_secuela"] == 1
    assert _fila(datos_modelo, ayuda.ID_SECUELA_FECHA_NULA)["es_secuela"] == 0
    assert _fila(datos_modelo, ayuda.ID_UNICA_DE_COLECCION)["es_secuela"] == 0
    sin_coleccion = datos_modelo[datos_modelo["belongs_to_collection"].isna()]
    assert (sin_coleccion["es_secuela"] == 0).all()


@pytest.mark.parametrize("semilla", [0, 7, 42, 123])
def test_particion_group_no_comparte_grupos(datos_modelo, semilla):
    train, test = splitting.split_data(datos_modelo, "group", seed=semilla)

    compartidos = set(splitting.make_groups(train)) & set(splitting.make_groups(test))
    assert compartidos == set()
    assert len(train) + len(test) == len(datos_modelo)


def test_particion_random_si_comparte_grupos_con_estos_datos(datos_modelo):
    """Control: sin esto, la prueba anterior podria pasar por falta de sagas."""
    train, test = splitting.split_data(datos_modelo, "random")

    assert set(splitting.make_groups(train)) & set(splitting.make_groups(test))


def test_train_por_consola_con_data_inexistente(ejecutar, tmp_path):
    salida = tmp_path / "modelos"

    proceso = ejecutar(
        "train.py",
        "--data", tmp_path / "no_existe.csv",
        "--version", "v-fallida",
        "--output-dir", salida,
    )

    assert proceso.returncode != 0
    assert "no_existe.csv" in proceso.stderr
    assert "Traceback" not in proceso.stderr
    assert not (salida / "v-fallida").exists()


def test_train_py_guarda_una_version(ejecutar_en_proceso, csv_crudo, tmp_path):
    proceso = ejecutar_en_proceso(
        "train.py", "--data", csv_crudo, "--version", "v-consola", "--output-dir", tmp_path
    )

    assert proceso.returncode == 0, proceso.stderr
    assert "Version v-consola guardada" in proceso.stdout
    versioning.load_version(tmp_path / "v-consola")
