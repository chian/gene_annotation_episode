# Supporting grader/operation accounting

The scientific-only census omitted 50 historical supporting rows: 17 preparation tools and 33 BV-BRC Data collection/query obligations. The historical total remains **114 inventory rows** (64 + 17 + 33).

Across the supplied scientific baseline and these supporting paths there are **45 sheet authorities, 132 authority/operation links and 120 distinct operation names**. Of those authorities, **44 contain some numerical components** and one is typed extraction/validation only. Numerical supporting counts are not scientific-confidence scores. One scientific authority has no dedicated named alias, so 43 of the 44 numerically capable authorities have named links.

| Authority | Historical preparation tools | Linked operation names | Meaning |
|---|---:|---:|---|
| HMMER alignment preparation | 2 | 6 | Alignment/model measurements, mask/map relationships and validation; no gene-function confidence. |
| HMMER artifact preparation | 3 | 7 | Decoded model/key/artifact counts, probability-body differences where decoded, and custody/format checks; opaque content remains unknown. |
| HMMER generated sequences | 1 | 5 | Generated sequence composition, counts, alignment quantities and consensus checks; not observed biological evidence. |
| HMMER score simulation | 1 | 4 | Native and independently fitted random-score distribution quantities with their selected populations. |
| HMMER model statistics | 1 | 1 | Native model statistics and explicit-parameter recalculation; missing background is unavailable. |
| HMMER FM index and literal matches | 2 | 3 | Index/source populations and literal-location/count validation; raw FM intervals are distinct from validated source matches. |
| Infernal preparation (one shared sheet, three branches) | 7 | 27 | 18 statistics/generated-data modes plus 9 artifact-validation modes; the latter compute counts/bytes and checks, not scientific-confidence scores. Branches are not extra independent analyses. |
| BV-BRC Data pages/counts/facets | Shared 33 Data rows | 2 | Native/valid/invalid row counts and same-response exact-population facet fractions; counts are not evidence confidence. |
| BV-BRC feature-sequence joins | Shared 33 Data rows | 2 | Selected features, native sequence occurrences, distinct exact sequence identities, missing/conflicting relationships and length agreement. |
| BV-BRC molecular measurements and relationships | Shared 33 Data rows | 2 | Retains source numerical measurements and experiment/bioset/feature/condition/unit associations. No separate numerical scoring calculator. |

Infernal's 27 links are **15 statistics/build/calibration + 3 generated-data + 9 artifact validation**. These are three branches of one sheet. The artifact branch computes counts and bytes as well as checks; it is not a scientific scoring path.

BV-BRC Data's three sheets share the same two names, `api.bvbrc.data.query` and `api.bvbrc.data.result`. The query supplies the response; result publication applies the selected calculator/extractor. This contributes six links but only two unique names.

| Linked names per authority | Number of authorities |
|---:|---:|
| 0 | 1 |
| 1 | 19 |
| 2 | 11 |
| 3 | 5 |
| 4 | 1 |
| 5 | 3 |
| 6 | 2 |
| 7 | 1 |
| 11 | 1 |
| 27 | 1 |

The arithmetic is **65 scientific names + 26 HMMER preparation names + 27 Infernal preparation names + 2 Data names = 120**. Links are **73 + 26 + 27 + 6 = 132**; numerical-component authorities account for 130 links and the typed molecular sheet for two.

Every supporting template has a source route into the appropriate result worker/reader/calculator or validator. Preparation exposure is conditional on explicit configured software bindings; installation, deployment, native execution and episode replay were not tested by this census. No production files, progress rows or earlier evidence were changed.

Exact names, sheet/calculator authorities, AST binding references and source hashes are retained in `census.json`. Different modes remain different names, not new algorithms or new historical inventory rows.
