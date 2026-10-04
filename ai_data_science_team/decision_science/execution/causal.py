from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LinearRegression, LogisticRegression

from .common import ExecutionResult, design_matrix, require_columns


def _standardized_mean_difference(
    values: np.ndarray,
    treatment: np.ndarray,
    weights: np.ndarray | None = None,
) -> float:
    treated = treatment == 1
    control = treatment == 0
    if weights is None:
        mt = float(np.mean(values[treated]))
        mc = float(np.mean(values[control]))
        vt = float(np.var(values[treated], ddof=1))
        vc = float(np.var(values[control], ddof=1))
    else:
        wt = weights[treated]
        wc = weights[control]
        vt_values = values[treated]
        vc_values = values[control]
        mt = float(np.average(vt_values, weights=wt))
        mc = float(np.average(vc_values, weights=wc))
        vt = float(np.average((vt_values - mt) ** 2, weights=wt))
        vc = float(np.average((vc_values - mc) ** 2, weights=wc))
    pooled = np.sqrt(max((vt + vc) / 2.0, 1e-12))
    return float((mt - mc) / pooled)


class CausalEngine:
    """Binary-treatment causal estimators with explicit positivity/balance diagnostics."""

    def ipw_ate(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        treatment: str,
        confounders: list[str],
        trim: float = 0.01,
    ) -> ExecutionResult:
        require_columns(data, [outcome, treatment, *confounders])
        working = data[[outcome, treatment, *confounders]].dropna().copy()
        t = pd.to_numeric(working[treatment], errors="raise").astype(int).to_numpy()
        if set(np.unique(t)) - {0, 1}:
            raise ValueError("Treatment must be coded 0/1.")
        y = pd.to_numeric(working[outcome], errors="raise").astype(float).to_numpy()
        x = design_matrix(working, confounders, add_intercept=False)

        propensity_model = LogisticRegression(max_iter=2000, solver="lbfgs")
        propensity_model.fit(x, t)
        ps = propensity_model.predict_proba(x)[:, 1]
        ps_clipped = np.clip(ps, trim, 1.0 - trim)
        weights = t / ps_clipped + (1 - t) / (1 - ps_clipped)

        design = sm.add_constant(t.astype(float))
        fitted = sm.WLS(y, design, weights=weights).fit(cov_type="HC3")
        ate = float(fitted.params[1])
        se = float(fitted.bse[1])
        ci_low, ci_high = map(float, fitted.conf_int()[1])

        balance_before: dict[str, float] = {}
        balance_after: dict[str, float] = {}
        encoded = pd.DataFrame(x, columns=x.columns)
        for column in encoded.columns:
            values = encoded[column].to_numpy(dtype=float)
            balance_before[column] = _standardized_mean_difference(values, t)
            balance_after[column] = _standardized_mean_difference(values, t, weights)

        max_post_balance = max((abs(v) for v in balance_after.values()), default=0.0)
        positivity_fraction = float(((ps < trim) | (ps > 1.0 - trim)).mean())
        warnings: list[str] = []
        if positivity_fraction > 0.05:
            warnings.append("Material propensity-score positivity violations detected.")
        if max_post_balance > 0.10:
            warnings.append("Residual covariate imbalance remains after weighting (|SMD| > 0.10).")

        return ExecutionResult(
            method="inverse_probability_weighted_ate",
            n=len(working),
            estimates={
                "ate": ate,
                "standard_error": se,
                "confidence_interval": [ci_low, ci_high],
            },
            diagnostics={
                "propensity_min": float(ps.min()),
                "propensity_max": float(ps.max()),
                "positivity_violation_fraction": positivity_fraction,
                "max_absolute_smd_before": max(
                    (abs(v) for v in balance_before.values()), default=0.0
                ),
                "max_absolute_smd_after": max_post_balance,
                "smd_before": balance_before,
                "smd_after": balance_after,
                "effective_sample_size": float(weights.sum() ** 2 / np.sum(weights ** 2)),
            },
            assumptions_checked={
                "binary_treatment_verified": True,
                "positivity_checked": True,
                "covariate_balance_checked": True,
                "identification_assumptions": None,
            },
            warnings=warnings,
            metadata={
                "identification_assumptions": [
                    "exchangeability conditional on supplied confounders",
                    "positivity",
                    "consistency",
                    "correct temporal ordering",
                ],
                "trim": trim,
            },
        )

    def aipw_ate(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        treatment: str,
        confounders: list[str],
        binary_outcome: bool = False,
        trim: float = 0.01,
    ) -> ExecutionResult:
        require_columns(data, [outcome, treatment, *confounders])
        working = data[[outcome, treatment, *confounders]].dropna().copy()
        t = pd.to_numeric(working[treatment], errors="raise").astype(int).to_numpy()
        if set(np.unique(t)) - {0, 1}:
            raise ValueError("Treatment must be coded 0/1.")
        y = pd.to_numeric(working[outcome], errors="raise").astype(float).to_numpy()
        x = design_matrix(working, confounders, add_intercept=False)

        propensity = LogisticRegression(max_iter=2000).fit(x, t)
        ps = np.clip(propensity.predict_proba(x)[:, 1], trim, 1 - trim)

        if binary_outcome:
            if set(np.unique(y)) - {0.0, 1.0}:
                raise ValueError("binary_outcome=True requires outcome coded 0/1.")
            model0 = LogisticRegression(max_iter=2000).fit(x[t == 0], y[t == 0])
            model1 = LogisticRegression(max_iter=2000).fit(x[t == 1], y[t == 1])
            mu0 = model0.predict_proba(x)[:, 1]
            mu1 = model1.predict_proba(x)[:, 1]
        else:
            model0 = LinearRegression().fit(x[t == 0], y[t == 0])
            model1 = LinearRegression().fit(x[t == 1], y[t == 1])
            mu0 = model0.predict(x)
            mu1 = model1.predict(x)

        pseudo = (
            mu1
            - mu0
            + t * (y - mu1) / ps
            - (1 - t) * (y - mu0) / (1 - ps)
        )
        ate = float(np.mean(pseudo))
        se = float(np.std(pseudo, ddof=1) / np.sqrt(len(pseudo)))
        ci = [ate - 1.96 * se, ate + 1.96 * se]
        positivity_fraction = float(((ps <= trim) | (ps >= 1 - trim)).mean())

        return ExecutionResult(
            method="augmented_inverse_probability_weighted_ate",
            n=len(working),
            estimates={
                "ate": ate,
                "standard_error": se,
                "confidence_interval": [float(ci[0]), float(ci[1])],
            },
            diagnostics={
                "propensity_min": float(ps.min()),
                "propensity_max": float(ps.max()),
                "positivity_violation_fraction": positivity_fraction,
            },
            assumptions_checked={
                "binary_treatment_verified": True,
                "positivity_checked": True,
                "doubly_robust_estimator_used": True,
                "identification_assumptions": None,
            },
            warnings=(
                ["Material propensity-score positivity violations detected."]
                if positivity_fraction > 0.05
                else []
            ),
            metadata={
                "identification_assumptions": [
                    "exchangeability conditional on supplied confounders",
                    "positivity",
                    "consistency",
                    "correct temporal ordering",
                    "at least one nuisance model is correctly specified for double robustness",
                ],
                "binary_outcome": binary_outcome,
                "trim": trim,
            },
        )
