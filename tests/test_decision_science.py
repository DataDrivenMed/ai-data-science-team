import pandas as pd

from ai_data_science_team.decision_science import (
    AnalysisContract,
    AnalysisType,
    DecisionScienceOrchestrator,
    ReviewStatus,
    assess_data_quality,
    recommend_methods,
)


def test_quality_gate_detects_duplicate_id():
    df = pd.DataFrame({"student_id": [1, 1, 2], "score": [90, 90, 80]})
    report = assess_data_quality(df, id_columns=["student_id"])
    assert report.gate == "NO_GO"
    assert any(
        issue.code == "duplicate_identifiers"
        for issue in report.issues
    )


def test_method_router_uses_causal_family():
    contract = AnalysisContract(
        question="Does the intervention improve scores?",
        decision_to_support="Whether to scale the intervention",
        population="students",
        outcome="score",
        analysis_type=AnalysisType.CAUSAL,
    )
    rec = recommend_methods(contract)
    assert rec.family == "causal inference"
    assert "DAG-guided adjustment" in rec.methods


def test_orchestrator_fails_predictive_results_without_holdout():
    df = pd.DataFrame({"x": range(30), "y": [0, 1] * 15})
    contract = AnalysisContract(
        question="Can x predict y?",
        decision_to_support="Whether to operationalize a model",
        population="sample",
        outcome="y",
        target_variable="y",
        analysis_type=AnalysisType.PREDICTIVE,
        outcome_type="binary",
    )
    orchestrator = DecisionScienceOrchestrator()
    run = orchestrator.prepare(contract, df)
    run = orchestrator.finalize(run, {"n": 30, "accuracy": 0.9})
    assert run.review is not None
    assert run.review.status == ReviewStatus.FAIL
    assert any(
        finding.code == "out_of_sample_missing"
        for finding in run.review.findings
    )


def test_predictive_review_passes_core_safeguards():
    df = pd.DataFrame({"x": range(30), "y": [0, 1] * 15})
    contract = AnalysisContract(
        question="Can x predict y?",
        decision_to_support="Whether to operationalize a model",
        population="sample",
        outcome="y",
        target_variable="y",
        analysis_type=AnalysisType.PREDICTIVE,
        outcome_type="binary",
    )
    orchestrator = DecisionScienceOrchestrator()
    run = orchestrator.prepare(contract, df)
    run = orchestrator.finalize(
        run,
        {
            "n": 30,
            "holdout_metrics": {"auc": 0.82},
            "target_leakage_checked": True,
        },
    )
    assert run.review is not None
    assert run.review.status in {
        ReviewStatus.PASS,
        ReviewStatus.PASS_WITH_WARNINGS,
    }
