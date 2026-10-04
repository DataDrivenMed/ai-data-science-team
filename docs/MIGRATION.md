# Migration Guide

No migration is required for existing AI Data Science Team users.

Existing imports and apps remain available. The new decision-science API is additive.

## Minimal use

```python
import pandas as pd

from ai_data_science_team import (
    AnalysisContract,
    AnalysisType,
    DecisionScienceOrchestrator,
)

df = pd.read_csv("data.csv")

contract = AnalysisContract(
    question="What predicts the outcome?",
    decision_to_support="Whether to build an operational model",
    population="eligible records",
    outcome="target",
    target_variable="target",
    analysis_type=AnalysisType.PREDICTIVE,
)

orchestrator = DecisionScienceOrchestrator()
run = orchestrator.prepare(
    contract,
    df,
    required_columns=["target"],
    id_columns=["record_id"],
)

if run.ready_for_analysis:
    # Execute the existing AI Data Science Team agents here.
    results = {
        "n": len(df),
        "holdout_metrics": {"auc": 0.82},
        "target_leakage_checked": True,
    }
    run = orchestrator.finalize(run, results)

print(run.review.to_dict())
```

## Decision-grade planner mode

The existing `WorkflowPlannerAgent` now recognizes lifecycle steps such as `frame`, `quality_gate`, `governance_check`, `method_select`, `review`, `red_team`, `evidence`, `reproducibility`, and `decision_report`.

Set `decision_grade_mode=True` in planner context when you want the planner to enforce those safeguards.
