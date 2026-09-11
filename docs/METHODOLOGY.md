# Analytical Framework and Metric Contracts

## Populations and grains

- Source cost/reason records: preserve row lineage; repeated final-rider timestamps are not independent dispatch events.
- Orders: exactly one principal source row per ID, joined to all recorded costs. Ambiguous principal rows fail validation.
- Rider-hours: union positive dated shift intervals by rider, clip to the observed window, allocate fractional hours and prevent overlap double-counting. Positive shifts longer than 16 hours are retained and sensitivity is reported.
- Calendar hours: every hour from the first observed order hour through the last. No recorded orders is distinct from unknown actual demand. Missing supply is not measured zero supply.

## KPIs

Service distributions use completed orders with finite nonnegative declared durations. Late incidence additionally requires a valid declared promise; flags are unknown outside this cohort. Report strict positive delay and >5-minute/>15-minute tolerances separately. Pre/post incidence divides affected orders by orders with the corresponding known counter. Event totals count repetitions. CPO is total recorded order cost divided by orders with known cost; currency and full accounting coverage are unverified.

Throughput is orders in hours with observed supply divided by the observed rider-hours in those same hours. Zero-demand supply hours are retained. Order-specific filters cannot allocate shared city-wide capacity, so the dashboard suppresses the ratio for those selections. It does not measure busy-time utilization.

## Segmentation and inference

Full-period demand, observed supply and pressure tertiles retain ties. Relative demand/supply tertiles are computed within clock hour to distinguish unusual conditions from predictable daily seasonality. Peak hours are the top quartile of clock-hour mean recorded demand. These are descriptive definitions; a high ratio is not a validated capacity shortage.

All groups remain visible with order, hour and date support. The reporting defaults require 100 orders across five dates for a supported descriptive comparison; inference requires each group to have at least 100 orders, 30 hours and ten dates. These cutoffs are transparent reporting rules, not guarantees of identification.

Headline contrasts use 500 resamples of complete dates with a fixed seed and percentile 95% intervals. Repeated rows from the same date remain together. Serial dependence across dates, observational confounding and the short study period limit generalization. Exploratory comparisons are not a controlled multiple-testing discovery exercise.

Grouped binomial models estimate pre incidence, post incidence and late >5-minute incidence with clock-hour, weekday, vertical and recorded dropoff-distance controls. Demand and observed supply enter separately; supported interactions are checked before estimation. Report convergence, design rank, analyzed orders and date-clustered uncertainty. Odds ratios are not probability changes. Weather lacks sufficient independent support and is not ranked against staffing. Offer compensation, physical parcel size and rejecting rider identities are unobserved.

Capacity threshold exploration uses discovery dates before the last ten complete dates. Confirmation uses only those final dates with the same support rule. Descriptive quantile boundaries are not operational trigger estimates. If an eligible, stable deterioration is absent, the correct result is no validated threshold.

## How findings become actions

Each major finding records observation, numeric evidence, interpretation, action and limitation. The priority matrix shows frequency, measured burden and controllability without fabricating avoided costs. Overlapping cohorts cannot be added together as benefits. Four pre events and observed stage P90 cutoffs identify diagnostic cohorts, not optimized intervention policies.

## Reproducibility

The manifest records source SHA-256 hashes, schema version, observed window, seed and segmentation boundaries. Independent source reconciliations, synthetic edge cases, actual-data interface checks and repeated complete builds validate different failure modes. Generated result tables are the numeric source for documentation; no external benchmark or generated business data enters the analysis.
