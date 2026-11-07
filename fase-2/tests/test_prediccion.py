"""Carga, prediccion, faltantes, columnas y categorias nuevas."""

import joblib
import numpy as np
import pandas as pd
import pytest

from conftest import leer_entrada, sha256_de_carpeta
from src import config, predicting


def _predecir(modelo_y_metadata, entrada: pd.DataFrame) -> np.ndarray:
    """Pasa una entrada de texto por la validacion del contrato y por el modelo."""
    modelo, metadata = modelo_y_metadata
    return predicting.predict_rows(
        modelo, predicting.prepare_input(entrada, metadata["contrato_entrada"])
    )


def _estado_aprendido(modelo) -> dict:
    """Reune lo que se aprendio en fit, en cada etapa del Pipeline."""
    pasos = modelo.named_steps["preprocesamiento"].named_transformers_
    regresor = modelo.named_steps["modelo"]
    return {
        "medianas": pasos["numericas"]["imputar"].statistics_,
        "medias": pasos["numericas"]["escalar"].mean_,
        "escalas": pasos["numericas"]["escalar"].scale_,
        "generos": pasos["genero"]["codificar"].categories_,
        "generos_raros": pasos["genero"]["codificar"].infrequent_categories_,
        "moda_idioma": pasos["idioma"]["imputar"].statistics_,
        "idiomas": pasos["idioma"]["codificar"].categories_,
        "idiomas_raros": pasos["idioma"]["codificar"].infrequent_categories_,
        "base": regresor._baseline_prediction,
        "arboles": [arbol.nodes for iteracion in regresor._predictors for arbol in iteracion],
    }


def test_modelo_responde_a_las_predictoras(modelo_cargado, csv_prediccion):
    """Control: con un modelo constante, varias pruebas pasarian sin probar nada."""
    entrada = leer_entrada(csv_prediccion)
    predicciones = _predecir(modelo_cargado, entrada)

    assert np.ptp(predicciones) > 1
    for columna, valor in (("budget", "1000000"), ("runtime", "60"), ("es_secuela", "1")):
        cambiada = entrada.assign(**{columna: valor})
        assert not np.allclose(_predecir(modelo_cargado, cambiada), predicciones)


def test_pipeline_recargado_predice_igual_que_en_memoria(entrenado, modelo_cargado, csv_prediccion):
    entrada = leer_entrada(csv_prediccion)

    recargadas = _predecir(modelo_cargado, entrada)

    assert recargadas.shape == (len(entrada),)
    assert np.allclose(recargadas, entrenado.predicciones_en_memoria)


def test_las_predicciones_siguen_el_orden_de_las_filas(entrenado, modelo_cargado, csv_prediccion):
    invertida = leer_entrada(csv_prediccion).iloc[::-1].reset_index(drop=True)

    predicciones = _predecir(modelo_cargado, invertida)

    assert np.allclose(predicciones, entrenado.predicciones_en_memoria[::-1])


def test_predict_por_consola_genera_el_csv(ejecutar, entrenado, csv_prediccion, tmp_path):
    salida = tmp_path / "subcarpeta" / "predicciones.csv"

    proceso = ejecutar(
        "predict.py",
        "--model", entrenado.dir_version,
        "--input", csv_prediccion,
        "--output", salida,
    )

    assert proceso.returncode == 0, proceso.stderr
    entrada = leer_entrada(csv_prediccion)
    resultado = pd.read_csv(salida)
    assert predicting.PREDICTION_COLUMN in resultado.columns
    assert len(resultado) == len(entrada)
    assert list(resultado["title"]) == list(entrada["title"])
    assert np.allclose(resultado["prediccion"], entrenado.predicciones_en_memoria)


def test_nulos_en_runtime_y_budget_se_predicen_sin_nan(modelo_cargado, csv_prediccion):
    entrada = leer_entrada(csv_prediccion).assign(budget="", runtime="")

    predicciones = _predecir(modelo_cargado, entrada)

    assert predicciones.shape == (len(entrada),)
    assert np.isfinite(predicciones).all()


@pytest.mark.parametrize("texto_nulo", predicting.NULL_TEXTS)
def test_todos_los_textos_nulos_equivalen_a_celda_vacia(modelo_cargado, csv_prediccion, texto_nulo):
    entrada = leer_entrada(csv_prediccion)

    con_texto = _predecir(modelo_cargado, entrada.assign(runtime=texto_nulo))

    assert np.array_equal(con_texto, _predecir(modelo_cargado, entrada.assign(runtime="")))


@pytest.mark.parametrize("columna", config.ZERO_AS_MISSING_COLUMNS)
def test_cero_predice_igual_que_nulo(modelo_cargado, csv_prediccion, columna):
    entrada = leer_entrada(csv_prediccion)

    con_cero = _predecir(modelo_cargado, entrada.assign(**{columna: "0"}))
    con_nulo = _predecir(modelo_cargado, entrada.assign(**{columna: ""}))

    assert np.array_equal(con_cero, con_nulo)


@pytest.mark.parametrize("columna", config.ZERO_AS_MISSING_COLUMNS)
def test_cero_predice_igual_que_nulo_directo_en_el_pipeline(modelo_cargado, csv_prediccion, columna):
    """Sin pasar por predicting: la conversion debe estar dentro del Pipeline."""
    modelo, metadata = modelo_cargado
    entrada = predicting.prepare_input(
        leer_entrada(csv_prediccion), metadata["contrato_entrada"]
    )

    con_cero = modelo.predict(entrada.assign(**{columna: 0}))
    con_nulo = modelo.predict(entrada.assign(**{columna: np.nan}))

    assert np.array_equal(con_cero, con_nulo)


def test_la_salida_conserva_el_cero_escrito(entrenado, csv_prediccion, tmp_path):
    entrada = tmp_path / "con_cero.csv"
    leer_entrada(csv_prediccion).assign(budget="0").to_csv(entrada, index=False)
    salida = tmp_path / "salida.csv"

    predicting.predict_file(entrenado.dir_version, entrada, salida)

    assert (leer_entrada(salida)["budget"] == "0").all()


def test_columnas_en_otro_orden_dan_lo_mismo(entrenado, modelo_cargado, csv_prediccion):
    entrada = leer_entrada(csv_prediccion)
    invertidas = entrada[list(reversed(entrada.columns))]
    assert list(invertidas.columns) != list(entrada.columns)

    predicciones = _predecir(modelo_cargado, invertidas)

    assert np.array_equal(predicciones, entrenado.predicciones_en_memoria)


def test_columnas_en_otro_orden_directo_en_el_pipeline(modelo_cargado, csv_prediccion):
    """prepare_input ya ordena: aqui se prueba la etapa inicial del Pipeline."""
    modelo, metadata = modelo_cargado
    entrada = predicting.prepare_input(
        leer_entrada(csv_prediccion), metadata["contrato_entrada"]
    )
    columnas = list(entrada.columns)
    columnas[0], columnas[1] = columnas[1], columnas[0]  # intercambia budget y runtime

    assert np.array_equal(modelo.predict(entrada[columnas]), modelo.predict(entrada))


@pytest.mark.parametrize(
    ("columna", "categoria"),
    [("genero_principal", "Genero inventado"), ("original_language", "xx")],
)
def test_categoria_no_vista_no_rompe_la_prediccion(modelo_cargado, csv_prediccion, columna, categoria):
    entrada = leer_entrada(csv_prediccion).assign(**{columna: categoria})

    predicciones = _predecir(modelo_cargado, entrada)

    assert predicciones.shape == (len(entrada),)
    assert np.isfinite(predicciones).all()


def test_idioma_no_visto_predice_como_uno_poco_frecuente(modelo_cargado, csv_prediccion):
    modelo, _ = modelo_cargado
    codificador = modelo.named_steps["preprocesamiento"].named_transformers_["idioma"]["codificar"]
    poco_frecuentes = codificador.infrequent_categories_[0]
    assert len(poco_frecuentes) > 0
    entrada = leer_entrada(csv_prediccion)

    no_visto = _predecir(modelo_cargado, entrada.assign(original_language="xx"))
    conocido = _predecir(modelo_cargado, entrada.assign(original_language=poco_frecuentes[0]))

    assert np.array_equal(no_visto, conocido)


def test_columnas_extra_se_ignoran_y_title_se_copia(entrenado, csv_prediccion, tmp_path):
    entrada = leer_entrada(csv_prediccion)
    con_extra = tmp_path / "con_extra.csv"
    entrada.assign(popularidad="texto cualquiera", vote_average="9.9").to_csv(
        con_extra, index=False, encoding="utf-8"
    )
    salida = tmp_path / "salida.csv"

    resultado = predicting.predict_file(entrenado.dir_version, con_extra, salida)

    escrito = leer_entrada(salida)
    assert resultado.ignored_columns == ("popularidad", "vote_average")
    assert list(escrito.columns) == ["title", *config.FEATURE_NAMES, "prediccion"]
    assert list(escrito["title"]) == list(entrada["title"])  # incluye tildes y comas
    assert np.allclose(escrito["prediccion"].astype(float), entrenado.predicciones_en_memoria)


def test_predecir_no_modifica_lo_aprendido(modelo_cargado, csv_prediccion):
    modelo, _ = modelo_cargado
    antes = joblib.hash(_estado_aprendido(modelo))
    entrada = leer_entrada(csv_prediccion).assign(
        budget="", runtime="0", original_language="xx", genero_principal="Otro"
    )

    _predecir(modelo_cargado, entrada)

    assert joblib.hash(_estado_aprendido(modelo)) == antes


def test_predecir_no_modifica_la_version_guardada(entrenado, csv_prediccion, tmp_path):
    antes = sha256_de_carpeta(entrenado.dir_version)

    predicting.predict_file(entrenado.dir_version, csv_prediccion, tmp_path / "salida.csv")

    assert sha256_de_carpeta(entrenado.dir_version) == antes
