<div align="center">
  <img src="./img/ai_data_science_logo.png" alt="AI Data Science Team" width="360">
</div>

# AI Data Science Team: Decision-Grade Fork

This repository is a maintained fork of
[Business Science's AI Data Science Team](https://github.com/business-science/ai-data-science-team).

The upstream project provides a strong collection of AI agents for data loading,
cleaning, wrangling, visualization, SQL, machine learning, MLflow, and multi-agent
analysis. This fork keeps those capabilities and adds a second layer focused on a
different problem:

> How do we make AI-generated analysis reproducible, reviewable, governed, and
> safe enough to support consequential decisions?

The result is not just another group of specialist agents. It is an analytical
control plane around those agents.

## What this fork adds

The new `ai_data_science_team.decision_science` package adds:

- **Analysis contracts** that define the decision, population, outcome, method
  class, assumptions, risks, and required outputs before analysis begins.
- **Data-quality gates** that run before cleaning and can stop analysis when
  required columns, identifier integrity, or numeric validity fail.
- **Governance checks** for sensitive-field names, credentials, and small-cell
  disclosure risk.
- **Method routing** across descriptive, inferential, predictive, causal,
  forecasting, survival, and longitudinal questions.
- **Independent review** that fails closed when key safeguards are missing.
- **Red-team analysis** that searches for competing explanations and required
  stress tests.
- **Evidence provenance** with SHA-256 dataset fingerprints and claim-level
  lineage.
- **Reproducibility packages** containing the contract, quality report, methods,
  results, review, evidence ledger, code, and environment metadata.
- **Decision-grade orchestration** that wraps existing agents instead of
  replacing them.
- **Decision-grade workflow planning** with explicit framing, quality,
  governance, review, evidence, and reproducibility steps.
- **Automated CI and tests** for the new control plane.

## Why this matters

A normal agent workflow often looks like:

```text
question -> clean -> analyze -> visualize -> model
```

This fork adds the controls that should surround that workflow:

```text
question
  -> decision framing
  -> data quality
  -> governance
  -> method selection
  -> existing data-science agents
  -> independent review
  -> red team
  -> evidence ledger
  -> reproducibility package
  -> decision report
  -> CQI monitoring
  -> leadership action
  -> remeasurement
  -> verified closure
```

The design goal is to make analytical failure visible rather than hide it behind
a polished chart or fluent explanation.

## Quickstart

### Install

```bash
git clone https://github.com/DataDrivenMed/ai-data-science-team.git
cd ai-data-science-team
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

### Run a decision-grade analysis gate

```python
import pandas as pd

from ai_data_science_team import (
    AnalysisContract,
    AnalysisType,
    DecisionScienceOrchestrator,
)

df = pd.read_csv("data.csv")

contract = AnalysisContract(
    question="Can the available predictors estimate the target on future cases?",
    decision_to_support="Whether to operationalize a predictive model",
    population="eligible records",
    outcome="target",
    target_variable="target",
    analysis_type=AnalysisType.PREDICTIVE,
    outcome_type="binary",
    human_approval_required=["model deployment"],
)

orchestrator = DecisionScienceOrchestrator()

run = orchestrator.prepare(
    contract,
    df,
    required_columns=["target"],
    id_columns=["record_id"],
)

print(run.quality.to_dict())
print(run.governance.to_dict())
print(run.methods.to_dict())

if run.ready_for_analysis:
    # Use the existing AI Data Science Team agents here.
    results = {
        "n": len(df),
        "holdout_metrics": {"auc": 0.82},
        "target_leakage_checked": True,
    }

    run = orchestrator.finalize(
        run,
        results,
        source="model evaluation",
        code_reference="analysis/model.py",
    )

    print(run.review.to_dict())
    print(run.red_team.to_dict())
    print(run.evidence.to_json())
```

## Data-quality gate

`assess_data_quality()` currently checks:

- required-column presence
- overall missingness
- columns with high missingness
- exact duplicate rows
- duplicate identifier values
- constant columns
- infinite numeric values
- temporal parsing failures
- small-dataset warnings

The gate returns one of:

- `GO`
- `CONDITIONAL_GO`
- `NO_GO`

Cleaning is intentionally downstream of this check. Otherwise an automated
cleaning step can erase evidence that the source system is producing bad data.

## Analytical method router

`recommend_methods()` distinguishes among:

| Question type | Method family |
|---|---|
| Descriptive | Distribution and stratified summaries |
| Inferential | Regression and confidence-interval based estimation |
| Predictive | Baselines, ensembles, out-of-sample validation |
| Causal | DAG-guided adjustment and causal estimators |
| Forecasting | Time-series models with chronological validation |
| Survival | Time-to-event methods |
| Longitudinal | Mixed-effects and clustered methods |

The router is now connected to executable statistical engines for inferential,
causal, forecasting, survival, and longitudinal analyses. Method-specific
variables with consequential meaning, such as a causal treatment/confounder set
or survival event definition, must still be supplied explicitly.


## Statistical execution engines

The fork now executes the major non-AutoML method families directly:

- **Inferential:** OLS, logistic regression, Poisson regression
- **Causal:** IPW and augmented IPW for binary treatments
- **Forecasting:** ARIMA with chronological holdout evaluation and naive baseline
- **Survival:** Kaplan-Meier and Cox proportional hazards
- **Longitudinal:** mixed-effects models and GEE

Execution outputs are typed, include diagnostics and uncertainty, enter the
evidence ledger, and are automatically passed through independent review.

Example:

```python
run = orchestrator.prepare(contract, df)

if run.ready_for_analysis:
    run = orchestrator.execute(run, df)

print(run.execution_result.to_dict())
print(run.review.to_dict())
```

Causal execution requires the treatment and confounder set explicitly. Survival
execution requires explicit duration/event columns. Forecasting requires an
explicit time index. Longitudinal models require the grouping unit.

See [Statistical execution engines](docs/EXECUTION_ENGINES.md).

## Academic medicine domain package

Academic medicine is now a six-subpack package:

- **Admissions:** applicant funnel, yield, MCAT/GPA profile, scholarship strategy,
  and demographic/fairness screening
- **UME:** USMLE, NBME, course performance, clerkships, remediation, progression
- **GME:** resident surveys, program outcomes, attrition, board outcomes, site
  analysis, workforce
- **Accreditation/CQI:** LCME and ACGME metric specifications, monitoring
  thresholds, alerts, and evidence lineage
- **Research:** NIH funding, publications, grants, clinical trials, research growth
- **Workforce:** retention, specialty, geography, underserved practice, pipeline
- **Executive/CQI:** unified metric registry, trend computation, threshold
  exceptions, evidence lineage, and leadership briefing

The original generic academic-medicine APIs remain backward compatible.

Each subpack keeps consequential definitions configurable. For example, the code
does not invent an institution's definition of match success, retention,
underserved practice, accreditation threshold, or demographic fairness.

See [Academic medicine domain package](docs/ACADEMIC_MEDICINE.md).

## Academic Medicine Executive Dashboard

The repository now includes a leadership-facing CQI and decision-intelligence
application:

```bash
streamlit run apps/academic-medicine-executive-dashboard/app.py
```

The dashboard uses the same academic-medicine metric definitions and calculators
as the underlying Python package. It provides:

- executive KPI portfolio status
- warning/critical exception management
- Admissions, UME, GME, Research, and Workforce domain views
- longitudinal trends
- configurable targets and thresholds
- dataset inventory and SHA-256 fingerprints
- claim/evidence lineage
- institutional CSV/XLSX upload
- editable CQI metric registry
- downloadable Dean/leadership brief generated from the same metric results
- corrective-action register with accountable owners and executive sponsors
- leadership decision log with rationale and options considered
- post-action remeasurement and verified closure
- downloadable accreditation/CQI evidence packets

A built-in synthetic demonstration mode allows the complete UI to run before
institutional datasets are connected.

See [Academic Medicine Executive Dashboard](apps/academic-medicine-executive-dashboard/README.md).

## Independent reviewer

`review_analysis()` checks the result independently from the code that produced
it.

Examples of blocking failures:

- a predictive model has no holdout or cross-validation evidence
- a causal analysis does not document identification assumptions
- the data-quality gate is `NO_GO`
- the analysis contract itself is invalid

Warnings can downgrade evidence strength even when the workflow is allowed to
continue.

Evidence strength is reported as:

- `HIGH`
- `MODERATE`
- `LOW`
- `INSUFFICIENT`

This is based on explicit rules, not an LLM confidence statement.

## Red-team layer

The red-team component forces the workflow to ask what else could explain the
result.

Typical challenges include:

- proxy relationships
- cohort effects
- missingness and selection
- leakage
- temporal mismatch
- residual confounding
- subgroup heterogeneity
- statistical significance without practical importance

The output includes a falsification or stress test for each major alternative
explanation.

## Evidence ledger and reproducibility

The evidence ledger records:

```text
claim
source
transformation
code reference
dataset fingerprint
validation status
metadata
timestamp
```

`ReproducibilityPackage` can write an auditable directory containing:

```text
analysis_contract.json
data_quality.json
method_recommendation.json
review_report.json
results.json
evidence_ledger.json
analysis.py
executive_summary.md
environment.json
```

## WorkflowPlannerAgent changes

The planner now understands both the original execution steps and these
decision-grade steps:

```text
frame
quality_gate
governance_check
method_select
review
red_team
evidence
reproducibility
decision_report
```

Use `decision_grade_mode=True` in the planner context to enforce ordering rules
such as quality assessment before cleaning and review after predictive modeling.

## Existing upstream capabilities preserved

This fork still includes the upstream agents and applications for:

- data loading
- data cleaning
- data wrangling
- feature engineering
- visualization
- exploratory analysis
- SQL database interaction
- H2O machine learning
- MLflow
- Pandas multi-agent analysis
- SQL multi-agent analysis
- supervisor-led workflows
- AI Pipeline Studio

Run the flagship upstream application with:

```bash
streamlit run apps/ai-pipeline-studio-app/app.py
```

## Repository structure

```text
ai_data_science_team/
  agents/
  ds_agents/
  ml_agents/
  multiagents/
  decision_science/
    contracts.py
    data_quality.py
    governance.py
    methods.py
    orchestrator.py
    provenance.py
    red_team.py
    reproducibility.py
    review.py

docs/
  ARCHITECTURE.md
  GOVERNANCE.md
  MIGRATION.md

tests/
  test_decision_science.py
```

## Development and validation

```bash
python -m compileall -q ai_data_science_team
pytest
ruff check ai_data_science_team/decision_science tests
```

GitHub Actions runs the decision-science checks on Python 3.10, 3.11, and 3.12.

## Current implementation boundary

The control plane now includes working inferential, causal, forecasting,
survival, and longitudinal execution engines plus the academic medicine domain
pack. Important boundaries remain:

- causal adjustment sets are not inferred automatically
- unmeasured-confounding sensitivity methods are not yet automated
- competing-risk and advanced time-varying survival models are not yet included
- multivariate/more complex random-effects structures still require explicit specification
- automated DAG construction is not included
- institution-specific policy engines still require local configuration
- observability records execution metadata but does not yet provide a full hosted tracing backend

Keeping these boundaries explicit is intentional. The repository should never
advertise an analytical safeguard that the code does not actually enforce.

## Recommended next phases

1. Build the next deep domain package for clinical research.
2. Add configurable local metric dictionaries and policy files for each academic-medicine subpack.
3. Add doubly robust cross-fitting and formal unmeasured-confounding sensitivity methods.
4. Add competing-risks and time-varying survival methods.
5. Add typed result adapters from existing LLM agents into the statistical reviewer.
6. Add prompt/model evaluation benchmarks and regression suites.
7. Add human approval checkpoints to the Pipeline Studio interface.
8. Add a hosted observability layer and post-decision monitoring workflows.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Governance](docs/GOVERNANCE.md)
- [Migration guide](docs/MIGRATION.md)
- [Statistical execution engines](docs/EXECUTION_ENGINES.md)
- [Academic medicine domain pack](docs/ACADEMIC_MEDICINE.md)

## Attribution

This repository is forked from
[business-science/ai-data-science-team](https://github.com/business-science/ai-data-science-team)
and retains its upstream license and attribution.

The decision-science control-plane additions in this fork are maintained in
[DataDrivenMed/ai-data-science-team](https://github.com/DataDrivenMed/ai-data-science-team).

## License

See [LICENSE](LICENSE).
