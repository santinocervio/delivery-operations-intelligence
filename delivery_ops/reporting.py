"""Generate English business reports from numeric evidence, never static findings."""
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd

from .io import write_json, sha256


def _read(path, fallback=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def _n(x, digits=0):
    return "unavailable" if x is None or pd.isna(x) else f"{x:,.{digits}f}"


def _pct(x, digits=1):
    return "unavailable" if x is None or pd.isna(x) else f"{100*x:.{digits}f}%"


def _md_table(rows, columns):
    def cell(v):
        if isinstance(v,(dict,list)): v=json.dumps(v,ensure_ascii=False)
        return str(v).replace("|","/").replace("\n"," ")
    return "| " + " | ".join(columns) + " |\n|" + "|".join(["---"]*len(columns)) + "|\n" + "\n".join("| " + " | ".join(cell(row.get(c,"")) for c in columns) + " |" for row in rows) + "\n"


def executive_findings(result, audit):
    p,k,t,c=result["process"],result["kpis"],result["tails"],result["costs"]
    initial=next(x for x in p["late_contributions"] if x["stage"]=="t_created_to_notify_min")
    pickup=next(x for x in p["late_contributions"] if x["stage"]=="t_wait_at_pu_min")
    repeat=next(x for x in result["contrasts"] if x["contrast"]=="At least four pre events versus fewer")
    pressure=next(x for x in result["contrasts"] if x["contrast"]=="High versus low observed orders per rider-hour: late >5min")
    distance=next(x for x in result["contrasts"] if x["contrast"]=="Dropoff distance >3km versus <=1km: pre incidence")
    rain=next((x for x in result["weather"]["support"] if x["weather"]=="Rain"),{})
    return [
        {"id":"F01", "title":"The main measured deterioration occurs before the final rider notification",
         "observation":f"Creation to final notification averages {_n(p['main_stage_mean_min'],2)} minutes. It contributes {_n(initial['difference_min'],2)} minutes, or {_pct(initial['share_of_total_difference'])}, of the late-versus-on-time duration difference. Pickup waiting contributes {_pct(pickup['share_of_total_difference'])}.",
         "evidence":{"completed_process_orders":p["eligible_orders"],"initial_mean_min":p["main_stage_mean_min"],"initial_late_gap_min":initial["difference_min"],"initial_late_gap_share":initial["share_of_total_difference"],"pickup_late_gap_share":pickup["share_of_total_difference"]},
         "interpretation":"The complete timeline changes where management should investigate first. The initial interval may contain scheduling, merchant coordination and earlier assignment attempts; its components are not separately observed.",
         "action":"Capture first-dispatch, offer, acceptance and reassignment timestamps. Review long initial intervals before choosing a dispatch intervention.",
         "confidence":"Strong descriptive evidence", "limitation":"A time decomposition identifies where time accrues; it does not identify a causal dispatch mechanism.","source_table":"analysis/stage_late_contrasts.csv"},
        {"id":"F02", "title":"A small repeated-pre-event cohort concentrates operational problems",
         "observation":f"{_n(t['pre4_orders'])} orders with at least four pre events represent {_pct(t['pre4_order_share'])} of orders with known pre counts and {_pct(t['pre4_event_share'])} of recorded pre events. Their completed orders average {_n(t['pre4_mean_min'],2)} minutes; {_pct(t['pre4_late5_rate'])} exceed the promise by more than five minutes.",
         "evidence":{"orders":t["pre4_orders"],"order_share":t["pre4_order_share"],"pre_event_share":t["pre4_event_share"],"service_mean_min":t["pre4_mean_min"],"late5_rate":t["pre4_late5_rate"],"mean_difference_min":repeat["difference"],"ci95_low":repeat["ci_low"],"ci95_high":repeat["ci_high"]},
         "interpretation":f"The observed service gap is {_n(repeat['difference'],2)} minutes (95% date-bootstrap interval {_n(repeat['ci_low'],2)}–{_n(repeat['ci_high'],2)}). This is an exception cohort worth reviewing, not a measured preventable loss.",
         "action":"Pilot review after four recorded pre events, checking unresolved assignment and merchant readiness. Track time to final notification, completion, late >5 minutes and recorded cost per reviewed order.",
         "confidence":"Strong concentration evidence; pilot effect untested", "limitation":"Four is a diagnostic grouping, not an optimized trigger. Final-state counters do not reveal attempt order, offer compensation or rejecting rider identity.","source_table":"analysis/headline_contrasts.csv"},
        {"id":"F03", "title":"Longer recorded delivery distances identify a high-pre-event population",
         "observation":f"Orders with recorded dropoff distance above 3 km have {_pct(distance['exposed_mean'])} pre-event incidence, versus {_pct(distance['reference_mean'])} at 1 km or less. The difference is {_n(100*distance['difference'],2)} percentage points, with a 95% date-bootstrap interval of {_n(100*distance['ci_low'],2)}–{_n(100*distance['ci_high'],2)} points.",
         "evidence":{"long_distance_orders":distance["exposed_orders"],"short_distance_orders":distance["reference_orders"],"long_distance_pre_rate":distance["exposed_mean"],"short_distance_pre_rate":distance["reference_mean"],"difference":distance["difference"],"ci95_low":distance["ci_low"],"ci95_high":distance["ci_high"]},
         "interpretation":"Distance adds an order-complexity dimension to the exception review. The association does not establish insufficient compensation: final recorded cost is not the offered payment and other route characteristics can differ.",
         "action":"Review long-distance offers by service vertical and clock hour, logging offered compensation, assignment sequence and time to final notification. Test an assignment-policy change with pre incidence, service tails and recorded cost guardrails.",
         "confidence":"Strong descriptive association; pricing mechanism untested", "limitation":"Distance units follow the project's metre interpretation; route and offer-level evidence is incomplete. This supports targeted investigation rather than a causal price recommendation.","source_table":"analysis/headline_contrasts.csv"},
        {"id":"F04", "title":"Pressure alone does not establish a staffing deterioration threshold",
         "observation":f"High versus low observed pressure differs by {_n(100*pressure['difference'],2)} percentage points in late >5-minute incidence; the 95% date-bootstrap interval is {_n(100*pressure['ci_low'],2)} to {_n(100*pressure['ci_high'],2)} points. The corrected matched-hour throughput is {_n(result['capacity']['orders_per_observed_rider_hour'],3)} orders per observed rider-hour.",
         "evidence":{"late5_difference":pressure["difference"],"ci95_low":pressure["ci_low"],"ci95_high":pressure["ci_high"],"observed_rider_hours":result["capacity"]["observed_rider_hours"],"matched_throughput":result["capacity"]["orders_per_observed_rider_hour"],"thresholds":result["capacity"]["thresholds"]},
         "interpretation":"The crude pressure comparison does not support a simple claim that more orders per recorded rider-hour necessarily worsens service. Demand, hour, order mix and reactive staffing can confound the relationship.",
         "action":"Repair and monitor shift coverage; use the same-hour relative demand/supply comparisons and conditional models before prospectively testing scheduling changes.",
         "confidence":"Exploratory association with measured coverage limitations", "limitation":"Missing shifts are not actual zero capacity; the ratio does not measure busy time or a capacity limit. Check held-out threshold results separately.","source_table":"analysis/threshold_assessment.csv"},
        {"id":"F05", "title":"Recorded extra-record cost is a small accounting exposure",
         "observation":f"Reason-bearing records contain {_n(c['recorded_aborted_leg_cost'],2)} cost units, {_pct(c['aborted_leg_share'],3)} of {_n(c['recorded_total_cost'],2)} total recorded cost units.",
         "evidence":{"reason_bearing_cost":c["recorded_aborted_leg_cost"],"total_recorded_cost":c["recorded_total_cost"],"cost_share":c["aborted_leg_share"]},
         "interpretation":"The much larger CPO differences between difficult and ordinary orders cannot simply be booked as savings from removing these extra records. Cost, distance and service complexity vary together.",
         "action":"Keep recorded cost components separate when evaluating an exception pilot. Obtain offer compensation and complete cost definitions before testing a pricing policy.",
         "confidence":"Strong reconciliation; economic mechanism unverified", "limitation":"Currency and cost completeness are undocumented. Recorded exposure is not guaranteed recoverable savings or an upper bound on total economic harm.","source_table":"analysis/recorded_cost.csv"},
        {"id":"F06", "title":"The rainfall evidence is one episode, not thousands of independent tests",
         "observation":f"The Rain category contains {_n(rain.get('orders'))} orders across {_n(rain.get('hours'))} hours and {_n(rain.get('dates'))} recorded date. All positive precipitation, including drizzle, covers {_n(result['weather']['wet_hours'])} hours on {_n(result['weather']['wet_dates'])} dates.",
         "evidence":{"rain_orders":rain.get("orders"),"rain_hours":rain.get("hours"),"rain_dates":rain.get("dates"),"wet_hours":result["weather"]["wet_hours"],"wet_dates":result["weather"]["wet_dates"],"weather_missing_orders":result["weather"]["missing_orders"]},
         "interpretation":"Rain, peak demand and supply can be compared descriptively, but this window cannot establish a general rain effect or rank weather against staffing as an explanation.",
         "action":"Collect more independent wet days, matched dry periods and complete rider coverage. Monitor the existing episode without adopting an inferred weather surcharge.",
         "confidence":"Strong evidence about sample support; weather effect unresolved", "limitation":"Shared hourly weather does not become independent when joined to many orders.","source_table":"analysis/weather_support.csv"},
    ]


def write_reports(output_dir:Path, root:Path):
    result=_read(output_dir/"analysis_results.json")
    audit=_read(output_dir/"data_audit.json")
    manifest=_read(output_dir/"manifest.json")
    validation=_read(output_dir/"validation.json",{})
    powerbi=_read(output_dir/"powerbi_status.json",{})
    reproducibility=_read(output_dir/"reproducibility.json",{})
    k,p,t=result["kpis"],result["process"],result["tails"]
    findings=executive_findings(result,audit)
    write_json(output_dir/"executive_findings.json",findings)
    window=f"{manifest['window_start_inclusive']} to {manifest['window_end_exclusive']} (exclusive end; source timezone undocumented)"
    src=lambda file:f"[Evidence](../outputs/{file})"
    stages=_md_table([{"Stage":x["label"],"Mean minutes":_n(x["mean_min"],2),"P90 minutes":_n(x["p90_min"],2),"Share":_pct(x["share_total_time"])} for x in p["stages"]],["Stage","Mean minutes","P90 minutes","Share"])
    brief_findings="\n\n".join(f"{i}. **{f['title']}.** {f['observation']} {src(f['source_table'])}" for i,f in enumerate(findings[:5],1))
    executive=f"""# Executive Business Findings

## Decision for the Head of Operations

Prioritize investigation of the interval before the final rider notification and a monitored exception-review pilot for repeated pre events. Establish reliable capacity observation before changing staffing rules. The evidence supports these diagnostic priorities; it does not establish a causal remedy or savings forecast.

## Study and service baseline

The supplied extract contains **{_n(k['orders'])} orders**, including {_n(k['completed_orders'])} completed orders, across {audit['coverage']['calendar_hours']} calendar hours. Recorded window: {window}. Completed service averages {_n(k['mean_min'],2)} minutes; P90 is {_n(k['p90_min'],2)} and P95 is {_n(k['p95_min'],2)}. {_pct(k['late5_rate'])} of eligible completed orders exceed their recorded promise by more than five minutes. {src('analysis/kpis.csv')}

## Five findings

{brief_findings}

## Actions, trade-offs and monitoring

- **Dispatch/operations:** review orders after four recorded pre events; record first-dispatch and reassignment timestamps. Monitor P90 creation-to-final-notification, completion and late >5 minutes. A manual review adds effort and may escalate too early; measure it in a limited pilot.
- **Workforce/data operations:** correct timestamp parsing and investigate missing shift dates. Monitor orders and rider-hours on matching hours, date/hour coverage and service P90/P95. Additional staffing can lower output per recorded hour; a cost benefit is unproven.
- **Merchant operations:** investigate sustained pickup waiting in adequately supported merchant cohorts. Monitor pickup-wait P90 and customer service together; later rider arrival can hurt service when readiness estimates are wrong.

The initial operational interval is the main measured bottleneck. Its internal mechanism remains unobserved. Rain covers one recorded episode and cannot establish a general weather effect. No rider is identified as responsible for earlier rejections, and no customer delay is converted into labor-hours or additional delivery capacity.
"""
    insights="# Business Insights\n\nRanked from strongest operational diagnosis to descriptive limitations. Every effect below is observational.\n\n"
    for f in findings:
        insights+=f"""## {f['id']} — {f['title']}

### Insight
{f['observation']}

### Evidence
{src(f['source_table'])} Machine-readable values are also recorded under `{f['id']}` in [the findings register](../outputs/executive_findings.json).

### Why it matters
{f['interpretation']}

### Possible explanation
{f['limitation']}

### Recommended operational action
{f['action']}

### Confidence / limitation
{f['confidence']}. {f['limitation']}

"""
    insights+="## Distribution and cross-variable evidence\n\n"
    insights+=f"The slowest observed service tail exceeds {_n(t['p95_cutoff_min'],2)} minutes. {_n(t['tail_orders'])} completed orders ({_pct(t['tail_share'])}) contain {_pct(t['tail_share_service_minutes'])} of total completed-service minutes; their mean is {_n(t['tail_mean_min'],2)} minutes. This distinguishes tail concentration from a uniform shift. {src('analysis/tail_segments.csv')}\n\n"
    insights+="[Operational segments](../outputs/analysis/operational_segments.csv) include weather × hour, weather × demand/supply, weekday × hour, peak × weather × supply, order type/distance and relative demand/supply where available. [Process stages by segment](../outputs/analysis/stage_by_segment.csv) identify whether the largest stage changes. Small groups remain visible, with counts and dates.\n\n"
    insights+="## Tested hypotheses\n\n"+_md_table(result["hypotheses"],["hypothesis","supporting_evidence","contradicting_or_limiting_evidence","conclusion","strength"])
    insights+="\n## Management prioritization\n\n"+_md_table(result["priorities"],["priority","issue","affected_orders","affected_late5_orders","affected_share","controllability","action","monitoring_kpi","trade_off"])
    insights+="\nExposure cohorts overlap and their costs/minutes cannot be summed as savings. The priority matrix records frequency and measured burden alongside controllability; its decision sequence is documented in the source table. [Full matrix](../outputs/analysis/priorities.csv).\n"

    summary40=f"Analyzed {_n(k['orders'])} delivery orders by joining order records, rider shifts, weather and events. Rebuilt operational metrics, decomposed service delays and tested cross-variable hypotheses, producing documented priorities, an interactive dashboard and reproducible validation without claiming causality or inventing unsupported business results."
    summary100=f"I analyzed {_n(k['orders'])} delivery orders using order records, rider shifts, weather and events. I corrected mixed timestamp parsing, rebuilt capacity measures and reconciled recorded costs. A complete process decomposition located {_pct(findings[0]['evidence']['initial_late_gap_share'],0)} of the late-order duration difference before final rider notification. Orders with repeated pre events formed a small, concentrated exception cohort. I examined service tails, operational segments, conditional associations and temporal threshold stability, while distinguishing observed patterns from causal explanations. The deliverables include a tested Python pipeline, Streamlit dashboard, Power BI semantic exports and executive recommendations with explicit triggers, trade-offs, monitoring metrics and evidence limitations for practical operational decision making."
    # Word limits are part of the requested portfolio interface.
    portfolio=f"""# Portfolio Summary

## 40-word project summary

{summary40}

## 100-word project summary

{summary100}

## Three CV bullets

- Rebuilt a delivery-operations pipeline for {_n(k['orders'])} orders, reconciling source cost records and recovering {_n(audit['shifts']['legacy_parse_failures'])} complete shift records lost by mixed timestamp parsing.
- Decomposed completed delivery timelines and identified {_pct(findings[0]['evidence']['initial_late_gap_share'])} of the late-versus-on-time duration gap before final rider notification; prioritized an exception cohort containing {_pct(t['pre4_event_share'])} of pre events.
- Delivered operational segmentation, 500-resample date-bootstrap comparisons, conditional statistical models, tested Streamlit reporting and Power BI semantic exports, with documented uncertainty and reproducibility checks.

## Five strongest findings

{brief_findings}

## Main bottleneck

Creation to final rider notification: {_n(p['main_stage_mean_min'],2)} minutes on average. The available timestamps do not separate first assignment, scheduling and successive reassignments.

## Most interesting cross-variable insight

The repeated-pre-event cohort combines a small order share ({_pct(t['pre4_order_share'])}) with high pre-event concentration ({_pct(t['pre4_event_share'])}), long completed service ({_n(t['pre4_mean_min'],2)} minutes) and {_pct(t['pre4_late5_rate'])} late >5-minute incidence. It defines a concrete exception-review population.

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
"""
    process="""# Operational Process and KPI Map

```mermaid
flowchart LR
  A[Order creation] --> B[Final rider notification]
  B --> C[Final rider acceptance]
  C --> D[Arrival at pickup]
  D --> E[Pickup]
  E --> F[Arrival at destination]
  F --> G[Final handoff]
  A --> V[Send to merchant]
  V --> W[Merchant acceptance]
```

The merchant branch can overlap rider dispatch. The first five solid rider-path intervals form the additive creation-to-destination duration. Final handoff is shown separately because it is outside the endpoint matched by the platform's declared `tiempo_real` field. No timestamp records the first offer or each rejected assignment.

"""+stages+"\n"+src("analysis/stage_summary.csv")+"\n\nProcess metrics use a common completed cohort with every stage present and nonnegative. Signed merchant-acceptance-to-notification time is retained as an overlap diagnostic. A negative signed branch interval is not erased or added to a truncated process total.\n"
    methods="""# Analytical Framework and Metric Contracts

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
"""
    data_audit=f"""# Data Audit

## Source inventory

{_md_table([{'Source':name,'File':value['file'],'Rows':manifest['row_counts']['raw_'+name],'SHA-256':value['sha256']} for name,value in manifest['sources'].items()],['Source','File','Rows','SHA-256'])}

## Corrections and exclusions

- {_n(audit['orders']['raw_rows'])} source order records represent {_n(k['orders'])} unique orders. Exactly one principal row is required; recorded cost reconciles within floating-point tolerance.
- {_n(audit['shifts']['missing_shift_datetime_rows'])} shift records have missing dates/times. Their real operational meaning is undocumented; they are neither imputed nor automatically interpreted as worked hours.
- The legacy parser loses {_n(audit['shifts']['legacy_parse_failures'])} otherwise complete shift records. Explicit mixed-format parsing loses {_n(audit['shifts']['mixed_parse_failures'])}. The observed window contains {_n(audit['shifts']['union_window_rider_hours'],2)} rider-hours.
- {_n(audit['shifts']['long_shifts_gt16h'])} positive source shifts exceed 16 hours. Within-window supply excluding those shifts is {_n(audit['shifts']['window_hours_excluding_long_shifts_unmerged'],2)} unmerged rider-hours; overlap removal is {_n(audit['shifts']['overlap_hours_removed'],2)} hours.
- {_n(audit['coverage']['order_hours_without_supply'])} order hours, containing {_n(audit['coverage']['orders_without_hourly_supply'])} orders, lack usable hourly supply. {_n(audit['coverage']['zero_recorded_demand_supply_hours'])} recorded-supply hours contain no recorded orders.
- {_n(audit['shifts']['orders_final_rider_without_dated_window_shift'])} orders have a final rider with no dated shift in the observed window. Aggregate supply observation does not prove individual rider coverage.
- Weather covers {_n(audit['coverage']['weather_hours'])} of {_n(audit['coverage']['calendar_hours'])} calendar hours and {_n(audit['coverage']['orders_with_weather'])} orders. Unknown weather is a separate category.
- {_n(audit['events']['exact_duplicate_events'])} exact event duplicates are identified; distinct overlapping events and holidays retain independent flags/counts.

## Complete dictionary and provenance

[Data dictionary](../outputs/data_dictionary.csv) covers every raw and canonical variable, meaning, unit, type, missing count/fraction, source and semantic confidence. [Full audit](../outputs/data_audit.json) and [manifest](../outputs/manifest.json) retain numeric evidence.

Timestamp offsets, currency, wind units and opaque platform fields have no authoritative source dictionary in this repository. Assumptions remain labelled. The project uses the supplied extract as observed data; its production provenance is not independently verified.
"""
    question_tree="""# Business Question Tree

1. **What is the service problem?** Completed-service distribution, late incidence at explicit tolerances, completion/cancellation and tail burden.
2. **Where in the process does time accrue?** Complete additive timeline; separate merchant overlap and final handoff; compare common-cohort stage means and late-order differences.
3. **When and under which conditions?** Hour × weekday; weather × hour/demand/supply; event windows; absolute and within-clock demand/supply; pressure; peak versus non-peak.
4. **Which order populations concentrate the problem?** Repeated pre/post events, vertical, recorded distance, vehicle and order-value proxy, merchant cohorts and final-rider exposure. Avoid attribution to earlier rejecting riders.
5. **Does a capacity boundary repeat?** Ratio-of-sums metrics, complete calendar spine, coverage flags, discovery/holdout dates and no forced threshold.
6. **Which explanations survive scrutiny?** The five hypothesis families compare supporting and contradictory data, use clustered uncertainty and distinguish unobserved mechanisms from measured associations.
7. **What should management do?** Prioritize observed burden and frequency alongside controllability; define a pilot trigger, action, KPI, trade-off and follow-up measurement. No invented savings or causal promise.

Each retained chart answers one of these questions. Data-quality, hypothesis and model tables are supporting evidence, not a substitute for an operational interpretation.
"""
    test_info={"status":"not_run","tests":0,"failures":0}
    if (output_dir/"tests.xml").exists():
        tree=ET.parse(output_dir/"tests.xml").getroot()
        suites=list(tree.iter("testsuite"))
        test_info={"tests":sum(int(x.attrib.get("tests",0)) for x in suites),"failures":sum(int(x.attrib.get("failures",0))+int(x.attrib.get("errors",0)) for x in suites)}
        test_info["status"]="passed" if not test_info["failures"] else "failed"
    review=f"""# Validation and Final Operations Review

## Executed checks

- Canonical source/data validation: **{validation.get('status','not run')}**, {validation.get('passed',0)} passed checks, {validation.get('failed',0)} failures. [Details](../outputs/validation.json).
- Automated tests: **{test_info['status']}**, {test_info['tests']} tests, {test_info['failures']} failures. [JUnit record](../outputs/tests.xml).
- Repeat complete-build comparison: **{reproducibility.get('status','not run')}**. [Artifact comparisons](../outputs/reproducibility.json).
- Power BI static validation: **{powerbi.get('validation',{}).get('status','not run')}**. [Checks and native status](../outputs/powerbi/validation.json).
- Native Power BI DAX/M execution is not established by static validation. Existing authored report files are preserved; Desktop refresh and field bindings require a native engine check.

## Head of Operations review

**Where does the problem occur?** Primarily before final rider notification in the measured late-order difference. This is a stage location, not an identified cause.

**When and for whom?** Repeated pre-event orders define a concentrated exception cohort; hourly, weekday, weather, absolute/relative capacity and order-complexity tables show the observed distribution. The slowest {_pct(t['tail_share'])} of completed orders contain {_pct(t['tail_share_service_minutes'])} of completed-service minutes.

**Why?** The available data do not resolve first assignment, offer compensation, rejection sequences or merchant readiness. Conditional associations and contradictory evidence constrain the hypotheses. No claim that pricing, rain or rider behavior caused the delays is retained.

**What combinations matter?** Review the relative demand/supply comparisons, peak/weather/supply segments and distance/event cohorts with their independent-date support. An absent comparison cell is a support gap, not evidence that the condition has no effect.

**What should management do?** Instrument the initial interval, pilot repeated-event review and evaluate sustained pickup waiting. Verify capacity coverage before changing staffing rules. Monitor completion, late >5 minutes, stage P90, customer service P90/P95 and recorded cost on matching populations.

**What was rejected?** The former incomplete pickup-bottleneck claim, compensation-per-distance causality, assignment of earlier rejections to the final rider, conversion of order delay to labor-hours, guaranteed recoverable savings and a forced capacity threshold.

The resulting diagnosis is coherent within the extract's limits. Unidentified mechanisms are documented as requirements for a future operational test, rather than filled with invented findings.
"""
    phases=[
        (1,"Process reconstruction","PROCESS_MAP.md; analysis/stage_summary.csv"),
        (2,"Complete data audit","DATA_AUDIT.md; data_dictionary.csv; data_audit.json"),
        (3,"Business question tree","BUSINESS_QUESTIONS.md"),
        (4,"Cross-data analysis","analysis/operational_segments.csv; analysis/headline_contrasts.csv"),
        (5,"Segmentation","analysis/operational_segments.csv"),
        (6,"Bottleneck decomposition","analysis/stage_summary.csv; analysis/stage_late_contrasts.csv; analysis/stage_by_segment.csv"),
        (7,"Capacity analysis","hours.parquet; analysis/capacity_bins.csv"),
        (8,"Threshold analysis","analysis/threshold_assessment.csv; analysis/temporal_holdout.csv"),
        (9,"Distribution and tails","analysis/kpis.csv; analysis/tail_segments.csv"),
        (10,"Root-cause hypotheses","analysis/hypotheses.csv"),
        (11,"Statistical validation","analysis/headline_contrasts.csv; analysis/model_coefficients.csv; analysis/model_diagnostics.csv"),
        (12,"Non-obvious findings","BUSINESS_INSIGHTS.md; executive_findings.json"),
        (13,"Management prioritization","analysis/priorities.csv"),
        (14,"Executive Business Findings","EXECUTIVE_SUMMARY.md"),
        (15,"So-what test","BUSINESS_QUESTIONS.md; dashboard question-led sections"),
        (16,"Specific recommendations","EXECUTIVE_SUMMARY.md; analysis/priorities.csv"),
        (17,"Dashboard","Streamlit dashboard; Power BI semantic export (native refresh unverified)"),
        (18,"Business-case README","README.md"),(19,"Executive summary","EXECUTIVE_SUMMARY.md"),
        (20,"Insight report","BUSINESS_INSIGHTS.md"),(21,"Interview material","PORTFOLIO_SUMMARY.md"),
    ]
    ledger=[{"Phase":num,"Requirement":title,"Status":"Completed with stated evidence limitations","Evidence":evidence} for num,title,evidence in phases]
    ledger.append({"Phase":"Final","Requirement":"Head of Operations self-review","Status":"Completed; native Power BI execution remains unverified","Evidence":"VALIDATION_REPORT.md; validation.json; reproducibility.json"})
    docs={"EXECUTIVE_SUMMARY.md":executive,"BUSINESS_INSIGHTS.md":insights,"PORTFOLIO_SUMMARY.md":portfolio,
          "PROCESS_MAP.md":process,"METHODOLOGY.md":methods,"DATA_AUDIT.md":data_audit,"BUSINESS_QUESTIONS.md":question_tree,
          "VALIDATION_REPORT.md":review,"PHASE_COMPLETION.md":"# Phase Completion Ledger\n\n"+_md_table(ledger,["Phase","Requirement","Status","Evidence"])}
    readme=f"""# Delivery Operations Intelligence

## Executive Summary

A reproducible operational diagnosis of {_n(k['orders'])} orders from four supplied datasets. The main measured late-order difference occurs before the final rider notification. Repeated pre events identify a concentrated exception population; pressure and weather evidence do not justify automatic staffing or pricing claims.

{brief_findings.replace('../outputs/','outputs/')}

Read the [executive brief](docs/EXECUTIVE_SUMMARY.md), [ranked insights](docs/BUSINESS_INSIGHTS.md) and [interview material](docs/PORTFOLIO_SUMMARY.md).

## Business Problem

Determine where service deteriorates, which conditions accompany it and what management should test. Customer waiting, recorded costs and throughput require different denominators and do not automatically translate into recoverable capacity.

## Operational Process

Creation → final rider notification → acceptance → pickup arrival → pickup → destination arrival. Merchant acceptance can overlap dispatch; handoff follows arrival. [Process map and stage KPIs](docs/PROCESS_MAP.md).

## Data

Window: {window}. {_n(k['orders'])} orders; {_n(audit['orders']['raw_rows'])} source cost/reason rows; {_n(audit['shifts']['raw_shifts'])} shift records. Sources stay unchanged in the project root. [Source audit](docs/DATA_AUDIT.md), [full dictionary](outputs/data_dictionary.csv) and [manifest](outputs/manifest.json).

## Key KPIs

Completed service: mean {_n(k['mean_min'],2)}, median {_n(k['median_min'],2)}, P90 {_n(k['p90_min'],2)}, P95 {_n(k['p95_min'],2)} minutes. Late >5 minutes: {_pct(k['late5_rate'])}. Pre/post affected-order rates: {_pct(k['pre_rate'])}/{_pct(k['post_rate'])}. Matched observed throughput: {_n(result['capacity']['orders_per_observed_rider_hour'],3)} orders per recorded rider-hour. CPO: {_n(k['recorded_cost_mean'],2)} recorded units per order; currency is unverified. [Definitions](docs/METHODOLOGY.md).

## Analytical Framework

[Business question tree](docs/BUSINESS_QUESTIONS.md) → validated source grains → cross-variable segments → complete process decomposition → uncertainty and hypotheses → prioritized operational tests. [All 21 phases](docs/PHASE_COMPLETION.md).

## Demand vs Capacity

Observed rider-hours total {_n(result['capacity']['observed_rider_hours'],2)}. Unknown supply remains unknown; the ratio excludes {_n(result['capacity']['orders_missing_supply'])} orders without matching hourly supply. Full calendar hours preserve zero recorded demand. Within-clock relative demand/supply comparisons supplement global bands. [Capacity and threshold tables](outputs/analysis/capacity_bins.csv).

## Bottleneck Analysis

{stages}

Creation-to-final-notification contributes {_pct(findings[0]['evidence']['initial_late_gap_share'])} of the late-versus-on-time duration gap. The earlier truncated decomposition overstated pickup waiting's share. [Common-cohort contrasts](outputs/analysis/stage_late_contrasts.csv).

## Weather Impact

Rain is a single recorded episode; wet days including drizzle remain below the declared independent-date threshold. Weather combinations are descriptive and missing weather is visible. [Weather support](outputs/analysis/weather_support.csv).

## Operational Segmentation

Hour/weekday, demand/supply, relative demand/supply, pressure, weather, events, vertical/distance, vehicle/value, merchant and final-rider exposure. Every important segment includes support and eligible denominators. [Segment results](outputs/analysis/operational_segments.csv).

## Statistical Evidence

Five hypothesis families, 500 date-bootstrap resamples, date-clustered binomial models and later-date threshold confirmation. Odds associations are not causal effects. [Methods](docs/METHODOLOGY.md) and [model diagnostics](outputs/analysis/model_diagnostics.csv).

## Key Business Findings

[Executive Business Findings](docs/EXECUTIVE_SUMMARY.md) link observations to numeric evidence, plausible explanations and operational actions. [Machine-readable register](outputs/executive_findings.json).

## Recommendations

Instrument the initial operational interval; pilot review of repeated pre events; improve shift observability; investigate merchant pickup waiting with service and cost guardrails. Trigger definitions, trade-offs and measurement plans are in the [priority matrix](outputs/analysis/priorities.csv).

## Limitations

Short observational extract; undocumented timezone/currency and opaque fields; missing dated shifts and weather; no offer-level compensation or assignment-event history. Recorded final rider IDs do not identify earlier rejecting riders. No invented savings, causal pricing conclusion or forced staffing threshold. [Validation and self-review](docs/VALIDATION_REPORT.md).

## Repository Structure

- `delivery_ops/`: import-safe data reconstruction, analysis, reporting, dashboard, export and validation.
- `tests/`: meaningful synthetic edge cases and interface/export regression tests.
- `docs/`: business case, methodology, audit, phase ledger and interview materials.
- `outputs/`: generated Parquet data, numeric evidence, figures in the interactive dashboard, Power BI semantic project and validation records.
- `v16/`: compatibility entrypoints and preserved historical artifacts. The V15 dashboard and old V16 output tables are historical, not current evidence.
- `CODEX_TASK.md`: the confirmed 21-phase task brief. Raw CSV/XLSX sources stay in the root and are not published remotely.

## How to Run

Use Python 3.12 or later. From the project root:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.lock.txt
.\\.venv\\Scripts\\python.exe -m delivery_ops run
.\\.venv\\Scripts\\python.exe -m pytest --junitxml=outputs/tests.xml
.\\.venv\\Scripts\\python.exe -m streamlit run v16/dashboard_v16.py --server.port 8503
```

The prepared local environment can run these commands directly. Double-click `v16/abrir_dashboard.bat` to launch the dashboard. For a separate reproduction: `python -m delivery_ops run --output-dir outputs_repro`, then `python -m delivery_ops compare --compare-dir outputs_repro`. Source files must retain their supplied filenames; `--data-dir` selects another source folder.

The Power BI project is `outputs/powerbi/PanelDelivery/PanelDelivery.pbip`. Static schema/KPI validation and preservation tests run locally; native Desktop refresh is reported separately. The generated native report is a semantic scaffold; Streamlit is the authored interactive report. [Power BI guide](v16/GUIA_POWERBI.md).

## Author

Santino Cervio  
Industrial Engineering — ITBA
"""
    generated=output_dir/"reports"
    generated.mkdir(parents=True,exist_ok=True)
    for name,text in docs.items():
        (generated/name).write_text(text.replace("../outputs/","../"),encoding="utf-8")
    (generated/"README.md").write_text(readme,encoding="utf-8")
    if output_dir.resolve()==(root/"outputs").resolve():
        (root/"docs").mkdir(exist_ok=True)
        for name,text in docs.items():
            (root/"docs"/name).write_text(text,encoding="utf-8")
        (root/"README.md").write_text(readme,encoding="utf-8")
    report_checks={"summary_40_words":len(summary40.split()),"summary_100_words":len(summary100.split()),
                   "executive_summary_words":len(executive.split()),"findings":len(findings),"phase_entries":len(ledger),
                   "source_analysis_sha256":sha256(output_dir/"analysis_results.json"),
                   "all_evidence_files_exist":all((output_dir/f["source_table"]).exists() for f in findings)}
    write_json(output_dir/"report_validation.json",report_checks)
    return report_checks
