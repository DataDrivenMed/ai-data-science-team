from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class AnalysisType(str, Enum):
    DESCRIPTIVE = "descriptive"
    INFERENTIAL = "inferential"
    PREDICTIVE = "predictive"
    CAUSAL = "causal"
    FORECASTING = "forecasting"
    SURVIVAL = "survival"
    LONGITUDINAL = "longitudinal"


class EvidenceStrength(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class ReviewStatus(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"


@dataclass(slots=True)
class AnalysisContract:
    question: str
    decision_to_support: str
    population: str
    outcome: str | None = None
    predictors: list[str] = field(default_factory=list)
    unit_of_analysis: str | None = None
    time_period: str | None = None
    analysis_type: AnalysisType = AnalysisType.DESCRIPTIVE
    inclusion_criteria: list[str] = field(default_factory=list)
    exclusion_criteria: list[str] = field(default_factory=list)
    required_outputs: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    decision_owner: str | None = None
    target_variable: str | None = None
    outcome_type: str | None = None
    human_approval_required: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name in ("question", "decision_to_support", "population"):
            if not getattr(self, name).strip():
                errors.append(f"{name} is required")
        if self.analysis_type in {AnalysisType.PREDICTIVE, AnalysisType.CAUSAL} and not (
            self.target_variable or self.outcome
        ):
            errors.append(f"{self.analysis_type.value} analysis requires an outcome/target")
        if self.analysis_type == AnalysisType.FORECASTING and not self.time_period:
            errors.append("forecasting analysis should define a time_period")
        return errors

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["analysis_type"] = self.analysis_type.value
        return data

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AnalysisContract":
        data = dict(value)
        if "analysis_type" in data and not isinstance(data["analysis_type"], AnalysisType):
            data["analysis_type"] = AnalysisType(str(data["analysis_type"]).lower())
        return cls(**data)


@dataclass(slots=True)
class QualityIssue:
    code: str
    severity: str
    message: str
    columns: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DataQualityReport:
    row_count: int
    column_count: int
    completeness_score: float
    integrity_score: float
    documentation_score: float | None
    temporal_validity_score: float | None
    representativeness_score: float | None
    overall_score: float
    gate: str
    issues: list[QualityIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MethodRecommendation:
    family: str
    methods: list[str]
    rationale: list[str]
    assumptions_to_check: list[str] = field(default_factory=list)
    sensitivity_analyses: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReviewFinding:
    code: str
    severity: str
    message: str
    remediation: str | None = None


@dataclass(slots=True)
class ReviewReport:
    status: ReviewStatus
    findings: list[ReviewFinding]
    checks_run: list[str]
    evidence_strength: EvidenceStrength

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["evidence_strength"] = self.evidence_strength.value
        return data


@dataclass(slots=True)
class DecisionOption:
    name: str
    expected_benefit: str
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    monitoring_metrics: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DecisionRecommendation:
    finding: str
    options: list[DecisionOption]
    recommended_option: str | None
    rationale: str
    evidence_strength: EvidenceStrength
    review_status: ReviewStatus
    next_review_trigger: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_strength"] = self.evidence_strength.value
        data["review_status"] = self.review_status.value
        return data
