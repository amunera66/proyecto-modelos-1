"""Entrena el modelo y guarda una version nueva. La logica esta en src/training.py."""

import argparse
import sys

from src import config, splitting
from src.data import DataError
from src.training import TrainingError, TrainingOptions, format_summary, train_model
from src.versioning import VersionError


def _proportion(text: str) -> float:
    value = float(text)
    if not 0 < value < 1:
        raise argparse.ArgumentTypeError("debe ser un numero entre 0 y 1")
    return value


def _non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("debe ser un entero mayor o igual a 0")
    return value


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
        "--version",
        required=True,
        help="identificador de la version nueva, por ejemplo v1; nunca se sobrescribe",
    )
    parser.add_argument(
        "--seed",
        type=_non_negative_int,
        default=config.SEED,
        help="semilla (default: %(default)s)",
    )
    parser.add_argument(
        "--test-size",
        type=_proportion,
        default=config.TEST_SIZE,
        help="proporcion de prueba; con group se aplica a los grupos (default: %(default)s)",
    )
    parser.add_argument(
        "--min-votes",
        type=_non_negative_int,
        default=config.MIN_VOTES,
        help="conserva vote_count mayor que este valor (default: %(default)s)",
    )
    parser.add_argument(
        "--split-strategy",
        choices=splitting.SPLIT_STRATEGIES,
        default=config.SPLIT_STRATEGY,
        help="particion; random sirve para comparar con la Fase 1 (default: %(default)s)",
    )
    parser.add_argument(
        "--sixth-feature",
        choices=config.SIXTH_FEATURE_OPTIONS,
        default=config.SIXTH_FEATURE,
        help="sexta predictora; es_franquicia sirve para comparar con la Fase 1 "
        "(default: %(default)s)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    options = TrainingOptions(
        data_path=args.data,
        version=args.version,
        target=args.target,
        output_dir=args.output_dir,
        seed=args.seed,
        test_size=args.test_size,
        min_votes=args.min_votes,
        split_strategy=args.split_strategy,
        sixth_feature=args.sixth_feature,
    )
    try:
        result = train_model(options)
    except (DataError, TrainingError, VersionError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(format_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
