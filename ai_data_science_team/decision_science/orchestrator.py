from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from .contracts import AnalysisContract, MethodRecommendation, ReviewReport
from .data_quality import assess_data_quality
from .governance import GovernanceReport, check_governance
from .methods import recommend_methods
from .provenance import EvidenceLedger, fingerprint_dataframe
from .red_team import RedTeamReport, red_team_analysis
from .review import review_analysis


@dataclass(slots=True)
class DecisionScienceRun:
    contract: AnalysisContract
    quality: Any
    governance: GovernanceReport
    methods: MethodRecommendation
    review: ReviewReport | None
    red_team: RedTeamReport | None
    evidence: EvidenceLedger

    @property
    def ready_for_analysis(self) -> bool:
        return (
            self.quality.gate != "NO_GO"
            and self.governance.status != "BLOCK"
            and not self.contract.validate()
        )


class DecisionScienceOrchestrator:
    """Deterministic control plane around the existing data-science agents.

    The orchestrator does not replace wrangling, visualization, SQL, or ML
    agents. It governs when they should run and what evidence must exist before
    results are trusted.
    """

    def __init__(self, *, small_cell_threshold: int = 5):
        self.small_cell_threshold = small_cell_threshold

    def prepare(
        self,
        contract: AnalysisContract,
        data: pd.DataFrame,
        *,
        required_columns: list[str] | None = None,
        documented_columns: list[str] | None = None,
        id_columns: list[str] | None = None,
        temporal_columns: list[str] | None = None,
    ) -> DecisionScienceRun:
        quality = assess_data_quality(
            data,
            required_columns=required_columns,
            documented_columns=documented_columns,
            id_columns=id_columns,
            temporal_columns=temporal_columns,
        )
        governance = check_governance(
            data,
            small_cell_threshold=self.small_cell_threshold,
        )
        methods = recommend_methods(contract)
        ledger = EvidenceLedger()
        ledger.add(
            kind="dataset",
            claim=(
                f"Analysis input contains {len(data)} rows and "
                f"{len(data.columns)} columns."
            ),
            source="in-memory pandas DataFrame",
            dataset_fingerprint=fingerprint_dataframe(data),
            validation_status=quality.gate,
        )

        return DecisionScienceRun(
            contract=contract,
            quality=quality,
            governance=governance,
            methods=methods,
            review=None,
            red_team=None,
            evidence=ledger,
        )

    def finalize(
        self,
        run: DecisionScienceRun,
        results: Mapping[str, Any],
        *,
        source: str = "analysis results",
        code_reference: str | None = None,
    ) -> DecisionScienceRun:
        run.review = review_analysis(
            run.contract,
            results,
            quality=run.quality,
        )
        run.red_team = red_team_analysis(run.contract, results)
        run.evidence.add(
            kind="result",
            claim="Primary analysis results recorded for independent review.",
            source=source,
            code_reference=code_reference,
            validation_status=run.review.status.value,
            metadata={
                "evidence_strength": run.review.evidence_strength.value
            },
        )
        return run
