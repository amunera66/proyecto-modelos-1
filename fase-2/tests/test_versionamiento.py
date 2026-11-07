"""Versiones: no se pisan, siguen cargando y las del repositorio funcionan."""

from dataclasses import replace

import joblib
import numpy as np
import pandas as pd
import pytest

from conftest import FASE2_DIR, leer_entrada, sha256_de_carpeta
from src import config, predicting, training, versioning

EJEMPLO = FASE2_DIR / "data" / "ejemplo_prediccion.csv"
MODELOS_REPO = FASE2_DIR / "models"


def _fechas(carpeta):
    return {archivo.name: archivo.stat().st_mtime_ns for archivo in carpeta.iterdir()}


def test_segunda_version_deja_intacta_la_primera(entrenado, csv_prediccion):
    primera = entrenado.dir_version
    hashes = sha256_de_carpeta(primera)
    fechas = _fechas(primera)

    segunda = training.train_model(
        replace(entrenado.opciones, version="v-segunda", seed=7)
    ).version_dir

    assert segunda != primera
    assert segunda.parent == primera.parent
    assert sha256_de_carpeta(primera) == hashes
    assert _fechas(primera) == fechas

    entrada_cruda = leer_entrada(csv_prediccion)
    predicciones = []
    for carpeta in (primera, segunda):
        modelo, metadata = versioning.load_version(carpeta)
        assert metadata["version"] == carpeta.name
        entrada = predicting.prepare_input(entrada_cruda, metadata["contrato_entrada"])
        predicciones.append(modelo.predict(entrada))
    # La semilla cambia la particion, asi que son dos modelos distintos
    assert not np.allclose(*predicciones)


def test_repetir_identificador_falla_sin_modificar_archivos(entrenado):
    carpeta = entrenado.dir_version
    hashes = sha256_de_carpeta(carpeta)
    fechas = _fechas(carpeta)

    with pytest.raises(versioning.VersionExistsError, match="ya existe"):
        training.train_model(entrenado.opciones)
    with pytest.raises(versioning.VersionExistsError, match="ya existe"):
        versioning.save_version(
            entrenado.pipeline_en_memoria,
            entrenado.resultado.metrics,
            entrenado.resultado.metadata,
            entrenado.dir_modelos,
            carpeta.name,
        )

    assert sha256_de_carpeta(carpeta) == hashes
    assert _fechas(carpeta) == fechas
    assert not list(entrenado.dir_modelos.glob(".tmp-*"))


def test_repetir_identificador_en_train_py(ejecutar_en_proceso, entrenado, csv_crudo):
    carpeta = entrenado.dir_version
    hashes = sha256_de_carpeta(carpeta)

    proceso = ejecutar_en_proceso(
        "train.py",
        "--data", csv_crudo,
        "--version", carpeta.name,
        "--output-dir", entrenado.dir_modelos,
    )

    assert proceso.returncode != 0
    assert "ya existe" in proceso.stderr
    assert sha256_de_carpeta(carpeta) == hashes


@pytest.mark.parametrize("version", ["..", "../fuera", "con espacio", ".oculta", ""])
def test_identificador_invalido_no_crea_nada(entrenado, tmp_path, version):
    opciones = replace(entrenado.opciones, version=version, output_dir=tmp_path)

    with pytest.raises(training.TrainingError, match="Version invalida"):
        training.train_model(opciones)

    assert list(tmp_path.iterdir()) == []


@pytest.fixture(scope="module")
def version_franquicia(entrenado, tmp_path_factory):
    """Una version entrenada con la sexta predictora de la Fase 1."""
    opciones = replace(
        entrenado.opciones,
        version="v-franquicia",
        output_dir=tmp_path_factory.mktemp("franquicia"),
        sixth_feature="es_franquicia",
    )
    return training.train_model(opciones).version_dir


def test_modelo_con_es_franquicia_se_carga_y_predice(version_franquicia, csv_prediccion, tmp_path):
    entrada = leer_entrada(csv_prediccion).rename(columns={"es_secuela": "es_franquicia"})
    ruta = tmp_path / "entrada.csv"
    entrada.to_csv(ruta, index=False, encoding="utf-8")
    salida = tmp_path / "salida.csv"

    _, metadata = versioning.load_version(version_franquicia)
    resultado = predicting.predict_file(version_franquicia, ruta, salida)

    assert metadata["sexta_predictora"] == "es_franquicia"
    assert [c["nombre"] for c in metadata["contrato_entrada"]][3] == "es_franquicia"
    assert resultado.rows == len(entrada)
    assert np.isfinite(pd.read_csv(salida)["prediccion"]).all()


def test_modelo_con_es_franquicia_exige_su_columna(version_franquicia, csv_prediccion, tmp_path):
    """El contrato viaja con la version: no depende de SIXTH_FEATURE."""
    with pytest.raises(predicting.data.MissingColumnsError, match="es_franquicia"):
        predicting.predict_file(version_franquicia, csv_prediccion, tmp_path / "salida.csv")


def test_modelo_del_paso_1_sin_kw_args_sigue_prediciendo(version_franquicia, csv_prediccion, tmp_path):
    """Los modelos del Paso 1 no guardaban su opcion: usan LEGACY_SIXTH_FEATURE."""
    modelo, metadata = versioning.load_version(version_franquicia)
    entrada = predicting.prepare_input(
        leer_entrada(csv_prediccion).rename(columns={"es_secuela": "es_franquicia"}),
        metadata["contrato_entrada"],
    )
    esperadas = modelo.predict(entrada)

    modelo.named_steps["ceros_a_nan"].kw_args = None
    ruta = tmp_path / "modelo_antiguo.joblib"
    joblib.dump(modelo, ruta)

    assert config.LEGACY_SIXTH_FEATURE == "es_franquicia"
    assert np.array_equal(joblib.load(ruta).predict(entrada), esperadas)


def test_versiones_del_repositorio_predicen_el_ejemplo(tmp_path):
    """Solo lectura: las salidas van a tmp_path y se comparan los hashes."""
    titulos = list(leer_entrada(EJEMPLO)["title"])
    predicciones = {}

    for version in ("v1", "v2"):
        carpeta = MODELOS_REPO / version
        hashes = sha256_de_carpeta(carpeta)
        salida = tmp_path / f"{version}.csv"

        resultado = predicting.predict_file(carpeta, EJEMPLO, salida)

        escrito = pd.read_csv(salida)
        _, metadata = versioning.load_version(carpeta)
        assert metadata["version"] == version
        assert metadata["sexta_predictora"] == "es_secuela"
        assert resultado.rows == len(titulos) == 12
        assert list(escrito["title"]) == titulos
        assert escrito["prediccion"].between(0, 10).all()
        assert sha256_de_carpeta(carpeta) == hashes
        predicciones[version] = escrito["prediccion"].to_numpy()

    assert not np.allclose(predicciones["v1"], predicciones["v2"])
