# Power BI semantic export and validation

The canonical Python pipeline produces the analytical data. Streamlit is the authored interactive report. The Power BI deliverable is a semantic model with reusable measures and a report scaffold. Its native Desktop open/refresh status is reported separately from static validation.

The public snapshot includes the exporter source and tests. Private fact/dimension datasets and native projects are excluded; obtain authorized inputs and build them locally following [Data access](../docs/DATA_ACCESS.md).

## Build and validate

Run from the repository root using the project environment:

```powershell
.\.venv\Scripts\python.exe -m delivery_ops powerbi --output-dir build
.\.venv\Scripts\python.exe -m delivery_ops validate-powerbi --output-dir build
```

Use the same output directory as the canonical ETL build. The command reads `orders.parquet` and `hours.parquet` there. Replace `build` above if the canonical run uses another directory. The compatibility scripts `v16/powerbi_export_v16.py` and `v16/generar_pbip.py` forward to `powerbi`; `v16/validar_pbip.py` forwards to the read-only validator. They accept the same command arguments.

The generated project is `<output-dir>/powerbi/PanelDelivery/PanelDelivery.pbip`. The historical native project remains in the original private workspace and is not distributed here. Native execution has not been verified.

## Artifacts and data flow

| Artifact | Purpose |
|---|---|
| `fact_orders.csv` | One row per canonical order; string identifiers, explicit eligibility flags, nullable event counts and unrounded recorded amounts |
| `fact_hours.csv` | Complete calendar-hour spine, including hours with no orders; recorded supply stays missing when unobserved |
| `dim_hour.csv` | Shared hour, date, weather, event and demand/supply/pressure context for both facts |
| `dim_*.csv` | Order attributes such as merchant, recorded final rider, vertical, vehicle, status and buckets |
| `measures.dax` | Generated descriptive measures; the Python definitions are the maintained source |
| `schema.json` | Explicit column types, relationships, expected totals, artifact hashes and report-preservation status |
| `validation.json` | Validation result saved by export; the standalone validator only reads files |
| `PanelDelivery/` | TMDL semantic model, M queries and a new report scaffold, or a preserved existing report |

Both facts relate many-to-one to `dim_hour[hour_id]`. All relationships have single-direction filtering from dimensions to facts. Pressure bands and weather/event filters therefore select the same hours in demand and recorded supply. There is no direct many-to-many fact relationship.

Use fields from `dim_hour` for calendar, weather, events and pressure-band visuals. Use the order dimensions for order-only attributes. Raw fact fields are hidden from the standard field list to favor the defined measures.

Numeric types are declared explicitly. IDs stay text so leading zeros survive. CSVs retain numeric precision and use UTF-8. Power Query converts numbers with `en-US` because the files use a decimal point. Missing numeric values are converted to null before type conversion.

## Metric definitions

| Measure | Definition and denominator |
|---|---|
| Orders | Canonical order rows, including recorded terminal statuses |
| Mean/P90 delivery minutes | Only orders meeting `service_eligible` |
| Late rate | Known late flags within `late_eligible`; unavailable observations are excluded from numerator and denominator |
| Pre/Post affected rate | Affected orders divided by orders with a known corresponding flag |
| Pre/Post events | Number of recorded events; this differs from affected orders when an order has multiple events |
| Recorded order cost | Sum of known canonical total cost; no currency or profit claim is inferred |
| Mean recorded cost | Recorded total divided by orders with known cost |
| Process-stage means | The common `process_eligible` cohort, with creation to final notification, final acceptance, pickup arrival, pickup and destination arrival |
| Recorded rider hours | Sum only where `supply_observed` is true |
| Recorded supply coverage | Calendar hours with recorded supply divided by selected calendar hours |
| Orders per recorded rider hour | Orders in selected hours with recorded supply divided by rider-hours in those same hours |

The load ratio is a coverage-limited descriptive proxy. It is not measured rider utilization or recoverable labor capacity. Undated shifts are excluded; missing supply is not replaced by zero. The ratio is blank when an order-only dimension or a direct fact-order filter is active, since the matching supply population cannot be attributed to those selections. Display `Supply interpretation` and `Recorded supply coverage` next to it.

The raw `f0` field has unverified units. Its export label states that uncertainty. It is not treated as physical order size, revenue or contribution margin. A final-assignment rider ID is not evidence of which rider rejected or abandoned an earlier dispatch.

No model measure claims causal delay, avoidable events, guaranteed savings, recovered rider hours or additional deliverable orders. Descriptive associations require a separately designed intervention before an operational effect can be estimated.

## Open or move the model

Open the generated `.pbip` in a compatible Power BI Desktop installation. Refresh the imported tables and inspect any native errors. If the build directory moved, change the single `DataFolder` Power Query parameter to its new absolute `powerbi` directory. Every table query uses that parameter.

A newly generated report has a named, empty page. Author visuals in Desktop, or use the Streamlit dashboard for the ready-to-use report. Recommended descriptive views are:

1. Order count, service-eligible count, late rate, mean/P90 delivery time, and recorded cost.
2. Affected-order rates by distance, vertical and hour with their known-observation counts alongside them.
3. Pre/Post rates by `dim_hour[pressure_band]`, using the shared hourly context.
4. Recorded supply coverage and order load by calendar hour, with the interpretation notice visible.
5. Merchant and final-rider descriptive comparisons, keeping exposure and eligible counts visible.

Use separate aligned charts for metrics in different units. Avoid labeling an observed difference as an intervention effect.

## Preservation and compatibility

Regeneration updates the canonical CSVs and semantic model. If a report directory already exists at the canonical target, its files are not rewritten. The exporter hashes readable existing report files before and after generation to verify byte preservation. An unreadable existing report is left untouched and reported as unverified.

The historical model is not migrated in place. Its earlier Spanish table names and unsupported simulator measures differ from the canonical schema. If an authored report is deliberately connected to the new model, its field bindings require review in Desktop; preserving report bytes does not prove those bindings remain compatible.

The exporter does not delete stale or inaccessible historical files, change ownership or override access controls. An existing project pointer and its user settings are preserved.

## What validation establishes

Static validation checks CSV hashes and row counts, declared column types, primary-key uniqueness, relationship coverage, TMDL table/column/measure references, shared M configuration, JSON syntax and numerical reconciliation against the canonical input summary. Hourly order counts must reconcile exactly with the order fact. Means, quantiles, costs and rates are compared at a documented numerical tolerance without rounding the exported data.

Regression tests cover leading-zero IDs, unknown outcomes, missing supply, denominator arithmetic, a full hourly spine, mismatched demand, report preservation and tampered numeric data. Fixtures are synthetic test inputs and are never presented as project findings.

These checks do not execute DAX or M, validate every native report field binding, or certify a successful Desktop refresh. `native_check.status` remains `blocked` until a native execution check is performed. Read `status`, `errors`, `warnings` and the native-check result separately; a passed static model is not a native execution pass.
