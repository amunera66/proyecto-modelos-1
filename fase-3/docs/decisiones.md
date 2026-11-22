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
| `api/main.py` | `create_app(settings=None, observer=None)`, `EventoPrediccion` y el objeto `app` para uvicorn |
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
python -m uvicorn api.main:app --port 8000

# Otra versión: cambiar la variable y reiniciar
$env:MODEL_VERSION = "v2"
python -m uvicorn api.main:app --port 8000
Remove-Item Env:MODEL_VERSION
```

Bash:

```bash
cd fase-3
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --port 8000

# Otra versión: cambiar la variable y reiniciar
MODEL_VERSION=v2 python -m uvicorn api.main:app --port 8000
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
| Error inesperado | 500 | `{"error": "Error interno al predecir"}`; el traceback queda solo en el log |

Si el modelo no está disponible, `/predict` responde 503 sin validar la entrada, porque el esquema depende del contrato de la versión.

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

- **Paso 2:** `POST /train`, pruebas con pytest y el cliente. `Settings.data_path` y `Settings.models_dir` ya están disponibles. `create_app` carga el modelo al crearse, así que `TestClient(create_app(Settings(...)))` funciona sin bloque `with`. Hay que decidir si `/train` cambia la versión que sirve `/predict`: hoy no hay recarga en caliente, por decisión del equipo.
- **Paso 3:** Docker y README. El README debe explicar cómo seleccionar la versión: cambiar `MODEL_VERSION` y reiniciar.

**A tener en cuenta**

- **Contexto de Docker en la raíz.** Con `docker build -f fase-3/Dockerfile .` desde la raíz, el contexto incluye `dataset/` (~940 MB), `.venv/`, `.git/`, el CSV y los `__pycache__`, y en la raíz no hay `.dockerignore`. Hay que crear `fase-3/Dockerfile.dockerignore`, que BuildKit usa en lugar del `.dockerignore` de la raíz, y que excluya al menos `dataset/`, `.venv/`, `.git/`, `**/__pycache__/`, `**/*.csv`, `fase-1/`, `fase-2/notebooks/`, `fase-2/tests/`, `fase-2/outputs/` y las credenciales. Los modelos se montan al ejecutar, como en la Fase 2. La imagen debe conservar `/app/fase-2/src` y `/app/fase-3/api`.
- **`origin/main` lleva 2 merges que no están en `develop`:** `77c5b26` (PR #9) y `06edb5c` (PR #13, de `develop` a `main`). No cambian el contenido; los commits de merge son los que faltan. El PR final de `develop` a `main` debe tenerlo en cuenta.
- **Aviso de starlette:** al importar `TestClient` aparece `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`. Con `httpx==0.28.1` funciona. Si molesta en pytest, se puede filtrar el aviso; cambiar de cliente sería una decisión del equipo.
- Los mensajes de error usan rutas relativas a la raíz, para no exponer rutas del equipo donde corre la API.

## Paso 2 – /train, pruebas y cliente

Pendiente.

## Paso 3 – Docker y README

Pendiente.

## Decisiones del equipo

Pendiente.
