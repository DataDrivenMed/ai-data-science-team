from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import pandas as pd


class ActionStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    VERIFIED = "VERIFIED"


@dataclass(slots=True)
class LeadershipAction:
    action_id: str
    metric_id: str
    metric_name: str
    domain: str
    trigger_status: str
    trigger_value: float | None
    owner: str
    action: str
    rationale: str
    success_criterion: str
    due_date: str | None = None
    review_date: str | None = None
    executive_sponsor: str | None = None
    target_value: float | None = None
    status: ActionStatus = ActionStatus.OPEN
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_record_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


@dataclass(slots=True)
class DecisionRecord:
    decision_id: str
    metric_id: str
    action_id: str | None
    decision: str
    rationale: str
    decision_maker: str
    options_considered: list[str] = field(default_factory=list)
    evidence_record_ids: list[str] = field(default_factory=list)
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OutcomeReview:
    review_id: str
    action_id: str
    metric_id: str
    measured_value: float | None
    metric_status: str
    success_met: bool
    reviewer: str
    notes: str = ""
    evidence_record_ids: list[str] = field(default_factory=list)
    reviewed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LeadershipActionRegistry:
    """Closed-loop CQI action, decision, and remeasurement registry."""

    def __init__(self) -> None:
        self._actions: dict[str, LeadershipAction] = {}
        self._decisions: list[DecisionRecord] = []
        self._reviews: list[OutcomeReview] = []

    @staticmethod
    def _id(prefix: str, *parts: Any) -> str:
        raw = "|".join(str(part) for part in parts).encode("utf-8")
        return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:12]}"

    def create_action(
        self,
        *,
        metric_id: str,
        metric_name: str,
        domain: str,
        trigger_status: str,
        trigger_value: float | None,
        owner: str,
        action: str,
        rationale: str,
        success_criterion: str,
        due_date: str | None = None,
        review_date: str | None = None,
        executive_sponsor: str | None = None,
        target_value: float | None = None,
        evidence_record_ids: list[str] | None = None,
    ) -> LeadershipAction:
        action_id = self._id(
            "ACT",
            metric_id,
            action,
            datetime.now(timezone.utc).isoformat(),
        )
        item = LeadershipAction(
            action_id=action_id,
            metric_id=metric_id,
            metric_name=metric_name,
            domain=domain,
            trigger_status=trigger_status,
            trigger_value=trigger_value,
            owner=owner,
            action=action,
            rationale=rationale,
            success_criterion=success_criterion,
            due_date=due_date,
            review_date=review_date,
            executive_sponsor=executive_sponsor,
            target_value=target_value,
            evidence_record_ids=list(evidence_record_ids or []),
        )
        self._actions[action_id] = item
        return item

    def create_from_exceptions(
        self,
        exceptions: pd.DataFrame,
        *,
        default_review_date: str | None = None,
    ) -> list[LeadershipAction]:
        created: list[LeadershipAction] = []
        existing_metric_ids = {
            action.metric_id
            for action in self._actions.values()
            if action.status not in {ActionStatus.COMPLETE, ActionStatus.VERIFIED}
        }
        for _, row in exceptions.iterrows():
            metric_id = str(row["metric_id"])
            if metric_id in existing_metric_ids:
                continue
            target = row.get("target")
            criterion = (
                f"Return {row['name']} to configured target"
                if pd.notna(target)
                else f"Move {row['name']} out of {row['status']} status"
            )
            created.append(
                self.create_action(
                    metric_id=metric_id,
                    metric_name=str(row["name"]),
                    domain=str(row["domain"]),
                    trigger_status=str(row["status"]),
                    trigger_value=(
                        None if pd.isna(row.get("value")) else float(row["value"])
                    ),
                    owner=str(row.get("owner") or "Unassigned"),
                    action="Define and execute a corrective action plan.",
                    rationale=(
                        f"Metric entered {row['status']} status under the configured CQI threshold."
                    ),
                    success_criterion=criterion,
                    review_date=default_review_date,
                    target_value=(
                        None if pd.isna(target) else float(target)
                    ),
                    evidence_record_ids=(
                        [str(row["evidence_record_id"])]
                        if pd.notna(row.get("evidence_record_id"))
                        else []
                    ),
                )
            )
        return created

    def update_action(
        self,
        action_id: str,
        *,
        status: ActionStatus | str | None = None,
        owner: str | None = None,
        action: str | None = None,
        rationale: str | None = None,
        success_criterion: str | None = None,
        due_date: str | None = None,
        review_date: str | None = None,
        executive_sponsor: str | None = None,
    ) -> LeadershipAction:
        item = self._actions[action_id]
        if status is not None:
            item.status = ActionStatus(status)
        for name, value in {
            "owner": owner,
            "action": action,
            "rationale": rationale,
            "success_criterion": success_criterion,
            "due_date": due_date,
            "review_date": review_date,
            "executive_sponsor": executive_sponsor,
        }.items():
            if value is not None:
                setattr(item, name, value)
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return item

    def record_decision(
        self,
        *,
        metric_id: str,
        decision: str,
        rationale: str,
        decision_maker: str,
        action_id: str | None = None,
        options_considered: list[str] | None = None,
        evidence_record_ids: list[str] | None = None,
    ) -> DecisionRecord:
        decision_id = self._id(
            "DEC",
            metric_id,
            decision,
            datetime.now(timezone.utc).isoformat(),
        )
        record = DecisionRecord(
            decision_id=decision_id,
            metric_id=metric_id,
            action_id=action_id,
            decision=decision,
            rationale=rationale,
            decision_maker=decision_maker,
            options_considered=list(options_considered or []),
            evidence_record_ids=list(evidence_record_ids or []),
        )
        self._decisions.append(record)
        return record

    def review_outcome(
        self,
        *,
        action_id: str,
        measured_value: float | None,
        metric_status: str,
        reviewer: str,
        notes: str = "",
        evidence_record_ids: list[str] | None = None,
    ) -> OutcomeReview:
        action = self._actions[action_id]
        success = self._success_met(
            action=action,
            measured_value=measured_value,
            metric_status=metric_status,
        )
        review_id = self._id(
            "REV",
            action_id,
            metric_status,
            datetime.now(timezone.utc).isoformat(),
        )
        review = OutcomeReview(
            review_id=review_id,
            action_id=action_id,
            metric_id=action.metric_id,
            measured_value=measured_value,
            metric_status=metric_status,
            success_met=success,
            reviewer=reviewer,
            notes=notes,
            evidence_record_ids=list(evidence_record_ids or []),
        )
        self._reviews.append(review)
        if success:
            action.status = ActionStatus.VERIFIED
        elif action.status == ActionStatus.COMPLETE:
            action.status = ActionStatus.IN_PROGRESS
        action.updated_at = datetime.now(timezone.utc).isoformat()
        return review

    @staticmethod
    def _success_met(
        *,
        action: LeadershipAction,
        measured_value: float | None,
        metric_status: str,
    ) -> bool:
        if metric_status == "ON_TARGET":
            return True
        if action.target_value is None or measured_value is None:
            return metric_status not in {"WARNING", "CRITICAL", "NO_DATA"}
        if action.trigger_value is None:
            return metric_status == "ON_TARGET"
        if action.trigger_value < action.target_value:
            return measured_value >= action.target_value
        if action.trigger_value > action.target_value:
            return measured_value <= action.target_value
        return metric_status == "ON_TARGET"

    @property
    def actions(self) -> tuple[LeadershipAction, ...]:
        return tuple(self._actions.values())

    @property
    def decisions(self) -> tuple[DecisionRecord, ...]:
        return tuple(self._decisions)

    @property
    def reviews(self) -> tuple[OutcomeReview, ...]:
        return tuple(self._reviews)

    def actions_frame(self) -> pd.DataFrame:
        return pd.DataFrame([item.to_dict() for item in self._actions.values()])

    def decisions_frame(self) -> pd.DataFrame:
        return pd.DataFrame([item.to_dict() for item in self._decisions])

    def reviews_frame(self) -> pd.DataFrame:
        return pd.DataFrame([item.to_dict() for item in self._reviews])

    def summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in ActionStatus}
        for action in self._actions.values():
            counts[action.status.value] += 1
        counts["TOTAL"] = len(self._actions)
        counts["DECISIONS"] = len(self._decisions)
        counts["REVIEWS"] = len(self._reviews)
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": [item.to_dict() for item in self._actions.values()],
            "decisions": [item.to_dict() for item in self._decisions],
            "reviews": [item.to_dict() for item in self._reviews],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LeadershipActionRegistry":
        registry = cls()
        for item in payload.get("actions", []):
            data = dict(item)
            data["status"] = ActionStatus(data["status"])
            action = LeadershipAction(**data)
            registry._actions[action.action_id] = action
        registry._decisions = [
            DecisionRecord(**item) for item in payload.get("decisions", [])
        ]
        registry._reviews = [
            OutcomeReview(**item) for item in payload.get("reviews", [])
        ]
        return registry

    @classmethod
    def from_json(cls, content: str) -> "LeadershipActionRegistry":
        return cls.from_dict(json.loads(content))
