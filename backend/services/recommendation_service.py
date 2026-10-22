from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from ..infrastructure.database import get_db_connection
from .forecast_service import DailyForecast, calculate_daily_forecast


RULES_VERSION = "reglas-v1"
FORECAST_CHECK_DAYS = (30, 60, 90)
TRACKED_KPI_CODES = (
    "flujo_neto_bancario",
    "margen_operativo",
    "desviacion_presupuestal",
)


def _load_open_alerts(cursor: Any) -> Tuple[List[Dict[str, Any]], bool]:
    cursor.execute("SELECT EXISTS (SELECT 1 FROM alertas)")
    has_alert_data = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT id, periodo, centro_costo_id, desviacion_pct, severidad,
               monto_presupuestado, monto_real
        FROM alertas
        WHERE estado IN ('nueva', 'en_revision')
        ORDER BY periodo DESC, id
        """,
    )
    alerts = [
        {
            "id": row[0],
            "periodo": row[1],
            "centro_costo_id": row[2],
            "desviacion_pct": Decimal(str(row[3])),
            "severidad": row[4],
            "monto_presupuestado": Decimal(str(row[5])),
            "monto_real": Decimal(str(row[6])),
        }
        for row in cursor.fetchall()
    ]
    return alerts, has_alert_data


def _load_latest_kpis(cursor: Any) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT DISTINCT ON (kd.codigo, kv.centro_costo_id)
               kv.id, kd.codigo, kv.periodo, kv.centro_costo_id, kv.valor
        FROM valores_kpi kv
        JOIN definiciones_kpi kd ON kd.id = kv.definicion_kpi_id
        WHERE kd.codigo = ANY(%s::varchar[])
        ORDER BY kd.codigo, kv.centro_costo_id, kv.periodo DESC, kv.id DESC
        """,
        (list(TRACKED_KPI_CODES),),
    )
    return [
        {
            "id": row[0],
            "codigo": row[1],
            "periodo": row[2],
            "centro_costo_id": row[3],
            "valor": Decimal(str(row[4])),
        }
        for row in cursor.fetchall()
    ]


def _load_forecast(cursor: Any) -> Tuple[Optional[DailyForecast], Optional[str]]:
    cursor.execute(
        """
        SELECT MIN(fecha_transaccion), MAX(fecha_transaccion)
        FROM transacciones
        WHERE tipo_fuente = 'banco'::fuente_tipo
        """
    )
    first_day, last_day = cursor.fetchone()
    if first_day is None or last_day is None:
        return None, "No hay histórico de transacciones bancarias."
    training_days = (last_day - first_day).days + 1
    if training_days < 180:
        return None, "Hay %s días de histórico; se requieren al menos 180." % training_days

    training_start = max(first_day, last_day - timedelta(days=179))
    cursor.execute(
        """
        SELECT calendar.day::date, COALESCE(SUM(t.monto), 0)
        FROM generate_series(%s::date, %s::date, INTERVAL '1 day') AS calendar(day)
        LEFT JOIN transacciones t
          ON t.fecha_transaccion = calendar.day::date
         AND t.tipo_fuente = 'banco'::fuente_tipo
        GROUP BY calendar.day
        ORDER BY calendar.day
        """,
        (training_start, last_day),
    )
    daily_values = [
        (target_date, Decimal(str(amount)))
        for target_date, amount in cursor.fetchall()
    ]
    forecast = calculate_daily_forecast(daily_values)
    if forecast is None:
        return None, "El histórico bancario no permite calcular un forecast válido."
    return forecast, None


def _recommendation(
    rule: str,
    period: date,
    situation: str,
    impact: str,
    recommendation_text: str,
    priority: str,
    alert_ids: Optional[List[int]] = None,
    kpi_ids: Optional[List[int]] = None,
    **evidence_details: Any,
) -> Dict[str, Any]:
    evidence = {
        "regla": rule,
        "alertas_ids": alert_ids or [],
        "kpis_ids": kpi_ids or [],
        **evidence_details,
    }
    return {
        "regla": rule,
        "periodo": period,
        "situacion": situation,
        "impacto": impact,
        "recomendacion_texto": recommendation_text,
        "prioridad": priority,
        "evidencia": evidence,
    }


def _build_recommendations(
    alerts: List[Dict[str, Any]],
    kpis: List[Dict[str, Any]],
    forecast: Optional[DailyForecast],
    alert_data_available: bool = True,
    missing_kpi_codes: Optional[List[str]] = None,
    forecast_unavailable_reason: Optional[str] = None,
) -> List[Dict[str, Any]]:
    recommendations: List[Dict[str, Any]] = []
    open_overruns = [
        alert
        for alert in alerts
        if alert["severidad"] == "alta" and alert["desviacion_pct"] > 0
    ]
    if open_overruns:
        latest_period = max(alert["periodo"] for alert in open_overruns)
        total_overrun = sum(
            (alert["monto_real"] - alert["monto_presupuestado"] for alert in open_overruns),
            Decimal("0"),
        )
        recommendations.append(
            _recommendation(
                "alerta_abierta_severidad_alta",
                latest_period,
                "%s alerta(s) abierta(s) de severidad alta presentan sobrepaso presupuestal."
                % len(open_overruns),
                "El gasto excede el presupuesto en %s."
                % format(total_overrun, "f"),
                "Revisar las partidas afectadas y acordar acciones de contención con sus responsables.",
                "alta",
                alert_ids=[alert["id"] for alert in open_overruns],
            )
        )

    alerts_by_cost_center: Dict[Optional[int], List[Dict[str, Any]]] = defaultdict(list)
    for alert in alerts:
        alerts_by_cost_center[alert["centro_costo_id"]].append(alert)
    for cost_center_id, center_alerts in alerts_by_cost_center.items():
        if len(center_alerts) < 2:
            continue
        latest_period = max(alert["periodo"] for alert in center_alerts)
        center_label = (
            "la empresa" if cost_center_id is None else "el centro de costo %s" % cost_center_id
        )
        recommendations.append(
            _recommendation(
                "alertas_recurrentes_por_centro",
                latest_period,
                "Hay %s alertas de desviación abiertas en %s."
                % (len(center_alerts), center_label),
                "Varias partidas requieren atención en el mismo ámbito financiero.",
                "Priorizar una revisión conjunta de las partidas y asignar responsables para cada alerta.",
                "media",
                alert_ids=[alert["id"] for alert in center_alerts],
                centro_costo_id=cost_center_id,
            )
        )

    for kpi in kpis:
        value = kpi["valor"]
        code = kpi["codigo"]
        if code == "flujo_neto_bancario" and value < 0:
            recommendations.append(
                _recommendation(
                    "flujo_neto_bancario_negativo",
                    kpi["periodo"],
                    "El flujo neto bancario del periodo es negativo.",
                    "Los movimientos bancarios netos reducen la caja en %s."
                    % format(abs(value), "f"),
                    "Revisar pagos y cobros próximos y validar el saldo inicial antes de tomar decisiones de liquidez.",
                    "alta",
                    kpi_ids=[kpi["id"]],
                    valor=format(value, "f"),
                    centro_costo_id=kpi["centro_costo_id"],
                )
            )
        elif code == "margen_operativo" and value < 0:
            recommendations.append(
                _recommendation(
                    "margen_operativo_negativo",
                    kpi["periodo"],
                    "El margen operativo calculado es negativo.",
                    "La operación presenta un margen de %s%%."
                    % format(value, "f"),
                    "Analizar ingresos y gastos operativos del periodo para identificar las partidas que presionan el margen.",
                    "alta",
                    kpi_ids=[kpi["id"]],
                    valor=format(value, "f"),
                    centro_costo_id=kpi["centro_costo_id"],
                )
            )
        elif code == "desviacion_presupuestal" and value > 0:
            recommendations.append(
                _recommendation(
                    "kpi_desviacion_presupuestal_positiva",
                    kpi["periodo"],
                    "El KPI de desviación presupuestal indica gasto por encima del presupuesto.",
                    "La desviación calculada es de %s%%." % format(value, "f"),
                    "Revisar el gasto del periodo frente al presupuesto y determinar si requiere ajuste o medidas correctivas.",
                    "alta" if value >= 20 else "media",
                    kpi_ids=[kpi["id"]],
                    valor=format(value, "f"),
                    centro_costo_id=kpi["centro_costo_id"],
                )
            )

    if forecast is not None and forecast.values:
        forecast_start = forecast.values[0].target_date - timedelta(days=1)
        negative_points = [
            {
                "dia_horizonte": horizon,
                "fecha_objetivo": point.target_date,
                "valor_predicho": format(point.predicted_value, "f"),
            }
            for horizon in FORECAST_CHECK_DAYS
            for point in forecast.values
            if (point.target_date - forecast_start).days == horizon
            and point.predicted_value < 0
        ]
        if negative_points:
            earliest_horizon = min(point["dia_horizonte"] for point in negative_points)
            recommendations.append(
                _recommendation(
                    "forecast_caja_negativa",
                    forecast_start,
                    "El forecast proyecta flujo neto bancario negativo a %s días."
                    % ", ".join(str(point["dia_horizonte"]) for point in negative_points),
                    "El flujo neto predicho alcanza %s en el primer horizonte negativo; no representa por sí solo un saldo de caja."
                    % negative_points[0]["valor_predicho"],
                    "Validar el saldo disponible y preparar un plan de liquidez para ese horizonte revisando cobros, pagos y alternativas de financiamiento.",
                    "alta" if earliest_horizon <= 30 else "media",
                    forecast=[
                        {
                            **point,
                            "fecha_objetivo": point["fecha_objetivo"].isoformat(),
                        }
                        for point in negative_points
                    ],
                )
            )

    missing_sources = []
    if not alert_data_available:
        missing_sources.append("alertas de desviación")
    if missing_kpi_codes:
        missing_sources.append("KPIs: %s" % ", ".join(missing_kpi_codes))
    if forecast_unavailable_reason:
        missing_sources.append("forecast: %s" % forecast_unavailable_reason)
    if missing_sources:
        recommendations.append(
            _recommendation(
                "datos_insuficientes",
                date.today(),
                "No hay datos suficientes para evaluar todas las reglas: %s."
                % "; ".join(missing_sources),
                "No se calcularon impactos ni resultados para las fuentes faltantes.",
                "Incorporar o actualizar los datos indicados y volver a generar las recomendaciones.",
                "baja",
                fuentes_faltantes=missing_sources,
                kpi_codigos_faltantes=missing_kpi_codes or [],
                motivo_forecast_no_disponible=forecast_unavailable_reason,
            )
        )

    return recommendations


def _persist_recommendations(
    cursor: Any,
    recommendations: List[Dict[str, Any]],
    user_id: Optional[UUID],
) -> List[Dict[str, Any]]:
    persisted: List[Dict[str, Any]] = []
    for recommendation in recommendations:
        prompt_used = json.dumps(
            {
                "regla": recommendation["regla"],
                "situacion": recommendation["situacion"],
                "impacto": recommendation["impacto"],
                "recomendacion_texto": recommendation["recomendacion_texto"],
            },
            ensure_ascii=False,
        )
        cursor.execute(
            """
            INSERT INTO recomendaciones_ia (
                usuario_id, periodo, situacion, impacto, recomendacion_texto,
                prioridad, evidencia, version_prompt, prompt_utilizado,
                texto_generado, nombre_modelo, generado_en
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
            RETURNING id, generado_en
            """,
            (
                str(user_id) if user_id else None,
                recommendation["periodo"],
                recommendation["situacion"],
                recommendation["impacto"],
                recommendation["recomendacion_texto"],
                recommendation["prioridad"],
                json.dumps(recommendation["evidencia"], ensure_ascii=False),
                RULES_VERSION,
                prompt_used,
                recommendation["recomendacion_texto"],
                RULES_VERSION,
                datetime.now(timezone.utc),
            ),
        )
        recommendation_id, generated_at = cursor.fetchone()
        persisted.append(
            {
                "id": recommendation_id,
                "user_id": user_id,
                "period": recommendation["periodo"],
                "situation": recommendation["situacion"],
                "impact": recommendation["impacto"],
                "recommendation_text": recommendation["recomendacion_texto"],
                "priority": recommendation["prioridad"],
                "evidence": recommendation["evidencia"],
                "prompt_version": RULES_VERSION,
                "generated_text": recommendation["recomendacion_texto"],
                "model_name": RULES_VERSION,
                "generated_at": generated_at,
            }
        )
    return persisted


def generate_recommendations(user_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    """Genera y guarda recomendaciones explicables con evidencia de datos financieros."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            alerts, alert_data_available = _load_open_alerts(cursor)
            kpis = _load_latest_kpis(cursor)
            forecast, forecast_unavailable_reason = _load_forecast(cursor)
            available_kpi_codes = {kpi["codigo"] for kpi in kpis}
            missing_kpi_codes = sorted(set(TRACKED_KPI_CODES) - available_kpi_codes)
            recommendations = _build_recommendations(
                alerts,
                kpis,
                forecast,
                alert_data_available=alert_data_available,
                missing_kpi_codes=missing_kpi_codes,
                forecast_unavailable_reason=forecast_unavailable_reason,
            )
            persisted = _persist_recommendations(cursor, recommendations, user_id)
            connection.commit()
    return persisted
