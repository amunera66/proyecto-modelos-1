"""Predice con una version guardada. La logica esta en src/predicting.py."""

import argparse
import sys

from src.data import DataError
from src.predicting import PredictionError, predict_file
from src.versioning import VersionError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predice vote_average con una version guardada del modelo.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="carpeta de la version (por ejemplo models/v1) o ruta a su modelo.joblib",
    )
    parser.add_argument(
        "--input", required=True, help="CSV con las 6 predictoras, sin la variable objetivo"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="CSV de salida: identificador si viene, predictoras y columna prediccion",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = predict_file(args.model, args.input, args.output)
    except (DataError, PredictionError, VersionError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if result.ignored_columns:
        ignored = ", ".join(result.ignored_columns)
        print(f"Aviso: se ignoran columnas que no usa el modelo: {ignored}", file=sys.stderr)
    print(f"{result.rows} predicciones guardadas en {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
