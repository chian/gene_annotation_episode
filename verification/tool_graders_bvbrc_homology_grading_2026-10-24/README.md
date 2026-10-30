# H2 pure BV-BRC Homology scientific adapters

This checkpoint implements three new pure modules and their tests. It does
not declare Homology installed, a live BV-BRC result acquired, or episode
communication complete. Every numerical fixture is explicitly **SYNTHETIC**.
No BLAST executable, local database search, remote job, network acquisition,
LLM, resource choice, credit observation or continuation policy ran here.

The controlling objective and all sixteen principles were reread verbatim
before work, after source/native transformation study, and before handoff.
H2/H1 contracts were reread. Existing shared BLAST parser, geometry, pairwise,
database and metadata implementation paths were inspected; shared code was not
edited by H2. H1's new explicit association inputs are consumed directly.
Host acquisition, persistence, remote custody, result publication, selected
child execution and typed-return admission remain separate work.

## Actual verification

The new reader/grader tests contain 131 synthetic cases. The affected combined
suite passed **335 tests** using `.venv/bin/python -m pytest -q` on:

- `tests/test_bvbrc_homology_inputs.py`
- `tests/test_bvbrc_homology_grader.py`
- `tests/test_blast_explicit_associations.py`
- `tests/test_blast_grading_inputs.py`
- `tests/test_blast_pairwise_grader.py`
- `tests/test_blast_database_grader.py`
- `tests/test_blast_reference_metadata.py`
- `tests/test_blast_graders_integration.py`

`test_receipt_335.json` records the final command, counts and code digests;
the earlier 334-test receipt remains as an earlier fact. These
checks cover five programs × two scientific modes × three declared numerical
representations; strict JSON, original ordinals, malformed/partial HSPs,
metadata collisions/conflicts, tables/headers, byte claims, whole versus partial
transfers, translated frame/strand/phase and explicit missing input behavior.
Saved-sheet recalculation is tested with readers, network and subprocess calls
disabled. Source quality and population correction use separate explicitly
supplied synthetic operands in tests; neither is invented from returned hits.

The retained HomologySearch `massage_blast_json` and `decode_title` methods
were actually executed on synthetic JSON through the earlier retained Perl
JSON::PP harness. All nine tested branch outputs and exact sidecar records
match the deterministic port. This is source transformation verification,
not native scientific execution. The receipt includes source/input/output
SHA256 and stdout. A failed triple-space feature-prefix extraction preserves
Perl's prior capture (`badprefix`) as the observed invalid ID. That ID stays
retained, while its raw-derived metadata association is unavailable. The
adapter does not replace it with a guessed feature ID or function.

Rebuild owned synthetic examples with:

```bash
.venv/bin/python verification/tool_graders_bvbrc_homology_grading_2026-10-24/build_examples.py
```

## Checkable quantities

| Example | Actual output |
| --- | --- |
| Two query raw report | Query 0 retains three hits/five HSPs; query 1 explicitly has zero hits. |
| Overlap and duplicate HSPs | Twelve pair representations, six distinct coordinate/identity pairs, six repeated representations; paired query positions 6/10 = 0.6; paired reference positions 6/8 = 0.75. |
| Explicit functions, bits 20 and 18, T=2 | Function masses 1 and 0.5; conditional weights 2/3 and 1/3; bits-16 unassigned group contributes 1/7 of all-group kernel mass. |
| Same saved sheet, T=1 | Conditional weights 0.8 and 0.2; no reader, acquisition or analysis rerun. |
| Table only 75.0% HSP | Alignment identity fraction 0.75, native mismatch 1, native gap openings 0; exact identical pairs, paired coverage and traceback remain unavailable. |
| Reverse blastx | Three aa pairs cover nine nt at [12,15), [9,12), [6,9); original native nt query denominator 15 yields 0.6 coverage. |
| Explicit pair binding | Six distinct pairs, duplicate HSP group [0,2], paired identity 1.0. The original database target remains retained. |
| Table selected as primary plus secondary raw zero query | Nonzero query uses the table; raw-only zero query retains its original locator/binding with null normalized result and null BLAST sheet, status unavailable, `homology_primary_query_unavailable`. The original raw `hits=[]` stays retained. No representation switch. |

`CHECK_RESULTS.json` and the complete saved sheets/calculations contain the
operands. No population adjustment is available in the main example. Native
taxon, lineage and source-quality measurements are unknown there; BV genome
IDs do not create taxids. The kernel explicitly lists taxonomy, target
compatibility, source quality, evidence codes, coverage/identity and shared
study information as retained but unused.

## Exact consumer interface

`read_homology_raw_json`, `read_homology_processed_json`,
`read_homology_tabular` and `reconcile_homology_artifacts` return exactly these
top-level fields:

```text
schema="bvbrc_homology_parse_v1", status, binding, queries, artifacts, diagnostics
```

Each query has `report_index`, `status`, `source_locator`, `normalized_result`,
`query_binding`, `query_binding_status`, `description_links`,
`native_tabular_measurements`, `diagnostics`. A normalized result retains all
usable native fields and all original report/hit/description/HSP ordinals;
invalid HSP slots remain explicit so complete coverage cannot be fabricated by
dropping one. Derived projections have their own digest and separate original
artifact digest/reference. Artifact rows contain the unchanged descriptor,
status, qualifications, parsed native document or original lines, diagnostics,
and cross-representation association sets. They contain no base64 byte copies.

The caller supplies `primary_representation` (`raw`, `processed`, `tabular`).
Canonical formats and six roles follow the H2 clarification; format selection
does not use filenames. Archive is retained by descriptor with explicit
`archive_decoder_not_provided`; no archive bytes were fabricated or decoded.
Missing secondary artifacts do not trigger a fetch or numerical fallback.

`read_homology_metadata` returns `bvbrc_homology_metadata_bindings_v1` plus
retained native sidecar/descriptor and diagnostics. `bind_homology_metadata`
retains native and supplied collections, converts them into actual H1 operands,
and exposes `record_origins` mapping every merged record index to its original
collection, record index and position. The exact source identifier and record
pointer remain unchanged. Its `queries[]` records contain:

```text
report_index, source_locator,
reference_metadata, description_bindings, sequence_identity_bindings,
target_context, database_profile, unresolved_metadata, diagnostics
```

Both H1 binding lists are always supplied. `supplied_metadata` uses the exact
H1 SHA256 full-sequence binding shape, with explicit original ordinals,
molecule, full length and both provenance pointer pairs. Invalid links remain
visible; neither native accession fallback nor metadata label grouping runs.
Native sidecar links require the same declared bundle/task; actual remote
authentication still belongs to the host. Explicit external assignments remain
usable independently of overwritten native sidecar keys when their own exact
links validate. Interval-scoped assignments and contig title assignments stay
retained but unused by the current whole-reference kernel.

`build_homology_sheet` returns `bvbrc_homology_sheet_v1` containing application,
scientific mode, binding, artifact descriptors/statuses, per-query normalized
input, exact metadata operands, shared `blast_sheet` (or null) and diagnostics.
Pairwise construction requires one supplied query, one supplied subject and
explicit one-member database proof. It keeps the database-backed native target.
An unproved pair retains native numerical data and has no substituted database
identification sheet.

`calculate_homology_alignment_supplements` returns
`bvbrc_homology_alignment_supplements_v1` with per-query/per-hit/per-HSP original
locators, shared alignment components, separately inspectable substitution
counts, query/reference gap runs, endpoint spans and span unions, plus native
tabular measurements and original-coordinate availability. New quantities
store value, origin, input operands, units, denominator, meaning and unavailable
uncertainty. Span coverage is explicitly distinct from paired coverage.

`calculate_homology_scores` returns `bvbrc_homology_scores_v1` with
`scientific_mode`, `queries`, `alignment_supplements`. Query rows contain
`report_index`, `source_locator`, `status`, `conditional_function_weights`
(the unchanged H1 calculation object or null), `pairwise_correspondence`
(shared HSPs/union or null), and diagnostics. A global explicit prior map must
match each query's actual function set; incompatibility is a local unavailable
calculation, never silent prior filtering. All successful other queries survive.

## Transfer clarification and remaining limitations

The C4 transfer fields use inclusive byte endpoints:

```text
requested_range = [start, end_inclusive|null] | null
observed_range = {start, end_inclusive, total_size} | null
```

A requested range alone does not mean a partial acquisition. A complete body
whose actual length equals the known full size is accepted when no partial
observed interval exists, including a service that ignored Range. An observed
interval is accepted only if its closed shape/integers/length establish the
entire [0,total_size-1] object. Partial bodies/intervals remain unavailable for
whole-document grading. The parser checks internal claims; the host must bind
them to original receipts and version evidence.

No actual retained live Homology artifacts, deployed producer/BLAST version,
database release, source quality/population data or complete episode path was
available or verified here. Headerless table query groups have only their
representation-local group ordinal and original line locators until explicit
input/cross-representation associations establish more; repeated titles alone
do not attach original sequences. A normalized FASTA coordinate-map reference
does not supply a map. Native/staged geometry is retained, while projection to
the original supplied sequence stays unavailable until actual map content has
a concrete validated input contract. Scientific metadata and its host source
custody require the separate integration adapter; the three H2 modules perform
no Store lookup, acquisition, publication or receiver admission.
