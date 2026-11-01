from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from backend.services import recommendation_service
from backend.services.forecast_service import DailyForecast, ForecastValue
from backend.services.recommendation_service import (
    RULES_VERSION,
    _build_recommendations,
    _persist_recommendations,
)
from backend.repositories.financial_repository import _calculate_kpi_change


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


def test_kpi_change_uses_percentage_points_for_rate_kpis() -> None:
    assert _calculate_kpi_change(
        "margen_operativo",
        Decimal("24.2866"),
        Decimal("-19.8436"),
    ) == Decimal("44.1302")
    assert _calculate_kpi_change(
        "desviacion_presupuestal",
        Decimal("101.8605"),
        Decimal("256.3455"),
    ) == Decimal("-154.4850")


def test_kpi_change_uses_absolute_previous_value_for_currency() -> None:
    assert _calculate_kpi_change(
        "flujo_neto_bancario",
        Decimal("881000"),
        Decimal("1615700"),
    ).quantize(Decimal("0.01")) == Decimal("-45.47")


def test_missing_sources_are_reported_without_invented_values() -> None:
    recommendations = _build_recommendations(
        [],
        [],
        None,
        alert_data_available=False,
        missing_kpi_codes=["flujo_neto_bancario", "margen_operativo"],
        forecast_unavailable_reason="No hay histórico bancario.",
    )

    assert len(recommendations) == 1
    missing_data = recommendations[0]
    assert missing_data["regla"] == "datos_insuficientes"
    assert "No se calcularon impactos ni resultados" in missing_data["impacto"]
    assert missing_data["evidencia"]["alertas_ids"] == []
    assert missing_data["evidencia"]["kpis_ids"] == []
    assert len(missing_data["evidencia"]["fuentes_faltantes"]) == 3


def test_recommendations_are_persisted_as_rules_with_version_and_evidence() -> None:
    generated_at = datetime.now(timezone.utc)

    class FakeCursor:
        def __init__(self, persisted_user_id=None) -> None:
            self.parameters = []
            self.statements = []
            self.persisted_user_id = persisted_user_id

        def execute(self, statement, parameters) -> None:
            self.statements.append(statement)
            self.parameters.append(parameters)

        def fetchone(self):
            return 501, generated_at, self.persisted_user_id

    recommendation = {
        "regla": "flujo_neto_bancario_negativo",
        "periodo": date(2026, 10, 1),
        "situacion": "El flujo neto bancario es negativo.",
        "impacto": "El flujo neto reduce caja en 50.",
        "recomendacion_texto": "Validar cobros y pagos.",
        "prioridad": "alta",
        "evidencia": {"regla": "flujo_neto_bancario_negativo", "alertas_ids": [], "kpis_ids": [21]},
    }
    user_id = UUID("00000000-0000-0000-0000-000000000002")
    cursor = FakeCursor(persisted_user_id=user_id)

    persisted = _persist_recommendations(cursor, [recommendation], user_id)

    inserted_values = cursor.parameters[0]
    assert len(cursor.statements) == 1
    assert "INSERT INTO recomendaciones_ia" in cursor.statements[0]
    assert "ON CONFLICT (periodo, (evidencia->>'regla'))" in cursor.statements[0]
    assert inserted_values[0] == str(user_id)
    assert inserted_values[6] == '{"regla": "flujo_neto_bancario_negativo", "alertas_ids": [], "kpis_ids": [21]}'
    assert inserted_values[7] == RULES_VERSION
    assert inserted_values[8] == "flujo_neto_bancario_negativo"
    assert inserted_values[9] == (
        "Situación: El flujo neto bancario es negativo.\n"
        "Impacto: El flujo neto reduce caja en 50.\n"
        "Recomendación: Validar cobros y pagos."
    )
    assert inserted_values[10] == RULES_VERSION
    assert persisted[0]["id"] == 501
    assert persisted[0]["evidence"] == recommendation["evidencia"]
    assert persisted[0]["model_name"] == RULES_VERSION
    assert persisted[0]["generated_at"] == generated_at


def test_anonymous_and_cfo_generations_reuse_the_same_rule_record() -> None:
    generated_at = datetime.now(timezone.utc)

    class FakeCursor:
        def __init__(self) -> None:
            self.statements = []
            self.parameters = []
            self.user_id = None

        def execute(self, statement, parameters) -> None:
            self.statements.append(" ".join(statement.split()))
            self.parameters.append(parameters)
            self.user_id = parameters[0] or self.user_id

        def fetchone(self):
            return 501, generated_at, self.user_id

    recommendation = {
        "regla": "flujo_neto_bancario_negativo",
        "periodo": date(2026, 10, 1),
        "situacion": "El flujo neto bancario es negativo.",
        "impacto": "El flujo neto reduce caja en 50.",
        "recomendacion_texto": "Validar cobros y pagos.",
        "prioridad": "alta",
        "evidencia": {"regla": "flujo_neto_bancario_negativo", "alertas_ids": [], "kpis_ids": [21]},
    }
    cfo_user_id = UUID("00000000-0000-0000-0000-000000000002")
    cursor = FakeCursor()

    anonymous_saved = _persist_recommendations(cursor, [recommendation], None)
    cfo_saved = _persist_recommendations(cursor, [recommendation], cfo_user_id)

    assert len(cursor.statements) == 2
    for statement in cursor.statements:
        assert "ON CONFLICT (periodo, (evidencia->>'regla'))" in statement
        assert "usuario_id = COALESCE(EXCLUDED.usuario_id, recomendaciones_ia.usuario_id)" in statement
    assert anonymous_saved[0]["id"] == cfo_saved[0]["id"] == 501
    assert anonymous_saved[0]["user_id"] is None
    assert str(cfo_saved[0]["user_id"]) == str(cfo_user_id)


def test_generate_recommendations_persists_explicit_missing_data_notice(monkeypatch) -> None:
    generated_at = datetime.now(timezone.utc)

    class FakeCursor:
        def __init__(self) -> None:
            self.result = None
            self.rows = []
            self.inserted_values = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def execute(self, statement, parameters=None) -> None:
            normalized = " ".join(statement.split()).lower()
            if normalized.startswith("select setval"):
                self.result = None
            elif normalized.startswith("select exists"):
                self.result = (False,)
            elif normalized.startswith("select id, periodo"):
                self.rows = []
            elif normalized.startswith("select distinct on"):
                self.rows = []
            elif normalized.startswith("select min(fecha_transaccion)"):
                self.result = (None, None)
            elif normalized.startswith("insert into recomendaciones_ia"):
                self.inserted_values = parameters
                self.result = (701, generated_at, parameters[0])
            else:
                raise AssertionError("Unexpected query: %s" % normalized)

        def fetchone(self):
            return self.result

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def cursor(self):
            return self.fake_cursor

        def commit(self) -> None:
            self.committed = True

    connection = FakeConnection()
    monkeypatch.setattr(recommendation_service, "get_db_connection", lambda: connection)

    generated = recommendation_service.generate_recommendations()

    assert connection.committed
    assert len(generated) == 1
    assert generated[0]["id"] == 701
    assert generated[0]["model_name"] == RULES_VERSION
    assert generated[0]["situation"].startswith("No hay datos suficientes")
    assert generated[0]["evidence"]["alertas_ids"] == []
    assert generated[0]["evidence"]["kpis_ids"] == []
    assert connection.fake_cursor.inserted_values[7] == RULES_VERSION
    assert connection.fake_cursor.inserted_values[10] == RULES_VERSION
