from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.controllers.financial_controller import require_authenticated_user
from backend.models.schemas import AlertResponse, AlertSeverity, AlertStatus
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


def test_dashboard_contract(analyst_session) -> None:
    response = client.get("/api/v1/dashboard")
    body = response.json()
    assert response.status_code == 200
    assert isinstance(body["kpis"], list)
    assert body["forecast"]["horizon_days"] == 90
    assert isinstance(body["alerts"], list)


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


def test_dashboard_requires_session() -> None:
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 401


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
