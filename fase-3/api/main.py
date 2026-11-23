"""API REST de la Fase 3: GET /health, POST /predict y POST /train.

Este modulo solo define create_app: importarlo no crea la app ni carga el
modelo. El objeto app para uvicorn esta en api/app.py.
Ejecutar desde fase-3/:  uvicorn api.app:app
La logica de prediccion es la de fase-2/src (versioning y predicting): aqui solo
se valida el JSON, se arma la respuesta y se avisa al observador. La de /train
esta en api/training.py y usa fase-2/src/training.py.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from api import _fase2  # noqa: F401  debe ir antes de importar src
from api import schema, training
from api.config import Settings
from api.config import display_path as _display
from api.config import hide_root as _hide_root
from src import config as fase2_config
from src import predicting, versioning
from src.data import DataError

logger = logging.getLogger("api")


@dataclass(frozen=True)
class EventoPrediccion:
    """Lo que recibe el observador por cada intento a /predict.

    fecha: momento en que llego la solicitud, en UTC e ISO 8601
    (por ejemplo 2026-11-22T15:04:05.123456+00:00).
    prediccion es None cuando la respuesta no fue 200.
    """

    fecha: str
    codigo_http: int
    version: str
    prediccion: float | None
    detalle: Any = None


Observer = Callable[[EventoPrediccion], None]


@dataclass
class ModelState:
    """Version cargada al crear la app. No se recarga en caliente."""

    version: str
    available: bool = False
    model: Any = None
    contract: list[dict] = field(default_factory=list)
    input_model: type[BaseModel] | None = None
    error: str | None = None


def _available_versions(settings: Settings) -> list[str]:
    if not settings.models_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in settings.models_dir.iterdir()
        if path.is_dir() and (path / versioning.MODEL_FILE).is_file()
    )


def load_model_state(settings: Settings) -> ModelState:
    """Carga la version configurada. Si falla, la API arranca igual sin modelo."""
    state = ModelState(version=settings.model_version)
    if not versioning.VERSION_PATTERN.fullmatch(settings.model_version):
        state.error = (
            f"MODEL_VERSION invalida: {settings.model_version!r}. "
            "Usa letras, numeros, punto, guion o guion bajo."
        )
        return state
    try:
        model, metadata = versioning.load_version(settings.model_path)
        contract = metadata.get("contrato_entrada")
        if not contract:
            raise ValueError("El metadata.json del modelo no trae el contrato de entrada.")
        input_model = schema.build_input_model(contract)
    except versioning.VersionNotFoundError as error:
        state.error = (
            f"No existe la version {settings.model_version} en {_display(settings.models_dir)} "
            f"({_hide_root(str(error))}). Versiones disponibles: "
            f"{', '.join(_available_versions(settings)) or 'ninguna'}. "
            "Cambia MODEL_VERSION y reinicia el servidor."
        )
    except (versioning.VersionError, ValueError, KeyError) as error:
        state.error = (
            f"No se pudo cargar la version {settings.model_version}: {_hide_root(str(error))}"
        )
    else:
        state.available = True
        state.model = model
        state.contract = contract
        state.input_model = input_model
        # La version informada es siempre la configurada (el nombre de la carpeta)
        if metadata.get("version") != settings.model_version:
            logger.warning(
                "metadata.json de %s dice version %r; se informa la configurada, %r",
                _display(settings.model_path),
                metadata.get("version"),
                settings.model_version,
            )
    if state.error:
        logger.error(state.error)
    return state


def _openapi_body(contract: list[dict]) -> dict:
    """Esquema del cuerpo para /docs. Sin modelo, usa el contrato por defecto de fase-2."""
    input_model = schema.build_input_model(contract or fase2_config.input_contract())
    return {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": input_model.model_json_schema()}},
        }
    }


def create_app(settings: Settings | None = None, observer: Observer | None = None) -> FastAPI:
    """Crea la API y carga la version configurada.

    observer, si se pasa, se llama exactamente una vez por cada solicitud a
    /predict, sea cual sea el codigo HTTP. Si falla, se registra en el log y la
    respuesta no cambia.
    """
    settings = settings or Settings.from_env()
    state = load_model_state(settings)

    app = FastAPI(
        title="API de prediccion de vote_average",
        description="Fase 3. Predice la calificacion de TMDB con una version guardada de la Fase 2.",
        version="1.0",
    )
    app.state.settings = settings
    app.state.model_state = state

    def notify(event: EventoPrediccion) -> None:
        if observer is None:
            return
        try:
            observer(event)
        except Exception:  # el registro nunca debe tumbar la respuesta
            logger.exception("El observador de /predict fallo")

    @app.get("/health")
    def health() -> dict:
        return {
            "estado": "en_ejecucion",
            "version": state.version,
            "modelo_disponible": state.available,
            "detalle": state.error,
        }

    def _predict_sync(features) -> float:
        return float(predicting.predict_rows(state.model, features)[0])

    async def _handle(request: Request) -> tuple[int, dict, float | None]:
        if not state.available:
            return 503, {
                "error": "Modelo no disponible",
                "version": state.version,
                "detalle": state.error,
            }, None

        body = await request.body()
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError) as error:
            return 400, {"error": "JSON mal formado", "detalle": str(error)}, None
        if not isinstance(payload, dict):
            return 400, {
                "error": "El cuerpo debe ser un objeto JSON con las predictoras",
                "detalle": f"Se recibio {type(payload).__name__}",
            }, None

        try:
            record = state.input_model.model_validate(payload)
        except ValidationError as error:
            return 422, {
                "error": "Entrada invalida",
                "detalle": schema.describe_errors(error, state.contract),
            }, None

        extra = sorted(set(payload) - {feature["nombre"] for feature in state.contract})
        if extra:
            logger.warning("Se ignoran campos que no usa el modelo: %s", ", ".join(extra))

        try:
            # Segunda capa: las reglas de fase-2 para la misma entrada
            raw = schema.to_raw_frame(record, state.contract)
            features = predicting.prepare_input(raw, state.contract)
        except (predicting.PredictionError, DataError) as error:
            return 422, {"error": "Entrada invalida", "detalle": str(error)}, None

        try:
            prediction = await run_in_threadpool(_predict_sync, features)
        except Exception:
            # La entrada ya es valida: si el modelo falla, es un error del servidor
            logger.exception("El modelo %s fallo al predecir una entrada valida", state.version)
            return 500, {
                "error": "Error interno al predecir",
                "version": state.version,
                "detalle": (
                    f"El modelo de la version {state.version} no pudo predecir con una "
                    "entrada valida. El detalle quedo en el log del servidor."
                ),
            }, None
        return 200, {"prediccion": prediction, "version": state.version}, prediction

    @app.post("/predict", openapi_extra=_openapi_body(state.contract))
    async def predict(request: Request) -> JSONResponse:
        fecha = datetime.now(timezone.utc).isoformat()
        status, content, prediction = 500, {"error": "Error interno al predecir"}, None
        try:
            status, content, prediction = await _handle(request)
        except Exception:
            logger.exception("Error inesperado en /predict")
        finally:
            notify(EventoPrediccion(
                fecha=fecha,
                codigo_http=status,
                version=state.version,
                prediccion=prediction,
                detalle=None if status == 200 else content,
            ))
        return JSONResponse(status_code=status, content=content)

    # def, no async def: FastAPI lo corre en un hilo aparte y /health sigue
    # respondiendo mientras se entrena. No recibe parametros: el cuerpo se ignora.
    @app.post("/train", status_code=201)
    def train() -> JSONResponse:
        """Entrena una version nueva con la configuracion de la Fase 2 y la guarda.

        No cambia la version que sirve /predict: para usarla hay que cambiar
        MODEL_VERSION y reiniciar el servidor.
        """
        try:
            result = training.train_new_version(settings, state.version)
        except training.TrainingFailure as failure:
            return JSONResponse(status_code=failure.status, content=failure.content)
        except Exception:
            logger.exception("Error inesperado en /train")
            return JSONResponse(status_code=500, content={
                "error": "Error interno al entrenar",
                "detalle": "El detalle quedo en el log del servidor.",
            })
        return JSONResponse(status_code=201, content=result.content)

    return app
