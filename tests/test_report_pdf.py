from datetime import date, datetime, timezone
from io import BytesIO
from uuid import UUID
from unittest.mock import MagicMock

from pypdf import PdfReader

from backend.repositories import financial_repository
from backend.services.report_pdf_service import generate_summary_report_pdf


def test_insert_summary_report_persists_pdf(monkeypatch) -> None:
    pdf_content = b"%PDF-1.4 stored report"
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = (
        7,
        date(2026, 10, 31),
        date(2026, 10, 1),
        date(2026, 10, 31),
        "manual",
        datetime.now(timezone.utc),
        {"kpis": []},
        True,
    )
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(financial_repository, "get_db_connection", lambda: connection)

    report = financial_repository.repository._insert_summary_report(
        date(2026, 10, 1),
        date(2026, 10, 31),
        "manual",
        {"kpis": []},
        pdf_content,
        UUID("00000000-0000-0000-0000-000000000002"),
    )

    assert pdf_content in cursor.execute.call_args.args[1]
    assert report.pdf_available is True
    connection.commit.assert_called_once()


def test_generate_summary_report_pdf_contains_report_sections() -> None:
    pdf_content = generate_summary_report_pdf(
        date(2026, 10, 1),
        date(2026, 10, 31),
        {
            "last_sync": "2026-10-31T12:00:00+00:00",
            "kpis": [
                {
                    "code": "ingresos_acumulados",
                    "name": "Ingresos acumulados",
                    "value": "24800000",
                    "period": "2026-10-01",
                }
            ],
            "forecast": {
                "monthly_values": [
                    {
                        "period": "2026-11-01",
                        "predicted_value": "12000",
                        "lower_bound": "10000",
                        "upper_bound": "14000",
                    }
                ]
            },
            "alerts": [
                {
                    "period": "2026-10-01",
                    "severity": "media",
                    "deviation_pct": "4.5",
                    "status": "nueva",
                }
            ],
            "recommendations": [
                {
                    "situation": "Gasto elevado",
                    "recommendation_text": "Revisar el presupuesto del área.",
                }
            ],
        },
    )

    pdf = PdfReader(BytesIO(pdf_content))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert pdf_content.startswith(b"%PDF-")
    assert "Resumen financiero" in text
    assert "Indicadores financieros" in text
    assert "Proyección de flujo neto" in text
    assert "Gasto elevado" in text
