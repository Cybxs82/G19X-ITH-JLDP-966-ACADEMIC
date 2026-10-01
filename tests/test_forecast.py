from datetime import date, timedelta
from decimal import Decimal

from backend.services.forecast_service import calculate_daily_forecast
from backend.services.ingestion_service import _refresh_bank_forecast


def test_daily_forecast_produces_90_points_and_backtest_error() -> None:
    first_day = date(2026, 1, 1)
    daily_values = [
        (first_day + timedelta(days=offset), Decimal(200 + offset * 2 + (offset % 7) * 5))
        for offset in range(180)
    ]

    forecast = calculate_daily_forecast(daily_values)

    assert forecast is not None
    assert len(forecast.values) == 90
    assert forecast.values[0].target_date == first_day + timedelta(days=180)
    assert forecast.values[-1].target_date == first_day + timedelta(days=269)
    assert forecast.backtest_mae > 0
    assert forecast.values[0].lower_bound <= forecast.values[0].predicted_value
    assert forecast.values[0].predicted_value <= forecast.values[0].upper_bound


def test_daily_forecast_requires_six_months_of_history() -> None:
    daily_values = [(date(2026, 1, 1) + timedelta(days=offset), Decimal(offset)) for offset in range(179)]

    assert calculate_daily_forecast(daily_values) is None


def test_bank_ingestion_persists_forecast_only_with_recent_six_months() -> None:
    last_day = date.today() - timedelta(days=1)
    first_day = last_day - timedelta(days=179)

    class FakeCursor:
        def __init__(self) -> None:
            self.result = None
            self.rows = []
            self.statements = []

        def execute(self, statement, parameters=None) -> None:
            self.statements.append((statement, parameters))
            normalized = statement.lstrip().lower()
            if normalized.startswith("select min(fecha_transaccion)"):
                self.result = (first_day, last_day)
            elif normalized.startswith("select calendar.day::date"):
                self.rows = [
                    (first_day + timedelta(days=offset), Decimal("100" + str(offset % 7)))
                    for offset in range(180)
                ]
            elif normalized.startswith("insert into ejecuciones_pronostico"):
                self.result = (901,)

        def fetchone(self):
            return self.result

        def fetchall(self):
            return self.rows

    cursor = FakeCursor()
    _refresh_bank_forecast(cursor)

    run_insert = next(query for query, _ in cursor.statements if "INSERT INTO ejecuciones_pronostico" in query)
    forecast_points = [query for query, _ in cursor.statements if "INSERT INTO valores_pronostico" in query]
    assert "regresion_lineal_diaria_v1" in run_insert
    assert len(forecast_points) == 90
