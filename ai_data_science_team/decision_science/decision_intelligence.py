from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Scenario:
    name: str
    expected_value: float
    implementation_cost: float = 0.0
    risk_penalty: float = 0.0
    feasibility: float = 1.0
    assumptions: list[str] = field(default_factory=list)
    monitoring_metrics: list[str] = field(default_factory=list)

    @property
    def utility(self) -> float:
        return (
            (self.expected_value - self.implementation_cost - self.risk_penalty)
            * max(0.0, min(1.0, self.feasibility))
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["utility"] = self.utility
        return data


def rank_scenarios(scenarios: list[Scenario]) -> list[Scenario]:
    """Rank explicit user-supplied scenarios without inventing probabilities."""
    return sorted(scenarios, key=lambda scenario: scenario.utility, reverse=True)
