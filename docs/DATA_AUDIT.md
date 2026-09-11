# Data Audit

## Source inventory

| Source | File | Rows | SHA-256 |
|---|---|---|---|
| events | Base de Eventos Especiales.xlsx | 78 | add9cae64743f2466034e2787b52adcd8a2afb703375b0d94cc0f80955ddec86 |
| orders | Base de Pedidos (1).csv | 347644 | 69d2df9138b060ef35bf45cf917688c9c2b93ee30503a50abbc2cbcadc67dafb |
| shifts | Base de Turnos.xlsx | 176235 | 38c7f6d24c523b13b7ac216d1e9de0b649ef5264e84b9457c21cfcbaf73368c3 |
| weather | Base de Clima.xlsx | 2136 | 6bb4248788f57c445812b1e0c3189716a127938ce8c022ebeb948f70b08c0ec9 |


## Corrections and exclusions

- 347,644 source order records represent 334,144 unique orders. Exactly one principal row is required; recorded cost reconciles within floating-point tolerance.
- 67,806 shift records have missing dates/times. Their real operational meaning is undocumented; they are neither imputed nor automatically interpreted as worked hours.
- The legacy parser loses 25,052 otherwise complete shift records. Explicit mixed-format parsing loses 0. The observed window contains 193,500.72 rider-hours.
- 4 positive source shifts exceed 16 hours. Within-window supply excluding those shifts is 193,500.72 unmerged rider-hours; overlap removal is 0.00 hours.
- 6 order hours, containing 9 orders, lack usable hourly supply. 53 recorded-supply hours contain no recorded orders.
- 20,206 orders have a final rider with no dated shift in the observed window. Aggregate supply observation does not prove individual rider coverage.
- Weather covers 695 of 743 calendar hours and 312,978 orders. Unknown weather is a separate category.
- 5 exact event duplicates are identified; distinct overlapping events and holidays retain independent flags/counts.

## Complete dictionary and provenance

[Data dictionary](../outputs/data_dictionary.csv) covers every raw and canonical variable, meaning, unit, type, missing count/fraction, source and semantic confidence. [Full audit](../outputs/data_audit.json) and [manifest](../outputs/manifest.json) retain numeric evidence.

Timestamp offsets, currency, wind units and opaque platform fields have no authoritative source dictionary in this repository. Assumptions remain labelled. The project uses the supplied extract as observed data; its production provenance is not independently verified.
