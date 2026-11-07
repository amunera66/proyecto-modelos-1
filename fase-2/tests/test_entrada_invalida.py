"""Entradas que deben rechazarse sin crear ni alterar la salida."""

import numpy as np
import pandas as pd
import pytest

from conftest import leer_entrada
from src import config, data, predicting, training


def _escribir(entrada, carpeta):
    ruta = carpeta / "entrada.csv"
    entrada.to_csv(ruta, index=False, encoding="utf-8")
    return ruta


def _assert_rechazada_por_consola(ejecutar, entrenado, entrada, salida, *mensajes):
    """Comprueba el codigo de salida, el mensaje y que no quede ningun archivo."""
    proceso = ejecutar(
        "predict.py",
        "--model", entrenado.dir_version,
        "--input", entrada,
        "--output", salida,
    )

    assert proceso.returncode != 0
    assert "Traceback" not in proceso.stderr
    for mensaje in mensajes:
        assert mensaje in proceso.stderr
    assert not salida.exists()
    assert list(salida.parent.glob(f".{salida.name}.*")) == []


@pytest.mark.parametrize("columna", config.FEATURE_NAMES)
def test_columna_ausente_lanza_la_excepcion_documentada(
    entrenado, csv_prediccion, tmp_path, columna
):
    entrada = _escribir(leer_entrada(csv_prediccion).drop(columns=columna), tmp_path)
    salida = tmp_path / "salida.csv"

    with pytest.raises(data.MissingColumnsError, match=columna) as error:
        predicting.predict_file(entrenado.dir_version, entrada, salida)

    assert error.value.missing == [columna]
    assert isinstance(error.value, data.DataError)
    assert not salida.exists()


def test_columna_ausente_en_el_pipeline_lanza_la_misma_excepcion(modelo_cargado, csv_prediccion):
    modelo, metadata = modelo_cargado
    entrada = predicting.prepare_input(
        leer_entrada(csv_prediccion), metadata["contrato_entrada"]
    )

    with pytest.raises(data.MissingColumnsError, match="runtime"):
        modelo.predict(entrada.drop(columns="runtime"))


def test_columna_ausente_por_consola(ejecutar, entrenado, csv_prediccion, tmp_path):
    entrada = _escribir(leer_entrada(csv_prediccion).drop(columns="runtime"), tmp_path)

    _assert_rechazada_por_consola(
        ejecutar, entrenado, entrada, tmp_path / "salida.csv", "runtime"
    )


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [("2", "solo acepta 0 o 1"), ("", "no admite nulos")],
    ids=["valor_2", "nulo"],
)
def test_es_secuela_invalida_en_predict_py(
    ejecutar_en_proceso, entrenado, csv_prediccion, tmp_path, valor, mensaje
):
    entrada = _escribir(leer_entrada(csv_prediccion).assign(es_secuela=valor), tmp_path)

    _assert_rechazada_por_consola(
        ejecutar_en_proceso, entrenado, entrada, tmp_path / "salida.csv", "es_secuela", mensaje
    )


@pytest.mark.parametrize("valor", ["2", "-1", "0.5", "si", "NA", "   "])
def test_es_secuela_invalida_lanza_error(entrenado, csv_prediccion, tmp_path, valor):
    """Una sola fila mala basta, y el mensaje dice cual es."""
    filas = leer_entrada(csv_prediccion)
    filas.loc[2, "es_secuela"] = valor
    salida = tmp_path / "salida.csv"

    with pytest.raises(predicting.PredictionError, match=r"es_secuela.*fila 3"):
        predicting.predict_file(entrenado.dir_version, _escribir(filas, tmp_path), salida)

    assert not salida.exists()


def test_budget_no_numerico_en_predict_py(ejecutar_en_proceso, entrenado, csv_prediccion, tmp_path):
    filas = leer_entrada(csv_prediccion)
    filas.loc[1, "budget"] = "mucho dinero"

    _assert_rechazada_por_consola(
        ejecutar_en_proceso,
        entrenado,
        _escribir(filas, tmp_path),
        tmp_path / "salida.csv",
        "budget",
        "mucho dinero",
    )


@pytest.mark.parametrize("columna", config.NUMERIC_FEATURES)
@pytest.mark.parametrize("valor", ["abc", "inf", "-inf", "1,5"])
def test_numerica_invalida_lanza_error(entrenado, csv_prediccion, tmp_path, columna, valor):
    filas = leer_entrada(csv_prediccion)
    filas.loc[0, columna] = valor

    with pytest.raises(predicting.PredictionError, match=f"{columna}.*no numericos"):
        predicting.predict_file(
            entrenado.dir_version, _escribir(filas, tmp_path), tmp_path / "salida.csv"
        )


def test_un_error_deja_intacta_una_salida_anterior(entrenado, csv_prediccion, tmp_path):
    salida = tmp_path / "salida.csv"
    salida.write_text("contenido anterior\n", encoding="utf-8")
    entrada = _escribir(leer_entrada(csv_prediccion).assign(es_secuela="2"), tmp_path)

    with pytest.raises(predicting.PredictionError):
        predicting.predict_file(entrenado.dir_version, entrada, salida)

    assert salida.read_text(encoding="utf-8") == "contenido anterior\n"


def test_entrada_sin_filas_lanza_error(entrenado, csv_prediccion, tmp_path):
    entrada = _escribir(leer_entrada(csv_prediccion).head(0), tmp_path)

    with pytest.raises(predicting.PredictionError, match="no tiene filas"):
        predicting.predict_file(entrenado.dir_version, entrada, tmp_path / "salida.csv")


def _con_coma_final(ruta, destino, solo_primera=False, encabezado=False):
    """Copia el CSV agregando una coma al final de las filas de datos."""
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cabeza, filas = lineas[0], lineas[1:]
    filas = [
        fila + "," if indice == 0 or not solo_primera else fila
        for indice, fila in enumerate(filas)
    ]
    texto = "\n".join([cabeza + ("," if encabezado else ""), *filas]) + "\n"
    destino.write_text(texto, encoding="utf-8")
    return destino


@pytest.mark.parametrize(
    "opciones",
    [{}, {"solo_primera": True}, {"encabezado": True}],
    ids=["todas_las_filas", "solo_la_primera_fila", "tambien_en_el_encabezado"],
)
def test_coma_final_no_desplaza_las_columnas(entrenado, csv_prediccion, tmp_path, opciones):
    entrada = _con_coma_final(csv_prediccion, tmp_path / "coma.csv", **opciones)
    salida = tmp_path / "salida.csv"

    predicting.predict_file(entrenado.dir_version, entrada, salida)

    escrito = leer_entrada(salida)
    assert escrito[["title", *config.FEATURE_NAMES]].equals(leer_entrada(csv_prediccion))
    assert np.allclose(escrito["prediccion"].astype(float), entrenado.predicciones_en_memoria)


def test_coma_final_en_predict_py_no_muestra_avisos(
    ejecutar_en_proceso, entrenado, csv_prediccion, tmp_path
):
    entrada = _con_coma_final(csv_prediccion, tmp_path / "coma.csv")
    salida = tmp_path / "salida.csv"

    proceso = ejecutar_en_proceso(
        "predict.py",
        "--model", entrenado.dir_version,
        "--input", entrada,
        "--output", salida,
    )

    assert proceso.returncode == 0, proceso.stderr
    assert proceso.stderr == ""
    assert len(leer_entrada(salida)) == len(leer_entrada(csv_prediccion))


@pytest.mark.parametrize(
    "contenido",
    [
        b"",
        b'title,budget\n"sin cerrar,1\n',
        "título,budget\nPelícula,1\n".encode("latin-1"),
        b"title,budget\nA,1\nB,2,3,4\n",
    ],
    ids=["vacio", "comilla_sin_cerrar", "no_es_utf8", "fila_posterior_con_campos_de_mas"],
)
def test_csv_ilegible_termina_con_mensaje_claro(
    ejecutar_en_proceso, entrenado, tmp_path, contenido
):
    entrada = tmp_path / "ilegible.csv"
    entrada.write_bytes(contenido)

    _assert_rechazada_por_consola(
        ejecutar_en_proceso, entrenado, entrada, tmp_path / "salida.csv", "No se pudo leer"
    )


def test_datos_de_mas_se_rechazan_en_vez_de_perderse(
    ejecutar_en_proceso, entrenado, csv_prediccion, tmp_path
):
    """Por ejemplo, un genero sin comillas con una coma adentro."""
    lineas = csv_prediccion.read_text(encoding="utf-8").splitlines()
    lineas[1] = lineas[1].replace("Action", "Action,Adventure")
    entrada = tmp_path / "datos_de_mas.csv"
    entrada.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    _assert_rechazada_por_consola(
        ejecutar_en_proceso,
        entrenado,
        entrada,
        tmp_path / "salida.csv",
        "mas campos que el encabezado",
        "linea 2",
    )


@pytest.fixture
def crudo_con_runtime_invalido(csv_crudo, tmp_path):
    """Devuelve una funcion que escribe el CSV crudo con un valor malo en runtime."""

    def _crear(valor, cantidad=1):
        crudo = pd.read_csv(csv_crudo, low_memory=False, dtype={"runtime": object})
        filas = crudo.index[crudo[config.TARGET].notna()][:cantidad]
        crudo.loc[filas, "runtime"] = valor
        ruta = tmp_path / "crudo_invalido.csv"
        crudo.to_csv(ruta, index=False)
        return ruta, [int(fila) + 1 for fila in filas]

    return _crear


def test_runtime_con_texto_lanza_data_error(crudo_con_runtime_invalido):
    ruta, filas = crudo_con_runtime_invalido("noventa")

    with pytest.raises(data.DataError, match="runtime") as error:
        data.clean_data(data.read_raw_csv(ruta))

    assert f"fila {filas[0]}: 'noventa'" in str(error.value)


def test_runtime_con_texto_no_entrena_ni_crea_la_version(crudo_con_runtime_invalido, tmp_path):
    ruta, _ = crudo_con_runtime_invalido("noventa")
    opciones = training.TrainingOptions(
        data_path=ruta, version="v-mala", output_dir=tmp_path / "modelos"
    )

    with pytest.raises(data.DataError, match="runtime"):
        training.train_model(opciones)

    assert not (tmp_path / "modelos").exists()


def test_runtime_infinito_tambien_se_rechaza(crudo_con_runtime_invalido):
    ruta, _ = crudo_con_runtime_invalido("inf")

    with pytest.raises(data.DataError, match="runtime"):
        data.clean_data(data.read_raw_csv(ruta))


def test_mensaje_de_runtime_limita_los_ejemplos(crudo_con_runtime_invalido):
    ruta, _ = crudo_con_runtime_invalido("x", cantidad=8)

    with pytest.raises(data.DataError, match="y 3 mas") as error:
        data.clean_data(data.read_raw_csv(ruta))

    assert str(error.value).count("fila ") == 5


def test_runtime_con_texto_en_train_py(crudo_con_runtime_invalido, ejecutar_en_proceso, tmp_path):
    ruta, _ = crudo_con_runtime_invalido("noventa")

    proceso = ejecutar_en_proceso(
        "train.py", "--data", ruta, "--version", "v-mala", "--output-dir", tmp_path / "modelos"
    )

    assert proceso.returncode != 0
    assert "runtime" in proceso.stderr and "noventa" in proceso.stderr
    assert "Traceback" not in proceso.stderr
    assert not (tmp_path / "modelos").exists()


def test_runtime_valido_sigue_igual_tras_la_validacion(csv_crudo):
    """Los nulos y los ceros se conservan: el 0 pasa a nulo mas adelante, no aqui."""
    crudo = data.read_raw_csv(csv_crudo)
    limpio = data.clean_data(crudo)

    esperado = crudo[crudo[config.TARGET].notna()].drop_duplicates(config.ID_COLUMN)["runtime"]
    assert limpio["runtime"].reset_index(drop=True).equals(esperado.reset_index(drop=True))
    assert limpio["runtime"].isna().any() and (limpio["runtime"] == 0).any()
