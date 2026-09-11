# Business Insights

Ranked from strongest operational diagnosis to descriptive limitations. Every effect below is observational.

## F01 — The main measured deterioration occurs before the final rider notification

### Insight
Creation to final notification averages 10.58 minutes. It contributes 6.05 minutes, or 51.0%, of the late-versus-on-time duration difference. Pickup waiting contributes 24.0%.

### Evidence
[Evidence](../outputs/analysis/stage_late_contrasts.csv) Machine-readable values are also recorded under `F01` in [the findings register](../outputs/executive_findings.json).

### Why it matters
The complete timeline changes where management should investigate first. The initial interval may contain scheduling, merchant coordination and earlier assignment attempts; its components are not separately observed.

### Possible explanation
A time decomposition identifies where time accrues; it does not identify a causal dispatch mechanism.

### Recommended operational action
Capture first-dispatch, offer, acceptance and reassignment timestamps. Review long initial intervals before choosing a dispatch intervention.

### Confidence / limitation
Strong descriptive evidence. A time decomposition identifies where time accrues; it does not identify a causal dispatch mechanism.

## F02 — A small repeated-pre-event cohort concentrates operational problems

### Insight
10,472 orders with at least four pre events represent 3.1% of orders with known pre counts and 36.6% of recorded pre events. Their completed orders average 45.88 minutes; 67.1% exceed the promise by more than five minutes.

### Evidence
[Evidence](../outputs/analysis/headline_contrasts.csv) Machine-readable values are also recorded under `F02` in [the findings register](../outputs/executive_findings.json).

### Why it matters
The observed service gap is 20.81 minutes (95% date-bootstrap interval 19.98–21.75). This is an exception cohort worth reviewing, not a measured preventable loss.

### Possible explanation
Four is a diagnostic grouping, not an optimized trigger. Final-state counters do not reveal attempt order, offer compensation or rejecting rider identity.

### Recommended operational action
Pilot review after four recorded pre events, checking unresolved assignment and merchant readiness. Track time to final notification, completion, late >5 minutes and recorded cost per reviewed order.

### Confidence / limitation
Strong concentration evidence; pilot effect untested. Four is a diagnostic grouping, not an optimized trigger. Final-state counters do not reveal attempt order, offer compensation or rejecting rider identity.

## F03 — Longer recorded delivery distances identify a high-pre-event population

### Insight
Orders with recorded dropoff distance above 3 km have 47.9% pre-event incidence, versus 17.3% at 1 km or less. The difference is 30.59 percentage points, with a 95% date-bootstrap interval of 29.49–31.61 points.

### Evidence
[Evidence](../outputs/analysis/headline_contrasts.csv) Machine-readable values are also recorded under `F03` in [the findings register](../outputs/executive_findings.json).

### Why it matters
Distance adds an order-complexity dimension to the exception review. The association does not establish insufficient compensation: final recorded cost is not the offered payment and other route characteristics can differ.

### Possible explanation
Distance units follow the project's metre interpretation; route and offer-level evidence is incomplete. This supports targeted investigation rather than a causal price recommendation.

### Recommended operational action
Review long-distance offers by service vertical and clock hour, logging offered compensation, assignment sequence and time to final notification. Test an assignment-policy change with pre incidence, service tails and recorded cost guardrails.

### Confidence / limitation
Strong descriptive association; pricing mechanism untested. Distance units follow the project's metre interpretation; route and offer-level evidence is incomplete. This supports targeted investigation rather than a causal price recommendation.

## F04 — Pressure alone does not establish a staffing deterioration threshold

### Insight
High versus low observed pressure differs by -0.58 percentage points in late >5-minute incidence; the 95% date-bootstrap interval is -2.14 to 1.25 points. The corrected matched-hour throughput is 1.727 orders per observed rider-hour.

### Evidence
[Evidence](../outputs/analysis/threshold_assessment.csv) Machine-readable values are also recorded under `F04` in [the findings register](../outputs/executive_findings.json).

### Why it matters
The crude pressure comparison does not support a simple claim that more orders per recorded rider-hour necessarily worsens service. Demand, hour, order mix and reactive staffing can confound the relationship.

### Possible explanation
Missing shifts are not actual zero capacity; the ratio does not measure busy time or a capacity limit. Check held-out threshold results separately.

### Recommended operational action
Repair and monitor shift coverage; use the same-hour relative demand/supply comparisons and conditional models before prospectively testing scheduling changes.

### Confidence / limitation
Exploratory association with measured coverage limitations. Missing shifts are not actual zero capacity; the ratio does not measure busy time or a capacity limit. Check held-out threshold results separately.

## F05 — Recorded extra-record cost is a small accounting exposure

### Insight
Reason-bearing records contain 384,517.81 cost units, 0.334% of 115,147,509.10 total recorded cost units.

### Evidence
[Evidence](../outputs/analysis/recorded_cost.csv) Machine-readable values are also recorded under `F05` in [the findings register](../outputs/executive_findings.json).

### Why it matters
The much larger CPO differences between difficult and ordinary orders cannot simply be booked as savings from removing these extra records. Cost, distance and service complexity vary together.

### Possible explanation
Currency and cost completeness are undocumented. Recorded exposure is not guaranteed recoverable savings or an upper bound on total economic harm.

### Recommended operational action
Keep recorded cost components separate when evaluating an exception pilot. Obtain offer compensation and complete cost definitions before testing a pricing policy.

### Confidence / limitation
Strong reconciliation; economic mechanism unverified. Currency and cost completeness are undocumented. Recorded exposure is not guaranteed recoverable savings or an upper bound on total economic harm.

## F06 — The rainfall evidence is one episode, not thousands of independent tests

### Insight
The Rain category contains 2,010 orders across 3 hours and 1 recorded date. All positive precipitation, including drizzle, covers 44 hours on 5 dates.

### Evidence
[Evidence](../outputs/analysis/weather_support.csv) Machine-readable values are also recorded under `F06` in [the findings register](../outputs/executive_findings.json).

### Why it matters
Rain, peak demand and supply can be compared descriptively, but this window cannot establish a general rain effect or rank weather against staffing as an explanation.

### Possible explanation
Shared hourly weather does not become independent when joined to many orders.

### Recommended operational action
Collect more independent wet days, matched dry periods and complete rider coverage. Monitor the existing episode without adopting an inferred weather surcharge.

### Confidence / limitation
Strong evidence about sample support; weather effect unresolved. Shared hourly weather does not become independent when joined to many orders.

## Distribution and cross-variable evidence

The slowest observed service tail exceeds 49.53 minutes. 16,606 completed orders (5.0%) contain 12.2% of total completed-service minutes; their mean is 62.76 minutes. This distinguishes tail concentration from a uniform shift. [Evidence](../outputs/analysis/tail_segments.csv)

[Operational segments](../outputs/analysis/operational_segments.csv) include weather × hour, weather × demand/supply, weekday × hour, peak × weather × supply, order type/distance and relative demand/supply where available. [Process stages by segment](../outputs/analysis/stage_by_segment.csv) identify whether the largest stage changes. Small groups remain visible, with counts and dates.

## Tested hypotheses

| hypothesis | supporting_evidence | contradicting_or_limiting_evidence | conclusion | strength |
|---|---|---|---|---|
| Demand/capacity mismatch is associated with pre-undispatch | {"global_high_demand_pre": {"comparison": "High demand: low versus high observed supply, pre incidence", "difference": null, "ci_low": null, "ci_high": null, "exposed_orders": 0, "reference_orders": 211435, "exposed_dates": 0, "reference_dates": 31, "inference_eligible": false}, "global_high_demand_late5": {"comparison": "High demand: low versus high observed supply, late >5min", "difference": null, "ci_low": null, "ci_high": null, "exposed_orders": 0, "reference_orders": 210367, "exposed_dates": 0, "reference_dates": 31, "inference_eligible": false}, "within_clock_pre": {"comparison": "Within-clock high demand: low versus high supply, pre incidence", "difference": -0.007419632276929211, "ci_low": null, "ci_high": null, "exposed_orders": 3177, "reference_orders": 98612, "exposed_dates": 5, "reference_dates": 23, "inference_eligible": false}, "within_clock_late5": {"comparison": "Within-clock high demand: low versus high supply, late >5min", "difference": -0.012261140353471756, "ci_low": null, "ci_high": null, "exposed_orders": 3170, "reference_orders": 98120, "exposed_dates": 5, "reference_dates": 23, "inference_eligible": false}, "within_clock_tail95": {"comparison": "Within-clock high demand: low versus high supply, P95-tail incidence", "difference": -0.010785833608753074, "ci_low": null, "ci_high": null, "exposed_orders": 3170, "reference_orders": 98120, "exposed_dates": 5, "reference_dates": 23, "inference_eligible": false}} | Global demand/supply bands may have no opposite-cell overlap. Within-clock bands restore some comparisons but use full-sample descriptive tertiles; supply is incomplete and scheduling may respond to demand. | Independent support for the within-clock high-demand comparison is insufficient; a mismatch mechanism is unproven. | Insufficient support |
| Weather relates to recorded cost through longer service time | {"service_difference": {"comparison": "Observed wet versus dry hours: service", "difference": 2.761179992900761, "ci_low": null, "ci_high": null, "exposed_orders": 22723, "reference_orders": 288595, "exposed_dates": 5, "reference_dates": 32, "inference_eligible": false}, "recorded_cost_difference": {"comparison": "Observed wet versus dry hours: recorded cost", "difference": 73.57582770053517, "ci_low": null, "ci_high": null, "exposed_orders": 22860, "reference_orders": 290118, "exposed_dates": 5, "reference_dates": 32, "inference_eligible": false}} | Only 5 wet dates and 44 wet hours. Final recorded cost and service time do not identify a mediation mechanism; monetary units are unverified. | Wet/dry differences are descriptive. Neither a general weather effect nor cost mediation is established. | Limited independent weather exposure |
| Low throughput reflects excess observed capacity during low demand | {"low_demand_profiles": [{"segmentation": "global", "supply_band": "Low", "hours": 183, "dates": 32, "orders": 6998, "observed_rider_hours": 5327.555958611111, "orders_per_observed_rider_hour": 1.3135479109682353}, {"segmentation": "global", "supply_band": "High", "hours": 0, "dates": 0, "orders": 0, "observed_rider_hours": null, "orders_per_observed_rider_hour": null}, {"segmentation": "within_clock", "supply_band": "Low", "hours": 171, "dates": 27, "orders": 61396, "observed_rider_hours": 36345.66560194445, "orders_per_observed_rider_hour": 1.6892248080529138}, {"segmentation": "within_clock", "supply_band": "High", "hours": 22, "dates": 13, "orders": 5823, "observed_rider_hours": 5867.251083333334, "orders_per_observed_rider_hour": 0.9924579530166974}], "global_cost": {"comparison": "Low demand: high versus low observed supply, recorded cost", "difference": null, "ci_low": null, "ci_high": null, "exposed_orders": 0, "reference_orders": 6998, "exposed_dates": 0, "reference_dates": 32, "inference_eligible": false}, "global_late5": {"comparison": "Low demand: high versus low observed supply, late >5min", "difference": null, "ci_low": null, "ci_high": null, "exposed_orders": 0, "reference_orders": 6909, "exposed_dates": 0, "reference_dates": 32, "inference_eligible": false}, "within_clock_cost": {"comparison": "Within-clock low demand: high versus low supply, recorded cost", "difference": 236.68119378125834, "ci_low": null, "ci_high": null, "exposed_orders": 5823, "reference_orders": 61396, "exposed_dates": 8, "reference_dates": 25, "inference_eligible": false}, "within_clock_late5": {"comparison": "Within-clock low demand: high versus low supply, late >5min", "difference": 0.05325549575127389, "ci_low": null, "ci_high": null, "exposed_orders": 5788, "reference_orders": 61052, "exposed_dates": 8, "reference_dates": 25, "inference_eligible": false}, "supply_hours_without_orders": 53} | A low orders/hour ratio follows mechanically from low demand or more recorded hours. Standby requirements, true busy time and staffing overhead costs are unavailable. | Identify low-throughput periods for schedule review; actual overstaffing, utilization and avoidable cost remain unmeasured. | Descriptive capacity proxy |
| Weather combined with peak demand worsens service and its upper tail | {"peak_service": {"comparison": "Peak hours: observed wet versus dry service", "difference": 2.7443388287922836, "ci_low": null, "ci_high": null, "exposed_orders": 13729, "reference_orders": 165963, "exposed_dates": 5, "reference_dates": 32, "inference_eligible": false}, "nonpeak_service": {"comparison": "Non-peak hours: observed wet versus dry service", "difference": 2.564089156556939, "ci_low": null, "ci_high": null, "exposed_orders": 8994, "reference_orders": 122632, "exposed_dates": 4, "reference_dates": 32, "inference_eligible": false}, "peak_p95_tail": {"comparison": "Peak hours: observed wet versus dry P95-tail incidence", "difference": 0.03046299205597844, "ci_low": null, "ci_high": null, "exposed_orders": 13729, "reference_orders": 165963, "exposed_dates": 5, "reference_dates": 32, "inference_eligible": false}} | The same weather dates supply many correlated orders. Separate peak/nonpeak differences do not prove an interaction; independent support is required in every comparison. | Combined conditions are described; no reproducible weather-by-peak effect is established in sparse exposure. | Insufficient interaction support |
| Staffing explains more performance variation than weather | {"staffing_associations": [{"model": "pre_any", "term": "log_hour_orders", "coefficient": -0.46609916414208485, "odds_ratio": 0.7239193256346839, "ci_low": 0.6256091756823526, "ci_high": 0.8376782349072543}, {"model": "pre_any", "term": "log_observed_rider_hours", "coefficient": 0.09270967117225926, "odds_ratio": 1.0663711620560672, "ci_low": 0.9391021800499284, "ci_high": 1.2108878878380938}, {"model": "pre_any", "term": "demand_supply_interaction", "coefficient": 0.0005132028908537145, "odds_ratio": 1.0005133346019879, "ci_low": 0.9161888084557479, "ci_high": 1.0925989528333548}, {"model": "post_any", "term": "log_hour_orders", "coefficient": -0.7659115414542499, "odds_ratio": 0.588081682145832, "ci_low": 0.5003128700605814, "ci_high": 0.691247588401223}, {"model": "post_any", "term": "log_observed_rider_hours", "coefficient": 0.7270396010243451, "odds_ratio": 1.655239066750063, "ci_low": 1.2037232157023061, "ci_high": 2.27611824076774}, {"model": "post_any", "term": "demand_supply_interaction", "coefficient": 0.09569280498168004, "odds_ratio": 1.100420968226476, "ci_low": 1.019756676002237, "ci_high": 1.187465927714935}, {"model": "_late5", "term": "log_hour_orders", "coefficient": -0.9934611311870911, "odds_ratio": 0.5022713426676095, "ci_low": 0.40676930334203304, "ci_high": 0.6201955250615258}, {"model": "_late5", "term": "log_observed_rider_hours", "coefficient": 0.7034727772267756, "odds_ratio": 1.6284199227633156, "ci_low": 1.2481130425266365, "ci_high": 2.1246083924292387}, {"model": "_late5", "term": "demand_supply_interaction", "coefficient": 0.03141745636874563, "odds_ratio": 1.0319161939702934, "ci_low": 0.9512230941205507, "ci_high": 1.1194545611433455}], "wet_dates": 5, "wet_hours": 44, "weather_inference_eligible": false} | Coefficient magnitudes on different scales are not explanatory importance. Sparse weather exposure prevents a fair head-to-head model comparison; no prediction experiment is claimed. | Staffing associations can be examined where estimable; relative staffing-versus-weather importance is not identified. | Relative-importance claim unsupported |
| Long dropoff distance is associated with pre-event incidence | {"comparison": "Dropoff distance >3km versus <=1km: pre incidence", "difference": 0.30593931696942067, "ci_low": 0.2948558933723757, "ci_high": 0.31607347203470265, "exposed_orders": 25562, "reference_orders": 148201, "exposed_dates": 32, "reference_dates": 32, "inference_eligible": true} | Offer-level payment and rejected-assignment history are unavailable. Recorded cost per kilometre cannot establish an incentive mechanism. | Evaluate the measured distance association; pricing mechanism remains untested. | Association only |
| Final-rider pickup waiting is the dominant measured stage | {"stages": [{"stage": "t_created_to_notify_min", "label": "Creation to final rider notification", "position": 1, "orders": 332378, "mean_min": 10.583951833054835, "median_min": 7.44737135, "p75_min": 15.054142841666666, "p90_min": 23.92657995333333, "p95_min": 30.670991565, "variance_min2": 123.00270621641091, "share_total_time": 0.41129504254300103, "total_mean_min": 25.73323463277163}, {"stage": "t_notify_to_accept_min", "label": "Final rider notification to acceptance", "position": 2, "orders": 332378, "mean_min": 0.2458187923857776, "median_min": 0.164721825, "p75_min": 0.30951157500000004, "p90_min": 0.5371326716666666, "p95_min": 0.7787050466666665, "variance_min2": 0.07620344806187294, "share_total_time": 0.009552580384617641, "total_mean_min": 25.73323463277163}, {"stage": "t_accept_to_pu_arrival_min", "label": "Final rider approach to merchant", "position": 3, "orders": 332378, "mean_min": 3.133853886551456, "median_min": 2.7260066666666667, "p75_min": 4.542476104166667, "p90_min": 6.597775978333334, "p95_min": 8.145094656666657, "variance_min2": 7.8342340402934765, "share_total_time": 0.12178235388101773, "total_mean_min": 25.73323463277163}, {"stage": "t_wait_at_pu_min", "label": "Final rider waiting at pickup", "position": 4, "orders": 332378, "mean_min": 4.600734930120526, "median_min": 3.309641666666667, "p75_min": 6.0474873375, "p90_min": 9.815682968333334, "p95_min": 12.77167511833333, "variance_min2": 17.67690741141509, "share_total_time": 0.17878572187972927, "total_mean_min": 25.73323463277163}, {"stage": "t_last_mile_min", "label": "Pickup to destination arrival", "position": 5, "orders": 332378, "mean_min": 7.168875190659029, "median_min": 6.384646, "p75_min": 9.241086870833332, "p90_min": 12.558203813333332, "p95_min": 15.000190701666668, "variance_min2": 18.49141312032456, "share_total_time": 0.2785843013116341, "total_mean_min": 25.73323463277163}], "late_gaps": [{"stage": "t_created_to_notify_min", "label": "Creation to final rider notification", "late_orders": 116927, "on_time_orders": 215451, "late_mean_min": 14.507968645088816, "on_time_mean_min": 8.454356176591428, "difference_min": 6.053612468497388, "share_of_total_difference": 0.5097087259420433, "total_difference_min": 11.87661140646377}, {"stage": "t_notify_to_accept_min", "label": "Final rider notification to acceptance", "late_orders": 116927, "on_time_orders": 215451, "late_mean_min": 0.278001504539442, "on_time_mean_min": 0.22835297424619366, "difference_min": 0.04964853029324834, "share_of_total_difference": 0.0041803616026560774, "total_difference_min": 11.87661140646377}, {"stage": "t_accept_to_pu_arrival_min", "label": "Final rider approach to merchant", "late_orders": 116927, "on_time_orders": 215451, "late_mean_min": 3.8298315708272397, "on_time_mean_min": 2.756141169092199, "difference_min": 1.0736904017350408, "share_of_total_difference": 0.09040376627551287, "total_difference_min": 11.87661140646377}, {"stage": "t_wait_at_pu_min", "label": "Final rider waiting at pickup", "late_orders": 116927, "on_time_orders": 215451, "late_mean_min": 6.447193847649245, "on_time_mean_min": 3.5986467437121044, "difference_min": 2.848547103937141, "share_of_total_difference": 0.23984510450403704, "total_difference_min": 11.87661140646377}, {"stage": "t_last_mile_min", "label": "Pickup to destination arrival", "late_orders": 116927, "on_time_orders": 215451, "late_mean_min": 8.368786514058915, "on_time_mean_min": 6.517673612057962, "difference_min": 1.8511129020009527, "share_of_total_difference": 0.15586204167575074, "total_difference_min": 11.87661140646377}]} | The earlier incomplete decomposition omitted the initial interval. Components describe the final recorded timeline, not the causes of each interval. | Largest measured stage: Creation to final rider notification. | Direct descriptive decomposition |
| Repeated pre events mark an operational exception cohort | {"service": {"comparison": "At least four pre events versus fewer", "difference": 20.805428701600214, "ci_low": 19.979693340801607, "ci_high": 21.75169747277198, "exposed_orders": 10376, "reference_orders": 321996, "exposed_dates": 32, "reference_dates": 32, "inference_eligible": true}, "cost": {"comparison": "At least four pre events versus fewer: recorded cost", "difference": 698.2789761327188, "ci_low": 670.7408515761022, "ci_high": 730.3115412925158, "exposed_orders": 10472, "reference_orders": 323666, "exposed_dates": 32, "reference_dates": 32, "inference_eligible": true}} | An observational final-counter cohort does not establish preventability or an optimal intervention trigger. | Use the observed cohort for diagnosis and a monitored pilot; do not book estimated savings. | Descriptive concentration |

## Management prioritization

| priority | issue | affected_orders | affected_late5_orders | affected_share | controllability | action | monitoring_kpi | trade_off |
|---|---|---|---|---|---|---|---|---|
| 1 | Long initial interval | 33238 | 16163.0 | 0.09947208389197472 | Moderate: operational escalation can be tested; missing assignment history limits diagnosis. | Instrument first dispatch and reassignment; review high-delay orders before testing an escalation workflow. | P90 creation-to-final-notification, late >5min, completion, recorded cost per reviewed order | Premature escalation and manual review add effort; validate a small pilot. |
| 2 | Pickup waiting tail | 33238 | 15417.0 | 0.09947208389197472 | Shared: merchant readiness and arrival coordination require joint action. | Review merchant readiness and rider arrival coordination in supported merchant cohorts. | Pickup wait P90, service P90, late >5min, completion | Later rider arrival can reduce waiting but delay delivery if readiness is misestimated. |
| 3 | Repeated pre events | 10472 | 6958.0 | 0.03133978165102471 | Moderate: dispatch policy is testable; rider offer decisions are unobserved. | Pilot exception review and capture why repeated assignments fail. | Time to final notification, pre-event count, completion, late >5min, recorded cost | Intervention can increase incentives or manual work; measure the trade-off. |
| 4 | High within-clock demand with low observed supply | 3177 | 424.0 | 0.009507876843516568 | Conditional: schedules can change, but actual capacity and coverage must be verified first. | Audit supply coverage and order mix before piloting a schedule adjustment in repeated problem windows. | Supply coverage, pressure proxy, service P95, late >5min, completion | More scheduled hours can reduce throughput per observed hour; no savings are assumed. |
| 5 | Missing hourly supply observations | 9 | 5.0 | 2.6934495307412374e-05 | High for data capture; missing observation does not mean no riders. | Repair missing shift observations and monitor join coverage before interpreting capacity metrics. | Observed-supply coverage of order hours and orders | Capture quality is an enabling investment with unquantified financial benefit. |

Exposure cohorts overlap and their costs/minutes cannot be summed as savings. The priority matrix records frequency and measured burden alongside controllability; its decision sequence is documented in the source table. [Full matrix](../outputs/analysis/priorities.csv).
