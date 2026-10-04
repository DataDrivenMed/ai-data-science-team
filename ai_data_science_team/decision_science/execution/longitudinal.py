from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.genmod.cov_struct import Exchangeable, Independence
from statsmodels.regression.mixed_linear_model import MixedLM

from .common import ExecutionResult, coefficient_table, design_matrix, require_columns


class LongitudinalEngine:
    """Mixed-effects and GEE execution for repeated/nested observations."""

    def mixed_effects(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        predictors: list[str],
        group: str,
        random_slope: str | None = None,
    ) -> ExecutionResult:
        columns = [outcome, group, *predictors] + ([random_slope] if random_slope else [])
        columns = list(dict.fromkeys(columns))
        require_columns(data, columns)
        working = data[columns].dropna().copy()
        y = pd.to_numeric(working[outcome], errors="raise").astype(float)
        x = design_matrix(working, predictors)
        groups = working[group]

        exog_re = None
        if random_slope:
            exog_re = sm.add_constant(
                pd.to_numeric(working[random_slope], errors="raise").astype(float)
            )

        model = MixedLM(
            endog=y,
            exog=x,
            groups=groups,
            exog_re=exog_re,
        )
        fitted = model.fit(reml=True, method="lbfgs", maxiter=500, disp=False)

        fixed_names = list(x.columns)
        params = np.asarray(fitted.fe_params, dtype=float)
        bse = np.asarray(fitted.bse_fe, dtype=float)
        estimates = {
            name: {
                "estimate": float(params[i]),
                "standard_error": float(bse[i]),
            }
            for i, name in enumerate(fixed_names)
        }

        return ExecutionResult(
            method="linear_mixed_effects",
            n=len(working),
            estimates={
                "fixed_effects": estimates,
                "random_effect_covariance": np.asarray(fitted.cov_re).tolist(),
            },
            diagnostics={
                "groups": int(pd.Series(groups).nunique()),
                "converged": bool(fitted.converged),
                "log_likelihood": float(fitted.llf),
                "aic": float(fitted.aic) if np.isfinite(fitted.aic) else None,
                "bic": float(fitted.bic) if np.isfinite(fitted.bic) else None,
            },
            assumptions_checked={
                "clustering_modeled": True,
                "convergence_checked": True,
                "random_effect_distribution_checked": None,
            },
            warnings=(
                [] if fitted.converged else ["Mixed-effects optimizer did not converge."]
            ),
            metadata={"random_slope": random_slope},
        )

    def gee(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        predictors: list[str],
        group: str,
        binary_outcome: bool = False,
        correlation: str = "exchangeable",
    ) -> ExecutionResult:
        require_columns(data, [outcome, group, *predictors])
        working = data[[outcome, group, *predictors]].dropna().copy()
        y = pd.to_numeric(working[outcome], errors="raise")
        if binary_outcome:
            y = y.astype(int)
            if set(y.unique()) - {0, 1}:
                raise ValueError("Binary GEE outcome must be coded 0/1.")
            family = sm.families.Binomial()
        else:
            y = y.astype(float)
            family = sm.families.Gaussian()

        x = design_matrix(working, predictors)
        cov_struct = Exchangeable() if correlation == "exchangeable" else Independence()
        fitted = sm.GEE(
            y,
            x,
            groups=working[group],
            family=family,
            cov_struct=cov_struct,
        ).fit()

        return ExecutionResult(
            method="generalized_estimating_equations",
            n=len(working),
            estimates={"coefficients": coefficient_table(fitted)},
            diagnostics={
                "groups": int(working[group].nunique()),
                "scale": float(fitted.scale),
            },
            assumptions_checked={
                "clustering_modeled": True,
                "working_correlation_declared": True,
                "robust_covariance_used": True,
            },
            metadata={
                "binary_outcome": binary_outcome,
                "correlation": correlation,
            },
        )
