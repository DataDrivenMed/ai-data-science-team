from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd

from ...contracts import AnalysisContract, AnalysisType
from ...memory import MetricDefinition


class AcademicMedicineStudy(str, Enum):
    USMLE_SCORE = "usmle_score"
    BOARD_PASS = "board_pass"
    ADMISSIONS_YIELD = "admissions_yield"
    RESIDENT_SURVEY = "resident_survey"
    RETENTION = "retention"
    MATCH_OUTCOME = "match_outcome"


@dataclass(slots=True)
class AcademicMedicineSchema:
    learner_id: str = "learner_id"
    cohort: str = "cohort"
    program: str | None = None
    site: str | None = None
    assessment_date: str | None = None
    attempt: str | None = None


def academic_medicine_metrics() -> list[MetricDefinition]:
    """Generic metric definitions intended to be customized to local policy."""
    return [
        MetricDefinition(
            name="first_attempt_pass_rate",
            definition="Proportion of eligible learners passing an assessment on the first documented attempt.",
            numerator="learners with first documented attempt coded pass",
            denominator="eligible learners with a documented first attempt",
            unit="proportion",
            suppression_threshold=5,
        ),
        MetricDefinition(
            name="board_score_mean",
            definition="Arithmetic mean of the specified board score for the defined cohort and attempt rule.",
            numerator="sum of included board scores",
            denominator="learners with included board scores",
            unit="score points",
            suppression_threshold=5,
        ),
        MetricDefinition(
            name="admissions_yield",
            definition="Proportion of admitted applicants who matriculate under the specified admission-cycle rules.",
            numerator="matriculated admitted applicants",
            denominator="admitted applicants eligible for yield calculation",
            unit="proportion",
            suppression_threshold=5,
        ),
        MetricDefinition(
            name="match_success",
            definition="Proportion of eligible graduating learners matching under the locally specified match-success definition.",
            numerator="eligible graduates meeting match-success definition",
            denominator="eligible graduates",
            unit="proportion",
            suppression_threshold=5,
        ),
        MetricDefinition(
            name="resident_survey_response_rate",
            definition="Proportion of eligible residents/fellows submitting the specified survey.",
            numerator="unique eligible respondents",
            denominator="eligible residents/fellows invited",
            unit="proportion",
            suppression_threshold=5,
        ),
        MetricDefinition(
            name="in_state_retention",
            definition="Proportion of the defined graduate cohort retained in-state at the specified follow-up point.",
            numerator="graduates meeting in-state retention definition",
            denominator="graduates with known eligible retention status",
            unit="proportion",
            suppression_threshold=5,
        ),
    ]


class AcademicMedicineDomainPack:
    """Academic-medicine contracts, validation, and disclosure rules.

    The pack deliberately requires local definitions for high-stakes metrics.
    It supplies reusable structure without hard-coding one institution's policy.
    """

    name = "academic_medicine"
    default_small_cell_threshold = 5

    def __init__(
        self,
        schema: AcademicMedicineSchema | None = None,
        *,
        small_cell_threshold: int = 5,
    ) -> None:
        self.schema = schema or AcademicMedicineSchema()
        self.small_cell_threshold = small_cell_threshold

    def validate_core(
        self,
        data: pd.DataFrame,
        *,
        require_unique_learner_per_cohort: bool = False,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        required = [self.schema.learner_id, self.schema.cohort]
        missing = [column for column in required if column not in data.columns]
        if missing:
            issues.append(
                {
                    "code": "missing_core_academic_medicine_columns",
                    "severity": "blocker",
                    "columns": missing,
                }
            )
            return issues

        if data[self.schema.learner_id].isna().any():
            issues.append(
                {
                    "code": "missing_learner_identifier",
                    "severity": "blocker",
                    "count": int(data[self.schema.learner_id].isna().sum()),
                }
            )

        if data[self.schema.cohort].isna().any():
            issues.append(
                {
                    "code": "missing_cohort",
                    "severity": "warning",
                    "count": int(data[self.schema.cohort].isna().sum()),
                }
            )

        if require_unique_learner_per_cohort:
            duplicate = data.duplicated(
                subset=[self.schema.learner_id, self.schema.cohort]
            )
            if duplicate.any():
                issues.append(
                    {
                        "code": "duplicate_learner_within_cohort",
                        "severity": "blocker",
                        "count": int(duplicate.sum()),
                    }
                )

        for column in (self.schema.program, self.schema.site):
            if column and column in data.columns:
                counts = data[column].value_counts(dropna=True)
                if not counts.empty and (counts < self.small_cell_threshold).any():
                    issues.append(
                        {
                            "code": "small_domain_cells",
                            "severity": "warning",
                            "column": column,
                            "threshold": self.small_cell_threshold,
                        }
                    )

        return issues

    def validate_assessment_attempts(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
    ) -> list[dict[str, Any]]:
        issues = self.validate_core(data)
        if outcome not in data.columns:
            issues.append(
                {
                    "code": "missing_assessment_outcome",
                    "severity": "blocker",
                    "column": outcome,
                }
            )
            return issues

        if self.schema.attempt and self.schema.attempt in data.columns:
            attempt = pd.to_numeric(data[self.schema.attempt], errors="coerce")
            if attempt.isna().any() or (attempt < 1).any():
                issues.append(
                    {
                        "code": "invalid_attempt_number",
                        "severity": "blocker",
                        "column": self.schema.attempt,
                    }
                )
        return issues

    def contract(
        self,
        study: AcademicMedicineStudy,
        *,
        outcome: str,
        predictors: list[str] | None = None,
        decision_to_support: str,
        population: str,
        analysis_type: AnalysisType | None = None,
        outcome_type: str | None = None,
    ) -> AnalysisContract:
        predictors = list(predictors or [])

        defaults: dict[AcademicMedicineStudy, tuple[AnalysisType, str | None]] = {
            AcademicMedicineStudy.USMLE_SCORE: (AnalysisType.INFERENTIAL, "continuous"),
            AcademicMedicineStudy.BOARD_PASS: (AnalysisType.INFERENTIAL, "binary"),
            AcademicMedicineStudy.ADMISSIONS_YIELD: (AnalysisType.INFERENTIAL, "binary"),
            AcademicMedicineStudy.RESIDENT_SURVEY: (AnalysisType.INFERENTIAL, "continuous"),
            AcademicMedicineStudy.RETENTION: (AnalysisType.INFERENTIAL, "binary"),
            AcademicMedicineStudy.MATCH_OUTCOME: (AnalysisType.INFERENTIAL, "binary"),
        }
        default_type, default_outcome_type = defaults[study]
        chosen_type = analysis_type or default_type
        chosen_outcome_type = outcome_type or default_outcome_type

        approval = []
        risks = [
            "cohort effects and policy changes can confound temporal comparisons",
            "missing outcomes may be informative rather than random",
            "small subgroup reporting can create disclosure risk",
        ]
        if chosen_type == AnalysisType.PREDICTIVE:
            approval.append("high-stakes learner prediction review")
            risks.append("prediction must not be used as an unreviewed learner-level decision rule")
        if chosen_type == AnalysisType.CAUSAL:
            approval.append("causal interpretation review")

        return AnalysisContract(
            question=f"Academic medicine study: {study.value}",
            decision_to_support=decision_to_support,
            population=population,
            outcome=outcome,
            target_variable=outcome if chosen_type in {AnalysisType.PREDICTIVE, AnalysisType.CAUSAL} else None,
            predictors=predictors,
            unit_of_analysis="learner unless explicitly redefined",
            analysis_type=chosen_type,
            outcome_type=chosen_outcome_type,
            assumptions=[
                "cohort and assessment definitions are stable or modeled explicitly",
                "attempt rules are prespecified when repeated assessments exist",
                "outcomes are aligned to the correct learner and time period",
            ],
            risks=risks,
            human_approval_required=approval,
            metadata={
                "domain": "academic_medicine",
                "study": study.value,
                "small_cell_threshold": self.small_cell_threshold,
            },
        )

    def board_score_contract(
        self,
        *,
        outcome: str,
        predictors: list[str],
        decision_to_support: str,
        population: str,
    ) -> AnalysisContract:
        return self.contract(
            AcademicMedicineStudy.USMLE_SCORE,
            outcome=outcome,
            predictors=predictors,
            decision_to_support=decision_to_support,
            population=population,
        )

    def board_pass_contract(
        self,
        *,
        outcome: str,
        predictors: list[str],
        decision_to_support: str,
        population: str,
    ) -> AnalysisContract:
        return self.contract(
            AcademicMedicineStudy.BOARD_PASS,
            outcome=outcome,
            predictors=predictors,
            decision_to_support=decision_to_support,
            population=population,
        )

    def admissions_yield_contract(
        self,
        *,
        outcome: str,
        predictors: list[str],
        decision_to_support: str,
        population: str,
    ) -> AnalysisContract:
        return self.contract(
            AcademicMedicineStudy.ADMISSIONS_YIELD,
            outcome=outcome,
            predictors=predictors,
            decision_to_support=decision_to_support,
            population=population,
        )


class AcademicMedicineMetricEngine:
    """Executable metric calculations with explicit denominators and attempt rules."""

    @staticmethod
    def first_attempt_pass_rate(
        data: pd.DataFrame,
        *,
        learner_id: str,
        attempt: str,
        passed: str,
    ) -> dict[str, Any]:
        required = [learner_id, attempt, passed]
        missing = [column for column in required if column not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        working = data[required].dropna().copy()
        working[attempt] = pd.to_numeric(working[attempt], errors="raise").astype(int)
        working[passed] = pd.to_numeric(working[passed], errors="raise").astype(int)
        if set(working[passed].unique()) - {0, 1}:
            raise ValueError("Pass indicator must be coded 0/1.")
        first = (
            working.sort_values([learner_id, attempt])
            .groupby(learner_id, as_index=False)
            .first()
        )
        numerator = int(first[passed].sum())
        denominator = int(len(first))
        return {
            "metric": "first_attempt_pass_rate",
            "numerator": numerator,
            "denominator": denominator,
            "value": numerator / denominator if denominator else None,
            "attempt_rule": "lowest documented attempt number per learner",
        }

    @staticmethod
    def admissions_yield(
        data: pd.DataFrame,
        *,
        applicant_id: str,
        admitted: str,
        matriculated: str,
    ) -> dict[str, Any]:
        required = [applicant_id, admitted, matriculated]
        missing = [column for column in required if column not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        working = data[required].dropna(subset=[applicant_id]).copy()
        if working[applicant_id].duplicated().any():
            raise ValueError("Admissions yield requires one row per applicant.")
        admitted_values = pd.to_numeric(working[admitted], errors="raise").astype(int)
        matriculated_values = pd.to_numeric(
            working[matriculated], errors="raise"
        ).astype(int)
        if set(admitted_values.unique()) - {0, 1}:
            raise ValueError("Admitted indicator must be coded 0/1.")
        if set(matriculated_values.unique()) - {0, 1}:
            raise ValueError("Matriculated indicator must be coded 0/1.")

        eligible = working.loc[admitted_values == 1]
        numerator = int(
            pd.to_numeric(eligible[matriculated], errors="raise").astype(int).sum()
        )
        denominator = int(len(eligible))
        return {
            "metric": "admissions_yield",
            "numerator": numerator,
            "denominator": denominator,
            "value": numerator / denominator if denominator else None,
        }

    @staticmethod
    def response_rate(
        *,
        eligible_count: int,
        respondent_ids: pd.Series | list[Any],
    ) -> dict[str, Any]:
        if eligible_count <= 0:
            raise ValueError("eligible_count must be positive.")
        respondents = pd.Series(respondent_ids).dropna().nunique()
        if respondents > eligible_count:
            raise ValueError("Unique respondents cannot exceed eligible_count.")
        return {
            "metric": "response_rate",
            "numerator": int(respondents),
            "denominator": int(eligible_count),
            "value": float(respondents / eligible_count),
        }

    @staticmethod
    def binary_rate(
        data: pd.DataFrame,
        *,
        learner_id: str,
        indicator: str,
        metric_name: str,
    ) -> dict[str, Any]:
        if learner_id not in data.columns or indicator not in data.columns:
            raise ValueError("Required learner identifier or indicator is missing.")
        working = data[[learner_id, indicator]].dropna().copy()
        if working[learner_id].duplicated().any():
            raise ValueError(f"{metric_name} requires one row per learner.")
        values = pd.to_numeric(working[indicator], errors="raise").astype(int)
        if set(values.unique()) - {0, 1}:
            raise ValueError("Indicator must be coded 0/1.")
        numerator = int(values.sum())
        denominator = int(len(values))
        return {
            "metric": metric_name,
            "numerator": numerator,
            "denominator": denominator,
            "value": numerator / denominator if denominator else None,
        }
