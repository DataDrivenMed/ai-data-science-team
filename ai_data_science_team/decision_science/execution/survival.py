from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.duration.survfunc import SurvfuncRight

from .common import ExecutionResult, design_matrix, require_columns


class SurvivalEngine:
    """Kaplan-Meier and Cox proportional-hazards execution."""

    def kaplan_meier(
        self,
        data: pd.DataFrame,
        *,
        duration: str,
        event: str,
    ) -> ExecutionResult:
        require_columns(data, [duration, event])
        working = data[[duration, event]].dropna().copy()
        times = pd.to_numeric(working[duration], errors="raise").astype(float).to_numpy()
        status = pd.to_numeric(working[event], errors="raise").astype(int).to_numpy()
        if (times < 0).any():
            raise ValueError("Durations must be non-negative.")
        if set(np.unique(status)) - {0, 1}:
            raise ValueError("Event indicator must be coded 0/1.")

        fitted = SurvfuncRight(times, status)
        survival_times = np.asarray(fitted.surv_times, dtype=float)
        survival_prob = np.asarray(fitted.surv_prob, dtype=float)

        median = None
        below = np.where(survival_prob <= 0.5)[0]
        if len(below):
            median = float(survival_times[below[0]])

        return ExecutionResult(
            method="kaplan_meier",
            n=len(working),
            estimates={
                "time": survival_times.tolist(),
                "survival_probability": survival_prob.tolist(),
                "median_survival": median,
            },
            diagnostics={
                "events": int(status.sum()),
                "censored": int((1 - status).sum()),
            },
            assumptions_checked={
                "nonnegative_duration_verified": True,
                "binary_event_verified": True,
            },
        )

    def cox_ph(
        self,
        data: pd.DataFrame,
        *,
        duration: str,
        event: str,
        predictors: list[str],
        ties: str = "breslow",
        ph_alpha: float = 0.05,
    ) -> ExecutionResult:
        require_columns(data, [duration, event, *predictors])
        working = data[[duration, event, *predictors]].dropna().copy()
        times = pd.to_numeric(working[duration], errors="raise").astype(float)
        status = pd.to_numeric(working[event], errors="raise").astype(int)
        if (times < 0).any():
            raise ValueError("Durations must be non-negative.")
        if set(status.unique()) - {0, 1}:
            raise ValueError("Event indicator must be coded 0/1.")
        x = design_matrix(working, predictors, add_intercept=False)

        fitted = PHReg(
            endog=times.to_numpy(),
            exog=x.to_numpy(),
            status=status.to_numpy(),
            ties=ties,
        ).fit()

        params = np.asarray(fitted.params, dtype=float)
        se = np.asarray(fitted.bse, dtype=float)
        pvalues = np.asarray(fitted.pvalues, dtype=float)
        ci = np.asarray(fitted.conf_int(), dtype=float)
        estimates = {}
        for index, name in enumerate(x.columns):
            estimates[str(name)] = {
                "log_hazard_ratio": float(params[index]),
                "hazard_ratio": float(np.exp(params[index])),
                "standard_error": float(se[index]),
                "p_value": float(pvalues[index]),
                "ci_low": float(np.exp(ci[index, 0])),
                "ci_high": float(np.exp(ci[index, 1])),
            }

        schoenfeld = np.asarray(fitted.schoenfeld_residuals, dtype=float)
        event_mask = status.to_numpy(dtype=bool)
        log_event_time = np.log(np.maximum(times.to_numpy()[event_mask], 1e-12))
        ph_tests: dict[str, dict[str, float | None]] = {}
        ph_pass = True
        for index, name in enumerate(x.columns):
            residual = schoenfeld[event_mask, index]
            valid = np.isfinite(residual) & np.isfinite(log_event_time)
            if valid.sum() < 5 or np.nanstd(residual[valid]) == 0:
                ph_tests[str(name)] = {"correlation": None, "p_value": None}
                continue
            correlation, p_value = pearsonr(log_event_time[valid], residual[valid])
            ph_tests[str(name)] = {
                "correlation": float(correlation),
                "p_value": float(p_value),
            }
            if p_value < ph_alpha:
                ph_pass = False

        warnings: list[str] = []
        if not ph_pass:
            warnings.append(
                "Schoenfeld-residual screening suggests non-proportional hazards for at least one covariate."
            )

        return ExecutionResult(
            method="cox_proportional_hazards",
            n=len(working),
            estimates={"hazard_ratios": estimates},
            diagnostics={
                "events": int(status.sum()),
                "censored": int((1 - status).sum()),
                "log_likelihood": float(fitted.llf),
                "proportional_hazards_tests": ph_tests,
                "proportional_hazards_alpha": ph_alpha,
            },
            assumptions_checked={
                "nonnegative_duration_verified": True,
                "binary_event_verified": True,
                "proportional_hazards_checked": True,
                "proportional_hazards_screen_passed": ph_pass,
            },
            warnings=warnings,
            metadata={"ties": ties},
        )
