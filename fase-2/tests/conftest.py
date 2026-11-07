"""Fixtures compartidas. Todo se genera en carpetas temporales, sin red ni datos reales."""

import hashlib
import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src import config, predicting, training, versioning

FASE2_DIR = Path(__file__).resolve().parents[1]
SEMILLA_DATOS = 2024
VERSION_ENTRENADA = "v-prueba"

# Filas con un papel concreto en las pruebas de limpieza y filtros
ID_NO_NUMERICO = "1997-08-20"
ID_DUPLICADO = 7001
ID_VOTOS_EN_EL_LIMITE = 7002  # vote_count == 10: el filtro la quita
ID_VOTOS_SOBRE_EL_LIMITE = 7003  # vote_count == 11: el filtro la conserva
ID_RUMORED = 7004
ID_STATUS_NULO = 7005
# Coleccion cuya primera pelicula no pasa los filtros, pero la segunda si
ID_PRECUELA_FILTRADA = 7101
ID_SECUELA_DE_FILTRADA = 7102
# Coleccion con dos peliculas empatadas en la primera fecha y una posterior
IDS_EMPATE_PRIMERA_FECHA = (7201, 7202)
ID_POSTERIOR_AL_EMPATE = 7203
ID_SECUELA_FECHA_NULA = 7301  # tiene coleccion, pero su fecha es nula
ID_UNICA_DE_COLECCION = 7401

GENEROS = {
    "Drama": 0.0,
    "Comedy": -0.3,
    "Action": -0.5,
    "Horror": -1.0,
    "Documentary": 1.0,
}
IDIOMAS_FRECUENTES = {"en": 0.0, "fr": 0.5, "es": 0.4}
# Aparecen una sola vez: quedan como categorias poco frecuentes si caen en train
IDIOMAS_RAROS = ("nb", "te", "ko", "ja", "pt", "de", "it", "ru", "sv", "da")


def _generos_texto(nombre: str | None) -> str:
    """Escribe la columna genres como el CSV real: una lista de dicts en texto."""
    if nombre is None:
        return "[]"
    return str([{"id": 1, "name": nombre}, {"id": 2, "name": "Thriller"}])


def _coleccion_texto(id_coleccion: int) -> str:
    """Escribe belongs_to_collection como el CSV real: un dict en texto."""
    return str(
        {
            "id": id_coleccion,
            "name": f"Coleccion {id_coleccion}",
            "poster_path": None,
            "backdrop_path": None,
        }
    )


def _pelicula(rng: np.random.Generator, id_pelicula: int, **cambios) -> dict:
    """Crea una pelicula valida. vote_average depende de las predictoras."""
    genero = str(rng.choice(list(GENEROS)))
    idioma = str(rng.choice(list(IDIOMAS_FRECUENTES), p=[0.7, 0.15, 0.15]))
    fila = {
        "id": id_pelicula,
        "budget": float(rng.integers(1, 200)) * 1_000_000,
        "runtime": float(rng.integers(70, 180)),
        "release_date": f"{rng.integers(1960, 2017)}-{rng.integers(1, 13):02d}-15",
        "belongs_to_collection": None,
        "genres": _generos_texto(genero),
        "original_language": idioma,
        "status": "Released",
        "vote_count": int(rng.integers(11, 3000)),
        "vote_average": 0.0,
    }
    fila.update(cambios)

    # La senal es fuerte para que el modelo responda a cada predictora, y los
    # faltantes tienen efecto propio para distinguir un 0 de un valor real.
    runtime = fila["runtime"]
    budget = fila["budget"]
    efecto_runtime = 1.0 if pd.isna(runtime) or runtime == 0 else (runtime - 120) * 0.03
    efecto_budget = -0.8 if pd.isna(budget) or budget == 0 else budget / 1e8
    promedio = (
        6.0
        + efecto_runtime
        + efecto_budget
        + GENEROS.get(genero, 0.0)
        + IDIOMAS_FRECUENTES.get(idioma, 0.0)
        + rng.normal(0, 0.05)
    )
    fila["vote_average"] = round(float(np.clip(promedio, 0, 10)), 1)
    return fila


def _con_efecto_secuela(fila: dict) -> dict:
    fila["vote_average"] = round(max(fila["vote_average"] - 1.2, 0.0), 1)
    return fila


def _colecciones(rng: np.random.Generator) -> list[dict]:
    """Sagas de 3 a 6 peliculas con fechas distintas: la primera vale 0, las demas 1."""
    filas = []
    for numero in range(14):
        anio = int(rng.integers(1970, 2005))
        for posicion in range(int(rng.integers(3, 7))):
            fila = _pelicula(
                rng,
                1000 + numero * 10 + posicion,
                release_date=f"{anio + 2 * posicion}-06-01",
                belongs_to_collection=_coleccion_texto(100 + numero),
            )
            filas.append(_con_efecto_secuela(fila) if posicion else fila)
    return filas


def _casos_de_secuela(rng: np.random.Generator) -> list[dict]:
    """Casos borde de la definicion de es_secuela (ver decisiones.md, C3)."""
    return [
        _pelicula(
            rng,
            ID_PRECUELA_FILTRADA,
            release_date="1990-01-01",
            belongs_to_collection=_coleccion_texto(900),
            vote_count=5,
        ),
        _pelicula(
            rng,
            ID_SECUELA_DE_FILTRADA,
            release_date="1995-01-01",
            belongs_to_collection=_coleccion_texto(900),
            vote_count=500,
        ),
        _pelicula(
            rng,
            IDS_EMPATE_PRIMERA_FECHA[0],
            release_date="2000-05-05",
            belongs_to_collection=_coleccion_texto(901),
        ),
        _pelicula(
            rng,
            IDS_EMPATE_PRIMERA_FECHA[1],
            release_date="2000-05-05",
            belongs_to_collection=_coleccion_texto(901),
        ),
        _pelicula(
            rng,
            ID_POSTERIOR_AL_EMPATE,
            release_date="2003-05-05",
            belongs_to_collection=_coleccion_texto(901),
        ),
        _pelicula(
            rng,
            ID_SECUELA_FECHA_NULA,
            release_date=None,
            belongs_to_collection=_coleccion_texto(901),
        ),
        _pelicula(
            rng,
            ID_UNICA_DE_COLECCION,
            release_date="2010-01-01",
            belongs_to_collection=_coleccion_texto(902),
        ),
    ]


def _sin_coleccion(rng: np.random.Generator, cantidad: int) -> list[dict]:
    filas = []
    for indice in range(cantidad):
        cambios = {}
        # Ceros y nulos en budget y runtime, repartidos a lo largo de las filas
        if indice % 4 == 0:
            cambios["budget"] = 0.0
        elif indice % 9 == 1:
            cambios["budget"] = None
        if indice % 7 == 0:
            cambios["runtime"] = 0.0
        elif indice % 11 == 1:
            cambios["runtime"] = None
        if indice % 13 == 0:
            cambios["genres"] = _generos_texto(None)
        if indice < len(IDIOMAS_RAROS):
            cambios["original_language"] = IDIOMAS_RAROS[indice]
        filas.append(_pelicula(rng, 2000 + indice, **cambios))
    return filas


def _filtradas_y_corruptas(rng: np.random.Generator) -> list[dict]:
    """Filas que la limpieza o los filtros deben quitar, y las del limite exacto."""
    filas = [_pelicula(rng, 3000 + indice, vote_count=int(rng.integers(0, 10))) for indice in range(8)]
    filas += [
        _pelicula(rng, 3100 + indice, status="Post Production") for indice in range(3)
    ]
    filas += [
        _pelicula(rng, ID_VOTOS_EN_EL_LIMITE, vote_count=10),
        _pelicula(rng, ID_VOTOS_SOBRE_EL_LIMITE, vote_count=11),
        _pelicula(rng, ID_RUMORED, status="Rumored"),
        _pelicula(rng, ID_STATUS_NULO, status=None),
        _pelicula(rng, ID_DUPLICADO),
        _pelicula(rng, ID_DUPLICADO),
    ]
    # Linea corrupta como las del CSV real: fecha en id y ruta en budget
    filas.append(
        {
            "id": ID_NO_NUMERICO,
            "budget": "/ruta_de_un_poster.jpg",
            "runtime": None,
            "release_date": None,
            "belongs_to_collection": None,
            "genres": "[]",
            "original_language": None,
            "status": None,
            "vote_count": None,
            "vote_average": None,
        }
    )
    return filas


def generar_csv_crudo() -> pd.DataFrame:
    """Devuelve unas 200 filas con el esquema de movies_metadata.csv."""
    rng = np.random.default_rng(SEMILLA_DATOS)
    filas = _colecciones(rng) + _casos_de_secuela(rng)
    filas += _filtradas_y_corruptas(rng)
    filas += _sin_coleccion(rng, 200 - len(filas))
    columnas = list(config.RAW_COLUMNS)
    return pd.DataFrame(filas, columns=columnas).sample(frac=1, random_state=SEMILLA_DATOS)


def sha256_de_carpeta(carpeta: Path) -> dict[str, str]:
    """Devuelve el hash de cada archivo de una carpeta."""
    return {
        archivo.name: hashlib.sha256(archivo.read_bytes()).hexdigest()
        for archivo in sorted(carpeta.iterdir())
    }


def leer_entrada(ruta: Path) -> pd.DataFrame:
    """Lee un CSV de prediccion como texto, para cambiar celdas sin alterar el resto."""
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


@pytest.fixture(scope="session")
def csv_crudo(tmp_path_factory) -> Path:
    """CSV sintetico con el esquema crudo."""
    ruta = tmp_path_factory.mktemp("datos") / "movies_sintetico.csv"
    generar_csv_crudo().to_csv(ruta, index=False)
    return ruta


@pytest.fixture(scope="session")
def csv_prediccion(tmp_path_factory) -> Path:
    """CSV de prediccion pequeno y valido, con las 6 predictoras y title."""
    filas = [
        ("Película uno", "150000000", "150", "2010", "0", "Action", "en"),
        ("Película dos", "2000000", "80", "1985", "1", "Horror", "en"),
        ("Película, tres", "90000000", "120", "1999", "1", "Comedy", "fr"),
        ("Cuatro", "1000000", "170", "2015", "0", "Documentary", "es"),
        ("Cinco", "40000000", "95", "1975", "0", "Drama", "en"),
        ("Seis", "120000000", "75", "2005", "1", "Action", "fr"),
    ]
    columnas = ["title", *config.FEATURE_NAMES]
    ruta = tmp_path_factory.mktemp("entrada") / "prediccion.csv"
    pd.DataFrame(filas, columns=columnas).to_csv(ruta, index=False, encoding="utf-8")
    return ruta


@pytest.fixture(scope="session")
def entrenado(tmp_path_factory, csv_crudo, csv_prediccion) -> SimpleNamespace:
    """Entrena una version una sola vez con src/training.py, sin subprocess.

    train_model no devuelve el Pipeline, asi que se envuelve save_version para
    predecir con el objeto en memoria justo antes de que se guarde.
    """
    dir_modelos = tmp_path_factory.mktemp("modelos")
    guardar = versioning.save_version
    capturado = {}

    def guardar_y_capturar(pipeline, metrics, metadata, output_dir, version):
        entrada = predicting.prepare_input(
            predicting.read_input(csv_prediccion), metadata["contrato_entrada"]
        )
        capturado["pipeline"] = pipeline
        capturado["predicciones"] = pipeline.predict(entrada)
        return guardar(pipeline, metrics, metadata, output_dir, version)

    opciones = training.TrainingOptions(
        data_path=csv_crudo, version=VERSION_ENTRENADA, output_dir=dir_modelos
    )
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(versioning, "save_version", guardar_y_capturar)
        resultado = training.train_model(opciones)

    return SimpleNamespace(
        dir_modelos=dir_modelos,
        dir_version=resultado.version_dir,
        opciones=opciones,
        resultado=resultado,
        pipeline_en_memoria=capturado["pipeline"],
        predicciones_en_memoria=capturado["predicciones"],
    )


@pytest.fixture
def modelo_cargado(entrenado):
    """Devuelve (pipeline, metadata) recargados desde el disco."""
    return versioning.load_version(entrenado.dir_version)


@pytest.fixture(scope="session")
def ejecutar():
    """Ejecuta train.py o predict.py como proceso aparte, desde fase-2/."""

    def _ejecutar(script: str, *argumentos) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, script, *map(str, argumentos)],
            cwd=FASE2_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            timeout=60,
            check=False,
        )

    return _ejecutar


@pytest.fixture
def ejecutar_en_proceso(monkeypatch, capsys):
    """Llama al main() de un script: mismo manejo de errores, sin importar sklearn de nuevo.

    Tiene la misma forma de uso que ejecutar. Cada proceso aparte tarda mas de un
    segundo en este equipo, asi que ejecutar se reserva para los casos que lo piden.
    """

    def _ejecutar(script: str, *argumentos) -> SimpleNamespace:
        monkeypatch.setattr(sys, "argv", [script, *map(str, argumentos)])
        capsys.readouterr()
        codigo = importlib.import_module(Path(script).stem).main()
        salida = capsys.readouterr()
        return SimpleNamespace(returncode=codigo, stdout=salida.out, stderr=salida.err)

    return _ejecutar
