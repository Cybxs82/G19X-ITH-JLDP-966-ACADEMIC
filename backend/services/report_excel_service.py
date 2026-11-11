import json
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


_HEADER_FILL = PatternFill("solid", fgColor="173B4B")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_TITLE_FONT = Font(size=16, bold=True, color="173B4B")


def _cell_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _number_value(value: Any) -> Any:
    if value is None or value == "":
        return value
    try:
        return float(Decimal(str(value)))
    except (ValueError, TypeError, ArithmeticError):
        return value


def _add_table(
    workbook: Workbook,
    title: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    number_formats: Optional[Dict[int, str]] = None,
) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(list(headers))
    for cell in sheet[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    for row in rows:
        sheet.append([_cell_value(value) for value in row])

    sheet.freeze_panes = "A2"
    if sheet.max_row > 1:
        sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        column_letter = column[0].column_letter
        width = max((len(str(cell.value or "")) for cell in column), default=10)
        sheet.column_dimensions[column_letter].width = min(max(width + 2, 12), 60)
    if number_formats:
        for column_index, number_format in number_formats.items():
            for row_index in range(2, sheet.max_row + 1):
                sheet.cell(row=row_index, column=column_index).number_format = number_format


def generate_summary_report_excel(
    period_from: str,
    period_to: str,
    snapshot: Dict[str, Any],
) -> bytes:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Resumen"
    summary["A1"] = "Resumen financiero"
    summary["A1"].font = _TITLE_FONT
    summary["A2"] = "Periodo"
    summary["B2"] = f"{period_from} al {period_to}"
    summary["A3"] = "Última sincronización"
    summary["B3"] = _cell_value(snapshot.get("last_sync") or "Sin sincronización")
    summary["A5"] = "Indicadores financieros"
    summary["A5"].font = Font(bold=True, color="087E8B")
    summary.append(["Indicador", "Código", "Valor", "Periodo"])
    for cell in summary[6]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
    for item in snapshot.get("kpis", []):
        summary.append([
            _cell_value(item.get("name", item.get("code", "Indicador"))),
            _cell_value(item.get("code", "")),
            _number_value(item.get("value", "")),
            _cell_value(item.get("period", "")),
        ])
    for row_index, item in enumerate(snapshot.get("kpis", []), start=7):
        code = item.get("code", "")
        summary.cell(row=row_index, column=3).number_format = (
            '"$"#,##0.00;[Red]("$"#,##0.00)'
            if code in {"flujo_neto_bancario", "ingresos_acumulados"}
            else '0.00"%"'
            if code in {"margen_operativo", "desviacion_presupuestal"}
            else "General"
        )
    summary.freeze_panes = "A7"
    summary.column_dimensions["A"].width = 34
    summary.column_dimensions["B"].width = 32
    summary.column_dimensions["C"].width = 20
    summary.column_dimensions["D"].width = 18

    forecast = snapshot.get("forecast", {})
    _add_table(
        workbook,
        "Pronóstico",
        ["Periodo", "Días", "Flujo neto estimado (MXN)", "Límite inferior (MXN)", "Límite superior (MXN)"],
        (
            [
                item.get("period", ""),
                item.get("days", ""),
                _number_value(item.get("predicted_value", "")),
                _number_value(item.get("lower_bound", "")),
                _number_value(item.get("upper_bound", "")),
            ]
            for item in forecast.get("monthly_values", [])
        ),
        {3: '"$"#,##0.00;[Red]("$"#,##0.00)', 4: '"$"#,##0.00;[Red]("$"#,##0.00)', 5: '"$"#,##0.00;[Red]("$"#,##0.00)'},
    )
    _add_table(
        workbook,
        "Alertas",
        ["ID", "Periodo", "Severidad", "Estado", "Desviación (%)", "Presupuesto (MXN)", "Real (MXN)", "Cuenta", "Centro de costo", "Comentario"],
        (
            [
                item.get("id", ""),
                item.get("period", ""),
                item.get("severity", ""),
                item.get("status", ""),
                _number_value(item.get("deviation_pct", "")),
                _number_value(item.get("budgeted_amount", "")),
                _number_value(item.get("actual_amount", "")),
                item.get("account_id", ""),
                item.get("cost_center_id", ""),
                item.get("comment", ""),
            ]
            for item in snapshot.get("alerts", [])
        ),
        {5: '0.00"%"', 6: '"$"#,##0.00;[Red]("$"#,##0.00)', 7: '"$"#,##0.00;[Red]("$"#,##0.00)'},
    )
    _add_table(
        workbook,
        "Recomendaciones",
        ["ID", "Periodo", "Prioridad", "Situación", "Impacto", "Recomendación", "Evidencia"],
        (
            [
                item.get("id", ""),
                item.get("period", ""),
                item.get("priority", ""),
                item.get("situation", ""),
                item.get("impact", ""),
                item.get("recommendation_text", ""),
                item.get("evidence", {}),
            ]
            for item in snapshot.get("recommendations", [])
        ),
    )

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
