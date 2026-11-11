from io import BytesIO

from openpyxl import load_workbook

from backend.services.report_excel_service import generate_summary_report_excel


def test_generate_summary_report_excel_has_data_sheets_and_numeric_values() -> None:
    content = generate_summary_report_excel(
        "2026-10-01",
        "2026-10-31",
        {
            "kpis": [
                {"name": "Flujo neto", "code": "flujo_neto_bancario", "value": "1234.56", "period": "2026-10"},
                {"name": "Margen", "code": "margen_operativo", "value": "12.5", "period": "2026-10"},
            ],
            "forecast": {
                "monthly_values": [
                    {"period": "2026-11", "days": 30, "predicted_value": "-240.50", "lower_bound": "-300", "upper_bound": "100"}
                ]
            },
            "alerts": [
                {
                    "id": 5,
                    "period": "2026-10",
                    "severity": "high",
                    "deviation_pct": "-15.25",
                    "budgeted_amount": "1000",
                    "actual_amount": "1152.5",
                }
            ],
            "recommendations": [
                {
                    "id": 8,
                    "recommendation_text": "=HYPERLINK(\"https://example.com\")",
                }
            ],
        },
    )
    workbook = load_workbook(BytesIO(content), data_only=True)

    assert workbook.sheetnames == ["Resumen", "Pronóstico", "Alertas", "Recomendaciones"]
    assert workbook["Resumen"]["C7"].value == 1234.56
    assert workbook["Resumen"]["C8"].value == 12.5
    assert workbook["Pronóstico"]["C2"].value == -240.5
    assert workbook["Alertas"]["E2"].value == -15.25
    assert workbook["Alertas"]["F2"].value == 1000
    assert workbook["Recomendaciones"]["F2"].value.startswith("'=")
