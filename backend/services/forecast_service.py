from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from math import sqrt
from typing import List, Optional, Sequence, Tuple


MINIMUM_TRAINING_DAYS = 180
FORECAST_HORIZON_DAYS = 90
HOLDOUT_DAYS = 30
CONFIDENCE_Z_80 = 1.2815515655446004


@dataclass(frozen=True)
class ForecastValue:
    target_date: date
    predicted_value: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


@dataclass(frozen=True)
class DailyForecast:
    values: List[ForecastValue]
    backtest_mae: Decimal


def _fit_regression(values: Sequence[Decimal], target_index: int) -> Tuple[float, float]:
    count = len(values)
    if count < 3:
        raise ValueError("Se requieren al menos 3 observaciones para ajustar el forecast")

    numeric_values = [float(value) for value in values]
    mean_x = (count - 1) / 2
    mean_y = sum(numeric_values) / count
    sum_squared_x = sum((index - mean_x) ** 2 for index in range(count))
    slope = sum((index - mean_x) * (value - mean_y) for index, value in enumerate(numeric_values)) / sum_squared_x
    intercept = mean_y - slope * mean_x
    residuals = [value - (intercept + slope * index) for index, value in enumerate(numeric_values)]
    residual_std = sqrt(sum(residual * residual for residual in residuals) / (count - 2))
    prediction = intercept + slope * target_index
    prediction_error = residual_std * sqrt(1 + 1 / count + (target_index - mean_x) ** 2 / sum_squared_x)
    return prediction, prediction_error


def calculate_daily_forecast(
    daily_values: Sequence[Tuple[date, Decimal]],
    horizon_days: int = FORECAST_HORIZON_DAYS,
) -> Optional[DailyForecast]:
    if len(daily_values) < MINIMUM_TRAINING_DAYS:
        return None
    if horizon_days < 1:
        raise ValueError("El horizonte debe ser positivo")

    values = [amount for _, amount in daily_values]
    holdout_start = len(values) - HOLDOUT_DAYS
    errors = []
    for target_index in range(holdout_start, len(values)):
        predicted, _ = _fit_regression(values[:target_index], target_index)
        errors.append(abs(float(values[target_index]) - predicted))
    mae = sum(errors) / len(errors)

    final_values: List[ForecastValue] = []
    last_date = daily_values[-1][0]
    for offset in range(horizon_days):
        predicted, prediction_error = _fit_regression(values, len(values) + offset)
        center = Decimal(str(predicted))
        spread = Decimal(str(prediction_error * CONFIDENCE_Z_80))
        final_values.append(
            ForecastValue(
                target_date=last_date + timedelta(days=offset + 1),
                predicted_value=center,
                lower_bound=center - spread,
                upper_bound=center + spread,
            )
        )
    return DailyForecast(values=final_values, backtest_mae=Decimal(str(mae)))
