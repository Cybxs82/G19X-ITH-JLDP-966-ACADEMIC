import json
from contextlib import nullcontext

import backend.services.ingestion_service as ingestion_service
from backend.services.ingestion_service import extract_document_values


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