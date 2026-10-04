# BUSINESS SCIENCE UNIVERSITY
# AI DATA SCIENCE TEAM
# ***
# Workflow Planner Agent

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Sequence

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate

from ai_data_science_team.templates import BaseAgent
from ai_data_science_team.utils.messages import get_last_user_message_content


AGENT_NAME = "workflow_planner_agent"

EXECUTION_STEPS = {
    "frame",
    "list_files",
    "load",
    "merge",
    "sql",
    "quality_gate",
    "governance_check",
    "wrangle",
    "clean",
    "eda",
    "viz",
    "feature",
    "method_select",
    "model",
    "evaluate",
    "review",
    "red_team",
    "evidence",
    "reproducibility",
    "mlflow_log",
    "mlflow_tools",
    "decision_report",
}

STEP_ORDER = [
    "frame",
    "list_files",
    "load",
    "merge",
    "sql",
    "quality_gate",
    "governance_check",
    "wrangle",
    "clean",
    "eda",
    "viz",
    "feature",
    "method_select",
    "model",
    "evaluate",
    "review",
    "red_team",
    "evidence",
    "reproducibility",
    "mlflow_log",
    "mlflow_tools",
    "decision_report",
]


def _safe_json_loads(text: str) -> dict:
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"steps": parsed}
    except Exception:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(1))
        return parsed if isinstance(parsed, dict) else {"steps": parsed}
    except Exception:
        return {}


def _normalize_steps(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    requested = {str(value).strip() for value in values}
    return [step for step in STEP_ORDER if step in requested]


class WorkflowPlannerAgent(BaseAgent):
    """Plan either a legacy task workflow or a decision-grade analytical workflow."""

    def __init__(self, model: Any, log: bool = False):
        self._params = {"model": model, "log": log}
        self.response: Optional[dict] = None

    def update_params(self, **kwargs):
        self._params.update(kwargs)

    def invoke_messages(
        self,
        messages: Sequence[BaseMessage],
        *,
        context: Optional[Dict[str, Any]] = None,
        user_instructions: Optional[str] = None,
        **kwargs,
    ):
        llm = self._params["model"]
        if user_instructions is None:
            user_instructions = get_last_user_message_content(messages)
        context = context or {}
        proactive_mode = bool(context.get("proactive_workflow_mode"))
        decision_grade = bool(context.get("decision_grade_mode"))

        system = (
            "You are the workflow planner for an AI data-science team. "
            "Return ONLY valid JSON.\n\n"
            "Available ordered steps:\n"
            "frame: define question, decision, population, outcome and risks\n"
            "list_files: inspect available files without loading contents\n"
            "load: load data\n"
            "merge: merge/join/concat datasets\n"
            "sql: query a database\n"
            "quality_gate: measure completeness, integrity and blocking defects\n"
            "governance_check: check sensitive fields and disclosure risks\n"
            "wrangle: reshape/transform data\n"
            "clean: impute/fix types/outliers after quality assessment\n"
            "eda: descriptive analysis\n"
            "viz: visualization\n"
            "feature: feature engineering\n"
            "method_select: select inferential/predictive/causal/forecast method family\n"
            "model: train a predictive ML model\n"
            "evaluate: out-of-sample model evaluation\n"
            "review: independent analytical review\n"
            "red_team: search for competing explanations and failure modes\n"
            "evidence: record provenance and claim lineage\n"
            "reproducibility: create a reproducibility package\n"
            "mlflow_log: log workflow artifacts\n"
            "mlflow_tools: inspect MLflow\n"
            "decision_report: convert validated results into decision options and monitoring\n\n"
            "Schema: {\"steps\": [...], \"target_variable\": str|null, "
            "\"analysis_type\": str|null, \"questions\": [...], \"notes\": [...]}.\n"
            "Rules:\n"
            "- Keep narrow requests narrow.\n"
            "- Do not treat the noun 'model' (for example a product model) as an ML request.\n"
            "- ML model/evaluate requires a target variable.\n"
            "- Never clean before quality_gate in decision-grade mode.\n"
            "- Causal claims require frame, quality_gate, method_select, review and red_team.\n"
            "- Predictive workflows require evaluate and review.\n"
            "- If decision_grade_mode is on, broad analytical requests should normally include "
            "frame, quality_gate, governance_check, method_select, review, evidence, "
            "reproducibility and decision_report.\n"
            f"- proactive_workflow_mode={'ON' if proactive_mode else 'OFF'}.\n"
            f"- decision_grade_mode={'ON' if decision_grade else 'OFF'}.\n"
        )

        human = (
            "User request:\n{user_instructions}\n\n"
            "Current context:\n{context_json}\n\n"
            "Return JSON only."
        )
        prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("human", human)]
        )
        response = (prompt | llm).invoke(
            {
                "user_instructions": user_instructions or "",
                "context_json": json.dumps(context, default=str),
            }
        )
        plan = _safe_json_loads(
            getattr(response, "content", "") or str(response)
        )

        steps = _normalize_steps(plan.get("steps"))
        target = plan.get("target_variable")
        target = str(target).strip() if target is not None else None
        analysis_type = plan.get("analysis_type")
        analysis_type = (
            str(analysis_type).strip().lower()
            if analysis_type is not None
            else None
        )

        questions = plan.get("questions", [])
        if isinstance(questions, str):
            questions = [questions]
        questions = [str(q).strip() for q in questions if str(q).strip()]

        notes = plan.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        notes = [str(n).strip() for n in notes if str(n).strip()]

        if any(step in steps for step in ("model", "evaluate")) and not target:
            steps = [s for s in steps if s not in {"model", "evaluate"}]
            questions.insert(
                0,
                "What is the target column name for modeling/evaluation?",
            )

        if decision_grade:
            requested = set(steps)
            if "clean" in requested and "quality_gate" not in requested:
                requested.add("quality_gate")
            if analysis_type == "causal":
                requested.update(
                    {"frame", "quality_gate", "method_select", "review", "red_team"}
                )
            if "model" in requested:
                requested.update({"evaluate", "review"})
            steps = [step for step in STEP_ORDER if step in requested]

        self.response = {
            "steps": steps,
            "target_variable": target,
            "analysis_type": analysis_type,
            "questions": questions,
            "notes": notes,
        }

    def get_plan(self) -> Optional[dict]:
        return self.response
