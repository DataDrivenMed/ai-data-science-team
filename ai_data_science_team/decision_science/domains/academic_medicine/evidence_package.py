from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from ...provenance import EvidenceLedger
from .leadership import LeadershipActionRegistry


class AccreditationEvidencePackage:
    """Build an audit-ready accreditation/CQI packet for one metric."""

    @staticmethod
    def build(
        *,
        metric_id: str,
        snapshot: pd.DataFrame,
        trends: pd.DataFrame | None,
        ledger: EvidenceLedger,
        actions: LeadershipActionRegistry | None = None,
    ) -> dict[str, Any]:
        current = snapshot.loc[snapshot["metric_id"] == metric_id]
        if current.empty:
            raise KeyError(f"Metric {metric_id!r} is not present in the snapshot.")
        row = current.iloc[-1]

        trend_rows = []
        if trends is not None and not trends.empty:
            trend_rows = (
                trends.loc[trends["metric_id"] == metric_id]
                .sort_values("period")
                .to_dict(orient="records")
            )

        evidence = [
            asdict(record)
            for record in ledger.records
            if record.metadata.get("metric_id") == metric_id
        ]

        action_rows: list[dict[str, Any]] = []
        decision_rows: list[dict[str, Any]] = []
        review_rows: list[dict[str, Any]] = []
        if actions is not None:
            action_rows = [
                item.to_dict()
                for item in actions.actions
                if item.metric_id == metric_id
            ]
            decision_rows = [
                item.to_dict()
                for item in actions.decisions
                if item.metric_id == metric_id
            ]
            action_ids = {item["action_id"] for item in action_rows}
            review_rows = [
                item.to_dict()
                for item in actions.reviews
                if item.action_id in action_ids
            ]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metric": row.to_dict(),
            "trend": trend_rows,
            "evidence_lineage": evidence,
            "leadership_actions": action_rows,
            "decision_log": decision_rows,
            "outcome_reviews": review_rows,
        }

    @classmethod
    def to_markdown(cls, package: dict[str, Any]) -> str:
        metric = package["metric"]
        lines = [
            f"# CQI / Accreditation Evidence Packet: {metric['name']}",
            "",
            f"**Metric ID:** {metric['metric_id']}",
            f"**Domain:** {metric['domain']}",
            f"**Status:** {metric['status']}",
            f"**Current value:** {metric['value']}",
            f"**Target:** {metric.get('target')}",
            f"**Owner:** {metric['owner']}",
            f"**Source:** {metric['source']}",
            f"**Standard / element:** {metric.get('standard_or_element') or 'Not specified'}",
            f"**Dataset fingerprint:** {metric.get('dataset_fingerprint') or 'Unavailable'}",
            "",
            "## Metric definition and calculation",
            f"- Calculator: {metric.get('calculation')}",
            f"- Numerator: {metric.get('numerator')}",
            f"- Denominator: {metric.get('denominator')}",
            f"- Warning threshold: {metric.get('warning_threshold')}",
            f"- Critical threshold: {metric.get('critical_threshold')}",
            "",
        ]

        trend = package.get("trend", [])
        if trend:
            lines.append("## Longitudinal performance")
            for row in trend:
                lines.append(
                    f"- {row.get('period')}: {row.get('value')} ({row.get('status')})"
                )
            lines.append("")

        lines.append("## Evidence lineage")
        evidence = package.get("evidence_lineage", [])
        if evidence:
            for record in evidence:
                lines.append(
                    f"- {record['record_id']}: {record['claim']} | "
                    f"{record['source']} | {record.get('created_at')}"
                )
        else:
            lines.append("- No evidence records available.")
        lines.append("")

        lines.append("## Leadership actions")
        action_rows = package.get("leadership_actions", [])
        if action_rows:
            for action in action_rows:
                lines.append(
                    f"- {action['action_id']} | {action['status']} | "
                    f"{action['owner']} | {action['action']}"
                )
        else:
            lines.append("- No actions recorded.")
        lines.append("")

        lines.append("## Decision log")
        decision_rows = package.get("decision_log", [])
        if decision_rows:
            for decision in decision_rows:
                lines.append(
                    f"- {decision['decided_at']} | {decision['decision_maker']} | "
                    f"{decision['decision']}"
                )
        else:
            lines.append("- No leadership decisions recorded.")
        lines.append("")

        lines.append("## Outcome verification")
        review_rows = package.get("outcome_reviews", [])
        if review_rows:
            for review in review_rows:
                lines.append(
                    f"- {review['reviewed_at']} | status={review['metric_status']} | "
                    f"success_met={review['success_met']} | reviewer={review['reviewer']}"
                )
        else:
            lines.append("- No post-action outcome review recorded.")
        return "\n".join(lines)

    @staticmethod
    def to_json(package: dict[str, Any], *, indent: int = 2) -> str:
        return json.dumps(package, indent=indent, sort_keys=True, default=str)
