from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .contracts import AnalysisContract, AnalysisType


@dataclass(slots=True)
class AlternativeExplanation:
    hypothesis: str
    why_plausible: str
    falsification_test: str


@dataclass(slots=True)
class RedTeamReport:
    alternative_explanations: list[AlternativeExplanation] = field(default_factory=list)
    interpretation_risks: list[str] = field(default_factory=list)
    required_stress_tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def red_team_analysis(
    contract: AnalysisContract,
    results: Mapping[str, Any],
) -> RedTeamReport:
    alternatives: list[AlternativeExplanation] = []
    risks = [
        "measurement or definition drift could explain part of the observed pattern",
        "missingness or selection could change the estimated relationship",
        "subgroup aggregation could conceal heterogeneous effects",
    ]
    tests = [
        "repeat key estimates by cohort/time period",
        "inspect missingness by outcome and exposure",
        "run subgroup/interaction checks when sample size permits",
    ]

    if contract.predictors:
        alternatives.append(AlternativeExplanation(
            hypothesis="Observed predictor effects are proxy relationships rather than direct mechanisms.",
            why_plausible="Correlated predictors can inherit signal from prior preparation, access, cohort composition, or other latent factors.",
            falsification_test="Refit with prespecified confounders/proxies, inspect coefficient stability, and test plausible interactions.",
        ))

    if contract.analysis_type == AnalysisType.CAUSAL:
        alternatives.append(AlternativeExplanation(
            hypothesis="Residual confounding explains the apparent treatment/exposure effect.",
            why_plausible="Observational exposure assignment is rarely random.",
            falsification_test="Use sensitivity analysis, negative controls where available, and alternative adjustment sets derived from a DAG.",
        ))

    if contract.analysis_type == AnalysisType.PREDICTIVE:
        alternatives.append(AlternativeExplanation(
            hypothesis="Performance is inflated by leakage or temporal mismatch.",
            why_plausible="Random splits and post-outcome features can make operational performance look unrealistically strong.",
            falsification_test="Use temporally valid holdout data and remove features unavailable at prediction time.",
        ))

    if results.get("p_value") is not None:
        risks.append("A statistically significant p-value does not establish practical importance or causality.")
        tests.append("report effect size and confidence interval alongside p-values")

    return RedTeamReport(
        alternative_explanations=alternatives,
        interpretation_risks=risks,
        required_stress_tests=tests,
    )
