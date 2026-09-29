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

## Población del modelo

El modelo se entrena y evalúa con 21.656 películas, tras dos filtros de filas con umbrales fijos:

- `status == "Released"`: se descartan 445 películas no estrenadas, porque la calificación de los usuarios se forma después del estreno.
- `vote_count > 10`: se descartan 23.329 películas estrenadas con 10 votos o menos. Las películas con 0 votos tienen `vote_average = 0` sin que nadie las haya calificado, y con pocos votos el promedio es muy ruidoso.

`vote_count` se usa solo para filtrar filas, como criterio de confiabilidad de la variable objetivo, y nunca como predictora. En consecuencia, el modelo aplica a películas estrenadas con un mínimo de votos; para películas con muy pocos votos sus predicciones no están validadas.

## Preparación de variables

| Predictora | Tipo | Origen y transformación |
|---|---|---|
| `budget` | numérica | 0 se convierte en `NaN` (presupuesto no reportado) |
| `runtime` | numérica | 0 se convierte en `NaN` (duración no reportada) |
| `release_year` | numérica | año de `release_date` |
| `es_franquicia` | binaria | 1 si `belongs_to_collection` tiene valor |
| `genero_principal` | categórica | primer género de la lista de `genres` (parseada con `ast.literal_eval`); `sin_genero` si está vacía |
| `original_language` | categórica | sin cambios; los idiomas poco frecuentes se agrupan dentro del Pipeline |

El género principal es un supuesto del equipo: TMDB no garantiza que el primer género de la lista sea el principal de la película.

Sobre el requisito de faltantes de la guía (entre 0,1 % y 2 % en alguna predictora): se cumple en el dataset original, donde `runtime` tiene 0,57 % de nulos reales. En las predictoras finales `runtime` tiene 0,96 % de faltantes, porque los valores 0 se convirtieron a `NaN` y el filtro cambió el total de películas. `budget` queda con 65,6 % de faltantes por la misma conversión.

## Fuga de información

El equipo aplicó tres medidas para evitar que el modelo use información que no estaría disponible al momento de predecir:

1. Exclusión de columnas: `vote_count`, `popularity` y `revenue` no se usan como predictoras, porque se generan después del estreno, en la misma ventana de tiempo en que se acumula la calificación. El notebook verifica con una aserción que ninguna quede entre las predictoras.
2. Split antes del preprocesamiento: los datos se dividen en train (80 %, 17.324 películas) y test (20 %, 4.332 películas) con semilla fija antes de imputar, escalar o codificar. Antes del split solo se hacen transformaciones fila por fila que no calculan estadísticas sobre el conjunto (convertir 0 en `NaN`, extraer el año, tomar el primer género, filtrar con umbrales fijos).
3. Preprocesamiento dentro de un Pipeline de scikit-learn: un `ColumnTransformer` imputa las numéricas con la mediana (con indicador de faltante) y las escala, e imputa y codifica las categóricas con `OneHotEncoder(min_frequency=0.01, handle_unknown="infrequent_if_exist")`. Las medianas, medias, desviaciones y la lista de idiomas y géneros frecuentes se aprenden solo con train y luego se aplican a test. Así, la agrupación de idiomas poco frecuentes no usa información de test, y una categoría nueva en test cae en el grupo "infrecuente" sin error.

Además, eliminar las películas duplicadas en la limpieza evita que una misma película quede a la vez en train y en test.

## Resultados

Pendiente: se completa cuando el notebook incluya el entrenamiento y la evaluación del modelo.
