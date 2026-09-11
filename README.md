# Delivery Operations Intelligence

A source-available portfolio case study by **Santino Cervio**, Industrial Engineering at ITBA.

This public repository includes reproducible Python code, synthetic tests, English reports and aggregate evidence from the original local analysis. Raw records, individual rider/merchant tables and native data exports are intentionally excluded. [Data access and reproduction](docs/DATA_ACCESS.md).

## Executive Summary

A reproducible operational diagnosis of 334,144 orders from four supplied datasets. The main measured late-order difference occurs before the final rider notification. Repeated pre events identify a concentrated exception population; pressure and weather evidence do not justify automatic staffing or pricing claims.

1. **The main measured deterioration occurs before the final rider notification.** Creation to final notification averages 10.58 minutes. It contributes 6.05 minutes, or 51.0%, of the late-versus-on-time duration difference. Pickup waiting contributes 24.0%. [Evidence](outputs/analysis/stage_late_contrasts.csv)

2. **A small repeated-pre-event cohort concentrates operational problems.** 10,472 orders with at least four pre events represent 3.1% of orders with known pre counts and 36.6% of recorded pre events. Their completed orders average 45.88 minutes; 67.1% exceed the promise by more than five minutes. [Evidence](outputs/analysis/headline_contrasts.csv)

3. **Longer recorded delivery distances identify a high-pre-event population.** Orders with recorded dropoff distance above 3 km have 47.9% pre-event incidence, versus 17.3% at 1 km or less. The difference is 30.59 percentage points, with a 95% date-bootstrap interval of 29.49–31.61 points. [Evidence](outputs/analysis/headline_contrasts.csv)

4. **Pressure alone does not establish a staffing deterioration threshold.** High versus low observed pressure differs by -0.58 percentage points in late >5-minute incidence; the 95% date-bootstrap interval is -2.14 to 1.25 points. The corrected matched-hour throughput is 1.727 orders per observed rider-hour. [Evidence](outputs/analysis/threshold_assessment.csv)

5. **Recorded extra-record cost is a small accounting exposure.** Reason-bearing records contain 384,517.81 cost units, 0.334% of 115,147,509.10 total recorded cost units. [Evidence](outputs/analysis/recorded_cost.csv)

Read the [executive brief](docs/EXECUTIVE_SUMMARY.md), [ranked insights](docs/BUSINESS_INSIGHTS.md) and [interview material](docs/PORTFOLIO_SUMMARY.md).

## Business Problem

Determine where service deteriorates, which conditions accompany it and what management should test. Customer waiting, recorded costs and throughput require different denominators and do not automatically translate into recoverable capacity.

## Operational Process

Creation → final rider notification → acceptance → pickup arrival → pickup → destination arrival. Merchant acceptance can overlap dispatch; handoff follows arrival. [Process map and stage KPIs](docs/PROCESS_MAP.md).

## Data

Window: 2024-06-30 22:00:00 to 2024-07-31 21:00:00 (exclusive end; source timezone undocumented). 334,144 orders; 347,644 source cost/reason rows; 176,235 shift records. The original sources were preserved unchanged during the private analysis; they are not distributed here. [Data access](docs/DATA_ACCESS.md). [Source audit](docs/DATA_AUDIT.md), [full dictionary](outputs/data_dictionary.csv) and [manifest](outputs/manifest.json).

## Key KPIs

Completed service: mean 25.72, median 23.02, P90 41.97, P95 49.53 minutes. Late >5 minutes: 15.6%. Pre/post affected-order rates: 25.8%/4.2%. Matched observed throughput: 1.727 orders per recorded rider-hour. CPO: 344.60 recorded units per order; currency is unverified. [Definitions](docs/METHODOLOGY.md).

## Analytical Framework

[Business question tree](docs/BUSINESS_QUESTIONS.md) → validated source grains → cross-variable segments → complete process decomposition → uncertainty and hypotheses → prioritized operational tests. [All 21 phases](docs/PHASE_COMPLETION.md).

## Demand vs Capacity

Observed rider-hours total 193,500.72. Unknown supply remains unknown; the ratio excludes 9 orders without matching hourly supply. Full calendar hours preserve zero recorded demand. Within-clock relative demand/supply comparisons supplement global bands. [Capacity and threshold tables](outputs/analysis/capacity_bins.csv).

## Bottleneck Analysis

| Stage | Mean minutes | P90 minutes | Share |
|---|---|---|---|
| Creation to final rider notification | 10.58 | 23.93 | 41.1% |
| Final rider notification to acceptance | 0.25 | 0.54 | 1.0% |
| Final rider approach to merchant | 3.13 | 6.60 | 12.2% |
| Final rider waiting at pickup | 4.60 | 9.82 | 17.9% |
| Pickup to destination arrival | 7.17 | 12.56 | 27.9% |


Creation-to-final-notification contributes 51.0% of the late-versus-on-time duration gap. The earlier truncated decomposition overstated pickup waiting's share. [Common-cohort contrasts](outputs/analysis/stage_late_contrasts.csv).

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
- `outputs/`: selected aggregate evidence, dictionary, source hashes and validation records from the original analysis. Private row-level and actor-level outputs are excluded.
- `v16/`: maintained compatibility entrypoints, dashboard launcher and Power BI guide. Historical datasets and native projects are excluded from the public repository.
- `CODEX_TASK.md`: the confirmed 21-phase task brief. The scope and exclusions of this public snapshot are documented in [PUBLICATION.md](docs/PUBLICATION.md).

## How to Run

Use Python 3.12 or later. The source and synthetic tests are usable without private operational records:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pytest
```

Read the published [executive summary](docs/EXECUTIVE_SUMMARY.md) and [aggregate evidence](outputs/analysis/) immediately. The interactive dashboard and full pipeline require the four private input files described in [DATA_ACCESS.md](docs/DATA_ACCESS.md). Obtain them through an authorized channel; this repository does not grant access or redistribution rights.

After placing the supplied files in the ignored `private_data/` directory:

```powershell
.\.venv\Scripts\python.exe -m delivery_ops run --data-dir private_data
.\.venv\Scripts\python.exe -m streamlit run v16/dashboard_v16.py --server.port 8503
```

For independent reproduction, use `python -m delivery_ops run --data-dir private_data --output-dir outputs_repro`, then `python -m delivery_ops compare --compare-dir outputs_repro`. The recorded default seed is 42 and headline bootstrap comparisons use 500 resamples. Generated row-level and actor-level data are ignored by Git. Review generated changes before staging aggregate evidence or reports.

A local full run also generates `outputs/powerbi/PanelDelivery/PanelDelivery.pbip`. It is excluded from the public snapshot because its fact/dimension exports contain private records. Static schema/KPI checks are distinct from native Desktop refresh, which remains unverified. The native report is a semantic scaffold; Streamlit is the authored interactive report. [Power BI guide](v16/GUIA_POWERBI.md).

## Publication and validation

This public copy does not change the numerical business conclusions. The original analysis records 26 canonical checks and two reproducible complete runs; those records describe execution against private inputs, not a fresh raw-data run performed from this public repository. See [validation](docs/VALIDATION_REPORT.md), [copy provenance](outputs/publication_provenance.json) and [publication scope](docs/PUBLICATION.md).

## Author

Santino Cervio  
Industrial Engineering — ITBA  
[GitHub](https://github.com/santinocervio)
