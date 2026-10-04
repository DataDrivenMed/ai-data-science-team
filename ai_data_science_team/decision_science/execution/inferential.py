from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan

from .common import ExecutionResult, coefficient_table, design_matrix, require_columns


class InferentialEngine:
    """Transparent regression engines with uncertainty and basic diagnostics."""

    def linear_regression(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        predictors: list[str],
        robust_se: bool = True,
    ) -> ExecutionResult:
        require_columns(data, [outcome, *predictors])
        working = data[[outcome, *predictors]].dropna().copy()
        y = pd.to_numeric(working[outcome], errors="raise").astype(float)
        x = design_matrix(working, predictors)

        model = sm.OLS(y, x)
        fitted = model.fit(cov_type="HC3" if robust_se else "nonrobust")
        residuals = np.asarray(fitted.resid, dtype=float)

        bp_stat, bp_pvalue, _, _ = het_breuschpagan(residuals, np.asarray(x))
        condition_number = float(np.linalg.cond(np.asarray(x)))
        warnings: list[str] = []
        if bp_pvalue < 0.05 and not robust_se:
            warnings.append("Heteroskedasticity detected; use robust standard errors.")
        if condition_number > 1000:
            warnings.append("Design matrix has a high condition number; inspect collinearity/scaling.")

        return ExecutionResult(
            method="ordinary_least_squares",
            n=len(working),
            estimates={
                "coefficients": coefficient_table(fitted),
                "r_squared": float(fitted.rsquared),
                "adjusted_r_squared": float(fitted.rsquared_adj),
            },
            diagnostics={
                "breusch_pagan_statistic": float(bp_stat),
                "breusch_pagan_p_value": float(bp_pvalue),
                "condition_number": condition_number,
                "residual_mean": float(np.mean(residuals)),
            },
            assumptions_checked={
                "uncertainty_reported": True,
                "heteroskedasticity_checked": True,
                "collinearity_screened": True,
            },
            warnings=warnings,
            metadata={"covariance_type": fitted.cov_type},
        )

    def logistic_regression(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        predictors: list[str],
    ) -> ExecutionResult:
        require_columns(data, [outcome, *predictors])
        working = data[[outcome, *predictors]].dropna().copy()
        y = pd.to_numeric(working[outcome], errors="raise").astype(int)
        if set(y.unique()) - {0, 1}:
            raise ValueError("Logistic regression outcome must be coded 0/1.")
        x = design_matrix(working, predictors)

        fitted = sm.GLM(y, x, family=sm.families.Binomial()).fit(cov_type="HC3")
        probabilities = np.asarray(fitted.predict(x), dtype=float)
        warnings: list[str] = []
        extreme = float(((probabilities < 0.01) | (probabilities > 0.99)).mean())
        if extreme > 0.20:
            warnings.append("Many fitted probabilities are extreme; inspect separation or sparse cells.")

        coefficients = coefficient_table(fitted)
        odds_ratios = {
            name: {
                "odds_ratio": float(np.exp(values["estimate"])),
                "ci_low": float(np.exp(values["ci_low"])),
                "ci_high": float(np.exp(values["ci_high"])),
            }
            for name, values in coefficients.items()
        }

        return ExecutionResult(
            method="logistic_regression",
            n=len(working),
            estimates={
                "coefficients": coefficients,
                "odds_ratios": odds_ratios,
                "aic": float(fitted.aic),
            },
            diagnostics={
                "deviance": float(fitted.deviance),
                "pearson_chi2": float(fitted.pearson_chi2),
                "extreme_probability_fraction": extreme,
            },
            assumptions_checked={
                "binary_outcome_verified": True,
                "uncertainty_reported": True,
                "separation_screened": True,
            },
            warnings=warnings,
            metadata={"covariance_type": fitted.cov_type},
        )

    def poisson_regression(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        predictors: list[str],
        exposure: str | None = None,
    ) -> ExecutionResult:
        columns = [outcome, *predictors] + ([exposure] if exposure else [])
        require_columns(data, columns)
        working = data[columns].dropna().copy()
        y = pd.to_numeric(working[outcome], errors="raise").astype(float)
        if (y < 0).any():
            raise ValueError("Poisson outcome must be non-negative.")
        x = design_matrix(working, predictors)

        offset = None
        if exposure:
            exposure_values = pd.to_numeric(working[exposure], errors="raise").astype(float)
            if (exposure_values <= 0).any():
                raise ValueError("Exposure values must be positive.")
            offset = np.log(exposure_values)

        fitted = sm.GLM(
            y,
            x,
            family=sm.families.Poisson(),
            offset=offset,
        ).fit(cov_type="HC3")

        dispersion = float(fitted.pearson_chi2 / max(fitted.df_resid, 1))
        warnings = []
        if dispersion > 1.5:
            warnings.append("Possible overdispersion; consider negative-binomial modeling.")

        return ExecutionResult(
            method="poisson_regression",
            n=len(working),
            estimates={
                "coefficients": coefficient_table(fitted),
                "aic": float(fitted.aic),
            },
            diagnostics={
                "dispersion": dispersion,
                "deviance": float(fitted.deviance),
            },
            assumptions_checked={
                "nonnegative_outcome_verified": True,
                "overdispersion_checked": True,
                "uncertainty_reported": True,
            },
            warnings=warnings,
            metadata={"covariance_type": fitted.cov_type},
        )
