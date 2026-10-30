# Synthetic cell verification

2026-10-23. Loaded the saved `SYNTHETIC_RECORD_001.json` and recomputed **21
numeric output cells**, including bound endpoints, with Python 3 standard-library
arithmetic. All comparisons passed at relative tolerance `1e-12` and absolute
tolerance `1e-14`. Decimal addition independently returned exactly
`0.11124225` for the six variance components and declared zero cross term.

The check also established the record's site/count relationships, symmetric
positive-definite system scale matrix, [0,1] correspondence ranges and explicit
nulls for unprovided preparation count, finite-sample degrees of freedom and
score sampling intervals. It did not infer values for those nulls.

| Output | Recomputed value |
|---|---:|
| S | 2.078347030916761 |
| B | 0.7775614860794029 |
| R | 0.7929855758048903 |
| D | 0.6165950427623814 |
| Proposed c | 0.6165950427623814 |

An initial invocation of `python` exited 127 because that executable name was
unavailable. The successful invocation used `python3`. No reader/scorer was
implemented, no production test suite or scientific investigation was run, and
no real-assay error model, target correspondence or scoring convention was
validated. The upstream corrected assay input itself was supplied, not
recomputed from raw assay operands absent from this port.
