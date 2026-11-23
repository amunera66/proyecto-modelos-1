# Fase 3: API REST de predicción

Proyecto integrador de Modelos y Simulación de Sistemas I (Universidad de Antioquia).

**Integrantes:** Alejandro Múnera Ramírez, Juan Esteban González Duque y Miguel Ángel Altamiranda.

## Qué hace

Una API con FastAPI que expone el modelo de la [Fase 2](../fase-2/README.md): predice `vote_average` (la calificación de TMDB, de 0 a 10) para una película y entrena versiones nuevas.

| Endpoint | Uso |
|---|---|
| `GET /health` | Estado de la API y versión cargada |
| `POST /predict` | Predicción para un registro JSON con las 6 predictoras |
| `POST /train` | Entrena una versión nueva con la configuración de la Fase 2 y la guarda en `fase-2/models` |

**Qué reutiliza de la Fase 2.** No copia código ni modelos: importa `fase-2/src` (carga de versiones, preparación de la entrada, predicción y entrenamiento) y usa las versiones guardadas en `fase-2/models`. El esquema de `/predict` sale del `contrato_entrada` de cada versión, y `/train` equivale a `python train.py --data <DATA_PATH> --output-dir <MODELS_DIR> --version vN`. Las decisiones y su evidencia están en [docs/decisiones.md](docs/decisiones.md).

## Requisitos y entorno local

Python 3.12.10. Los comandos se ejecutan desde `fase-3/`, salvo los de Docker, que van desde la raíz del repositorio.

PowerShell:

```powershell
cd fase-3
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
cd fase-3
python -m venv .venv
source .venv/Scripts/activate   # Git Bash en Windows
# source .venv/bin/activate     # Linux o macOS
python -m pip install -r requirements.txt
```

`requirements.txt` trae las dependencias de la Fase 2 más FastAPI, uvicorn y httpx, todas con versión exacta. En un entorno nuevo, `pip check` no reporta conflictos.

## Datos y modelos

| Qué | Dónde | Cómo se obtiene |
|---|---|---|
| `movies_metadata.csv` (solo lo usa `/train`) | `fase-2/data/movies_metadata.csv` | Se descarga de Kaggle; no se sube al repositorio. Ver [fase-2/data/README.md](../fase-2/data/README.md) |
| Versiones del modelo | `fase-2/models/<version>/` | `v1` y `v2` vienen en el repositorio. `/train` agrega `v3`, `v4`, ... |

Cada versión tiene `modelo.joblib`, `metrics.json` y `metadata.json`. `/predict` funciona sin el CSV; `/train` responde 503 si no lo encuentra.

## Ejecución local

PowerShell:

```powershell
python -m uvicorn api.app:app --port 8000
```

Bash:

```bash
python -m uvicorn api.app:app --port 8000
```

La documentación interactiva queda en `http://localhost:8000/docs`.

## Ejecución con Docker

La imagen `modelos-fase3:1.0` usa `python:3.12.10-slim` y solo trae el código (`fase-2/src` y `fase-3/api`) y las dependencias. Los datos y los modelos se montan desde tu equipo. Pesa 746 MB en disco y 159 MB comprimida.

- **Se construye desde la raíz del repositorio**, porque necesita `fase-2/src`. El punto final del comando es el contexto. `fase-3/Dockerfile.dockerignore` lo reduce a 17 archivos (unos 86 KB): no envía `dataset/`, `.venv/`, `.git/`, `fase-1/`, los CSV, los modelos ni las credenciales.
- **Puerto:** uvicorn escucha en `0.0.0.0:8000` dentro del contenedor y se publica con `-p 8000:8000`.
- **Datos:** `fase-2/data` se monta en `/app/fase-2/data` en **solo lectura** (`:ro`).
- **Modelos:** `fase-2/models` se monta en `/app/fase-2/models` **con escritura**, porque `/train` guarda ahí la versión nueva. La versión queda en tu equipo aunque se borre el contenedor.

**Dónde se verificó:** Windows 11 ARM64, Docker Desktop 4.98.0 (Docker 29.9.2, motor `linux/arm64`), en Windows PowerShell 5.1 y en Git Bash (GNU bash 5.3). Los dos bloques corrieron completos.

PowerShell, desde la raíz:

```powershell
docker build -f fase-3/Dockerfile -t modelos-fase3:1.0 .

$commit = git rev-parse HEAD
docker run -d --name api-fase3 `
  -p 8000:8000 `
  -e "GIT_COMMIT=$commit" `
  -v "${PWD}/fase-2/data:/app/fase-2/data:ro" `
  -v "${PWD}/fase-2/models:/app/fase-2/models" `
  modelos-fase3:1.0
```

Bash, desde la raíz (`MSYS_NO_PATHCONV=1` es necesario en Git Bash; sin esa variable, `/app/...` se convierte en una ruta de Windows):

```bash
export MSYS_NO_PATHCONV=1
docker build -f fase-3/Dockerfile -t modelos-fase3:1.0 .

docker run -d --name api-fase3 \
  -p 8000:8000 \
  -e GIT_COMMIT="$(git rev-parse HEAD)" \
  -v "$(pwd)/fase-2/data:/app/fase-2/data:ro" \
  -v "$(pwd)/fase-2/models:/app/fase-2/models" \
  modelos-fase3:1.0
```

### Detener y eliminar el contenedor

Al terminar de probar. El comando es igual en PowerShell y en Bash. Las versiones que creó `/train` quedan en `fase-2/models`.

```text
docker rm -f api-fase3
```

### Variables de entorno

| Variable | Por defecto | En el contenedor | Uso |
|---|---|---|---|
| `MODEL_VERSION` | `v1` | `v1` | Versión que carga la API al iniciar |
| `MODELS_DIR` | `fase-2/models` | `/app/fase-2/models` | Carpeta de versiones |
| `DATA_PATH` | `fase-2/data/movies_metadata.csv` | `/app/fase-2/data/movies_metadata.csv` | CSV crudo para `/train` |
| `GIT_COMMIT` | Sin valor | La que se pase con `-e` | Commit que `/train` guarda en `metadata.json`. La imagen no trae git: sin esta variable queda `no disponible` |

Las rutas relativas se resuelven desde la raíz del repositorio, que en la imagen es `/app`. Con los montajes de arriba no hace falta pasar `MODELS_DIR` ni `DATA_PATH`. Si montas en otras rutas, pásalas con `-e`, por ejemplo `-e "MODELS_DIR=/modelos"`. Una variable vacía equivale a su valor por defecto.

## Endpoints

Las respuestas de esta sección son las de la verificación en Docker con `v1`.

### GET /health

Responde 200 mientras la API corre, aunque no haya modelo.

```json
{"estado": "en_ejecucion", "version": "v1", "modelo_disponible": true, "detalle": null}
```

Si la versión no se pudo cargar, `modelo_disponible` es `false` y `detalle` explica el motivo y lista las versiones disponibles.

### POST /predict

Recibe un objeto JSON con las 6 predictoras. Las 6 claves son obligatorias; para un dato faltante se envía `null` donde el contrato lo permite. Los tipos son estrictos: por ejemplo, `"165000000"` (texto) en `budget` da 422. El detalle de la validación está en [docs/decisiones.md](docs/decisiones.md).

| Campo | Tipo | Admite `null` |
|---|---|---|
| `budget` | número | Sí |
| `runtime` | número | Sí |
| `release_year` | número | Sí |
| `es_secuela` | entero 0 o 1 | No |
| `genero_principal` | texto | Sí |
| `original_language` | texto | Sí |

Ejemplo con Toy Story 2 (id 863 en `movies_metadata.csv`, `vote_average` real 7.3), el registro del cliente de prueba:

```json
{"budget": 90000000, "runtime": 92, "release_year": 1999, "es_secuela": 1, "genero_principal": "Animation", "original_language": "en"}
```

Respuesta 200:

```json
{"prediccion": 6.2250117576267305, "version": "v1"}
```

La película puede haber quedado en el entrenamiento de `v1`, así que esta predicción no evalúa el modelo.

### POST /train

No recibe parámetros: un cuerpo, si llega, se ignora. Entrena con la configuración de la Fase 2 (objetivo `vote_average`, semilla 42, partición por grupos) y guarda la versión con el siguiente identificador libre: con `v1` y `v2`, `v3`. Nunca sobrescribe. En la verificación en Docker tardó 19 s.

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

La versión nueva queda en `fase-2/models/v3`, con sus tres archivos. Esa carpeta no se sube al repositorio: como `.gitignore` permite `fase-2/models/**`, aparece en `git status` y hay que borrarla después de probar.

## Errores

Ninguna respuesta de error trae el traceback; cuando aplica, queda en el log del servidor.

| Código | Endpoint | Cuándo ocurre |
|---|---|---|
| 400 | `/predict` | El cuerpo no es JSON válido o no es un objeto |
| 422 | `/predict` | Falta una clave, un tipo no es compatible, hay `null` donde no se permite o `es_secuela` no es 0 ni 1. Trae un elemento por campo |
| 503 | `/predict` | La versión de `MODEL_VERSION` no existe o no se pudo cargar |
| 503 | `/train` | No existe el archivo de `DATA_PATH` (por ejemplo, falta el montaje de los datos) |
| 500 | `/predict` | El modelo falla con una entrada que ya pasó la validación, u otro error inesperado |
| 500 | `/train` | Los datos del CSV no sirven (`Datos de entrenamiento invalidos`), no se puede escribir en `MODELS_DIR` (`No se pudo guardar la version`, por ejemplo con `:ro`) u otro error inesperado |
| 409 | `/train` | Otro proceso guardó el mismo identificador mientras se entrenaba |

Ejemplo de 422, verificado en Docker con el registro de Toy Story 2 sin `runtime`:

```json
{"error": "Entrada invalida", "detalle": [{"campo": "runtime", "mensaje": "Campo obligatorio ausente; si el dato falta, envia null"}]}
```

## Seleccionar una versión

La API carga la versión de `MODEL_VERSION` una sola vez, al iniciar. **`/train` no cambia la versión activa:** para usar una versión nueva, o volver a una anterior, se cambia `MODEL_VERSION` y se reinicia el servidor o el contenedor. Las versiones disponibles son las carpetas de `fase-2/models` con un `modelo.joblib`; si la versión pedida no existe, `/health` y el 503 de `/predict` las listan.

Local, PowerShell:

```powershell
$env:MODEL_VERSION = "v2"
python -m uvicorn api.app:app --port 8000
# Volver a v1, la versión por defecto
Remove-Item Env:MODEL_VERSION
python -m uvicorn api.app:app --port 8000
```

Local, Bash:

```bash
MODEL_VERSION=v2 python -m uvicorn api.app:app --port 8000
# Volver a v1, la versión por defecto
python -m uvicorn api.app:app --port 8000
```

En Docker se reemplaza el contenedor con `-e MODEL_VERSION=v2`. Para volver a `v1`, se repite sin esa variable. PowerShell, desde la raíz:

```powershell
docker rm -f api-fase3
$commit = git rev-parse HEAD
docker run -d --name api-fase3 `
  -p 8000:8000 `
  -e "GIT_COMMIT=$commit" `
  -e "MODEL_VERSION=v2" `
  -v "${PWD}/fase-2/data:/app/fase-2/data:ro" `
  -v "${PWD}/fase-2/models:/app/fase-2/models" `
  modelos-fase3:1.0
```

Bash, desde la raíz (con `export MSYS_NO_PATHCONV=1` en Git Bash):

```bash
docker rm -f api-fase3
docker run -d --name api-fase3 \
  -p 8000:8000 \
  -e GIT_COMMIT="$(git rev-parse HEAD)" \
  -e MODEL_VERSION=v2 \
  -v "$(pwd)/fase-2/data:/app/fase-2/data:ro" \
  -v "$(pwd)/fase-2/models:/app/fase-2/models" \
  modelos-fase3:1.0
```

Con `v2`, `/health` y `/predict` informan `"version": "v2"`, y Toy Story 2 da 6.473487560963072.

## Cliente de prueba

Con la API corriendo, en local o en Docker, desde `fase-3/` en el equipo. Solo usa la biblioteca estándar, así que no necesita el entorno de la API. Consulta `/health`, envía Toy Story 2 a `/predict` y muestra la solicitud y la respuesta. Termina con código 0 si las dos respuestas son 200.

```text
python cliente/cliente.py
python cliente/cliente.py --url http://localhost:8001
```

[cliente/comandos_curl.md](cliente/comandos_curl.md) tiene los mismos pasos, y `/train`, con `curl` en Bash y con `Invoke-RestMethod` y `curl.exe` en PowerShell.

## Pruebas

Desde `fase-3/`, con las dependencias de `requirements.txt`. Debe ser `python -m pytest`, no `pytest`, para que `api` se pueda importar. El comando es igual en PowerShell y en Bash, no usa red ni el CSV completo y no necesita la API corriendo.

```text
python -m pytest
```

Resultado: `21 passed`.

| Archivo en `tests/` | Qué verifica |
|---|---|
| `test_api.py` | `/health`; predicción con `v1` (claves `prediccion` y `version`); 422 sin `runtime`, con tipos o valores inválidos; 400 con JSON mal formado; campos extra; `runtime: null`; 503 con una versión inexistente; 500 sin traceback; versión informada según `MODEL_VERSION`; llamadas al observador de la Fase 4 |
| `test_train.py` | `/train` es síncrono; crea `v3` y luego `v4` sin tocar `v1` ni `v2` ni cambiar la versión activa; 503 sin datos; 500 con datos inválidos; numeración de versiones; dos llamadas simultáneas no repiten identificador |

Las pruebas leen `fase-2/models` sin modificarlo (comparan sus hashes al inicio y al final), y las de `/train` escriben en una carpeta temporal. La lista completa está en "Paso 2" de [docs/decisiones.md](docs/decisiones.md).

## Limitaciones conocidas

- **Si el CSV existe pero no se puede leer** (por ejemplo, por permisos), el error se informa como fallo al guardar (`No se pudo guardar la version`), no como un problema de los datos.
- **Si `DATA_PATH` o `MODELS_DIR` están fuera del repositorio**, los mensajes de error pueden mostrar rutas absolutas. En la verificación, con `MODELS_DIR=/modelos`, el error decía `No se pudo escribir en /modelos`.
- **Los errores de datos de `/train` no quedan en el log**: solo se informan en la respuesta.
- **Un solo worker.** La imagen corre uvicorn con un proceso. El lock que reserva el identificador de `/train` vale dentro de un proceso; con varios workers, dos entrenamientos simultáneos podrían elegir el mismo identificador y uno recibiría 409.
- **Portabilidad comprobada solo en ARM64.** La imagen se construyó y probó en Windows 11 ARM64 con motor `linux/arm64`. No se probó en x86-64, Linux ni macOS.
- **`git_commit` no detecta cambios sin commit,** igual que en la Fase 2.
- Las limitaciones del modelo (fecha de corte no verificada, categorías que distinguen mayúsculas, entre otras) son las de la [Fase 2](../fase-2/README.md#limitaciones-conocidas).

## Uso de asistentes de IA

El equipo usó Claude (Anthropic), mediante Claude Code, como asistente para generar y revisar código, pruebas y documentación. Las decisiones de modelado, partición y corrección las tomó el equipo con base en los análisis documentados, y todos los resultados reportados se obtuvieron ejecutando el código.

## Trabajo del equipo

Miguel Ángel Altamiranda quedó eximido de esta entrega con el aval del profesor, y Alejandro asumió sus pasos.

Los datos salen de los merge commits y de GitHub. En GitHub, Juan Esteban González Duque es `Juanesgodu` (confirmado por el equipo) y Alejandro Múnera Ramírez es `amunera66`.

| Paso | Contenido | Hizo | PR | Aprobado y integrado por |
|---|---|---|---|---|
| 1 | API base: `/health` y `/predict` | Alejandro | #14 | Juan Esteban |
| 2 | `/train`, pruebas con pytest y cliente | Juan Esteban | #16 | Alejandro |
| 3 | Docker y README | Alejandro | Este PR | Pendiente; revisor designado: Juan Esteban |

Los PR #15 y #17 son de la Fase 4.
