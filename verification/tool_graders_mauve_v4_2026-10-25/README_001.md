# Native Mauve v4 explicit-segment component: verification 001

This is workload A of fixed row C-L202-GenomeAlignment. It implements a native
reader, detached document/selection/component validators, and deterministic
numerical calculations. It does not complete the service or episode path.
No existing shared source, native receipt, inventory, permanent decision record,
model prompt, controller, or tool registration was edited.

Authority: immutable user objective
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The accepted shapes are INTERFACES_002.md and IMPLEMENTATION_OWNERSHIP_003.md;
BOUNDARY_PROPOSAL_001.md supplies the numerical definitions where not superseded.
PURPOSE AND AUTHORITY and all 16 DESIGN PRINCIPLES were reread verbatim after
native-source examination and again before the final handoff.

## Public interfaces

```python
mauve_v4_formats.parse_mauve_v4(data: bytes, *, artifact: dict, encoding: str) -> dict
mauve_v4_format_contracts.validate_mauve_v4_document(document: dict) -> dict
mauve_v4_calculators.calculate_mauve_v4_segments(document: dict, *, selection: dict, inputs: dict | None) -> dict
mauve_v4_calculation_contracts.validate_mauve_v4_selection(selection: dict) -> dict
mauve_v4_calculation_contracts.validate_mauve_v4_components(value: dict) -> dict
```

Encoding is exactly ascii or utf-8. The schema records and keys are those in
interface 002. Every validator returns detached data. Non-null inputs use the
public `bvbrc_genome_alignment_input_contracts.validate_genome_alignment_inputs`;
there is no weaker fallback. The schema dependency is initialized at module
import, not first introduced during a selected calculation.

## Numerical meaning

Each NumericCell carries the explicit selection population, units, state,
origin, numerator/denominator, method ID, evidence and requirement references.
Methods are `mauve_v4_<field>_v1`. Uncertainty is null; exact arithmetic does not
manufacture experimental uncertainty or annotation confidence.

| Field family | Inputs, formula and units | Missing/qualification behavior |
|---|---|---|
| `alignment_columns` | Valid native length/width; columns in the complete explicit segment, calculated projection of its retained NativeNumber | Invalid native width is incompatible; raw native token remains in the document |
| `selected_column_count` | Sum of end-start over explicit ascending disjoint selected ranges; columns | Invalid caller ranges raise; zero selected columns remain zero |
| `selected_nongap_count`, `selected_gap_count` | Literal nongap/gap characters in the selected row columns; characters | For present coordinate-only anchors, nongaps=selected columns and gaps=0, without claiming known nucleotide symbols. Coordinate-only absent members have nongaps=0; their unobserved gap count is not measured |
| `selected_canonical_count`, `selected_ambiguity_count`, `selected_other_count` | Selected row characters classified as A/C/G/T, R/Y/S/W/K/M/B/D/H/V/N, or remaining nongap symbols; characters | Without source symbols, present anchors are missing, absent anchors are not measured. `uppercase` normalizes before classification; `preserve` leaves lowercase in other. Native unknown symbols remain retained malformed material rather than trusted biological rows |
| Pair counts | Mutually exclusive identical canonical, canonical substitution, A-only-gap, B-only-gap, both-gap, ambiguous/other counts over selected columns; columns | Pair absence is not coobserved, never zero identity. Missing source symbols, incomplete membership, and incompatible rows retain distinct unavailable states |
| `comparable_canonical`, `identity_fraction` | Identical+substitutions; identical/comparable | A zero denominator produces not_measured with null fraction and explicit 0/0; no mean of percentages or new aggregate confidence is created |
| Native member interval | For signed start s and full segment residue count r, `[abs(s)-1, abs(s)-1+r)`; positive/negative sign gives strand | Ungapped r is native length; gapped r is full-row nongaps. Zero start is biological absence and has no interval |
| Selected placements | Nongap source positions in chosen columns, compressed into intervals on the forward native axis; strand retained | Reverse positions descend from the rightmost nucleotide. No positions or alignment columns are invented between anchors |
| `known_union_bases` | Length of union of known placements; nucleotides | Available for an explicitly known partial subset, with `partial_selected` population qualification |
| `placement_bases` | Sum of placement lengths; nucleotide_placements | Repeated representations remain separate placements, not independent evidence |
| `multiply_represented_bases` | Length of native positions covered by at least two placements; nucleotides | Overlap is explicitly diagnosed |
| `excess_placement_bases` | Placement sum minus unique union; nucleotide_placements | Does not inflate unique coverage |
| `denominator_bases` | Explicit native declared member length (`native_observation`) or exact C-validated staged length (`calculated`); nucleotides | No automatic substitution. Missing native declarations require primary output; conflicting declarations are incompatible. Unverified source bindings cannot supply a denominator. `none` means not measured |
| `coverage_fraction` | Known union / the selected denominator | Source mismatch/out-of-bounds or malformed dependent native values are incompatible. Missing selected rows make the whole fraction truncated. Zero denominator is not measured |
| `complement_intervals`, `complement_bases` | Complement within `[0, denominator)` and its length; nucleotides | Only for complete selected populations with usable matching denominators; unavailable otherwise |

Raw gapped rows belonging to absent-zero members retain their literal gap
counts. Those characters do not establish biological pair correspondence.
For an incomplete or malformed positional N-row section, the entire section's
member assignments remain untrusted; original observed row ordinals survive in
the document. Independently complete neighboring segments can be selected.

Source extraction reads only the supplied validated components and exact record
symbols. Gapped source comparison is case-insensitive literal IUPAC equality;
N is not a wildcard. A source mismatch preserves native counts and invalidates
dependent source fractions. Exact native path tokens are checked; basename
similarity cannot bind an input. C extraction/association and host custody remain
responsible for authenticating supplied metadata and actual task relationships.

## Filled examples and evidence levels

`official_small.document.json` and `official_small.components.json` use the
original upstream small.mauve bytes, SHA256
`a0e700b702070ebd061f6ca5c5b0d9338ad8c330ad16b94c9a0090041cd8cd88`, 1007 bytes,
from koadman/mauve revision `56238aefa0f0c25134f3f0b244c0d7560cbaa9d7`.
Its original acquisition receipt is preserved in the boundary directory.

* Five intervals contain eight explicit segments.
* Member 0 covers 690/693 native-declared bases; the complement is `[578,581)`.
  Member 1 covers 2000/2000. These are native-declared, not genome-census fractions.
* The emitted gapped segment has width 269, nongaps 4/269, gaps 265/0, and
  canonical identity 4/4. The three shared coordinate-only anchors have missing
  identity because their characters are not emitted.

`synthetic_reverse_overlap.*.json` and `synthetic_supplied_inputs.json` are
explicitly synthetic fixtures, including the task/custody metadata. Source
lengths are 6 and 4 while native declarations are 100 and 100. A reverse anchor
extracts `TACG`; three selected placements give member 0 union=5, placement
sum=12, multiply represented=4, excess=7, source fraction=5/6. Member 1 gives
union=4, sum=12, multiply represented=4, excess=8, source fraction=4/4.
No fixture metadata claims a real BV-BRC task.

## Commands and results

* `python3 -m pytest -q tests/test_mauve_v4_formats.py tests/test_mauve_v4_calculators.py`
  passed 78 owned tests after the numerical and missing-state corrections.
* `python3 -m pytest -q tests/test_mauve_v4_formats.py tests/test_mauve_v4_calculators.py tests/test_bvbrc_genome_alignment_input_contracts.py --junitxml=verification/tool_graders_mauve_v4_2026-10-25/pytest_001.xml`
  passed 128 tests in 0.56 seconds. The shared C validator tests account for the
  additional 50 tests. The JUnit receipt records the actual execution.
* `python3 verification/tool_graders_mauve_v4_2026-10-25/run_verification.py`
  reproduced the filled examples and checked 5235 nested saved-field mutations
  with zero unexpected exception types. Some replacements are legitimately
  valid; targeted tests establish the scientific rejection cases.

Tests cover digest/encoding/format failures, metadata conflicts, raw numeric
tokens, whitespace filenames, malformed/truncated gapped sections, observed
ordinals, reverse coordinates, ambiguity/case policy, zero denominators,
source mismatch, exact path/source-length corruption, repeated/overlapping
placements, and invalid saved numeric relationships. Recalculation from saved
documents with changed column selections is exercised with filesystem reads,
network sockets, native process creation and native parsing blocked. Saved
component validation is also exercised with the scientific calculator blocked.
Owned file hashes and generated artifact hashes are in VERIFICATION_001.json.

## Limits and remaining consumers

No new native scientific alignment, installation, live BV-BRC call, API task,
or HPC job ran. Local artifacts are small, with no added wall-time budget.
The official source example establishes native-format/numerical behavior, not
the deployed service's version or success. No whole-genome census, inter-anchor
alignment, native LCB score, independence weight, or annotation score is inferred.
Unknown syntax remains explicit partial data. Syntax completeness does not
prove complete transport or a successful native execution.

C's actual input extraction and same-task artifact associations, D's sheet
composition, E's adapter/projections, F's typed return and G's shared registration
remain separate work. The historical legacy wrapper/XMFA incompatibility remains
unresolved by this parser. Source authentication, live native artifacts and a
complete selected-tool/child/artifact/typed-return path remain unverified here.
