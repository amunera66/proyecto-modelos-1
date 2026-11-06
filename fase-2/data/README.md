# Datos

La aplicación usa `movies_metadata.csv` de [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) (Rounak Banik, Kaggle). El archivo no se sube al repositorio y debe quedar en esta ruta:

```text
fase-2/data/movies_metadata.csv
```

## Descargar el archivo

Los comandos se ejecutan desde la carpeta `fase-2/`.

### A mano

1. Entra a la [página del dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) y descárgalo.
2. Descomprímelo y copia solo `movies_metadata.csv` en `fase-2/data/`.

### Con la CLI de Kaggle

La CLI no hace parte de `fase-2/requirements.txt`, porque la aplicación no la necesita. Hay que instalarla aparte con `pip install kaggle` y tener configurado un token de la API de Kaggle. El token nunca se sube al repositorio.

PowerShell:

```powershell
kaggle datasets download -d rounakbanik/the-movies-dataset -f movies_metadata.csv -p data
# Solo si quedó comprimido:
Expand-Archive data\movies_metadata.csv.zip -DestinationPath data
Remove-Item data\movies_metadata.csv.zip
```

Bash:

```bash
kaggle datasets download -d rounakbanik/the-movies-dataset -f movies_metadata.csv -p data
# Solo si quedó comprimido:
unzip data/movies_metadata.csv.zip -d data
rm data/movies_metadata.csv.zip
```

## Verificar el archivo

Este es el archivo con el que se reprodujeron los resultados de la Fase 1:

| Dato | Valor de referencia |
|---|---|
| Tamaño | 34.445.126 bytes |
| SHA-256 | `37ec322786b136a24604564e55160be75f8937546f11cb1a990076971fa895fd` |

PowerShell (muestra el hash en mayúsculas; la comparación con `-eq` no distingue mayúsculas de minúsculas):

```powershell
(Get-Item data\movies_metadata.csv).Length
(Get-FileHash data\movies_metadata.csv -Algorithm SHA256).Hash -eq "37ec322786b136a24604564e55160be75f8937546f11cb1a990076971fa895fd"
```

Bash:

```bash
wc -c < data/movies_metadata.csv
sha256sum data/movies_metadata.csv
```

Si el hash no coincide, el archivo es otra versión del dataset y las métricas pueden cambiar frente a las documentadas.
