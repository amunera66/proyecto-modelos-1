"""Predice con una version guardada. La implementacion llega en el Paso 4."""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Predice vote_average con una version guardada del modelo.",
    )
    parser.add_argument(
        "--model", required=True, help="carpeta de la version o ruta a su modelo.joblib"
    )
    parser.add_argument(
        "--input", required=True, help="CSV con las 6 predictoras, sin el objetivo"
    )
    parser.add_argument("--output", required=True, help="CSV de salida con las predicciones")
    return parser


def main() -> int:
    build_parser().parse_args()
    print("predict.py: pendiente, se implementa en el Paso 4.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
