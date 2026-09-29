# Proyecto Modelos 1: predicción de la calificación de películas

Proyecto integrador del curso Modelos y Simulación de Sistemas I (Universidad de Antioquia, Ingeniería de Sistemas, profesor Raúl Ramos). El proyecto lleva un modelo de Machine Learning desde un notebook hasta un prototipo desplegable, en cuatro fases acumulativas: modelo predictivo, scripts y Docker, API REST y monitoreo básico.

## Equipo

- Alejandro Múnera Ramírez
- Miguel Ángel Altamiranda
- Juan Esteban González Duque

## Problema

El equipo busca predecir la calificación promedio que los usuarios de TMDB le dan a una película (`vote_average`, escala continua de 0 a 10) a partir de características que se conocen antes o al momento del estreno: presupuesto, duración, género, idioma original, año de estreno y si pertenece a una franquicia. Es un problema de regresión.

## Dataset

- Nombre: The Movies Dataset (Rounak Banik), Kaggle.
- Enlace: https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset
- Archivo usado: `movies_metadata.csv` (34,4 MB, 45.466 filas, 24 columnas).
- Variable objetivo: `vote_average`.

El paquete de Kaggle trae siete archivos, pero el proyecto solo usa `movies_metadata.csv`, porque es el único donde cada fila es una película con sus predictoras y la variable objetivo juntas.

El CSV no se sube al repositorio (está en `.gitignore`). Para obtenerlo hay dos opciones:

1. Descarga manual: entrar al enlace de Kaggle, descargar el dataset, descomprimirlo y copiar solo `movies_metadata.csv` en la carpeta `data/` del repositorio.
2. Con la CLI de Kaggle (requiere tener configurado un token de la API de Kaggle):

   ```bash
   kaggle datasets download -d rounakbanik/the-movies-dataset -f movies_metadata.csv -p data
   ```

   Si el archivo queda comprimido (`movies_metadata.csv.zip`), se descomprime dentro de `data/`.

La ruta esperada por el notebook es `data/movies_metadata.csv`.

## Estructura del repositorio

```
proyecto-modelos-1/
  data/                  CSV del dataset (no versionado)
  fase-1/                Fase 1: notebook, modelo guardado y README de la fase
  requirements.txt       Dependencias del proyecto
  requirements.lock.txt  Versiones exactas probadas por el equipo
  verificar_entorno.py   Comprueba que el entorno quedó bien instalado
```

## Instalación

Requisitos: Python 3.12 y Git. El entorno se probó en Windows 11 ARM64 (Python ARM64 nativo); todas las dependencias tienen wheels precompiladas para esa plataforma.

```bash
git clone https://github.com/amunera66/proyecto-modelos-1.git
cd proyecto-modelos-1
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
python verificar_entorno.py
```

Para reproducir exactamente las versiones con las que trabajó el equipo se puede usar `pip install -r requirements.lock.txt` en lugar de `requirements.txt`. Ese archivo se generó en Windows e incluye paquetes solo de Windows (por ejemplo `pywinpty`); en Linux o macOS se usa `requirements.txt`.

Nota para Windows 11: si Smart App Control está activado, puede bloquear las DLL de numpy y pandas con el error "Una directiva de Control de aplicaciones bloqueó este archivo". En ese caso hay que desactivarlo en Seguridad de Windows, Control de aplicaciones y navegador.

## Flujo de trabajo en Git

- `main`: versiones entregadas.
- `develop`: rama de integración.
- `feature/*`: una rama por bloque de trabajo; cada una se integra a `develop` mediante un Pull Request.

## Fases

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Modelo predictivo (`fase-1/`) | En desarrollo |
| 2 | Scripts y Docker | Pendiente |
| 3 | API REST | Pendiente |
| 4 | Monitoreo básico | Pendiente |
