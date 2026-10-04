from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .common import proportion_metric, require_binary, require_columns


@dataclass(slots=True)
class WorkforceSchema:
    person_id: str = "person_id"
    cohort: str = "cohort"
    retained_in_state: str = "retained_in_state"
    specialty: str = "specialty"
    geography: str = "geography"
    underserved: str = "underserved"
    pipeline_stage: str = "pipeline_stage"


class WorkforcePack:
    name = "workforce"

    def __init__(self, schema: WorkforceSchema | None = None) -> None:
        self.schema = schema or WorkforceSchema()

    def retention_rate(self, data: pd.DataFrame) -> dict[str, Any]:
        require_columns(data, [self.schema.person_id, self.schema.retained_in_state])
        frame = data[[self.schema.person_id, self.schema.retained_in_state]].dropna().copy()
        if frame[self.schema.person_id].duplicated().any():
            raise ValueError("Retention requires one row per person.")
        retained = require_binary(frame[self.schema.retained_in_state], name=self.schema.retained_in_state)
        return proportion_metric(
            name="in_state_retention",
            numerator=int(retained.sum()),
            denominator=int(len(retained)),
            definition="People retained in the target state divided by eligible people with known retention status.",
        ).to_dict()

    def specialty_distribution(self, data: pd.DataFrame) -> pd.DataFrame:
        require_columns(data, [self.schema.specialty])
        result = (
            data[self.schema.specialty]
            .value_counts(dropna=False)
            .rename_axis("specialty")
            .reset_index(name="count")
        )
        result["proportion"] = result["count"] / result["count"].sum()
        return result

    def geography_distribution(self, data: pd.DataFrame) -> pd.DataFrame:
        require_columns(data, [self.schema.geography])
        result = (
            data[self.schema.geography]
            .value_counts(dropna=False)
            .rename_axis("geography")
            .reset_index(name="count")
        )
        result["proportion"] = result["count"] / result["count"].sum()
        return result

    def underserved_practice_rate(self, data: pd.DataFrame) -> dict[str, Any]:
        require_columns(data, [self.schema.person_id, self.schema.underserved])
        frame = data[[self.schema.person_id, self.schema.underserved]].dropna().copy()
        if frame[self.schema.person_id].duplicated().any():
            raise ValueError("Underserved practice rate requires one row per person.")
        values = require_binary(frame[self.schema.underserved], name=self.schema.underserved)
        return proportion_metric(
            name="underserved_practice_rate",
            numerator=int(values.sum()),
            denominator=int(len(values)),
            definition="People practicing in the locally defined underserved setting divided by eligible people with known status.",
        ).to_dict()

    def pipeline(self, data: pd.DataFrame, *, stage_order: list[str] | None = None) -> pd.DataFrame:
        require_columns(data, [self.schema.pipeline_stage])
        counts = (
            data[self.schema.pipeline_stage]
            .value_counts(dropna=False)
            .rename_axis("stage")
            .reset_index(name="count")
        )
        counts["proportion_of_total"] = counts["count"] / counts["count"].sum()
        if stage_order:
            order = {stage: index for index, stage in enumerate(stage_order)}
            counts["_order"] = counts["stage"].map(order).fillna(len(order))
            counts = counts.sort_values(["_order", "stage"]).drop(columns="_order")
        return counts.reset_index(drop=True)

    def pipeline_conversion(
        self,
        data: pd.DataFrame,
        *,
        from_stage: str,
        to_stage: str,
    ) -> dict[str, Any]:
        require_columns(data, [self.schema.person_id, self.schema.pipeline_stage])
        frame = data[[self.schema.person_id, self.schema.pipeline_stage]].dropna().copy()
        reached_from = set(
            frame.loc[frame[self.schema.pipeline_stage] == from_stage, self.schema.person_id]
        )
        reached_to = set(
            frame.loc[frame[self.schema.pipeline_stage] == to_stage, self.schema.person_id]
        )
        numerator = len(reached_from.intersection(reached_to))
        denominator = len(reached_from)
        return {
            "from_stage": from_stage,
            "to_stage": to_stage,
            "numerator": numerator,
            "denominator": denominator,
            "conversion_rate": numerator / denominator if denominator else None,
        }
