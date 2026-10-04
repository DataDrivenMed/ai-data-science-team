from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DomainPack:
    name: str
    required_definitions: list[str] = field(default_factory=list)
    default_approval_gates: list[str] = field(default_factory=list)
    default_governance_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


ACADEMIC_MEDICINE = DomainPack(
    name="academic_medicine",
    required_definitions=[
        "learner/cohort identifier",
        "outcome definition",
        "assessment timing",
        "inclusion/exclusion rules",
        "site/program definitions when applicable",
    ],
    default_approval_gates=[
        "small-cell reporting",
        "high-stakes learner prediction",
        "causal interpretation",
        "external transmission of learner-level data",
    ],
    default_governance_rules=[
        "review direct identifiers",
        "review small subgroup counts",
        "preserve cohort and assessment timing",
        "separate descriptive, predictive, and causal claims",
    ],
)

CLINICAL_RESEARCH = DomainPack(
    name="clinical_research",
    required_definitions=[
        "population",
        "exposure/intervention",
        "outcome",
        "time zero",
        "follow-up",
        "censoring",
    ],
    default_approval_gates=[
        "PHI use outside approved environment",
        "causal interpretation",
        "patient-level disclosure",
    ],
    default_governance_rules=[
        "review direct identifiers",
        "define time zero before modeling",
        "document censoring and missingness",
    ],
)
