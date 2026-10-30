# Native homology results acquisition

`homology_results.HomologyResults` extracts the actual one-query phmmer output
into canonical references and alignment observations. It is an ordinary Python
tool API, not a new episode loop, scientific interpreter or report composer.
The optional [shared job-role binding](HOMOLOGY_EPISODES.md) exposes this
capability to results-acquisition children under the parent's scope and form.

## Execution and publication

`NativePhmmerInput.from_job` resolves the registered job and admitted handoff.
`extract` accepts an explicit scope, page size and offset. Later pages bind an
explicit snapshot. The query must be a scoped canonical protein sequence whose
symbols match the native query. The configured policy applies to parsing through
the existing durable native lifecycle; default work time remains unset.

The finite parser preserves sequence and domain scores, independent and
conditional E-values, inclusion flags, coordinates and actual gapped alignment
symbols. No inclusion threshold becomes an acceptance gate. Complete earlier
domains survive a later truncated domain. A missing query header is a parsing
failure, not a successful zero-hit search. Available native bytes are retained
even when extraction fails.

The worker streams the database and writes measurements to SQLite. Host-side
publication streams sequence validation and publishes rows independently. A
failed row rolls back that row, retains earlier valid publications and returns
typed failure information. Reference names and full database headers retain
their native meaning; generated local accessions are not public accessions.

The parser cache binds input bytes, query, database/executable digests, parser
implementation and format versions. Capture provenance is separate: identical
bytes from another execution can reuse parsing while retaining both origins.
Equivalent measurements reuse canonical observations and add provenance
witnesses rather than duplicate contributions. Job-bound reads and explicit
retries must match the saved physical `job_ref` and `registry_ref`, in addition
to the query and execution dependencies. Standalone captures do not acquire a
job identity. Failed attempts are not silently retried. Explicit retries retain
the old failure and identify the new attempt.

Every successfully published native row records its original parser ordinal,
canonical `record_ref`, record type (`reference` or `observation`) and retained
source artifact byte spans. `extract.result.publication_rows` returns that exact
mapping for the requested page, including reused canonical records. The same
row witness is durable in `homology_result_witnesses`, keyed by snapshot and
ordinal. Failed publication rolls back its witness with that row; a later
explicit acquisition can fill the gap. Repeated acquisition preserves the same
mapping. A reference witness identifies its hit-table or native-text row;
alignment witnesses identify printed domain text. These spans do not cover every
numeric summary field or database sequence; the complete native sources,
database digest and canonical reference sequence provenance remain available.

`witnesses(record_ref, scope=..., offset=..., limit=...)` reads these witnesses
for a canonical reference or observation within the caller's query scope.
Existing historical `homology_measurement_witnesses` tables remain unchanged;
they are not used to invent missing native ordinals or acquisition coverage.

## Read-only coverage

`recorded_coverage(store, snapshot_ref, query_ref=..., scope=...,
execution_context=...)` reads one actual captured query's inventory and durable
row witnesses. `HomologyResults.coverage` delegates to that same implementation.
The function creates no schema, commits no transaction, launches no parser and
reads no present-day job output or parser cache. It can therefore run within an
existing Store read snapshot. A job-bound capture requires the exact execution
context pair; an unknown snapshot or mismatched query, scope or physical job is
a `ContractError`.

The result retains snapshot, query, native-source and execution-source references
and separates these facts:

| Fields | Meaning |
| --- | --- |
| `parsed_row_count` | Captured successfully parsed reference and alignment rows; not an assumed complete native result count |
| `acquired_row_count`, `acquired_ordinal_intervals` | Unique rows with durable ordinal-to-record witnesses; ordinals start at one and intervals are half-open `[start,end)` |
| `all_parsed_rows_acquired` | All captured parsed rows have exact publication witnesses |
| `parser_finished`, `native_error_count`, `parse_execution_failure` | Parser completion, representation errors and execution failure remain separate |
| `native_termination_seen`, `native_result_complete` | Retained native query/program terminators were observed; completeness additionally requires a finished parser without errors or execution failure |

Acquiring every row of a partial parse prefix does not establish complete native
results. A clean parse of text ending before native termination can likewise
publish successfully while `native_result_complete` is false. Historical
captures lacking inventory or ordinal tracking return null for those unknown
facts. Coverage records acquisition and provenance; it supplies no scientific or
operational score, unit, action choice or continuation rule.

`changed_record_refs` denotes newly published canonical alignment observations.
It is not a scientific score or evidence that a function has been established.
No assessment, annotation, credit formula or continuation decision is created.
The existing `sequence.sites` tool can inspect selected native alignment sites;
the parent remains responsible for scientific integration.

## Communication and shared learning

Canonical result references can be returned through the parent's declared form.
JSON extraction results alone do not replace that boundary or prove runtime
role enforcement. Internal cache/attempt identities are not scientific findings.
Scientific measurements and interpretations do not enter the global execution
history. This adapter does not yet publish its execution statistics there.

## Verification and remaining work

The current direct results group passed **11 tests in 182.32 seconds**. It covers
exact reference/observation ordinal witnesses, gap recovery, reused canonical
records, source spans, read-only coverage without a parser cache, incomplete
native output, physical job/registry enforcement and historical unknowns.
Two additional shared-runtime/form checks passed in **28.15 seconds**, including
optional storage failure without losing valid results. No new full-corpus search
or configured-model investigation was started.

An earlier frozen-code results/state/communication/native lifecycle/resource/mapping
group passed **56 tests, with 1 explicit OOM probe skipped**. Seven results tests
exercise all 20 retained real HSPs, weak and negative scores, bounded extraction,
partial recovery, publication failures, provenance reuse and explicit retry.
These checks use retained full-corpus output and small engineering native jobs;
they are not a new full-corpus search or configured-model annotation run.

Production scoring choices and a model-driven scientific investigation remain
unfinished. Duration expectations are implemented separately from scientific
credit and local continuation; these tests add no time-based stopping rule.
Native search completion now has optional global execution
recording; parser jobs are not recorded as search durations. The
overall workflow host and durable archive growth are not aggregate-capped by
the native worker limits.
