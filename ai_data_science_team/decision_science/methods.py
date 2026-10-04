from __future__ import annotations

from .contracts import AnalysisContract, AnalysisType, MethodRecommendation


def recommend_methods(contract: AnalysisContract) -> MethodRecommendation:
    """Route an explicit analytical question to an appropriate method family."""
    t = contract.analysis_type
    outcome_type = (contract.outcome_type or "").lower()

    if t == AnalysisType.DESCRIPTIVE:
        return MethodRecommendation(
            family="descriptive statistics",
            methods=["distribution summaries", "missingness profile", "stratified summaries"],
            rationale=["The contract asks to characterize data rather than estimate an effect or predict outcomes."],
            assumptions_to_check=["measurement definitions are stable across groups and time"],
        )

    if t == AnalysisType.INFERENTIAL:
        if outcome_type in {"binary", "boolean"}:
            methods = ["logistic regression", "risk/rate comparison"]
        elif outcome_type in {"count", "rate"}:
            methods = ["Poisson or negative-binomial regression"]
        else:
            methods = ["linear regression", "group comparison with confidence intervals"]
        return MethodRecommendation(
            family="inferential statistics",
            methods=methods,
            rationale=["The goal is estimation/testing rather than pure prediction."],
            assumptions_to_check=["independence or modeled clustering", "functional form", "residual/model diagnostics", "missing-data mechanism"],
            sensitivity_analyses=["robust standard errors", "alternative covariate specification"],
        )

    if t == AnalysisType.PREDICTIVE:
        return MethodRecommendation(
            family="predictive modeling",
            methods=["regularized baseline model", "tree-based ensemble", "out-of-sample evaluation"],
            rationale=["The contract prioritizes prediction on unseen observations."],
            assumptions_to_check=["no target leakage", "train/test temporal integrity", "representative holdout"],
            sensitivity_analyses=["cross-validation", "calibration", "subgroup performance", "feature ablation"],
        )

    if t == AnalysisType.CAUSAL:
        return MethodRecommendation(
            family="causal inference",
            methods=["DAG-guided adjustment", "propensity/IPW or outcome regression", "doubly robust estimation"],
            rationale=["The question asks about an intervention/exposure effect rather than association alone."],
            assumptions_to_check=["exchangeability/no unmeasured confounding", "positivity", "consistency", "correct temporal ordering"],
            sensitivity_analyses=["unmeasured-confounding sensitivity", "alternative adjustment sets", "negative controls when available"],
            warnings=["Do not label an observational association as causal unless identification assumptions are defensible."],
        )

    if t == AnalysisType.FORECASTING:
        return MethodRecommendation(
            family="time-series forecasting",
            methods=["seasonal naive baseline", "ETS/ARIMA", "feature-based forecasting if justified"],
            rationale=["The outcome is indexed over time and future observations are the target."],
            assumptions_to_check=["chronological validation", "seasonality", "structural breaks", "forecast horizon alignment"],
            sensitivity_analyses=["rolling-origin backtests", "alternative horizons"],
        )

    if t == AnalysisType.SURVIVAL:
        return MethodRecommendation(
            family="time-to-event analysis",
            methods=["Kaplan-Meier", "Cox proportional hazards", "accelerated failure-time model if needed"],
            rationale=["Time-to-event outcomes require explicit treatment of censoring."],
            assumptions_to_check=["censoring mechanism", "proportional hazards when Cox is used"],
            sensitivity_analyses=["time-varying effects", "competing-risks analysis when applicable"],
        )

    if t == AnalysisType.LONGITUDINAL:
        return MethodRecommendation(
            family="longitudinal/multilevel modeling",
            methods=["mixed-effects model", "GEE", "multilevel generalized model"],
            rationale=["Repeated or nested observations violate simple independence assumptions."],
            assumptions_to_check=["clustering structure", "within-unit correlation", "random-effects specification"],
            sensitivity_analyses=["alternative correlation structures", "cluster-robust inference"],
        )

    raise ValueError(f"Unsupported analysis type: {t}")
