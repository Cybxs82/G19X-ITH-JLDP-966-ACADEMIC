from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from .schemas import (
    AlertResponse,
    AlertSeverity,
    AlertStatus,
    FeedbackCreate,
    FeedbackResponse,
    ForecastPointResponse,
    ForecastResponse,
    KpiResponse,
    RecommendationResponse,
    SyncResponse,
)


class InMemoryRepository:
    """Repositorio de desarrollo; reemplazable por una implementacion PostgreSQL."""

    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        current_period = date.today().replace(day=1)
        self._last_sync = now
        self._next_alert_id = 4
        self._next_feedback_id = 1
        self._next_sync_id = 2
        self._kpis = [
            KpiResponse(id=1, code="liquidez_inmediata", name="Liquidez inmediata", category="liquidez", value=Decimal("2.48"), period=current_period, change_pct=Decimal("8.4")),
            KpiResponse(id=2, code="margen_operativo", name="Margen operativo", category="rentabilidad", value=Decimal("18.6"), period=current_period, change_pct=Decimal("2.1")),
            KpiResponse(id=3, code="ingresos_acumulados", name="Ingresos acumulados", category="rentabilidad", value=Decimal("24800000"), period=current_period, change_pct=Decimal("12.7")),
            KpiResponse(id=4, code="desviacion_presupuestal", name="Desviacion presupuestal", category="presupuesto", value=Decimal("-3.2"), period=current_period, change_pct=Decimal("0")),
        ]
        self._alerts = [
            AlertResponse(id=1, kpi_id=4, period=date(2026, 3, 18), deviation_pct=Decimal("14.2"), severity=AlertSeverity.alta, status=AlertStatus.activa, detected_at=now),
            AlertResponse(id=2, kpi_id=4, period=date(2026, 3, 16), deviation_pct=Decimal("7.8"), severity=AlertSeverity.media, status=AlertStatus.activa, detected_at=now),
            AlertResponse(id=3, kpi_id=4, period=date(2026, 3, 12), deviation_pct=Decimal("5.6"), severity=AlertSeverity.media, status=AlertStatus.activa, detected_at=now),
        ]
        self._recommendations = [
            RecommendationResponse(id=1, period=current_period, generated_text="Revisar la renovacion de proveedores de tecnologia: el gasto supera el presupuesto y concentra la mayor desviacion mensual.", model_name="gpt-4o-mini", generated_at=now),
            RecommendationResponse(id=2, period=current_period, generated_text="Acelerar la cobranza de cuentas por cobrar para liberar caja durante el proximo trimestre.", model_name="gpt-4o-mini", generated_at=now),
        ]

    def list_kpis(self, period_from: Optional[date] = None, period_to: Optional[date] = None, cost_center_id: Optional[int] = None) -> List[KpiResponse]:
        return [
            item for item in self._kpis
            if (period_from is None or item.period >= period_from)
            and (period_to is None or item.period <= period_to)
            and (cost_center_id is None or item.cost_center_id == cost_center_id)
        ]

    def forecast(self, horizon_days: int) -> ForecastResponse:
        now = datetime.now(timezone.utc)
        start = date.today()
        values = []
        for offset in range(0, horizon_days + 1, 30):
            predicted = Decimal("5800000") + Decimal(offset) * Decimal("12000")
            spread = Decimal("250000") + Decimal(offset) * Decimal("8500")
            values.append(ForecastPointResponse(target_date=start + timedelta(days=offset), predicted_value=predicted, lower_bound=predicted - spread, upper_bound=predicted + spread))
        return ForecastResponse(forecast_run_id=1, model_name="cashflow_baseline_v1", generated_at=now, horizon_days=horizon_days, values=values)

    def list_alerts(self, status: Optional[AlertStatus] = None, severity: Optional[AlertSeverity] = None, cost_center_id: Optional[int] = None) -> List[AlertResponse]:
        return [
            item for item in self._alerts
            if (status is None or item.status == status)
            and (severity is None or item.severity == severity)
            and (cost_center_id is None or item.cost_center_id == cost_center_id)
        ]

    def update_alert(self, alert_id: int, status: AlertStatus, comment: Optional[str], attended_by: Optional[UUID]) -> Optional[AlertResponse]:
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.status = status
                alert.comment = comment
                alert.attended_by = attended_by
                alert.attended_at = datetime.now(timezone.utc) if status != AlertStatus.activa else None
                return alert
        return None

    def list_recommendations(self, period: Optional[date] = None) -> List[RecommendationResponse]:
        return [item for item in self._recommendations if period is None or item.period == period]

    def create_feedback(self, feedback: FeedbackCreate) -> FeedbackResponse:
        result = FeedbackResponse(id=self._next_feedback_id, created_at=datetime.now(timezone.utc), **feedback.model_dump())
        self._next_feedback_id += 1
        return result

    def create_sync(self, data_source_id: int) -> SyncResponse:
        started = datetime.now(timezone.utc)
        result = SyncResponse(id=self._next_sync_id, data_source_id=data_source_id, status="exitoso", started_at=started, finished_at=started, rows_ingested=0)
        self._next_sync_id += 1
        self._last_sync = started
        return result

    @property
    def last_sync(self) -> datetime:
        return self._last_sync


repository = InMemoryRepository()
