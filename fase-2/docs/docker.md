# Docker

Esta guía construye la imagen de la aplicación y ejecuta `train.py` y `predict.py` en contenedores. La imagen solo trae el código y sus dependencias: los datos y los modelos se montan desde tu equipo, y lo que escribe el contenedor queda en tus carpetas.

## Qué se verificó

| Dato | Valor |
|---|---|
| Equipo | Windows 11 ARM64, con Docker Desktop y motor `linux/arm64` (Docker 29.9.2) |
| Terminales | Windows PowerShell 5.1 y Git Bash (GNU bash 5.3): construir, entrenar, predecir, comparar y comprobar el error corrió en las dos. La limpieza final solo se ejecutó en Git Bash |
| Imagen | `modelos-fase2:1.0`, sobre `python:3.12.10-slim`, plataforma `linux/arm64` |
| Tamaño de la imagen | 720 MB en disco (`DISK USAGE`) y 153 MB comprimida (`CONTENT SIZE`) |
| Contenido de `/app` | `predict.py`, `train.py`, `requirements.txt` y `src/`, con 12 archivos en total. Sin CSV, modelos, credenciales ni `__pycache__` |

Los comandos no se probaron en Linux, macOS ni equipos x86-64.

## Antes de empezar

- Docker Desktop debe estar en marcha: `docker info` tiene que mostrar la sección `Server`.
- `movies_metadata.csv` debe estar en `data/` ([instrucciones](../data/README.md)).
- Los comandos se ejecutan desde `fase-2/`.
- Las rutas de `-v` van entre comillas, porque la ruta del proyecto puede tener espacios.
- `python predict.py` y `python -c` sin `docker run` usan tu Python local, con `requirements.txt` instalado.

Sobre los montajes:

| Comando | `data/` | `models/` | `outputs/` |
|---|---|---|---|
| Entrenar | Solo lectura | Escritura | Sin montar |
| Predecir | Solo lectura | Solo lectura | Escritura |

## PowerShell

```powershell
# Construir la imagen y ver su tamano
docker build -t modelos-fase2:1.0 .
docker images modelos-fase2:1.0

# Ver la ayuda (CMD por defecto) y comprobar que /app no trae datos ni modelos
docker run --rm modelos-fase2:1.0
docker run --rm modelos-fase2:1.0 ls -a /app

# Entrenar una version
$commit = git rev-parse HEAD
docker run --rm `
  -e "GIT_COMMIT=$commit" `
  -v "${PWD}/data:/app/data:ro" `
  -v "${PWD}/models:/app/models" `
  modelos-fase2:1.0 `
  python train.py --data data/movies_metadata.csv --version v-docker

# Predecir con la version nueva
docker run --rm `
  -v "${PWD}/models:/app/models:ro" `
  -v "${PWD}/data:/app/data:ro" `
  -v "${PWD}/outputs:/app/outputs" `
  modelos-fase2:1.0 `
  python predict.py --model models/v-docker --input data/ejemplo_prediccion.csv --output outputs/predicciones_docker_v-docker.csv

# Predecir con v1
docker run --rm `
  -v "${PWD}/models:/app/models:ro" `
  -v "${PWD}/data:/app/data:ro" `
  -v "${PWD}/outputs:/app/outputs" `
  modelos-fase2:1.0 `
  python predict.py --model models/v1 --input data/ejemplo_prediccion.csv --output outputs/predicciones_docker_v1.csv

# Comparar v1 en el contenedor con v1 en local
python predict.py --model models\v1 --input data\ejemplo_prediccion.csv --output outputs\predicciones_local_v1.csv
python -c "import numpy as np, pandas as pd; a = pd.read_csv('outputs/predicciones_docker_v1.csv')['prediccion'].to_numpy(); b = pd.read_csv('outputs/predicciones_local_v1.csv')['prediccion'].to_numpy(); print('filas', len(a), len(b)); print('allclose', np.allclose(a, b)); print('diferencia maxima', np.abs(a - b).max()); print('identicas', int((a == b).sum()), 'de', len(a))"

# Comprobar en tu equipo lo que dejaron los contenedores
Get-ChildItem models\v-docker
Get-ChildItem outputs -Filter *.csv
python -c "import json; m = json.load(open('models/v-docker/metadata.json', encoding='utf-8')); print(m['git_commit'])"

# Comprobar un error: a la entrada le falta runtime
python -c "import pandas as pd; pd.read_csv('data/ejemplo_prediccion.csv').drop(columns='runtime').to_csv('outputs/sin_runtime.csv', index=False)"
docker run --rm `
  -v "${PWD}/models:/app/models:ro" `
  -v "${PWD}/outputs:/app/outputs" `
  modelos-fase2:1.0 `
  python predict.py --model models/v1 --input outputs/sin_runtime.csv --output outputs/no_debe_existir.csv
$LASTEXITCODE
Test-Path outputs\no_debe_existir.csv

# Limpiar: v-docker no se sube. Esto borra todos los CSV de outputs/
# Estas dos lineas no se ejecutaron en la verificacion: la limpieza se hizo en Git Bash
Remove-Item -Recurse models\v-docker
Remove-Item outputs\*.csv
```

## Bash

`MSYS_NO_PATHCONV=1` es necesario en Git Bash. Sin esa variable, `/app/data` se convierte en `C:/Program Files/Git/app/data` y el contenedor no encuentra la carpeta.

```bash
export MSYS_NO_PATHCONV=1

# Construir la imagen y ver su tamano
docker build -t modelos-fase2:1.0 .
docker images modelos-fase2:1.0

# Ver la ayuda (CMD por defecto) y comprobar que /app no trae datos ni modelos
docker run --rm modelos-fase2:1.0
docker run --rm modelos-fase2:1.0 ls -a /app

# Entrenar una version
docker run --rm \
  -e GIT_COMMIT="$(git rev-parse HEAD)" \
  -v "$(pwd)/data:/app/data:ro" \
  -v "$(pwd)/models:/app/models" \
  modelos-fase2:1.0 \
  python train.py --data data/movies_metadata.csv --version v-docker

# Predecir con la version nueva
docker run --rm \
  -v "$(pwd)/models:/app/models:ro" \
  -v "$(pwd)/data:/app/data:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  modelos-fase2:1.0 \
  python predict.py --model models/v-docker --input data/ejemplo_prediccion.csv --output outputs/predicciones_docker_v-docker.csv

# Predecir con v1
docker run --rm \
  -v "$(pwd)/models:/app/models:ro" \
  -v "$(pwd)/data:/app/data:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  modelos-fase2:1.0 \
  python predict.py --model models/v1 --input data/ejemplo_prediccion.csv --output outputs/predicciones_docker_v1.csv

# Comparar v1 en el contenedor con v1 en local
python predict.py --model models/v1 --input data/ejemplo_prediccion.csv --output outputs/predicciones_local_v1.csv
python -c "import numpy as np, pandas as pd; a = pd.read_csv('outputs/predicciones_docker_v1.csv')['prediccion'].to_numpy(); b = pd.read_csv('outputs/predicciones_local_v1.csv')['prediccion'].to_numpy(); print('filas', len(a), len(b)); print('allclose', np.allclose(a, b)); print('diferencia maxima', np.abs(a - b).max()); print('identicas', int((a == b).sum()), 'de', len(a))"

# Comprobar en tu equipo lo que dejaron los contenedores
ls models/v-docker
ls outputs/*.csv
python -c "import json; m = json.load(open('models/v-docker/metadata.json', encoding='utf-8')); print(m['git_commit'])"

# Comprobar un error: a la entrada le falta runtime
python -c "import pandas as pd; pd.read_csv('data/ejemplo_prediccion.csv').drop(columns='runtime').to_csv('outputs/sin_runtime.csv', index=False)"
docker run --rm \
  -v "$(pwd)/models:/app/models:ro" \
  -v "$(pwd)/outputs:/app/outputs" \
  modelos-fase2:1.0 \
  python predict.py --model models/v1 --input outputs/sin_runtime.csv --output outputs/no_debe_existir.csv
echo $?
ls outputs/no_debe_existir.csv

# Limpiar: v-docker no se sube. Esto borra todos los CSV de outputs/
rm -r models/v-docker
rm outputs/*.csv
```

## Resultados

### Entrenamiento

`v-docker` usó los valores por defecto de `train.py`, igual que `v1`, y dio CV RMSE 0,7946 y prueba RMSE 0,8007, con 17.335 filas de entrenamiento y 4.321 de prueba.

Su `metrics.json` es idéntico byte a byte al de `v1`. En `metadata.json` solo difieren `version`, `fecha` y `git_commit`.

### Portabilidad

`v1` se entrenó en Windows ARM64. Se comparó su predicción en el contenedor (Linux ARM64) con la de `predict.py` en local, sobre las 12 filas de `data/ejemplo_prediccion.csv`.

| Medida | Resultado |
|---|---|
| `np.allclose` | `True` |
| Diferencia máxima | 0,0 |
| Predicciones idénticas | 12 de 12 |
| Archivos CSV | Idénticos byte a byte |

El resultado fue el mismo en PowerShell y en Git Bash. **Alcance:** las dos plataformas son ARM64. Esto no prueba el resultado en un equipo x86-64, donde Docker usaría la imagen `linux/amd64`.

### Persistencia y errores

- Después de eliminar cada contenedor, en el equipo seguían `models/v-docker`, con sus tres archivos, y los CSV de `outputs/`. No quedó ningún contenedor de esta imagen.
- `metadata.json` registró el commit completo que se pasó en `GIT_COMMIT`. La imagen no trae git, así que ese es el valor que usa.
- Con la entrada sin `runtime`, `predict.py` mostró `Error: Faltan columnas requeridas: runtime`, terminó con código 1 y no creó `outputs/no_debe_existir.csv`.
- Con `:ro`, escribir en `/app/models` o `/app/data` falla con `Read-only file system`.

## Solución de problemas

**`docker info` no muestra `Server`, o sale `failed to connect to the docker API`.** Docker Desktop no está en marcha. Ábrelo y espera a que el motor termine de iniciar.

**Docker Desktop falla con `Wsl/Service/CreateInstance/ERROR_TIMEOUT`.** Esto ocurrió en el equipo de verificación y se resolvió reiniciando WSL y Docker Desktop. Cierra Docker Desktop, reinicia WSL y vuelve a abrirlo. Reiniciar WSL detiene todas sus distribuciones y los contenedores en ejecución. El arreglo lo reportó el equipo: estos comandos no se ejecutaron durante esta verificación.

PowerShell:

```powershell
wsl --shutdown
```

Bash:

```bash
wsl.exe --shutdown
```

**`ls: cannot access 'C:/Program Files/Git/app/data'`.** Falta `export MSYS_NO_PATHCONV=1` en Git Bash.

**`invalid reference format: repository name (...) must be lowercase`.** En Git Bash, a `-v` le faltan las comillas y la ruta con espacios se parte en dos.
