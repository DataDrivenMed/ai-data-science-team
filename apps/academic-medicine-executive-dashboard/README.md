# Academic Medicine Executive Dashboard

A consultant-grade Streamlit executive cockpit for academic health sciences performance, CQI, evidence lineage, and leadership decision support.

## Run

```bash
streamlit run apps/academic-medicine-executive-dashboard/app.py
```

## Executive experience

The dashboard is organized into six surfaces:

1. **Executive Summary**: portfolio KPIs, exception-first view, and downloadable Dean/leadership brief.
2. **CQI Radar**: all configured metrics with target, warning, and critical thresholds.
3. **Domain Performance**: focused Admissions, UME, GME, Research, and Workforce scorecards.
4. **Trends**: longitudinal metric trajectories and target reference lines.
5. **Evidence**: source inventory, SHA-256 dataset fingerprints, calculations, and evidence records.
6. **Leadership Actions**: corrective action register, owners, sponsors, due dates, executive decision log, and post-action outcome verification.
7. **Accreditation Evidence**: metric-level evidence packet linking definition, trends, provenance, actions, decisions, and closure review.
8. **Data & Configuration**: institutional uploads and editable metric registry.

## Data modes

### Demonstration

The application starts with synthetic demonstration data so the full dashboard can be evaluated immediately.

### Institutional upload

CSV/XLSX files can replace the Admissions, UME, GME, Research, and Workforce datasets for the current session.

The default calculators expect the schema documented in `docs/ACADEMIC_MEDICINE.md`. Local schemas can be adapted by using the subpack schema objects or by registering custom CQI calculators.

## Metric registry

Each CQI metric is defined by one `CQIMetricSpec`:

- metric ID and display name
- domain
- dataset
- calculator
- owner
- source
- direction of desired performance
- target
- warning threshold
- critical threshold
- period column
- display unit
- accreditation standard/element
- cadence
- calculator parameters

The same specification drives the dashboard, alerts, longitudinal trends, evidence lineage, and leadership brief.

## Design principles

- exception-first for executives
- definitions before visualization
- no hidden denominator changes
- source lineage for every metric
- configurable thresholds instead of institution-specific hard coding
- one metric definition across dashboard and executive brief
- descriptive comparisons are not presented as causal findings
- data/configuration controls are separated from leadership views


## Closed-loop CQI

The dashboard now closes the loop from exception to verified outcome:

```text
metric threshold breach
→ corrective action
→ accountable owner
→ leadership decision
→ execution status
→ remeasurement
→ verified closure or continued action
→ accreditation/CQI evidence packet
```

Action and decision records can be downloaded as JSON. Evidence packets can be downloaded as Markdown or JSON for committee review, accreditation files, or institutional archives.
