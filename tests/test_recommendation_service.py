from datetime import date, timedelta
from decimal import Decimal

from backend.services.forecast_service import DailyForecast, ForecastValue
from backend.services.recommendation_service import _build_recommendations


def test_rules_generate_evidence_based_recommendations() -> None:
    period = date(2026, 10, 1)
    alerts = [
        {
            "id": 12,
            "periodo": period,
            "centro_costo_id": 4,
            "desviacion_pct": Decimal("22"),
            "severidad": "alta",
            "monto_presupuestado": Decimal("100"),
            "monto_real": Decimal("122"),
        },
        {
            "id": 13,
            "periodo": period,
            "centro_costo_id": 4,
            "desviacion_pct": Decimal("8"),
            "severidad": "media",
            "monto_presupuestado": Decimal("100"),
            "monto_real": Decimal("108"),
        },
    ]
    kpis = [
        {"id": 21, "codigo": "flujo_neto_bancario", "periodo": period, "centro_costo_id": None, "valor": Decimal("-50")},
        {"id": 22, "codigo": "margen_operativo", "periodo": period, "centro_costo_id": None, "valor": Decimal("-2")},
        {"id": 23, "codigo": "desviacion_presupuestal", "periodo": period, "centro_costo_id": None, "valor": Decimal("12")},
    ]
    forecast_start = period
    forecast_values = [
        ForecastValue(
            target_date=forecast_start + timedelta(days=offset),
            predicted_value=Decimal("-%s" % offset) if offset in (30, 60, 90) else Decimal("100"),
            lower_bound=Decimal("-100"),
            upper_bound=Decimal("100"),
        )
        for offset in range(1, 91)
    ]
    forecast = DailyForecast(values=forecast_values, backtest_mae=Decimal("1"))

    recommendations = _build_recommendations(alerts, kpis, forecast)

    assert len(recommendations) == 6
    assert {item["regla"] for item in recommendations} == {
        "alerta_abierta_severidad_alta",
        "alertas_recurrentes_por_centro",
        "flujo_neto_bancario_negativo",
        "margen_operativo_negativo",
        "kpi_desviacion_presupuestal_positiva",
        "forecast_caja_negativa",
    }
    for item in recommendations:
        assert all(
            key in item
            for key in ("situacion", "impacto", "recomendacion_texto", "prioridad", "evidencia")
        )
        assert "alertas_ids" in item["evidencia"]
        assert "kpis_ids" in item["evidencia"]

    by_rule = {item["regla"]: item for item in recommendations}
    assert by_rule["alerta_abierta_severidad_alta"]["evidencia"]["alertas_ids"] == [12]
    assert by_rule["alertas_recurrentes_por_centro"]["evidencia"]["alertas_ids"] == [12, 13]
    assert by_rule["flujo_neto_bancario_negativo"]["evidencia"]["kpis_ids"] == [21]
    assert [point["dia_horizonte"] for point in by_rule["forecast_caja_negativa"]["evidencia"]["forecast"]] == [30, 60, 90]


def test_rules_do_not_recommend_when_values_are_not_outside_thresholds() -> None:
    period = date(2026, 10, 1)
    kpis = [
        {"id": 31, "codigo": "flujo_neto_bancario", "periodo": period, "centro_costo_id": None, "valor": Decimal("0")},
        {"id": 32, "codigo": "margen_operativo", "periodo": period, "centro_costo_id": None, "valor": Decimal("0")},
        {"id": 33, "codigo": "desviacion_presupuestal", "periodo": period, "centro_costo_id": None, "valor": Decimal("0")},
    ]

    assert _build_recommendations([], kpis, None) == []
