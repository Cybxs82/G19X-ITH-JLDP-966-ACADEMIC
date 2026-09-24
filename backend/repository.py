from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from .database import get_db_connection
from .schemas import (
    AlertResponse,
    AlertSeverity,
    AlertStatus,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackType,
    ForecastPointResponse,
    ForecastResponse,
    KpiResponse,
    RecommendationResponse,
    SyncResponse,
)


class InMemoryRepository:
    """Repositorio basado en PostgreSQL para la plataforma financiera."""

    def __init__(self) -> None:
        self._last_sync = datetime.now(timezone.utc)
        self._ensure_seed_data()

    def _ensure_seed_data(self) -> None:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                current_period = date.today().replace(day=1)
                cursor.execute(
                    """
                    INSERT INTO kpi_definitions (id, code, name, category, formula_description)
                    VALUES
                        (1, 'liquidez_inmediata', 'Liquidez inmediata', 'liquidez', 'Activo circulante / pasivo circulante'),
                        (2, 'margen_operativo', 'Margen operativo', 'rentabilidad', 'EBITDA / ingresos totales'),
                        (3, 'ingresos_acumulados', 'Ingresos acumulados', 'rentabilidad', 'Total de ingresos acumulados del periodo'),
                        (4, 'desviacion_presupuestal', 'Desviación presupuestal', 'presupuesto', 'Desviación real frente al presupuesto')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
                cursor.execute(
                    "DELETE FROM kpi_values WHERE id NOT IN (1, 2, 3, 4)"
                )
                cursor.execute(
                    """
                    INSERT INTO kpi_values (id, kpi_id, cost_center_id, period, value, calculated_at)
                    VALUES
                        (1, 1, NULL, %s, 2.48, %s),
                        (2, 2, NULL, %s, 18.6, %s),
                        (3, 3, NULL, %s, 24800000, %s),
                        (4, 4, NULL, %s, -3.2, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        kpi_id = EXCLUDED.kpi_id,
                        cost_center_id = EXCLUDED.cost_center_id,
                        period = EXCLUDED.period,
                        value = EXCLUDED.value,
                        calculated_at = EXCLUDED.calculated_at
                    """,
                    (
                        current_period,
                        datetime.now(timezone.utc),
                        current_period,
                        datetime.now(timezone.utc),
                        current_period,
                        datetime.now(timezone.utc),
                        current_period,
                        datetime.now(timezone.utc),
                    ),
                )

                now = datetime.now(timezone.utc)
                cursor.execute("DELETE FROM alerts WHERE id NOT IN (1, 2, 3)")
                cursor.execute(
                    """
                    INSERT INTO alerts (id, kpi_id, cost_center_id, period, deviation_pct, severity, status, detected_at)
                    VALUES
                        (1, 4, NULL, %s, 14.2, 'alta', 'activa', %s),
                        (2, 4, NULL, %s, 7.8, 'media', 'activa', %s),
                        (3, 4, NULL, %s, 5.6, 'media', 'activa', %s)
                    ON CONFLICT (id) DO UPDATE SET
                        kpi_id = EXCLUDED.kpi_id,
                        cost_center_id = EXCLUDED.cost_center_id,
                        period = EXCLUDED.period,
                        deviation_pct = EXCLUDED.deviation_pct,
                        severity = EXCLUDED.severity,
                        status = EXCLUDED.status,
                        detected_at = EXCLUDED.detected_at
                    """,
                    (
                        date(2026, 3, 18),
                        now,
                        date(2026, 3, 16),
                        now,
                        date(2026, 3, 12),
                        now,
                    ),
                )

                cursor.execute("DELETE FROM ai_recommendations WHERE id NOT IN (1, 2)")
                now = datetime.now(timezone.utc)
                cursor.execute(
                    """
                    INSERT INTO ai_recommendations (id, period, prompt_used, generated_text, model_name, generated_at)
                    VALUES
                        (1, %s, %s, %s, %s, %s),
                        (2, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        period = EXCLUDED.period,
                        prompt_used = EXCLUDED.prompt_used,
                        generated_text = EXCLUDED.generated_text,
                        model_name = EXCLUDED.model_name,
                        generated_at = EXCLUDED.generated_at
                    """,
                    (
                        date.today().replace(day=1),
                        'Resumen ejecutivo del periodo financiero actual.',
                        'Revisar la renovacion de proveedores de tecnologia: el gasto supera el presupuesto y concentra la mayor desviacion mensual.',
                        'gpt-4o-mini',
                        now,
                        date.today().replace(day=1),
                        'Resumen ejecutivo del periodo financiero actual.',
                        'Acelerar la cobranza de cuentas por cobrar para liberar caja durante el proximo trimestre.',
                        'gpt-4o-mini',
                        now,
                    ),
                )

                cursor.execute("SELECT COUNT(*) FROM forecast_runs WHERE id = 1")
                if cursor.fetchone()[0] == 0:
                    now = datetime.now(timezone.utc)
                    start = date.today()
                    cursor.execute(
                        """
                        INSERT INTO forecast_runs (id, model_name, run_at, training_data_from, training_data_to, notes)
                        VALUES (1, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id
                        """,
                        ("cashflow_baseline_v1", now, start - timedelta(days=365), start, "Modelo de referencia para flujo de caja"),
                    )
                    forecast_row = cursor.fetchone()
                    forecast_run_id = forecast_row[0] if forecast_row is not None else 1
                    for offset in (0, 30, 60, 90):
                        target_date = start + timedelta(days=offset)
                        predicted = Decimal("5800000") + Decimal(offset) * Decimal("12000")
                        spread = Decimal("250000") + Decimal(offset) * Decimal("8500")
                        cursor.execute(
                            """
                            INSERT INTO forecast_values (forecast_run_id, target_date, predicted_value, lower_bound, upper_bound)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (forecast_run_id, target_date) DO UPDATE SET
                                predicted_value = EXCLUDED.predicted_value,
                                lower_bound = EXCLUDED.lower_bound,
                                upper_bound = EXCLUDED.upper_bound
                            """,
                            (forecast_run_id, target_date, predicted, predicted - spread, predicted + spread),
                        )

                cursor.execute("SELECT max(finished_at) FROM sync_logs")
                if cursor.fetchone()[0] is None:
                    cursor.execute(
                        "INSERT INTO data_sources (name, type, connection_config, is_active) VALUES (%s, %s, %s::jsonb, %s) RETURNING id",
                        ("ERP demo", "erp", '{"source": "demo"}', True),
                    )
                    data_source_id = cursor.fetchone()[0]
                    now = datetime.now(timezone.utc)
                    cursor.execute(
                        """
                        INSERT INTO sync_logs (data_source_id, started_at, finished_at, status, rows_ingested, error_message)
                        VALUES (%s, %s, %s, 'exitoso', 0, NULL)
                        """,
                        (data_source_id, now, now),
                    )

                conn.commit()

    def _fetch_kpis(self, period_from: Optional[date], period_to: Optional[date], cost_center_id: Optional[int]) -> List[KpiResponse]:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT kv.id, kd.code, kd.name, kd.category, kv.value, kv.period, kv.cost_center_id
                    FROM kpi_values kv
                    JOIN kpi_definitions kd ON kd.id = kv.kpi_id
                    WHERE (%s::date IS NULL OR kv.period >= %s)
                      AND (%s::date IS NULL OR kv.period <= %s)
                      AND (%s IS NULL OR kv.cost_center_id = %s)
                    ORDER BY kv.period DESC, kd.id ASC
                """
                cursor.execute(query, (period_from, period_from, period_to, period_to, cost_center_id, cost_center_id))
                rows = cursor.fetchall()

        result: List[KpiResponse] = []
        for row in rows:
            change_pct = self._compute_change_pct(row[2], row[5], row[3])
            result.append(
                KpiResponse(
                    id=row[0],
                    code=row[1],
                    name=row[2],
                    category=row[3],
                    value=Decimal(str(row[4])),
                    period=row[5],
                    cost_center_id=row[6],
                    change_pct=change_pct,
                )
            )
        return result

    def _compute_change_pct(self, kpi_name: str, period: date, category: str) -> Optional[Decimal]:
        # La comparación se hace contra el mismo KPI en el periodo anterior si existe.
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT kv.value
                    FROM kpi_values kv
                    JOIN kpi_definitions kd ON kd.id = kv.kpi_id
                    WHERE kd.name = %s
                      AND kv.period < %s
                    ORDER BY kv.period DESC
                    LIMIT 1
                    """,
                    (kpi_name, period),
                )
                prev_row = cursor.fetchone()
                if prev_row is None:
                    return None
                current_value = self._current_kpi_value(kpi_name, period)
                previous_value = Decimal(str(prev_row[0]))
                if previous_value == 0:
                    return None
                return ((current_value - previous_value) / previous_value) * Decimal("100")

    def _current_kpi_value(self, kpi_name: str, period: date) -> Decimal:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT kv.value
                    FROM kpi_values kv
                    JOIN kpi_definitions kd ON kd.id = kv.kpi_id
                    WHERE kd.name = %s AND kv.period = %s
                    ORDER BY kv.id DESC
                    LIMIT 1
                    """,
                    (kpi_name, period),
                )
                row = cursor.fetchone()
                if row is None:
                    return Decimal("0")
                return Decimal(str(row[0]))

    def list_kpis(
        self,
        period_from: Optional[date] = None,
        period_to: Optional[date] = None,
        cost_center_id: Optional[int] = None,
    ) -> List[KpiResponse]:
        return self._fetch_kpis(period_from, period_to, cost_center_id)

    def forecast(self, horizon_days: int) -> ForecastResponse:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT fr.id, fr.model_name, fr.run_at, fv.target_date, fv.predicted_value, fv.lower_bound, fv.upper_bound
                    FROM forecast_runs fr
                    JOIN forecast_values fv ON fv.forecast_run_id = fr.id
                    WHERE fv.target_date <= %s
                    ORDER BY fv.target_date ASC
                    LIMIT %s
                    """,
                    ((date.today() + timedelta(days=horizon_days)), horizon_days + 1),
                )
                rows = cursor.fetchall()

        if not rows:
            self._ensure_seed_data()
            return self.forecast(horizon_days)

        first_row = rows[0]
        values = [
            ForecastPointResponse(
                target_date=row[3],
                predicted_value=Decimal(str(row[4])),
                lower_bound=Decimal(str(row[5])) if row[5] is not None else None,
                upper_bound=Decimal(str(row[6])) if row[6] is not None else None,
            )
            for row in rows
        ]
        return ForecastResponse(
            forecast_run_id=first_row[0],
            model_name=first_row[1],
            generated_at=first_row[2],
            horizon_days=horizon_days,
            values=values,
        )

    def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        cost_center_id: Optional[int] = None,
    ) -> List[AlertResponse]:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT id, kpi_id, cost_center_id, period, deviation_pct, severity, status, detected_at, attended_by, attended_at, comment
                    FROM alerts
                    WHERE (%s::text IS NULL OR status = %s)
                      AND (%s::text IS NULL OR severity = %s)
                      AND (%s IS NULL OR cost_center_id = %s)
                    ORDER BY deviation_pct DESC, detected_at DESC
                """
                cursor.execute(query, (status.value if status else None, status.value if status else None, severity.value if severity else None, severity.value if severity else None, cost_center_id, cost_center_id))
                rows = cursor.fetchall()

        return [
            AlertResponse(
                id=row[0],
                kpi_id=row[1],
                cost_center_id=row[2],
                period=row[3],
                deviation_pct=Decimal(str(row[4])),
                severity=AlertSeverity(row[5]),
                status=AlertStatus(row[6]),
                detected_at=row[7],
                attended_by=row[8],
                attended_at=row[9],
                comment=row[10],
            )
            for row in rows
        ]

    def update_alert(
        self,
        alert_id: int,
        status: AlertStatus,
        comment: Optional[str],
        attended_by: Optional[UUID],
    ) -> Optional[AlertResponse]:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE alerts
                    SET status = %s,
                        comment = %s,
                        attended_by = %s,
                        attended_at = %s
                    WHERE id = %s
                    RETURNING id, kpi_id, cost_center_id, period, deviation_pct, severity, status, detected_at, attended_by, attended_at, comment
                    """,
                    (status.value, comment, str(attended_by) if attended_by else None, datetime.now(timezone.utc) if status != AlertStatus.activa else None, alert_id),
                )
                row = cursor.fetchone()
                conn.commit()

        if row is None:
            return None

        return AlertResponse(
            id=row[0],
            kpi_id=row[1],
            cost_center_id=row[2],
            period=row[3],
            deviation_pct=Decimal(str(row[4])),
            severity=AlertSeverity(row[5]),
            status=AlertStatus(row[6]),
            detected_at=row[7],
            attended_by=row[8],
            attended_at=row[9],
            comment=row[10],
        )

    def list_recommendations(self, period: Optional[date] = None) -> List[RecommendationResponse]:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT id, period, generated_text, model_name, generated_at
                    FROM ai_recommendations
                    WHERE %s::date IS NULL OR period = %s
                    ORDER BY generated_at DESC
                """
                cursor.execute(query, (period, period))
                rows = cursor.fetchall()

        return [
            RecommendationResponse(
                id=row[0],
                period=row[1],
                generated_text=row[2],
                model_name=row[3],
                generated_at=row[4],
            )
            for row in rows
        ]

    def create_feedback(self, feedback: FeedbackCreate) -> FeedbackResponse:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                created_at = datetime.now(timezone.utc)
                cursor.execute(
                    """
                    INSERT INTO ai_feedback (recommendation_id, user_id, feedback, comment, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, recommendation_id, user_id, feedback, comment, created_at
                    """,
                    (feedback.recommendation_id, str(feedback.user_id), feedback.feedback.value, feedback.comment, created_at),
                )
                row = cursor.fetchone()
                conn.commit()

        return FeedbackResponse(
            id=row[0],
            recommendation_id=row[1],
            user_id=row[2],
            feedback=FeedbackType(row[3]),
            comment=row[4],
            created_at=row[5],
        )

    def create_sync(self, data_source_id: int) -> SyncResponse:
        started = datetime.now(timezone.utc)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sync_logs (data_source_id, started_at, finished_at, status, rows_ingested, error_message)
                    VALUES (%s, %s, %s, 'exitoso', 0, NULL)
                    RETURNING id
                    """,
                    (data_source_id, started, started),
                )
                inserted_id = cursor.fetchone()[0]
                conn.commit()

        self._last_sync = started
        return SyncResponse(
            id=inserted_id,
            data_source_id=data_source_id,
            status="exitoso",
            started_at=started,
            finished_at=started,
            rows_ingested=0,
        )

    @property
    def last_sync(self) -> datetime:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(finished_at) FROM sync_logs")
                row = cursor.fetchone()
                self._last_sync = row[0] or datetime.now(timezone.utc)
        return self._last_sync


repository = InMemoryRepository()
