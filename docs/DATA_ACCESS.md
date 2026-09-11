# Data access and local reproduction

The public repository distributes code, documentation and selected aggregate analytical results. It does not distribute the operational source records or authorize their redistribution.

## Required private inputs

Obtain authorized copies of the four supplied files and keep their names unchanged. Place them in `private_data/` at the repository root, which is ignored by Git, or use another private directory with `--data-dir`.

| Pipeline source | Required filename | Format |
|---|---|---|
| Orders and recorded costs/reasons | `Base de Pedidos (1).csv` | CSV |
| Rider shifts | `Base de Turnos.xlsx` | Excel |
| Hourly weather | `Base de Clima.xlsx` | Excel |
| Special events | `Base de Eventos Especiales.xlsx` | Excel |

[manifest.json](../outputs/manifest.json) records the exact source hashes and row counts used in the published analysis. [The dictionary](../outputs/data_dictionary.csv) documents source fields, units, missingness and interpretations. It contains schema metadata, not source rows. A different dataset requires a new pipeline run and its conclusions may differ.

## Reproduce privately

Install the locked dependencies in a Python 3.12+ virtual environment, then run:

```powershell
.\.venv\Scripts\python.exe -m delivery_ops run --data-dir private_data
.\.venv\Scripts\python.exe -m delivery_ops run --data-dir private_data --output-dir outputs_repro
.\.venv\Scripts\python.exe -m delivery_ops compare --compare-dir outputs_repro
.\.venv\Scripts\python.exe -m streamlit run v16/dashboard_v16.py --server.port 8503
```

Synthetic tests need no source files: `python -m pytest`. The full pipeline, source reconciliations, Streamlit dashboard and Power BI refresh require the private inputs and generated local outputs. GitHub Pages cannot execute a Python or Streamlit application.

## Excluded private artifacts

- All raw CSV and Excel files.
- All Parquet datasets, including orders, cost records, rider-hours, calendar hours and excluded shift records.
- `outputs/analysis/merchant_screening.csv` and `outputs/analysis/rider_exposure.csv`, which expose individual actor identifiers.
- Power BI data exports, dimensions, native projects and local settings.
- Historical V15/V16 datasets, legacy snapshots, logs, caches, virtual environments and credentials.

Where historical evidence records name one of these artifacts, that name documents what was checked during the original private run; it is not a download link. The public analysis table registry omits the two actor-level tables. No raw-data download URL is supplied.

## Responsible reuse

The case is an observational portfolio analysis. It does not imply employment by, endorsement from or affiliation with PedidosYa. Currency, timezone and some source-field interpretations remain unverified. Do not interpret aggregate associations as causal effects, guaranteed savings or individual rider performance evaluations.
