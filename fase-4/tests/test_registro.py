"""Pruebas del registro de predicciones en CSV."""

import re
import threading
from datetime import datetime, timezone

from api.main import EventoPrediccion
from registro.csv_logger import COLUMNS, RegistroCSV, format_timestamp

from conftest import DUNE, TOP_GUN, read_log

HEADER = list(COLUMNS)
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00")


def test_dos_validas_y_una_incompleta_dejan_tres_filas(make_client, log_path):
    client = make_client()
    r1 = client.post("/predict", json=DUNE)
    r2 = client.post("/predict", json=TOP_GUN)
    r3 = client.post("/predict", json={k: v for k, v in DUNE.items() if k != "runtime"})
    assert [r1.status_code, r2.status_code, r3.status_code] == [200, 200, 422]

    lines = read_log(log_path)
    assert lines[0] == HEADER
    rows = lines[1:]
    assert len(rows) == 3
    assert [row[1] for row in rows] == ["200", "200", "422"]
    for row, response in zip(rows[:2], (r1, r2)):
        assert row[2] == "v1"
        assert float(row[3]) == response.json()["prediccion"]
    assert rows[2][2:] == ["", ""]


def test_json_mal_formado_deja_una_fila_400_sin_version(make_client, log_path):
    response = make_client().post(
        "/predict", content=b'{"budget": 1,', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    rows = read_log(log_path)[1:]
    assert len(rows) == 1
    assert rows[0][1:] == ["400", "", ""]


def test_version_inexistente_deja_una_fila_503_sin_version(make_client, log_path):
    response = make_client(version="v9").post("/predict", json=DUNE)
    assert response.status_code == 503
    rows = read_log(log_path)[1:]
    assert len(rows) == 1
    assert rows[0][1:] == ["503", "", ""]


def test_error_del_modelo_deja_500_con_version_y_sin_prediccion(make_client, log_path):
    client = make_client()

    class ModeloRoto:
        def predict(self, X):
            raise ValueError("fallo simulado")

    client.app.state.model_state.model = ModeloRoto()
    assert client.post("/predict", json=DUNE).status_code == 500
    assert read_log(log_path)[1][1:] == ["500", "v1", ""]


def test_encabezado_una_sola_vez_con_dos_observadores(log_path):
    evento = EventoPrediccion(
        fecha="2026-11-06T10:02:00.123456+00:00",
        codigo_http=422,
        version="v1",
        prediccion=None,
    )
    RegistroCSV(log_path)(evento)
    RegistroCSV(log_path)(evento)
    row = ["2026-11-06T10:02:00+00:00", "422", "", ""]
    assert read_log(log_path) == [HEADER, row, row]


def test_historial_se_conserva_entre_ejecuciones(make_client, log_path):
    assert make_client().post("/predict", json=DUNE).status_code == 200
    assert make_client().post("/predict", json=TOP_GUN).status_code == 200
    lines = read_log(log_path)
    assert lines.count(HEADER) == 1
    assert len(lines) == 3
    assert [row[1:3] for row in lines[1:]] == [["200", "v1"], ["200", "v1"]]


def test_archivo_vacio_recibe_el_encabezado(log_path):
    log_path.parent.mkdir(parents=True)
    log_path.write_text("", encoding="utf-8")
    RegistroCSV(log_path)(EventoPrediccion("2026-11-06T10:02:00+00:00", 400, "v1", None))
    assert read_log(log_path) == [HEADER, ["2026-11-06T10:02:00+00:00", "400", "", ""]]


def test_health_no_escribe_en_el_registro(make_client, log_path):
    assert make_client().get("/health").status_code == 200
    assert not log_path.exists()


def test_fecha_hora_en_utc_a_segundos(make_client, log_path):
    before = datetime.now(timezone.utc).replace(microsecond=0)
    make_client().post("/predict", json=DUNE)
    after = datetime.now(timezone.utc)
    value = read_log(log_path)[1][0]
    assert TIMESTAMP.fullmatch(value)
    assert before <= datetime.fromisoformat(value) <= after


def test_format_timestamp_convierte_a_utc_y_trunca():
    assert format_timestamp("2026-11-06T05:02:00.999999-05:00") == "2026-11-06T10:02:00+00:00"


def test_escrituras_simultaneas_no_se_mezclan(log_path):
    registro = RegistroCSV(log_path)
    evento = EventoPrediccion("2026-11-06T10:02:00+00:00", 200, "v1", 6.758120437797601)

    def escribir():
        for _ in range(50):
            registro(evento)

    hilos = [threading.Thread(target=escribir) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    lines = read_log(log_path)
    assert lines[0] == HEADER
    assert len(lines) == 1 + 8 * 50
    assert all(line == ["2026-11-06T10:02:00+00:00", "200", "v1", "6.758120437797601"] for line in lines[1:])
