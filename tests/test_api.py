from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert response.json()["database"] in {"connected", "unavailable"}


def test_dashboard_contract() -> None:
    response = client.get("/api/v1/dashboard")
    body = response.json()
    assert response.status_code == 200
    assert len(body["kpis"]) == 4
    assert body["forecast"]["horizon_days"] == 90
    assert len(body["alerts"]) == 3


def test_alert_can_be_attended() -> None:
    response = client.patch(
        "/api/v1/alerts/1",
        json={"status": "atendida", "comment": "Validada por el analista"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "atendida"


def test_alert_filter() -> None:
    response = client.get("/api/v1/alerts", params={"status": "activa", "severity": "media"})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_forecast_accepts_only_supported_horizons() -> None:
    response = client.get("/api/v1/forecast", params={"days": 45})
    assert response.status_code == 422


def test_dashboard_rejects_inverted_period() -> None:
    response = client.get(
        "/api/v1/dashboard",
        params={"period_from": "2026-12-01", "period_to": "2026-01-01"},
    )
    assert response.status_code == 422
