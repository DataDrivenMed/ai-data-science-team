# Statistical Execution Engines

The decision-science layer includes executable statistical engines backed by statsmodels and scikit-learn.

## Inferential

`InferentialEngine` implements:

- ordinary least squares with optional HC3 robust standard errors
- logistic regression with HC3 covariance and odds ratios
- Poisson regression with optional exposure offsets

Diagnostics include heteroskedasticity screening, condition number, deviance, extreme fitted probabilities, and Poisson dispersion.

## Causal

`CausalEngine` implements binary-treatment average treatment effect estimators:

- inverse probability weighting (IPW)
- augmented inverse probability weighting (AIPW)

The caller must explicitly provide treatment and confounder columns. The library never infers an adjustment set from correlations.

Diagnostics include:

- propensity-score range
- positivity violations
- effective sample size
- standardized mean differences before and after weighting
- explicit identification assumptions

AIPW is doubly robust with respect to the supplied propensity and outcome nuisance models, but that property does not remove the need for a defensible confounder set or unmeasured-confounding sensitivity analysis.

## Forecasting

`ForecastEngine.arima()` implements ARIMA forecasting with:

- chronological holdout validation
- MAE and RMSE
- last-value naive baseline comparison
- AIC and BIC
- forecast confidence intervals

A forecast that does not beat the naive baseline is returned with a warning rather than silently treated as useful.

## Survival

`SurvivalEngine` implements:

- Kaplan-Meier survival estimation
- Cox proportional-hazards regression

The Cox engine reports hazard ratios and confidence intervals and performs a Schoenfeld-residual correlation screen against log event time for each encoded covariate.

This is a useful diagnostic screen, not a substitute for substantive model review, inspection of time-varying effects, or competing-risk methods when the study requires them.

## Longitudinal

`LongitudinalEngine` implements:

- linear mixed-effects models
- generalized estimating equations (GEE)

Mixed-effects execution reports convergence and random-effect covariance. GEE supports Gaussian or binary outcomes with exchangeable or independent working correlation.

## Router

`StatisticalExecutionRouter` dispatches an `AnalysisContract` to the appropriate engine. It intentionally refuses to infer variables whose meaning is consequential, including:

- causal treatment
- causal confounders
- survival duration/event
- forecast time index
- longitudinal grouping unit

Those must be supplied explicitly.

## Orchestrator execution

```python
run = orchestrator.prepare(contract, df)

if run.ready_for_analysis:
    run = orchestrator.execute(
        run,
        df,
        # method-specific arguments when required
    )

print(run.execution_result.to_dict())
print(run.review.to_dict())
```

The execution result is automatically recorded in the evidence ledger and passed through the independent reviewer and red-team layer.
