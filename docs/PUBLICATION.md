# Public repository scope

This is a curated public copy of the completed Delivery Operations Intelligence project. It is intended to demonstrate operational reasoning, reproducible implementation and transparent evidence limits.

## Included

- Canonical Python source and synthetic regression tests.
- English business reports, source dictionary, original task brief and dependency declarations.
- Maintained V16 compatibility scripts and guide; Streamlit remains the primary interface.
- Seventeen aggregate analysis CSV tables, executive findings and aggregate analytical JSON.
- Original source SHA-256 hashes, aggregate audit, canonical validation, reproducibility and report-validation records.
- A file-by-file copy-provenance manifest and checks executed on this public snapshot.

## Excluded

Raw inputs, individual rider and merchant tables, all Parquet files, Power BI fact/dimension exports, native projects, historical datasets, logs, environments and secrets. See [DATA_ACCESS.md](DATA_ACCESS.md) for exact inputs and reproduction instructions. The dictionary may name identifier fields; it does not contain identifier values.

## Changes for publication

Numerical findings and aggregate CSV bytes are preserved from the original analysis. The aggregate analysis JSON omits links to the two private actor-level tables and carries a publication note. README, guides and validation links explain which artifacts require private input. The dashboard launcher checks for private canonical orders before starting. Absolute local paths are removed from public metadata if present. Source files otherwise remain unchanged.

The public record preserves original checks as historical evidence; it does not claim that private-source checks can run without the private data. Native Power BI execution remains unverified. The package is not represented as an official PedidosYa product or proof of employment.

## Provenance and checks

[publication_provenance.json](../outputs/publication_provenance.json) lists source and public hashes for every copied artifact, identifies publication adaptations and verifies that recorded raw-source hashes match the unchanged private files. It contains repository-relative filenames only.

[publication_validation.json](../outputs/publication_validation.json) records tests and publication checks on this curated copy. The aggregate allowlist in `.gitignore` prevents normal staging of regenerated raw, actor-level and Power BI outputs. Always review staged changes before publishing a later run.
