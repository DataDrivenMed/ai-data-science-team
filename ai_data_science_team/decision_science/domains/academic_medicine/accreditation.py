from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .common import require_columns


@dataclass(slots=True)
class AccreditationMetricSpec:
    metric_id: str
    name: str
    owner: str
    source: str
    direction: str = "higher_is_better"
    target: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    standard_or_element: str | None = None
    cadence: str | None = None


class AccreditationPack:
    name = "accreditation"

    @staticmethod
    def metric_status(value: float, spec: AccreditationMetricSpec) -> str:
        direction = spec.direction
        if direction not in {"higher_is_better", "lower_is_better"}:
            raise ValueError("direction must be higher_is_better or lower_is_better")

        if direction == "higher_is_better":
            if spec.critical_threshold is not None and value < spec.critical_threshold:
                return "CRITICAL"
            if spec.warning_threshold is not None and value < spec.warning_threshold:
                return "WARNING"
            if spec.target is not None and value >= spec.target:
                return "ON_TARGET"
            return "MONITOR"

        if spec.critical_threshold is not None and value > spec.critical_threshold:
            return "CRITICAL"
        if spec.warning_threshold is not None and value > spec.warning_threshold:
            return "WARNING"
        if spec.target is not None and value <= spec.target:
            return "ON_TARGET"
        return "MONITOR"

    def cqi_snapshot(
        self,
        data: pd.DataFrame,
        *,
        metric_id: str = "metric_id",
        value: str = "value",
        specs: list[AccreditationMetricSpec],
    ) -> pd.DataFrame:
        require_columns(data, [metric_id, value])
        spec_map = {spec.metric_id: spec for spec in specs}
        rows: list[dict[str, Any]] = []
        for _, row in data.iterrows():
            mid = str(row[metric_id])
            if mid not in spec_map:
                continue
            spec = spec_map[mid]
            numeric_value = float(row[value])
            rows.append(
                {
                    "metric_id": mid,
                    "name": spec.name,
                    "value": numeric_value,
                    "status": self.metric_status(numeric_value, spec),
                    "owner": spec.owner,
                    "source": spec.source,
                    "standard_or_element": spec.standard_or_element,
                    "cadence": spec.cadence,
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def threshold_alerts(snapshot: pd.DataFrame) -> pd.DataFrame:
        require_columns(snapshot, ["status"])
        return snapshot.loc[snapshot["status"].isin(["WARNING", "CRITICAL"])].copy()

    @staticmethod
    def evidence_lineage(
        *,
        metric_id: str,
        source: str,
        source_version: str | None,
        calculation: str,
        owner: str,
        review_date: str | None = None,
        evidence_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "metric_id": metric_id,
            "source": source,
            "source_version": source_version,
            "calculation": calculation,
            "owner": owner,
            "review_date": review_date,
            "evidence_refs": list(evidence_refs or []),
        }

    @staticmethod
    def lcme_spec(
        *,
        element: str,
        metric_id: str,
        name: str,
        owner: str,
        source: str,
        target: float | None = None,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        direction: str = "higher_is_better",
        cadence: str | None = None,
    ) -> AccreditationMetricSpec:
        return AccreditationMetricSpec(
            metric_id=metric_id,
            name=name,
            owner=owner,
            source=source,
            direction=direction,
            target=target,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            standard_or_element=f"LCME {element}",
            cadence=cadence,
        )

    @staticmethod
    def acgme_spec(
        *,
        requirement: str,
        metric_id: str,
        name: str,
        owner: str,
        source: str,
        target: float | None = None,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        direction: str = "higher_is_better",
        cadence: str | None = None,
    ) -> AccreditationMetricSpec:
        return AccreditationMetricSpec(
            metric_id=metric_id,
            name=name,
            owner=owner,
            source=source,
            direction=direction,
            target=target,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            standard_or_element=f"ACGME {requirement}",
            cadence=cadence,
        )
