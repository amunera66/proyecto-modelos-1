# Comandos de prueba con curl

Los mismos pasos de `cliente.py`, con la API corriendo en `http://localhost:8000`. La entrada es Toy Story 2 (id 863 en `movies_metadata.csv`, `vote_average` real 7.3); sus predictoras se derivaron con las funciones de fase-2 (ver el docstring de `cliente.py`).

## Bash

```bash
curl -s http://localhost:8000/health

curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"budget": 90000000, "runtime": 92, "release_year": 1999, "es_secuela": 1, "genero_principal": "Animation", "original_language": "en"}'

# Entrenar una version nueva (no cambia la que sirve la API)
curl -s -X POST http://localhost:8000/train
```

## PowerShell

Con `Invoke-RestMethod`:

```powershell
Invoke-RestMethod http://localhost:8000/health

$cuerpo = '{"budget": 90000000, "runtime": 92, "release_year": 1999, "es_secuela": 1, "genero_principal": "Animation", "original_language": "en"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType "application/json" -Body $cuerpo

# Entrenar una version nueva (no cambia la que sirve la API)
Invoke-RestMethod -Method Post -Uri http://localhost:8000/train
```

Con `curl.exe` (en PowerShell, `curl` a secas es un alias de `Invoke-WebRequest`). El cuerpo se pasa por la entrada estándar con `--data-binary "@-"`, porque Windows PowerShell 5.1 quita las comillas dobles de un JSON pasado como argumento:

```powershell
curl.exe -s http://localhost:8000/health

$cuerpo = '{"budget": 90000000, "runtime": 92, "release_year": 1999, "es_secuela": 1, "genero_principal": "Animation", "original_language": "en"}'
$cuerpo | curl.exe -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" --data-binary "@-"

curl.exe -s -X POST http://localhost:8000/train
```

Con `v1`, la predicción esperada se documenta en `docs/decisiones.md` (Paso 2).
