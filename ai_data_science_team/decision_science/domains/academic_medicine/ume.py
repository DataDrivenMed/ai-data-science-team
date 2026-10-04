from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ...contracts import AnalysisContract, AnalysisType
from .common import (
    DomainMetric,
    proportion_metric,
    require_binary,
    require_columns,
    standard_contract,
)


@dataclass(slots=True)
class UMESchema:
    learner_id: str = "learner_id"
    cohort: str = "cohort"
    exam: str = "exam"
    score: str = "score"
    passed: str = "passed"
    attempt: str = "attempt"
    course: str = "course"
    clerkship: str = "clerkship"
    remediated: str = "remediated"
    progressed: str = "progressed"


class UMEPack:
    name = "ume"

    def __init__(self, schema: UMESchema | None = None) -> None:
        self.schema = schema or UMESchema()

    def first_attempt_outcomes(
        self,
        data: pd.DataFrame,
        *,
        exam_name: Any | None = None,
    ) -> dict[str, Any]:
        columns = [
            self.schema.learner_id,
            self.schema.exam,
            self.schema.score,
            self.schema.passed,
            self.schema.attempt,
        ]
        require_columns(data, columns)
        frame = data[columns].dropna(
            subset=[self.schema.learner_id, self.schema.exam, self.schema.attempt]
        ).copy()
        if exam_name is not None:
            frame = frame.loc[frame[self.schema.exam] == exam_name]
        frame[self.schema.attempt] = pd.to_numeric(frame[self.schema.attempt], errors="raise")
        first = (
            frame.sort_values(
                [self.schema.learner_id, self.schema.exam, self.schema.attempt]
            )
            .groupby([self.schema.learner_id, self.schema.exam], as_index=False)
            .first()
        )
        first["_passed"] = require_binary(first[self.schema.passed], name=self.schema.passed)
        first["_score"] = pd.to_numeric(first[self.schema.score], errors="coerce")
        n = int(len(first))
        return {
            "n": n,
            "first_attempt_pass_rate": float(first["_passed"].mean()) if n else None,
            "mean_score": float(first["_score"].mean()) if first["_score"].notna().any() else None,
            "median_score": float(first["_score"].median()) if first["_score"].notna().any() else None,
            "attempt_rule": "lowest documented attempt per learner/exam",
        }

    def nbme_summary(
        self,
        data: pd.DataFrame,
        *,
        clerkship: str | None = None,
    ) -> dict[str, Any]:
        columns = [self.schema.learner_id, self.schema.clerkship, self.schema.score]
        require_columns(data, columns)
        frame = data[columns].copy()
        if clerkship is not None:
            frame = frame.loc[frame[self.schema.clerkship] == clerkship]
        scores = pd.to_numeric(frame[self.schema.score], errors="coerce")
        return {
            "n": int(scores.notna().sum()),
            "mean": float(scores.mean()) if scores.notna().any() else None,
            "median": float(scores.median()) if scores.notna().any() else None,
            "p10": float(scores.quantile(0.10)) if scores.notna().any() else None,
            "p90": float(scores.quantile(0.90)) if scores.notna().any() else None,
            "clerkship": clerkship,
        }

    def course_performance(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        require_columns(data, [self.schema.course, self.schema.score])
        frame = data[[self.schema.course, self.schema.score]].copy()
        frame["_score"] = pd.to_numeric(frame[self.schema.score], errors="coerce")
        summary = (
            frame.groupby(self.schema.course)["_score"]
            .agg(["count", "mean", "median", "std"])
            .reset_index()
        )
        return summary

    def clerkship_summary(self, data: pd.DataFrame) -> pd.DataFrame:
        require_columns(data, [self.schema.clerkship, self.schema.score])
        frame = data[[self.schema.clerkship, self.schema.score]].copy()
        frame["_score"] = pd.to_numeric(frame[self.schema.score], errors="coerce")
        return (
            frame.groupby(self.schema.clerkship)["_score"]
            .agg(["count", "mean", "median", "std"])
            .reset_index()
        )

    def remediation_rate(self, data: pd.DataFrame) -> DomainMetric:
        require_columns(data, [self.schema.learner_id, self.schema.remediated])
        frame = data[[self.schema.learner_id, self.schema.remediated]].dropna().copy()
        if frame[self.schema.learner_id].duplicated().any():
            raise ValueError("Remediation rate requires one row per learner.")
        values = require_binary(frame[self.schema.remediated], name=self.schema.remediated)
        return proportion_metric(
            name="remediation_rate",
            numerator=int(values.sum()),
            denominator=int(len(values)),
            definition="Learners requiring remediation divided by eligible learners.",
        )

    def progression_rate(self, data: pd.DataFrame) -> DomainMetric:
        require_columns(data, [self.schema.learner_id, self.schema.progressed])
        frame = data[[self.schema.learner_id, self.schema.progressed]].dropna().copy()
        if frame[self.schema.learner_id].duplicated().any():
            raise ValueError("Progression rate requires one row per learner.")
        values = require_binary(frame[self.schema.progressed], name=self.schema.progressed)
        return proportion_metric(
            name="progression_rate",
            numerator=int(values.sum()),
            denominator=int(len(values)),
            definition="Learners progressing under the specified rule divided by eligible learners.",
        )

    def usmle_contract(
        self,
        *,
        outcome: str,
        predictors: list[str],
        decision_to_support: str,
        population: str,
        binary: bool = False,
    ) -> AnalysisContract:
        return standard_contract(
            question="Which pre-specified factors are associated with USMLE outcome?",
            decision_to_support=decision_to_support,
            population=population,
            outcome=outcome,
            predictors=predictors,
            analysis_type=AnalysisType.INFERENTIAL,
            outcome_type="binary" if binary else "continuous",
            assumptions=["attempt rule is prespecified", "predictors precede the outcome in time"],
            risks=["cohort effects", "informative missingness", "retake handling can change estimates"],
            metadata={"domain": "academic_medicine", "subpack": "ume", "analysis": "usmle"},
        )
