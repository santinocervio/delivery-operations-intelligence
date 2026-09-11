# Portfolio Summary

## 40-word project summary

Analyzed 334,144 delivery orders by joining order records, rider shifts, weather and events. Rebuilt operational metrics, decomposed service delays and tested cross-variable hypotheses, producing documented priorities, an interactive dashboard and reproducible validation without claiming causality or inventing unsupported business results.

## 100-word project summary

I analyzed 334,144 delivery orders using order records, rider shifts, weather and events. I corrected mixed timestamp parsing, rebuilt capacity measures and reconciled recorded costs. A complete process decomposition located 51% of the late-order duration difference before final rider notification. Orders with repeated pre events formed a small, concentrated exception cohort. I examined service tails, operational segments, conditional associations and temporal threshold stability, while distinguishing observed patterns from causal explanations. The deliverables include a tested Python pipeline, Streamlit dashboard, Power BI semantic exports and executive recommendations with explicit triggers, trade-offs, monitoring metrics and evidence limitations for practical operational decision making.

## Three CV bullets

- Rebuilt a delivery-operations pipeline for 334,144 orders, reconciling source cost records and recovering 25,052 complete shift records lost by mixed timestamp parsing.
- Decomposed completed delivery timelines and identified 51.0% of the late-versus-on-time duration gap before final rider notification; prioritized an exception cohort containing 36.6% of pre events.
- Delivered operational segmentation, 500-resample date-bootstrap comparisons, conditional statistical models, tested Streamlit reporting and Power BI semantic exports, with documented uncertainty and reproducibility checks.

## Five strongest findings

1. **The main measured deterioration occurs before the final rider notification.** Creation to final notification averages 10.58 minutes. It contributes 6.05 minutes, or 51.0%, of the late-versus-on-time duration difference. Pickup waiting contributes 24.0%. [Evidence](../outputs/analysis/stage_late_contrasts.csv)

2. **A small repeated-pre-event cohort concentrates operational problems.** 10,472 orders with at least four pre events represent 3.1% of orders with known pre counts and 36.6% of recorded pre events. Their completed orders average 45.88 minutes; 67.1% exceed the promise by more than five minutes. [Evidence](../outputs/analysis/headline_contrasts.csv)

3. **Longer recorded delivery distances identify a high-pre-event population.** Orders with recorded dropoff distance above 3 km have 47.9% pre-event incidence, versus 17.3% at 1 km or less. The difference is 30.59 percentage points, with a 95% date-bootstrap interval of 29.49–31.61 points. [Evidence](../outputs/analysis/headline_contrasts.csv)

4. **Pressure alone does not establish a staffing deterioration threshold.** High versus low observed pressure differs by -0.58 percentage points in late >5-minute incidence; the 95% date-bootstrap interval is -2.14 to 1.25 points. The corrected matched-hour throughput is 1.727 orders per observed rider-hour. [Evidence](../outputs/analysis/threshold_assessment.csv)

5. **Recorded extra-record cost is a small accounting exposure.** Reason-bearing records contain 384,517.81 cost units, 0.334% of 115,147,509.10 total recorded cost units. [Evidence](../outputs/analysis/recorded_cost.csv)

## Main bottleneck

Creation to final rider notification: 10.58 minutes on average. The available timestamps do not separate first assignment, scheduling and successive reassignments.

## Most interesting cross-variable insight

The repeated-pre-event cohort combines a small order share (3.1%) with high pre-event concentration (36.6%), long completed service (45.88 minutes) and 67.1% late >5-minute incidence. It defines a concrete exception-review population.

## Most counterintuitive insight

Higher observed orders per rider-hour does not show a reliably worse crude late >5-minute rate in this extract. The date-bootstrap interval spans zero. That challenges a simple capacity narrative; it does not prove that adding riders is harmful or unnecessary.

## Strongest management recommendation

Instrument the initial interval and pilot repeated-pre-event review. Define the trigger, log resolution, compare with similar untreated periods and monitor completion, service tails and recorded cost. Do not promise recovered capacity or savings.

## Technical tools used

Python, pandas, NumPy, openpyxl for source reading, Parquet/PyArrow, statsmodels, date-block bootstrap, pytest, Streamlit, Plotly, Power Query, DAX and TMDL. Native Power BI refresh remains a separate validation requirement.

## Business skills demonstrated

Process reconstruction, KPI definition, source reconciliation, demand/capacity analysis, operational segmentation, hypothesis testing, uncertainty communication, management prioritization and experiment design.

## 30-second interview explanation

I rebuilt a delivery-operations case from four datasets. The first challenge was measurement: repeated order records and timestamp parsing distorted the earlier metrics. I then reconstructed the complete timeline and found that the largest late-order difference occurred before the final rider notification. I proposed a measurable exception-review pilot and clearly separated the observed evidence from causal claims.

## Two-minute interview explanation

The project began as a delivery dashboard, but I treated it as an operational diagnosis. I first established what a row represented, reconciled costs and rebuilt rider-hours from shifts. Mixed timestamp formats had silently removed complete records, which materially distorted capacity measures. I preserved unknown shifts and weather instead of interpreting missing data as actual zero capacity or dry conditions.

Next, I reconstructed an additive order timeline. Merchant acceptance can overlap rider dispatch, so summing an incomplete sequence gives a misleading bottleneck. On a common completed-order cohort, the largest difference between late and punctual orders appears before the final rider notification. That tells management where to investigate; the available data cannot distinguish the internal scheduling and reassignment mechanisms.

I combined service tails, event counts, distance, time of day, demand, observed capacity and weather. Repeated pre events identify a small population with disproportionate operational problems. I used date-level uncertainty and conditional models to avoid treating thousands of orders sharing the same weather as independent observations. I also reserved later dates to check candidate capacity thresholds.

My recommendation is a limited exception-review pilot supported by better dispatch instrumentation. Its success must be measured through completion, time to final notification, service tails and recorded cost. The final work includes reproducible code, automated checks, interactive reporting and an executive brief; it does not turn associations into promised savings.

## Author

Santino Cervio — Industrial Engineering, ITBA.
