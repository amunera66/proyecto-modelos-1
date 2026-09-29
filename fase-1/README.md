# Fase 1: modelo predictivo

Esta fase construye un modelo de regresión que predice `vote_average` (calificación promedio de los usuarios de TMDB, de 0 a 10) a partir de características conocidas antes o al momento del estreno de una película. El problema, el dataset y la instalación del entorno se describen en el [README principal](../README.md).

## Contenido de la carpeta

- `fase1_modelo_predictivo.ipynb`: notebook con la carga, limpieza, análisis exploratorio, preparación de variables, entrenamiento, evaluación y guardado del modelo.
- `models/`: pipeline entrenado guardado con joblib.

## Cómo ejecutar el notebook

1. Tener el entorno instalado y `data/movies_metadata.csv` en su lugar (ver el README principal).
2. Abrir el notebook y ejecutarlo completo con el kernel del entorno virtual del proyecto (`.venv`):
   - En VS Code: abrir `fase1_modelo_predictivo.ipynb`, seleccionar el intérprete `.venv` como kernel y usar "Restart" y luego "Run All".
   - En Jupyter: desde la raíz del repositorio, con el entorno activado, ejecutar `jupyter lab` y abrir el notebook; luego "Kernel", "Restart Kernel and Run All Cells".
3. Para comprobar que corre de principio a fin sin abrir la interfaz, desde la raíz del repositorio:

   ```bash
   jupyter nbconvert --to notebook --execute fase-1/fase1_modelo_predictivo.ipynb --output-dir /tmp --output verificacion.ipynb
   ```

   En Windows se puede usar cualquier carpeta temporal en `--output-dir`. El comando termina con error si alguna celda falla, y no modifica el notebook original.

## Limpieza de datos

El archivo original tiene 45.466 filas y 24 columnas. El notebook elimina 36 filas:

- 3 filas corruptas por errores de parsing: algunas sinopsis tienen comas o saltos de línea mal escapados, y los valores quedan desplazados de columna (en `adult` aparece texto, en `budget` la ruta de un póster y en `id` una fecha). Se detectan porque `id` no es numérico.
- 3 filas incompletas, que son la primera mitad de esas mismas líneas partidas: solo tienen entre 8 y 10 columnas con dato y no tienen `vote_average`.
- 30 filas duplicadas: 29 películas aparecen repetidas con el mismo `id` y sus copias solo difieren en `popularity` y `vote_count`. Se conserva la primera aparición. Esto además evita que una misma película quede a la vez en entrenamiento y en prueba.

El dataset limpio tiene 45.430 películas.

## Hallazgos del análisis exploratorio

- `vote_average` no tiene nulos después de la limpieza, pero 2.896 películas (6,4 %) tienen 0 votos y por eso una calificación de 0 que no es real. El 52,1 % de las películas tiene 10 votos o menos, y la calificación es más dispersa cuanto menos votos hay (desviación estándar de 1,66 con 1 a 5 votos frente a 0,86 con más de 100).
- `budget` tiene 80,5 % de ceros y `runtime` 3,43 % de ceros: son faltantes codificados como 0.
- `runtime` tiene 257 nulos reales (0,57 %), lo que cumple el requisito de la guía de que alguna predictora tenga entre 0,1 % y 2 % de faltantes.
- `original_language` tiene 89 idiomas, con el inglés en el 71 % de las películas.
- Solo el 9,9 % de las películas pertenece a una colección (`belongs_to_collection`).

## Resultados

Pendiente: se completa cuando el notebook incluya el entrenamiento y la evaluación del modelo.
