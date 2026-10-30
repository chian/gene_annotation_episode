# A103 numerical contrast ready for review

The missing second empirical scoring operand is supplied by a **new STRING neighborhood observation tied to the published BioY case**, not by the paper's copy counts.

| Separate one-question example | Actual neighborhood `s` | `t=+1*s` | `S` | `O` | `c=S(1−O)` | Combined score excluded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing RibK–RibB reference pair | .956 | .956 | .956 | 0 | **.956** | .959 |
| New SB1003 BioY–BioN reference pair | .844 | .844 | .844 | 0 | **.844** | .999 |

Each example has weight 1; `C` and `E` are not applicable to the native route. The .112 neighborhood difference is descriptive. Combined scores reverse the order by .040 because they mix channels; neither difference is a calibrated comparison of biological truth across species.

The new record was retrieved on **2026-10-24 UTC** for `272942.RCAP_rcc03249` / `272942.RCAP_rcc03250`. STRING's BioN label is `cbiQ3`; UniProt D5ARG9 explicitly supplies `bioN`, that synonym, the same locus and STRING cross-reference. Both reference proteins identify strain SB1003/taxon 272942. This verifies the reference-locus link, **not the historical assayed construct's sequence**. The .844 value is not a 2007 paper measurement and is not assigned to ybhP or any unmapped supplied target.

The historical BioY fraction remains approximate and lacks an unambiguous recovered spatial count table; `50/150` is not fabricated. Its count-route coordinate remains null with `[0,1]` bounds. Biological calibration uncertainty and direct/transferred neighborhood breakdown are unreported for the new native row.

The exact returned pair, complete query parameters, response counts, aliases and version observation are retained. Twenty-eight bounded identity/arithmetic checks passed. A separate field-format check validates the final `filled_cells_002.json` without changing numerical values. First and second retrievals represent the same pair and count once.

This supplies the requested numerical example for the parent's review. Existing formulas and records are unchanged. Axis/goal completion remains the parent's decision, and user judgment of this addition is still outstanding.
