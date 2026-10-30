# A104 research draft handoff

Status: reviewable numerical sheet draft delivered. No axis is marked complete,
no formula is adopted, and no production code, reader, prompt, library, scientific
run, alignment or job was changed or launched.

## Review order and files

The parent must retain the required full authority reset after each paper-specific
packet, before its interpretation or the next packet. Scientific content is
separated so that this can be done without opening the cross-case synthesis first.

1. `PAPER01_PORPHYRAN_2012_BOUNDARY_001.md`
2. `PAPER02_THYX_2007_BOUNDARY_001.md`
3. `PAPER03_PORPHYRAN_2010_PHYLOGENY_001.md`
4. `A104_NUMERICAL_SHEET_DRAFT_001.md` — cross-case numerical synthesis and
   complete proposed cell/compilation specification.

Each paper's full post-inspection reset is recorded in the correspondingly
numbered `authority_reset_paper01_001.json`, `authority_reset_paper02_001.json`
and `authority_reset_paper03_001.json`. `initial_authority_read_001.json` records
the initial read and its repairs. `TASK_SCOPE_001.md` preserves the bounded
assignment, current A104 direction, latest human instruction and active-goal
attachment location. No permanent authority files were mutated.

## Draft-criterion coverage

| Requested draft item | Location |
| --- | --- |
| Exact numerical cells, types, input units and denominators | Sheet section 2 |
| Explicit bounded combination and all scale/coefficient meanings | Sheet section 3 |
| Contrasting published numerical inputs and checked conversions | Paper 03 packet; sheet section 4 |
| Fully filled explicitly synthetic endpoint | Sheet section 5; arithmetic fixture and results |
| Dependence, conflicts, support-method distinctions, nondetection and missingness | Sheet sections 3 and 6 |
| Source-to-cell trace and ambiguity-resolving complements | Sheet section 7; individual paper packets |
| Exact future-reader input/output contracts and unimplemented status | Sheet section 8 |
| Remaining policy judgment, data gaps and scope limits | Sheet section 9 |

All calculations and coefficients are explicit within the sheet's declared
region/ensemble scope. The sheet identifies missing published operands rather
than replacing them with scores. Integration across incompatible target scopes
is explicitly outside that numerical scope. The parent must print the useful
examples and formulas for the user's judgment; this file does not substitute for
that conversation or for the user's feedback.

## Actual checks and limits

`arithmetic_checks_001.py` executed successfully with Python 3 and no external
packages. `arithmetic_results_001.json` retains its results. The checks cover
exact rational arithmetic, synthetic rooted-triplet enumeration, synthetic
patristic distances, the complete synthetic endpoint, missingness examples,
and 320 bounded-output combinations. Published figure topology was manually
inspected; this script does not independently reconstruct the publication.

No production tests or biological computations were run. No empirical
calibration, implementation of a reader contract, or full real-data aggregate
is claimed. The study-specific inspection limits are preserved in the source
packets and reset records.

`ARTIFACT_MANIFEST_001.json` records byte sizes and SHA-256 digests of the 28
artifacts present before this handoff and manifest were created. The manifest
and this handoff are not recursively included in that inventory.
