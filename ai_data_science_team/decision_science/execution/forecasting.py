from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from .common import ExecutionResult, require_columns


class ForecastEngine:
    """Univariate ARIMA forecasting with chronological holdout diagnostics."""

    def arima(
        self,
        data: pd.DataFrame,
        *,
        time: str,
        outcome: str,
        order: tuple[int, int, int] = (1, 1, 0),
        horizon: int = 5,
        holdout: int | None = None,
    ) -> ExecutionResult:
        require_columns(data, [time, outcome])
        working = data[[time, outcome]].dropna().copy()
        working[time] = pd.to_datetime(working[time], errors="raise")
        working = working.sort_values(time)
        if working[time].duplicated().any():
            raise ValueError("Forecast time column must contain unique timestamps.")
        y = pd.to_numeric(working[outcome], errors="raise").astype(float)
        if len(y) < max(12, sum(order) + 5):
            raise ValueError("Insufficient observations for ARIMA execution.")

        holdout = holdout if holdout is not None else min(max(horizon, 3), max(3, len(y) // 5))
        if holdout >= len(y) - 5:
            raise ValueError("Holdout leaves too few observations for training.")

        train = y.iloc[:-holdout]
        test = y.iloc[-holdout:]
        fitted_train = ARIMA(train, order=order).fit()
        predicted = np.asarray(fitted_train.forecast(steps=holdout), dtype=float)
        actual = test.to_numpy(dtype=float)
        mae = float(np.mean(np.abs(actual - predicted)))
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        naive = np.repeat(float(train.iloc[-1]), holdout)
        naive_mae = float(np.mean(np.abs(actual - naive)))

        final_model = ARIMA(y, order=order).fit()
        forecast = final_model.get_forecast(steps=horizon)
        mean = np.asarray(forecast.predicted_mean, dtype=float)
        ci = np.asarray(forecast.conf_int(alpha=0.05), dtype=float)

        warnings: list[str] = []
        if mae >= naive_mae:
            warnings.append("ARIMA did not outperform the last-value naive baseline on holdout data.")

        return ExecutionResult(
            method="arima_forecast",
            n=len(working),
            estimates={
                "forecast": mean.tolist(),
                "confidence_interval": ci.tolist(),
                "horizon": horizon,
            },
            diagnostics={
                "holdout_size": holdout,
                "mae": mae,
                "rmse": rmse,
                "naive_mae": naive_mae,
                "aic": float(final_model.aic),
                "bic": float(final_model.bic),
            },
            assumptions_checked={
                "chronological_validation": True,
                "unique_time_index": True,
                "baseline_comparison": True,
            },
            warnings=warnings,
            metadata={
                "order": list(order),
                "time_start": str(working[time].iloc[0]),
                "time_end": str(working[time].iloc[-1]),
            },
        )
