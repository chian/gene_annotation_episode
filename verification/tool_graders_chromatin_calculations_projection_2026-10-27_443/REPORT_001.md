# C2 chromatin calculations and selected numerical returns

Additive implementation evidence, 2026-10-27. This packet covers the fixed
B-L124-analyze_chromatin_interactions calculations/projection workload only.
It changes no tool tally, goal, evidence axis, literature grader, W05 formula,
shared execution behavior, resource decision, model prompt or accounting row.

The complete original attachment was read at the start. Its objective and all
sixteen design principles were reread verbatim after source/interface examination
and again before this report, followed by the agreed numerical/return contract.
The attachment SHA256 is
11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7.
No GOAL.md was read. This report is implementation evidence, not goal authority.

## Implemented owned files and ports

`gene_annotation_episode/chromatin_interaction_calculations.py`:

- `calculate_contact_enrichment(sheet, *, tables, normalization, parameters)`
- `calculate_insulation_components(sheet, *, tables, normalization, parameters)`
- `calculate_chromatin_components(sheet, *, tables, parameters)`

`gene_annotation_episode/chromatin_interaction_result_views.py`:

- `project_chromatin_result(sheet, components, *, selector)`

Tests are exclusively `tests/test_chromatin_interaction_calculations.py` and
`tests/test_chromatin_interaction_result_views.py`. Supporting fixture/runner
files and evidence are contained in this packet. Final exact SHA256 pins are in
OWNED_SOURCE_PINS.sha256 and check006/source_pins_before.json.

The accepted441/439 signatures and closed array/record shapes are used directly.
C1 owns the real contracts, readers, tables and sheet construction. There is no
stand-in production schema or parser. The BLAST HSP sheet/input/calculator pair
was inspected for separation of responsibilities; its biological formula was
not copied. No production code imports verification files.

## Numerical behavior

The contact calculation uses exact selected-population diagonals. Native counts,
explicitly selected supplied weights, transformed contacts, sums, sums of squares,
means, population variances, ratios, flags and representation multiplicities stay
separate. Raw mode leaves normalized_contact not_measured. Native/supplied
reference assertions and unused metadata remain in the unchanged source sheet.
Unknown reference identity is qualified; conflicting assertions prevent anchor
association while independent matrix statistics survive.

Sorted sparse arrays are traversed repeatedly, with native pair searches and
one accumulator per separation. No Python list/dictionary of every pixel and no
dense whole-chromosome copy is created. Established sparse zeros contribute their
exact counts and centered moments in bulk. Masked bins are excluded from the
diagonal denominator; missing/invalid weights do not become masks or trigger raw
fallback. Stable partial sums and an origin-centered second pass preserve small
integer differences above the floating-point exact-integer range. Nonfinite,
overflow and unrepresentable positive-moment results are explicitly unavailable,
independently by component.

Every full insulation window is retained, including the final one. Incomplete
windows keep known counts/sums, do not become zero, and do not allow the boundary
rule to skip a missing immediate neighbor. Strict local minima and strict supplied
thresholds define boundaries; domains join adjacent selected boundaries without
adding region edges. These are heuristic measurements, not p/q values or calibrated
uncertainty. Supplied precomputed weights are applied; no balancing was performed.

Projection supports all five accepted variants, explicit keys and flattened pages,
exact requested field order, and mandatory keys/qualifications. It validates source
sheet digests, exact ordered table identities, mode/parameter snapshots, native
pair associations, measurement population keys and domain relationships. A selected
page does not alter any calculation population. Selected null fields have located
qualifications; unrelated pair failures remain private.

Root approved domain keys based on frozen population ordinal (`p0.domain0`, etc.)
to remain within the closed key length even for a 256-character population key.
The exact population_key remains a separate foreign key. No record shape changed.

C1 identified a retained malformed lower-triangle row case during integration.
C2 excludes such a row from the mathematical upper triangle only for a partial
population with a matching native_parse/malformed_native_index failure at every
exact original source-row locator. Its source array remains unchanged, and the
incomplete population cannot produce a full expectation/fold. Undiagnosed lower
rows reject rather than being silently reinterpreted.

## Executed verification

Every pytest/native check used existing local_jobs/native_lifecycle with an
immutable source snapshot, 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time
allocation. Scratch enforcement is monitored with possible overshoot; this is
not described as an aggregate hard filesystem quota. All handles were followed
to terminal results. Source/binary pins and failures are retained for every run.

| Run | Actual result | Purpose |
|---|---|---|
| check001 | Collection failed, 0 tests | Test-only import spelling used a hyphenated directory in Python import syntax; corrected. |
| check002 | 45 passed, 1 failed | Fixture attempted to mutate the same read-only weight array; corrected by copying before the next fixture variant. |
| check003 | 50 passed | Full focused suite including actual440 Cooler files through C1 and C2. |
| check004 | 54 passed | Added numerical-range, complete sparse-zero, mask and population-order checks. |
| check005 | 12 passed, 43 deselected | Focused domain/insulation/order follow-up including maximal population key. |
| check006 | 10 passed, 46 deselected | Final native/partial/arithmetic/maximal-key follow-up, retained numerical output, and diagnosed lower-triangle case. |

All executed snapshots and binary pins were unchanged. check004 observed one
concurrent checkout change in literature_episodes.py; the immutable executed
snapshot was unchanged, and C2 did not modify or revert that file. check006
observed no checkout drift. The final test inventory contains 56 cases; it is
not claimed that all 56 were run together against the final snapshot. The changed
domain and retained-malformed-row paths were specifically rerun after the full
54-case pass. No broad unrelated suite was run.

check003 onward used the actual440 reference Python, h5py3.16.0 and NumPy2.5.0.
The test runner explicitly appends the existing root environment for jsonschema
and pins that dependency closure. This test environment composition is not a
claim that C3's production SoftwareBinding is established. No environment was
installed or modified. Earlier pure checks used the existing root interpreter
and NumPy2.5.4, with their own separate pins.

## Filled actual numerical examples

check006 retained actual emitted sheets/components under temporary/pytest. Their
selected numerical values are collected in NUMERICAL_EXAMPLES_001.json.

| Actual serialized synthetic native input | Verified values |
|---|---|
|440 four-bin Cooler, raw | Anchor contact6; d2 count2, sum8, mean4, variance4; fold1.5. |
|440 same four-bin Cooler, supplied weights[1,2,1,2] | Raw anchor6 remains; selected d2 sum14, mean7, variance1; fold6/7. |
|440 six-bin sparse Cooler | Full cross sums[5,1,5,1,5]; mean3.4; floating representation of variance3.84; minima z=-1.224744871391589; boundaries20/40bp; domain[20,40), length20bp=0.02kb. |

Changing the fold threshold and changing insulation threshold to-1.3 recalculated
the saved data without source acquisition/re-extraction; the latter produced no
boundaries/domains. Tests also verified zero contact with positive expectation
gives fold0, expectation0 gives undefined fold, actual duplicate/same-bin element
occurrences remain distinct from bin pairs, source NaN masks and invalid weights
differ, and an absent/malformed/missing cell does not become an observed zero.

The native files are genuine HDF5 serializations of synthetic inputs, not
biological experiments. WORKED_RECORDS JSON is a hand-authored numerical oracle,
not native-format evidence. Actual input parsing in these joined checks used C1's
production ports and real440 bytes, not fixture-format stand-ins.

## Limits

C2 did not run or verify the full selected library→launch→local child→capture→
worker→receiving episode path, credit/continuation, or a live biological dataset.
Those remain C3/root integration work. HIC native parsing remains a separate
unfinished format task. Large chromosome-scale throughput/resource-fit behavior
was not benchmarked. Passing these bounded component/native joins does not
establish a completed tool or increase any capability tally.
