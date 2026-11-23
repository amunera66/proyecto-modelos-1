"""Pruebas de GET /health y POST /predict con TestClient y fase-2/models/v1."""

import math
import shutil

import pytest
from conftest import ENTRADA_VALIDA, MODELOS_REPO, PREDICCION_V1, settings_repo
from fastapi.testclient import TestClient

from api.main import create_app

MENSAJE_AUSENTE = "Campo obligatorio ausente; si el dato falta, envia null"


def sin(campo: str) -> dict:
    return {clave: valor for clave, valor in ENTRADA_VALIDA.items() if clave != campo}


# --- Las tres pruebas obligatorias ---


def test_health_responde_200(cliente):
    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "estado": "en_ejecucion",
        "version": "v1",
        "modelo_disponible": True,
        "detalle": None,
    }


def test_entrada_valida_devuelve_prediccion_y_version(cliente):
    respuesta = cliente.post("/predict", json=ENTRADA_VALIDA)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"prediccion", "version"}
    assert cuerpo["version"] == "v1"
    assert isinstance(cuerpo["prediccion"], float)
    assert cuerpo["prediccion"] == pytest.approx(PREDICCION_V1, abs=1e-9)


def test_entrada_sin_variable_obligatoria_se_rechaza(cliente):
    respuesta = cliente.post("/predict", json=sin("runtime"))

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "error": "Entrada invalida",
        "detalle": [{"campo": "runtime", "mensaje": MENSAJE_AUSENTE}],
    }


# --- Validacion de la entrada ---


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("es_secuela", 2, "Solo acepta los enteros 0 o 1"),
        ("budget", "mucho", "Debe ser un numero (entero o decimal) o null"),
        ("runtime", True, "Debe ser un numero (entero o decimal) o null"),
    ],
    ids=["es_secuela_2", "budget_texto", "runtime_true"],
)
def test_tipo_o_valor_invalido_da_422(cliente, campo, valor, mensaje):
    respuesta = cliente.post("/predict", json={**ENTRADA_VALIDA, campo: valor})

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "error": "Entrada invalida",
        "detalle": [{"campo": campo, "mensaje": mensaje, "valor_recibido": valor}],
    }


def test_json_mal_formado_da_400(cliente):
    respuesta = cliente.post(
        "/predict",
        content='{"budget": 165000000, "runtime": ',
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == "JSON mal formado"


def test_campo_extra_se_ignora(cliente):
    respuesta = cliente.post("/predict", json={**ENTRADA_VALIDA, "titulo": "Dune"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"prediccion": PREDICCION_V1, "version": "v1"}


def test_runtime_null_predice(cliente):
    respuesta = cliente.post("/predict", json={**ENTRADA_VALIDA, "runtime": None})

    assert respuesta.status_code == 200
    prediccion = respuesta.json()["prediccion"]
    assert math.isfinite(prediccion)
    assert prediccion != pytest.approx(PREDICCION_V1)


# --- Version y errores del servidor ---


def test_version_inexistente_da_503():
    cliente = TestClient(create_app(settings_repo("v9")))

    salud = cliente.get("/health").json()
    respuesta = cliente.post("/predict", json=ENTRADA_VALIDA)

    assert salud["modelo_disponible"] is False
    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["error"] == "Modelo no disponible"
    assert cuerpo["version"] == "v9"
    assert "Versiones disponibles: v1, v2" in cuerpo["detalle"]


class ModeloQueFalla:
    def predict(self, X):
        raise RuntimeError("fallo interno simulado")


def test_error_del_modelo_da_500_sin_traceback():
    app = create_app(settings_repo())
    app.state.model_state.model = ModeloQueFalla()

    respuesta = TestClient(app).post("/predict", json=ENTRADA_VALIDA)

    assert respuesta.status_code == 500
    assert respuesta.json()["error"] == "Error interno al predecir"
    assert respuesta.json()["version"] == "v1"
    assert "Traceback" not in respuesta.text
    assert "fallo interno simulado" not in respuesta.text


def test_version_informada_es_la_configurada_por_variable(monkeypatch):
    for variable in ("MODELS_DIR", "DATA_PATH"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("MODEL_VERSION", "v2")
    cliente = TestClient(create_app())

    respuesta = cliente.post("/predict", json=ENTRADA_VALIDA)

    assert cliente.get("/health").json()["version"] == "v2"
    assert respuesta.status_code == 200
    assert respuesta.json()["version"] == "v2"
    assert respuesta.json()["prediccion"] != pytest.approx(PREDICCION_V1)


def test_version_informada_es_el_nombre_de_la_carpeta(tmp_path):
    # La copia conserva metadata["version"] == "v1"; se informa la configurada
    shutil.copytree(MODELOS_REPO / "v1", tmp_path / "mi-version")
    cliente = TestClient(create_app(settings_repo("mi-version", models_dir=tmp_path)))

    respuesta = cliente.post("/predict", json=ENTRADA_VALIDA)

    assert cliente.get("/health").json()["version"] == "mi-version"
    assert respuesta.json() == {"prediccion": PREDICCION_V1, "version": "mi-version"}


# --- Observador para la Fase 4 ---


def test_observador_se_llama_una_vez_por_intento():
    eventos = []
    cliente = TestClient(create_app(settings_repo(), observer=eventos.append))

    cliente.post("/predict", json=ENTRADA_VALIDA)
    cliente.post("/predict", json=sin("runtime"))
    cliente.post("/predict", content="{", headers={"Content-Type": "application/json"})
    cliente.get("/health")  # no es un intento de prediccion

    assert [evento.codigo_http for evento in eventos] == [200, 422, 400]
    assert eventos[0].prediccion == pytest.approx(PREDICCION_V1)
    assert eventos[0].detalle is None
    assert [evento.prediccion for evento in eventos[1:]] == [None, None]
    assert all(evento.version == "v1" for evento in eventos)


def test_observador_tambien_recibe_503():
    eventos = []
    cliente = TestClient(create_app(settings_repo("v9"), observer=eventos.append))

    cliente.post("/predict", json=ENTRADA_VALIDA)

    assert [(evento.codigo_http, evento.version) for evento in eventos] == [(503, "v9")]
