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

Dentro de Python, pega esto. Debe imprimir `True`:

```python
import joblib, numpy as np
from sklearn.model_selection import train_test_split
from src import config, data, features, pipeline
df = features.derive_features(data.apply_filters(data.clean_data(data.read_raw_csv("data/movies_metadata.csv"))))
X, y = df[list(config.FEATURE_NAMES)], df[config.TARGET]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=config.TEST_SIZE, random_state=config.SEED)
modelo = pipeline.build_pipeline(config.SEED).fit(X_tr, y_tr)
fase1 = joblib.load("../fase-1/models/modelo_vote_average.joblib")
print(np.allclose(modelo.predict(X_te), fase1.predict(X_te)))
```

**Qué falta**

- **Paso 2, lo siguiente:** análisis de correcciones, `src/splitting.py` y `es_secuela`. Ninguno de los dos existe todavía.
- **Paso 3:** `train.py` y el esquema de `metrics.json`. Los argumentos `--split-strategy` y `--franchise-feature` no están en el `--help` actual, porque dependen del Paso 2.
- **Paso 4:** `predict.py`, incluida la validación de que `es_franquicia` no tenga nulos y solo tenga 0 o 1.
- **Horizonte del objetivo:** sigue como `no verificado`.

## Paso 2 – Correcciones

## Decisiones del equipo

## Paso 3 – Entrenamiento

## Paso 4 – Predicción

## Paso 5 – Pruebas

## Paso 6 – Docker
