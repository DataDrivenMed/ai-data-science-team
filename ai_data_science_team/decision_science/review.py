from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import (
    AnalysisContract,
    AnalysisType,
    DataQualityReport,
    EvidenceStrength,
    ReviewFinding,
    ReviewReport,
    ReviewStatus,
)


def review_analysis(
    contract: AnalysisContract,
    results: Mapping[str, Any],
    *,
    quality: DataQualityReport | None = None,
) -> ReviewReport:
    """Independent rule-based review that fails closed on major analytical omissions."""
    findings: list[ReviewFinding] = []
    checks = [
        "contract validity",
        "data-quality gate",
        "sample size",
        "uncertainty",
        "method-specific safeguards",
    ]

    for error in contract.validate():
        findings.append(ReviewFinding(
            "contract_invalid",
            "blocker",
            error,
            "Correct the analysis contract before interpretation.",
        ))

    if quality is not None and quality.gate == "NO_GO":
        findings.append(ReviewFinding(
            "data_quality_no_go",
            "blocker",
            "Data quality gate is NO_GO.",
            "Resolve blocking data defects and rerun quality checks.",
        ))
    elif quality is not None and quality.gate == "CONDITIONAL_GO":
        findings.append(ReviewFinding(
            "data_quality_warning",
            "warning",
            "Data quality gate is CONDITIONAL_GO.",
            "Carry limitations into interpretation and address material issues.",
        ))

    n = results.get("n") or results.get("sample_size")
    if n is not None and int(n) < 20:
        findings.append(ReviewFinding(
            "small_sample",
            "warning",
            f"Analysis uses a small sample (n={n}).",
            "Emphasize uncertainty; avoid unstable subgroup/model claims.",
        ))

    if contract.analysis_type in {AnalysisType.INFERENTIAL, AnalysisType.CAUSAL}:
        has_uncertainty = any(
            k in results
            for k in (
                "confidence_interval",
                "confidence_intervals",
                "ci",
                "standard_error",
                "standard_errors",
            )
        )
        if not has_uncertainty:
            findings.append(ReviewFinding(
                "uncertainty_missing",
                "warning",
                "No confidence interval or standard error was supplied.",
                "Report estimate uncertainty, not only point estimates or p-values.",
            ))

    if contract.analysis_type == AnalysisType.PREDICTIVE:
        if not any(k in results for k in ("holdout_metrics", "test_metrics", "cross_validation")):
            findings.append(ReviewFinding(
                "out_of_sample_missing",
                "blocker",
                "Predictive results lack documented out-of-sample evaluation.",
                "Evaluate on a holdout set or cross-validation scheme that prevents leakage.",
            ))
        if results.get("target_leakage_checked") is not True:
            findings.append(ReviewFinding(
                "leakage_not_verified",
                "warning",
                "Target leakage check is not documented.",
                "Document leakage checks before trusting performance.",
            ))

    if contract.analysis_type == AnalysisType.CAUSAL:
        if not results.get("identification_assumptions"):
            findings.append(ReviewFinding(
                "causal_identification_missing",
                "blocker",
                "Causal identification assumptions are not documented.",
                "State exchangeability, positivity, consistency, and temporal assumptions.",
            ))
        if not results.get("sensitivity_analysis"):
            findings.append(ReviewFinding(
                "causal_sensitivity_missing",
                "warning",
                "No causal sensitivity analysis is documented.",
                "Test robustness to alternative specifications or unmeasured confounding.",
            ))

    blocker = any(f.severity == "blocker" for f in findings)
    warning = any(f.severity == "warning" for f in findings)
    status = (
        ReviewStatus.FAIL
        if blocker
        else ReviewStatus.PASS_WITH_WARNINGS
        if warning
        else ReviewStatus.PASS
    )

    if status == ReviewStatus.FAIL:
        strength = EvidenceStrength.INSUFFICIENT
    elif warning:
        strength = EvidenceStrength.LOW
    elif quality is not None and quality.overall_score < 90:
        strength = EvidenceStrength.MODERATE
    else:
        strength = EvidenceStrength.HIGH

    return ReviewReport(
        status=status,
        findings=findings,
        checks_run=checks,
        evidence_strength=strength,
    )
