import json
from contextlib import nullcontext
from datetime import date
from decimal import Decimal

import backend.services.ingestion_service as ingestion_service
from backend.services.ingestion_service import _canonical_budget_row, _refresh_alerts, extract_document_values


def test_csv_document_values_are_saved_without_normalization() -> None:
    content = b"fecha,monto,detalle\n31/02/2025,001.2300,  valor crudo  "

    values = extract_document_values("erp.csv", content)

    assert values == [
        {
            "row_number": 2,
            "values": {
                "fecha": "31/02/2025",
                "monto": "001.2300",
                "detalle": "  valor crudo  ",
            },
        }
    ]


def test_erp_document_ingestion_writes_only_raw_staging_values(monkeypatch) -> None:
    class FakeCursor:
        def __init__(self) -> None:
            self.statements = []
            self.result = None
            self.rows = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def execute(self, statement, parameters=None) -> None:
            self.statements.append((statement, parameters))
            normalized = statement.lstrip().lower()
            if normalized.startswith("insert into fuentes_datos"):
                self.result = (41,)
            elif normalized.startswith("insert into registros_sincronizacion"):
                self.result = (73,)
            else:
                self.result = None

        def fetchone(self):
            return self.result

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()
            self.committed = False

        def cursor(self):
            return self.fake_cursor

        def commit(self) -> None:
            self.committed = True

    connection = FakeConnection()
    monkeypatch.setattr(ingestion_service, "get_db_connection", lambda: nullcontext(connection))

    result = ingestion_service.ingest_erp_document(
        "erp.csv",
        b"fecha,monto\n31/02/2025,001.2300",
    )

    staging_query, staging_parameters = next(
        (query, parameters)
        for query, parameters in connection.fake_cursor.statements
        if "INSERT INTO datos_temporales_erp" in query
    )
    statements = " ".join(query.lower() for query, _ in connection.fake_cursor.statements)
    assert result["rows_ingested"] == 1
    assert json.loads(staging_parameters[1]) == {
        "file_name": "erp.csv",
        "row_number": 2,
        "values": {"fecha": "31/02/2025", "monto": "001.2300"},
    }
    assert "transacciones" not in statements
    assert "valores_kpi" not in statements
    assert connection.committed


def test_financial_ingestion_preserves_raw_values_and_consolidates(monkeypatch) -> None:
    class FakeCursor:
        def __init__(self) -> None:
            self.statements = []
            self.result = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def execute(self, statement, parameters=None) -> None:
            self.statements.append((statement, parameters))
            normalized = statement.lstrip().lower()
            self.rows = []
            if normalized.startswith("insert into fuentes_datos"):
                self.result = (41,)
            elif normalized.startswith("insert into registros_sincronizacion"):
                self.result = (73,)
            elif normalized.startswith("insert into cuentas"):
                self.result = (101,)
            elif normalized.startswith("insert into centros_costo"):
                self.result = (202,)
            elif normalized.startswith("select id, codigo from definiciones_kpi"):
                self.rows = [
                    (1, "flujo_neto_bancario"),
                    (2, "margen_operativo"),
                    (3, "ingresos_acumulados"),
                    (4, "desviacion_presupuestal"),
                ]
            elif normalized.startswith("select date_trunc('month', fecha_transaccion)::date,") and "sum(case when monto > 0" in normalized:
                self.rows = [(date(2026, 1, 1), Decimal("1.23"), Decimal("0"))]
            elif normalized.startswith("select date_trunc('month', fecha_transaccion)::date, coalesce(sum(monto)"):
                self.rows = []
            elif normalized.startswith("select periodo, coalesce(sum(monto_presupuestado)"):
                self.rows = []
            elif normalized.startswith("select b.cuenta_id, b.centro_costo_id"):
                self.rows = []
            else:
                self.result = None

        def fetchone(self):
            return self.result

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()
            self.committed = False

        def cursor(self):
            return self.fake_cursor

        def commit(self) -> None:
            self.committed = True

    connection = FakeConnection()
    monkeypatch.setattr(ingestion_service, "get_db_connection", lambda: nullcontext(connection))

    result = ingestion_service.ingest_file(
        "erp.csv",
        b"fecha,monto,referencia\n2026-01-05,001.2300,ERP-0001",
        "erp",
    )

    staging_query, staging_parameters = next(
        (query, parameters)
        for query, parameters in connection.fake_cursor.statements
        if "INSERT INTO datos_temporales_erp" in query
    )
    statements = " ".join(query.lower() for query, _ in connection.fake_cursor.statements)
    assert result["rows_ingested"] == 1
    assert json.loads(staging_parameters[1]) == {
        "file_name": "erp.csv",
        "row_number": 2,
        "values": {"fecha": "2026-01-05", "monto": "001.2300", "referencia": "ERP-0001"},
    }
    assert "insert into transacciones" in statements
    assert "insert into valores_kpi" in statements
    assert connection.committed
    kpi_writes = [parameters for query, parameters in connection.fake_cursor.statements if "INSERT INTO valores_kpi" in query]
    assert {parameters[0] for parameters in kpi_writes} == {2, 3}
    assert {Decimal(str(parameters[2])) for parameters in kpi_writes} == {Decimal("100"), Decimal("1.23")}


def test_budget_row_uses_month_period_and_preserves_amount() -> None:
    row = _canonical_budget_row(
        {"periodo": "2026-01-29", "monto_presupuestado": "001250.00", "cuenta": "5101", "centro_costo": "CC-TEC"},
        2,
    )

    assert row["period"] == date(2026, 1, 1)
    assert row["amount"] == Decimal("1250.00")
    assert row["account_code"] == "5101"
    assert row["cost_center_code"] == "CC-TEC"


def test_alert_thresholds_are_ten_and_twenty_percent() -> None:
    class FakeCursor:
        def __init__(self) -> None:
            self.rows = [
                (1, None, date(2026, 1, 1), Decimal("100"), Decimal("115")),
                (2, None, date(2026, 1, 1), Decimal("100"), Decimal("125")),
                (3, None, date(2026, 1, 1), Decimal("100"), Decimal("90")),
            ]
            self.statements = []

        def execute(self, statement, parameters=None) -> None:
            self.statements.append((statement, parameters))

        def fetchall(self):
            return self.rows

    cursor = FakeCursor()
    _refresh_alerts(cursor)

    alert_writes = [parameters for query, parameters in cursor.statements if "INSERT INTO alertas" in query]
    assert "setval" in cursor.statements[0][0].lower()
    assert [parameters[6] for parameters in alert_writes] == ["media", "alta", "media"]
    assert [parameters[5] for parameters in alert_writes] == [Decimal("15.00"), Decimal("25.00"), Decimal("-10.00")]