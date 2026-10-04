from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MetricDefinition:
    name: str
    definition: str
    numerator: str | None = None
    denominator: str | None = None
    unit: str | None = None
    owner: str | None = None
    source: str | None = None
    suppression_threshold: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class InstitutionalKnowledgeStore:
    """Small local registry for stable institutional analytical definitions."""

    def __init__(self) -> None:
        self.metrics: dict[str, MetricDefinition] = {}
        self.terms: dict[str, str] = {}
        self.known_limitations: list[str] = []

    def add_metric(self, metric: MetricDefinition) -> None:
        self.metrics[metric.name] = metric

    def add_term(self, term: str, definition: str) -> None:
        self.terms[term] = definition

    def add_limitation(self, limitation: str) -> None:
        if limitation not in self.known_limitations:
            self.known_limitations.append(limitation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": {
                name: asdict(metric)
                for name, metric in sorted(self.metrics.items())
            },
            "terms": dict(sorted(self.terms.items())),
            "known_limitations": list(self.known_limitations),
        }

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return target
