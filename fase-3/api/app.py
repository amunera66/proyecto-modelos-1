"""Objeto app para uvicorn. Importar este modulo crea la app y carga el modelo.

Ejecutar desde fase-3/:  uvicorn api.app:app
Las pruebas deben importar create_app desde api.main, que no carga nada.
"""

from api.main import create_app

app = create_app()
