from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ...contracts import AnalysisContract, AnalysisType
from .common import (
    DomainMetric,
    one_row_per_entity,
    proportion_metric,
    require_binary,
    require_columns,
    standard_contract,
)


@dataclass(slots=True)
class AdmissionsSchema:
    applicant_id: str = "applicant_id"
    cycle: str = "cycle"
    applied: str = "applied"
    interviewed: str = "interviewed"
    admitted: str = "admitted"
    matriculated: str = "matriculated"
    mcat: str = "mcat"
    gpa: str = "gpa"
    science_gpa: str = "science_gpa"
    scholarship_amount: str = "scholarship_amount"


class AdmissionsPack:
    name = "admissions"

    def __init__(self, schema: AdmissionsSchema | None = None) -> None:
        self.schema = schema or AdmissionsSchema()

    def validate(self, data: pd.DataFrame) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        required = [self.schema.applicant_id, self.schema.cycle]
        missing = [column for column in required if column not in data.columns]
        if missing:
            return [{"code": "missing_required_columns", "severity": "blocker", "columns": missing}]
        if data[self.schema.applicant_id].isna().any():
            issues.append({"code": "missing_applicant_id", "severity": "blocker"})
        duplicate = data.duplicated([self.schema.applicant_id, self.schema.cycle])
        if duplicate.any():
            issues.append(
                {
                    "code": "duplicate_applicant_cycle",
                    "severity": "blocker",
                    "count": int(duplicate.sum()),
                }
            )
        for column in [self.schema.mcat, self.schema.gpa, self.schema.science_gpa]:
            if column in data.columns:
                values = pd.to_numeric(data[column], errors="coerce")
                if values.isna().sum() > data[column].isna().sum():
                    issues.append(
                        {
                            "code": "non_numeric_academic_metric",
                            "severity": "warning",
                            "column": column,
                        }
                    )
        return issues

    def applicant_funnel(self, data: pd.DataFrame) -> dict[str, DomainMetric]:
        columns = [
            self.schema.applicant_id,
            self.schema.applied,
            self.schema.interviewed,
            self.schema.admitted,
            self.schema.matriculated,
        ]
        require_columns(data, columns)
        one_row_per_entity(data, self.schema.applicant_id)
        frame = data[columns].copy()
        for column in columns[1:]:
            frame[column] = require_binary(frame[column], name=column)

        applied = int(frame[self.schema.applied].sum())
        interviewed = int(frame[self.schema.interviewed].sum())
        admitted = int(frame[self.schema.admitted].sum())
        matriculated = int(frame[self.schema.matriculated].sum())

        return {
            "interview_rate": proportion_metric(
                name="interview_rate",
                numerator=interviewed,
                denominator=applied,
                definition="Interviewed applicants divided by applicants.",
            ),
            "admit_rate": proportion_metric(
                name="admit_rate",
                numerator=admitted,
                denominator=interviewed,
                definition="Admitted applicants divided by interviewed applicants.",
            ),
            "yield": proportion_metric(
                name="yield",
                numerator=matriculated,
                denominator=admitted,
                definition="Matriculated applicants divided by admitted applicants.",
            ),
            "overall_matriculation_rate": proportion_metric(
                name="overall_matriculation_rate",
                numerator=matriculated,
                denominator=applied,
                definition="Matriculated applicants divided by applicants.",
            ),
        }

    def academic_profile(
        self,
        data: pd.DataFrame,
        *,
        matriculated_only: bool = False,
    ) -> dict[str, dict[str, float | int | None]]:
        columns = [self.schema.mcat, self.schema.gpa, self.schema.science_gpa]
        require_columns(data, columns)
        frame = data.copy()
        if matriculated_only:
            require_columns(frame, [self.schema.matriculated])
            matriculated = require_binary(frame[self.schema.matriculated], name=self.schema.matriculated)
            frame = frame.loc[matriculated == 1]

        output: dict[str, dict[str, float | int | None]] = {}
        for column in columns:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            output[column] = {
                "n": int(len(values)),
                "mean": float(values.mean()) if len(values) else None,
                "median": float(values.median()) if len(values) else None,
                "p25": float(values.quantile(0.25)) if len(values) else None,
                "p75": float(values.quantile(0.75)) if len(values) else None,
            }
        return output

    def scholarship_strategy(
        self,
        data: pd.DataFrame,
        *,
        target_column: str | None = None,
        target_value: Any | None = None,
    ) -> dict[str, Any]:
        require_columns(
            data,
            [
                self.schema.applicant_id,
                self.schema.admitted,
                self.schema.matriculated,
                self.schema.scholarship_amount,
            ],
        )
        frame = data.copy()
        if target_column is not None:
            require_columns(frame, [target_column])
            frame = frame.loc[frame[target_column] == target_value]

        admitted = require_binary(frame[self.schema.admitted], name=self.schema.admitted)
        eligible = frame.loc[admitted == 1].copy()
        one_row_per_entity(eligible, self.schema.applicant_id)
        eligible["_matriculated"] = require_binary(
            eligible[self.schema.matriculated],
            name=self.schema.matriculated,
        )
        eligible["_scholarship"] = pd.to_numeric(
            eligible[self.schema.scholarship_amount],
            errors="raise",
        ).fillna(0.0)

        with_award = eligible["_scholarship"] > 0
        without_award = ~with_award

        def rate(mask: pd.Series) -> float | None:
            denominator = int(mask.sum())
            if denominator == 0:
                return None
            return float(eligible.loc[mask, "_matriculated"].mean())

        return {
            "eligible_admits": int(len(eligible)),
            "total_scholarship_commitment": float(eligible["_scholarship"].sum()),
            "mean_award_among_awarded": (
                float(eligible.loc[with_award, "_scholarship"].mean())
                if with_award.any()
                else 0.0
            ),
            "yield_with_scholarship": rate(with_award),
            "yield_without_scholarship": rate(without_award),
            "awarded_count": int(with_award.sum()),
            "target_column": target_column,
            "target_value": target_value,
            "warning": "Observed yield differences are descriptive and should not be interpreted as scholarship causal effects without adjustment.",
        }

    def fairness_summary(
        self,
        data: pd.DataFrame,
        *,
        group: str,
        outcome: str,
        reference_group: Any | None = None,
        minimum_n: int = 5,
    ) -> dict[str, Any]:
        require_columns(data, [group, outcome])
        frame = data[[group, outcome]].dropna().copy()
        frame["_outcome"] = require_binary(frame[outcome], name=outcome)

        rows: dict[str, dict[str, float | int | None]] = {}
        for value, subset in frame.groupby(group, dropna=False):
            n = int(len(subset))
            rows[str(value)] = {
                "n": n,
                "rate": float(subset["_outcome"].mean()) if n >= minimum_n else None,
                "suppressed": n < minimum_n,
            }

        if reference_group is None:
            eligible = {
                key: value
                for key, value in rows.items()
                if value["rate"] is not None
            }
            reference_key = max(
                eligible,
                key=lambda key: eligible[key]["n"],
                default=None,
            )
        else:
            reference_key = str(reference_group)

        reference_rate = (
            rows.get(reference_key, {}).get("rate") if reference_key is not None else None
        )
        for values in rows.values():
            rate = values["rate"]
            values["risk_difference_vs_reference"] = (
                float(rate - reference_rate)
                if rate is not None and reference_rate is not None
                else None
            )
            values["rate_ratio_vs_reference"] = (
                float(rate / reference_rate)
                if rate is not None and reference_rate not in (None, 0)
                else None
            )

        return {
            "group": group,
            "outcome": outcome,
            "reference_group": reference_key,
            "minimum_n": minimum_n,
            "groups": rows,
            "note": "Group-level rate differences are descriptive screening signals, not proof of bias or discrimination.",
        }

    def yield_contract(
        self,
        *,
        predictors: list[str],
        decision_to_support: str,
        population: str,
    ) -> AnalysisContract:
        return standard_contract(
            question="Which applicant-level factors are associated with matriculation among admitted applicants?",
            decision_to_support=decision_to_support,
            population=population,
            outcome=self.schema.matriculated,
            predictors=predictors,
            analysis_type=AnalysisType.INFERENTIAL,
            outcome_type="binary",
            assumptions=["one row per applicant/cycle", "admissions-cycle definitions are stable or modeled"],
            risks=["selection into the admitted pool can affect associations"],
            metadata={"domain": "academic_medicine", "subpack": "admissions", "analysis": "yield"},
        )
