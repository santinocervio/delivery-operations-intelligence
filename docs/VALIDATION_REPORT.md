# Validation and Final Operations Review

These checks describe the original private-source analysis. The public snapshot includes selected aggregate records; full data reruns require [authorized inputs](DATA_ACCESS.md). Synthetic publication checks are recorded separately in [publication validation](../outputs/publication_validation.json).

## Executed checks

- Canonical source/data validation: **passed**, 26 passed checks, 0 failures. [Details](../outputs/validation.json).
- Automated tests: **passed**, 40 tests, 0 failures. [Original private-run test record: not distributed](DATA_ACCESS.md#excluded-private-artifacts).
- Repeat complete-build comparison: **passed**. [Artifact comparisons](../outputs/reproducibility.json).
- Power BI static validation: **passed**. [Private export and native status](DATA_ACCESS.md#excluded-private-artifacts).
- Native Power BI DAX/M execution is not established by static validation. Existing authored report files are preserved; Desktop refresh and field bindings require a native engine check.

## Head of Operations review

**Where does the problem occur?** Primarily before final rider notification in the measured late-order difference. This is a stage location, not an identified cause.

**When and for whom?** Repeated pre-event orders define a concentrated exception cohort; hourly, weekday, weather, absolute/relative capacity and order-complexity tables show the observed distribution. The slowest 5.0% of completed orders contain 12.2% of completed-service minutes.

**Why?** The available data do not resolve first assignment, offer compensation, rejection sequences or merchant readiness. Conditional associations and contradictory evidence constrain the hypotheses. No claim that pricing, rain or rider behavior caused the delays is retained.

**What combinations matter?** Review the relative demand/supply comparisons, peak/weather/supply segments and distance/event cohorts with their independent-date support. An absent comparison cell is a support gap, not evidence that the condition has no effect.

**What should management do?** Instrument the initial interval, pilot repeated-event review and evaluate sustained pickup waiting. Verify capacity coverage before changing staffing rules. Monitor completion, late >5 minutes, stage P90, customer service P90/P95 and recorded cost on matching populations.

**What was rejected?** The former incomplete pickup-bottleneck claim, compensation-per-distance causality, assignment of earlier rejections to the final rider, conversion of order delay to labor-hours, guaranteed recoverable savings and a forced capacity threshold.

The resulting diagnosis is coherent within the extract's limits. Unidentified mechanisms are documented as requirements for a future operational test, rather than filled with invented findings.
