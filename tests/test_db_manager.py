from pathlib import Path

from core import db_manager


def _payload_base(**overrides):
    data = {
        "id_indicador": "150",
        "nombre_indicador": "Tasa Aprobacion",
        "proceso": "ACADEMICA",
        "periodo": "Marzo",
        "anio": 2026,
        "tiene_om": 1,
        "numero_om": "OM-2026-001",
        "comentario": "",
    }
    data.update(overrides)
    return data


def test_guardar_y_leer_registro_sqlite(tmp_path, monkeypatch):
    tmp_db = Path(tmp_path) / "registros_om_test.db"
    monkeypatch.setattr(db_manager, "DB_PATH", tmp_db)
    monkeypatch.setattr(db_manager, "_use_pg", lambda: False)

    db_manager._init_sqlite()

    ok = db_manager.guardar_registro_om(_payload_base())
    assert ok is True

    rows = db_manager.leer_registros_om()
    assert len(rows) == 1
    assert rows[0]["id_indicador"] == "150"
    assert rows[0]["numero_om"] == "OM-2026-001"
    assert rows[0]["anio"] == 2026


def test_upsert_unico_actualiza_registro_existente(tmp_path, monkeypatch):
    tmp_db = Path(tmp_path) / "registros_om_test.db"
    monkeypatch.setattr(db_manager, "DB_PATH", tmp_db)
    monkeypatch.setattr(db_manager, "_use_pg", lambda: False)

    db_manager._init_sqlite()

    assert db_manager.guardar_registro_om(_payload_base(numero_om="OM-2026-001", tiene_om=1)) is True
    assert db_manager.guardar_registro_om(_payload_base(numero_om="OM-2026-999", tiene_om=0, comentario="Sin apertura")) is True

    rows = db_manager.leer_registros_om()
    assert len(rows) == 1
    assert rows[0]["numero_om"] == "OM-2026-999"
    assert rows[0]["tiene_om"] == 0
    assert rows[0]["comentario"] == "Sin apertura"


def test_leer_registros_filtra_por_anio(tmp_path, monkeypatch):
    tmp_db = Path(tmp_path) / "registros_om_test.db"
    monkeypatch.setattr(db_manager, "DB_PATH", tmp_db)
    monkeypatch.setattr(db_manager, "_use_pg", lambda: False)

    db_manager._init_sqlite()

    db_manager.guardar_registro_om(_payload_base(anio=2026, id_indicador="150", numero_om="OM-1"))
    db_manager.guardar_registro_om(_payload_base(anio=2025, id_indicador="151", numero_om="OM-2", periodo="Abril"))

    rows_2026 = db_manager.leer_registros_om(anio=2026)
    rows_2025 = db_manager.leer_registros_om(anio=2025)

    assert len(rows_2026) == 1
    assert rows_2026[0]["id_indicador"] == "150"
    assert len(rows_2025) == 1
    assert rows_2025[0]["id_indicador"] == "151"


def test_leer_registros_filtra_por_periodo(tmp_path, monkeypatch):
    tmp_db = Path(tmp_path) / "registros_om_test.db"
    monkeypatch.setattr(db_manager, "DB_PATH", tmp_db)
    monkeypatch.setattr(db_manager, "_use_pg", lambda: False)

    db_manager._init_sqlite()

    db_manager.guardar_registro_om(_payload_base(anio=2026, id_indicador="150", periodo="Mayo", numero_om="OM-1"))
    db_manager.guardar_registro_om(_payload_base(anio=2026, id_indicador="151", periodo="Junio", numero_om="OM-2"))

    rows_mayo = db_manager.leer_registros_om(periodo="Mayo")
    rows_junio = db_manager.leer_registros_om(periodo="junio")

    assert len(rows_mayo) == 1
    assert rows_mayo[0]["id_indicador"] == "150"
    assert len(rows_junio) == 1
    assert rows_junio[0]["id_indicador"] == "151"


def test_registros_om_como_dict(tmp_path, monkeypatch):
    tmp_db = Path(tmp_path) / "registros_om_test.db"
    monkeypatch.setattr(db_manager, "DB_PATH", tmp_db)
    monkeypatch.setattr(db_manager, "_use_pg", lambda: False)

    db_manager._init_sqlite()

    db_manager.guardar_registro_om(_payload_base(id_indicador="200", numero_om="OM-200", periodo="Mayo"))

    result = db_manager.registros_om_como_dict(anio=2026)

    assert "200" in result
    assert result["200"]["numero_om"] == "OM-200"
    assert result["200"]["periodo"] == "Mayo"
    assert result["200"]["anio"] == 2026


def test_guardar_registro_om_normaliza_periodo_yyyy_mm(tmp_path, monkeypatch):
    tmp_db = Path(tmp_path) / "registros_om_test.db"
    monkeypatch.setattr(db_manager, "DB_PATH", tmp_db)
    monkeypatch.setattr(db_manager, "_use_pg", lambda: False)

    db_manager._init_sqlite()

    assert db_manager.guardar_registro_om(_payload_base(id_indicador="201", numero_om="OM-2025-101", periodo="2025-12", anio=0)) is True
    rows = db_manager.leer_registros_om()
    assert len(rows) == 1
    assert rows[0]["periodo"] == "Diciembre"
    assert rows[0]["anio"] == 2025
