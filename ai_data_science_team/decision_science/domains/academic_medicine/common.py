from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ...contracts import AnalysisContract, AnalysisType


@dataclass(slots=True)
class DomainMetric:
    name: str
    numerator: float | int | None
    denominator: float | int | None
    value: float | None
    unit: str
    definition: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": self.value,
            "unit": self.unit,
            "definition": self.definition,
            "metadata": self.metadata,
        }


def require_columns(data: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def require_binary(series: pd.Series, *, name: str) -> pd.Series:
    values = pd.to_numeric(series, errors="raise").astype(int)
    invalid = set(values.dropna().unique()) - {0, 1}
    if invalid:
        raise ValueError(f"{name} must be coded 0/1.")
    return values


def one_row_per_entity(data: pd.DataFrame, entity_id: str) -> None:
    if data[entity_id].duplicated().any():
        raise ValueError(f"{entity_id} must be unique for this metric.")


def proportion_metric(
    *,
    name: str,
    numerator: int,
    denominator: int,
    definition: str,
    metadata: dict[str, Any] | None = None,
) -> DomainMetric:
    return DomainMetric(
        name=name,
        numerator=numerator,
        denominator=denominator,
        value=(numerator / denominator if denominator else None),
        unit="proportion",
        definition=definition,
        metadata=metadata or {},
    )


def standard_contract(
    *,
    question: str,
    decision_to_support: str,
    population: str,
    outcome: str | None,
    predictors: list[str] | None = None,
    analysis_type: AnalysisType = AnalysisType.INFERENTIAL,
    outcome_type: str | None = None,
    assumptions: list[str] | None = None,
    risks: list[str] | None = None,
    approvals: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AnalysisContract:
    return AnalysisContract(
        question=question,
        decision_to_support=decision_to_support,
        population=population,
        outcome=outcome,
        target_variable=outcome
        if analysis_type in {AnalysisType.PREDICTIVE, AnalysisType.CAUSAL}
        else None,
        predictors=list(predictors or []),
        analysis_type=analysis_type,
        outcome_type=outcome_type,
        assumptions=list(assumptions or []),
        risks=list(risks or []),
        human_approval_required=list(approvals or []),
        metadata=metadata or {},
    )
