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


def _nested_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _has_uncertainty(results: Mapping[str, Any]) -> bool:
    direct = {
        "confidence_interval",
        "confidence_intervals",
        "ci",
        "standard_error",
        "standard_errors",
    }
    if any(key in results for key in direct):
        return True
    estimates = _nested_mapping(results.get("estimates"))
    if any(key in estimates for key in direct):
        return True

    for section_name in ("coefficients", "hazard_ratios", "fixed_effects", "odds_ratios"):
        section = _nested_mapping(estimates.get(section_name))
        for values in section.values():
            if isinstance(values, Mapping) and any(
                key in values for key in ("standard_error", "ci_low", "ci_high")
            ):
                return True
    return False


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
        findings.append(
            ReviewFinding(
                "contract_invalid",
                "blocker",
                error,
                "Correct the analysis contract before interpretation.",
            )
        )

    if quality is not None and quality.gate == "NO_GO":
        findings.append(
            ReviewFinding(
                "data_quality_no_go",
                "blocker",
                "Data quality gate is NO_GO.",
                "Resolve blocking data defects and rerun quality checks.",
            )
        )
    elif quality is not None and quality.gate == "CONDITIONAL_GO":
        findings.append(
            ReviewFinding(
                "data_quality_warning",
                "warning",
                "Data quality gate is CONDITIONAL_GO.",
                "Carry limitations into interpretation and address material issues.",
            )
        )

    n = results.get("n") or results.get("sample_size")
    if n is not None and int(n) < 20:
        findings.append(
            ReviewFinding(
                "small_sample",
                "warning",
                f"Analysis uses a small sample (n={n}).",
                "Emphasize uncertainty; avoid unstable subgroup/model claims.",
            )
        )

    if contract.analysis_type in {AnalysisType.INFERENTIAL, AnalysisType.CAUSAL}:
        if not _has_uncertainty(results):
            findings.append(
                ReviewFinding(
                    "uncertainty_missing",
                    "warning",
                    "No confidence interval or standard error was supplied.",
                    "Report estimate uncertainty, not only point estimates or p-values.",
                )
            )

    if contract.analysis_type == AnalysisType.PREDICTIVE:
        if not any(
            key in results
            for key in ("holdout_metrics", "test_metrics", "cross_validation")
        ):
            findings.append(
                ReviewFinding(
                    "out_of_sample_missing",
                    "blocker",
                    "Predictive results lack documented out-of-sample evaluation.",
                    "Evaluate on a holdout set or cross-validation scheme that prevents leakage.",
                )
            )
        if results.get("target_leakage_checked") is not True:
            findings.append(
                ReviewFinding(
                    "leakage_not_verified",
                    "warning",
                    "Target leakage check is not documented.",
                    "Document leakage checks before trusting performance.",
                )
            )

    metadata = _nested_mapping(results.get("metadata"))
    diagnostics = _nested_mapping(results.get("diagnostics"))
    assumptions = _nested_mapping(results.get("assumptions_checked"))

    if contract.analysis_type == AnalysisType.CAUSAL:
        identification = results.get("identification_assumptions") or metadata.get(
            "identification_assumptions"
        )
        if not identification:
            findings.append(
                ReviewFinding(
                    "causal_identification_missing",
                    "blocker",
                    "Causal identification assumptions are not documented.",
                    "State exchangeability, positivity, consistency, and temporal assumptions.",
                )
            )
        positivity_fraction = diagnostics.get("positivity_violation_fraction")
        if positivity_fraction is not None and float(positivity_fraction) > 0.05:
            findings.append(
                ReviewFinding(
                    "positivity_concern",
                    "warning",
                    "Propensity diagnostics show material positivity violations.",
                    "Revisit the target population, trim rule, and overlap assumptions.",
                )
            )
        max_smd = diagnostics.get("max_absolute_smd_after")
        if max_smd is not None and float(max_smd) > 0.10:
            findings.append(
                ReviewFinding(
                    "residual_imbalance",
                    "warning",
                    "Post-weighting covariate imbalance exceeds |SMD| 0.10.",
                    "Re-specify the propensity model or use an alternative estimator.",
                )
            )
        if not results.get("sensitivity_analysis"):
            findings.append(
                ReviewFinding(
                    "causal_sensitivity_missing",
                    "warning",
                    "No unmeasured-confounding sensitivity analysis is documented.",
                    "Add a sensitivity analysis before strong causal interpretation.",
                )
            )

    if contract.analysis_type == AnalysisType.FORECASTING:
        if assumptions.get("chronological_validation") is not True:
            findings.append(
                ReviewFinding(
                    "forecast_validation_missing",
                    "blocker",
                    "Forecast results lack chronological validation.",
                    "Use a time-ordered holdout or rolling-origin backtest.",
                )
            )
        if assumptions.get("baseline_comparison") is not True:
            findings.append(
                ReviewFinding(
                    "forecast_baseline_missing",
                    "warning",
                    "Forecast results are not compared with a simple baseline.",
                    "Compare against a naive or seasonal-naive forecast.",
                )
            )

    if contract.analysis_type == AnalysisType.SURVIVAL:
        if assumptions.get("binary_event_verified") is not True:
            findings.append(
                ReviewFinding(
                    "survival_event_invalid",
                    "blocker",
                    "Survival event coding was not verified.",
                    "Use an explicit 0/1 event indicator.",
                )
            )
        if results.get("method") == "cox_proportional_hazards":
            if assumptions.get("proportional_hazards_checked") is not True:
                findings.append(
                    ReviewFinding(
                        "ph_assumption_unverified",
                        "warning",
                        "The proportional-hazards assumption has not been verified.",
                        "Run proportional-hazards diagnostics before relying on Cox estimates.",
                    )
                )
            elif assumptions.get("proportional_hazards_screen_passed") is False:
                findings.append(
                    ReviewFinding(
                        "ph_assumption_concern",
                        "warning",
                        "Schoenfeld-residual screening suggests non-proportional hazards.",
                        "Consider time-varying effects, stratification, or an alternative model.",
                    )
                )

    if contract.analysis_type == AnalysisType.LONGITUDINAL:
        if assumptions.get("clustering_modeled") is not True:
            findings.append(
                ReviewFinding(
                    "clustering_not_modeled",
                    "blocker",
                    "Repeated/nested observations are not modeled as clustered.",
                    "Use mixed-effects or GEE methods with an explicit grouping variable.",
                )
            )
        if diagnostics.get("converged") is False:
            findings.append(
                ReviewFinding(
                    "longitudinal_nonconvergence",
                    "blocker",
                    "The mixed-effects model did not converge.",
                    "Re-specify the random-effects structure or optimizer.",
                )
            )

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
