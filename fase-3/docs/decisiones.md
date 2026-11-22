# Decisiones de la Fase 3

Registro compartido del equipo. Cada integrante edita solo la sección de su paso.

## Paso 1 – API base

API REST con FastAPI en `fase-3/api/`, con `GET /health` y `POST /predict`. No modifica `fase-1/` ni `fase-2/`: carga las versiones de `fase-2/models` y reutiliza `fase-2/src` sin copiarlo. Las rutas de los comandos parten de `fase-3/`, salvo que se indique otra cosa.

### Estructura

| Archivo | Contenido |
|---|---|
| `api/_fase2.py` | Agrega `<raíz>/fase-2` a `sys.path` y comprueba que `src` sea el de fase-2. Define `REPO_ROOT` |
| `api/config.py` | `Settings` y `Settings.from_env()`: variables de entorno y resolución de rutas |
| `api/schema.py` | Esquema de `/predict` construido desde `contrato_entrada`, traducción de errores y paso a DataFrame |
| `api/main.py` | `create_app(settings=None, observer=None)` y `EventoPrediccion`. Importarlo no crea la app ni carga el modelo |
| `api/app.py` | Solo `app = create_app()`, el objeto que usa uvicorn: `uvicorn api.app:app` |
| `requirements.txt` | Las 6 dependencias de fase-2 más las de la API, todas con versión exacta |

### Cómo se reutiliza fase-2

- **`src` debe importarse con ese nombre.** `modelo.joblib` guarda una referencia a `src.features.prepare_model_input`, así que el paquete de fase-2 tiene que ser importable como `src`. Por eso el código de la Fase 3 está en `api/` y no en un paquete `src` propio.
- **Sin `PYTHONPATH`.** `api/_fase2.py` calcula `<raíz>/fase-2` desde su propio archivo y lo pone primero en `sys.path`. Si se importara otro `src`, falla con un mensaje claro. En Docker basta conservar la estructura `<raíz>/fase-2` y `<raíz>/fase-3`.
- **Funciones usadas:** `versioning.load_version` y `versioning.VERSION_PATTERN`, `predicting.prepare_input` y `predicting.predict_rows`, y `config.input_contract` solo para `/docs` cuando no hay modelo. No se copió ninguna lógica.

### Dependencias

Python 3.12.10. `pip check` no reporta conflictos.

| Paquete | Versión | Uso |
|---|---|---|
| pandas, numpy, scikit-learn, joblib, scipy, pytest | Las de `fase-2/requirements.txt` | Sin cambios |
| `fastapi` | 0.165.0 | API |
| `starlette` | 1.10.0 | Base de FastAPI; se fija para que la instalación sea reproducible |
| `pydantic` | 2.14.4 | Validación; el código la usa directamente |
| `uvicorn` | 0.54.0 | Servidor |
| `httpx` | 0.28.1 | `TestClient` para las pruebas del Paso 2 |

### Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `MODEL_VERSION` | `v1` | Versión que carga `/predict` |
| `MODELS_DIR` | `fase-2/models` | Carpeta de versiones |
| `DATA_PATH` | `fase-2/data/movies_metadata.csv` | CSV crudo. Solo se guarda en `Settings`: lo usará `/train` en el Paso 2 |

- **Las rutas relativas se resuelven desde la raíz del repositorio**, no desde la carpeta actual: funcionan igual al lanzar uvicorn desde `fase-3/` o desde la raíz. Una variable vacía equivale a su valor por defecto.
- **La versión se carga una sola vez, al crear la app.** No hay recarga en caliente: para cambiar de versión, o volver a una anterior, se cambia `MODEL_VERSION` y se reinicia el servidor.
- `MODEL_VERSION` se valida con `VERSION_PATTERN`, así que un valor como `../x` no sale de `MODELS_DIR`.

### Uso

PowerShell:

```powershell
cd fase-3
python -m pip install -r requirements.txt
python -m uvicorn api.app:app --port 8000

# Otra versión: cambiar la variable y reiniciar
$env:MODEL_VERSION = "v2"
python -m uvicorn api.app:app --port 8000
Remove-Item Env:MODEL_VERSION
```

Bash:

```bash
cd fase-3
python -m pip install -r requirements.txt
python -m uvicorn api.app:app --port 8000

# Otra versión: cambiar la variable y reiniciar
MODEL_VERSION=v2 python -m uvicorn api.app:app --port 8000
```

La documentación interactiva queda en `http://localhost:8000/docs`, con el esquema del cuerpo de `/predict` tomado del contrato de la versión cargada.

### GET /health

Siempre responde 200 mientras la API corre, aunque no haya modelo.

```json
{"estado": "en_ejecucion", "version": "v1", "modelo_disponible": true, "detalle": null}
```

Si la versión no se pudo cargar, `modelo_disponible` es `false` y `detalle` explica por qué y lista las versiones disponibles.

### POST /predict

Recibe un objeto JSON con las 6 predictoras y devuelve `{"prediccion": 6.758120437797601, "version": "v1"}`. No necesita `vote_average`. La predicción no se redondea.

**Esquema.** Se construye desde `contrato_entrada` de la versión cargada, así que sigue el contrato de cada versión. Tipos estrictos, por decisión del equipo:

| Tipo del contrato | Acepta | Rechaza |
|---|---|---|
| `numerica` | Enteros y decimales finitos | Texto (también `"165000000"`), booleanos, `NaN` e `Infinity` |
| `binaria` (`es_secuela`) | Solo los enteros de `valores_validos`: 0 o 1 | `1.0`, `true`, `2` y `null` |
| `categorica` | Texto | Números y booleanos |

- Las 6 claves son obligatorias. Para un dato faltante se envía `null`, y solo donde el contrato pone `nulos_permitidos`. Luego lo resuelve el imputador guardado, como en la Fase 2.
- Los campos extra se ignoran, como en `predict.py`, con un aviso en el log del servidor.
- **Diferencia con `predict.py`:** el CSV acepta números escritos como texto; la API no, porque JSON tiene números propios.

**Errores**

| Caso | Código | Cuerpo |
|---|---|---|
| JSON mal formado, o que no es un objeto | 400 | `{"error": "JSON mal formado", "detalle": "..."}` |
| Clave ausente, tipo incompatible, `null` no permitido, valor fuera de 0 y 1 | 422 | `{"error": "Entrada invalida", "detalle": [{"campo": "runtime", "mensaje": "...", "valor_recibido": ...}]}`, un elemento por campo |
| Versión no disponible | 503 | `{"error": "Modelo no disponible", "version": "v9", "detalle": "..."}` |
| El modelo falla con una entrada que ya pasó la validación | 500 | `{"error": "Error interno al predecir", "version": "v1", "detalle": "El modelo de la version v1 no pudo predecir con una entrada valida. ..."}`; el traceback queda solo en el log |
| Cualquier otro error inesperado | 500 | `{"error": "Error interno al predecir"}`; el traceback queda solo en el log |

Si el modelo no está disponible, `/predict` responde 503 sin validar la entrada, porque el esquema depende del contrato de la versión.

**Versión informada.** `/predict` y `/health` informan la versión configurada, `MODEL_VERSION`, que es el nombre de la carpeta. Si `metadata["version"]` no coincide con ese nombre, por ejemplo en una carpeta copiada con otro nombre, la API la carga igual y deja un aviso en el log.

**Dos capas de validación.** Lo que pasa por pydantic se escribe como un DataFrame de una fila, en texto, y entra a `predicting.prepare_input`, que aplica las reglas de la Fase 2: nulos, conversión numérica, valores válidos y orden de columnas. Los decimales se escriben con `repr`, que conserva el valor exacto. Si esa segunda capa rechaza algo, la respuesta es 422 con su mensaje.

**Textos que cuentan como nulos.** Por reutilizar `prepare_input`, una categórica con `""`, `"NA"`, `"None"` u otro texto de `NULL_TEXTS` se trata como nula, igual que en el CSV.

### Gancho para la Fase 4

```python
from api.main import create_app, EventoPrediccion

def registrar(evento: EventoPrediccion) -> None:
    ...  # escribir el registro

app = create_app(observer=registrar)
```

- El observador se llama **exactamente una vez por cada solicitud a `/predict`**, sea cual sea el código: 200, 400, 422, 503 o 500. Va en el `finally` del endpoint.
- `EventoPrediccion` es inmutable y trae `fecha`, `codigo_http`, `version`, `prediccion` y `detalle`.
- **`fecha`** es el momento en que llegó la solicitud, **en UTC y en ISO 8601**, con microsegundos y zona: `2026-11-22T16:25:32.384916+00:00`.
- `prediccion` es `None` si el código no es 200, y `detalle` trae el cuerpo del error; con 200, `detalle` es `None`.
- Si el observador lanza una excepción, queda en el log y la respuesta no cambia.

### Verificación manual

Con uvicorn en local (Windows ARM64, Python 3.12.10): `MODEL_VERSION` sin definir en el puerto 8000, `v9` en el 8001 y `v2` en el 8002. Las solicitudes completas y sus respuestas están en el PR.

| Caso | Código | Resultado |
|---|---|---|
| (a) `/health` | 200 | `modelo_disponible: true`, versión `v1` |
| (b) Fila Dune de `ejemplo_prediccion.csv` | 200 | 6.758120437797601, igual a `predict.py` con `v1` (`np.isclose` verdadero, y además idéntica) |
| (c) `runtime: null` | 200 | 6.117448035556853 |
| (d) Sin la clave `runtime` | 422 | `campo: runtime`, `Campo obligatorio ausente; si el dato falta, envia null` |
| (e) `es_secuela: 2` | 422 | `Solo acepta los enteros 0 o 1` |
| (f) `budget: "mucho"` | 422 | `Debe ser un numero (entero o decimal) o null` |
| (g) `MODEL_VERSION=v9` | 503 | `/health` da 200 con `modelo_disponible: false`; el mensaje lista `v1, v2` |
| (h) `MODEL_VERSION=v2` | 200 | 7.083528517809986, versión `v2`, igual a `predict.py` con `v2` |
| `runtime: true` | 422 | Rechazado: no se convierte en 1.0 |
| `original_language: 5` | 422 | `Debe ser un texto o null` |
| `budget: "165000000"` | 422 | Rechazado por ser texto |
| JSON mal formado | 400 | `JSON mal formado` |

Con `TestClient` también se comprobó que el observador recibió 7 eventos por 7 solicitudes, entre ellas 400 y 422, y que un observador que falla no cambia la respuesta 200.

**Tras la revisión del PR #14.** Se repitieron con uvicorn (`uvicorn api.app:app`) los casos (a), (b), (d) y (g), con los mismos resultados. Además, con `TestClient`:

| Caso | Resultado |
|---|---|
| `import api.main` | No crea la app, no carga el modelo y no escribe en el log, aun con `MODEL_VERSION=v9` |
| Modelo que falla al predecir una entrada válida | 500 con el mensaje de la tabla de errores, sin traceback en la respuesta; el observador recibe `codigo_http=500` |
| Copia de `v1` en una carpeta `v1-copia` | `/health` y `/predict` informan `v1-copia`, y el log avisa que `metadata.json` dice `v1` |

### Para el siguiente relevo

**Qué quedó listo**

- `GET /health` y `POST /predict`, con la validación descrita y el gancho `observer` para la Fase 4.
- `requirements.txt` con versiones exactas, instalado sin conflictos.

**Cómo verificarlo**

Desde `fase-3/`, con las dependencias instaladas, levanta el servidor como en "Uso" y prueba en otra terminal:

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health
$cuerpo = '{"budget": 165000000, "runtime": 155, "release_year": 2021, "es_secuela": 0, "genero_principal": "Science Fiction", "original_language": "en"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body $cuerpo
```

Bash:

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"budget": 165000000, "runtime": 155, "release_year": 2021, "es_secuela": 0, "genero_principal": "Science Fiction", "original_language": "en"}'
```

Con `v1`, la predicción debe ser 6.758120437797601.

**Qué falta**

- **Paso 2:** `POST /train`, pruebas con pytest y el cliente.
  - `Settings.data_path` y `Settings.models_dir` ya están disponibles, y también `request.app.state.settings`.
  - Las pruebas importan `create_app` desde `api.main`, que no carga nada, nunca desde `api.app`. `create_app` carga el modelo al crearse, así que `TestClient(create_app(Settings(...)))` funciona sin bloque `with`.
  - **`/train` debe ser un endpoint síncrono (`def`, no `async def`).** FastAPI corre los `def` en un hilo aparte; con `async def`, entrenar bloquearía el servidor y `/health` dejaría de responder mientras dura el entrenamiento.
  - `/train` crea una versión nueva pero no cambia la que sirve la API (ver "Decisiones del equipo").
  - **pytest debe filtrar la advertencia de httpx** (`StarletteDeprecationWarning` al importar `TestClient`), con `filterwarnings` en la configuración de pytest de `fase-3/`.
- **Paso 3:** Docker y README. El README debe explicar cómo seleccionar la versión: cambiar `MODEL_VERSION` y reiniciar.

**A tener en cuenta**

- **Contexto de Docker en la raíz.** Con `docker build -f fase-3/Dockerfile .` desde la raíz, el contexto incluye `dataset/` (~940 MB), `.venv/`, `.git/`, el CSV y los `__pycache__`, y en la raíz no hay `.dockerignore`. Hay que crear `fase-3/Dockerfile.dockerignore`, que BuildKit usa en lugar del `.dockerignore` de la raíz, y que excluya al menos `dataset/`, `.venv/`, `.git/`, `**/__pycache__/`, `**/*.csv`, `fase-1/`, `fase-2/notebooks/`, `fase-2/tests/`, `fase-2/outputs/` y las credenciales. Los modelos se montan al ejecutar, como en la Fase 2. La imagen debe conservar `/app/fase-2/src` y `/app/fase-3/api`.
- **`origin/main` lleva 2 merges que no están en `develop`:** `77c5b26` (PR #9) y `06edb5c` (PR #13, de `develop` a `main`). No cambian el contenido; los commits de merge son los que faltan. El PR final de `develop` a `main` debe tenerlo en cuenta.
- **Aviso de starlette:** al importar `TestClient` aparece `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`. Con `httpx==0.28.1` funciona; el Paso 2 lo filtra en pytest. Cambiar de cliente sería una decisión del equipo.
- Los mensajes de error usan rutas relativas a la raíz, para no exponer rutas del equipo donde corre la API.

## Paso 2 – /train, pruebas y cliente

Agrega `POST /train`, las pruebas con pytest y un cliente de prueba. No modifica `fase-1/`, `fase-2/` ni `fase-4/`. Las rutas de los comandos parten de `fase-3/`.

### Archivos

| Archivo | Contenido |
|---|---|
| `api/training.py` (nuevo) | Lógica de `/train`: siguiente identificador libre, reserva con lock, llamada a `src.training.train_model` y traducción de errores |
| `api/main.py` | Registra `POST /train`. Las funciones `_display` y `_hide_root` pasaron a `api/config.py` para compartirlas con `api/training.py`; `/health` y `/predict` no cambian |
| `api/config.py` | Agrega `display_path` y `hide_root`, las mismas funciones que estaban en `main.py` |
| `pytest.ini` (nuevo) | `testpaths = tests` y el filtro de la advertencia de httpx |
| `tests/conftest.py`, `tests/test_api.py`, `tests/test_train.py` (nuevos) | 21 pruebas |
| `cliente/cliente.py` (nuevo) | Cliente con solo la biblioteca estándar |
| `cliente/comandos_curl.md` (nuevo) | Los mismos pasos con curl, para Bash y PowerShell |

### POST /train

Entrena con la configuración de la Fase 2 y guarda una versión nueva en `MODELS_DIR`. **No cambia la versión que sirve `/predict`** (ver "Decisiones del equipo"): para usarla hay que cambiar `MODEL_VERSION` y reiniciar.

- **Reutiliza `src/training.py`** igual que `train.py`: arma un `TrainingOptions` con `data_path = DATA_PATH`, `output_dir = MODELS_DIR` y el identificador nuevo, y deja los demás campos en sus defaults: objetivo `vote_average`, semilla 42, `test_size` 0.2, `min_votes` 10, partición `group` y `es_secuela`. Equivale a `python train.py --data <DATA_PATH> --output-dir <MODELS_DIR> --version vN`. No se copió lógica de fase-2.
- **No recibe parámetros.** Acepta un cuerpo vacío; si llega un cuerpo, se ignora (ver "Decisiones del equipo").
- **Identificador:** el siguiente `vN` libre en `MODELS_DIR`, a partir del mayor número existente: con `v1` y `v2`, `v3`. Solo cuentan los nombres `v` seguidos de dígitos; `v-test` o `v1-copia` no afectan la numeración.
- **Sin choques:** un lock reserva el identificador antes de entrenar, así que dos `/train` simultáneos reciben `v3` y `v4`. El lock vale dentro de un proceso, y uvicorn corre con uno solo por defecto. Con varios procesos, `save_version` sigue sin sobrescribir y la API responde 409. El lock es una decisión del equipo (ver "Decisiones del equipo").
- **Guardado:** con `save_version`, que nunca sobrescribe y escribe en una carpeta temporal que renombra al final. La respuesta llega cuando los tres archivos ya están guardados.
- **Síncrono:** el endpoint es `def`, así que FastAPI lo corre en un hilo aparte y `/health` sigue respondiendo mientras se entrena. Una prueba lo comprueba.
- **`git_commit`** se calcula igual que en fase-2: `git rev-parse HEAD` o, si no hay git (Docker), la variable `GIT_COMMIT`. Como en fase-2, no detecta cambios sin commit.
- Con el CSV completo tarda unos 5 s en este equipo.

Respuesta 201:

```json
{
  "version": "v3",
  "ruta": "fase-2/models/v3",
  "metrica_principal": "RMSE",
  "metricas": {
    "modelo": {
      "prueba": {"MAE": 0.6198764861376928, "RMSE": 0.8006998908850606, "R2": 0.3490927504445702},
      "cv_media": {"MAE": 0.6150446841879766, "RMSE": 0.7946378625181731, "R2": 0.34903920749062983}
    },
    "baseline": {"prueba": {"MAE": 0.7854306778621616, "RMSE": 0.9929515949761448, "R2": -0.001003798354173746}}
  },
  "version_activa": "v1",
  "detalle": "Version v3 guardada. La API sigue sirviendo v1: para usar v3, cambia MODEL_VERSION y reinicia el servidor."
}
```

`ruta` es relativa a la raíz del repositorio. Si `MODELS_DIR` queda fuera del repositorio, se informa como `MODELS_DIR/v3`, para no exponer rutas del equipo donde corre la API. Las métricas completas quedan en `metrics.json`.

**Errores.** Confirmados por el equipo (ver "Decisiones del equipo"). Ninguno muestra el traceback en la respuesta.

| Caso | Código | Cuerpo |
|---|---|---|
| No existe el archivo de `DATA_PATH` | 503 | `{"error": "Datos de entrenamiento no disponibles", "detalle": "No se encontro el archivo de datos fase-2/data/movies_metadata.csv. Revisa DATA_PATH o el montaje de los datos y vuelve a intentar."}` |
| El CSV no se puede leer o sus datos no sirven: columnas faltantes, valores que no se pueden procesar, objetivo inválido, sin películas tras los filtros | 500 | `{"error": "Datos de entrenamiento invalidos", "detalle": "<archivo>: <mensaje de fase-2>"}` |
| Otro proceso guardó el mismo identificador mientras se entrenaba | 409 | `{"error": "La version ya existe", "version": "v3", "detalle": "..."}` |
| No se puede escribir en `MODELS_DIR`, por ejemplo con un montaje de solo lectura | 500 | `{"error": "No se pudo guardar la version", "version": "v3", "detalle": "... Revisa que MODELS_DIR exista y tenga permiso de escritura ..."}`; el traceback queda en el log |
| Cualquier otro error inesperado | 500 | `{"error": "Error interno al entrenar", "detalle": "El detalle quedo en el log del servidor."}` |

Por qué esos códigos: el cliente no envía datos, así que un problema con el CSV no es un error de la solicitud (4xx) sino del servidor. Se usa 503 cuando falta el archivo, porque se resuelve montándolo o corrigiendo `DATA_PATH` y volviendo a intentar, y 500 cuando el archivo existe pero sus datos no sirven. El campo `error` distingue los casos. Ningún error deja una versión a medias.

### Pruebas

Desde `fase-3/`, con las dependencias de `requirements.txt`. Debe ser `python -m pytest`, no `pytest`, para que `api` se pueda importar. El comando es igual en PowerShell y en Bash:

```
python -m pytest -v
```

Resultado en Windows ARM64, con Python 3.12.10: **21 pruebas aprobadas en cerca de 1,5 s**, sin advertencias.

**Modelo pequeño: `fase-2/models/v1`.** Está en el repositorio, pesa cerca de 380 KB y carga en menos de un segundo. Permite comparar con la predicción ya verificada en el Paso 1 (6.758120437797601 para Dune) sin entrenar nada para probar `/predict`. Un modelo sintético exigiría entrenarlo en cada ejecución y no se podría comparar con `predict.py`. Se usa en modo solo lectura: el fixture `modelos_del_repo_intactos` compara los hashes de `fase-2/models` al inicio y al final, y falla si cambiaron. Además, los `Settings` de esas pruebas apuntan `DATA_PATH` a un archivo inexistente, así que un `/train` por error respondería 503 sin escribir. Las pruebas de `/train` copian `v1` y `v2` a `tmp_path` y escriben ahí.

| Prueba | Verifica |
|---|---|
| **Obligatorias** (`test_api.py`) | |
| `test_health_responde_200` | 200 y el cuerpo completo de `/health` |
| `test_entrada_valida_devuelve_prediccion_y_version` | 200, claves exactas `prediccion` y `version`, versión `v1` y la predicción de Dune |
| `test_entrada_sin_variable_obligatoria_se_rechaza` | Sin `runtime`: 422 con `campo: runtime` y `Campo obligatorio ausente; si el dato falta, envia null` |
| **Extras** (`test_api.py`) | |
| `test_tipo_o_valor_invalido_da_422` (3 casos) | `es_secuela: 2`, `budget: "mucho"` y `runtime: true`: 422 con el campo, el mensaje y el valor recibido |
| `test_json_mal_formado_da_400` | 400 con `JSON mal formado` |
| `test_campo_extra_se_ignora` | Un campo de más da la misma predicción |
| `test_runtime_null_predice` | `runtime: null` da 200 con una predicción finita y distinta |
| `test_version_inexistente_da_503` | Con `v9`: `/predict` da 503 y lista `v1, v2`; `/health` informa `modelo_disponible: false` |
| `test_error_del_modelo_da_500_sin_traceback` | Un modelo que lanza una excepción da 500 sin traceback ni el mensaje interno |
| `test_version_informada_es_la_configurada_por_variable` | Con la variable `MODEL_VERSION=v2`, `/health` y `/predict` informan `v2` |
| `test_version_informada_es_el_nombre_de_la_carpeta` | Una copia de `v1` llamada `mi-version` se informa como `mi-version` |
| `test_observador_se_llama_una_vez_por_intento` | 200, 422 y 400 producen 3 eventos, en orden; `/health` no produce eventos |
| `test_observador_tambien_recibe_503` | Sin modelo, un intento produce un evento 503 |
| **`/train`** (`test_train.py`, CSV sintético de 60 películas) | |
| `test_train_es_sincrono` | El endpoint no es `async def` |
| `test_train_crea_version_nueva_y_no_cambia_la_activa` | Sin cuerpo: 201 con `v3`, los tres archivos y `metadata.json` con objetivo y semilla 42; `v1` y `v2` sin cambios (hashes); `/health` y `/predict` siguen en `v1`; un segundo `/train` da `v4`; una app nueva con `v3` predice con `v3` |
| `test_train_sin_archivo_de_datos_da_503` | 503 y no crea carpetas |
| `test_train_con_datos_invalidos_da_500_sin_traceback` | CSV sin `vote_average`: 500 con el mensaje de fase-2 y sin temporales a medias |
| `test_siguiente_identificador` | `v1` en una carpeta vacía; ignora `v-test`, `v10-copia` y `V20`; cuenta un archivo `v7` y las reservas |
| `test_train_simultaneos_no_repiten_identificador` | Dos llamadas a la vez reciben `v3` y `v4`. Usa un entrenamiento falso con una barrera para que las dos estén "entrenando" al mismo tiempo |

Se comprobó que la última prueba detecta el error: sin la reserva, los dos hilos eligen `v3` y la prueba falla.

**Advertencia de httpx.** `pytest.ini` filtra solo `StarletteDeprecationWarning` con el mensaje `Using httpx with starlette.testclient is deprecated`. Cualquier otra advertencia se sigue mostrando.

### Cliente de prueba

`cliente/cliente.py` usa solo la biblioteca estándar (`urllib`). Consulta `/health`, envía una predicción a `/predict` y muestra la solicitud y la respuesta. Termina con código 0 si las dos respuestas son 200, y con 1 si no lo son o si no se puede conectar.

```
python cliente/cliente.py
python cliente/cliente.py --url http://localhost:8001
```

**La entrada es una película real: Toy Story 2** (id 863). Se tomó su fila de `movies_metadata.csv` y se derivaron las 6 predictoras con las funciones de fase-2 sobre el CSV completo: `data.clean_data`, `features.add_sequel_feature`, `data.apply_filters` y `features.derive_features`. Hay que usar el CSV completo porque `es_secuela` depende de las demás películas de la colección. Los valores quedan fijos en el script:

```json
{"budget": 90000000, "runtime": 92, "release_year": 1999, "es_secuela": 1, "genero_principal": "Animation", "original_language": "en"}
```

En el CSV su `vote_average` es 7.3, con 3914 votos. Con `v1` la predicción es **6.2250117576267305**, igual a la de `predicting.prepare_input` y `predicting.predict_rows` de fase-2. La película puede haber quedado en el entrenamiento de `v1`, así que esto no evalúa el modelo. Los valores de `data/ejemplo_prediccion.csv` son ilustrativos y no se usaron.

`cliente/comandos_curl.md` tiene los mismos pasos con `curl` en Bash, y con `Invoke-RestMethod` y `curl.exe` en PowerShell. Con `curl.exe` el JSON se pasa por la entrada estándar (`--data-binary "@-"`), porque Windows PowerShell 5.1 quita las comillas dobles de un argumento. Los comandos de PowerShell se probaron contra el servidor.

### Verificación manual

Con `python -m uvicorn api.app:app --port 8000` desde `fase-3/` (Windows ARM64, Python 3.12.10). Antes se guardaron los hashes de los archivos de `v1` y `v2`.

| Paso | Resultado |
|---|---|
| (a) `python cliente/cliente.py` | `/health` 200 con `v1`; `/predict` 200 con `{"prediccion": 6.2250117576267305, "version": "v1"}`; código de salida 0 |
| (b) `POST /train` sin cuerpo | 201 en 5,5 s, con `version: v3` y `ruta: fase-2/models/v3`. Un `/health` enviado durante el entrenamiento respondió 200 en 0,2 s |
| (b) Carpeta nueva | `fase-2/models/v3` con `metadata.json`, `metrics.json` y `modelo.joblib`. `metadata.json` trae `version: v3`, `objetivo: vote_average`, `semilla: 42` y el `git_commit` actual |
| (b) Versiones anteriores | `sha256sum -c` da OK en los 6 archivos de `v1` y `v2` |
| (b) Versión activa | `/predict` siguió informando `v1` |
| (c) Reinicio con `MODEL_VERSION=v3` | `/health` y `/predict` informan `v3`. Toy Story 2 da 6.2250117576267305 y Dune 6.758120437797601, igual que con `v1` |
| (d) Limpieza | Se borró `fase-2/models/v3`; los hashes de `v1` y `v2` siguen iguales |

`v3` dio las mismas métricas y predicciones que `v1`, y su `metrics.json` es idéntico byte a byte: se entrenó con el mismo CSV, la misma semilla y el mismo código de entrenamiento. Coincide con lo que la Fase 2 documentó sobre el determinismo sin parada temprana. El `git_commit` registrado fue el de `HEAD`, aunque había cambios sin commit en `fase-3/`. Es la limitación ya conocida de fase-2, y aquí no afecta el resultado, porque el código de entrenamiento es el de fase-2, sin cambios.

### Para el siguiente relevo

Este relevo reemplaza la lista "Qué falta" del Paso 1, cuyo Paso 2 ya quedó hecho.

**Qué quedó listo**

- `POST /train`, las 21 pruebas con `pytest.ini` y el cliente con sus comandos curl.

**Cómo verificarlo**

Desde `fase-3/`, `python -m pytest -v` debe dar 21 pruebas aprobadas. Con el servidor corriendo, `python cliente/cliente.py` debe mostrar 6.2250117576267305 con `v1`. Un `POST /train` crea `fase-2/models/v3`, que **no se sube al repositorio**. Como `.gitignore` permite `fase-2/models/**`, aparecerá en `git status`: bórrala después de probar.

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/train
Remove-Item -Recurse ..\fase-2\models\v3
```

Bash:

```bash
curl -s -X POST http://localhost:8000/train
rm -r ../fase-2/models/v3
```

**Qué falta: Paso 3, Docker y README de `fase-3/`**

- **Puerto 8000.** Dentro del contenedor, uvicorn debe escuchar en `0.0.0.0`: `python -m uvicorn api.app:app --host 0.0.0.0 --port 8000`, ejecutado desde `/app/fase-3`, y publicarse con `-p 8000:8000`. Con el `127.0.0.1` por defecto, el cliente no llega desde fuera del contenedor.
- **Montajes.** La imagen no lleva datos ni modelos.
  - Datos en **solo lectura**: la carpeta con `movies_metadata.csv` en `/app/fase-2/data`, con `:ro`. Es el `DATA_PATH` por defecto.
  - `models/` **con escritura**: `fase-2/models` en `/app/fase-2/models`, sin `:ro`, porque `/train` guarda ahí la versión nueva, que así queda en el equipo al borrar el contenedor. Con un montaje de solo lectura, `/train` responde 500 con `No se pudo guardar la version`.
  - Las rutas relativas de `DATA_PATH` y `MODELS_DIR` se resuelven desde la raíz del repositorio, que en la imagen es `/app` si se conserva la estructura `/app/fase-2/src` y `/app/fase-3/api`.
- **`GIT_COMMIT`.** En la imagen no hay git ni `.git`, así que `metadata.json` toma el commit de esta variable; sin ella queda `no disponible`. Se pasa al ejecutar: `-e GIT_COMMIT=$(git rev-parse HEAD)` en Bash y `-e "GIT_COMMIT=$(git rev-parse HEAD)"` en PowerShell.
- **`.dockerignore`.** Además de lo que el Paso 1 lista para `fase-3/Dockerfile.dockerignore`, hay que excluir `fase-3/tests/`, `fase-3/cliente/`, `fase-3/pytest.ini`, `**/.pytest_cache/` y `fase-2/models/`: las pruebas y el cliente no corren en la imagen, y los modelos se montan.
- **Cliente.** Corre desde el equipo, no desde el contenedor: `python cliente/cliente.py` desde `fase-3/`, con `--url` si se publica en otro puerto. No necesita dependencias.
- **README.** Debe incluir un ejemplo de solicitud y respuesta de `/predict`, por ejemplo la salida del cliente con Toy Story 2, y también uno de `/train`. Debe explicar que `/train` no cambia la versión activa y que, para usar la nueva, se cambia `MODEL_VERSION` y se reinicia, y cómo correr las pruebas.

**A tener en cuenta**

- **`fase-2/models/` debe tener permiso de escritura** donde corra `/train`. En Linux, el usuario del contenedor debe poder escribir en el montaje.
- **Varios workers:** el lock de `/train` es por proceso. Con varios workers de uvicorn, dos entrenamientos simultáneos podrían elegir el mismo identificador; `save_version` no sobrescribe y uno de los dos recibe 409.

## Paso 3 – Docker y README

Agrega `fase-3/Dockerfile`, `fase-3/Dockerfile.dockerignore` y `fase-3/README.md`. No modifica `fase-1/`, `fase-2/`, `fase-4/` ni el código de `fase-3/api`, `fase-3/tests` o `fase-3/cliente`. Los comandos de Docker parten de la raíz del repositorio.

### Qué se decidió

| Decisión | Motivo |
|---|---|
| Construir desde la raíz: `docker build -f fase-3/Dockerfile -t modelos-fase3:1.0 .` | La imagen necesita `fase-2/src`, que está fuera de `fase-3/` |
| Base `python:3.12.10-slim`, la misma de la Fase 2 | Misma versión de Python que el entorno local |
| `/app` es la raíz del repositorio: la imagen copia `fase-2/src` en `/app/fase-2/src` y `fase-3/api` en `/app/fase-3/api` | `api/_fase2.py` calcula `<raíz>/fase-2` desde su propio archivo, y las rutas por defecto (`fase-2/models`, `fase-2/data/movies_metadata.csv`) caen justo en los montajes. No hace falta `PYTHONPATH` ni pasar `MODELS_DIR` o `DATA_PATH` |
| Directorio de trabajo `/app/fase-3` y `CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]`, con `EXPOSE 8000` | uvicorn agrega la carpeta actual a `sys.path`, así que `api` se importa desde ahí. Con `0.0.0.0` responde fuera del contenedor |
| Se instala `fase-3/requirements.txt` completo, incluidos pytest y httpx | Es el archivo de dependencias de la fase; separar las de pruebas cambiaría el código de la fase. Las pruebas no se copian a la imagen |
| `Dockerfile.dockerignore` excluye todo (`*`) y vuelve a incluir solo `fase-2/src/`, `fase-3/api/` y `fase-3/requirements.txt`. Dentro de eso excluye cachés, CSV, ZIP, modelos (`*.joblib`, `*.pkl`) y credenciales | Una lista de exclusión tendría que nombrar cada carpeta de la raíz y se rompería al agregar una nueva. Con la lista de inclusión, `dataset/`, `.venv/`, `.git/`, `fase-1/`, `fase-4/`, los datos, los modelos, `outputs/`, las pruebas, el cliente y los parches no llegan nunca |
| Datos montados en solo lectura y `fase-2/models` con escritura | `/train` guarda la versión nueva en el equipo; los datos no deben cambiar |
| Sin `HEALTHCHECK` ni usuario no root | La imagen base no trae `curl`, y el montaje de modelos debe tener escritura; en Docker Desktop (Windows) los archivos quedan en el equipo sin problemas de permisos. Queda como mejora |

### Verificación en Docker

Windows 11 ARM64, Docker Desktop 4.98.0 (Docker 29.9.2, motor `linux/arm64`). Contenedor con `-p 8000:8000`, `fase-2/data` en `/app/fase-2/data:ro`, `fase-2/models` en `/app/fase-2/models` y `GIT_COMMIT` con el hash de `HEAD`. El flujo completo se ejecutó en Windows PowerShell 5.1 y se repitió en Git Bash (GNU bash 5.3) hasta `/train`.

| Paso | Resultado |
|---|---|
| Contexto de construcción | 17 archivos, 85.574 bytes. Se midió con una construcción aparte que copia todo el contexto, con el mismo `.dockerignore` |
| Imagen | `modelos-fase3:1.0`, 746 MB en disco y 159 MB comprimida |
| `/app` en el contenedor | Solo `fase-2/src` (9 archivos `.py`), `fase-3/api` (7 archivos `.py`) y `fase-3/requirements.txt`: 17 archivos, sin datos, modelos, credenciales ni `__pycache__`. No hay git |
| (a) `/health` | 200, `{"estado": "en_ejecucion", "version": "v1", "modelo_disponible": true, "detalle": null}` |
| (b) `python cliente/cliente.py` desde el equipo | `/health` 200 y `/predict` 200 con `{"prediccion": 6.2250117576267305, "version": "v1"}`, igual que en local; código de salida 0 |
| (c) Toy Story 2 sin `runtime` | 422, `campo: runtime`, `Campo obligatorio ausente; si el dato falta, envia null` |
| (d) `POST /train` | 201 en 19 s, con `version: v3` y `version_activa: v1`. En el equipo apareció `fase-2/models/v3` con `metadata.json`, `metrics.json` y `modelo.joblib`; `metadata.json` registró el `git_commit` pasado en `GIT_COMMIT`, y `metrics.json` es idéntico al de `v1`. `/predict` siguió en `v1` |
| (d) Persistencia | Después de `docker stop` y `docker rm`, `fase-2/models/v3` seguía en el equipo con sus tres archivos |
| (e) `MODEL_VERSION=v2` | `/health` y `/predict` informan `v2`. Toy Story 2 da 6.473487560963072 y Dune 7.083528517809986, igual que en el Paso 1 |
| `MODEL_VERSION=v9` | `/health` 200 con `modelo_disponible: false`; `/predict` 503, con las versiones disponibles en el mensaje |
| `MODELS_DIR=/modelos` y `DATA_PATH=/datos/movies_metadata.csv`, con los modelos en `:ro` | `/predict` 200 con `v1`; `/train` 500 con `No se pudo guardar la version` y la ruta `/modelos` en el mensaje |
| (f) `python -m pytest` en local | 21 pruebas aprobadas. También en un entorno nuevo con `requirements.txt` instalado, donde `pip check` no reportó conflictos |
| Limpieza | Se borraron `v3` y la `v4` creada en la repetición con Git Bash; `git status` no muestra cambios en `fase-2/models` |

También se comprobó en local `python -m uvicorn api.app:app --port 8000` con el cliente: misma respuesta que en Docker.

### Para el siguiente relevo

**Qué quedó listo**

- La imagen de la API y su `.dockerignore`, y el README de `fase-3/` con la ejecución local y en Docker, los endpoints, los errores, la selección de versión, el cliente, las pruebas y las limitaciones.

**Cómo verificarlo**

Desde la raíz, construir y correr el contenedor como en la sección "Ejecución con Docker" del README; luego, desde `fase-3/`, `python cliente/cliente.py` debe mostrar 6.2250117576267305 con `v1`. Un `POST /train` crea `fase-2/models/v3`, que no se sube: bórrala después de probar.

**A tener en cuenta**

- **El log del contenedor solo muestra los mensajes de uvicorn y los avisos o errores de la API.** El logger `api` no tiene un handler propio, así que sus mensajes `INFO` (como `Entrenando la version ...`) no aparecen; los `WARNING` y `ERROR` sí. Configurarlo sería un cambio de código.
- **README y Docker de la Fase 4.** La imagen de este paso sirve `api.app:app`, que no registra las predicciones. La Fase 4 tiene su propia app con el observador (`fase-4/registro/app.py`). Su Docker puede partir de este Dockerfile, copiar también `fase-4/registro` conservando la estructura y montar `fase-4/registros` con escritura; su `.dockerignore` tendría que volver a incluir esa carpeta.
- La portabilidad solo se comprobó en ARM64.

## Decisiones del equipo

### /train no cambia la versión que sirve la API

Decidido en la revisión del PR #14. `POST /train` crea una versión nueva en `MODELS_DIR`, pero no cambia la que sirve `/predict`: la API sigue con la versión que cargó al iniciar. Para usar la versión nueva hay que cambiar `MODEL_VERSION` y reiniciar el servidor. Es coherente con la decisión del Paso 1 de cargar el modelo al iniciar, sin recarga en caliente.

### Códigos de error de /train

Confirmado por el equipo en el Paso 2. `POST /train` responde 503 si no existe el archivo de `DATA_PATH`; 500 con `"Datos de entrenamiento invalidos"` si el CSV existe pero sus datos no sirven; 409 si otro proceso guardó el mismo identificador mientras se entrenaba; 500 con `"No se pudo guardar la version"` si no se puede escribir en `MODELS_DIR`, y 500 con `"Error interno al entrenar"` ante cualquier otro error. Ninguna respuesta muestra el traceback. El cliente no envía los datos, así que un problema con el CSV es del servidor y no se responde con 4xx. La tabla completa está en "Paso 2 – /train, pruebas y cliente".

### /train ignora el cuerpo

Confirmado por el equipo en el Paso 2. `POST /train` no recibe parámetros: acepta un cuerpo vacío y, si llega uno, lo ignora. Siempre entrena con la configuración de la Fase 2 (`DATA_PATH`, objetivo `vote_average`, semilla 42 y los demás defaults de `TrainingOptions`).

### Un lock reserva el identificador de /train

Confirmado por el equipo en el Paso 2. Antes de entrenar, `/train` reserva el siguiente `vN` libre con un lock, así que dos llamadas simultáneas reciben identificadores distintos y pueden entrenar a la vez. El lock vale dentro de un proceso; con varios workers de uvicorn, `save_version` sigue sin sobrescribir y una de las llamadas recibe 409.
