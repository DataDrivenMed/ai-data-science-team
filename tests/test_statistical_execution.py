import numpy as np
import pandas as pd

from ai_data_science_team.decision_science import (
    AcademicMedicineDomainPack,
    AcademicMedicineMetricEngine,
    AcademicMedicineSchema,
    AcademicMedicineStudy,
    AnalysisContract,
    AnalysisType,
    CausalEngine,
    DecisionScienceOrchestrator,
    ForecastEngine,
    InferentialEngine,
    LongitudinalEngine,
    ReviewStatus,
    SurvivalEngine,
    academic_medicine_metrics,
)


def test_linear_regression_recovers_known_slope():
    rng = np.random.default_rng(11)
    x = rng.normal(size=250)
    y = 3.0 + 2.0 * x + rng.normal(scale=0.5, size=250)
    result = InferentialEngine().linear_regression(
        pd.DataFrame({"x": x, "y": y}),
        outcome="y",
        predictors=["x"],
    )
    slope = result.estimates["coefficients"]["x"]["estimate"]
    assert abs(slope - 2.0) < 0.15
    assert result.assumptions_checked["heteroskedasticity_checked"] is True


def test_logistic_regression_returns_odds_ratios_and_uncertainty():
    rng = np.random.default_rng(12)
    x = rng.normal(size=350)
    p = 1.0 / (1.0 + np.exp(-(-0.3 + 1.2 * x)))
    y = rng.binomial(1, p)
    result = InferentialEngine().logistic_regression(
        pd.DataFrame({"x": x, "y": y}),
        outcome="y",
        predictors=["x"],
    )
    assert result.estimates["odds_ratios"]["x"]["odds_ratio"] > 1.0
    assert "standard_error" in result.estimates["coefficients"]["x"]


def test_aipw_recovers_positive_treatment_effect():
    rng = np.random.default_rng(13)
    n = 900
    x = rng.normal(size=n)
    ps = 1.0 / (1.0 + np.exp(-(0.5 * x)))
    treatment = rng.binomial(1, ps)
    outcome = 1.5 * treatment + 0.8 * x + rng.normal(scale=1.0, size=n)
    data = pd.DataFrame({"x": x, "treatment": treatment, "outcome": outcome})

    result = CausalEngine().aipw_ate(
        data,
        outcome="outcome",
        treatment="treatment",
        confounders=["x"],
    )
    assert abs(result.estimates["ate"] - 1.5) < 0.25
    assert result.estimates["confidence_interval"][0] < result.estimates["ate"]
    assert result.estimates["confidence_interval"][1] > result.estimates["ate"]


def test_forecast_engine_uses_chronological_holdout():
    rng = np.random.default_rng(14)
    n = 72
    dates = pd.date_range("2020-01-01", periods=n, freq="MS")
    values = 20 + 0.4 * np.arange(n) + rng.normal(scale=0.5, size=n)
    result = ForecastEngine().arima(
        pd.DataFrame({"date": dates, "value": values}),
        time="date",
        outcome="value",
        order=(1, 1, 0),
        horizon=4,
        holdout=8,
    )
    assert len(result.estimates["forecast"]) == 4
    assert result.diagnostics["holdout_size"] == 8
    assert result.assumptions_checked["chronological_validation"] is True


def test_kaplan_meier_is_monotone_nonincreasing():
    data = pd.DataFrame(
        {
            "time": [1, 2, 3, 4, 5, 6, 7, 8],
            "event": [1, 0, 1, 1, 0, 1, 0, 1],
        }
    )
    result = SurvivalEngine().kaplan_meier(
        data,
        duration="time",
        event="event",
    )
    probs = result.estimates["survival_probability"]
    assert all(a >= b for a, b in zip(probs, probs[1:]))
    assert result.diagnostics["events"] == 5


def test_mixed_effects_models_clustered_repeated_measures():
    rng = np.random.default_rng(15)
    rows = []
    for learner in range(40):
        intercept = rng.normal(scale=1.2)
        for time in range(4):
            score = 10 + 0.7 * time + intercept + rng.normal(scale=0.4)
            rows.append({"learner": learner, "time": time, "score": score})
    result = LongitudinalEngine().mixed_effects(
        pd.DataFrame(rows),
        outcome="score",
        predictors=["time"],
        group="learner",
    )
    assert result.diagnostics["groups"] == 40
    assert result.diagnostics["converged"] is True
    assert result.estimates["fixed_effects"]["time"]["estimate"] > 0.4


def test_orchestrator_executes_inferential_contract_and_reviews_output():
    rng = np.random.default_rng(16)
    x = rng.normal(size=120)
    y = 2 + 1.1 * x + rng.normal(scale=0.7, size=120)
    data = pd.DataFrame({"x": x, "y": y})
    contract = AnalysisContract(
        question="Is x associated with y?",
        decision_to_support="Whether to investigate x as a meaningful predictor",
        population="synthetic observations",
        outcome="y",
        predictors=["x"],
        analysis_type=AnalysisType.INFERENTIAL,
        outcome_type="continuous",
    )
    orchestrator = DecisionScienceOrchestrator()
    run = orchestrator.prepare(contract, data)
    run = orchestrator.execute(run, data)
    assert run.execution_result is not None
    assert run.execution_result.method == "ordinary_least_squares"
    assert run.review is not None
    assert run.review.status in {ReviewStatus.PASS, ReviewStatus.PASS_WITH_WARNINGS}


def test_academic_medicine_pack_builds_board_contract_and_validates_duplicates():
    pack = AcademicMedicineDomainPack(
        AcademicMedicineSchema(
            learner_id="student_id",
            cohort="class_year",
            attempt="attempt",
        )
    )
    contract = pack.contract(
        AcademicMedicineStudy.BOARD_PASS,
        outcome="passed",
        predictors=["mcat"],
        decision_to_support="Identify population-level academic support signals",
        population="medical students",
    )
    assert contract.analysis_type == AnalysisType.INFERENTIAL
    assert contract.outcome_type == "binary"
    assert contract.metadata["domain"] == "academic_medicine"

    data = pd.DataFrame(
        {
            "student_id": [1, 1, 2],
            "class_year": [2027, 2027, 2027],
            "attempt": [1, 1, 1],
            "passed": [1, 1, 0],
        }
    )
    issues = pack.validate_core(data, require_unique_learner_per_cohort=True)
    assert any(issue["code"] == "duplicate_learner_within_cohort" for issue in issues)


def test_academic_medicine_metrics_include_core_definitions():
    names = {metric.name for metric in academic_medicine_metrics()}
    assert {
        "first_attempt_pass_rate",
        "board_score_mean",
        "admissions_yield",
        "match_success",
        "resident_survey_response_rate",
        "in_state_retention",
    }.issubset(names)


def test_cox_engine_reports_ph_diagnostics():
    rng = np.random.default_rng(17)
    n = 260
    x = rng.normal(size=n)
    event_time = rng.exponential(scale=8.0, size=n) / np.exp(0.45 * x)
    censor_time = rng.exponential(scale=14.0, size=n)
    observed = np.minimum(event_time, censor_time)
    event = (event_time <= censor_time).astype(int)
    result = SurvivalEngine().cox_ph(
        pd.DataFrame({"time": observed, "event": event, "x": x}),
        duration="time",
        event="event",
        predictors=["x"],
    )
    assert "x" in result.estimates["hazard_ratios"]
    assert result.assumptions_checked["proportional_hazards_checked"] is True
    assert "x" in result.diagnostics["proportional_hazards_tests"]


def test_academic_medicine_metric_engine_uses_first_documented_attempt():
    data = pd.DataFrame(
        {
            "student_id": [1, 1, 2, 2, 3],
            "attempt": [1, 2, 1, 2, 1],
            "passed": [0, 1, 1, 1, 1],
        }
    )
    metric = AcademicMedicineMetricEngine.first_attempt_pass_rate(
        data,
        learner_id="student_id",
        attempt="attempt",
        passed="passed",
    )
    assert metric["numerator"] == 2
    assert metric["denominator"] == 3
    assert abs(metric["value"] - (2 / 3)) < 1e-12


def test_academic_medicine_admissions_yield_has_explicit_denominator():
    data = pd.DataFrame(
        {
            "applicant": [1, 2, 3, 4],
            "admitted": [1, 1, 0, 1],
            "matriculated": [1, 0, 0, 1],
        }
    )
    metric = AcademicMedicineMetricEngine.admissions_yield(
        data,
        applicant_id="applicant",
        admitted="admitted",
        matriculated="matriculated",
    )
    assert metric["numerator"] == 2
    assert metric["denominator"] == 3
