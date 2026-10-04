# Academic Medicine Domain Pack

The academic medicine domain pack adds reusable semantics, data checks, contracts, and metric calculations for medical education analytics.

It does not hard-code one institution's local definitions. High-stakes definitions such as match success, learner risk, cohort eligibility, or retention must be set by the institution using the analysis.

## Core schema

`AcademicMedicineSchema` maps local column names to:

- learner identifier
- cohort
- program
- site
- assessment date
- attempt number

## Supported study templates

`AcademicMedicineStudy` currently includes:

- USMLE or other board score
- board pass/fail
- admissions yield
- resident survey
- retention
- match outcome

`AcademicMedicineDomainPack.contract()` builds an `AnalysisContract` with academic-medicine-specific assumptions, risks, disclosure concerns, and human approval requirements.

## Validation

The pack can check:

- presence of learner and cohort identifiers
- missing learner identifiers
- missing cohort values
- duplicate learner/cohort records when one row per learner is required
- small cells in program or site variables
- assessment outcome presence
- valid positive attempt numbering

The pack deliberately separates repeated-assessment datasets from one-row-per-learner datasets. Attempt rules should be prespecified before calculating first-attempt outcomes.

## Executable metrics

`AcademicMedicineMetricEngine` currently implements:

### First-attempt pass rate

Uses the lowest documented attempt number per learner.

Returns:

- numerator
- denominator
- rate
- explicit attempt rule

### Admissions yield

Requires one row per applicant.

Denominator: admitted applicants.

Numerator: admitted applicants who matriculated.

### Survey response rate

Requires the explicit eligible population count and unique respondent identifiers.

### Generic learner-level binary rate

Supports retention, match success, or another locally defined 0/1 outcome, while requiring one row per learner.

## Generic metric registry

`academic_medicine_metrics()` provides definitions for:

- first-attempt pass rate
- board score mean
- admissions yield
- match success
- resident survey response rate
- in-state retention

These definitions are templates. Local eligibility, follow-up timing, and policy definitions must be documented in the analysis contract.

## Example: board-score analysis

```python
from ai_data_science_team import (
    AcademicMedicineDomainPack,
    AcademicMedicineSchema,
    DecisionScienceOrchestrator,
)

pack = AcademicMedicineDomainPack(
    AcademicMedicineSchema(
        learner_id="student_id",
        cohort="graduation_year",
        attempt="step2_attempt",
    )
)

contract = pack.board_score_contract(
    outcome="step2_ck",
    predictors=["mcat", "science_gpa"],
    decision_to_support="Identify population-level academic preparation signals",
    population="matriculated medical students with eligible Step 2 CK outcomes",
)

orchestrator = DecisionScienceOrchestrator()
run = orchestrator.prepare(
    contract,
    df,
    id_columns=["student_id"],
)

run = orchestrator.execute(run, df)
```

## High-stakes use

The domain pack is intended for population-level analysis and decision support. Individual learner prediction, progression, admissions, ranking, or intervention decisions require explicit governance and human review. The code records these approval requirements but does not replace institutional policy, educational judgment, or due process.
