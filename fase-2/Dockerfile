# Imagen de la aplicacion. Solo trae el codigo y sus dependencias: los datos y
# los modelos se montan al ejecutar. Los comandos estan en docs/docker.md.
FROM python:3.12.10-slim

WORKDIR /app

# Las dependencias van primero para reutilizar esta capa si solo cambia el codigo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY train.py predict.py ./

CMD ["python", "predict.py", "--help"]
