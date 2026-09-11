# Executive Business Findings

## Decision for the Head of Operations

Prioritize investigation of the interval before the final rider notification and a monitored exception-review pilot for repeated pre events. Establish reliable capacity observation before changing staffing rules. The evidence supports these diagnostic priorities; it does not establish a causal remedy or savings forecast.

## Study and service baseline

The supplied extract contains **334,144 orders**, including 332,378 completed orders, across 743 calendar hours. Recorded window: 2024-06-30 22:00:00 to 2024-07-31 21:00:00 (exclusive end; source timezone undocumented). Completed service averages 25.72 minutes; P90 is 41.97 and P95 is 49.53. 15.6% of eligible completed orders exceed their recorded promise by more than five minutes. [Evidence](../outputs/analysis/kpis.csv)

## Five findings

1. **The main measured deterioration occurs before the final rider notification.** Creation to final notification averages 10.58 minutes. It contributes 6.05 minutes, or 51.0%, of the late-versus-on-time duration difference. Pickup waiting contributes 24.0%. [Evidence](../outputs/analysis/stage_late_contrasts.csv)

2. **A small repeated-pre-event cohort concentrates operational problems.** 10,472 orders with at least four pre events represent 3.1% of orders with known pre counts and 36.6% of recorded pre events. Their completed orders average 45.88 minutes; 67.1% exceed the promise by more than five minutes. [Evidence](../outputs/analysis/headline_contrasts.csv)

3. **Longer recorded delivery distances identify a high-pre-event population.** Orders with recorded dropoff distance above 3 km have 47.9% pre-event incidence, versus 17.3% at 1 km or less. The difference is 30.59 percentage points, with a 95% date-bootstrap interval of 29.49–31.61 points. [Evidence](../outputs/analysis/headline_contrasts.csv)

4. **Pressure alone does not establish a staffing deterioration threshold.** High versus low observed pressure differs by -0.58 percentage points in late >5-minute incidence; the 95% date-bootstrap interval is -2.14 to 1.25 points. The corrected matched-hour throughput is 1.727 orders per observed rider-hour. [Evidence](../outputs/analysis/threshold_assessment.csv)

5. **Recorded extra-record cost is a small accounting exposure.** Reason-bearing records contain 384,517.81 cost units, 0.334% of 115,147,509.10 total recorded cost units. [Evidence](../outputs/analysis/recorded_cost.csv)

## Actions, trade-offs and monitoring

- **Dispatch/operations:** review orders after four recorded pre events; record first-dispatch and reassignment timestamps. Monitor P90 creation-to-final-notification, completion and late >5 minutes. A manual review adds effort and may escalate too early; measure it in a limited pilot.
- **Workforce/data operations:** correct timestamp parsing and investigate missing shift dates. Monitor orders and rider-hours on matching hours, date/hour coverage and service P90/P95. Additional staffing can lower output per recorded hour; a cost benefit is unproven.
- **Merchant operations:** investigate sustained pickup waiting in adequately supported merchant cohorts. Monitor pickup-wait P90 and customer service together; later rider arrival can hurt service when readiness estimates are wrong.

The initial operational interval is the main measured bottleneck. Its internal mechanism remains unobserved. Rain covers one recorded episode and cannot establish a general weather effect. No rider is identified as responsible for earlier rejections, and no customer delay is converted into labor-hours or additional delivery capacity.
