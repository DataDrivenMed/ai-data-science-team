# Academic Medicine Domain Package

The academic medicine implementation is now organized as a package with six
specialized subpacks:

```text
academic_medicine/
├── admissions.py
├── ume.py
├── gme.py
├── accreditation.py
├── research.py
├── workforce.py
├── core.py
└── common.py
```

The original `AcademicMedicineDomainPack`, schemas, study templates, and metric
engine remain available for backward compatibility.

The subpacks add executable domain logic while keeping local institutional
definitions configurable.

## Admissions

`AdmissionsPack` includes:

- applicant funnel
- interview rate
- admit rate
- admissions yield
- overall matriculation rate
- MCAT/GPA/science-GPA profile summaries
- scholarship strategy summaries
- demographic/fairness screening
- yield analysis contracts

Scholarship comparisons are explicitly descriptive. The package does not label
an observed yield difference as a scholarship effect without causal adjustment.

Fairness summaries report group counts, outcome rates, risk differences, and rate
ratios against an explicit or automatically selected reference group. Small
groups can be suppressed with a configurable minimum N.

## UME

`UMEPack` includes:

- USMLE or other repeated board-assessment first-attempt outcomes
- NBME score summaries
- course-performance summaries
- clerkship summaries
- remediation rate
- progression rate
- USMLE analysis contracts

First-attempt calculations use the lowest documented attempt per learner and
exam. This prevents later successful retakes from being misclassified as
first-attempt passes.

## GME

`GMEPack` includes:

- resident/fellow survey response rate
- attrition rate
- board pass rate
- retention rate
- program-level outcomes
- site-level outcome summaries
- specialty/workforce distributions
- attrition analysis contracts

Program and site tables support minimum-cell suppression.

## Accreditation and CQI

`AccreditationPack` adds configurable:

- LCME metric specifications
- ACGME metric specifications
- CQI snapshots
- target/warning/critical thresholds
- threshold alerts
- evidence lineage

Thresholds are not hard-coded. Each metric specification records its owner,
source, direction, target, warning threshold, critical threshold, accreditation
standard or element, and monitoring cadence.

Example:

```python
spec = AccreditationPack.lcme_spec(
    element="8.4",
    metric_id="board_pass",
    name="First-attempt board pass",
    owner="UME",
    source="Board outcomes",
    target=0.95,
    warning_threshold=0.90,
    critical_threshold=0.85,
    cadence="annual",
)
```

## Research

`ResearchPack` includes:

- NIH funding trend
- absolute funding growth
- funding CAGR
- publication volume
- citation volume
- citations per publication
- grant success rate
- clinical-trial portfolio/status
- configurable research growth index

The research growth index combines funding, publications, and awarded grants
using explicit weights that must sum to 1.0.

## Workforce

`WorkforcePack` includes:

- in-state retention
- specialty distribution
- geographic distribution
- underserved-practice rate
- pipeline stage counts
- pipeline conversion between stages

Definitions such as "retained in-state" or "underserved practice" remain local
policy definitions and are not inferred by the library.

## Core academic-medicine package

The original core APIs remain available:

- `AcademicMedicineDomainPack`
- `AcademicMedicineMetricEngine`
- `AcademicMedicineSchema`
- `AcademicMedicineStudy`
- `academic_medicine_metrics()`

They continue to support generic board score/pass, admissions yield, resident
survey, retention, and match analyses.

## High-stakes use

These subpacks are designed for population-level institutional analytics and
decision support.

Individual admissions, learner progression, remediation, resident standing,
faculty/trainee ranking, or other consequential person-level decisions require
institutional policy, appropriate governance, and human review.

Descriptive demographic differences are screening signals. They are not, by
themselves, evidence of bias, discrimination, or causal mechanisms.


## Closed-loop CQI and leadership action

The academic medicine package now includes:

- `LeadershipActionRegistry`
- `LeadershipAction`
- `DecisionRecord`
- `OutcomeReview`
- `AccreditationEvidencePackage`

A warning or critical metric can be converted into an owned corrective action. The action records the trigger, owner, rationale, success criterion, due/review dates, target value, executive sponsor, status, and linked evidence.

Leadership decisions can be recorded with decision maker, rationale, options considered, and evidence references.

After intervention, the same metric is remeasured. The outcome review determines whether the configured success criterion has been met. Successful remeasurement moves the action to `VERIFIED`; unsuccessful remeasurement keeps the CQI cycle open.

The evidence packager combines:

- current metric definition and result
- target/warning/critical thresholds
- longitudinal performance
- dataset fingerprint and evidence lineage
- corrective actions
- leadership decision log
- outcome verification

This creates a single traceable record from institutional data to CQI closure.
