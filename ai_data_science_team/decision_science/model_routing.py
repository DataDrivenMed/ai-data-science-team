from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TaskProfile:
    task_type: str
    reasoning_required: int = 3
    coding_required: int = 0
    context_required: int = 0
    cost_sensitivity: int = 3


@dataclass(frozen=True, slots=True)
class ModelCapability:
    name: str
    reasoning: int
    coding: int
    context: int
    relative_cost: int
    allowed_tasks: frozenset[str] = field(default_factory=frozenset)


class ModelRouter:
    """Provider-neutral deterministic router.

    Scores are intentionally supplied by the deployer. The library does not
    invent benchmark values for model providers.
    """

    def __init__(self, models: list[ModelCapability]):
        if not models:
            raise ValueError("at least one model capability is required")
        self.models = models

    def choose(self, task: TaskProfile) -> ModelCapability:
        candidates = [
            model
            for model in self.models
            if not model.allowed_tasks or task.task_type in model.allowed_tasks
        ]
        if not candidates:
            raise ValueError(f"no model is allowed for task_type={task.task_type!r}")

        def score(model: ModelCapability) -> float:
            capability = (
                min(model.reasoning, task.reasoning_required) * 3
                + min(model.coding, task.coding_required) * 2
                + min(model.context, task.context_required)
            )
            cost_penalty = model.relative_cost * task.cost_sensitivity
            shortfall = (
                max(0, task.reasoning_required - model.reasoning) * 8
                + max(0, task.coding_required - model.coding) * 6
                + max(0, task.context_required - model.context) * 2
            )
            return capability - cost_penalty - shortfall

        return max(candidates, key=score)
