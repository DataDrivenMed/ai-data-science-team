from __future__ import annotations

from typing import Any

import pandas as pd

from ..contracts import AnalysisContract, AnalysisType
from .causal import CausalEngine
from .common import ExecutionResult
from .forecasting import ForecastEngine
from .inferential import InferentialEngine
from .longitudinal import LongitudinalEngine
from .survival import SurvivalEngine


class StatisticalExecutionRouter:
    """Dispatch an AnalysisContract to an executable statistical engine.

    Execution-specific parameters are explicit. The router never infers a
    treatment, time, event, grouping variable, or causal adjustment set.
    """

    def __init__(self) -> None:
        self.inferential = InferentialEngine()
        self.causal = CausalEngine()
        self.forecasting = ForecastEngine()
        self.survival = SurvivalEngine()
        self.longitudinal = LongitudinalEngine()

    def execute(
        self,
        contract: AnalysisContract,
        data: pd.DataFrame,
        **kwargs: Any,
    ) -> ExecutionResult:
        outcome = kwargs.pop("outcome", None) or contract.outcome or contract.target_variable
        predictors = kwargs.pop("predictors", None)
        if predictors is None:
            predictors = list(contract.predictors)

        if contract.analysis_type == AnalysisType.INFERENTIAL:
            if not outcome:
                raise ValueError("Inferential execution requires an outcome.")
            outcome_type = (contract.outcome_type or "continuous").lower()
            if outcome_type in {"binary", "boolean"}:
                return self.inferential.logistic_regression(
                    data,
                    outcome=outcome,
                    predictors=predictors,
                )
            if outcome_type in {"count", "rate"}:
                return self.inferential.poisson_regression(
                    data,
                    outcome=outcome,
                    predictors=predictors,
                    exposure=kwargs.pop("exposure", None),
                )
            return self.inferential.linear_regression(
                data,
                outcome=outcome,
                predictors=predictors,
                robust_se=kwargs.pop("robust_se", True),
            )

        if contract.analysis_type == AnalysisType.CAUSAL:
            if not outcome:
                raise ValueError("Causal execution requires an outcome.")
            treatment = kwargs.pop("treatment", None)
            confounders = kwargs.pop("confounders", None)
            if not treatment or not confounders:
                raise ValueError("Causal execution requires explicit treatment and confounders.")
            estimator = kwargs.pop("estimator", "aipw").lower()
            if estimator == "ipw":
                return self.causal.ipw_ate(
                    data,
                    outcome=outcome,
                    treatment=treatment,
                    confounders=list(confounders),
                    trim=kwargs.pop("trim", 0.01),
                )
            if estimator == "aipw":
                return self.causal.aipw_ate(
                    data,
                    outcome=outcome,
                    treatment=treatment,
                    confounders=list(confounders),
                    binary_outcome=(contract.outcome_type or "").lower() in {"binary", "boolean"},
                    trim=kwargs.pop("trim", 0.01),
                )
            raise ValueError(f"Unsupported causal estimator: {estimator}")

        if contract.analysis_type == AnalysisType.FORECASTING:
            if not outcome:
                raise ValueError("Forecast execution requires an outcome.")
            time = kwargs.pop("time", None)
            if not time:
                raise ValueError("Forecast execution requires an explicit time column.")
            return self.forecasting.arima(
                data,
                time=time,
                outcome=outcome,
                order=kwargs.pop("order", (1, 1, 0)),
                horizon=kwargs.pop("horizon", 5),
                holdout=kwargs.pop("holdout", None),
            )

        if contract.analysis_type == AnalysisType.SURVIVAL:
            duration = kwargs.pop("duration", None)
            event = kwargs.pop("event", None)
            if not duration or not event:
                raise ValueError("Survival execution requires duration and event columns.")
            if predictors:
                return self.survival.cox_ph(
                    data,
                    duration=duration,
                    event=event,
                    predictors=predictors,
                    ties=kwargs.pop("ties", "breslow"),
                )
            return self.survival.kaplan_meier(
                data,
                duration=duration,
                event=event,
            )

        if contract.analysis_type == AnalysisType.LONGITUDINAL:
            if not outcome:
                raise ValueError("Longitudinal execution requires an outcome.")
            group = kwargs.pop("group", None)
            if not group:
                raise ValueError("Longitudinal execution requires a grouping variable.")
            engine = kwargs.pop("engine", "mixed_effects").lower()
            if engine == "mixed_effects":
                return self.longitudinal.mixed_effects(
                    data,
                    outcome=outcome,
                    predictors=predictors,
                    group=group,
                    random_slope=kwargs.pop("random_slope", None),
                )
            if engine == "gee":
                return self.longitudinal.gee(
                    data,
                    outcome=outcome,
                    predictors=predictors,
                    group=group,
                    binary_outcome=(contract.outcome_type or "").lower() in {"binary", "boolean"},
                    correlation=kwargs.pop("correlation", "exchangeable"),
                )
            raise ValueError(f"Unsupported longitudinal engine: {engine}")

        raise ValueError(
            f"Analysis type {contract.analysis_type.value!r} is not handled by the statistical execution router."
        )
