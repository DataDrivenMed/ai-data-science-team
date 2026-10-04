from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from .contracts import DataQualityReport, QualityIssue


def _clip_score(value: float) -> float:
    return round(float(max(0.0, min(100.0, value))), 1)


def assess_data_quality(
    data: pd.DataFrame,
    *,
    required_columns: Iterable[str] | None = None,
    documented_columns: Iterable[str] | None = None,
    id_columns: Iterable[str] | None = None,
    temporal_columns: Iterable[str] | None = None,
    min_rows: int = 20,
) -> DataQualityReport:
    """Run a deterministic pre-analysis quality gate on a pandas DataFrame."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    required = list(required_columns or [])
    documented = set(documented_columns or [])
    ids = list(id_columns or [])
    temporal = list(temporal_columns or [])
    issues: list[QualityIssue] = []

    rows, cols = data.shape
    missing_cells = int(data.isna().sum().sum())
    total_cells = max(rows * cols, 1)
    completeness = 100.0 * (1.0 - missing_cells / total_cells)

    missing_required = [c for c in required if c not in data.columns]
    if missing_required:
        issues.append(QualityIssue(
            code="missing_required_columns",
            severity="blocker",
            message="Required columns are absent from the dataset.",
            columns=missing_required,
        ))

    duplicate_rows = int(data.duplicated().sum()) if rows else 0
    if duplicate_rows:
        issues.append(QualityIssue(
            code="duplicate_rows",
            severity="warning",
            message=f"Detected {duplicate_rows} exact duplicate rows.",
            details={"duplicate_rows": duplicate_rows},
        ))

    duplicate_ids: dict[str, int] = {}
    for col in ids:
        if col in data.columns:
            count = int(data[col].dropna().duplicated().sum())
            if count:
                duplicate_ids[col] = count
    if duplicate_ids:
        issues.append(QualityIssue(
            code="duplicate_identifiers",
            severity="blocker",
            message="Identifier columns contain duplicate non-null values.",
            columns=list(duplicate_ids),
            details=duplicate_ids,
        ))

    constant_columns = [c for c in data.columns if data[c].nunique(dropna=False) <= 1]
    if constant_columns:
        issues.append(QualityIssue(
            code="constant_columns",
            severity="info",
            message="Columns with no analytical variation were detected.",
            columns=constant_columns,
        ))

    high_missing = [c for c in data.columns if float(data[c].isna().mean()) >= 0.30]
    if high_missing:
        issues.append(QualityIssue(
            code="high_missingness",
            severity="warning",
            message="One or more columns have at least 30% missing values.",
            columns=high_missing,
            details={c: round(float(data[c].isna().mean()), 4) for c in high_missing},
        ))

    numeric_cols = list(data.select_dtypes(include=[np.number]).columns)
    infinite_counts: dict[str, int] = {}
    for col in numeric_cols:
        values = pd.to_numeric(data[col], errors="coerce")
        count = int(np.isinf(values.to_numpy(dtype=float, na_value=np.nan)).sum())
        if count:
            infinite_counts[col] = count
    if infinite_counts:
        issues.append(QualityIssue(
            code="infinite_values",
            severity="blocker",
            message="Numeric columns contain infinite values.",
            columns=list(infinite_counts),
            details=infinite_counts,
        ))

    temporal_failures: dict[str, int] = {}
    for col in temporal:
        if col in data.columns:
            parsed = pd.to_datetime(data[col], errors="coerce", utc=True)
            failed = int(parsed.isna().sum() - data[col].isna().sum())
            if failed > 0:
                temporal_failures[col] = failed
    if temporal_failures:
        issues.append(QualityIssue(
            code="invalid_temporal_values",
            severity="warning",
            message="Temporal columns contain values that could not be parsed.",
            columns=list(temporal_failures),
            details=temporal_failures,
        ))

    if rows < min_rows:
        issues.append(QualityIssue(
            code="small_dataset",
            severity="warning",
            message=f"Dataset contains only {rows} rows; inference and modeling may be unstable.",
            details={"minimum_reference_rows": min_rows},
        ))

    integrity_penalty = min(100.0, duplicate_rows / max(rows, 1) * 40.0)
    integrity_penalty += 25.0 * bool(duplicate_ids)
    integrity_penalty += 25.0 * bool(infinite_counts)
    integrity_penalty += 25.0 * bool(missing_required)
    integrity = _clip_score(100.0 - integrity_penalty)

    documentation_score: float | None = None
    if documented:
        documentation_score = _clip_score(
            100.0 * len(documented.intersection(data.columns)) / max(cols, 1)
        )

    temporal_score: float | None = None
    if temporal:
        total_temporal = sum(
            max(int(data[c].notna().sum()), 1) for c in temporal if c in data.columns
        )
        failed_temporal = sum(temporal_failures.values())
        temporal_score = _clip_score(
            100.0 * (1.0 - failed_temporal / max(total_temporal, 1))
        )

    scored = [completeness, integrity]
    if documentation_score is not None:
        scored.append(documentation_score)
    if temporal_score is not None:
        scored.append(temporal_score)
    overall = _clip_score(sum(scored) / len(scored))

    blocker = any(issue.severity == "blocker" for issue in issues)
    if blocker or overall < 60:
        gate = "NO_GO"
    elif overall < 85 or any(issue.severity == "warning" for issue in issues):
        gate = "CONDITIONAL_GO"
    else:
        gate = "GO"

    metrics: dict[str, Any] = {
        "missing_cells": missing_cells,
        "missing_cell_fraction": round(missing_cells / total_cells, 6),
        "duplicate_rows": duplicate_rows,
        "constant_column_count": len(constant_columns),
        "high_missingness_column_count": len(high_missing),
    }

    return DataQualityReport(
        row_count=rows,
        column_count=cols,
        completeness_score=_clip_score(completeness),
        integrity_score=integrity,
        documentation_score=documentation_score,
        temporal_validity_score=temporal_score,
        representativeness_score=None,
        overall_score=overall,
        gate=gate,
        issues=issues,
        metrics=metrics,
    )
