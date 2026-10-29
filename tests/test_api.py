from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.controllers import financial_controller
from backend.controllers.financial_controller import require_authenticated_user
from backend.models.schemas import AlertResponse, AlertSeverity, AlertStatus, ForecastResponse
from backend.infrastructure import database
from backend.infrastructure.config import Settings
from backend.infrastructure.database import get_db_connection
from main import app, repository


client = TestClient(app)


@pytest.fixture
def analyst_session():
    app.dependency_overrides[require_authenticated_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000002",
        "role": "analista",
    }
    yield
    app.dependency_overrides.pop(require_authenticated_user, None)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert response.json()["database"] in {"connected", "unavailable"}


def test_health_reports_missing_database_url(monkeypatch) -> None:
    message = (
        "Falta configurar CFO_DATABASE_URL. Define una URL de conexión a PostgreSQL "
        "en el archivo .env o en las variables de entorno."
    )
    monkeypatch.delenv("CFO_DATABASE_URL", raising=False)
    settings = Settings()
    monkeypatch.setattr(database, "get_settings", lambda: settings)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"
    assert response.json()["database_error"] == message
    assert settings.database_url == ""


def test_alert_id_sequence_is_ahead_of_existing_rows() -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(id), 0) FROM alertas")
            maximum_id = cursor.fetchone()[0]
            cursor.execute("SELECT last_value, is_called FROM alertas_id_seq")
            sequence_value, is_called = cursor.fetchone()

    assert sequence_value >= maximum_id
    assert maximum_id == 0 or is_called


def test_dashboard_contract(analyst_session) -> None:
    response = client.get("/api/v1/dashboard")
    body = response.json()
    assert response.status_code == 200
    assert isinstance(body["kpis"], list)
    assert body["forecast"]["horizon_days"] == 90
    assert isinstance(body["alerts"], list)


def test_dashboard_propagates_date_and_center_filters(monkeypatch, analyst_session) -> None:
    captured = {}

    def fake_kpis(period_from, period_to, cost_center_id):
        captured["kpis"] = (period_from, period_to, cost_center_id)
        return []

    def fake_forecast(horizon_days, period_from, period_to, cost_center_id):
        captured["forecast"] = (horizon_days, period_from, period_to, cost_center_id)
        return ForecastResponse(
            forecast_run_id=0,
            model_name="sin_datos",
            generated_at=datetime.now(timezone.utc),
            horizon_days=horizon_days,
            values=[],
        )

    def fake_alerts(*, cost_center_id, period_from, period_to):
        captured["alerts"] = (period_from, period_to, cost_center_id)
        return []

    monkeypatch.setattr(repository, "list_kpis", fake_kpis)
    monkeypatch.setattr(repository, "forecast", fake_forecast)
    monkeypatch.setattr(repository, "list_alerts", fake_alerts)
    monkeypatch.setattr(repository, "list_recommendations", lambda: [])
    monkeypatch.setattr(financial_controller, "generate_recommendations", lambda: [])

    response = client.get(
        "/api/v1/dashboard",
        params={"period_from": "2026-04-01", "period_to": "2026-09-30", "cost_center_id": 4, "horizon_days": 60},
    )

    assert response.status_code == 200
    expected_filters = (date(2026, 4, 1), date(2026, 9, 30), 4)
    assert captured["kpis"] == expected_filters
    assert captured["alerts"] == expected_filters
    assert captured["forecast"] == (60, *expected_filters)


def test_dashboard_rejects_unsupported_forecast_horizon(analyst_session) -> None:
    response = client.get("/api/v1/dashboard", params={"horizon_days": 45})

    assert response.status_code == 422


def test_dashboard_does_not_generate_recommendations(monkeypatch, analyst_session) -> None:
    generated = []
    monkeypatch.setattr(repository, "list_kpis", lambda *args: [])
    monkeypatch.setattr(repository, "forecast", lambda *args: ForecastResponse(
        forecast_run_id=0,
        model_name="sin_datos",
        generated_at=datetime.now(timezone.utc),
        horizon_days=args[0],
        values=[],
    ))
    monkeypatch.setattr(repository, "list_alerts", lambda **kwargs: [])
    monkeypatch.setattr(repository, "list_recommendations", lambda: [])
    monkeypatch.setattr(type(repository), "last_sync", property(lambda self: None))

    def fake_generate_recommendations():
        generated.append(True)
        return []

    monkeypatch.setattr(financial_controller, "generate_recommendations", fake_generate_recommendations)

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert generated == []
    assert response.json()["recommendations"] == []


def test_alert_can_be_attended(monkeypatch, analyst_session) -> None:
    updated_alert = AlertResponse(
        id=1,
        account_id=1,
        period=date(2026, 1, 1),
        budgeted_amount=Decimal("100"),
        actual_amount=Decimal("115"),
        deviation_pct=Decimal("15"),
        severity=AlertSeverity.media,
        status=AlertStatus.en_revision,
        detected_at=datetime.now(timezone.utc),
    )
    updated_arguments = {}

    def fake_update_alert(*args):
        updated_arguments["values"] = args
        return updated_alert

    monkeypatch.setattr(repository, "update_alert", fake_update_alert)
    response = client.patch(
        "/api/v1/alerts/1",
        json={
            "status": "en_revision",
            "comment": "Validada por el analista",
            "attended_by": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "en_revision"
    assert str(updated_arguments["values"][3]) == "00000000-0000-0000-0000-000000000002"


def test_alert_filter(analyst_session) -> None:
    response = client.get("/api/v1/alerts", params={"status": "nueva", "severity": "media"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_forecast_accepts_only_supported_horizons(analyst_session) -> None:
    response = client.get("/api/v1/forecast", params={"days": 45})
    assert response.status_code == 422


def test_dashboard_rejects_inverted_period(analyst_session) -> None:
    response = client.get(
        "/api/v1/dashboard",
        params={"period_from": "2026-12-01", "period_to": "2026-01-01"},
    )
    assert response.status_code == 422


def test_erp_document_ingestion_requires_session() -> None:
    response = client.post(
        "/api/v1/ingestion/documents",
        files={"file": ("erp.csv", b"fecha,monto\n2026-01-01,10", "text/csv")},
    )

    assert response.status_code == 401


def test_practice_data_cleanup_requires_session() -> None:
    response = client.delete("/api/v1/ingestion/practice-data")

    assert response.status_code == 401


def test_practice_data_cleanup_is_limited_to_ingestion_roles(monkeypatch) -> None:
    monkeypatch.setitem(
        app.dependency_overrides,
        require_authenticated_user,
        lambda: {"id": "00000000-0000-0000-0000-000000000001", "role": "cfo"},
    )
    response = client.delete("/api/v1/ingestion/practice-data")
    response = client.delete("/api/v1/ingestion/practice-data")
    assert response.status_code == 403
    assert response.status_code == 403


def test_practice_data_cleanup_returns_deleted_record_counts(monkeypatch, analyst_session) -> None:
    counts = {
        "transactions": 12,
        "budgets": 4,
        "erp_staging": 12,
        "bank_staging": 30,
        "sync_logs": 3,
        "data_sources": 3,
    }
    calls = []

    def fake_delete_practice_data():
        calls.append("delete")
        return counts

    def fake_generate_recommendations():
        calls.append("generate")

    monkeypatch.setattr(financial_controller, "delete_practice_data", fake_delete_practice_data)
    monkeypatch.setattr(financial_controller, "generate_recommendations", fake_generate_recommendations)

    response = client.delete("/api/v1/ingestion/practice-data")

    assert response.status_code == 200
    assert response.json() == counts
    assert calls == ["delete", "generate"]


def test_dashboard_requires_session() -> None:
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 401


def test_generate_recommendations_requires_session() -> None:
    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 401


def test_get_recommendations_only_lists_existing_recommendations(monkeypatch, analyst_session) -> None:
    calls = []

    def fake_list_recommendations(period):
        calls.append(("list", period))
        return []

    monkeypatch.setattr(financial_controller, "generate_recommendations", lambda: calls.append("generate"))
    monkeypatch.setattr(repository, "list_recommendations", fake_list_recommendations)

    response = client.get("/api/v1/recommendations", params={"period": "2026-10-01"})

    assert response.status_code == 200
    assert response.json() == []
    assert calls == [("list", date(2026, 10, 1))]


@pytest.mark.parametrize(
    ("route", "ingestion_function"),
    [
        ("/api/v1/ingestion/files", "ingest_file"),
        ("/api/v1/ingestion/documents", "ingest_erp_document"),
        ("/api/v1/ingestion/budgets", "ingest_budget_file"),
    ],
)
def test_ingestion_generates_recommendations_after_loading(
    monkeypatch,
    analyst_session,
    route,
    ingestion_function,
) -> None:
    calls = []
    monkeypatch.setattr(
        financial_controller,
        ingestion_function,
        lambda *args: calls.append("ingest") or {
            "sync_log_id": 1,
            "data_source_id": 1,
            "rows_ingested": 1,
            "status": "completada",
        },
    )
    monkeypatch.setattr(
        financial_controller,
        "generate_recommendations",
        lambda: calls.append("generate"),
    )

    response = client.post(
        route,
        files={"file": ("financial.csv", b"periodo,monto\n2026-01-01,10", "text/csv")},
    )

    assert response.status_code == 202
    assert calls == ["ingest", "generate"]


@pytest.mark.parametrize("role", ["cfo", "administrador"])
def test_generate_recommendations_returns_persisted_rule_shape(monkeypatch, role) -> None:
    generated_for = {}
    user_id = "00000000-0000-0000-0000-000000000002"
    monkeypatch.setitem(
        app.dependency_overrides,
        require_authenticated_user,
        lambda: {"id": user_id, "role": role},
    )

    def fake_generate_recommendations(requested_user_id):
        generated_for["user_id"] = str(requested_user_id)
        return [
            {
                "id": 44,
                "user_id": requested_user_id,
                "period": date(2026, 10, 1),
                "situation": "El margen operativo es negativo.",
                "impact": "Margen: -2%.",
                "recommendation_text": "Revisar gastos.",
                "priority": "alta",
                "evidence": {"regla": "margen_operativo_negativo", "alertas_ids": [], "kpis_ids": [11]},
                "prompt_version": "reglas-v1",
                "generated_text": "Revisar gastos.",
                "model_name": "reglas-v1",
                "generated_at": datetime.now(timezone.utc),
            }
        ]

    monkeypatch.setattr(financial_controller, "generate_recommendations", fake_generate_recommendations)

    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 200
    assert generated_for["user_id"] == user_id
    assert response.json()[0]["model_name"] == "reglas-v1"
    assert response.json()[0]["prompt_version"] == "reglas-v1"
    assert response.json()[0]["evidence"]["kpis_ids"] == [11]


def test_analyst_cannot_generate_recommendations(analyst_session) -> None:
    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 403


def test_cost_centers_require_session() -> None:
    response = client.get("/api/v1/cost-centers")

    assert response.status_code == 401


def test_cfo_cannot_update_alert(monkeypatch) -> None:
    app.dependency_overrides[require_authenticated_user] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "role": "cfo",
    }
    try:
        response = client.patch(
            "/api/v1/alerts/1",
            json={"status": "en_revision", "comment": "Revisión"},
        )
    finally:
        app.dependency_overrides.pop(require_authenticated_user, None)

    assert response.status_code == 403


def test_budget_ingestion_requires_session() -> None:
    response = client.post(
        "/api/v1/ingestion/budgets",
        files={"file": ("presupuesto.csv", b"periodo,monto_presupuestado,cuenta\n2026-01-01,100,5001", "text/csv")},
    )

    assert response.status_code == 401
