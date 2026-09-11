Act as a senior Business Operations Analyst, Operations Researcher, Data Analyst and Data Scientist.

I am an Industrial Engineering student at ITBA applying for Business Operations roles at AI-driven companies.

This repository contains a delivery-operations project based on datasets such as:

- orders
- weather
- rider shifts
- operational timestamps
- service metrics
- cost metrics
- demand information

Your main objective is NOT to make the project visually attractive.

Your main objective is to extract the strongest, most useful and most defensible business conclusions possible from the available data.

The finished project must demonstrate that I can:

- understand an operational system end to end
- detect bottlenecks
- connect KPIs to operational causes
- combine multiple datasets
- segment problems
- identify where and when performance deteriorates
- distinguish symptoms from root causes
- formulate and test business hypotheses
- translate analysis into operational actions
- prioritize recommendations according to impact

Do not fabricate conclusions.

Every important conclusion must be supported by actual data available in the repository.

Do not confuse correlation with causation.

If evidence is weak, say so explicitly.

==================================================
PHASE 1 — UNDERSTAND THE BUSINESS PROCESS
==================================================

Before modifying code, reconstruct the operational process represented by the data.

Identify the main stages of an order.

For example, if supported by the timestamps:

Order created
→ assignment / dispatch
→ rider arrival
→ pickup
→ delivery
→ completion

Determine which timestamps correspond to each operational stage.

Create a clear process map.

Then identify which KPI reflects each stage.

The analysis should answer:

Where exactly is time being lost?

Is the delay generated before rider assignment, after assignment, at pickup, during transport, or somewhere else?

==================================================
PHASE 2 — COMPLETE DATA AUDIT
==================================================

Inspect every dataset, notebook, script and existing visualization.

Create a data dictionary containing:

- variable
- meaning
- unit
- type
- missing values
- possible business interpretation
- dataset source

Identify keys that allow datasets to be joined.

Check whether the current analysis is using all relevant variables.

Search for potentially valuable information that was previously ignored.

==================================================
PHASE 3 — BUILD A BUSINESS QUESTION TREE
==================================================

Do not begin with charts.

Begin with business questions.

Structure the analysis around a hierarchy similar to:

1. What determines service performance?

2. When does performance deteriorate?

3. Where does performance deteriorate?

4. Which part of the operational process creates the deterioration?

5. Is the problem driven by:
   - demand
   - rider capacity
   - weather
   - time of day
   - operational zone
   - service complexity
   - order volume
   - insufficient staffing
   - dispatch inefficiency
   - pickup delays
   - another identifiable factor?

6. What is the relationship between these problems and:
   - UTR
   - CPO
   - pre-undispatch
   - service time
   - rider utilization
   - throughput
   - other relevant KPIs?

7. Which problems should management prioritize?

==================================================
PHASE 4 — CROSS-DATA ANALYSIS
==================================================

This phase is extremely important.

Do not analyze variables only in isolation.

Cross multiple dimensions to uncover interactions.

Examples, when supported by available data:

Weather × hour

Weather × demand

Weather × rider availability

Weather × pre-undispatch

Weather × CPO

Weather × UTR

Demand × rider availability

Demand × pre-undispatch

Demand × CPO

Demand × UTR

Hour × demand × riders

Hour × weather × service performance

Day of week × hour × demand

Day of week × staffing

Rider availability × order volume

Rider availability × service time

High-demand periods × weather conditions

High-demand periods × capacity shortage

Peak hours × pre-undispatch

Peak hours × cost

Peak hours × utilization

Investigate combined conditions.

Do not stop at conclusions such as:

"Rain increases delays."

Instead investigate questions such as:

Does rain increase delays at all hours, or only during peak demand?

Does rain itself explain the increase in CPO, or does CPO increase because rain coincides with rider shortages?

Does poor UTR occur because demand falls, because there are too many riders, or because service times increase?

Are the worst operational periods defined by one variable or by combinations such as:

high demand + rain + low rider availability?

==================================================
PHASE 5 — SEGMENTATION
==================================================

Find meaningful operational segments.

Possible segmentation dimensions include:

- hour
- day of week
- weather
- demand level
- rider availability
- rider/order ratio
- service-time quartile
- pre-undispatch quartile
- operational zones if available
- order type if available
- high/medium/low demand

Create segments such as:

High demand / sufficient riders

High demand / insufficient riders

Low demand / excess riders

Rain / sufficient riders

Rain / insufficient riders

Peak / non-peak

Then compare KPIs between these groups.

The goal is to identify the operational conditions associated with the best and worst performance.

==================================================
PHASE 6 — BOTTLENECK DECOMPOSITION
==================================================

Do not use total delivery time alone.

Decompose performance into process components.

Determine which stages explain most of the deterioration.

For example:

Total service time
=
pre-dispatch
+
rider assignment
+
pickup
+
transport
+
other identifiable stages

Where technically possible, calculate:

- average
- median
- percentiles
- variance
- contribution to total time

Compare these components between operational segments.

Answer:

Which stage is the true bottleneck?

Does the bottleneck change according to demand, weather or staffing?

==================================================
PHASE 7 — CAPACITY ANALYSIS
==================================================

Study the relationship between orders and rider capacity.

Construct meaningful indicators such as:

orders per rider

riders per active order

demand-to-capacity ratio

rider utilization

or other defensible capacity proxies.

Investigate whether there is a threshold beyond which performance deteriorates rapidly.

For example:

At what demand-to-rider ratio does pre-undispatch start increasing significantly?

Does CPO increase when capacity exceeds or falls below certain levels?

Does excessive staffing reduce UTR?

The objective is to understand both:

UNDERCAPACITY
and
OVERCAPACITY.

==================================================
PHASE 8 — THRESHOLD ANALYSIS
==================================================

Search for operational thresholds rather than only averages.

Examples:

When demand exceeds X orders/hour, performance worsens.

When orders/rider exceed X, pre-undispatch accelerates.

When rider availability falls below X relative to demand, service quality deteriorates.

Do not force thresholds if the data does not support them.

Use bins, quantiles, rolling averages, regression or other reasonable techniques.

==================================================
PHASE 9 — DISTRIBUTION ANALYSIS
==================================================

Do not rely solely on averages.

Operations often fail in the tails.

Analyze:

- median
- P75
- P90
- P95
- extreme cases

Determine whether poor service is:

a general deterioration

or

a small group of extremely bad orders.

Identify what conditions are associated with extreme cases.

==================================================
PHASE 10 — ROOT CAUSE HYPOTHESES
==================================================

Create explicit hypotheses.

Examples:

H1:
High demand increases pre-undispatch because rider capacity becomes insufficient.

H2:
Rain increases CPO primarily through longer service times.

H3:
Low UTR during certain hours is caused by excess rider capacity relative to demand.

H4:
The worst service performance occurs when rain and peak demand happen simultaneously.

H5:
A staffing mismatch explains more variation in performance than weather alone.

Test each hypothesis with the available data.

For each hypothesis report:

- supporting evidence
- contradicting evidence
- strength of evidence
- conclusion

==================================================
PHASE 11 — STATISTICAL VALIDATION
==================================================

When appropriate, use statistical analysis to determine whether observed differences are meaningful.

Possible techniques:

- correlations
- grouped comparisons
- confidence intervals
- hypothesis tests
- simple regression
- multiple regression
- interaction terms

For example:

Performance =
Demand
+ Riders
+ Weather
+ Hour
+ Demand × Riders
+ Weather × Demand

The goal is not academic complexity.

The goal is to determine whether apparent operational relationships remain relevant after accounting for other factors.

Avoid making causal claims unless the methodology supports them.

==================================================
PHASE 12 — FIND NON-OBVIOUS INSIGHTS
==================================================

Actively search for counterintuitive or non-obvious results.

Examples:

Rain may not be the main problem.

The real problem may be that staffing does not adjust sufficiently when rain and demand coincide.

High rider availability may not always improve operations.

Too many riders during low-demand periods may reduce utilization and increase CPO.

Peak demand may not be problematic when rider capacity is sufficient.

A specific combination of demand, weather and staffing may explain most extreme delays.

Do not manufacture surprising conclusions.

Search systematically for them.

==================================================
PHASE 13 — MANAGEMENT PRIORITIZATION
==================================================

Not every finding is equally important.

Rank identified problems using a framework such as:

Impact
×
Frequency
×
Operational controllability

For each problem estimate, using available data:

- how often it occurs
- how much it affects KPIs
- whether management can control it
- which operational lever could address it

Create a prioritization matrix.

==================================================
PHASE 14 — STRONG BUSINESS CONCLUSIONS
==================================================

Create a section:

## Executive Business Findings

The strongest findings should follow this structure:

OBSERVATION

EVIDENCE

BUSINESS INTERPRETATION

OPERATIONAL ACTION

For example:

Observation:
Service performance deteriorates primarily during high-demand periods when rider capacity does not scale proportionally.

Evidence:
[actual project statistics]

Interpretation:
The main issue appears to be a capacity mismatch rather than demand growth itself.

Operational action:
Use demand-based rider scheduling or dynamic staffing thresholds.

Do this for every major conclusion.

==================================================
PHASE 15 — "SO WHAT?" TEST
==================================================

For every chart, table or statistical result ask:

"So what?"

If a visualization does not contribute to a business conclusion, operational diagnosis or decision, consider removing or deprioritizing it.

Every major visualization must answer a question.

==================================================
PHASE 16 — BUSINESS RECOMMENDATIONS
==================================================

Recommendations must be specific.

Avoid generic recommendations such as:

"Optimize rider allocation."

Prefer recommendations such as:

"Increase rider coverage during the identified demand window when orders-per-rider exceeds the observed deterioration threshold."

Where possible specify:

- trigger
- operational action
- KPI expected to improve
- trade-off
- monitoring metric

Do not fabricate expected improvement percentages.

==================================================
PHASE 17 — DASHBOARD
==================================================

The dashboard is secondary to the analysis.

Only redesign it where necessary to make the business conclusions easier to understand.

The dashboard should help management answer:

What is wrong?

When does it happen?

Why does it happen?

How severe is it?

What should we do?

Suggested sections:

Executive Overview

Demand vs Capacity

Process Bottlenecks

Service Performance

Weather & External Conditions

Cost & Efficiency

Critical Operational Segments

Management Insights

==================================================
PHASE 18 — README
==================================================

The README should behave like a short business case.

Suggested structure:

# Delivery Operations Intelligence

## Executive Summary

Summarize the 3–5 strongest operational findings.

## Business Problem

## Operational Process

## Data

## Key KPIs

## Analytical Framework

## Demand vs Capacity

## Bottleneck Analysis

## Weather Impact

## Operational Segmentation

## Statistical Evidence

## Key Business Findings

## Recommendations

## Limitations

## Repository Structure

## How to Run

## Author

Santino Cervio
Industrial Engineering — ITBA

==================================================
PHASE 19 — EXECUTIVE SUMMARY
==================================================

Create:

docs/EXECUTIVE_SUMMARY.md

Maximum approximately 2 pages.

Write it as if it were going to the COO / Head of Operations.

Include:

1. Main operational problem
2. Three to five strongest findings
3. Evidence
4. Business interpretation
5. Main bottleneck
6. Recommended actions
7. KPIs management should monitor

Avoid excessive technical detail.

==================================================
PHASE 20 — INSIGHT REPORT
==================================================

Create:

docs/BUSINESS_INSIGHTS.md

For every major insight include:

### Insight

### Evidence

### Why it matters

### Possible explanation

### Recommended operational action

### Confidence / limitation

Rank insights from strongest to weakest.

==================================================
PHASE 21 — INTERVIEW MATERIAL
==================================================

Create:

docs/PORTFOLIO_SUMMARY.md

Include:

- 40-word project summary
- 100-word project summary
- 3 strong CV bullets
- 5 strongest business findings
- main bottleneck identified
- most interesting cross-variable insight
- most counterintuitive insight
- strongest management recommendation
- technical tools used
- business skills demonstrated
- 30-second interview explanation
- 2-minute interview explanation

==================================================
FINAL REVIEW
==================================================

Before finishing, act as a Head of Business Operations reviewing this project.

Ask:

Did the candidate merely visualize data?

Or did the candidate actually understand how the operation works?

Can I clearly identify:

- where the problem happens?
- when it happens?
- why it happens?
- what combination of variables explains it?
- what management should do?
- which KPIs should be monitored afterward?

If these questions cannot be answered strongly, continue analyzing the available data.

Perform additional segmentation, cross-analysis or statistical validation where appropriate.

Do not stop simply because the dashboard works.

The project is finished only when the data has been converted into a coherent operational diagnosis and a set of defensible business recommendations.