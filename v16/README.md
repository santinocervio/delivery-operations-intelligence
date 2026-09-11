# V16 compatibility entrypoints

The maintained project is [Delivery Operations Intelligence](../README.md). These filenames forward to the canonical Python package; they do not contain independent analytical definitions.

Run the pipeline from the repository root with `python -m delivery_ops run --data-dir private_data`. After a private local build, `abrir_dashboard.bat` launches Streamlit on port 8503.

The public copy excludes historical `salidas_v16`, `powerbi`, `PanelDelivery` and `legacy` artifacts. Raw inputs and generated row-level outputs are also excluded. See [data access](../docs/DATA_ACCESS.md), [methodology](../docs/METHODOLOGY.md) and the [Power BI guide](GUIA_POWERBI.md).
