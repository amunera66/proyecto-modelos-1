"""Pruebas del script de monitoreo. Usan tmp_path; no levantan la API ni usan la red."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import monitoreo
from registro.csv_logger import COLUMNS

FASE4 = Path(__file__).resolve().parent.parent
HEADER = ",".join(COLUMNS)


def write_log(path: Path, rows: list[str], header: str = HEADER) -> Path:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def run_main(path: Path, capsys) -> tuple[int, str, str]:
    code = monitoreo.main(["--registro", str(path)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def run_cli(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env.pop("LOG_PATH", None)
    return subprocess.run(
        [sys.executable, "monitoreo.py", *args],
        cwd=FASE4,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )


def test_solo_encabezado_da_cero_y_sin_solicitudes(tmp_path, capsys):
    path = write_log(tmp_path / "registro.csv", [])
    code, out, _ = run_main(path, capsys)
    assert code == 0
    assert "Total de solicitudes: 0" in out
    assert "Solicitudes fallidas (4xx o 5xx): 0" in out
    assert "Porcentaje de fallos: sin solicitudes" in out


def test_archivo_inexistente_da_cero_sin_solicitudes_y_aviso(tmp_path, capsys):
    path = tmp_path / "no_existe.csv"
    code, out, _ = run_main(path, capsys)
    assert code == 0
    assert "Total de solicitudes: 0" in out
    assert "Porcentaje de fallos: sin solicitudes" in out
    assert "el archivo no existe" in out
    assert not path.exists()


def test_archivo_vacio_da_cero_y_sin_solicitudes(tmp_path, capsys):
    path = tmp_path / "vacio.csv"
    path.write_text("", encoding="utf-8")
    code, out, _ = run_main(path, capsys)
    assert code == 0
    assert "Total de solicitudes: 0" in out
    assert "Porcentaje de fallos: sin solicitudes" in out
    assert "vacio" in out


def test_dos_validas_y_una_rechazada_dan_33_3(tmp_path, capsys):
    path = write_log(
        tmp_path / "registro.csv",
        [
            "2026-11-22T19:36:10+00:00,200,v1,6.2250117576267305",
            "2026-11-22T19:36:11+00:00,200,v1,7.0",
            "2026-11-22T19:36:12+00:00,422,,",
        ],
    )
    code, out, _ = run_main(path, capsys)
    assert code == 0
    assert "Total de solicitudes: 3" in out
    assert "Solicitudes fallidas (4xx o 5xx): 1" in out
    assert "Porcentaje de fallos: 33,3 %" in out


def test_solo_200_da_cero_por_ciento(tmp_path, capsys):
    path = write_log(
        tmp_path / "registro.csv",
        ["2026-11-22T19:36:10+00:00,200,v1,6.5", "2026-11-22T19:36:11+00:00,200,v2,7.1"],
    )
    code, out, _ = run_main(path, capsys)
    assert code == 0
    assert "Total de solicitudes: 2" in out
    assert "Solicitudes fallidas (4xx o 5xx): 0" in out
    assert "Porcentaje de fallos: 0,0 %" in out


def test_500_y_503_cuentan_como_fallidos(tmp_path):
    path = write_log(
        tmp_path / "registro.csv",
        [
            "2026-11-22T19:36:10+00:00,200,v1,6.5",
            "2026-11-22T19:36:11+00:00,500,v1,",
            "2026-11-22T19:36:12+00:00,503,,",
            "2026-11-22T19:36:13+00:00,200,v1,6.6",
        ],
    )
    resumen = monitoreo.resumir(monitoreo.leer_registro(path).filas)
    assert resumen.total == 4
    assert resumen.fallidas == 2
    assert monitoreo.formatear_porcentaje(monitoreo.porcentaje_fallos(resumen)) == "50,0 %"


def test_filas_desordenadas_dan_el_mismo_resultado(tmp_path):
    rows = [
        "2026-11-22T19:36:10+00:00,200,v1,6.5",
        "2026-11-22T19:36:11+00:00,422,,",
        "2026-11-22T19:36:12+00:00,200,v1,6.6",
        "2026-11-22T19:36:13+00:00,500,v1,",
    ]
    ordered = monitoreo.resumir(monitoreo.leer_registro(write_log(tmp_path / "a.csv", rows)).filas)
    shuffled = [rows[3], rows[0], rows[2], rows[1]]
    unordered = monitoreo.resumir(
        monitoreo.leer_registro(write_log(tmp_path / "b.csv", shuffled)).filas
    )
    assert (unordered.total, unordered.fallidas) == (ordered.total, ordered.fallidas) == (4, 2)
    assert unordered.por_codigo == ordered.por_codigo


def test_estado_http_no_entero_da_error(tmp_path, capsys):
    path = write_log(tmp_path / "registro.csv", ["2026-11-22T19:36:10+00:00,ok,v1,6.5"])
    code, out, err = run_main(path, capsys)
    assert code != 0
    assert out == ""
    assert "estado_http" in err and "no es un entero" in err


def test_porcentaje_con_un_decimal_y_coma():
    assert monitoreo.formatear_porcentaje(100 / 3) == "33,3 %"
    assert monitoreo.formatear_porcentaje(200 / 3) == "66,7 %"
    assert monitoreo.formatear_porcentaje(100.0) == "100,0 %"
    assert monitoreo.formatear_porcentaje(None) == "sin solicitudes"


def test_encabezado_invalido_da_error_por_linea_de_comandos(tmp_path):
    path = write_log(
        tmp_path / "registro.csv",
        ["2026-11-22T19:36:10+00:00,200,v1,6.5"],
        header="fecha,codigo,version,prediccion",
    )
    result = run_cli("--registro", str(path))
    assert result.returncode != 0
    assert result.stdout == ""
    assert "encabezado no coincide" in result.stderr
    assert "Traceback" not in result.stderr


def test_help_funciona_por_linea_de_comandos():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--registro" in result.stdout


@pytest.mark.parametrize("value", ["", "   "])
def test_sin_registro_usa_log_path_o_el_valor_por_defecto(monkeypatch, value):
    monkeypatch.setenv("LOG_PATH", value)
    path = monitoreo.log_path_from_env()
    assert monitoreo.ruta_para_mostrar(path) == "fase-4/registros/predicciones.csv"
