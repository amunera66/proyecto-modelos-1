"""Entrena y versiona el modelo. La implementacion llega en el Paso 3."""

import argparse
import sys

from src import config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Entrena el modelo de vote_average y guarda una version nueva.",
    )
    parser.add_argument("--data", required=True, help="ruta al CSV crudo movies_metadata.csv")
    parser.add_argument(
        "--target", default=config.TARGET, help="columna objetivo (default: %(default)s)"
    )
    parser.add_argument(
        "--output-dir", default="models", help="carpeta de versiones (default: %(default)s)"
    )
    parser.add_argument(
        "--version", required=True, help="identificador de la version nueva, por ejemplo v1"
    )
    parser.add_argument(
        "--seed", type=int, default=config.SEED, help="semilla (default: %(default)s)"
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=config.TEST_SIZE,
        help="proporcion de prueba (default: %(default)s)",
    )
    parser.add_argument(
        "--min-votes",
        type=int,
        default=config.MIN_VOTES,
        help="conserva vote_count mayor que este valor (default: %(default)s)",
    )
    return parser


def main() -> int:
    build_parser().parse_args()
    print("train.py: pendiente, se implementa en el Paso 3.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
