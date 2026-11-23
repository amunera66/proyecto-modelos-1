"""Esquema de /predict, construido desde el contrato_entrada de metadata.json.

Tipos estrictos (decision del equipo):
- numerica: entero o decimal finito; se rechazan textos y booleanos.
- binaria: solo los enteros de valores_validos (0 o 1); se rechazan 1.0 y true.
- categorica: solo texto; se rechazan numeros.
null solo se acepta donde el contrato pone nulos_permitidos. Las claves del
contrato son obligatorias y las demas se ignoran.
"""

import math
from typing import Annotated, Any

import pandas as pd
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, create_model
from pydantic_core import PydanticCustomError

KINDS = ("numerica", "binaria", "categorica")


def _allowed_text(valid_values: list) -> str:
    return " o ".join(str(value) for value in valid_values)


def _check_valid_values(valid_values: list):
    def check(value):
        if value is not None and value not in valid_values:
            raise PydanticCustomError(
                "valor_no_permitido",
                "Solo acepta los enteros {permitidos}",
                {"permitidos": _allowed_text(valid_values)},
            )
        return value

    return check


def _field_type(feature: dict) -> Any:
    kind = feature["tipo"]
    if kind not in KINDS:
        raise ValueError(f"Tipo desconocido en el contrato para {feature['nombre']}: {kind!r}")
    if kind == "numerica":
        base = Annotated[float, Field(strict=True, allow_inf_nan=False)]
    elif kind == "binaria":
        base = Annotated[int, Field(strict=True)]
    else:
        base = Annotated[str, Field(strict=True)]
    annotated = base | None if feature["nulos_permitidos"] else base
    if feature.get("valores_validos") is not None:
        annotated = Annotated[annotated, AfterValidator(_check_valid_values(feature["valores_validos"]))]
    return annotated


def build_input_model(contract: list[dict]) -> type[BaseModel]:
    """Crea el modelo de pydantic: todas las claves obligatorias, extras ignoradas."""
    fields = {feature["nombre"]: (_field_type(feature), ...) for feature in contract}
    return create_model(
        "EntradaPrediccion", __config__=ConfigDict(extra="ignore"), **fields
    )


def _expected_text(feature: dict) -> str:
    kind = feature["tipo"]
    if kind == "numerica":
        text = "un numero (entero o decimal)"
    elif kind == "binaria":
        text = f"uno de los enteros {_allowed_text(feature.get('valores_validos') or [0, 1])}"
    else:
        text = "un texto"
    return text + (" o null" if feature["nulos_permitidos"] else "")


def _json_safe(value: Any) -> Any:
    """inf y NaN no son JSON valido: se devuelven como texto."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def describe_errors(error: ValidationError, contract: list[dict]) -> list[dict]:
    """Traduce los errores de pydantic a [{campo, mensaje, valor_recibido}]."""
    by_name = {feature["nombre"]: feature for feature in contract}
    details = []
    for item in error.errors():
        name = str(item["loc"][0]) if item["loc"] else ""
        feature = by_name.get(name)
        detail = {"campo": name}
        if item["type"] == "missing":
            detail["mensaje"] = "Campo obligatorio ausente" + (
                "; si el dato falta, envia null" if feature and feature["nulos_permitidos"] else ""
            )
        else:
            received = item.get("input")
            if received is None and feature and not feature["nulos_permitidos"]:
                detail["mensaje"] = "No admite null"
            elif item["type"] == "finite_number":
                detail["mensaje"] = "Debe ser un numero finito"
            elif item["type"] == "valor_no_permitido":
                detail["mensaje"] = item["msg"]
            elif feature is not None:
                detail["mensaje"] = f"Debe ser {_expected_text(feature)}"
            else:
                detail["mensaje"] = item["msg"]
            detail["valor_recibido"] = _json_safe(received)
        details.append(detail)
    return details


def _to_text(value: Any) -> str:
    """Escribe un valor ya validado como lo leeria predicting.read_input desde un CSV.

    repr de un float conserva el valor exacto al volver a convertirlo en numero.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def to_raw_frame(record: BaseModel, contract: list[dict]) -> pd.DataFrame:
    """DataFrame de una fila, de texto, que acepta predicting.prepare_input."""
    values = record.model_dump()
    return pd.DataFrame(
        {feature["nombre"]: [_to_text(values[feature["nombre"]])] for feature in contract},
        dtype=object,
    )
