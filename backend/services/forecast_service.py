from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from math import sqrt
from typing import Dict, List, Optional, Sequence, Tuple


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
class MonthlyForecastValue:
    period: date
    days: int
    predicted_value: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


@dataclass(frozen=True)
class DailyForecast:
    values: List[ForecastValue]
    backtest_mae: Decimal
    monthly_values: List[MonthlyForecastValue] = field(default_factory=list)


def _regression_parameters(values: Sequence[Decimal]) -> Tuple[float, float, float, float, float]:
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
    return intercept, slope, residual_std, mean_x, sum_squared_x


def _fit_regression(values: Sequence[Decimal], target_index: int) -> Tuple[float, float]:
    intercept, slope, residual_std, mean_x, sum_squared_x = _regression_parameters(values)
    count = len(values)
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

    _, _, residual_std, mean_x, sum_squared_x = _regression_parameters(values)
    final_values: List[ForecastValue] = []
    monthly_predictions: Dict[date, Dict[str, float]] = {}
    last_date = daily_values[-1][0]
    for offset in range(horizon_days):
        target_index = len(values) + offset
        predicted, prediction_error = _fit_regression(values, target_index)
        center = Decimal(str(predicted))
        spread = Decimal(str(prediction_error * CONFIDENCE_Z_80))
        target_date = last_date + timedelta(days=offset + 1)
        final_values.append(
            ForecastValue(
                target_date=target_date,
                predicted_value=center,
                lower_bound=center - spread,
                upper_bound=center + spread,
            )
        )
        month = target_date.replace(day=1)
        monthly = monthly_predictions.setdefault(month, {"days": 0, "predicted": 0.0, "index_sum": 0.0})
        monthly["days"] += 1
        monthly["predicted"] += predicted
        monthly["index_sum"] += target_index

    monthly_values = []
    for month, monthly in monthly_predictions.items():
        days = int(monthly["days"])
        sum_centered_indices = monthly["index_sum"] - days * mean_x
        sum_variance = residual_std**2 * (
            days + days**2 / len(values) + sum_centered_indices**2 / sum_squared_x
        )
        spread = sqrt(sum_variance) * CONFIDENCE_Z_80
        center = monthly["predicted"]
        monthly_values.append(
            MonthlyForecastValue(
                period=month,
                days=days,
                predicted_value=Decimal(str(center)),
                lower_bound=Decimal(str(center - spread)),
                upper_bound=Decimal(str(center + spread)),
            )
        )
    return DailyForecast(
        values=final_values,
        monthly_values=monthly_values,
        backtest_mae=Decimal(str(mae)),
    )
