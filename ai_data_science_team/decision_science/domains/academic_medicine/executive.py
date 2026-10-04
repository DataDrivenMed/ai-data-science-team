from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd

from ...provenance import EvidenceLedger, fingerprint_dataframe
from .accreditation import AccreditationMetricSpec, AccreditationPack
from .admissions import AdmissionsPack
from .gme import GMEPack
from .research import ResearchPack
from .ume import UMEPack
from .workforce import WorkforcePack


@dataclass(slots=True)
class RegisteredDataset:
    name: str
    data: pd.DataFrame
    source: str
    version: str | None
    fingerprint: str
    loaded_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "loaded_at": self.loaded_at,
            "rows": int(len(self.data)),
            "columns": int(len(self.data.columns)),
        }


class DatasetRegistry:
    def __init__(self) -> None:
        self._datasets: dict[str, RegisteredDataset] = {}

    def register(self, name: str, data: pd.DataFrame, *, source: str, version: str | None = None) -> RegisteredDataset:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        if not name.strip():
            raise ValueError("dataset name is required")
        registered = RegisteredDataset(
            name=name,
            data=data.copy(),
            source=source,
            version=version,
            fingerprint=fingerprint_dataframe(data),
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )
        self._datasets[name] = registered
        return registered

    def get(self, name: str) -> RegisteredDataset:
        if name not in self._datasets:
            raise KeyError(f"Dataset {name!r} is not registered.")
        return self._datasets[name]

    def names(self) -> list[str]:
        return sorted(self._datasets)

    def inventory(self) -> pd.DataFrame:
        return pd.DataFrame([dataset.to_dict() for dataset in self._datasets.values()])


@dataclass(slots=True)
class CQIMetricSpec:
    metric_id: str
    name: str
    domain: str
    dataset: str
    calculator: str
    owner: str
    source: str
    direction: str = "higher_is_better"
    target: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    period_column: str | None = None
    unit: str = "proportion"
    standard_or_element: str | None = None
    cadence: str | None = None
    calculator_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MetricResult:
    metric_id: str
    name: str
    domain: str
    value: float | None
    unit: str
    status: str
    owner: str
    source: str
    dataset: str
    target: float | None
    warning_threshold: float | None
    critical_threshold: float | None
    standard_or_element: str | None
    cadence: str | None
    period: str | None = None
    numerator: float | int | None = None
    denominator: float | int | None = None
    evidence_record_id: str | None = None
    dataset_fingerprint: str | None = None
    calculation: str | None = None
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AcademicMedicineCQIEngine:
    """Unified academic-medicine metric, trend, alert, and evidence engine."""

    def __init__(self, *, registry: DatasetRegistry | None = None, ledger: EvidenceLedger | None = None) -> None:
        self.registry = registry or DatasetRegistry()
        self.ledger = ledger or EvidenceLedger()
        self.admissions = AdmissionsPack()
        self.ume = UMEPack()
        self.gme = GMEPack()
        self.accreditation = AccreditationPack()
        self.research = ResearchPack()
        self.workforce = WorkforcePack()
        self._calculators: dict[str, Callable[..., Any]] = {
            "admissions.interview_rate": lambda df, **_: self.admissions.applicant_funnel(df)["interview_rate"],
            "admissions.admit_rate": lambda df, **_: self.admissions.applicant_funnel(df)["admit_rate"],
            "admissions.yield": lambda df, **_: self.admissions.applicant_funnel(df)["yield"],
            "admissions.matriculation_rate": lambda df, **_: self.admissions.applicant_funnel(df)["overall_matriculation_rate"],
            "ume.first_attempt_pass_rate": self._ume_first_attempt_pass_rate,
            "ume.remediation_rate": lambda df, **_: self.ume.remediation_rate(df),
            "ume.progression_rate": lambda df, **_: self.ume.progression_rate(df),
            "gme.survey_response_rate": lambda df, **_: self.gme.survey_response(df),
            "gme.attrition_rate": lambda df, **_: self.gme.attrition_rate(df),
            "gme.board_pass_rate": lambda df, **_: self.gme.board_pass_rate(df),
            "gme.retention_rate": lambda df, **_: self.gme.retention_rate(df),
            "research.nih_funding": self._research_nih_funding,
            "research.grant_success_rate": self._research_grant_success,
            "research.total_publications": self._research_publications,
            "research.unique_trials": self._research_trials,
            "workforce.in_state_retention": self._workforce_retention,
            "workforce.underserved_practice_rate": self._workforce_underserved,
        }

    @property
    def calculators(self) -> tuple[str, ...]:
        return tuple(sorted(self._calculators))

    def register_calculator(self, name: str, calculator: Callable[..., Any]) -> None:
        self._calculators[name] = calculator

    def compute(self, spec: CQIMetricSpec, *, period: Any | None = None) -> MetricResult:
        dataset = self.registry.get(spec.dataset)
        data = dataset.data
        if spec.period_column and period is not None:
            if spec.period_column not in data.columns:
                raise ValueError(f"Period column {spec.period_column!r} not found in dataset {spec.dataset!r}.")
            data = data.loc[data[spec.period_column].astype(str) == str(period)].copy()

        if spec.calculator not in self._calculators:
            raise KeyError(f"Unknown calculator {spec.calculator!r}.")
        raw = self._calculators[spec.calculator](data, **spec.calculator_params)
        value, numerator, denominator, warning, calculation = self._normalize_metric(raw)

        status = "NO_DATA"
        if value is not None:
            status = self.accreditation.metric_status(
                float(value),
                AccreditationMetricSpec(
                    metric_id=spec.metric_id,
                    name=spec.name,
                    owner=spec.owner,
                    source=spec.source,
                    direction=spec.direction,
                    target=spec.target,
                    warning_threshold=spec.warning_threshold,
                    critical_threshold=spec.critical_threshold,
                    standard_or_element=spec.standard_or_element,
                    cadence=spec.cadence,
                ),
            )

        record = self.ledger.add(
            kind="cqi_metric",
            claim=f"{spec.name} = {value}",
            source=dataset.source,
            transformation=calculation or spec.calculator,
            dataset_fingerprint=dataset.fingerprint,
            validation_status=status,
            metadata={
                "metric_id": spec.metric_id,
                "domain": spec.domain,
                "dataset": spec.dataset,
                "period": None if period is None else str(period),
                "owner": spec.owner,
                "standard_or_element": spec.standard_or_element,
            },
        )
        return MetricResult(
            metric_id=spec.metric_id,
            name=spec.name,
            domain=spec.domain,
            value=None if value is None else float(value),
            unit=spec.unit,
            status=status,
            owner=spec.owner,
            source=spec.source,
            dataset=spec.dataset,
            target=spec.target,
            warning_threshold=spec.warning_threshold,
            critical_threshold=spec.critical_threshold,
            standard_or_element=spec.standard_or_element,
            cadence=spec.cadence,
            period=None if period is None else str(period),
            numerator=numerator,
            denominator=denominator,
            evidence_record_id=record.record_id,
            dataset_fingerprint=dataset.fingerprint,
            calculation=calculation or spec.calculator,
            warning=warning,
        )

    def snapshot(self, specs: list[CQIMetricSpec]) -> pd.DataFrame:
        return pd.DataFrame([self.compute(spec).to_dict() for spec in specs])

    def trends(self, specs: list[CQIMetricSpec]) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for spec in specs:
            if not spec.period_column:
                continue
            dataset = self.registry.get(spec.dataset)
            if spec.period_column not in dataset.data.columns:
                continue
            periods = dataset.data[spec.period_column].dropna().astype(str).drop_duplicates().sort_values()
            for period in periods:
                rows.append(self.compute(spec, period=period).to_dict())
        return pd.DataFrame(rows)

    def domain_scorecard(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot.empty:
            return pd.DataFrame()
        rows = []
        for domain, subset in snapshot.groupby("domain"):
            counts = subset["status"].value_counts()
            attention = int(counts.get("WARNING", 0) + counts.get("CRITICAL", 0))
            rows.append({
                "domain": domain,
                "metrics": int(len(subset)),
                "on_target": int(counts.get("ON_TARGET", 0)),
                "monitor": int(counts.get("MONITOR", 0)),
                "warning": int(counts.get("WARNING", 0)),
                "critical": int(counts.get("CRITICAL", 0)),
                "attention_rate": attention / len(subset) if len(subset) else 0.0,
            })
        return pd.DataFrame(rows).sort_values(["critical", "warning", "domain"], ascending=[False, False, True])

    @staticmethod
    def exceptions(snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot.empty:
            return snapshot.copy()
        order = {"CRITICAL": 0, "WARNING": 1}
        frame = snapshot.loc[snapshot["status"].isin(order)].copy()
        if frame.empty:
            return frame
        frame["_order"] = frame["status"].map(order)
        return frame.sort_values(["_order", "domain", "name"]).drop(columns="_order")

    def executive_brief(
        self,
        snapshot: pd.DataFrame,
        trends: pd.DataFrame | None = None,
        *,
        institution_name: str = "Academic Health Center",
        as_of: str | None = None,
    ) -> str:
        as_of = as_of or datetime.now(timezone.utc).date().isoformat()
        if snapshot.empty:
            return f"# {institution_name} Executive Academic Medicine Brief\\n\\nNo CQI metrics are available."

        total = len(snapshot)
        critical = snapshot.loc[snapshot["status"] == "CRITICAL"]
        warning = snapshot.loc[snapshot["status"] == "WARNING"]
        on_target = snapshot.loc[snapshot["status"] == "ON_TARGET"]
        monitor = snapshot.loc[snapshot["status"] == "MONITOR"]
        lines = [
            f"# {institution_name} Executive Academic Medicine Brief",
            "",
            f"**As of:** {as_of}",
            "",
            "## Executive signal",
            f"{len(on_target)} of {total} monitored metrics are on target; {len(monitor)} are in monitor status, {len(warning)} require attention, and {len(critical)} are critical.",
            "",
        ]
        if not critical.empty:
            lines.append("## Immediate executive attention")
            for _, row in critical.head(5).iterrows():
                lines.append(f"- **{row['name']} ({row['domain']}):** {self._format_value(row['value'], row['unit'])}. Owner: {row['owner']}.")
            lines.append("")
        if not warning.empty:
            lines.append("## Watch list")
            for _, row in warning.head(7).iterrows():
                lines.append(f"- **{row['name']} ({row['domain']}):** {self._format_value(row['value'], row['unit'])}. Review trajectory, denominator, and action plan.")
            lines.append("")
        signals = self._trend_signals(trends)
        if signals:
            lines.append("## Longitudinal signals")
            lines.extend(f"- {signal}" for signal in signals[:6])
            lines.append("")
        lines.extend([
            "## Leadership action frame",
            "1. Confirm ownership and action plans for every critical metric.",
            "2. Review warning metrics for trajectory, denominator changes, and data-quality issues.",
            "3. Distinguish true performance change from definition or source-system change.",
            "4. Preserve evidence lineage and document decisions before the next CQI cycle.",
            "",
            "## Evidence note",
            "All values use the same registered datasets, metric definitions, thresholds, and evidence lineage as the dashboard.",
        ])
        return "\\n".join(lines)

    @staticmethod
    def _normalize_metric(raw: Any) -> tuple[float | None, float | int | None, float | int | None, str | None, str | None]:
        if hasattr(raw, "to_dict"):
            raw = raw.to_dict()
        if isinstance(raw, dict):
            value = raw.get("value")
            if value is None:
                for key in ("success_rate", "conversion_rate", "end_funding", "total_publications", "unique_trials", "first_attempt_pass_rate"):
                    if key in raw:
                        value = raw[key]
                        break
            return (
                None if value is None else float(value),
                raw.get("numerator"),
                raw.get("denominator"),
                raw.get("warning"),
                raw.get("definition") or raw.get("metric"),
            )
        if isinstance(raw, (int, float)):
            return float(raw), None, None, None, None
        raise TypeError(f"Unsupported metric result type: {type(raw).__name__}")

    def _ume_first_attempt_pass_rate(self, df: pd.DataFrame, **params: Any) -> dict[str, Any]:
        result = self.ume.first_attempt_outcomes(df, exam_name=params.get("exam_name"))
        return {"value": result["first_attempt_pass_rate"], "denominator": result["n"], "definition": result["attempt_rule"]}

    def _research_nih_funding(self, df: pd.DataFrame, **_: Any) -> dict[str, Any]:
        result = self.research.nih_funding_trend(df)
        return {"value": result["end_funding"], "definition": "Most recent NIH funding value in selected data."}

    def _research_grant_success(self, df: pd.DataFrame, **_: Any) -> dict[str, Any]:
        result = self.research.grant_success(df)
        return {"value": result["success_rate"], "numerator": result["awarded"], "denominator": result["submitted"], "definition": "Awarded grants divided by submitted grants."}

    def _research_publications(self, df: pd.DataFrame, **_: Any) -> dict[str, Any]:
        result = self.research.publication_summary(df)
        return {"value": result["total_publications"], "definition": "Total publications in selected data."}

    def _research_trials(self, df: pd.DataFrame, **_: Any) -> dict[str, Any]:
        result = self.research.clinical_trial_portfolio(df)
        return {"value": result["unique_trials"], "definition": "Unique clinical trials in selected data."}

    def _workforce_retention(self, df: pd.DataFrame, **_: Any) -> dict[str, Any]:
        return self.workforce.retention_rate(df)

    def _workforce_underserved(self, df: pd.DataFrame, **_: Any) -> dict[str, Any]:
        return self.workforce.underserved_practice_rate(df)

    @staticmethod
    def _format_value(value: Any, unit: Any) -> str:
        if value is None or pd.isna(value):
            return "No data"
        if unit == "proportion":
            return f"{float(value) * 100:.1f}%"
        if unit == "currency":
            return f"${float(value):,.0f}"
        if unit == "count":
            return f"{float(value):,.0f}"
        return f"{float(value):,.2f}"

    @staticmethod
    def _trend_signals(trends: pd.DataFrame | None) -> list[str]:
        if trends is None or trends.empty:
            return []
        signals: list[str] = []
        for _, subset in trends.groupby("metric_id"):
            subset = subset.dropna(subset=["value"]).copy().sort_values("period")
            if len(subset) < 2:
                continue
            first = float(subset.iloc[0]["value"])
            last = float(subset.iloc[-1]["value"])
            delta = last - first
            name = str(subset.iloc[-1]["name"])
            unit = str(subset.iloc[-1]["unit"])
            if unit == "proportion":
                change = f"{delta * 100:+.1f} percentage points"
            elif unit == "currency":
                change = f"${delta:+,.0f}"
            else:
                change = f"{delta:+,.2f}"
            signals.append(f"{name} changed {change} from {subset.iloc[0]['period']} to {subset.iloc[-1]['period']}.")
        return signals
