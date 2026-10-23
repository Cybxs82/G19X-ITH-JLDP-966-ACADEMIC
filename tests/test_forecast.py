from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from backend.repositories.financial_repository import repository
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


def test_monthly_forecast_aggregates_daily_values_and_confidence() -> None:
    first_day = date(2026, 1, 1)
    daily_values = [
        (first_day + timedelta(days=offset), Decimal(200 + offset * 2 + (offset % 7) * 5))
        for offset in range(180)
    ]

    forecast = calculate_daily_forecast(daily_values, 90)

    assert forecast is not None
    expected_by_month = defaultdict(Decimal)
    for point in forecast.values:
        expected_by_month[point.target_date.replace(day=1)] += point.predicted_value
    assert {point.period: point.days for point in forecast.monthly_values} == {
        date(2026, 6, 1): 1,
        date(2026, 7, 1): 31,
        date(2026, 8, 1): 31,
        date(2026, 9, 1): 27,
    }
    for point in forecast.monthly_values:
        assert abs(point.predicted_value - expected_by_month[point.period]) < Decimal("0.01")
        assert point.lower_bound <= point.predicted_value <= point.upper_bound


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


def test_dashboard_forecast_uses_history_before_selected_report_period(monkeypatch) -> None:
    first_day = date(2026, 1, 1)
    last_day = first_day + timedelta(days=199)
    report_from = last_day - timedelta(days=29)

    class FakeCursor:
        def __init__(self) -> None:
            self.result = None
            self.rows = []
            self.statements = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def execute(self, statement, parameters=None) -> None:
            normalized = " ".join(statement.split()).lower()
            self.statements.append((normalized, parameters))
            if normalized.startswith("select min(fecha_transaccion)"):
                self.result = (first_day, last_day)
            elif normalized.startswith("select calendar.day::date"):
                training_start = parameters[0]
                self.rows = [
                    (training_start + timedelta(days=offset), Decimal(1000 + offset * 3))
                    for offset in range(180)
                ]
            else:
                raise AssertionError("Unexpected query: %s" % normalized)

        def fetchone(self):
            return self.result

        def fetchall(self):
            return self.rows

    class FakeConnection:
        def __init__(self) -> None:
            self.fake_cursor = FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def cursor(self):
            return self.fake_cursor

    connection = FakeConnection()
    monkeypatch.setattr(
        "backend.repositories.financial_repository.get_db_connection",
        lambda: connection,
    )

    forecast = repository.forecast(30, report_from, last_day, 2)

    date_query, date_params = connection.fake_cursor.statements[0]
    training_query, training_params = connection.fake_cursor.statements[1]
    assert "fecha_transaccion >= " not in date_query
    assert date_params == (last_day, last_day, 2, 2)
    assert "generate_series" in training_query
    assert training_params == (first_day + timedelta(days=20), last_day, 2, 2)
    assert forecast.model_name == "regresion_lineal_diaria_v1"
    assert len(forecast.values) == 30
    assert sum(point.days for point in forecast.monthly_values) == 30
