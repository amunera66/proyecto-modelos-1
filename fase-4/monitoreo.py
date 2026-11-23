"""Monitoreo del registro de predicciones: total de solicitudes y porcentaje de fallos.

Desde fase-4/:

    python monitoreo.py
    python monitoreo.py --registro registros/muestra_predicciones.csv

Sin --registro usa la ruta de registro.config: LOG_PATH, o
fase-4/registros/predicciones.csv por defecto. Solo usa la biblioteca estandar
(csv): no importa registro.app, asi que no crea la app ni carga el modelo.

- Total de solicitudes: filas del CSV sin el encabezado.
- Fallidas: filas con estado_http >= 400 (4xx y 5xx). No se usan version ni
  prediccion, que pueden estar vacias por otros motivos.
- No se supone que las filas esten ordenadas por fecha_hora: el conteo no
  depende del orden.
"""

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from registro.config import log_path_from_env
from registro.csv_logger import COLUMNS

REPO_ROOT = Path(__file__).resolve().parent.parent
FAILED_FROM = 400  # 4xx y 5xx
NO_REQUESTS = "sin solicitudes"
NO_VERSION = "(sin version)"


class RegistroInvalidoError(Exception):
    """El registro existe pero no se puede leer o no tiene el formato esperado."""


@dataclass
class Resumen:
    """Conteos del registro."""

    total: int = 0
    fallidas: int = 0
    por_codigo: Counter = field(default_factory=Counter)
    por_version: Counter = field(default_factory=Counter)


@dataclass
class Lectura:
    """Filas leidas y el estado del archivo."""

    filas: list[dict]
    existe: bool = True
    vacio: bool = False


def leer_registro(path: Path) -> Lectura:
    """Lee el CSV del registro y valida el encabezado y estado_http.

    Si el archivo no existe o esta vacio devuelve cero filas. Lanza
    RegistroInvalidoError si el encabezado no es COLUMNS, si una fila no tiene
    4 columnas o si estado_http no es un entero.
    """
    if not path.exists():
        return Lectura(filas=[], existe=False)
    if not path.is_file():
        raise RegistroInvalidoError(f"{path} no es un archivo")
    try:
        # utf-8-sig tolera un BOM, por si el archivo se guardo desde Excel
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            header = next(reader, None)
            if header is None:
                return Lectura(filas=[], vacio=True)
            if tuple(header) != COLUMNS:
                raise RegistroInvalidoError(
                    f"El encabezado no coincide con el del registro. "
                    f"Esperado: {','.join(COLUMNS)}. Encontrado: {','.join(header)}"
                )
            filas = []
            for row in reader:
                if not row:  # linea en blanco
                    continue
                line = reader.line_num
                if len(row) != len(COLUMNS):
                    raise RegistroInvalidoError(
                        f"La linea {line} tiene {len(row)} columnas; se esperaban {len(COLUMNS)}"
                    )
                fila = dict(zip(COLUMNS, row))
                try:
                    fila["estado_http"] = int(fila["estado_http"])
                except ValueError:
                    raise RegistroInvalidoError(
                        f"La linea {line} tiene un estado_http que no es un entero: "
                        f"{fila['estado_http']!r}"
                    ) from None
                filas.append(fila)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise RegistroInvalidoError(f"No se pudo leer {path}: {error}") from error
    return Lectura(filas=filas)


def es_fallida(estado_http: int) -> bool:
    """4xx o 5xx."""
    return estado_http >= FAILED_FROM


def resumir(filas: list[dict]) -> Resumen:
    """Cuenta el total, las fallidas y el desglose por codigo y por version."""
    resumen = Resumen()
    for fila in filas:
        estado = fila["estado_http"]
        resumen.total += 1
        resumen.fallidas += es_fallida(estado)
        resumen.por_codigo[estado] += 1
        resumen.por_version[fila["version"] or NO_VERSION] += 1
    return resumen


def porcentaje_fallos(resumen: Resumen) -> float | None:
    """Fallidas / total x 100, o None si no hay solicitudes."""
    if resumen.total == 0:
        return None
    return resumen.fallidas / resumen.total * 100


def formatear_porcentaje(valor: float | None) -> str:
    """Un decimal con coma, como en la especificacion: 33,3 %."""
    if valor is None:
        return NO_REQUESTS
    return f"{valor:.1f}".replace(".", ",") + " %"


def ruta_para_mostrar(path: Path) -> str:
    """Relativa a la raiz del repositorio si esta dentro; si no, tal como se recibio."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def formatear_reporte(path: Path, lectura: Lectura, resumen: Resumen) -> str:
    """Texto que muestra el script."""
    lineas = [f"Registro: {ruta_para_mostrar(path)}"]
    if not lectura.existe:
        lineas.append("Aviso: el archivo no existe; todavia no se ha registrado ninguna solicitud.")
    elif lectura.vacio:
        lineas.append("Aviso: el archivo esta vacio; no tiene ni el encabezado.")
    lineas += [
        f"Total de solicitudes: {resumen.total}",
        f"Solicitudes fallidas (4xx o 5xx): {resumen.fallidas}",
        f"Porcentaje de fallos: {formatear_porcentaje(porcentaje_fallos(resumen))}",
    ]
    if resumen.total:
        lineas += ["", "Por codigo HTTP:"]
        for codigo, cantidad in sorted(resumen.por_codigo.items()):
            marca = " (fallida)" if es_fallida(codigo) else ""
            lineas.append(f"  {codigo}: {cantidad}{marca}")
        lineas += ["", "Por version:"]
        for version, cantidad in sorted(resumen.por_version.items()):
            lineas.append(f"  {version}: {cantidad}")
    return "\n".join(lineas)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Muestra el total de solicitudes a /predict y el porcentaje de fallidas "
            "(HTTP 4xx o 5xx) a partir del registro CSV."
        )
    )
    parser.add_argument(
        "--registro",
        type=Path,
        default=None,
        help=(
            "CSV del registro. Por defecto, LOG_PATH o fase-4/registros/predicciones.csv. "
            "Una ruta relativa se toma desde la carpeta actual."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    path = args.registro if args.registro is not None else log_path_from_env()
    try:
        lectura = leer_registro(path)
    except RegistroInvalidoError as error:
        print(f"Error en el registro {ruta_para_mostrar(path)}: {error}", file=sys.stderr)
        return 1
    print(formatear_reporte(path, lectura, resumir(lectura.filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
