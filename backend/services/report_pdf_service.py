from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from io import BytesIO
from typing import Any, Dict, Iterable, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


_NAVY = colors.HexColor("#102b35")
_TEAL = colors.HexColor("#087e8b")
_PALE_BLUE = colors.HexColor("#eaf3f5")
_MUTED = colors.HexColor("#53666d")


def _safe_text(value: Any) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def _amount(value: Any, code: str = "") -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    if code in {"flujo_neto_bancario", "ingresos_acumulados"}:
        return f"${amount:,.2f} MXN"
    suffix = "%" if code in {"margen_operativo", "desviacion_presupuestal"} else ""
    return f"{amount:,.2f}{suffix}"


def _section_title(title: str, styles: Dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(_safe_text(title), styles["section"])


def _table(rows: List[List[Any]], widths: List[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("TEXTCOLOR", (0, 1), (-1, -1), _NAVY),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d5e0e3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _paragraph_list(items: Iterable[str], styles: Dict[str, ParagraphStyle]) -> List[Paragraph]:
    return [Paragraph(f"&bull; {_safe_text(item)}", styles["body"]) for item in items]


def _draw_footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d5e0e3"))
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawString(0.65 * inch, 0.35 * inch, "Resumen financiero · Uso interno")
    canvas.drawRightString(7.85 * inch, 0.35 * inch, f"Página {document.page}")
    canvas.restoreState()


def generate_summary_report_pdf(
    period_from: date,
    period_to: date,
    snapshot: Dict[str, Any],
) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.75 * inch,
        title=f"Resumen financiero {period_from.isoformat()} - {period_to.isoformat()}",
        author="Foresight · Plataforma CFO",
    )
    base_styles = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_LEFT,
            textColor=_NAVY,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base_styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=_MUTED,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "ReportSection",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=_TEAL,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base_styles["BodyText"],
            fontSize=8.5,
            leading=12,
            textColor=_NAVY,
            spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "ReportCell",
            parent=base_styles["BodyText"],
            fontSize=8,
            leading=10,
            textColor=_NAVY,
        ),
        "header_cell": ParagraphStyle(
            "ReportHeaderCell",
            parent=base_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
    }

    def cell(value: Any, header: bool = False) -> Paragraph:
        return Paragraph(_safe_text(value), styles["header_cell" if header else "cell"])

    content: List[Any] = [
        Paragraph("Resumen financiero", styles["title"]),
        Paragraph(
            f"Periodo: {period_from.isoformat()} al {period_to.isoformat()}",
            styles["subtitle"],
        ),
    ]

    kpis = snapshot.get("kpis", [])
    content.append(_section_title("Indicadores financieros", styles))
    if kpis:
        content.append(
            _table(
                [[cell("Indicador", True), cell("Valor", True), cell("Periodo", True)]]
                + [
                    [
                        cell(item.get("name", item.get("code", "Indicador"))),
                        cell(_amount(item.get("value", ""), item.get("code", ""))),
                        cell(item.get("period", "")),
                    ]
                    for item in kpis
                ],
                [3.3 * inch, 1.8 * inch, 2.0 * inch],
            )
        )
    else:
        content.extend(_paragraph_list(["No había indicadores disponibles para este periodo."], styles))

    forecast = snapshot.get("forecast", {})
    monthly_values = forecast.get("monthly_values", [])
    content.append(_section_title("Proyección de flujo neto", styles))
    if monthly_values:
        content.append(
            _table(
                [[cell("Periodo", True), cell("Proyección", True), cell("Intervalo", True)]]
                + [
                    [
                        cell(item.get("period", "")),
                        cell(_amount(item.get("predicted_value", ""), "flujo_neto_bancario")),
                        cell(
                            f"{_amount(item.get('lower_bound', ''), 'flujo_neto_bancario')} a "
                            f"{_amount(item.get('upper_bound', ''), 'flujo_neto_bancario')}"
                        ),
                    ]
                    for item in monthly_values
                ],
                [1.5 * inch, 2.2 * inch, 3.4 * inch],
            )
        )
    else:
        content.extend(_paragraph_list(["No hay histórico bancario suficiente para la proyección."], styles))

    alerts = snapshot.get("alerts", [])
    content.append(_section_title(f"Alertas ({len(alerts)})", styles))
    if alerts:
        content.append(
            _table(
                [[cell("Periodo", True), cell("Severidad", True), cell("Desviación", True), cell("Estado", True)]]
                + [
                    [
                        cell(item.get("period", "")),
                        cell(item.get("severity", "")),
                        cell(f"{_amount(item.get('deviation_pct', ''))}%"),
                        cell(item.get("status", "")),
                    ]
                    for item in alerts
                ],
                [1.5 * inch, 1.4 * inch, 2.0 * inch, 2.2 * inch],
            )
        )
    else:
        content.extend(_paragraph_list(["No hay alertas para este periodo."], styles))

    recommendations = snapshot.get("recommendations", [])
    content.append(_section_title(f"Recomendaciones ({len(recommendations)})", styles))
    if recommendations:
        content.extend(
            _paragraph_list(
                [
                    f"{item.get('situation', 'Recomendación')}: {item.get('recommendation_text', '')}"
                    for item in recommendations
                ],
                styles,
            )
        )
    else:
        content.extend(_paragraph_list(["No hay recomendaciones disponibles para este resumen."], styles))

    last_sync = snapshot.get("last_sync")
    content.append(Spacer(1, 8))
    content.append(
        Paragraph(
            f"Última sincronización registrada: {_safe_text(last_sync or 'Sin sincronización')}",
            styles["subtitle"],
        )
    )
    document.build(content, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
