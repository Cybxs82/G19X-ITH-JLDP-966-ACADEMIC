from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ..infrastructure.database import get_db_connection
from ..services.ingestion_service import refresh_kpis_from_transactions
from ..models.schemas import (
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


class PostgreSQLRepository:
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
                    INSERT INTO definiciones_kpi (id, codigo, nombre, categoria, descripcion_formula)
                    VALUES
                        (1, 'liquidez_inmediata', 'Liquidez inmediata', 'liquidez', 'Activo circulante / pasivo circulante'),
                        (2, 'margen_operativo', 'Margen operativo', 'rentabilidad', 'EBITDA / ingresos totales'),
                        (3, 'ingresos_acumulados', 'Ingresos acumulados', 'rentabilidad', 'Total de ingresos acumulados del periodo'),
                        (4, 'desviacion_presupuestal', 'Desviación presupuestal', 'presupuesto', 'Desviación real frente al presupuesto')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
                cursor.execute(
                    "DELETE FROM valores_kpi WHERE id NOT IN (1, 2, 3, 4)"
                )
                cursor.execute(
                    """
                    INSERT INTO valores_kpi (id, definicion_kpi_id, centro_costo_id, periodo, valor, calculado_en)
                    VALUES
                        (1, 1, NULL, %s, 2.48, %s),
                        (2, 2, NULL, %s, 18.6, %s),
                        (3, 3, NULL, %s, 24800000, %s),
                        (4, 4, NULL, %s, -3.2, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        definicion_kpi_id = EXCLUDED.definicion_kpi_id,
                        centro_costo_id = EXCLUDED.centro_costo_id,
                        periodo = EXCLUDED.periodo,
                        valor = EXCLUDED.valor,
                        calculado_en = EXCLUDED.calculado_en
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
                cursor.execute("DELETE FROM alertas WHERE id NOT IN (1, 2, 3)")
                cursor.execute("SELECT setval('cuentas_id_seq', COALESCE(MAX(id), 1), TRUE) FROM cuentas")
                account_ids = {}
                for code, name in (
                    ("GASTO-TEC", "Servicios profesionales"),
                    ("GASTO-OPS", "Logística y distribución"),
                    ("GASTO-COM", "Campaña de adquisición"),
                ):
                    cursor.execute(
                        """
                        INSERT INTO cuentas (codigo, nombre, categoria)
                        VALUES (%s, %s, 'egreso')
                        ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
                        RETURNING id
                        """,
                        (code, name),
                    )
                    account_ids[code] = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO alertas (id, cuenta_id, centro_costo_id, periodo, monto_presupuestado, monto_real, desviacion_pct, severidad, estado, detectado_en)
                    VALUES
                        (1, %s, NULL, %s, 100000, 114200, 14.2, 'alta', 'nueva', %s),
                        (2, %s, NULL, %s, 100000, 107800, 7.8, 'media', 'nueva', %s),
                        (3, %s, NULL, %s, 100000, 105600, 5.6, 'media', 'nueva', %s)
                    ON CONFLICT (id) DO UPDATE SET
                        cuenta_id = EXCLUDED.cuenta_id,
                        centro_costo_id = EXCLUDED.centro_costo_id,
                        periodo = EXCLUDED.periodo,
                        monto_presupuestado = EXCLUDED.monto_presupuestado,
                        monto_real = EXCLUDED.monto_real,
                        desviacion_pct = EXCLUDED.desviacion_pct,
                        severidad = EXCLUDED.severidad,
                        estado = EXCLUDED.estado,
                        detectado_en = EXCLUDED.detectado_en
                    """,
                    (
                        account_ids["GASTO-TEC"],
                        date(2026, 3, 18),
                        now,
                        account_ids["GASTO-OPS"],
                        date(2026, 3, 16),
                        now,
                        account_ids["GASTO-COM"],
                        date(2026, 3, 12),
                        now,
                    ),
                )

                cursor.execute("DELETE FROM recomendaciones_ia WHERE id NOT IN (1, 2)")
                now = datetime.now(timezone.utc)
                cursor.execute(
                    """
                    INSERT INTO recomendaciones_ia
                        (id, usuario_id, periodo, situacion, impacto, recomendacion_texto, prioridad, evidencia, version_prompt, prompt_utilizado, texto_generado, nombre_modelo, generado_en)
                    VALUES
                        (1, NULL, %s, %s, %s, %s, 'alta', '{}'::jsonb, 'v1', %s, %s, %s, %s),
                        (2, NULL, %s, %s, %s, %s, 'media', '{}'::jsonb, 'v1', %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        periodo = EXCLUDED.periodo,
                        situacion = EXCLUDED.situacion,
                        impacto = EXCLUDED.impacto,
                        recomendacion_texto = EXCLUDED.recomendacion_texto,
                        prioridad = EXCLUDED.prioridad,
                        evidencia = EXCLUDED.evidencia,
                        version_prompt = EXCLUDED.version_prompt,
                        prompt_utilizado = EXCLUDED.prompt_utilizado,
                        texto_generado = EXCLUDED.texto_generado,
                        nombre_modelo = EXCLUDED.nombre_modelo,
                        generado_en = EXCLUDED.generado_en
                    """,
                    (
                        date.today().replace(day=1),
                        'Desviación en proveedores de tecnología.',
                        'El gasto supera el presupuesto mensual.',
                        'Revisar la renovación de proveedores de tecnología.',
                        'Resumen ejecutivo del periodo financiero actual.',
                        'Revisar la renovacion de proveedores de tecnologia: el gasto supera el presupuesto y concentra la mayor desviacion mensual.',
                        'gpt-4o-mini',
                        now,
                        date.today().replace(day=1),
                        'Ciclo de cobranza prolongado.',
                        'La cobranza lenta reduce la caja disponible.',
                        'Acelerar la cobranza de cuentas por cobrar.',
                        'Resumen ejecutivo del periodo financiero actual.',
                        'Acelerar la cobranza de cuentas por cobrar para liberar caja durante el proximo trimestre.',
                        'gpt-4o-mini',
                        now,
                    ),
                )

                cursor.execute("SELECT COUNT(*) FROM ejecuciones_pronostico WHERE id = 1")
                if cursor.fetchone()[0] == 0:
                    now = datetime.now(timezone.utc)
                    start = date.today()
                    cursor.execute(
                        """
                        INSERT INTO ejecuciones_pronostico (id, nombre_modelo, ejecutado_en, datos_entrenamiento_desde, datos_entrenamiento_hasta, notas)
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
                            INSERT INTO valores_pronostico (ejecucion_pronostico_id, fecha_objetivo, valor_predicho, limite_inferior, limite_superior)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (ejecucion_pronostico_id, fecha_objetivo) DO UPDATE SET
                                valor_predicho = EXCLUDED.valor_predicho,
                                limite_inferior = EXCLUDED.limite_inferior,
                                limite_superior = EXCLUDED.limite_superior
                            """,
                            (forecast_run_id, target_date, predicted, predicted - spread, predicted + spread),
                        )

                cursor.execute("SELECT max(finalizado_en) FROM registros_sincronizacion")
                if cursor.fetchone()[0] is None:
                    cursor.execute(
                        "INSERT INTO fuentes_datos (nombre, tipo, configuracion_conexion, esta_activa) VALUES (%s, %s, %s::jsonb, %s) RETURNING id",
                        ("ERP demo", "erp", '{"source": "demo"}', True),
                    )
                    data_source_id = cursor.fetchone()[0]
                    now = datetime.now(timezone.utc)
                    cursor.execute(
                        """
                        INSERT INTO registros_sincronizacion (fuente_datos_id, iniciado_en, finalizado_en, estado, filas_ingresadas, mensaje_error)
                        VALUES (%s, %s, %s, 'exitoso', 0, NULL)
                        """,
                        (data_source_id, now, now),
                    )

                conn.commit()

    def _fetch_kpis(self, period_from: Optional[date], period_to: Optional[date], cost_center_id: Optional[int]) -> List[KpiResponse]:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                                        SELECT kv.id, kd.codigo, kd.nombre, kd.categoria, kv.valor, kv.periodo, kv.centro_costo_id
                                        FROM valores_kpi kv
                                        JOIN definiciones_kpi kd ON kd.id = kv.definicion_kpi_id
                                        WHERE (%s::date IS NULL OR kv.periodo >= %s)
                                            AND (%s::date IS NULL OR kv.periodo <= %s)
                                            AND (%s IS NULL OR kv.centro_costo_id = %s)
                                        ORDER BY kv.periodo DESC, kd.id ASC
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
                    SELECT kv.valor
                    FROM valores_kpi kv
                    JOIN definiciones_kpi kd ON kd.id = kv.definicion_kpi_id
                                        WHERE kd.nombre = %s
                                            AND kv.periodo < %s
                                        ORDER BY kv.periodo DESC
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
                    SELECT kv.valor
                    FROM valores_kpi kv
                    JOIN definiciones_kpi kd ON kd.id = kv.definicion_kpi_id
                    WHERE kd.nombre = %s AND kv.periodo = %s
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
        refresh_kpis_from_transactions()
        return self._fetch_kpis(period_from, period_to, cost_center_id)

    def forecast(self, horizon_days: int) -> ForecastResponse:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT fr.id, fr.nombre_modelo, fr.ejecutado_en, fv.fecha_objetivo, fv.valor_predicho, fv.limite_inferior, fv.limite_superior
                    FROM ejecuciones_pronostico fr
                    JOIN valores_pronostico fv ON fv.ejecucion_pronostico_id = fr.id
                    WHERE fv.fecha_objetivo <= %s
                    ORDER BY fv.fecha_objetivo ASC
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
                                        SELECT id, cuenta_id, centro_costo_id, periodo, monto_presupuestado, monto_real, desviacion_pct, severidad, estado, detectado_en, responsable_id, atendido_por, atendido_en, comentario
                                        FROM alertas
                                        WHERE (%s::text IS NULL OR estado = %s)
                                            AND (%s::text IS NULL OR severidad = %s)
                                            AND (%s IS NULL OR centro_costo_id = %s)
                                        ORDER BY desviacion_pct DESC, detectado_en DESC
                """
                cursor.execute(query, (status.value if status else None, status.value if status else None, severity.value if severity else None, severity.value if severity else None, cost_center_id, cost_center_id))
                rows = cursor.fetchall()

        return [
            AlertResponse(
                id=row[0],
                account_id=row[1],
                cost_center_id=row[2],
                period=row[3],
                budgeted_amount=Decimal(str(row[4])),
                actual_amount=Decimal(str(row[5])),
                deviation_pct=Decimal(str(row[6])),
                severity=AlertSeverity(row[7]),
                status=AlertStatus(row[8]),
                detected_at=row[9],
                responsible_id=row[10],
                attended_by=row[11],
                attended_at=row[12],
                comment=row[13],
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
                    UPDATE alertas
                    SET estado = %s,
                        comentario = %s,
                        responsable_id = %s,
                        atendido_por = %s,
                        atendido_en = %s
                    WHERE id = %s
                    RETURNING id, cuenta_id, centro_costo_id, periodo, monto_presupuestado, monto_real, desviacion_pct, severidad, estado, detectado_en, responsable_id, atendido_por, atendido_en, comentario
                    """,
                    (status.value, comment, str(attended_by) if attended_by else None, str(attended_by) if attended_by else None, datetime.now(timezone.utc) if status in {AlertStatus.cerrada, AlertStatus.falsa} else None, alert_id),
                )
                row = cursor.fetchone()
                conn.commit()

        if row is None:
            return None

        return AlertResponse(
            id=row[0],
            account_id=row[1],
            cost_center_id=row[2],
            period=row[3],
            budgeted_amount=Decimal(str(row[4])),
            actual_amount=Decimal(str(row[5])),
            deviation_pct=Decimal(str(row[6])),
            severity=AlertSeverity(row[7]),
            status=AlertStatus(row[8]),
            detected_at=row[9],
            responsible_id=row[10],
            attended_by=row[11],
            attended_at=row[12],
            comment=row[13],
        )

    def list_recommendations(self, period: Optional[date] = None) -> List[RecommendationResponse]:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT id, usuario_id, periodo, situacion, impacto, recomendacion_texto, prioridad, evidencia, version_prompt, texto_generado, nombre_modelo, generado_en
                    FROM recomendaciones_ia
                    WHERE %s::date IS NULL OR periodo = %s
                    ORDER BY generado_en DESC
                """
                cursor.execute(query, (period, period))
                rows = cursor.fetchall()

        return [
            RecommendationResponse(
                id=row[0],
                user_id=row[1],
                period=row[2],
                situation=row[3],
                impact=row[4],
                recommendation_text=row[5],
                priority=row[6],
                evidence=row[7],
                prompt_version=row[8],
                generated_text=row[9],
                model_name=row[10],
                generated_at=row[11],
            )
            for row in rows
        ]

    def create_feedback(self, feedback: FeedbackCreate) -> FeedbackResponse:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                created_at = datetime.now(timezone.utc)
                cursor.execute(
                    """
                    INSERT INTO retroalimentacion_ia (recomendacion_id, usuario_id, retroalimentacion, comentario, creado_en)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, recomendacion_id, usuario_id, retroalimentacion, comentario, creado_en
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
                    INSERT INTO registros_sincronizacion (fuente_datos_id, iniciado_en, finalizado_en, estado, filas_ingresadas, mensaje_error)
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
                cursor.execute("SELECT MAX(finalizado_en) FROM registros_sincronizacion")
                row = cursor.fetchone()
                self._last_sync = row[0] or datetime.now(timezone.utc)
        return self._last_sync


repository = PostgreSQLRepository()
