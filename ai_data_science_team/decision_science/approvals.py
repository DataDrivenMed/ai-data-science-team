from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(slots=True)
class ApprovalGate:
    gate_id: str
    action: str
    rationale: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: str | None = None
    decided_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def approve(self, actor: str) -> None:
        self.status = ApprovalStatus.APPROVED
        self.approved_by = actor
        self.decided_at = datetime.now(timezone.utc).isoformat()

    def reject(self, actor: str) -> None:
        self.status = ApprovalStatus.REJECTED
        self.approved_by = actor
        self.decided_at = datetime.now(timezone.utc).isoformat()

    @property
    def can_execute(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class ApprovalRegistry:
    def __init__(self) -> None:
        self._gates: dict[str, ApprovalGate] = {}

    def require(self, gate_id: str, action: str, rationale: str) -> ApprovalGate:
        gate = ApprovalGate(gate_id=gate_id, action=action, rationale=rationale)
        self._gates[gate_id] = gate
        return gate

    def get(self, gate_id: str) -> ApprovalGate:
        return self._gates[gate_id]

    @property
    def pending(self) -> tuple[ApprovalGate, ...]:
        return tuple(g for g in self._gates.values() if g.status == ApprovalStatus.PENDING)
