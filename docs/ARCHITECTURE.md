# Decision-Science Architecture

This fork preserves the upstream AI Data Science Team agents and adds a control plane for decision-grade analytical work.

## Design principle

The system is organized around an analytical lifecycle rather than around a growing list of agents:

1. Frame the decision
2. Inspect and load data
3. Run a data-quality gate
4. Run governance checks
5. Select an analytical method family
6. Execute existing wrangling, EDA, visualization, SQL, and ML agents
7. Independently review results
8. Red-team the interpretation
9. Record evidence and provenance
10. Write a reproducibility package
11. Translate validated findings into decision options and monitoring

## Core package

The new code lives in `ai_data_science_team/decision_science/`.

- `contracts.py`: typed analytical contract and review/result models
- `data_quality.py`: deterministic pre-analysis quality gate
- `methods.py`: method-family routing for descriptive, inferential, predictive, causal, forecasting, survival, and longitudinal questions
- `review.py`: independent fail-closed checks
- `red_team.py`: competing explanations and stress tests
- `governance.py`: sensitive-field and small-cell screening
- `provenance.py`: evidence ledger and dataset fingerprints
- `reproducibility.py`: auditable analysis bundles
- `orchestrator.py`: control plane connecting the lifecycle

## Backward compatibility

Existing agents, apps, and multi-agent workflows are not removed. The new layer decides when they should run and what must be checked before their outputs are treated as decision-ready evidence.

## Quality gates

The orchestration layer is intentionally fail-closed for major defects:

- duplicate identifiers
- absent required columns
- infinite numeric values
- predictive results without out-of-sample evaluation
- causal claims without identification assumptions
- credential-like fields in data

Warnings do not automatically block work, but they downgrade evidence strength and should appear in interpretation.

## Extension model

Domain packs should add semantic rules without duplicating the core lifecycle. Examples:

- academic medicine
- clinical research
- admissions
- graduate medical education
- finance
- operations

A domain pack can supply required variables, data dictionaries, suppression thresholds, approved methods, metric definitions, and domain-specific validation.
