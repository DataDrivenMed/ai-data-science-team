from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class ReproducibilityPackage:
    """Write a compact, auditable analysis bundle to disk."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def _serialize(value: Any) -> Any:
        if hasattr(value, "to_dict"):
            return value.to_dict()
        if is_dataclass(value):
            return asdict(value)
        return value

    def write(
        self,
        *,
        contract: Any,
        quality_report: Any | None = None,
        method_recommendation: Any | None = None,
        review_report: Any | None = None,
        evidence_ledger: Any | None = None,
        results: dict[str, Any] | None = None,
        analysis_code: str | None = None,
        executive_summary: str | None = None,
    ) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        payloads = {
            "analysis_contract.json": contract,
            "data_quality.json": quality_report,
            "method_recommendation.json": method_recommendation,
            "review_report.json": review_report,
            "results.json": results,
        }

        for name, value in payloads.items():
            if value is None:
                continue
            (self.root / name).write_text(
                json.dumps(
                    self._serialize(value),
                    indent=2,
                    sort_keys=True,
                    default=str,
                ) + "\n",
                encoding="utf-8",
            )

        if evidence_ledger is not None:
            content = (
                evidence_ledger.to_json(indent=2)
                if hasattr(evidence_ledger, "to_json")
                else json.dumps(
                    self._serialize(evidence_ledger),
                    indent=2,
                    default=str,
                )
            )
            (self.root / "evidence_ledger.json").write_text(
                content + "\n",
                encoding="utf-8",
            )

        if analysis_code:
            (self.root / "analysis.py").write_text(
                analysis_code.rstrip() + "\n",
                encoding="utf-8",
            )
        if executive_summary:
            (self.root / "executive_summary.md").write_text(
                executive_summary.rstrip() + "\n",
                encoding="utf-8",
            )

        environment = {
            "python": sys.version,
            "platform": platform.platform(),
        }
        (self.root / "environment.json").write_text(
            json.dumps(environment, indent=2) + "\n",
            encoding="utf-8",
        )
        return self.root
