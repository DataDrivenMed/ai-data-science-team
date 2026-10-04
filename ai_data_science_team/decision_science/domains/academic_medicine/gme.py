from __future__ import annotations

from dataclasses import dataclass

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
class GMESchema:
    trainee_id: str = "trainee_id"
    program: str = "program"
    site: str = "site"
    survey_eligible: str = "survey_eligible"
    survey_responded: str = "survey_responded"
    attrited: str = "attrited"
    board_passed: str = "board_passed"
    retained: str = "retained"
    specialty: str = "specialty"


class GMEPack:
    name = "gme"

    def __init__(self, schema: GMESchema | None = None) -> None:
        self.schema = schema or GMESchema()

    def survey_response(self, data: pd.DataFrame) -> DomainMetric:
        require_columns(
            data,
            [self.schema.trainee_id, self.schema.survey_eligible, self.schema.survey_responded],
        )
        frame = data[
            [self.schema.trainee_id, self.schema.survey_eligible, self.schema.survey_responded]
        ].dropna(subset=[self.schema.trainee_id]).copy()
        if frame[self.schema.trainee_id].duplicated().any():
            raise ValueError("Survey response rate requires one row per trainee.")
        eligible = require_binary(frame[self.schema.survey_eligible], name=self.schema.survey_eligible)
        responded = require_binary(frame[self.schema.survey_responded], name=self.schema.survey_responded)
        mask = eligible == 1
        numerator = int(responded.loc[mask].sum())
        denominator = int(mask.sum())
        return proportion_metric(
            name="resident_survey_response_rate",
            numerator=numerator,
            denominator=denominator,
            definition="Unique eligible respondents divided by eligible trainees.",
        )

    def attrition_rate(self, data: pd.DataFrame) -> DomainMetric:
        return self._trainee_binary_rate(
            data,
            self.schema.attrited,
            "attrition_rate",
            "Trainees meeting the local attrition definition divided by eligible trainees.",
        )

    def board_pass_rate(self, data: pd.DataFrame) -> DomainMetric:
        return self._trainee_binary_rate(
            data,
            self.schema.board_passed,
            "board_pass_rate",
            "Eligible trainees passing the specified board examination divided by eligible trainees with known outcomes.",
        )

    def retention_rate(self, data: pd.DataFrame) -> DomainMetric:
        return self._trainee_binary_rate(
            data,
            self.schema.retained,
            "gme_retention_rate",
            "Trainees meeting the local retention definition divided by eligible trainees with known status.",
        )

    def _trainee_binary_rate(
        self,
        data: pd.DataFrame,
        indicator: str,
        name: str,
        definition: str,
    ) -> DomainMetric:
        require_columns(data, [self.schema.trainee_id, indicator])
        frame = data[[self.schema.trainee_id, indicator]].dropna().copy()
        if frame[self.schema.trainee_id].duplicated().any():
            raise ValueError(f"{name} requires one row per trainee.")
        values = require_binary(frame[indicator], name=indicator)
        return proportion_metric(
            name=name,
            numerator=int(values.sum()),
            denominator=int(len(values)),
            definition=definition,
        )

    def program_outcomes(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        minimum_n: int = 5,
    ) -> pd.DataFrame:
        require_columns(data, [self.schema.program, outcome])
        frame = data[[self.schema.program, outcome]].dropna().copy()
        values = require_binary(frame[outcome], name=outcome)
        frame["_value"] = values
        summary = (
            frame.groupby(self.schema.program)["_value"]
            .agg(n="count", rate="mean")
            .reset_index()
        )
        summary["suppressed"] = summary["n"] < minimum_n
        summary.loc[summary["suppressed"], "rate"] = pd.NA
        return summary

    def site_analysis(
        self,
        data: pd.DataFrame,
        *,
        outcome: str,
        minimum_n: int = 5,
    ) -> pd.DataFrame:
        require_columns(data, [self.schema.site, outcome])
        frame = data[[self.schema.site, outcome]].dropna().copy()
        frame["_outcome"] = pd.to_numeric(frame[outcome], errors="coerce")
        summary = (
            frame.groupby(self.schema.site)["_outcome"]
            .agg(n="count", mean="mean", median="median", std="std")
            .reset_index()
        )
        summary["suppressed"] = summary["n"] < minimum_n
        for column in ["mean", "median", "std"]:
            summary.loc[summary["suppressed"], column] = pd.NA
        return summary

    def workforce_distribution(self, data: pd.DataFrame) -> pd.DataFrame:
        require_columns(data, [self.schema.specialty])
        counts = data[self.schema.specialty].value_counts(dropna=False).rename_axis("specialty")
        result = counts.reset_index(name="count")
        result["proportion"] = result["count"] / result["count"].sum()
        return result

    def attrition_contract(
        self,
        *,
        predictors: list[str],
        decision_to_support: str,
        population: str,
    ) -> AnalysisContract:
        return standard_contract(
            question="Which pre-specified factors are associated with trainee attrition?",
            decision_to_support=decision_to_support,
            population=population,
            outcome=self.schema.attrited,
            predictors=predictors,
            analysis_type=AnalysisType.INFERENTIAL,
            outcome_type="binary",
            assumptions=["attrition definition is prespecified and stable"],
            risks=["program-level clustering", "small program sizes", "informative missingness"],
            metadata={"domain": "academic_medicine", "subpack": "gme", "analysis": "attrition"},
        )
