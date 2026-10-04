import pandas as pd

from ai_data_science_team import (
    AccreditationMetricSpec,
    AccreditationPack,
    AdmissionsPack,
    GMEPack,
    ResearchPack,
    UMEPack,
    WorkforcePack,
)


def test_admissions_funnel_and_fairness():
    df = pd.DataFrame(
        {
            "applicant_id": [1, 2, 3, 4, 5, 6],
            "cycle": [2026] * 6,
            "applied": [1] * 6,
            "interviewed": [1, 1, 1, 1, 0, 0],
            "admitted": [1, 1, 1, 0, 0, 0],
            "matriculated": [1, 0, 1, 0, 0, 0],
            "mcat": [515, 510, 512, 508, 506, 505],
            "gpa": [3.8, 3.7, 3.75, 3.6, 3.5, 3.4],
            "science_gpa": [3.7, 3.6, 3.7, 3.5, 3.4, 3.3],
            "scholarship_amount": [10000, 0, 5000, 0, 0, 0],
            "group": ["A", "A", "B", "B", "B", "B"],
        }
    )
    pack = AdmissionsPack()
    funnel = pack.applicant_funnel(df)
    assert funnel["yield"].numerator == 2
    assert funnel["yield"].denominator == 3
    fairness = pack.fairness_summary(
        df,
        group="group",
        outcome="admitted",
        reference_group="B",
        minimum_n=2,
    )
    assert fairness["groups"]["A"]["rate"] == 1.0
    assert fairness["groups"]["B"]["rate"] == 0.25


def test_ume_attempt_and_progression_logic():
    df = pd.DataFrame(
        {
            "learner_id": [1, 1, 2, 3],
            "exam": ["Step2", "Step2", "Step2", "Step2"],
            "score": [205, 230, 245, 250],
            "passed": [0, 1, 1, 1],
            "attempt": [1, 2, 1, 1],
            "progressed": [1, 1, 1, 1],
        }
    )
    pack = UMEPack()
    result = pack.first_attempt_outcomes(df, exam_name="Step2")
    assert result["n"] == 3
    assert abs(result["first_attempt_pass_rate"] - (2 / 3)) < 1e-12

    progression = pd.DataFrame(
        {"learner_id": [1, 2, 3], "progressed": [1, 1, 0]}
    )
    metric = pack.progression_rate(progression)
    assert metric.numerator == 2
    assert metric.denominator == 3


def test_gme_response_attrition_and_program_outcomes():
    df = pd.DataFrame(
        {
            "trainee_id": [1, 2, 3, 4],
            "program": ["A", "A", "B", "B"],
            "survey_eligible": [1, 1, 1, 1],
            "survey_responded": [1, 0, 1, 1],
            "attrited": [0, 1, 0, 0],
        }
    )
    pack = GMEPack()
    response = pack.survey_response(df)
    assert response.numerator == 3
    assert response.denominator == 4
    attrition = pack.attrition_rate(df)
    assert attrition.value == 0.25
    summary = pack.program_outcomes(df, outcome="attrited", minimum_n=2)
    assert set(summary["program"]) == {"A", "B"}


def test_accreditation_thresholds_and_alerts():
    pack = AccreditationPack()
    spec = AccreditationMetricSpec(
        metric_id="pass",
        name="Board pass",
        owner="UME",
        source="Board data",
        direction="higher_is_better",
        target=0.95,
        warning_threshold=0.90,
        critical_threshold=0.85,
        standard_or_element="LCME 8.4",
    )
    snapshot = pack.cqi_snapshot(
        pd.DataFrame({"metric_id": ["pass"], "value": [0.88]}),
        specs=[spec],
    )
    assert snapshot.iloc[0]["status"] == "WARNING"
    alerts = pack.threshold_alerts(snapshot)
    assert len(alerts) == 1


def test_research_metrics_and_growth_index():
    df = pd.DataFrame(
        {
            "year": [2024, 2025, 2026],
            "nih_funding": [10.0, 12.0, 15.0],
            "publications": [100, 110, 130],
            "grant_awarded": [20, 21, 25],
            "grant_submitted": [40, 42, 50],
        }
    )
    pack = ResearchPack()
    funding = pack.nih_funding_trend(df)
    assert funding["absolute_growth"] == 5.0
    grants = pack.grant_success(df)
    assert grants["awarded"] == 66.0
    index = pack.research_growth_index(df, baseline_year=2024)
    assert abs(index.iloc[0]["research_growth_index"] - 1.0) < 1e-12


def test_workforce_retention_and_pipeline_conversion():
    pack = WorkforcePack()
    retention_df = pd.DataFrame(
        {
            "person_id": [1, 2, 3, 4],
            "retained_in_state": [1, 1, 0, 1],
        }
    )
    retention = pack.retention_rate(retention_df)
    assert retention["numerator"] == 3
    assert retention["denominator"] == 4

    pipeline_df = pd.DataFrame(
        {
            "person_id": [1, 1, 2, 2, 3],
            "pipeline_stage": [
                "medical_school",
                "residency",
                "medical_school",
                "residency",
                "medical_school",
            ],
        }
    )
    conversion = pack.pipeline_conversion(
        pipeline_df,
        from_stage="medical_school",
        to_stage="residency",
    )
    assert conversion["numerator"] == 2
    assert conversion["denominator"] == 3
