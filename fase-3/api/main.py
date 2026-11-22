"""API REST de la Fase 3: GET /health y POST /predict.

Ejecutar desde fase-3/:  uvicorn api.main:app
La logica de prediccion es la de fase-2/src (versioning y predicting): aqui solo
se valida el JSON, se arma la respuesta y se avisa al observador.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from api._fase2 import REPO_ROOT  # debe ir antes de importar src
from api import schema
from api.config import Settings
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


def _display(path: Path) -> str:
    """Ruta relativa a la raiz del repo si esta dentro de el, para no exponer rutas locales."""
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _hide_root(text: str) -> str:
    """Quita el prefijo de la raiz del repo de un mensaje de fase-2."""
    for root in (str(REPO_ROOT.resolve()), str(REPO_ROOT)):
        text = text.replace(root + "\\", "").replace(root + "/", "")
    return text


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
        state.version = metadata.get("version", settings.model_version)
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

    def _predict_sync(record: BaseModel) -> float:
        raw = schema.to_raw_frame(record, state.contract)
        features = predicting.prepare_input(raw, state.contract)
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
            prediction = await run_in_threadpool(_predict_sync, record)
        except (predicting.PredictionError, DataError) as error:
            # Segunda capa: las reglas de fase-2 para la misma entrada
            return 422, {"error": "Entrada invalida", "detalle": str(error)}, None
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

    return app


app = create_app()
