"""Observador que registra cada intento a /predict en un CSV.

Formato (una fila por intento, UTF-8, separador coma, fin de linea \\n):

    fecha_hora,estado_http,version,prediccion
    2026-11-22T18:04:05+00:00,200,v1,6.758120437797601
    2026-11-22T18:04:06+00:00,422,,

- fecha_hora: llegada de la solicitud, ISO 8601 en UTC, a segundos, con +00:00.
- estado_http: codigo HTTP de la respuesta.
- version: solo cuando se uso el modelo (200 y 500); vacia en 400, 422 y 503.
- prediccion: solo en los 200; vacia en cualquier error.

El archivo se abre en modo agregar, asi que el historial se conserva entre
ejecuciones. El encabezado se escribe solo si el archivo no existe o esta vacio.
"""

import csv
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COLUMNS = ("fecha_hora", "estado_http", "version", "prediccion")
STATUS_WITH_VERSION = (200, 500)  # codigos en los que se llego a usar el modelo
STATUS_WITH_PREDICTION = (200,)


def format_timestamp(value: str | datetime) -> str:
    """ISO 8601 en UTC, a segundos: 2026-11-22T18:04:05+00:00."""
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    if moment.tzinfo is None:  # fase-3 siempre manda la zona; por si acaso se asume UTC
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def build_row(evento: Any) -> list:
    """Convierte un EventoPrediccion de fase-3 en una fila del CSV."""
    status = int(evento.codigo_http)
    version = evento.version if status in STATUS_WITH_VERSION and evento.version else ""
    prediction = evento.prediccion if status in STATUS_WITH_PREDICTION else None
    return [
        format_timestamp(evento.fecha),
        status,
        version,
        "" if prediction is None else repr(float(prediction)),
    ]


class RegistroCSV:
    """Observador para create_app(observer=...): agrega una fila por cada evento.

    El lock evita que dos solicitudes simultaneas mezclen sus filas dentro del
    mismo proceso. No protege contra varios procesos escribiendo el mismo
    archivo: el servidor debe correr con un solo worker.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, evento: Any) -> None:
        row = build_row(evento)
        with self._lock:
            # La carpeta se revisa en cada escritura por si se borro con el servidor en marcha
            self.path.parent.mkdir(parents=True, exist_ok=True)
            needs_header = not self.path.exists() or self.path.stat().st_size == 0
            with self.path.open("a", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, lineterminator="\n")
                if needs_header:
                    writer.writerow(COLUMNS)
                writer.writerow(row)
