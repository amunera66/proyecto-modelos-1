# Fase 4: registro de predicciones y monitoreo básico

Proyecto integrador de Modelos y Simulación de Sistemas I (Universidad de Antioquia).

**Integrantes:** Alejandro Múnera Ramírez, Juan Esteban González Duque y Miguel Ángel Altamiranda.

## Qué agrega sobre la Fase 3

La API de la [Fase 3](../fase-3/README.md) sigue igual: `/health`, `/predict` y `/train`. La Fase 4 le agrega dos cosas:

1. **Un registro de predicciones.** Cada `POST /predict`, también los rechazados, deja una fila en un CSV. No copia la API: crea la app de fase-3 con `create_app(observer=RegistroCSV(LOG_PATH))`, y fase-3 llama a ese observador una vez por solicitud. `uvicorn api.app:app`, desde `fase-3/`, sigue sin registrar nada.
2. **Un script de monitoreo** (`monitoreo.py`) que lee el registro y muestra el total de solicitudes, las fallidas y su porcentaje.

Las decisiones y su evidencia están en [docs/decisiones.md](docs/decisiones.md).

### Qué se entrega

| Entregable | Archivo |
|---|---|
| Código del registro | `registro/`: `csv_logger.py` (el observador), `config.py` (`LOG_PATH`) y `app.py` (la app con el registro) |
| Script de monitoreo | `monitoreo.py` |
| Muestra del registro | `registros/muestra_predicciones.csv` y la salida del script sobre ella, `registros/muestra_salida_monitoreo.txt` |
| Pruebas | `tests/` (27 pruebas) |
| Docker | `Dockerfile` y `Dockerfile.dockerignore` |

## Entorno local

Python 3.12.10. Los comandos van desde `fase-4/`, salvo los de Docker, que van desde la raíz del repositorio. `requirements.txt` tiene las mismas versiones exactas de fase-3, sin dependencias nuevas.

PowerShell:

```powershell
cd fase-4
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación del entorno, llama directamente a su Python, también en los demás comandos de esta guía:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest
```

O permite los scripts solo en esa ventana y vuelve a activar el entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Bash:

```bash
cd fase-4
python -m venv .venv
source .venv/Scripts/activate   # Git Bash en Windows
# source .venv/bin/activate     # Linux o macOS
python -m pip install -r requirements.txt
```

Los modelos `v1` y `v2` vienen en el repositorio (`fase-2/models`). `/predict` funciona sin el CSV de datos; solo `/train` lo necesita (ver [fase-2/data/README.md](../fase-2/data/README.md)).

## Ejecución local

Desde `fase-4/`. El comando es igual en PowerShell y en Bash:

```text
python -m uvicorn registro.app:app --port 8000
```

| Variable | Por defecto | Uso |
|---|---|---|
| `MODEL_VERSION` | `v1` | Versión que carga la API al iniciar |
| `LOG_PATH` | `fase-4/registros/predicciones.csv` | Archivo del registro. Una ruta relativa se toma desde la raíz del repositorio |
| `MODELS_DIR`, `DATA_PATH`, `GIT_COMMIT` | Los de fase-3 | Ver el [README de fase-3](../fase-3/README.md#variables-de-entorno) |

**Registro persistente:** `fase-4/registros/predicciones.csv`. Se abre en modo agregar, así que conserva el historial entre ejecuciones. Git lo ignora; las muestras de la misma carpeta sí se versionan.

## Ejecución con Docker

La imagen `modelos-fase4:1.0` usa `python:3.12.10-slim` y solo trae el código (`fase-2/src`, `fase-3/api`, `fase-4/registro` y `fase-4/monitoreo.py`) y las dependencias: 23 archivos en `/app`. Pesa 746 MB en disco y 159 MB comprimida. Los datos, los modelos y el registro se montan desde tu equipo.

- **Se construye desde la raíz del repositorio**, porque necesita `fase-2/src` y `fase-3/api`. `fase-4/Dockerfile.dockerignore` no deja entrar datos, modelos, registros, pruebas, `.venv/`, `.git/` ni credenciales.
- **Montajes:**

  | Carpeta del equipo | En el contenedor | Modo | Para qué |
  |---|---|---|---|
  | `fase-2/data` | `/app/fase-2/data` | Solo lectura (`:ro`) | CSV de `/train` |
  | `fase-2/models` | `/app/fase-2/models` | Escritura | Versiones del modelo; `/train` guarda ahí las nuevas |
  | `fase-4/registros` | `/app/fase-4/registros` | Escritura | **Registro persistente**, `fase-4/registros/predicciones.csv` |

  Si no se monta `fase-4/registros`, el registro queda dentro del contenedor y se pierde al eliminarlo.
- **Registro en otro archivo:** agrega `-e LOG_PATH=...` al `docker run`, con una ruta relativa a la raíz dentro de `fase-4/registros/`, para que quede en el montaje. Por ejemplo, en PowerShell `` -e "LOG_PATH=fase-4/registros/prueba.csv" ` `` y en Bash `-e LOG_PATH=fase-4/registros/prueba.csv \`. Para leerlo: `docker exec api-fase4 python monitoreo.py --registro registros/prueba.csv`. Git solo ignora `predicciones.csv`: borra el archivo de prueba al terminar.
- **Puerto:** uvicorn escucha en `0.0.0.0:8000`, con un solo worker, y se publica con `-p 8000:8000`.

**Dónde se verificó:** Windows 11 ARM64, Docker Desktop (Docker 29.9.2, motor `linux/arm64`), en Windows PowerShell 5.1 y en Git Bash (GNU bash 5.3), desde una copia nueva del repositorio. Los dos bloques corrieron completos.

PowerShell, desde la raíz:

```powershell
docker build -f fase-4/Dockerfile -t modelos-fase4:1.0 .

$commit = git rev-parse HEAD
docker run -d --name api-fase4 `
  -p 8000:8000 `
  -e "GIT_COMMIT=$commit" `
  -e "MODEL_VERSION=v1" `
  -v "${PWD}/fase-2/data:/app/fase-2/data:ro" `
  -v "${PWD}/fase-2/models:/app/fase-2/models" `
  -v "${PWD}/fase-4/registros:/app/fase-4/registros" `
  modelos-fase4:1.0
```

Bash, desde la raíz (`MSYS_NO_PATHCONV=1` es necesario en Git Bash; sin esa variable, `/app/...` se convierte en una ruta de Windows):

```bash
export MSYS_NO_PATHCONV=1
docker build -f fase-4/Dockerfile -t modelos-fase4:1.0 .

docker run -d --name api-fase4 \
  -p 8000:8000 \
  -e GIT_COMMIT="$(git rev-parse HEAD)" \
  -e MODEL_VERSION=v1 \
  -v "$(pwd)/fase-2/data:/app/fase-2/data:ro" \
  -v "$(pwd)/fase-2/models:/app/fase-2/models" \
  -v "$(pwd)/fase-4/registros:/app/fase-4/registros" \
  modelos-fase4:1.0
```

En Git Bash, `$(pwd)` debe empezar por la unidad (`/c/...`). Si el repositorio está en una carpeta que Git Bash muestra como `/tmp/...`, Docker no encuentra las carpetas, monta carpetas vacías y `/health` responde `modelo_disponible: false`. En la verificación pasó con una copia dentro de la carpeta temporal de Windows; se resolvió entrando a la carpeta por su ruta `/c/...`.

Comprobar que arrancó con `v1`:

```text
curl http://localhost:8000/health
```

```json
{"estado":"en_ejecucion","version":"v1","modelo_disponible":true,"detalle":null}
```

En PowerShell 5.1, `curl` es un alias de `Invoke-WebRequest`; usa `curl.exe` o `Invoke-RestMethod http://localhost:8000/health`.

### Detener y eliminar el contenedor

Al terminar de probar. El comando es igual en PowerShell y en Bash. El registro queda en `fase-4/registros/predicciones.csv` y las versiones que creó `/train`, en `fase-2/models`.

```text
docker rm -f api-fase4
```

## Formato del registro

CSV en UTF-8, con coma, fin de línea `\n`, encabezado en la primera línea y una fila por cada `POST /predict`:

```text
fecha_hora,estado_http,version,prediccion
2026-11-22T22:56:29+00:00,200,v1,6.2250117576267305
2026-11-22T22:56:29+00:00,422,,
```

| Columna | Contenido |
|---|---|
| `fecha_hora` | Llegada de la solicitud, ISO 8601 en UTC, a segundos |
| `estado_http` | Código HTTP de la respuesta |
| `version` | `MODEL_VERSION`, solo cuando se usó el modelo (200 y 500); vacía en 400, 422 y 503 |
| `prediccion` | Solo en los 200, igual a la respuesta; vacía en cualquier error |

`/health` y `/train` no escriben en el registro.

## Script de monitoreo

Desde `fase-4/`, igual en PowerShell y en Bash, con la API corriendo o detenida:

```text
python monitoreo.py
python monitoreo.py --registro registros/muestra_predicciones.csv
```

Sin `--registro` lee el mismo archivo que el servidor (`LOG_PATH` o `fase-4/registros/predicciones.csv`). Con `--registro`, una ruta relativa se toma desde la carpeta actual.

En Docker, sobre el registro montado:

```text
docker exec api-fase4 python monitoreo.py
```

Cuenta como **fallidas** las filas con `estado_http >= 400` y muestra el porcentaje con un decimal. Si el archivo no existe o está vacío, muestra total 0 y `sin solicitudes`. Los demás casos están en "Paso 4" de [docs/decisiones.md](docs/decisiones.md).

## Reporte

**Ejecución:** el ensayo de Juan Esteban (Paso 4), con la API local (`uvicorn registro.app:app`) y `MODEL_VERSION=v1`. Sus resultados quedaron versionados en `registros/muestra_predicciones.csv` y `registros/muestra_salida_monitoreo.txt`. Se enviaron tres `POST /predict`:

| # | Película | Respuesta de la API |
|---|---|---|
| 1 | Toy Story 2 (`budget` 90000000, `runtime` 92, `release_year` 1999, `es_secuela` 1, Animation, en) | 200: `{"prediccion": 6.2250117576267305, "version": "v1"}` |
| 2 | The Matrix (`budget` 63000000, `runtime` 136, `release_year` 1999, `es_secuela` 0, Action, en) | 200: `{"prediccion": 6.454525153977101, "version": "v1"}` |
| 3 | The Matrix sin la clave `runtime` | 422: `{"error": "Entrada invalida", "detalle": [{"campo": "runtime", "mensaje": "Campo obligatorio ausente; si el dato falta, envia null"}]}` |

Registro (`registros/muestra_predicciones.csv`):

```text
fecha_hora,estado_http,version,prediccion
2026-11-22T22:56:29+00:00,200,v1,6.2250117576267305
2026-11-22T22:56:29+00:00,200,v1,6.454525153977101
2026-11-22T22:56:29+00:00,422,,
```

Salida de `python monitoreo.py --registro registros/muestra_predicciones.csv` (`registros/muestra_salida_monitoreo.txt`):

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

**Indicadores:** 3 solicitudes; tasa de fallos 1/3 (33,3 %).

**Resultado:** la API hizo dos predicciones con `v1` y rechazó la tercera con 422 porque faltaba la clave `runtime`, sin llegar al modelo; ese rechazo era el resultado esperado de la prueba de validación. Las 3 filas del registro coinciden con la salida del script: solo el 422 es >= 400.

**En Docker dio lo mismo.** Se repitieron las tres solicitudes con la imagen de esta fase, sobre un registro vacío (`fase-4/registros/predicciones.csv`), en PowerShell y en Git Bash. Las respuestas, los códigos y las predicciones fueron idénticos; el registro siguió en el equipo después de `docker rm -f`, y `monitoreo.py`, dentro del contenedor y en local, dio la misma salida de la muestra, salvo la línea `Registro:`, que nombra el archivo leído. Ese registro de prueba se borró después.

Las dos películas pueden haber quedado en el entrenamiento de `v1`, así que las predicciones no evalúan el modelo.

## Versiones

| Versión | Estado | Dónde | Diferencia |
|---|---|---|---|
| `v1` | **Activa** (valor por defecto de `MODEL_VERSION`) | `fase-2/models/v1/` | Semilla 42 |
| `v2` | Alternativa, para volver o comparar | `fase-2/models/v2/` | Semilla 7. Según la [Fase 2](../fase-2/README.md#qué-diferencia-a-v1-de-v2), es la única diferencia: mismo CSV, mismo commit y mismos hiperparámetros; solo cambia qué películas quedan en entrenamiento y en prueba. En CV las dos rinden casi igual (RMSE 0,7946 y 0,7948) |

Cada carpeta tiene `modelo.joblib`, `metrics.json` y `metadata.json`; el identificador está en `metadata.json` (`"version"`).

**Cuál usa la API:** `GET /health` la informa en `version`, y cada fila del registro guarda la versión con que se predijo.

**Cambiar de versión:** la API carga `MODEL_VERSION` una sola vez, al iniciar; se cambia la variable y se reinicia. No hace falta cambiar código.

Local, PowerShell:

```powershell
$env:MODEL_VERSION = "v2"
python -m uvicorn registro.app:app --port 8000
# Volver a v1
Remove-Item Env:MODEL_VERSION
python -m uvicorn registro.app:app --port 8000
```

Local, Bash:

```bash
MODEL_VERSION=v2 python -m uvicorn registro.app:app --port 8000
# Volver a v1
python -m uvicorn registro.app:app --port 8000
```

En Docker se elimina el contenedor y se vuelve a crear con `MODEL_VERSION=v2`. Para volver a `v1`, se repite con `MODEL_VERSION=v1`.

PowerShell, desde la raíz:

```powershell
docker rm -f api-fase4
$commit = git rev-parse HEAD
docker run -d --name api-fase4 `
  -p 8000:8000 `
  -e "GIT_COMMIT=$commit" `
  -e "MODEL_VERSION=v2" `
  -v "${PWD}/fase-2/data:/app/fase-2/data:ro" `
  -v "${PWD}/fase-2/models:/app/fase-2/models" `
  -v "${PWD}/fase-4/registros:/app/fase-4/registros" `
  modelos-fase4:1.0
```

Bash, desde la raíz (con `export MSYS_NO_PATHCONV=1` en Git Bash):

```bash
docker rm -f api-fase4
docker run -d --name api-fase4 \
  -p 8000:8000 \
  -e GIT_COMMIT="$(git rev-parse HEAD)" \
  -e MODEL_VERSION=v2 \
  -v "$(pwd)/fase-2/data:/app/fase-2/data:ro" \
  -v "$(pwd)/fase-2/models:/app/fase-2/models" \
  -v "$(pwd)/fase-4/registros:/app/fase-4/registros" \
  modelos-fase4:1.0
```

Con `v2`, `/health` informa `"version":"v2"` y Toy Story 2 da 6.473487560963072 (con `v1`, 6.2250117576267305).

**`/train` crea versiones nuevas sin activarlas.** Guarda `v3`, `v4`, ... en `fase-2/models` y la API sigue con la versión activa hasta que se cambie `MODEL_VERSION` y se reinicie. Esas carpetas no se suben al repositorio.

## Política de reentrenamiento

El modelo se revisa cuando se actualice el dataset o cuando se acumulen al menos 500 películas nuevas con más de 10 votos, porque solo entonces se conoce su calificación real. Alejandro ejecuta `/train` para crear una versión candidata. Las dos versiones se comparan con el RMSE sobre el mismo conjunto reservado de películas nuevas que ninguna haya visto, y la candidata solo se activa, cambiando `MODEL_VERSION`, si su RMSE es menor que el de la versión activa.

## Pruebas

Desde `fase-4/`, igual en PowerShell y en Bash. No usan red ni el CSV de datos y no necesitan la API corriendo:

```text
python -m pytest
```

Resultado: **27 pruebas aprobadas**, en el entorno del equipo y en un entorno nuevo creado desde una copia del repositorio (`pip check` sin conflictos).

| Archivo en `tests/` | Pruebas | Qué verifica |
|---|---|---|
| `test_registro.py` | 11 | Dos válidas y una incompleta dejan 3 filas (200, 200, 422); filas de 400, 503 y 500 con o sin versión según el caso; el encabezado se escribe una sola vez; el historial se conserva; `/health` no escribe; fecha en UTC a segundos; escrituras simultáneas no se mezclan |
| `test_config.py` | 3 | Importar `registro.config` no carga el modelo; `LOG_PATH` por defecto, vacía y relativa |
| `test_monitoreo.py` | 13 | Archivo inexistente, vacío o solo con encabezado; 200, 200 y 422 dan `33,3 %`; 500 y 503 cuentan como fallidos; el orden de las filas no cambia el resultado; errores claros sin traceback; `--help` |

El registro de las pruebas va a una carpeta temporal y `fase-2/models` solo se lee. La lista completa está en [docs/decisiones.md](docs/decisiones.md).

## Limitaciones conocidas

- **Un solo worker.** El lock del registro evita que se mezclen filas dentro de un proceso, pero no entre varios procesos que escriban el mismo archivo.
- **Si escribir una fila falla**, por ejemplo por permisos, la respuesta de `/predict` no cambia, pero esa fila se pierde y el error queda solo en el log del servidor.
- **Un 500 siempre lleva versión**, aunque en el caso raro de un error inesperado antes de usar el modelo no se haya usado. Distinguirlos exigiría modificar fase-3.
- **Las filas pueden no estar ordenadas por `fecha_hora`:** la hora es la de llegada, pero la fila se escribe al responder. No afecta el total ni el porcentaje.
- **Portabilidad comprobada solo en ARM64.** La imagen se construyó y probó en Windows 11 ARM64 con motor `linux/arm64`. No se probó en x86-64, Linux ni macOS.
- **El log del contenedor no muestra los mensajes INFO de la API.** `docker logs` muestra los de uvicorn (cada solicitud con su código), pero no los INFO del logger de la API, como `Entrenando la version ...` de `/train`.
- Las limitaciones de la API y del modelo son las de la [Fase 3](../fase-3/README.md#limitaciones-conocidas) y la [Fase 2](../fase-2/README.md#limitaciones-conocidas).

## Uso de asistentes de IA

El equipo usó Claude (Anthropic), mediante Claude Code, como asistente para generar y revisar código, pruebas y documentación. Las decisiones de modelado, partición y corrección las tomó el equipo con base en los análisis documentados, y todos los resultados reportados se obtuvieron ejecutando el código.

## Trabajo del equipo (fases 3 y 4)

Miguel Ángel Altamiranda quedó eximido de esta entrega con el aval del profesor, y Alejandro asumió sus pasos.

Los datos salen de los merge commits y de GitHub. En GitHub, Alejandro Múnera Ramírez es `amunera66` y Juan Esteban González Duque es `Juanesgodu`.

| Fase · Paso | Contenido | Hizo | PR | Revisor |
|---|---|---|---|---|
| 3 · 1 | API base: `/health` y `/predict` | Alejandro | #14 | Juan Esteban |
| 4 · 2 | Registro de predicciones en CSV | Alejandro | #15 | Juan Esteban |
| 3 · 2 | `/train`, pruebas con pytest y cliente | Juan Esteban | #16 | Alejandro |
| 4 · 4 | Script de monitoreo y ensayo | Juan Esteban | #17 | Alejandro |
| 3 · 3 | Docker y README de fase-3 | Alejandro (`amunera66`) | #18 | Juan Esteban (`Juanesgodu`) |
| 4 · 6 | Docker y README de fase-4 | Alejandro (`amunera66`) | #19 | Juan Esteban (`Juanesgodu`) |

En los PR #14 a #17, el revisor dio la aprobación formal en GitHub (*Approve*) antes del merge e integró el PR; nunca fue quien lo abrió. En la Fase 2 algunas aprobaciones fueron comentarios publicados después del merge.
