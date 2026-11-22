"""Cliente de prueba de la API: consulta /health y envia una prediccion a /predict.

Solo usa la biblioteca estandar. Con la API corriendo, desde fase-3/:

    python cliente/cliente.py
    python cliente/cliente.py --url http://localhost:8001

La entrada es una pelicula real del proyecto: Toy Story 2 (id 863 de TMDB), una
fila de movies_metadata.csv. Sus 6 predictoras se derivaron con las funciones de
fase-2 (data.clean_data, features.add_sequel_feature, data.apply_filters y
features.derive_features) sobre el CSV completo, y se dejan fijas aqui. En el
CSV, su vote_average es 7.3 con 3914 votos. Puede haber quedado en el
entrenamiento de v1, asi que la prediccion no es una evaluacion del modelo.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

PELICULA = "Toy Story 2 (id 863 en movies_metadata.csv; vote_average real: 7.3)"
ENTRADA = {
    "budget": 90000000,
    "runtime": 92,
    "release_year": 1999,
    "es_secuela": 1,
    "genero_principal": "Animation",
    "original_language": "en",
}
TIEMPO_MAXIMO = 30  # segundos


def solicitar(metodo: str, url: str, cuerpo: dict | None = None) -> tuple[int, object]:
    """Envia la solicitud y devuelve (codigo, cuerpo). Los 4xx y 5xx tambien se devuelven."""
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    solicitud = urllib.request.Request(url, data=datos, method=metodo)
    if datos is not None:
        solicitud.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(solicitud, timeout=TIEMPO_MAXIMO) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        texto = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(texto)
        except ValueError:
            return error.code, texto


def mostrar(titulo: str, metodo: str, url: str, cuerpo: dict | None = None) -> int:
    print(f"== {titulo}")
    print(f"{metodo} {url}")
    if cuerpo is not None:
        print("Solicitud:")
        print(json.dumps(cuerpo, indent=2, ensure_ascii=False))
    codigo, respuesta = solicitar(metodo, url, cuerpo)
    print(f"Respuesta (HTTP {codigo}):")
    print(json.dumps(respuesta, indent=2, ensure_ascii=False))
    print()
    return codigo


def main() -> int:
    parser = argparse.ArgumentParser(description="Cliente de prueba de /health y /predict.")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="URL base de la API (default: %(default)s)"
    )
    base = parser.parse_args().url.rstrip("/")

    try:
        salud = mostrar("Estado de la API", "GET", f"{base}/health")
        print(f"Pelicula: {PELICULA}")
        prediccion = mostrar("Prediccion", "POST", f"{base}/predict", ENTRADA)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        motivo = getattr(error, "reason", error)
        print(f"Error: no se pudo conectar con {base} ({motivo}). Revisa que la API este corriendo.",
              file=sys.stderr)
        return 1
    return 0 if salud == 200 and prediccion == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
