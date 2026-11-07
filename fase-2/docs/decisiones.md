# Decisiones de la Fase 2

Registro compartido del equipo. Cada integrante edita solo la sección de su paso.

## Paso 1 – Base de la Fase 1

Esta sección fija de qué se parte y qué interfaces comparte el equipo. Las rutas de los comandos parten de `fase-2/`, salvo que se indique otra cosa.

### Lo que dejó la Fase 1

"c.N" es el número de celda del notebook `fase-1/fase1_modelo_predictivo.ipynb`, contando desde 0. La tabla describe la Fase 1 tal como se entregó; los cambios están en el apartado siguiente.

| # | Dato | Valor | Fuente |
|---|---|---|---|
| 1 | Origen | The Movies Dataset (Rounak Banik, Kaggle), descarga manual o con la CLI de Kaggle | README raíz |
| 1 | Archivo | `movies_metadata.csv`, leído con `pd.read_csv(..., low_memory=False)`: 45.466 filas × 24 columnas | c.4 |
| 2 | Limpieza 1 | Elimina filas con `id` no numérico: −3 → 45.463 | c.9, c.11 |
| 2 | Limpieza 2 | Elimina filas con `vote_average` nulo (primera mitad de las líneas partidas): −3 → 45.460 | c.13, c.14 |
| 2 | Limpieza 3 | Convierte `id` a int64, y `budget` y `popularity` a numérico con `errors="raise"`; no quita filas | c.16 |
| 2 | Limpieza 4 | `drop_duplicates(subset="id", keep="first")`: −30 (59 filas, 29 películas) → 45.430 | c.20 |
| 2 | Limpieza 5 | `status == "Released"`: −445; los nulos también salen | c.51 |
| 2 | Limpieza 6 | `vote_count > 10`: −23.329 → 21.656. Va en la misma máscara que la regla 5, así que el orden entre ambas no importa | c.51 |
| 2 | Limpieza 7 y 8 | `budget` 0 → `NaN` y `runtime` 0 → `NaN`, después de filtrar; no quita filas | c.54 |
| 2 | Lo que no se hace | No recorta atípicos: conserva `runtime` > 300 y 112 películas con `budget` < 1.000 en la población final. No elimina filas por nulos en predictoras | c.36, c.39 |
| 3 | `budget` | Numérica (float), de `budget`, 0 → `NaN`; 65,60 % de faltantes | c.54, c.56 |
| 3 | `runtime` | Numérica (float), de `runtime`, 0 → `NaN`; 0,96 % de faltantes | c.54, c.56 |
| 3 | `release_year` | Numérica (float), año de `release_date` con `errors="coerce"`; 3 faltantes | c.54, c.56 |
| 3 | `es_franquicia` | Binaria (int), `belongs_to_collection.notna()`; sin faltantes | c.54 |
| 3 | `genero_principal` | Categórica, primer `name` de `genres` con `ast.literal_eval`; `sin_genero` si la lista está vacía (106 películas) | c.54 |
| 3 | `original_language` | Categórica, sin cambios; 1 faltante | c.54, c.56 |
| 4 | Numéricas | `SimpleImputer(strategy="median", add_indicator=True)` → `StandardScaler()`. Medianas: 12.000.000, 98 y 2004. El escalador también escala los 3 indicadores | c.63, c.66 |
| 4 | Binaria | `passthrough`, sin imputación | c.63 |
| 4 | Categóricas | `SimpleImputer(strategy="most_frequent")` (modas `Drama` y `en`) → `OneHotEncoder(min_frequency=0.01, handle_unknown="infrequent_if_exist", sparse_output=False)` | c.63 |
| 4 | Resultado | `remainder="drop"`; 32 columnas: 3 numéricas, 3 indicadores, 1 binaria, 15 de género y 10 de idioma. Ajustado solo con train | c.65–c.68 |
| 5 | Partición | Hold-out aleatorio con `train_test_split`, `test_size=0.2`, `random_state=42`; 17.324 / 4.332 | c.61 |
| 5 | Estratificación y grupos | Ninguna de las dos. Hay 469 colecciones en ambos lados (1.280 en train, 565 en prueba) | c.61 |
| 5 | CV | `KFold(n_splits=5, shuffle=True, random_state=42)`, solo sobre train | c.72 |
| 6 | Comparados | `DummyRegressor(strategy="mean")`, `Ridge(alpha=1.0)`, `HistGradientBoostingRegressor(random_state=42)` | c.70 |
| 6 | Elegido | HistGradientBoosting, por menor RMSE en CV; sin búsqueda de hiperparámetros y sin usar prueba | c.73 |
| 6 | Hiperparámetros efectivos | `learning_rate=0.1`, `max_iter=100`, `max_leaf_nodes=31`, `min_samples_leaf=20`, `l2_regularization=0`, `max_bins=255`, `early_stopping="auto"`, `validation_fraction=0.1`, `n_iter_no_change=10`, `tol=1e-7`. Usó las 100 iteraciones | `.joblib` |
| 7 | CV (MAE / RMSE / R²) | Baseline 0,7771 / 0,9865 / −0,0002 · Ridge 0,6631 / 0,8592 / 0,2412 · HGB 0,6170 / 0,7989 / 0,3440; desviación del RMSE de HGB entre folds 0,0072 | c.72 |
| 7 | Prueba (MAE / RMSE / R²) | Baseline 0,7823 / 0,9880 / −0,0004 · Ridge 0,6578 / 0,8499 / 0,2598 · HGB 0,6059 / 0,7813 / 0,3745 | c.75, JSON |
| 8 | Versiones | Python 3.12.10, scikit-learn 1.9.1, pandas 3.0.6, numpy 2.5.3, joblib 1.6.0, en Windows ARM64 | JSON |
| 8 | Solo en el lock | scipy 1.18.1, pytest 9.1.1 y el resto; el `requirements.txt` de la raíz no fija versiones | `requirements*.txt` |
| 9 | Columnas de entrada | Las 6 predictoras **ya derivadas**, no las columnas crudas. Reordena por nombre, ignora columnas extra y falla si falta una. Una categoría nueva cae en el grupo infrecuente | README, `.joblib` |

Datos locales que la Fase 1 no registró: `movies_metadata.csv` pesa 34.445.126 bytes y su SHA-256 es `37ec322786b136a24604564e55160be75f8937546f11cb1a990076971fa895fd`. Con ese archivo se reproduce todo lo anterior. No se conoce la versión de Kaggle ni la fecha de descarga.

### Decisiones del Paso 1

| # | Decisión | ¿Cambia la Fase 1? | Efecto comprobado |
|---|---|---|---|
| 1 | `status == "Released"` y `vote_count > 10` se mantienen como filtros fijos, en `src/config.py` y en `metadata.json` | **No.** Solo se hacen explícitos | Sin el filtro de `status` entrarían 88 filas más |
| 2 | La conversión de 0 a `NaN` en `budget` y `runtime` pasa a ser la primera etapa del Pipeline, con `FunctionTransformer` y `feature_names_out="one-to-one"`. También se conserva en `derive_features`, porque es idempotente | **Sí, cambia.** Antes solo estaba fuera del Pipeline | `runtime=0` y `runtime` nulo dan la misma predicción, y lo mismo con `budget`. Antes eran 7,17 frente a 5,72 y 6,06 frente a 6,02 en una misma película de ejemplo |
| 3 | Admiten nulos `budget`, `runtime`, `release_year`, `genero_principal` y `original_language`. `es_franquicia` no los admite y solo acepta 0 o 1 | **Sí, cambia.** La Fase 1 no lo definía | Queda en `src/config.py`. El Pipeline no lo hace cumplir: `predict.py` debe validarlo en el Paso 4 |
| 3 | `genero_principal` se imputa con `SimpleImputer(strategy="constant", fill_value="sin_genero")`; `original_language` sigue con `most_frequent` | **Sí, cambia.** Antes un género nulo se volvía `Drama` | No altera las métricas: en los datos no hay géneros nulos. Un género nulo ahora predice igual que `sin_genero` |
| 4 | `fase-2/requirements.txt` fija pandas 3.0.6, numpy 2.5.3, scikit-learn 1.9.1, joblib 1.6.0, scipy 1.18.1 y pytest 9.1.1, para Python 3.12.10 | **No cambia el modelo.** Es un archivo nuevo | Todo está satisfecho en el entorno local |

Ajustes de implementación que se derivan de lo anterior:

- **Etapa inicial del Pipeline:** `prepare_model_input` selecciona las 6 predictoras en el orden del contrato y luego convierte los ceros. Con `one-to-one`, `FunctionTransformer` renombra por posición una salida en otro orden. Con la versión inicial, intercambiar `budget` y `runtime` daba predicciones erróneas sin ningún error, y una columna extra o ausente daba `Length mismatch`. Ahora el orden no afecta el resultado, las columnas extra se ignoran y una columna ausente lanza `MissingColumnsError`.
- **Categóricas:** el transformador `categoricas` se separó en `genero` e `idioma`, porque usan imputadores distintos. Cambian los prefijos de los nombres de salida, pero no el orden ni los valores.
- **Baseline:** `build_baseline()` es un Pipeline con el mismo preprocesamiento y `DummyRegressor(strategy="mean")`, igual que en la Fase 1.
- **`popularity`:** no es columna requerida, porque ninguna predictora la usa. Si está en el CSV, `clean_data` la convierte igual que la Fase 1.
- **Aserciones del notebook:** las que dependían del CSV real, como la de `adult`, no pasaron a `clean_data`. No cambian las filas resultantes.

### Verificación contra la Fase 1

Se armó el Pipeline con `src/`, con el CSV de referencia y la partición de la Fase 1.

| Comprobación | Fase 1 | `fase-2/src` | ¿Coincide? |
|---|---|---|---|
| Filas: crudas / limpias / población | 45.466 / 45.430 / 21.656 | 45.466 / 45.430 / 21.656 | Sí |
| Partición: train / prueba | 17.324 / 4.332 | 17.324 / 4.332 | Sí |
| HGB en prueba: MAE / RMSE / R² | 0,6059 / 0,7813 / 0,3745 | 0,6059 / 0,7813 / 0,3745 | Sí |
| Baseline en prueba: MAE / RMSE / R² | 0,7823 / 0,9880 / −0,0004 | 0,7823 / 0,9880 / −0,0004 | Sí |
| HGB en CV: MAE / RMSE / R² | 0,6170 / 0,7989 / 0,3440 | 0,6170 / 0,7989 / 0,3440 | Sí |
| Baseline en CV: MAE / RMSE / R² | 0,7771 / 0,9865 / −0,0002 | 0,7771 / 0,9865 / −0,0002 | Sí |
| Predicciones sobre prueba frente al `.joblib` | — | `np.allclose` verdadero; diferencia máxima 0,0 | Sí |
| Hiperparámetros del HGB | — | `get_params()` idéntico | Sí |

### Riesgos

- **`early_stopping="auto"` depende del tamaño de los datos.** Se activa solo si el conjunto de ajuste tiene más de 10.000 filas. En la Fase 1 estuvo activa: reservó cerca del 10 % de train para validación interna, aunque llegó a las 100 iteraciones. Un `--min-votes` más alto o el CSV sintético del Paso 5 pueden desactivarla y cambiar el entrenamiento.
- **El número de columnas de los indicadores depende de la partición.** `add_indicator=True` crea indicadores solo para las columnas con faltantes en train. `release_year` tiene 3 nulos: con otra semilla o estrategia podría no tener ninguno en train, y serían 31 columnas en vez de 32. Un nulo al predecir se imputaría igual, pero sin indicador.
- **El `.joblib` depende de `src`.** Guarda una referencia a `src.features.prepare_model_input`, así que para cargarlo `src` debe ser importable y esa función no se puede mover ni renombrar sin invalidar las versiones guardadas.
- **La etapa inicial debe seguir devolviendo el orden del contrato.** Si se simplifica, vuelve el error silencioso descrito arriba.
- **Dependencias indirectas:** `threadpoolctl` no está fijada, porque no hace parte de la decisión 4. La instala pip como dependencia de scikit-learn.
- **Plataforma:** los resultados se comprobaron en Windows ARM64. No se ha comprobado que Linux en Docker dé exactamente los mismos números.

### Diferencias menores

- **Métricas del profesor y locales:** el profesor obtuvo MAE 0,6060, RMSE 0,7815 y R² 0,3741 (plan de la Fase 2). En local dan 0,6059, 0,7813 y 0,3745, igual que el notebook y el `.joblib`. El repositorio no explica la diferencia; la plataforma es una hipótesis sin comprobar.
- **R² del baseline:** el README de la Fase 1 lo redondea a 0,000. Los valores reales son −0,0002 en CV y −0,0004 en prueba.

### Interfaces compartidas

Cambiar cualquiera de estas interfaces afecta a los demás pasos: se avisa en el grupo antes de hacerlo.

**`src/config.py`**

| Nombre | Contenido |
|---|---|
| `SEED`, `TEST_SIZE`, `MIN_VOTES` | 42, 0.2 y 10 |
| `TARGET`, `ID_COLUMN`, `RAW_COLUMNS` | Objetivo, identificador y columnas crudas requeridas |
| `STATUS_RELEASED`, `ZERO_AS_MISSING_COLUMNS` | `"Released"` y `("budget", "runtime")` |
| `FEATURES` | Tupla de `Feature(name, kind, nullable, valid_values)` |
| `FEATURE_NAMES`, `NUMERIC_FEATURES`, `BINARY_FEATURES`, `CATEGORICAL_FEATURES` | Nombres de las predictoras, en el orden del contrato |
| `input_contract() -> list[dict]` | Contrato de entrada para `metadata.json` |

**`src/data.py`**

```python
class DataError(Exception)
class MissingColumnsError(DataError)  # .missing tiene las columnas faltantes
validate_columns(df, required=config.RAW_COLUMNS) -> None
read_raw_csv(path) -> pd.DataFrame
clean_data(df) -> pd.DataFrame                       # reglas 1 a 4
apply_filters(df, min_votes=config.MIN_VOTES) -> pd.DataFrame  # reglas 5 y 6
describe_dataset(path, rows_raw, rows_clean, rows_filtered, min_votes=config.MIN_VOTES) -> dict
```

**`src/features.py`**

```python
zeros_to_nan(X) -> pd.DataFrame
prepare_model_input(X) -> pd.DataFrame   # primera etapa del Pipeline
first_genre(genres_text) -> str
derive_features(df) -> pd.DataFrame      # agrega las predictoras y conserva las demás columnas
```

**`src/pipeline.py`**

```python
HGB_PARAMS: dict
build_pipeline(seed=config.SEED) -> Pipeline  # pasos: ceros_a_nan, preprocesamiento, modelo
build_baseline() -> Pipeline
```

**`src/versioning.py`**

```python
class VersionError(Exception)
class VersionExistsError(VersionError)
class VersionNotFoundError(VersionError)
class VersionLoadError(VersionError)
get_git_commit() -> str
build_metadata(version, pipeline, seed, data_info, partition, target=config.TARGET) -> dict
save_version(pipeline, metrics, metadata, output_dir, version) -> Path
load_version(path) -> tuple[Pipeline, dict]
```

- `save_version` crea `<output_dir>/<version>/` con `modelo.joblib`, `metrics.json` y `metadata.json`. Falla si la versión ya existe, si el identificador es inválido o si faltan claves en `metadata`. Escribe en una carpeta temporal y la renombra al final.
- `load_version` acepta la carpeta de la versión o la ruta a su `modelo.joblib`. Solo se deben cargar modelos de confianza, porque joblib usa pickle.

Uso esperado:

```python
crudo = data.read_raw_csv(ruta_csv)
limpio = data.clean_data(crudo)
filtrado = data.apply_filters(limpio, min_votes)
df = features.derive_features(filtrado)
# ... partir los datos, ajustar el Pipeline y calcular metrics ...
info = data.describe_dataset(ruta_csv, len(crudo), len(limpio), len(filtrado), min_votes)
particion = {"estrategia": "random", "test_size": 0.2, "n_train": 17324, "n_test": 4332}
metadata = versioning.build_metadata(version, modelo, seed, info, particion)
versioning.save_version(modelo, metrics, metadata, "models", version)
```

### Esquema de metadata.json

| Clave | Tipo | Contenido |
|---|---|---|
| `version` | texto | Identificador de la versión |
| `fecha` | texto | Fecha y hora UTC en ISO 8601 |
| `tipo_problema` | texto | `regresion` |
| `objetivo` | texto | `vote_average` |
| `algoritmo` | texto | Clase del regresor |
| `contrato_entrada` | lista | Un objeto por predictora: `nombre`, `tipo`, `nulos_permitidos`, `valores_validos` (`[0, 1]` en `es_franquicia`; `null` en las demás) |
| `hiperparametros` | objeto | `get_params()` del regresor |
| `semilla` | número | Semilla usada |
| `datos` | objeto | `fuente`, `url`, `archivo`, `tamano_bytes`, `sha256`, `filas_antes_limpieza`, `filas_despues_limpieza`, `filas_tras_filtros` y `filtros` (`status`, `vote_count_minimo_exclusivo`) |
| `horizonte_objetivo` | texto | Por ahora `no verificado` |
| `particion` | objeto | `estrategia`, `test_size`, `n_train`, `n_test` |
| `metrica_principal` | texto | `RMSE`, la métrica con la que la Fase 1 eligió el modelo |
| `entorno` | objeto | `python`, `librerias` (scikit-learn, pandas, numpy, joblib, scipy) y `requirements` |
| `git_commit` | texto | Commit de git; si no hay, `GIT_COMMIT`; si tampoco, `no disponible` |

`filas_despues_limpieza` son las filas tras las reglas 1 a 4, y `filas_tras_filtros`, las que quedan tras las reglas 5 y 6. `metrics.json` no tiene un esquema fijo todavía: lo define el Paso 3.

### Para el siguiente relevo

**Qué quedó listo**

- La estructura de `fase-2/`, con los módulos de `src/` y `train.py` y `predict.py` solo con `--help`. Si se ejecutan con sus argumentos, avisan que están pendientes y terminan con código 1.
- Limpieza, predictoras, Pipeline, baseline y versionamiento, comprobados contra la Fase 1.
- `.gitignore` de la raíz: excluye el CSV y `outputs/*` de `fase-2/`, y permite versionar `fase-2/models/`.

**Cómo verificarlo**

Instala las dependencias y copia `movies_metadata.csv` en `fase-2/data/` ([instrucciones](../data/README.md)).

PowerShell:

```powershell
cd fase-2
python -m pip install -r requirements.txt
python train.py --help
python predict.py --help
python
```

Bash:

```bash
cd fase-2
python -m pip install -r requirements.txt
python train.py --help
python predict.py --help
python
```

Dentro de Python, pega esto. Debe imprimir `True`. Fija `es_franquicia` porque desde el Paso 2 el default es `es_secuela`:

```python
import joblib, numpy as np
from sklearn.model_selection import train_test_split
from src import config, data, features, pipeline
df = features.derive_features(data.apply_filters(data.clean_data(data.read_raw_csv("data/movies_metadata.csv"))))
X, y = df[list(config.get_feature_names("es_franquicia"))], df[config.TARGET]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=config.TEST_SIZE, random_state=config.SEED)
modelo = pipeline.build_pipeline(config.SEED, "es_franquicia").fit(X_tr, y_tr)
fase1 = joblib.load("../fase-1/models/modelo_vote_average.joblib")
print(np.allclose(modelo.predict(X_te), fase1.predict(X_te)))
```

**Qué falta**

- **Paso 2, lo siguiente:** análisis de correcciones, `src/splitting.py` y `es_secuela`. Ninguno de los dos existe todavía.
- **Paso 3:** `train.py` y el esquema de `metrics.json`. Los argumentos `--split-strategy` y `--franchise-feature` no están en el `--help` actual, porque dependen del Paso 2.
- **Paso 4:** `predict.py`, incluida la validación de que `es_franquicia` no tenga nulos y solo tenga 0 o 1.
- **Horizonte del objetivo:** sigue como `no verificado`.

## Paso 2 – Correcciones

El análisis completo, con sus gráficas, está en `notebooks/analisis_correcciones.ipynb`. Esta sección trae los resultados y lo que cambió en `src/`. Lo que eligió el equipo está en "Decisiones del equipo".

Los análisis que miran `vote_average` usan solo entrenamiento: el de la partición `random` en C1 y el de la partición `group` en C3. Los conteos de colecciones, fechas y filtros usan todo el dataset, porque no miran el objetivo.

### C1. EDA complementario

- **Redundancia:** no hay. La mayor correlación entre `budget`, `runtime` y `release_year` es 0,323 (Spearman, `budget` y `runtime`).
- **Relación con `vote_average`:** `runtime` tiene Spearman 0,229, `release_year` −0,163 y `budget` −0,046. El resultado casi no cambia con el train por grupos.
- **Categorías:** `Documentary` tiene la mayor mediana (7,1) y `Horror` la menor (5,5). `en` tiene la mediana más baja por idioma (6,1); los demás grupos tienen 6,5 o más.
- **`budget` nulo:** faltar casi no cambia la calificación promedio (d de Cohen −0,025), pero se relaciona con la época y con el tipo de película. Hasta 1999, las películas con presupuesto reportado están mejor calificadas (+0,17 y +0,13); desde 2000 la diferencia casi desaparece.
- La importancia por permutación de la Fase 1 no reemplaza este análisis: mide de qué depende el modelo ya ajustado, no cómo se relacionan los datos.

### C2. Sagas compartidas

| Partición | Filas train / prueba | Colecciones en ambos lados | Películas de prueba en colección vista |
|---|---|---|---|
| `random` | 17.324 / 4.332 | **469** | 604 |
| `group` | 17.335 / 4.321 (19,95 %) | **0** | 0 |

Semilla 42, MAE / RMSE / R²:

| Modelo | Partición | CV | Prueba | Desviación del RMSE en CV |
|---|---|---|---|---|
| HGB | `random` | 0,6170 / 0,7989 / 0,3440 | 0,6059 / 0,7813 / 0,3745 | 0,0072 |
| HGB | `group` | 0,6187 / 0,7981 / 0,3433 | 0,6205 / 0,8028 / 0,3457 | 0,0208 |
| Baseline | `random` | 0,7771 / 0,9865 / −0,0002 | 0,7823 / 0,9880 / −0,0004 | 0,0058 |
| Baseline | `group` | 0,7776 / 0,9852 / −0,0008 | 0,7854 / 0,9930 / −0,0010 | 0,0176 |

- La partición por grupos no empeora la CV. En prueba, el RMSE sube 0,0215 con la semilla 42, pero en promedio de 10 semillas sube 0,0071 (desviación de 0,0068).
- HGB supera al baseline con las dos estrategias: reduce el RMSE un 20,9 % con `random` y un 19,2 % con `group`.
- La mayor desviación con grupos viene de un fold más difícil también para el baseline; no es un error del código.

**Sobre C4:** la cercanía entre CV y prueba no descarta un efecto de la partición. La prueba de la Fase 1 (RMSE 0,7813) quedó por debajo de la media de `random` en 10 semillas (0,7921, desviación de 0,0079). Es evidencia favorable, no una garantía.

### C3. `es_franquicia` al estreno

Dataset limpio:

| Medida | Valor |
|---|---|
| Películas con colección | 4.487 |
| Primeras de su colección por `release_date` | 1.704 (38,0 %), 15 empatadas en la primera fecha |
| Colecciones | 1.695 |
| Colecciones con una sola película | 390 (23,0 %) |
| `es_secuela = 1` | 2.781 |

`vote_average` en el train por grupos:

| Grupo | n | Media | Mediana |
|---|---|---|---|
| Sin colección | 14.566 | 6,212 | 6,3 |
| Primera de su colección | 1.092 | 6,318 | 6,4 |
| Secuela | 1.677 | 5,830 | 5,9 |

Partición por grupos, semilla 42, MAE / RMSE / R²:

| Sexta predictora | CV | Prueba | Iteraciones |
|---|---|---|---|
| `es_franquicia` | 0,6187 / 0,7981 / 0,3433 | 0,6205 / 0,8028 / 0,3457 | 92 |
| `es_secuela` | 0,6153 / 0,7949 / 0,3486 | 0,6187 / 0,8007 / 0,3491 | 64 |

- `es_franquicia` junta dos comportamientos opuestos: el 39,4 % de sus unos en train son primeras películas, que tienen la mejor media, y el resto son secuelas, que tienen la peor.
- Hay colecciones que no pudieron existir como saga al estreno. *Blade Runner* (1982) figura en una colección sin que el dataset tenga otra película de ella.
- `es_secuela` gana en las 10 semillas, por 0,0029 de RMSE en promedio (desviación de 0,0015). Es una mejora pequeña, pero consistente.
- **Limitación de `es_secuela`:** vale 0 si la película anterior no está en el dataset. Eso puede afectar a parte de las 207 películas de la población que son las únicas de su colección.

**Definición de `es_secuela`:** vale 1 si en su colección existe otra película con `release_date` estrictamente anterior, y 0 si no tiene colección o es la primera.

- Se calcula sobre el dataset limpio, antes de los filtros. Esto importa: 30 películas de la población tienen una precuela que los filtros quitaron.
- **Empates:** si varias comparten la primera fecha, todas valen 0.
- **Fechas nulas o inválidas:** la película vale 0, y esas fechas no cuentan como anteriores para las demás.

### C5. Horizonte del objetivo

| Paso | Quita | Quedan |
|---|---|---|
| CSV crudo | — | 45.466 |
| Limpieza (reglas 1 a 4) | 36 | 45.430 |
| `status == "Released"` | 445 | 44.985 |
| `vote_count > 10` | 23.329 | 21.656 |

Si `vote_count > 10` se aplica primero, quita 23.686 filas y `status` quita después 88.

- **Fecha de corte de `vote_average`: no verificada.** La descripción del dataset dice que incluye películas "released on or before July 2017". Se consultó en réplicas ([hyper.ai](https://hyper.ai/en/datasets/34654) y [Baselight](https://baselight.app/u/kaggle/dataset/rounakbanik_the_movies_dataset)), porque la página de Kaggle no entregó su descripción. Esa frase delimita qué películas entran, no cuándo se descargaron los votos.
- **Máximo de `release_date`:** en la población es 2017-10-27 (*Call Me by Your Name*). Quedan 12 películas posteriores a julio de 2017, y algunas ya tienen muchos votos (*The Dark Tower*, 688). Eso sugiere una descarga posterior a julio de 2017, sin fijar una fecha.
- **Fechas de hasta 2020:** no sobreviven. Las 6 posteriores a 2017 no están estrenadas. *Avatar 2* (58 votos) y *Bad Boys for Life* (12 votos) superan el filtro de votos, así que las quita el de `status`.
- **Qué implica:** el horizonte no es igual para todas las películas. Una de 1995 acumuló votos durante más de 20 años y una de 2017, semanas o meses. `TARGET_HORIZON` sigue en `no verificado`.

### Opciones que se presentaron al equipo

**(a) Partición**

| Opción | A favor | En contra |
|---|---|---|
| `group` | Evalúa con sagas no vistas; responde a C2 | Prueba distinta a la de la Fase 1; +0,0071 de RMSE en promedio |
| `random` | Comparación directa con la Fase 1 | Deja 469 colecciones en ambos lados; evalúa solo sagas conocidas |

**(b) Sexta predictora**

| Opción | A favor | En contra |
|---|---|---|
| `es_secuela` | Se conoce al estreno; mantiene 6 predictoras; mejora en 10 de 10 semillas | Cambia el contrato; vale 0 si falta la película anterior en el dataset |
| `es_franquicia` | Mantiene el modelo y el contrato de la Fase 1 | Para el 38 % de sus casos, la información podría no existir al estreno |

### Cambios en `src/`

Con `random` y `es_franquicia` no cambia ningún resultado: selecciona las mismas filas que la Fase 1 y las predicciones sobre prueba son idénticas a las del `.joblib`. Los defaults ahora son `group` y `es_secuela`. Estas firmas actualizan las del Paso 1:

```python
# src/config.py
CV_FOLDS = 5
SPLIT_STRATEGY = "group"
SIXTH_FEATURE_OPTIONS = ("es_franquicia", "es_secuela")
SIXTH_FEATURE = "es_secuela"
LEGACY_SIXTH_FEATURE = "es_franquicia"
get_features(sixth_feature=SIXTH_FEATURE) -> tuple[Feature, ...]
get_feature_names(sixth_feature=SIXTH_FEATURE) -> tuple[str, ...]
input_contract(sixth_feature=SIXTH_FEATURE) -> list[dict]

# src/features.py
prepare_model_input(X, sixth_feature=config.LEGACY_SIXTH_FEATURE) -> pd.DataFrame
collection_ids(df) -> pd.Series
add_sequel_feature(df) -> pd.DataFrame   # recibe el dataset limpio, antes de los filtros

# src/pipeline.py
build_pipeline(seed=config.SEED, sixth_feature=config.SIXTH_FEATURE) -> Pipeline
build_baseline(sixth_feature=config.SIXTH_FEATURE) -> Pipeline

# src/splitting.py (nuevo)
SPLIT_STRATEGIES = ("random", "group")
make_groups(df) -> pd.Series
split_data(df, strategy=config.SPLIT_STRATEGY, test_size=config.TEST_SIZE, seed=config.SEED) -> tuple[pd.DataFrame, pd.DataFrame]
make_cv(strategy=config.SPLIT_STRATEGY, seed=config.SEED) -> KFold | GroupKFold
cross_validate_model(estimator, train_df, strategy=config.SPLIT_STRATEGY, feature_names=config.FEATURE_NAMES, seed=config.SEED, target=config.TARGET) -> dict
```

- **La sexta predictora viaja con el artefacto.** `prepare_model_input` la recibe por `kw_args`, y `build_metadata` la lee del Pipeline. Así, cambiar `SIXTH_FEATURE` no rompe las versiones ya guardadas. Si `prepare_model_input` leyera la opción de `config` al predecir, un modelo entrenado con la otra variable fallaría.
- **`LEGACY_SIXTH_FEATURE` no se cambia.** Los modelos guardados con el código del Paso 1 no llevan su opción, así que usan ese valor por defecto, que debe seguir siendo `es_franquicia`. Con `SIXTH_FEATURE` como valor por defecto, esos modelos fallaban con `MissingColumnsError`. Se comprobó con un modelo guardado por el código del Paso 1 y otro por el del Paso 2: los dos, cargados con los nuevos defaults, dan predicciones idénticas a las originales.
- **Regla de `es_secuela`:** comparte con `es_franquicia` el contrato binario: solo 0 o 1, sin nulos.
- **`es_secuela` debe calcularse antes de los filtros.** El flujo es `clean_data` → `add_sequel_feature` → `apply_filters` → `derive_features`.
- **`make_groups`:** los grupos son `coleccion_<id>` y `pelicula_<id>`.

### Riesgos para los siguientes pasos

- **La parada temprana no respeta grupos.** Su validación interna es aleatoria, así que dentro de train puede ver una saga en ambos lados. Tampoco es estable: las iteraciones variaron entre 51 y 100 con las semillas probadas. Las 100 de la semilla 42 con `random` no eran la regla. Esto no afecta a la prueba, pero sí puede influir en la comparación entre `es_franquicia` y `es_secuela`.
- **Con `group`, `test_size` se aplica a los grupos, no a las filas.** Hay que reportar los tamaños reales.
- **`GroupKFold(5)` no baraja.** Por eso sus folds no cambian con la semilla.

### Dependencias

La aplicación usa solo `requirements.txt`. El notebook necesita además `requirements-notebook.txt`, con matplotlib, Jupyter, ipykernel y nbconvert. Se separaron para que Docker y las pruebas no instalen lo que la aplicación no usa.

### Para ejecutar el notebook

El notebook busca el CSV en `fase-2/data/` y después en `data/`. Los comandos se ejecutan desde `fase-2/` y tardan unos minutos.

PowerShell:

```powershell
python -m pip install -r requirements.txt -r requirements-notebook.txt
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks\analisis_correcciones.ipynb
```

Bash:

```bash
python -m pip install -r requirements.txt -r requirements-notebook.txt
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/analisis_correcciones.ipynb
```

### Para el siguiente relevo

**Qué quedó listo**

- `src/splitting.py`, `es_secuela` y la opción de sexta predictora, con los defaults que eligió el equipo: `group` y `es_secuela`.
- `notebooks/analisis_correcciones.ipynb`, ejecutado, y `docs/correcciones_fase1.md`, con cada corrección y su evidencia.

**Cómo verificarlo**

Desde `fase-2/`, con el CSV en `data/`, abre `python` en PowerShell o Bash y pega esto. Debe mostrar `RMSE` de 0,7949 en CV y 0,8007 en prueba:

```python
from sklearn.metrics import root_mean_squared_error
from src import config, data, features, pipeline, splitting
limpio = features.add_sequel_feature(data.clean_data(data.read_raw_csv("data/movies_metadata.csv")))
df = features.derive_features(data.apply_filters(limpio))
train, test = splitting.split_data(df)
columnas = list(config.FEATURE_NAMES)
print(splitting.cross_validate_model(pipeline.build_pipeline(), train))
modelo = pipeline.build_pipeline().fit(train[columnas], train[config.TARGET])
print(root_mean_squared_error(test[config.TARGET], modelo.predict(test[columnas])))
```

**Qué falta: Paso 3, `train.py`**

- Seguir el flujo `read_raw_csv` → `clean_data` → `add_sequel_feature` → `apply_filters` → `derive_features`. Si se omite `add_sequel_feature`, el Pipeline falla con `MissingColumnsError`.
- Partir con `splitting.split_data` y hacer la CV con `splitting.cross_validate_model`, usando los defaults nuevos. La CV debe hacerse solo con train, con `GroupKFold(5)`.
- Agregar `--split-strategy` y `--franchise-feature`, con sus defaults tomados de `SPLIT_STRATEGY` y `SIXTH_FEATURE`.
- Medir la decisión (c) y reportar la comparación con las métricas de "Decisiones del equipo".
- Reportar los tamaños reales de la partición, porque `test_size` se aplica a los grupos.

**Después del Paso 3**

- Paso 4: `predict.py` debe validar `es_secuela` (solo 0 o 1, sin nulos), y el CSV de ejemplo debe usar esa columna.

## Decisiones del equipo

### Métricas con las decisiones (a) y (b)

Son los resultados con los defaults de `src/config.py`, semilla 42 y `early_stopping="auto"`. MAE / RMSE / R²:

| Modelo | CV (`GroupKFold(5)`) | Prueba |
|---|---|---|
| HGB | 0,6153 / 0,7949 / 0,3486 | 0,6187 / 0,8007 / 0,3491 |
| Baseline | 0,7776 / 0,9852 / −0,0008 | 0,7854 / 0,9930 / −0,0010 |

Filas: 17.335 en entrenamiento y 4.321 en prueba, sin colecciones compartidas.

### (a) Partición por grupos

**Decisión:** `group`, con `GroupShuffleSplit` para prueba y `GroupKFold(5)` para CV.

**Justificación:**

- La partición aleatoria deja 469 colecciones en entrenamiento y en prueba; por grupos deja 0.
- El costo es bajo. En CV, el RMSE casi no cambia (0,7989 frente a 0,7981, con `es_franquicia`). En prueba sube 0,0215 con la semilla 42, pero 0,0071 en promedio de 10 semillas (desviación de 0,0068).

**Limitaciones:**

- La prueba tiene películas distintas a las de la Fase 1, así que sus métricas no se comparan directamente.
- `test_size` se aplica a los grupos: la prueba quedó con el 19,95 % de las filas.
- `GroupKFold(5)` no baraja y deja un fold más difícil: la desviación del RMSE es 0,0216, frente a 0,0072 con `KFold` en la Fase 1.

### (b) `es_secuela` como sexta predictora

**Decisión:** `es_secuela` reemplaza a `es_franquicia`. El contrato sigue teniendo 6 predictoras.

**Justificación:**

- `es_secuela` se conoce al estreno. En cambio, 1.704 de las 4.487 películas con colección (38,0 %) son la primera de su saga, y para ellas la colección podría no existir al estrenarse.
- `es_franquicia` mezcla dos grupos opuestos: las primeras películas tienen media 6,318 y las secuelas 5,830; las películas sin colección, 6,212.
- Con partición por grupos, el RMSE baja de 0,7981 a 0,7949 en CV y de 0,8028 a 0,8007 en prueba. Gana en las 10 semillas probadas, por 0,0029 en promedio (desviación de 0,0015).

**Limitaciones:**

- **`es_secuela` vale 0 si falta la película anterior en el dataset.** Puede afectar a parte de las 207 películas de la población que son las únicas de su colección. También vale 0 si la fecha es nula o si la película empata en la primera fecha.
- La mejora es pequeña y menor que la desviación entre folds (0,02), aunque consistente.
- La comparación incluye la parada temprana: 92 iteraciones con `es_franquicia` y 64 con `es_secuela`.

### (c) Evaluar HGB sin parada temprana

**Decisión pendiente de medir en el Paso 3:** evaluar HGB con `early_stopping=False` y `max_iter=100`. Todavía no se cambia en `pipeline.py`.

**Justificación:** la validación interna de la parada temprana es aleatoria y no respeta grupos. Además, la Fase 1 usó 100 iteraciones.

**Qué hay que tener en cuenta al medirla:**

- Las 100 iteraciones de la Fase 1 se dieron con `early_stopping="auto"` activo y con la semilla 42. Con otras semillas varió entre 51 y 100, y el modelo con los defaults actuales se detiene en 64.
- `early_stopping=False` no reproduce el entrenamiento de la Fase 1: entrena con todo train, no con cerca del 90 %, y dejaría de ser igual al `.joblib`.
- Las métricas de esta sección cambiarán si se aplica la decisión. El Paso 3 debe reportar las dos variantes con la misma partición.

### Limitación general: fecha de corte

La fecha de corte de `vote_average` queda **no verificada**. La descripción del dataset habla de películas hasta julio de 2017, según réplicas, pero no dice cuándo se descargaron los votos, y 12 películas de la población tienen fecha posterior. El objetivo es el promedio acumulado hasta esa fecha desconocida, con un horizonte distinto para cada película. El detalle está en la sección C5.

## Paso 3 – Entrenamiento

## Paso 4 – Predicción

## Paso 5 – Pruebas

## Paso 6 – Docker
