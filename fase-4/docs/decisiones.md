# Decisiones de la Fase 4

Registro compartido del equipo. Cada integrante edita solo la sección de su paso.

## Paso 2 – Registro

Cada llamada a `POST /predict` agrega una fila a un CSV, también las rechazadas por validación. No modifica `fase-1/`, `fase-2/` ni `fase-3/`: usa `create_app` de fase-3 y le pasa un observador. Las rutas de los comandos parten de `fase-4/`, salvo que se indique otra cosa.

### Estructura

| Archivo | Contenido |
|---|---|
| `registro/_fase3.py` | Agrega `<raíz>/fase-3` a `sys.path`, con una ruta relativa al propio archivo, y comprueba que `api` sea el de fase-3. Fase-3 hace lo mismo con fase-2 |
| `registro/csv_logger.py` | `RegistroCSV(path)`, el observador, y `build_row` y `format_timestamp` |
| `registro/config.py` | `DEFAULT_LOG_PATH` y `log_path_from_env()`. Importarlo no crea la app ni carga el modelo |
| `registro/app.py` | `app = create_app(observer=RegistroCSV(LOG_PATH))`, para `uvicorn registro.app:app`. Importarlo crea la app y carga el modelo |
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
| `LOG_PATH` | `fase-4/registros/predicciones.csv` | Archivo del registro. La lee `registro.config`; si es relativa, se resuelve desde la raíz del repositorio con `resolve_path` de fase-3, que se importa sin cargar el modelo |
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

Resultado en Windows ARM64, con Python 3.12.10: **14 pruebas aprobadas en 0,61 s**, sin advertencias. `pytest.ini` filtra el aviso de starlette sobre httpx. El registro va a un `tmp_path`; `fase-2/models/v1` solo se lee.

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
| **`test_config.py`** | |
| `test_importar_config_no_crea_la_app_ni_carga_el_modelo` | En un proceso aparte, con `MODEL_VERSION=v9`, `import registro.config` no importa `registro.app`, `api.main`, scikit-learn ni pandas, no escribe nada en stderr y da la ruta por defecto. Se comprobó que falla si `registro.config` importa `registro.app` |
| `test_log_path_por_defecto_y_vacio` | Sin `LOG_PATH`, o con `LOG_PATH` vacía, se usa `fase-4/registros/predicciones.csv` |
| `test_log_path_relativo_se_resuelve_desde_la_raiz` | Una ruta relativa se resuelve desde la raíz del repo, y una absoluta se respeta |

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

- `RegistroCSV`, `registro/config.py` y `registro/app.py`, con el registro de cada intento a `/predict`.
- 14 pruebas en `tests/`.

**Formato del registro, para el script de monitoreo (Paso 4)**

- **Ubicar el registro con `registro.config`:** `from registro.config import log_path_from_env`. Devuelve `LOG_PATH` resuelta desde la raíz del repositorio, o `fase-4/registros/predicciones.csv` por defecto. Importarlo no crea la app ni carga el modelo. **No importes `registro.app`**, porque ese sí crea la app y carga el modelo.
- **Columnas con `registro.csv_logger.COLUMNS`:** `("fecha_hora", "estado_http", "version", "prediccion")`, en ese orden. Ese módulo tampoco importa fase-3 ni scikit-learn.
- Archivo en UTF-8, con coma, fin de línea `\n` y encabezado en la primera línea.
- `fecha_hora`: `AAAA-MM-DDTHH:MM:SS+00:00`, siempre UTC. `pd.to_datetime(..., utc=True)` y `datetime.fromisoformat` lo leen directamente.
- `estado_http`: entero. **Total de solicitudes** = número de filas sin el encabezado. **Fallidas** = filas con `estado_http >= 400`, es decir 4xx y 5xx. Porcentaje = fallidas / total × 100.
- **Cuenta las fallidas solo con `estado_http >= 400`, sin usar `version` ni `prediccion`.** Esas columnas pueden estar vacías por motivos distintos: un 500 lleva versión pero no predicción, y un 400, 422 o 503 no lleva ninguna de las dos. En pandas, `pd.read_csv` lee los vacíos como `NaN`; con `dtype=str` y `keep_default_na=False`, como `""`.
- **Solo se registran los POST que llegan a `/predict`.** Un `GET /predict` responde 405 y no deja fila, y `/health` tampoco escribe. El total es el de los intentos de predicción, no el de todas las solicitudes al servidor.
- **Las filas pueden no estar ordenadas por `fecha_hora`.** La hora es la de llegada, pero la fila se escribe al responder, así que con solicitudes simultáneas una más reciente puede quedar antes. No afecta el total ni el porcentaje; si el script filtra por intervalos de tiempo, debe ordenar o filtrar por `fecha_hora` y no suponer el orden del archivo.
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

`monitoreo.py` lee el registro y muestra el total de solicitudes a `/predict`, las fallidas (HTTP 4xx o 5xx) y su porcentaje. No modifica `fase-1/`, `fase-2/`, `fase-3/` ni el código de `registro/`. Las rutas de los comandos parten de `fase-4/`, salvo que se indique otra cosa.

### Archivos

| Archivo | Contenido |
|---|---|
| `monitoreo.py` | El script. Funciones `leer_registro`, `resumir`, `porcentaje_fallos`, `formatear_porcentaje` y `formatear_reporte`; `main` solo las orquesta |
| `tests/test_monitoreo.py` | 13 pruebas del script, con `tmp_path`, sin la API y sin red |
| `registros/muestra_predicciones.csv` | Registro del ensayo, versionado como muestra |
| `registros/muestra_salida_monitoreo.txt` | Salida del script sobre ese registro |

### Cómo se usa

PowerShell:

```powershell
cd fase-4
python monitoreo.py                     # LOG_PATH, o fase-4/registros/predicciones.csv
python monitoreo.py --registro registros/muestra_predicciones.csv
python monitoreo.py --help

# Con LOG_PATH, igual que el servidor
$env:LOG_PATH = "fase-4/registros/muestra_predicciones.csv"
python monitoreo.py
Remove-Item Env:LOG_PATH
```

Bash:

```bash
cd fase-4
python monitoreo.py
python monitoreo.py --registro registros/muestra_predicciones.csv
python monitoreo.py --help

LOG_PATH=fase-4/registros/muestra_predicciones.csv python monitoreo.py
```

- **Sin `--registro`** usa `registro.config.log_path_from_env()`, la misma ruta que el servidor: `LOG_PATH` resuelta desde la raíz del repositorio, o `fase-4/registros/predicciones.csv`. **Con `--registro`**, una ruta relativa se toma desde la carpeta actual, como en cualquier programa de línea de comandos.
- Solo usa la biblioteca estándar (`csv`). Importa `registro.config` y `registro.csv_logger.COLUMNS`, que no cargan el modelo; no importa `registro.app`.

### Reglas de conteo

- **Total de solicitudes:** filas sin el encabezado. Las líneas en blanco se ignoran.
- **Fallidas:** filas con `estado_http >= 400`. No se usan `version` ni `prediccion`.
- **Porcentaje:** fallidas / total × 100, con un decimal y coma decimal: `33,3 %`. Con total 0 se muestra `sin solicitudes`.
- No se supone que las filas estén ordenadas por `fecha_hora`: el conteo no depende del orden.
- Además del resultado pedido, se muestra un desglose por código HTTP, marcando los fallidos, y por versión. Las filas sin versión (400, 422 y 503) aparecen como `(sin version)`.
- El archivo se lee con `utf-8-sig`, que acepta el CSV del registro y también uno guardado con BOM, por ejemplo desde Excel.

### Casos especiales

| Caso | Resultado | Código de salida |
|---|---|---|
| Solo el encabezado | Total 0 y `sin solicitudes` | 0 |
| El archivo no existe | Total 0, `sin solicitudes` y un aviso de que el archivo no existe. No lo crea | 0 |
| Archivo de 0 bytes, sin encabezado | Total 0, `sin solicitudes` y un aviso de que está vacío | 0 |
| Encabezado distinto de `COLUMNS` | Error con el encabezado esperado y el encontrado, en stderr, sin traceback | 1 |
| `estado_http` que no es entero, o una fila sin 4 columnas | Error con el número de línea, en stderr, sin traceback | 1 |
| El archivo no se puede leer (permisos, codificación) | Error en stderr, sin traceback | 1 |

Los mensajes del script van sin tildes, como los del resto del código, para que se vean bien en cualquier consola de Windows.

### Pruebas

Desde `fase-4/`, igual en PowerShell y en Bash:

```text
python -m pytest -v
```

Resultado en Windows ARM64, con Python 3.12.10: **27 pruebas aprobadas en 0,80 s** (14 del registro y 13 del script), sin advertencias.

| Prueba | Verifica |
|---|---|
| `test_solo_encabezado_da_cero_y_sin_solicitudes` | Total 0, 0 fallidas y `sin solicitudes` |
| `test_archivo_inexistente_da_cero_sin_solicitudes_y_aviso` | Total 0, `sin solicitudes`, el aviso, y el archivo no se crea |
| `test_archivo_vacio_da_cero_y_sin_solicitudes` | Un archivo de 0 bytes da total 0 y `sin solicitudes` |
| `test_dos_validas_y_una_rechazada_dan_33_3` | 200, 200 y 422: 3 solicitudes, 1 fallida y `33,3 %` |
| `test_solo_200_da_cero_por_ciento` | `0,0 %` |
| `test_500_y_503_cuentan_como_fallidos` | 200, 500, 503 y 200: 2 fallidas y `50,0 %` |
| `test_filas_desordenadas_dan_el_mismo_resultado` | Las mismas filas en otro orden dan el mismo total, fallidas y desglose |
| `test_estado_http_no_entero_da_error` | Código distinto de cero, nada en stdout y el error en stderr |
| `test_porcentaje_con_un_decimal_y_coma` | `33,3 %`, `66,7 %`, `100,0 %` y `sin solicitudes` |
| `test_encabezado_invalido_da_error_por_linea_de_comandos` | Con `subprocess` y `sys.executable`: código distinto de cero, mensaje claro y sin traceback |
| `test_help_funciona_por_linea_de_comandos` | `--help` sale con 0 y menciona `--registro` |
| `test_sin_registro_usa_log_path_o_el_valor_por_defecto` (2 casos) | Con `LOG_PATH` vacía o con espacios, la ruta es `fase-4/registros/predicciones.csv` |

### Ensayo

`python -m uvicorn registro.app:app --port 8040` desde `fase-4/`, con `MODEL_VERSION=v1` y `LOG_PATH=fase-4/registros/muestra_predicciones.csv`, un archivo que no existía. `/health` respondió 200 con `version: v1` y `modelo_disponible: true`. Luego se enviaron tres `POST /predict`:

| # | Película | Entrada | Respuesta |
|---|---|---|---|
| 1 | Toy Story 2 (id 863 de TMDB; `vote_average` real 7.3), la misma del cliente de fase-3 | `budget` 90000000, `runtime` 92, `release_year` 1999, `es_secuela` 1, `genero_principal` Animation, `original_language` en | 200: `{"prediccion": 6.2250117576267305, "version": "v1"}` |
| 2 | The Matrix (id 603; `vote_average` real 7.9, 9079 votos) | `budget` 63000000, `runtime` 136, `release_year` 1999, `es_secuela` 0, `genero_principal` Action, `original_language` en | 200: `{"prediccion": 6.454525153977101, "version": "v1"}` |
| 3 | The Matrix sin `runtime` | Las mismas predictoras de la #2, sin la clave `runtime` | 422: `{"error": "Entrada invalida", "detalle": [{"campo": "runtime", "mensaje": "Campo obligatorio ausente; si el dato falta, envia null"}]}` |

- **Origen de The Matrix:** sus 6 predictoras se derivaron de `movies_metadata.csv` con las funciones de fase-2, en el mismo orden que el entrenamiento: `data.read_raw_csv`, `data.clean_data`, `features.add_sequel_feature`, `data.apply_filters` y `features.derive_features`. Con las mismas funciones se confirmaron los valores de Toy Story 2. No se usaron los valores ilustrativos de `ejemplo_prediccion.csv`.
- **Comprobación:** `python predict.py --model models/v1` de fase-2 da la misma predicción para The Matrix, 6.454525153977101. Las dos películas pueden haber quedado en el entrenamiento de `v1`, así que las predicciones no son una evaluación del modelo.
- **Causa del rechazo:** en la #3 falta la clave `runtime`. El contrato la admite con valor `null` cuando el dato no se conoce, pero la clave es obligatoria, así que la API responde 422 sin llegar al modelo. Por eso la fila no tiene versión ni predicción.

Registro resultante (`registros/muestra_predicciones.csv`):

```text
fecha_hora,estado_http,version,prediccion
2026-11-22T22:56:29+00:00,200,v1,6.2250117576267305
2026-11-22T22:56:29+00:00,200,v1,6.454525153977101
2026-11-22T22:56:29+00:00,422,,
```

Salida de `python monitoreo.py --registro registros/muestra_predicciones.csv` (`registros/muestra_salida_monitoreo.txt`); con `LOG_PATH` apuntando al mismo archivo y sin `--registro` sale igual:

```text
Registro: fase-4/registros/muestra_predicciones.csv
Total de solicitudes: 3
Solicitudes fallidas (4xx o 5xx): 1
Porcentaje de fallos: 33,3 %

Por codigo HTTP:
  200: 2
  422: 1 (fallida)

Por version:
  (sin version): 1
  v1: 2
```

**Comparación con las filas:** el CSV tiene 3 filas sin el encabezado, con códigos 200, 200 y 422. Solo el 422 es >= 400, así que hay 1 fallida de 3: 33,3 %. Coincide con la salida del script y con el ejemplo de la especificación. Las predicciones del CSV son las mismas de las respuestas, y el log de uvicorn muestra los mismos tres códigos.

Las dos muestras quedan en el repositorio: `.gitignore` solo excluye `fase-4/registros/predicciones.csv`, que sigue ignorado (`git check-ignore`).

### Para el siguiente relevo

Para quien haga Docker y el README de fase-4 (Paso 6).

**Qué quedó listo**

- Registro (Paso 2) y script de monitoreo (Paso 4), con 27 pruebas en `tests/`.
- Muestras del ensayo en `registros/`: `muestra_predicciones.csv` y `muestra_salida_monitoreo.txt`. Los resultados están en "Ensayo", arriba.
- Fase-3 ya tiene su Paso 2 (`/train`, pruebas y cliente) en `develop`, así que la nota del Paso 2 sobre eso ya no aplica.

**Comandos para el README**

- Inicio del servidor, desde `fase-4/`: `python -m uvicorn registro.app:app --port 8000`. Variables: `MODEL_VERSION` (por defecto `v1`) y `LOG_PATH` (por defecto `fase-4/registros/predicciones.csv`).
- Monitoreo, desde `fase-4/`: `python monitoreo.py`, o `python monitoreo.py --registro <archivo>`. Los comandos de PowerShell y Bash están en "Cómo se usa".
- Pruebas, desde `fase-4/`: `python -m pytest -v`.

**Docker**

- **Montar `fase-4/registros/`** desde el equipo, con escritura. Si no se monta, el registro queda dentro del contenedor y se pierde al eliminarlo. El script se puede correr en el equipo sobre esa carpeta montada, o dentro del contenedor con `python monitoreo.py`.
- Sigue aplicando lo anotado en el Paso 2: conservar la estructura `fase-2/`, `fase-3/` y `fase-4/` en la imagen, un `.dockerignore`, un solo worker de uvicorn y la nota sobre archivos de root en Linux.
- Si se quiere usar `/train` dentro del contenedor, `fase-2/models` también se monta con escritura, como anotó fase-3.

**Versiones para documentar**

- **`v1` es la activa** (valor por defecto de `MODEL_VERSION`) **y `v2` la anterior.** Las dos están en `fase-2/models`.
- Para pasar de una a otra se cambia `MODEL_VERSION` y se reinicia el servidor; no hay recarga en caliente. Las filas del registro guardan la versión con que se predijo, así que el desglose por versión del script muestra cuántas salieron de cada una.
- **La versión creada al probar `/train`** (`v3`, o el siguiente `vN` libre) también se puede usar de la misma forma, con `MODEL_VERSION=v3` y reinicio. Fase-3 indica que esa carpeta no se sube al repositorio.

**Falta**

- La **política de reentrenamiento** en el README de fase-4.
- La sección **«Reporte»** del README, con el ensayo de arriba: las películas enviadas, las respuestas, la causa del rechazo, el registro y la salida del script.
- El Dockerfile y su prueba.

## Paso 6 – Docker y README

Pendiente.

## Decisiones del equipo

### Formato de fecha_hora

`fecha_hora` se escribe en ISO 8601, en UTC, truncada a segundos y con la zona explícita: `2026-11-06T10:02:00+00:00`. El ejemplo de la especificación no lleva zona; se agregó `+00:00` para que no haya dudas de que es UTC.

### Versión en los 500

Un 500 siempre se registra con versión, aunque en el caso raro de un error inesperado antes de usar el modelo no se haya usado. Distinguirlos exigiría modificar fase-3.
