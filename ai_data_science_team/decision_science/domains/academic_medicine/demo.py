from __future__ import annotations

import pandas as pd

from .executive import CQIMetricSpec


def demo_datasets() -> dict[str, pd.DataFrame]:
    admissions_rows = []
    applicant_id = 1
    for cycle, applied, interviewed, admitted, matriculated in [
        ("2023", 100, 60, 34, 18),
        ("2024", 105, 64, 36, 20),
        ("2025", 110, 66, 38, 23),
        ("2026", 115, 70, 40, 26),
    ]:
        for index in range(applied):
            admissions_rows.append({
                "applicant_id": applicant_id,
                "cycle": cycle,
                "applied": 1,
                "interviewed": int(index < interviewed),
                "admitted": int(index < admitted),
                "matriculated": int(index < matriculated),
                "mcat": 506 + (index % 10),
                "gpa": 3.35 + (index % 12) * 0.04,
                "science_gpa": 3.30 + (index % 11) * 0.04,
                "scholarship_amount": 10000 if index < min(8, admitted) else 0,
            })
            applicant_id += 1

    ume_rows = []
    learner_id = 1
    for cohort, pass_count, total in [
        ("2023", 88, 95), ("2024", 90, 96), ("2025", 91, 97), ("2026", 90, 98)
    ]:
        for index in range(total):
            passed = int(index < pass_count)
            ume_rows.append({
                "learner_id": learner_id,
                "cohort": cohort,
                "exam": "Step2",
                "score": 244 + (index % 17) - (0 if passed else 18),
                "passed": passed,
                "attempt": 1,
                "course": "Core",
                "clerkship": "Medicine",
                "remediated": int(not passed),
                "progressed": int(index < total - 2),
            })
            learner_id += 1

    gme_rows = []
    trainee_id = 1
    for year, response_count, attrition_count in [
        ("2023", 70, 4), ("2024", 74, 3), ("2025", 78, 3), ("2026", 76, 5)
    ]:
        total = 90
        for index in range(total):
            gme_rows.append({
                "trainee_id": trainee_id,
                "year": year,
                "program": ["Medicine", "Surgery", "Pediatrics"][index % 3],
                "site": ["University", "Affiliate A", "Affiliate B"][index % 3],
                "survey_eligible": 1,
                "survey_responded": int(index < response_count),
                "attrited": int(index < attrition_count),
                "board_passed": int(index < 84),
                "retained": int(index < 58),
                "specialty": ["Medicine", "Surgery", "Pediatrics"][index % 3],
            })
            trainee_id += 1

    research = pd.DataFrame({
        "year": ["2023", "2024", "2025", "2026"],
        "nih_funding": [31_000_000, 34_500_000, 38_000_000, 41_500_000],
        "publications": [720, 755, 804, 846],
        "citations": [9500, 10100, 11200, 12500],
        "grant_submitted": [235, 248, 260, 275],
        "grant_awarded": [73, 78, 83, 90],
        "trial_id": ["T1", "T2", "T3", "T4"],
        "trial_status": ["Recruiting", "Recruiting", "Active", "Completed"],
    })

    workforce_rows = []
    person_id = 1
    for cohort, retained, underserved, total in [
        ("2023", 62, 24, 100), ("2024", 64, 25, 100),
        ("2025", 67, 28, 100), ("2026", 69, 31, 100)
    ]:
        for index in range(total):
            workforce_rows.append({
                "person_id": person_id,
                "cohort": cohort,
                "retained_in_state": int(index < retained),
                "specialty": ["Primary Care", "Surgical", "Other"][index % 3],
                "geography": ["Urban", "Rural", "Suburban"][index % 3],
                "underserved": int(index < underserved),
                "pipeline_stage": "Practice",
            })
            person_id += 1

    return {
        "admissions": pd.DataFrame(admissions_rows),
        "ume": pd.DataFrame(ume_rows),
        "gme": pd.DataFrame(gme_rows),
        "research": research,
        "workforce": pd.DataFrame(workforce_rows),
    }


def demo_metric_specs() -> list[CQIMetricSpec]:
    return [
        CQIMetricSpec("admissions_yield", "Admissions Yield", "Admissions", "admissions", "admissions.yield", "Admissions", "Admissions cycle data", target=.65, warning_threshold=.60, critical_threshold=.52, period_column="cycle", cadence="annual"),
        CQIMetricSpec("step2_first_pass", "Step 2 First-Attempt Pass", "UME", "ume", "ume.first_attempt_pass_rate", "UME", "Board outcome data", target=.95, warning_threshold=.93, critical_threshold=.90, period_column="cohort", cadence="annual", standard_or_element="LCME 8.4", calculator_params={"exam_name": "Step2"}),
        CQIMetricSpec("ume_progression", "UME Progression", "UME", "ume", "ume.progression_rate", "Student Affairs / UME", "Progression records", target=.98, warning_threshold=.96, critical_threshold=.94, period_column="cohort", cadence="annual"),
        CQIMetricSpec("gme_survey_response", "Resident Survey Response", "GME", "gme", "gme.survey_response_rate", "GME", "Resident survey", target=.85, warning_threshold=.80, critical_threshold=.70, period_column="year", cadence="annual"),
        CQIMetricSpec("gme_attrition", "GME Attrition", "GME", "gme", "gme.attrition_rate", "GME", "Program records", direction="lower_is_better", target=.03, warning_threshold=.05, critical_threshold=.07, period_column="year", cadence="annual"),
        CQIMetricSpec("nih_funding", "NIH Funding", "Research", "research", "research.nih_funding", "Research", "Research finance", target=40_000_000, warning_threshold=35_000_000, critical_threshold=30_000_000, period_column="year", unit="currency", cadence="annual"),
        CQIMetricSpec("grant_success", "Grant Success Rate", "Research", "research", "research.grant_success_rate", "Research", "Sponsored projects", target=.34, warning_threshold=.30, critical_threshold=.25, period_column="year", cadence="annual"),
        CQIMetricSpec("state_retention", "In-State Retention", "Workforce", "workforce", "workforce.in_state_retention", "Workforce Strategy", "Graduate workforce data", target=.70, warning_threshold=.65, critical_threshold=.58, period_column="cohort", cadence="annual"),
        CQIMetricSpec("underserved_practice", "Underserved Practice", "Workforce", "workforce", "workforce.underserved_practice_rate", "Workforce Strategy", "Graduate workforce data", target=.32, warning_threshold=.27, critical_threshold=.22, period_column="cohort", cadence="annual"),
    ]
