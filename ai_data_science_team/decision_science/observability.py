from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ExecutionEvent:
    component: str
    task: str
    status: str
    started_at: str
    finished_at: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    cost_usd: float | None = None
    retries: int = 0
    tool_calls: int = 0
    validation_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceRecorder:
    def __init__(self) -> None:
        self._events: list[ExecutionEvent] = []

    def start(self, component: str, task: str, **kwargs: Any) -> ExecutionEvent:
        event = ExecutionEvent(
            component=component,
            task=task,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )
        self._events.append(event)
        return event

    def finish(
        self,
        event: ExecutionEvent,
        *,
        status: str = "success",
        latency_ms: float | None = None,
        validation_status: str | None = None,
    ) -> None:
        event.status = status
        event.finished_at = datetime.now(timezone.utc).isoformat()
        event.latency_ms = latency_ms
        event.validation_status = validation_status

    @property
    def events(self) -> tuple[ExecutionEvent, ...]:
        return tuple(self._events)

    def summary(self) -> dict[str, Any]:
        total_cost = sum(e.cost_usd or 0.0 for e in self._events)
        return {
            "events": len(self._events),
            "failures": sum(e.status == "failure" for e in self._events),
            "retries": sum(e.retries for e in self._events),
            "tool_calls": sum(e.tool_calls for e in self._events),
            "cost_usd": round(total_cost, 6),
        }
