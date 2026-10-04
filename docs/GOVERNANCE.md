# Governance and Analytical Safety

The decision-science layer treats governance as part of analysis, not a final publishing step.

## Human approval gates

Human approval is recommended before:

- deleting or excluding observations
- imputing outcomes
- changing inclusion/exclusion criteria
- using sensitive identifiers outside an approved environment
- deploying a predictive model
- making a causal claim from observational data
- publishing small-cell subgroup results
- taking a consequential operational action

The `AnalysisContract.human_approval_required` field is the canonical place to record these gates.

## Data quality

`assess_data_quality()` measures observable defects before cleaning. This separation matters because cleaning can otherwise hide evidence of upstream data problems.

Current deterministic checks include:

- missingness
- exact duplicate rows
- duplicate identifiers
- required-column presence
- constant columns
- high-missingness columns
- infinite numeric values
- temporal parsing failures
- small dataset warnings

## Privacy and disclosure

`check_governance()` screens column names for common direct identifiers and credentials and flags categorical small cells. These checks are conservative heuristics, not a substitute for institutional privacy review.

## Evidence strength

Evidence strength is derived from explicit review status and measured quality, not from an LLM's self-reported confidence.

- HIGH
- MODERATE
- LOW
- INSUFFICIENT

## Provenance

The evidence ledger records:

- claim
- source
- transformation
- code reference
- dataset fingerprint
- validation status
- metadata
- timestamp

Dataset fingerprints use SHA-256 so an analysis can be tied to the exact input representation used.

## Causal language

Observational associations should not be described as causal without explicit identification assumptions and sensitivity analysis. The reviewer fails causal analyses that omit identification assumptions.
