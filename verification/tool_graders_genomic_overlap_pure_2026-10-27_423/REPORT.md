# G1 pure genomic overlap handoff

Implemented only the accepted G1 responsibilities for
`B-L123-analyze_genomic_region_overlap`. This is a supplied-data numerical
implementation, not a bound scientific tool or full Workflow completion.

## Files and interfaces

Production files are `gene_annotation_episode/genomic_overlap_contracts.py`,
`genomic_overlap_inputs.py`, and `genomic_overlap_calculations.py`. Tests are
`tests/test_genomic_overlap_inputs.py` and
`tests/test_genomic_overlap_calculations.py`. All other work is in this packet.
No shared runtime, catalog, inventory, model prompt, literature grader, W05,
prior verification record or running packet410 job was changed.

The modules export HANDOFF's five exact reader/builder/calculator signatures,
all declared record aliases including the six long names, and the three shared
schema/validation/canonical-hash helpers. The fixed 62 schema definitions are a
Python constant matching the frozen DATA_CONTRACT definitions. Production does
not load verification files. Structural validation is strict finite JSON, with
bool and floating-point values rejected for integer fields; returned records and
schemas are detached. Readers/builders/calculators additionally validate source
identity, original row joins, coordinates, duplicate groups, canonical order,
native endpoints and widths, reference relations, complete/partial state and
request ordering. No acquisition, native execution, resource choice, model call,
execution authority or credit observation occurs in these functions.

Original valid and invalid occurrences keep their data ordinals and source
locators; headers do not consume an occurrence ordinal. Native row identity
joins exact tokens, never names. Duplicate input occurrences remain separate;
repeated native pairs are rejected. Known canonical-file identities are checked
against the normalized canonical BED4 bytes, while unknown null identities stay
legal for supplied output. Exact native width sums, unique unions and
occurrence-based denominators remain separate quantities. Component snapshots
retain the canonical sheet hash and supplied rational parameters.

The accepted additive invocation rule is implemented from packet422
`NATIVE_METADATA_CLARIFICATIONS_003.md`: compatible reordered/unsorted declared
intersect invocations and `intersectBed` preserve complete supplied-table scope;
uninterpreted or restrictive options produce a located parse failure and partial
results. Verified valid rows remain eligible for explicit subset lower bounds.
Empty argv with explicit supplied completeness is legal. Live original-action
and invocation authority remains the host's responsibility.

## Verification actually executed

All pytest and numerical examples ran through `local_jobs`, using readonly
executed-source snapshots, 20 GiB RAM, 4 GiB scratch, zero swap and no wall
allocation. Each attempt retains selected request, original/after source pins,
stdout/stderr, JUnit output, local lifecycle state and final receipt.

| Attempt | Focused tests | Result | Executed pins |
| --- | ---: | --- | --- |
| check001 | 81 | passed, 3.88 s pytest | unchanged; no checkout drift |
| check002 | 85 | passed, 15.80 s pytest | unchanged; no checkout drift |
| check003 | 96 | passed, 16.16 s pytest | unchanged; no checkout drift |

The final receipt confirms memory_max 21474836480, memory_swap_max 0,
runtime_max infinity and systemd control-group execution. Scratch is monitored
visible allocated bytes with possible overshoot; the existing per-file size
limit is 4294967296. This report does not upgrade that enforcement into a hard
aggregate scratch quota.

Tests cover the exact worked418 read/parse/sheet/component chain, variable BED
widths including BED12 retained optional fields, array extra JSON values, invalid
coordinates and Unicode, source locators, duplicates, touching boundaries,
different chromosomes, long coordinates through 2**63-1, no-hit/empty/missing/
partial/malformed distinctions, foreign native tokens, stale digests, native
width conflicts, wrong original bindings, reference absence/conflicts, and an
independent valid pair beside an invalid third input. Saved recalculation runs
with file acquisition, process execution and networking patched unavailable,
leaves source data and earlier components unchanged, and uses exact integer
threshold cross-products. A 2,048-region sparse example verifies no-hit zeros,
ordered adjacency and selected/unfiltered populations without a runtime cutoff.

Actual retained packet421 bytes were read, not rerun. Its native tokens are
A1/B1, whereas the frozen G1 contract requires s0_r0/s1_r0. The untouched bytes
therefore test explicit token incompatibility. Seven additional numerical tests
explicitly remap these tokens as derived fixtures; they are not claimed as new
or untouched native canonical-token evidence. G2/root owns that later actual
bound-driver verification.

## Checkable numerical results

The full populated supplied-data example is `check003/FILLED_EXAMPLE.json`,
labeled hand-worked synthetic supplied data with no execution claim.

| Case | Pair count | Pairwise width sum | Unique shared bp | Denominator / ratio |
| --- | ---: | ---: | ---: | --- |
| A=[0,10),[5,15); B=[7,12) | 2 | 8 | 5 | combined union 15; Jaccard 5/15 |
| Same source, minimum overlap 4 | selected 1 | selected 5 | selected 5 | affected A occurrences 1/2; unfiltered Jaccard still 5/15 |
| Two duplicate A and two duplicate B occurrences | 4 | 20 | 5 | combined union 15; Jaccard 5/15 |
| First valid width-3 row plus truncated second row | observed lower bound 1 | observed lower bound 3 | observed lower bound 3 | exact totals/Jaccard null; A/B unions remain 15/5 |
| Both valid inputs empty | 0 | 0 | 0 | combined union 0; Jaccard null, zero_denominator |

The set arithmetic and numeric results remain coordinate geometry under the
supplied reference qualification. Missing references do not become compatibility
claims, and conflicts do not become a fabricated numeric penalty.

## Final source pins

| File | SHA-256 |
| --- | --- |
| genomic_overlap_contracts.py | 1bde770d3360feb38d2d3c77a5ab8c44f2c810cd86dbbf9cf15d0b658d4a906e |
| genomic_overlap_inputs.py | f84562475133ac699a1f82d42d4693a9f50a3ce16ea4f457a5e56ce643b6ee23 |
| genomic_overlap_calculations.py | 1c7c4f4bd08323eb1903ac94774ca7d7d6d6829cc4ab6a4744fd96a4d0de9e84 |
| test_genomic_overlap_inputs.py | ba05b3e50845d4f2c1047128332e541cb8d479f05e3081c32a182efda60a9fa3 |
| test_genomic_overlap_calculations.py | bf2cf1b5ad813161476f8d4856f1b71224656be870fae682a3128f248c01cc5b |

`RESULT.json` gives exact paths and the final executed pin records. Contracts418
and immutable goal hashes were checked against the accepted422 pins. The
immutable objective and all sixteen principles were read verbatim after native
examination and again at completion, followed by the accepted root contract,
HANDOFF, numerical formulas and additive invocation clarification.

## Remaining owners and explicit limits

G3a owns projection. It reported packet424/check003 passing all 41 projection
tests, including the joined reader/calculator/projection path, using these exact
final G1 source pins with no executed or checkout drift; those receipts belong
to packet424. Root/G2 still own child execution binding, actual canonical-token
native output, full artifact custody, selected-action authority, replay and
full Workflow return verification. No completed-scientific-tool count is
increased by this pure handoff.

The parsers require supplied bytes/streams and metadata; they do not retain
artifacts themselves. Retention of complete original bytes remains the caller's
responsibility. When supplied bytes exceed the declared source size,418 cannot
represent an honest parsed_byte_count greater than that identity's size. The
reader returns unavailable with actual observed size versus declared size and
zero parsed bytes, instead of trimming or relabeling the foreign bytes. Rebinding
the correctly retained identity is the repair. Same-size digest conflicts and
short data retain valid parsed rows with partial qualification; unverified byte
identity cannot establish genuine subset lower bounds.

Large tables are processed in memory inside the caller's bounded worker. Ordered
adjacency avoids a region-by-edge scan; this is not a disk-streaming calculator
or an execution resource fallback. A source declaration of completeness is
preserved as a supplied assertion: the calculator does not invent unreported
native pairs by rerunning intersection from coordinates.
