"""Hace importable el paquete api de fase-3 sin copiarlo.

Las rutas se calculan desde este archivo: no hay rutas absolutas y funciona
igual en local y en Docker si se conserva la estructura <raiz>/fase-2,
<raiz>/fase-3 y <raiz>/fase-4. Al importar api, fase-3 hace lo mismo con
fase-2 (api/_fase2.py), que necesita el modelo guardado.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FASE3_DIR = REPO_ROOT / "fase-3"

if not (FASE3_DIR / "api" / "__init__.py").is_file():
    raise ImportError(f"No se encontro el paquete api de fase-3 en {FASE3_DIR / 'api'}")

if str(FASE3_DIR) not in sys.path:
    sys.path.insert(0, str(FASE3_DIR))

import api  # noqa: E402

if Path(api.__file__).resolve().parent != (FASE3_DIR / "api").resolve():
    raise ImportError(
        f"Se importo otro paquete api ({api.__file__}), no el de fase-3. "
        "Revisa PYTHONPATH o la carpeta desde la que se ejecuta."
    )
