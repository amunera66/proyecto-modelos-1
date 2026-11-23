# Imagen de la API de la Fase 3. Solo trae el codigo y sus dependencias: los
# datos y los modelos se montan al ejecutar. Los comandos estan en el README.
#
# Se construye desde la raiz del repositorio, porque necesita fase-2/src:
#   docker build -f fase-3/Dockerfile -t modelos-fase3:1.0 .
# El contexto lo filtra fase-3/Dockerfile.dockerignore.
FROM python:3.12.10-slim

# /app es la raiz del repositorio dentro de la imagen. Se conserva la estructura
# fase-2/src y fase-3/api para que api/_fase2.py encuentre src, y para que las
# rutas por defecto (fase-2/models y fase-2/data/movies_metadata.csv) apunten a
# los montajes /app/fase-2/models y /app/fase-2/data.
WORKDIR /app

# Las dependencias van primero para reutilizar esta capa si solo cambia el codigo
COPY fase-3/requirements.txt fase-3/requirements.txt
RUN pip install --no-cache-dir -r fase-3/requirements.txt

COPY fase-2/src/ fase-2/src/
COPY fase-3/api/ fase-3/api/

WORKDIR /app/fase-3
EXPOSE 8000

# 0.0.0.0 para que la API responda fuera del contenedor (con -p 8000:8000)
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
