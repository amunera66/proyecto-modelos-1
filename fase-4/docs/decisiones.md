# Decisiones de la Fase 4

Registro compartido del equipo. Cada integrante edita solo la sección de su paso.

## Paso 2 – Registro

Cada llamada a `POST /predict` agrega una fila a un CSV, también las rechazadas por validación. No modifica `fase-1/`, `fase-2/` ni `fase-3/`: usa `create_app` de fase-3 y le pasa un observador. Las rutas de los comandos parten de `fase-4/`, salvo que se indique otra cosa.

### Estructura

| Archivo | Contenido |
|---|---|
| `registro/_fase3.py` | Agrega `<raíz>/fase-3` a `sys.path`, con una ruta relativa al propio archivo, y comprueba que `api` sea el de fase-3. Fase-3 hace lo mismo con fase-2 |
| `registro/csv_logger.py` | `RegistroCSV(path)`, el observador, y `build_row` y `format_timestamp` |
| `registro/app.py` | `app = create_app(observer=RegistroCSV(LOG_PATH))`, para `uvicorn registro.app:app` |
| `registros/.gitkeep` | La carpeta del registro queda en el repositorio; el registro vivo no |
| `requirements.txt` | Las mismas versiones exactas de `fase-3/requirements.txt`, sin dependencias nuevas |
| `pytest.ini` y `tests/` | Pruebas del registro |

El paquete se llama `registro` porque `api` lo usa fase-3 y `src`, fase-2 y el modelo guardado.

### Cómo se engancha a fase-3

```python
from api.main import create_app
from registro.csv_logger import RegistroCSV

app = create_app(observer=RegistroCSV(LOG_PATH))
```

Fase-3 llama al observador exactamente una vez por cada solicitud a `/predict`, con cualquier código, desde el `finally` del endpoint. Si el observador falla, por ejemplo porque no se puede escribir el archivo, fase-3 registra el error en su log y la respuesta no cambia, pero esa fila se pierde. `/health` no llama al observador. La app de fase-3 sola (`uvicorn api.app:app`) sigue igual y no registra nada.

### Configuración

| Variable | Por defecto | Uso |
|---|---|---|
| `LOG_PATH` | `fase-4/registros/predicciones.csv` | Archivo del registro. Si es relativa, se resuelve desde la raíz del repositorio con `resolve_path` de fase-3 |
| `MODEL_VERSION`, `MODELS_DIR` | Los de fase-3 | Versión del modelo, sin cambios |

PowerShell:

```powershell
cd fase-4
python -m pip install -r requirements.txt
python -m uvicorn registro.app:app --port 8000

# Registro en otro archivo
$env:LOG_PATH = "fase-4/registros/otro.csv"
python -m uvicorn registro.app:app --port 8000
Remove-Item Env:LOG_PATH
```

Bash:

```bash
cd fase-4
python -m pip install -r requirements.txt
python -m uvicorn registro.app:app --port 8000

# Registro en otro archivo
LOG_PATH=fase-4/registros/otro.csv python -m uvicorn registro.app:app --port 8000
```

### Formato del registro

CSV en UTF-8, separado por comas, con fin de línea `\n` y una fila por intento:

```text
fecha_hora,estado_http,version,prediccion
2026-11-22T19:36:10+00:00,200,v1,6.758120437797601
2026-11-22T19:36:10+00:00,422,,
```

| Columna | Contenido |
|---|---|
| `fecha_hora` | Momento en que llegó la solicitud. ISO 8601 en UTC, truncado a segundos, con `+00:00` (decisión del equipo) |
| `estado_http` | Código HTTP de la respuesta, como entero |
| `version` | La versión configurada (`MODEL_VERSION`), solo cuando se usó el modelo: 200 y 500. Vacía en 400, 422 y 503 |
| `prediccion` | Solo en los 200, con todos los decimales, igual a la respuesta. Vacía en cualquier error |

- **Archivo:** se abre en modo agregar (`"a"`, UTF-8, `newline=""`), así que el historial se conserva entre ejecuciones. El encabezado se escribe solo si el archivo no existe o está vacío; se revisa en cada escritura, así que si alguien borra el archivo con el servidor en marcha, el siguiente intento lo crea de nuevo con encabezado. La carpeta se crea si falta.
- **Concurrencia:** un `threading.Lock` evita que dos solicitudes simultáneas mezclen sus filas dentro del mismo proceso. No protege si varios procesos escriben el mismo archivo, así que el servidor debe correr con un solo worker, que es lo que hace uvicorn por defecto.
- **Un 500 siempre lleva versión** (decisión del equipo). Fase-3 responde 500 en dos casos: cuando el modelo falla con una entrada válida, y ante un error inesperado que podría ocurrir antes de usar el modelo. El observador no puede distinguirlos sin modificar fase-3, así que el segundo caso, que es raro, también queda con versión.
- **`.gitignore`:** la raíz excluye solo `fase-4/registros/predicciones.csv`. Cualquier otro archivo de esa carpeta, como uno de muestra, se puede versionar.

### Pruebas

Desde `fase-4/`. El comando es igual en PowerShell y en Bash:

```text
python -m pytest -v
```

Resultado en Windows ARM64, con Python 3.12.10: **11 pruebas aprobadas en 0,62 s**, sin advertencias. `pytest.ini` filtra el aviso de starlette sobre httpx. El registro va a un `tmp_path`; `fase-2/models/v1` solo se lee.

| Prueba | Verifica |
|---|---|
| `test_dos_validas_y_una_incompleta_dejan_tres_filas` | Exactamente 3 filas (200, 200, 422); versión y predicción solo en las válidas, y la predicción es la misma de la respuesta |
| `test_json_mal_formado_deja_una_fila_400_sin_version` | Una fila 400 sin versión ni predicción |
| `test_version_inexistente_deja_una_fila_503_sin_version` | Con `v9`, una fila 503 sin versión |
| `test_error_del_modelo_deja_500_con_version_y_sin_prediccion` | Un modelo que falla deja 500 con versión y sin predicción |
| `test_encabezado_una_sola_vez_con_dos_observadores` | Dos `RegistroCSV` sobre el mismo archivo escriben el encabezado una vez |
| `test_historial_se_conserva_entre_ejecuciones` | Dos apps sobre el mismo archivo agregan sus filas |
| `test_archivo_vacio_recibe_el_encabezado` | Un archivo que existe pero está vacío recibe el encabezado |
| `test_health_no_escribe_en_el_registro` | `/health` no crea el archivo |
| `test_fecha_hora_en_utc_a_segundos` | Formato `AAAA-MM-DDTHH:MM:SS+00:00` y hora dentro del intervalo de la solicitud |
| `test_format_timestamp_convierte_a_utc_y_trunca` | Una hora en otra zona se pasa a UTC y se truncan los microsegundos |
| `test_escrituras_simultaneas_no_se_mezclan` | 8 hilos con 50 filas cada uno dejan 400 filas completas |

### Verificación manual

`uvicorn registro.app:app` desde `fase-4/`, con `LOG_PATH` en una carpeta temporal que no existía. Los registros de prueba se borraron al final.

| Caso | Resultado |
|---|---|
| (a) Dune y Top Gun: Maverick de `ejemplo_prediccion.csv`, y una sin `runtime` | 200, 200 y 422; 3 filas |
| (b) JSON mal formado | 400; una fila sin versión |
| (c) Reiniciar el servidor y enviar Parasite | 200; el CSV conserva las 4 filas anteriores y el encabezado no se repite |
| (d) `/health` | 200; el registro sigue con 6 líneas |
| (e) `uvicorn api.app:app` desde `fase-3/` | `/health` y `/predict` responden 200; no se crea ni se modifica ningún archivo |

CSV resultante:

```text
fecha_hora,estado_http,version,prediccion
2026-11-22T19:36:10+00:00,200,v1,6.758120437797601
2026-11-22T19:36:10+00:00,200,v1,6.760580876200448
2026-11-22T19:36:10+00:00,422,,
2026-11-22T19:36:11+00:00,400,,
2026-11-22T19:36:16+00:00,200,v1,7.240972748649045
```

También se comprobó que, sin `LOG_PATH`, el registro va a `fase-4/registros/predicciones.csv` y que git lo ignora.

### Para el siguiente relevo

**Qué quedó listo**

- `RegistroCSV` y `registro/app.py`, con el registro de cada intento a `/predict`.
- 11 pruebas en `tests/`.

**Formato del registro, para el script de monitoreo (Paso 4)**

- Archivo: `fase-4/registros/predicciones.csv` por defecto, o el de `LOG_PATH`. UTF-8, coma, fin de línea `\n`, encabezado en la primera línea.
- Columnas, en este orden: `fecha_hora,estado_http,version,prediccion`.
- `fecha_hora`: `AAAA-MM-DDTHH:MM:SS+00:00`, siempre UTC. `pd.to_datetime(..., utc=True)` y `datetime.fromisoformat` lo leen directamente.
- `estado_http`: entero. **Total de solicitudes** = número de filas sin el encabezado. **Fallidas** = filas con `estado_http >= 400`, es decir 4xx y 5xx. Porcentaje = fallidas / total × 100.
- `version` y `prediccion` pueden estar vacías: en pandas, leer con `keep_default_na=True` (vacío → `NaN`), o con `dtype=str` y `keep_default_na=False` (vacío → `""`). Una fila de error tiene `prediccion` vacía; `version` también lo está en 400, 422 y 503.
- El archivo puede no existir todavía, si no ha llegado ninguna solicitud, o estar vacío: el script debe manejar los dos casos con un mensaje claro.

**Docker (Paso 6)**

- **La carpeta `fase-4/registros/` debe montarse** desde el equipo, con escritura, igual que `models/` en la Fase 2. Si no se monta, el registro queda dentro del contenedor y se pierde al eliminarlo.
- La imagen debe conservar la estructura `<raíz>/fase-2/src`, `<raíz>/fase-3/api` y `<raíz>/fase-4/registro`, porque los imports se calculan con rutas relativas. Aplica lo mismo que anotó fase-3 sobre el contexto en la raíz: hace falta un `Dockerfile.dockerignore` que excluya `dataset/`, `.venv/`, `.git/`, los CSV y los `__pycache__`.
- Correr con un solo worker de uvicorn (el valor por defecto), por la limitación de concurrencia.
- En Linux, si el contenedor corre como root, el CSV del registro puede quedar a nombre de root. Fase-2 anotó la misma limitación y no la comprobó.

**A tener en cuenta**

- Si escribir el registro falla, la respuesta de `/predict` no cambia, pero esa fila se pierde y el error queda solo en el log del servidor.
- `fase-3` sigue sin su Paso 2 (`/train` y pruebas) en `develop`. Si `/train` se agrega a fase-3, no pasa por el observador y no se registra: la especificación solo pide registrar `/predict`.

## Paso 4 – Script de monitoreo

Pendiente.

## Paso 6 – Docker y README

Pendiente.

## Decisiones del equipo

### Formato de fecha_hora

`fecha_hora` se escribe en ISO 8601, en UTC, truncada a segundos y con la zona explícita: `2026-11-06T10:02:00+00:00`. El ejemplo de la especificación no lleva zona; se agregó `+00:00` para que no haya dudas de que es UTC.

### Versión en los 500

Un 500 siempre se registra con versión, aunque en el caso raro de un error inesperado antes de usar el modelo no se haya usado. Distinguirlos exigiría modificar fase-3.
