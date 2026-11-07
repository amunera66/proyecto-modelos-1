# Fase 2: predicción de la calificación de películas

Proyecto integrador de Modelos y Simulación de Sistemas I (Universidad de Antioquia).

**Integrantes:** Alejandro Múnera Ramírez, Miguel Ángel Altamiranda y Juan Esteban González Duque.

## Problema y relación con la Fase 1

Se predice `vote_average`, la calificación promedio de TMDB (de 0 a 10), a partir de 6 predictoras que se conocen al estreno. Es un problema de regresión.

La [Fase 1](../fase-1/README.md) dejó un notebook y un modelo. Esta fase lo convierte en una aplicación reutilizable: `train.py` entrena y guarda versiones, `predict.py` predice con una versión guardada, y todo corre también en Docker. El algoritmo sigue siendo `HistGradientBoostingRegressor`.

Las decisiones del equipo y sus cifras están en [docs/decisiones.md](docs/decisiones.md).

## Correcciones respecto a la Fase 1

El detalle y la evidencia están en [docs/correcciones_fase1.md](docs/correcciones_fase1.md).

| Corrección | Qué cambió |
|---|---|
| C1. EDA complementario | Correlaciones, relación con el objetivo, análisis por género e idioma, y redundancias. No hay predictoras redundantes: la mayor correlación es 0,323 |
| C2. Partición por grupos | Con la partición aleatoria, 469 colecciones quedaban en entrenamiento y en prueba. Con `GroupShuffleSplit` y `GroupKFold(5)` quedan 0 |
| C3. `es_secuela` | Reemplaza a `es_franquicia`, porque el 38,0 % de las películas con colección son la primera de su saga y la colección podría no existir al estreno. Siguen siendo 6 predictoras |
| C4. Estabilidad entre CV y prueba | La cercanía entre CV y prueba es evidencia favorable, no una garantía. Con 10 semillas, la prueba de la Fase 1 (RMSE 0,7813) quedó por debajo del promedio de la partición aleatoria (0,7921, desviación de 0,0079): esa partición resultó favorable |
| C5. Filtros explícitos | `status == "Released"` y `vote_count > 10` son reglas fijas en `src/config.py` y quedan en `metadata.json` |
| Parada temprana desactivada | `early_stopping=False`, porque su validación interna ignora los grupos. No empeora el RMSE de CV: lo mejora 0,0006 en promedio de 10 semillas |

## Qué se predice

El modelo predice `vote_average` **acumulado hasta la fecha de corte del dataset, que no está verificada**. Se entrenó solo con películas en `status == "Released"` y con más de 10 votos: 21.656 de las 45.466 filas del CSV.

Esto implica que:

- El horizonte no es igual para todas: una película de 1995 acumuló votos durante más de 20 años, y una de 2017, semanas o meses.
- No predice la calificación final de una película, sino un promedio a una fecha desconocida.
- Para una película con pocos votos, o sin estrenar, el modelo está por fuera de la población con la que se entrenó.

## Requisitos y entorno

Se necesita Python 3.12.10. Los comandos se ejecutan desde `fase-2/`.

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación del entorno, llama directamente a su Python, también en los demás comandos de esta guía:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe train.py --help
```

Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash en Windows
# source .venv/bin/activate     # Linux o macOS
python -m pip install -r requirements.txt
```

El notebook `notebooks/analisis_correcciones.ipynb` necesita además `requirements-notebook.txt`:

```text
python -m pip install -r requirements.txt -r requirements-notebook.txt
```

## Datos

La aplicación usa `movies_metadata.csv` de [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) (Rounak Banik, Kaggle). Descárgalo de Kaggle y déjalo en `data/movies_metadata.csv`. El archivo no se sube al repositorio. [data/README.md](data/README.md) explica la descarga, incluida la CLI de Kaggle.

Verifica que sea el archivo de referencia (34.445.126 bytes). Si el hash no coincide, las métricas pueden cambiar.

PowerShell (debe mostrar `True`):

```powershell
(Get-FileHash data\movies_metadata.csv -Algorithm SHA256).Hash -eq "37ec322786b136a24604564e55160be75f8937546f11cb1a990076971fa895fd"
```

Bash (debe mostrar ese mismo hash):

```bash
sha256sum data/movies_metadata.csv
```

### CSV de predicción

`train.py` recibe el CSV crudo. `predict.py` recibe las 6 predictoras ya derivadas, sin la variable objetivo, en cualquier orden y en UTF-8. Puede traer `id` o `title`, que se copian a la salida. [data/ejemplo_prediccion.csv](data/ejemplo_prediccion.csv) es un ejemplo de 12 filas.

| Columna | Tipo | Admite nulos | Ejemplo |
|---|---|---|---|
| `budget` | numérica | Sí | `165000000` |
| `runtime` | numérica | Sí | `155` |
| `release_year` | numérica | Sí | `2021` |
| `es_secuela` | binaria: 0 o 1 | No | `0` |
| `genero_principal` | categórica | Sí | `Science Fiction` |
| `original_language` | categórica | Sí | `en` |

## Uso

### Entrenar

Crea una versión nueva en `models/` y nunca sobrescribe una existente.

PowerShell:

```powershell
python train.py --help
python train.py --data data\movies_metadata.csv --version v3
```

Bash:

```bash
python train.py --help
python train.py --data data/movies_metadata.csv --version v3
```

| Argumento | Default | Uso |
|---|---|---|
| `--data` | obligatorio | CSV crudo |
| `--version` | obligatorio | Identificador de la versión |
| `--target` | `vote_average` | Columna objetivo |
| `--output-dir` | `models` | Carpeta de versiones |
| `--seed` | 42 | Semilla de la partición y del modelo |
| `--test-size` | 0.2 | Con `group` se aplica a los grupos, no a las filas |
| `--min-votes` | 10 | Conserva `vote_count` mayor que este valor |
| `--split-strategy` | `group` | `random` sirve para comparar con la Fase 1 |
| `--sixth-feature` | `es_secuela` | `es_franquicia` sirve para comparar con la Fase 1 |

### Predecir

`--model` acepta la carpeta de la versión o la ruta a su `modelo.joblib`. `predict.py` nunca entrena ni reajusta transformaciones.

PowerShell:

```powershell
python predict.py --help
python predict.py --model models\v1 --input data\ejemplo_prediccion.csv --output outputs\predicciones_v1.csv
```

Bash:

```bash
python predict.py --help
python predict.py --model models/v1 --input data/ejemplo_prediccion.csv --output outputs/predicciones_v1.csv
```

La salida trae el identificador si venía, las 6 predictoras tal como se escribieron y la columna `prediccion`, con una fila por cada fila de entrada, en el mismo orden.

### Comportamiento ante la entrada

| Caso | Comportamiento |
|---|---|
| Columnas adicionales | Se ignoran con un aviso en stderr, salvo `id` y `title` |
| Columnas en otro orden | Se reordenan según el contrato |
| Categoría no vista | No da error ni aviso: predice igual que una categoría conocida pero poco frecuente |
| Mayúsculas en categorías | Se distinguen: `EN` no es `en`. Cuenta como desconocida y cambia la predicción sin avisar |
| `budget` o `runtime` en 0 | Se tratan como faltantes: 0 y nulo dan la misma predicción. La salida conserva el 0 |
| Nulos en numéricas | Los resuelve la mediana de entrenamiento, guardada en el modelo |
| `genero_principal` nulo | Se imputa como `sin_genero` |
| `original_language` nulo | Se imputa con la moda de entrenamiento, `en` |
| Columna requerida ausente | Error que nombra la columna |
| `es_secuela` nula o distinta de 0 y 1 | Error con la columna y unas filas de ejemplo |
| Texto o `inf` en una numérica | Error con la columna y unas filas de ejemplo |
| Coma final en las filas | Se acepta si el campo sobrante está vacío; si trae datos, es un error que indica la línea |

Son nulas las celdas vacías y los textos `NA`, `N/A`, `NaN`, `nan`, `NULL`, `null`, `None` y `<NA>`. Los errores previsibles van a stderr, con código de salida 1, y no crean el archivo de salida.

## Dónde queda cada cosa

| Qué | Dónde |
|---|---|
| Modelo con su preprocesamiento | `models/<version>/modelo.joblib` |
| Métricas del modelo y del baseline | `models/<version>/metrics.json` |
| Metadatos: contrato, datos, partición, entorno y commit | `models/<version>/metadata.json` |
| Predicciones | La ruta de `--output`; `outputs/` no se sube al repositorio |

### Qué diferencia a v1 de v2

Las dos usan el mismo CSV, el commit `878d57a`, `es_secuela`, partición por grupos y los mismos hiperparámetros. **La única diferencia es la semilla:** `v1` usa 42 y `v2`, `--seed 7`. Sin parada temprana, la semilla solo cambia qué películas quedan en entrenamiento y en prueba.

El mejor resultado de `v2` en prueba no la hace mejor: se evaluó con otras películas, y en CV las dos rinden casi igual. Sobre el CSV de ejemplo, sus predicciones difieren hasta en 0,34 puntos, lo que mide cuánto depende una predicción de la partición.

## Métricas

La CV es `GroupKFold(5)` sobre entrenamiento, con la media (desviación entre folds). El modelo reduce el RMSE de prueba frente al baseline en las dos versiones.

| Versión | Modelo | Filas train / prueba | CV MAE | CV RMSE | CV R² | Prueba MAE | Prueba RMSE | Prueba R² |
|---|---|---|---|---|---|---|---|---|
| `v1` | HGB | 17.335 / 4.321 | 0,6150 (0,0115) | 0,7946 (0,0217) | 0,3490 (0,0140) | 0,6199 | 0,8007 | 0,3491 |
| `v1` | Baseline | 17.335 / 4.321 | 0,7776 (0,0089) | 0,9852 (0,0176) | −0,0008 (0,0011) | 0,7854 | 0,9930 | −0,0010 |
| `v2` | HGB | 17.318 / 4.338 | 0,6152 (0,0060) | 0,7948 (0,0124) | 0,3460 (0,0243) | 0,6119 | 0,7986 | 0,3631 |
| `v2` | Baseline | 17.318 / 4.338 | 0,7756 (0,0060) | 0,9832 (0,0109) | −0,0002 (0,0003) | 0,7913 | 1,0007 | −0,0001 |

### Comparación con la Fase 1

| Modelo | Partición | Sexta predictora | Parada temprana | CV RMSE | Prueba MAE | Prueba RMSE | Prueba R² |
|---|---|---|---|---|---|---|---|
| Fase 1 | Aleatoria | `es_franquicia` | `"auto"` | 0,7989 | 0,6059 | 0,7813 | 0,3745 |
| `v1` | Por grupos | `es_secuela` | `False` | 0,7946 | 0,6199 | 0,8007 | 0,3491 |

En prueba, `v1` parece peor que la Fase 1, pero **las dos cifras no se comparan directamente**, porque se evaluaron con películas distintas.

- `v1` se evalúa con sagas que el modelo no vio; la Fase 1 tenía 604 películas de prueba en una colección vista. Es una prueba más exigente y más cercana a una película nueva. En 10 semillas, partir por grupos cuesta 0,0071 de RMSE en promedio.
- La partición de la Fase 1 resultó favorable: su RMSE de 0,7813 quedó por debajo del promedio de 0,7921 en 10 semillas.
- En CV, `v1` queda con un RMSE ligeramente menor. La diferencia es pequeña frente a la desviación entre folds.
- `es_secuela` mejora el RMSE en 0,0029 en promedio de 10 semillas. El motivo del cambio no fue esa mejora, sino que la variable se conoce al estreno.

## Docker

La imagen `modelos-fase2:1.0` usa `python:3.12.10-slim` y solo trae el código y las dependencias: los datos y los modelos se montan desde tu equipo. Pesa 720 MB en disco y 153 MB comprimida.

**Dónde se verificó:** Windows 11 ARM64 con Docker Desktop (motor `linux/arm64`), en PowerShell y Git Bash. Los comandos completos, la comparación de portabilidad y la solución de problemas están en [docs/docker.md](docs/docker.md).

PowerShell:

```powershell
docker build -t modelos-fase2:1.0 .

$commit = git rev-parse HEAD
docker run --rm `
  -e "GIT_COMMIT=$commit" `
  -v "${PWD}/data:/app/data:ro" `
  -v "${PWD}/models:/app/models" `
  modelos-fase2:1.0 `
  python train.py --data data/movies_metadata.csv --version v-docker

docker run --rm `
  -v "${PWD}/models:/app/models:ro" `
  -v "${PWD}/data:/app/data:ro" `
  -v "${PWD}/outputs:/app/outputs" `
  modelos-fase2:1.0 `
  python predict.py --model models/v1 --input data/ejemplo_prediccion.csv --output outputs/predicciones_docker_v1.csv
```

Bash (`MSYS_NO_PATHCONV=1` es necesario en Git Bash):

```bash
export MSYS_NO_PATHCONV=1
docker build -t modelos-fase2:1.0 .

docker run --rm \
  -e GIT_COMMIT="$(git rev-parse HEAD)" \
  -v "$(pwd)/data:/app/data:ro" \
  -v "$(pwd)/models:/app/models" \
  modelos-fase2:1.0 \
  python train.py --data data/movies_metadata.csv --version v-docker

docker run --rm \
  -v "$(pwd)/models:/app/models:ro" \
  -v "$(pwd)/data:/app/data:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  modelos-fase2:1.0 \
  python predict.py --model models/v1 --input data/ejemplo_prediccion.csv --output outputs/predicciones_docker_v1.csv
```

`v1` se entrenó en Windows ARM64 y predice igual en el contenedor: diferencia máxima de 0,0 en las 12 filas del ejemplo.

## Pruebas

El comando es igual en PowerShell y en Bash. Debe ser `python -m pytest`, no `pytest`, para que `src` se pueda importar. No usa red ni el CSV completo.

```text
python -m pytest
```

| Archivo en `tests/` | Qué verifica |
|---|---|
| `test_entrenamiento.py` | Archivos de la versión, `metrics.json`, esquema de `metadata.json`, limpieza, filtros, `es_secuela` y partición sin grupos compartidos |
| `test_prediccion.py` | Carga y predicción iguales a las del modelo en memoria, orden de filas y columnas, nulos, ceros, categorías nuevas y columnas extra; predecir no cambia el modelo |
| `test_entrada_invalida.py` | Columnas ausentes, `es_secuela` y numéricas inválidas, coma final, CSV ilegible y `runtime` inválido: sin traceback y sin archivo de salida |
| `test_versionamiento.py` | Una versión nueva no altera la anterior, un identificador repetido falla, los modelos con `es_franquicia` siguen funcionando, y `v1` y `v2` predicen el ejemplo |

Cada prueba está descrita en la sección "Paso 5 – Pruebas" de [docs/decisiones.md](docs/decisiones.md).

## Limitaciones conocidas

- **Fecha de corte no verificada.** La descripción del dataset habla de películas hasta julio de 2017, según réplicas, pero no dice cuándo se descargaron los votos.
- **`es_secuela` vale 0 si la película anterior no está en el dataset.** Puede afectar a parte de las 207 películas de la población que son las únicas de su colección.
- **Las categorías distinguen mayúsculas.** Los errores de escritura en `genero_principal` y `original_language` no se detectan.
- **Dos casos de entrenamiento aún terminan con traceback:** `vote_average` infinito e `id` que no cabe en int64. Terminan con código 1, no crean la versión y son poco probables en este dataset.
- **`data/ejemplo_prediccion.csv` tiene valores ilustrativos,** no datos verificados de esas películas.
- **La portabilidad solo se comprobó en ARM64.** Se comparó Windows ARM64 con Linux ARM64, en 12 filas. No se comprobó en x86-64.

## Fuentes

- [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset), de Rounak Banik, en Kaggle.
- Réplicas de la descripción del dataset, consultadas porque la página de Kaggle no la entregó: [hyper.ai](https://hyper.ai/en/datasets/34654) y [Baselight](https://baselight.app/u/kaggle/dataset/rounakbanik_the_movies_dataset).

Uso de asistentes de IA: el equipo usó Claude (Anthropic), mediante Claude Code, como asistente para generar y revisar código, pruebas y documentación. Las decisiones de modelado, partición y corrección las tomó el equipo con base en los análisis documentados, y todos los resultados reportados se obtuvieron ejecutando el código.

Aparte de esa asistencia, los documentos del repositorio no registran código externo adaptado.

## Versión entregada

La entrega se identificará con la etiqueta de git `entrega-2`, sobre `main`. La etiqueta se crea al integrar este trabajo: si aún no aparece en `git tag`, la entrega no se ha cerrado.

## Trabajo del equipo

Los números de PR salen de los merge commits y de GitHub. Ningún PR del #1 al #10 tiene una aprobación formal de GitHub antes del merge.

| Paso | Contenido | Hizo | PR | Merge por | Revisión |
|---|---|---|---|---|---|
| 1 | Estructura, limpieza e interfaces | Alejandro | #5 | Juan Esteban | Sin aprobación registrada |
| 2 | Correcciones de la Fase 1 | Alejandro | #6 | Juan Esteban | Sin aprobación registrada |
| 3 | `train.py` y versionamiento | Juan Esteban | #7 | Miguel | Aprobado por Miguel en un comentario, publicado después del merge |
| 4 | `predict.py`, ejemplo, `v1` y `v2` | Juan Esteban | #8 | Miguel | Aprobado por Miguel en un comentario, publicado después del merge |
| 5 | Pruebas con pytest y correcciones | Miguel | #9 | Alejandro | Revisor designado: Alejandro; sin aprobación registrada |
| 6 | Docker | Miguel | #10 | Alejandro | Revisor designado: Alejandro; sin aprobación registrada |
| 7 | README | Alejandro | Este PR | Pendiente | Revisor designado: Juan Esteban |

Sobre la integración: el PR #9 (Paso 5) se integró por error en `main`, pero su contenido llegó a `develop` a través del PR #10, que partía de esa rama. Los commits del Paso 3 (PR #7) entraron a `develop` a través del PR #8. El PR final de `develop` a `main` dejará ambas ramas alineadas.

## Evidencia de ejecución

Salidas reales en Windows ARM64, con PowerShell, desde `fase-2/`.

`python -m pytest`:

```text
102 passed in 8.11s
```

`python train.py --data data\movies_metadata.csv --version v-readme` (versión temporal, ya borrada):

```text
Version v-readme guardada.
Particion group: 17335 filas de entrenamiento, 4321 de prueba, 0 grupos compartidos.
Sexta predictora: es_secuela.

             CV MAE  CV RMSE    CV R2      MAE     RMSE       R2
Modelo       0.6150   0.7946   0.3490   0.6199   0.8007   0.3491
Baseline     0.7776   0.9852  -0.0008   0.7854   0.9930  -0.0010
```

`python predict.py --model models\v1 --input data\ejemplo_prediccion.csv --output outputs\predicciones_v1.csv`:

```text
12 predicciones guardadas en outputs\predicciones_v1.csv
```

```text
title,budget,runtime,release_year,es_secuela,genero_principal,original_language,prediccion
Dune,165000000,155,2021,0,Science Fiction,en,6.758120437797601
Top Gun: Maverick,170000000,131,2022,1,Action,en,6.760580876200448
```

`docker run` de `predict.py` con `models/v1`, y comparación con la salida local:

```text
12 predicciones guardadas en outputs/predicciones_docker_v1.csv
allclose True diferencia maxima 0.0
```
