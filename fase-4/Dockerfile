# Imagen de la API de la Fase 4: la de fase-3 con el registro de predicciones.
# Solo trae el codigo y sus dependencias: los datos, los modelos y el registro se
# montan al ejecutar. Los comandos estan en el README.
#
# Se construye desde la raiz del repositorio, porque necesita fase-2/src y fase-3/api:
#   docker build -f fase-4/Dockerfile -t modelos-fase4:1.0 .
# El contexto lo filtra fase-4/Dockerfile.dockerignore.
FROM python:3.12.10-slim

# /app es la raiz del repositorio dentro de la imagen. Se conserva la estructura
# fase-2/src, fase-3/api y fase-4/registro porque los imports se calculan con
# rutas relativas (registro/_fase3.py y api/_fase2.py), y para que las rutas por
# defecto (fase-2/models, fase-2/data/movies_metadata.csv y
# fase-4/registros/predicciones.csv) apunten a los montajes.
WORKDIR /app

# Las dependencias van primero para reutilizar esta capa si solo cambia el codigo.
# fase-4/requirements.txt tiene las mismas versiones de fase-3/requirements.txt.
COPY fase-4/requirements.txt fase-4/requirements.txt
RUN pip install --no-cache-dir -r fase-4/requirements.txt

COPY fase-2/src/ fase-2/src/
COPY fase-3/api/ fase-3/api/
COPY fase-4/registro/ fase-4/registro/
COPY fase-4/monitoreo.py fase-4/monitoreo.py

WORKDIR /app/fase-4
EXPOSE 8000

# Un solo worker (el valor por defecto): el lock del registro vale dentro de un proceso.
# 0.0.0.0 para que la API responda fuera del contenedor (con -p 8000:8000).
CMD ["uvicorn", "registro.app:app", "--host", "0.0.0.0", "--port", "8000"]
