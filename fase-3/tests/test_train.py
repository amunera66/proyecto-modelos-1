"""Pruebas de POST /train con un CSV sintetico pequeno en tmp_path.

Entrenan con fase-2/src/training.py de verdad, sobre 60 peliculas, en una copia
de v1 y v2: nunca escriben en fase-2/models.
"""

import inspect
import json
import threading

import numpy as np
import pandas as pd
import pytest
from conftest import ENTRADA_VALIDA, hashes_de_carpeta
from fastapi.testclient import TestClient

from api import training
from api.config import Settings
from api.main import create_app
from src import config as fase2_config
from src import versioning
from src.training import TrainingResult

ARCHIVOS_VERSION = {versioning.MODEL_FILE, versioning.METRICS_FILE, versioning.METADATA_FILE}
GENEROS = {"Drama": 0.5, "Comedy": -0.3, "Action": -0.5, "Horror": -1.0}


def csv_sintetico(filas: int = 60, semilla: int = 0) -> pd.DataFrame:
    """Peliculas con el esquema crudo de movies_metadata.csv. Una saga de 4 al inicio."""
    rng = np.random.default_rng(semilla)
    peliculas = []
    for indice in range(filas):
        genero = str(rng.choice(list(GENEROS)))
        runtime = float(rng.integers(70, 180))
        en_saga = indice < 4
        peliculas.append({
            "id": 100 + indice,
            "budget": float(rng.integers(0, 200)) * 1_000_000,
            "runtime": runtime,
            "release_date": f"{2000 + indice % 4 if en_saga else rng.integers(1970, 2017)}-06-01",
            "belongs_to_collection": str({"id": 9, "name": "Saga"}) if en_saga else None,
            "genres": str([{"id": 1, "name": genero}]),
            "original_language": str(rng.choice(["en", "fr", "es"])),
            "status": "Released",
            "vote_count": int(rng.integers(11, 500)),
            "vote_average": round(float(np.clip(
                6 + GENEROS[genero] + (runtime - 120) * 0.02 + rng.normal(0, 0.1), 0, 10
            )), 1),
        })
    return pd.DataFrame(peliculas, columns=list(fase2_config.RAW_COLUMNS))


@pytest.fixture
def datos(tmp_path):
    ruta = tmp_path / "movies_sintetico.csv"
    csv_sintetico().to_csv(ruta, index=False)
    return ruta


def settings_temporales(models_dir, data_path, version="v1") -> Settings:
    return Settings(model_version=version, models_dir=models_dir, data_path=data_path)


def test_train_es_sincrono():
    """Decision del equipo: def, no async def, para no bloquear /health."""
    app = create_app(Settings(model_version="v9"))
    ruta = next(ruta for ruta in app.routes if getattr(ruta, "path", None) == "/train")

    assert not inspect.iscoroutinefunction(ruta.endpoint)


def test_train_crea_version_nueva_y_no_cambia_la_activa(copia_de_versiones, datos):
    antes = {v: hashes_de_carpeta(copia_de_versiones / v) for v in ("v1", "v2")}
    cliente = TestClient(create_app(settings_temporales(copia_de_versiones, datos)))

    respuesta = cliente.post("/train")  # sin cuerpo

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["version"] == "v3"
    assert cuerpo["ruta"] == "MODELS_DIR/v3"  # fuera del repo no se expone la ruta local
    assert cuerpo["version_activa"] == "v1"
    assert cuerpo["metrica_principal"] == "RMSE"
    assert set(cuerpo["metricas"]["modelo"]["prueba"]) == {"MAE", "RMSE", "R2"}
    assert set(cuerpo["metricas"]["modelo"]["cv_media"]) == {"MAE", "RMSE", "R2"}

    nueva = copia_de_versiones / "v3"
    assert {archivo.name for archivo in nueva.iterdir()} == ARCHIVOS_VERSION
    metadata = json.loads((nueva / versioning.METADATA_FILE).read_text(encoding="utf-8"))
    assert metadata["version"] == "v3"
    assert metadata["objetivo"] == "vote_average"
    assert metadata["semilla"] == 42
    assert metadata["datos"]["archivo"] == "movies_sintetico.csv"
    assert metadata["git_commit"]

    # Las versiones anteriores siguen igual y la API sigue sirviendo v1
    assert {v: hashes_de_carpeta(copia_de_versiones / v) for v in ("v1", "v2")} == antes
    assert sorted(p.name for p in copia_de_versiones.iterdir()) == ["v1", "v2", "v3"]
    assert cliente.get("/health").json()["version"] == "v1"
    assert cliente.post("/predict", json=ENTRADA_VALIDA).json()["version"] == "v1"

    # Un segundo /train usa el siguiente identificador y conserva v3
    segunda = cliente.post("/train", json={})
    assert segunda.status_code == 201
    assert segunda.json()["version"] == "v4"
    assert {archivo.name for archivo in nueva.iterdir()} == ARCHIVOS_VERSION

    # Con MODEL_VERSION=v3 y una app nueva (equivale a reiniciar), /predict la usa
    reiniciada = TestClient(create_app(settings_temporales(copia_de_versiones, datos, "v3")))
    prediccion = reiniciada.post("/predict", json=ENTRADA_VALIDA)
    assert prediccion.status_code == 200
    assert prediccion.json()["version"] == "v3"


def test_train_sin_archivo_de_datos_da_503(copia_de_versiones, tmp_path):
    cliente = TestClient(
        create_app(settings_temporales(copia_de_versiones, tmp_path / "no_existe.csv"))
    )

    respuesta = cliente.post("/train")

    assert respuesta.status_code == 503
    assert respuesta.json()["error"] == "Datos de entrenamiento no disponibles"
    assert "DATA_PATH" in respuesta.json()["detalle"]
    assert sorted(p.name for p in copia_de_versiones.iterdir()) == ["v1", "v2"]


def test_train_con_datos_invalidos_da_500_sin_traceback(copia_de_versiones, tmp_path):
    datos = tmp_path / "sin_objetivo.csv"
    csv_sintetico().drop(columns=["vote_average"]).to_csv(datos, index=False)
    cliente = TestClient(create_app(settings_temporales(copia_de_versiones, datos)))

    respuesta = cliente.post("/train")

    assert respuesta.status_code == 500
    assert respuesta.json()["error"] == "Datos de entrenamiento invalidos"
    assert "Faltan columnas requeridas: vote_average" in respuesta.json()["detalle"]
    assert "Traceback" not in respuesta.text
    # Ni la version ni temporales a medias
    assert sorted(p.name for p in copia_de_versiones.iterdir()) == ["v1", "v2"]


def test_siguiente_identificador(tmp_path):
    assert training.next_version(tmp_path / "no_existe") == "v1"
    for nombre in ("v1", "v2", "v-test", "v10-copia", "V20"):
        (tmp_path / nombre).mkdir()
    (tmp_path / "v7").write_text("archivo, no carpeta")

    assert training.next_version(tmp_path) == "v8"
    assert training.next_version(tmp_path, {"v9"}) == "v10"


def test_train_simultaneos_no_repiten_identificador(copia_de_versiones, datos):
    """Los dos hilos reservan su identificador antes de que alguno guarde."""
    barrera = threading.Barrier(2, timeout=10)

    def entrenamiento_falso(opciones):
        barrera.wait()  # ambos estan "entrenando" a la vez
        carpeta = opciones.output_dir / opciones.version
        carpeta.mkdir()  # falla si el identificador se repitiera
        metrica = {"MAE": 0.0, "RMSE": 0.0, "R2": 0.0}
        cv = {nombre: {"media": 0.0, "desviacion": 0.0} for nombre in metrica}
        metricas = {"modelo": {"prueba": metrica, "cv": cv}, "baseline": {"prueba": metrica}}
        return TrainingResult(carpeta, metricas, {})

    settings = settings_temporales(copia_de_versiones, datos)
    versiones, errores = [], []

    def llamar():
        try:
            versiones.append(training.train_new_version(settings, "v1", entrenamiento_falso).version)
        except Exception as error:  # se revisa abajo
            errores.append(error)

    hilos = [threading.Thread(target=llamar) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=20)

    assert errores == []
    assert sorted(versiones) == ["v3", "v4"]
