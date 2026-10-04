from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .common import require_columns


@dataclass(slots=True)
class ResearchSchema:
    year: str = "year"
    nih_funding: str = "nih_funding"
    publications: str = "publications"
    citations: str = "citations"
    grant_submitted: str = "grant_submitted"
    grant_awarded: str = "grant_awarded"
    trial_id: str = "trial_id"
    trial_status: str = "trial_status"


class ResearchPack:
    name = "research"

    def __init__(self, schema: ResearchSchema | None = None) -> None:
        self.schema = schema or ResearchSchema()

    def nih_funding_trend(self, data: pd.DataFrame) -> dict[str, Any]:
        require_columns(data, [self.schema.year, self.schema.nih_funding])
        frame = data[[self.schema.year, self.schema.nih_funding]].dropna().copy()
        frame[self.schema.year] = pd.to_numeric(frame[self.schema.year], errors="raise")
        frame[self.schema.nih_funding] = pd.to_numeric(
            frame[self.schema.nih_funding], errors="raise"
        )
        frame = frame.sort_values(self.schema.year)
        first = float(frame[self.schema.nih_funding].iloc[0])
        last = float(frame[self.schema.nih_funding].iloc[-1])
        periods = max(int(frame[self.schema.year].iloc[-1] - frame[self.schema.year].iloc[0]), 0)
        cagr = None
        if periods > 0 and first > 0 and last >= 0:
            cagr = float((last / first) ** (1 / periods) - 1)
        return {
            "start_year": int(frame[self.schema.year].iloc[0]),
            "end_year": int(frame[self.schema.year].iloc[-1]),
            "start_funding": first,
            "end_funding": last,
            "absolute_growth": last - first,
            "cagr": cagr,
        }

    def publication_summary(self, data: pd.DataFrame) -> dict[str, Any]:
        require_columns(data, [self.schema.publications])
        publications = pd.to_numeric(data[self.schema.publications], errors="coerce")
        result = {
            "total_publications": float(publications.sum()),
            "mean_publications_per_row": float(publications.mean()),
        }
        if self.schema.citations in data.columns:
            citations = pd.to_numeric(data[self.schema.citations], errors="coerce")
            result["total_citations"] = float(citations.sum())
            result["citations_per_publication"] = (
                float(citations.sum() / publications.sum())
                if publications.sum() > 0
                else None
            )
        return result

    def grant_success(self, data: pd.DataFrame) -> dict[str, Any]:
        require_columns(data, [self.schema.grant_submitted, self.schema.grant_awarded])
        submitted = pd.to_numeric(data[self.schema.grant_submitted], errors="raise")
        awarded = pd.to_numeric(data[self.schema.grant_awarded], errors="raise")
        total_submitted = float(submitted.sum())
        total_awarded = float(awarded.sum())
        if total_awarded > total_submitted:
            raise ValueError("Awarded grants cannot exceed submitted grants.")
        return {
            "submitted": total_submitted,
            "awarded": total_awarded,
            "success_rate": total_awarded / total_submitted if total_submitted else None,
        }

    def clinical_trial_portfolio(self, data: pd.DataFrame) -> dict[str, Any]:
        require_columns(data, [self.schema.trial_id, self.schema.trial_status])
        frame = data[[self.schema.trial_id, self.schema.trial_status]].dropna().copy()
        frame = frame.drop_duplicates(self.schema.trial_id)
        counts = frame[self.schema.trial_status].value_counts().to_dict()
        return {
            "unique_trials": int(frame[self.schema.trial_id].nunique()),
            "status_counts": {str(key): int(value) for key, value in counts.items()},
        }

    def research_growth_index(
        self,
        data: pd.DataFrame,
        *,
        baseline_year: int,
        funding_weight: float = 0.5,
        publication_weight: float = 0.3,
        grant_weight: float = 0.2,
    ) -> pd.DataFrame:
        require_columns(
            data,
            [
                self.schema.year,
                self.schema.nih_funding,
                self.schema.publications,
                self.schema.grant_awarded,
            ],
        )
        frame = data.copy()
        frame[self.schema.year] = pd.to_numeric(frame[self.schema.year], errors="raise").astype(int)
        base_rows = frame.loc[frame[self.schema.year] == baseline_year]
        if base_rows.empty:
            raise ValueError("baseline_year is not present in the data.")

        metrics = [
            (self.schema.nih_funding, funding_weight),
            (self.schema.publications, publication_weight),
            (self.schema.grant_awarded, grant_weight),
        ]
        weight_sum = sum(weight for _, weight in metrics)
        if not np.isclose(weight_sum, 1.0):
            raise ValueError("Growth-index weights must sum to 1.")

        components = []
        for column, weight in metrics:
            values = pd.to_numeric(frame[column], errors="coerce")
            baseline = float(pd.to_numeric(base_rows[column], errors="coerce").mean())
            normalized = values / baseline if baseline != 0 else pd.Series(np.nan, index=frame.index)
            components.append(normalized * weight)

        result = frame[[self.schema.year]].copy()
        result["research_growth_index"] = sum(components)
        result["baseline_year"] = baseline_year
        return result
