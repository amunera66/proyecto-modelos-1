"""Hace importable el paquete src de fase-2 sin copiarlo.

El modelo.joblib guarda una referencia a src.features.prepare_model_input, asi
que src debe importarse con ese nombre exacto. Por eso fase-3 no tiene un
paquete propio llamado src. Las rutas se calculan desde este archivo: no hay
rutas absolutas y funciona igual en local y en Docker, si se conserva la
estructura <raiz>/fase-2 y <raiz>/fase-3.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FASE2_DIR = REPO_ROOT / "fase-2"

if not (FASE2_DIR / "src" / "__init__.py").is_file():
    raise ImportError(f"No se encontro el paquete src de fase-2 en {FASE2_DIR / 'src'}")

if str(FASE2_DIR) not in sys.path:
    sys.path.insert(0, str(FASE2_DIR))

import src  # noqa: E402

if Path(src.__file__).resolve().parent != (FASE2_DIR / "src").resolve():
    raise ImportError(
        f"Se importo otro paquete src ({src.__file__}), no el de fase-2. "
        "Revisa PYTHONPATH o la carpeta desde la que se ejecuta."
    )
