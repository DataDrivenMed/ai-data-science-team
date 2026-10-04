from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

import pandas as pd


DEFAULT_SENSITIVE_PATTERNS = {
    "direct_identifier": r"(^|_)(name|first_name|last_name|full_name|ssn|social_security|mrn|medical_record|email|phone|address|street)($|_)",
    "credential": r"(^|_)(password|secret|token|api_key|access_key)($|_)",
}


@dataclass(slots=True)
class GovernanceFinding:
    code: str
    severity: str
    message: str
    columns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GovernanceReport:
    status: str
    findings: list[GovernanceFinding]
    small_cell_threshold: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_governance(
    data: pd.DataFrame,
    *,
    small_cell_threshold: int = 5,
    sensitive_patterns: dict[str, str] | None = None,
) -> GovernanceReport:
    patterns = sensitive_patterns or DEFAULT_SENSITIVE_PATTERNS
    findings: list[GovernanceFinding] = []
    cols = [str(c) for c in data.columns]

    for code, pattern in patterns.items():
        matched = [
            c for c in cols if re.search(pattern, c, flags=re.IGNORECASE)
        ]
        if matched:
            findings.append(GovernanceFinding(
                code=code,
                severity="blocker" if code == "credential" else "warning",
                message="Potential sensitive columns detected by name. Review before external transmission or publication.",
                columns=matched,
            ))

    categorical = data.select_dtypes(
        include=["object", "category", "string", "bool"]
    )
    small_cell_cols: list[str] = []
    for col in categorical.columns:
        counts = categorical[col].value_counts(dropna=True)
        if not counts.empty and (counts < small_cell_threshold).any():
            small_cell_cols.append(str(col))

    if small_cell_cols:
        findings.append(GovernanceFinding(
            code="small_cells",
            severity="warning",
            message=(
                f"Categorical variables contain cells smaller than "
                f"{small_cell_threshold}; suppress or aggregate before disclosure "
                "when policy requires it."
            ),
            columns=small_cell_cols,
        ))

    status = (
        "BLOCK"
        if any(f.severity == "blocker" for f in findings)
        else "REVIEW"
        if findings
        else "PASS"
    )
    return GovernanceReport(
        status=status,
        findings=findings,
        small_cell_threshold=small_cell_threshold,
    )
