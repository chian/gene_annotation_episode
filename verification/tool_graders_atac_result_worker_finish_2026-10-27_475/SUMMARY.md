# ATAC result worker completion, workload B

Final acceptance: `check008` passed all **49 tests in 134.77 seconds**, exit 0,
terminal and quiescent. Original unit:
`gene-local-job-86256a523c9c4effb7d074b18cfb34a1.service`.
Source, input, interpreter/launcher and dependency-file pins remained unchanged.
All six production modules and three test files match the accepted snapshot.
The original handle, full receipt, JUnit output and filled native example are
under `check008`; `RESULTS.json` gives the compact handoff and exact source pins.

## Scope and callable handoff

The six owned production modules are `atac_differential_result_contracts.py`,
`atac_differential_result_worker.py`, `atac_differential_result_views.py`,
`atac_differential_return_views.py`, `atac_differential_execution_information.py`
and `native_atac_differential_preparation.py`. The three owned test modules are
`tests/test_atac_differential_result_{worker,views,preparation}.py`.

Exact public ports remain those in accepted 466 sections 5–6:

- Schemas: `atac_result_schema(kind)` and
  `validate_atac_result_record(kind, value)`. `Failure` is A's exact native
  failure schema; numerical issue types remain separate.
- Worker construction: `build_native_atac_worker_plan(...)`,
  `build_saved_atac_worker_plan(...)`; preparation:
  `prepare_atac_result_worker(store, *, plan, policy)` and
  `validate_prepared_atac_worker(store, value, *, plan)`.
- Finite execution: `validate_atac_result_worker_plan(value)`,
  `validate_atac_result_worker_result(value)`,
  `run_atac_result_worker(plan)`, `main(argv=None)`.
- Projection: `project_atac_result(sheet, calculations, *, selector,
  component_rows=None, region_rows=None)` and `native_counts(sheet)`.
- Receiving forms: `atac_fact_sources()`, `requested_atac_sources(schema)`,
  `validate_atac_fact_values(source, value)`,
  `select_atac_return_facts(groups, *, schema)`. Exact sources are
  `atac_differential_projection`, `atac_differential_saved_sheets`, and
  `atac_differential_failures`.
- Selection information: `atac_result_selector_schema()`,
  `validate_atac_result_selector(selector, *, request)`,
  `describe_atac_result(target, *, selector)`.

The selector is an independently scoped JSON Schema resource, including when
embedded in an outer assignment's `allOf/then`. Requested return trees must
match registered fact schemas exactly; wrapping them in a weaker schema fails.
Complete row projections require their complete eligible count and exact
requested window length. Unknown totals remain null.

## Implementation findings and repairs

The worker consumes the existing 467 bridge, 468 header parser, and 460
calculators. No numerical or metadata comparison algorithm was duplicated or
changed. The native plan uses A's full capture validator. A verified native
bundle's actual `HeaderExtraction` record supplies a stable separate
`atac_header_inspection:` producer identity, derived from the original attempt
identity and that exact record; its source is the authenticated bundle artifact.
It is not a callpeak producer identity. This preserves parsed header completeness
and the original input/run/ordinal association.

All emitted nine-column raw track records are saved, with raw chromosome tokens,
lexemes, locators and source ordinals. Derived partition manifests use explicit
signal1/background1/signal2/background2 order, independent of JSON key order.
Write-through partition/component/region iteration retains emitted prefixes.
Every projected and underlying supplied stream is finalized after a failure;
all final issues are retained. A failed iterator never becomes an exhausted
normal end and never flushes an open region as if it had ended normally.

Saved preparation authenticates the sheet and exact Store custody paths. A
currently absent or changed raw attachment reaches the finite worker, which can
retain valid independent output and specific stream failures. Native input
custody checks remain strict. Original saved identities are never replaced by
the identity of a partial output copy. C owns admission and deciding whether a
complete saved bundle can be returned.

Preparation follows the current-host snapshot precedent: current interpreter,
AST source closure and actually imported schema dependencies, one original
native lifecycle handle, no new public runtime factory option. Native lifecycle
controls use ordinary JSON; their exact retained identities authenticate them
without incorrectly requiring ATAC's canonical serializer. The frozen
environment includes its own `PIP_CACHE_DIR`. Closed replay uses saved controls
and does not require current source snapshots or original inputs.

## Concrete checked numbers

Actual native evidence comes from A's final
`tool_graders_atac_native_producer_finish_2026-10-27_474/native002` execution.
B consumes retained bytes from that run; B does not rerun MACS2.

- Treatment totals: 105 and 200; actual post-filter depth operands: 100 and 200
  tags. Native bdgdiff CLI depth lexemes remain `0.0001` and `0.0002` million tags.
- Actual original 48-byte headers each report `chrToy` length 12000, with M5
  unknown. Shared header content remains two input/run occurrences.
- Raw signal/background table row counts: 110/35 and 210/69.
- In selected `[0,12000)`, all four tracks are observed over 8060 bases;
  3940 bases have at least one unavailable track. Unknown tails are not zero.
- Native differential category counts: 1/1/0. The common native BED is a present
  complete header-only file, so its zero is distinct from an absent file.
- Corrected derived condition1 region `[908,1141)` has 233 qualifying bases,
  numerator 34938.38709259033 and mean 149.95015919566666. Condition2 region
  `[2916,3183)` has 267 qualifying bases, numerator 31258.987461090088 and mean
  117.07485940483178. Original native BED coordinates and scores remain separate
  and retain the demonstrated MACS2 coordinate-displacement qualification.
- The explicit four-track fixture declares depths 1/2 **million tags**. It does
  not invent observed read counts. Its 15 float32 likelihood values match the
  retained native diagnostic. Correct derived regions are `[100,200)` score
  17.7408447265625, common `[200,300)` score 5.425064273367752e-7, and
  `[300,400)` score 12.148710250854492. Each has 100 qualifying bases.
- Explicit fixture cutoff 20 produces zero derived regions. Actual native saved
  cutoff 1000 also produces zero regions, with its native sheet unchanged.

`FILLED_ACTUAL_NATIVE_EXAMPLE.json` in the accepted check records the actual
native sheet, calculations, corrected regions and changed-cutoff recalculation.
Before recalculation the test removes its byte-for-byte copies of all original
native captures and its first worker directory. Network/process acquisition is
forbidden; worker reads are restricted to the authenticated saved sheet/tables
and new output directory.

## Partial-state and lifecycle checks

Missing depth preserves null plus the other actual operand; genuine native zero
preserves zero and its `zero_depth` reason. Unit mismatch retains partitions and
unavailable components/regions. Wrong reference metadata disables only affected
ports. Missing background2 preserves calculations using unaffected operands.
Boolean summary claims cannot override the bridge's source-derived eligibility.

Two distinct late failures are recorded even after the selected population has
ended; valid partition/component prefixes survive, an open region is not
fabricated, and previously closed regions survive. Aliases preserve original
raw tokens; external alias reordering yields the explicit required-order issue.
Empty, missing, negative/null, duplicate and out-of-reference rows retain their
separate observed/missing/invalid/ambiguous meanings and original occurrences.

A real finite preparation with missing signal1 and malformed background1 yields
both streams `(extent=partial, exhausted=false)` and independently drains signal2
and background2 to `(extent=complete, exhausted=true)`. The missing attachment
records `saved_attachment_unavailable` plus `calculation_stream_failed`; the
malformed stream records its located `calculation_stream_failed`. A changed but
parseable table records `artifact_digest_mismatch` plus the stream failure.
Derived prefixes are partial, with unknown complete eligible totals.

The actual finite worker is checked under 20 GiB RAM, 4 GiB scratch, zero swap,
and no wall budget. Its retained execution verifies the exact cgroup allocation.
After its own source snapshot and original input copies are removed, closed
preparation replay succeeds while fresh prepare/start/status calls are forbidden.
The original handle bytes remain unchanged.

## Verification history and limits

Every selected check has its own frozen source snapshot, input and interpreter
pins, original handle, stdout/stderr and retained terminal receipt. The harness
also records installed dependency-file pins. The production worker independently
pins its actual schema closure, including optional `idna`, before and after its
selected execution. No attempt was restarted because of elapsed time.

Earlier attempts are preserved: check001 failed in fixture staging before a
native handle; check002 had 38 passes and two failures (a test using an invalid
declared zero and lifecycle JSON serializer mismatch); check003 had 39 passes
and the now-corrected header producer binding failure. Its launcher was edited
while it ran, so its binary-pin comparison truthfully reports that drift.
Check004 stopped on a new test's syntax error. Check005 passed 45 tests with
unchanged source/input/binary/dependency pins; its checkout drift records only
concurrent C-owned files. Check006's two added row tests compared JSON lists to
Python tuples incorrectly; corrected tests passed all four cases in check007.
No production edits followed check005. Check008 passed the final combined run
with the optional outer schema dependency added to its pins.

The original goal attachment, all 16 principles, required design documents and
complete accepted 466/461/relevant 460 contracts were read. The original objective
and principles were reread verbatim after actual native-output examination and
the current input/output and scoring contracts reread before acceptance. The
original goal, permanent records and inventory rows were not edited.

This packet verifies B's retained-data worker and real finite preparation path.
Native production execution is evidenced by A's packet. Receiver authority,
receipt publication and completion belong to C; the actual selected-tool to
child to receiving-episode path, one-action credit and controller behavior belong
to root integration. B's tests do not claim those whole-path properties. The
toy native inputs establish format and arithmetic behavior, not biological
validation, replicate uncertainty or annotation-confidence calibration.
