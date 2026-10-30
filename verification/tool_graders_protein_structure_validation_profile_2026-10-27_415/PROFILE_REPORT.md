# Retained protein result validation profile, packet415

The measured bottleneck is repeated schema construction and validation support,
with substantial recursive copying and normalization. This result supports a
narrow pure-schema optimization first. It does not justify caching successful
receipt or access decisions, skipping original commissions, or omitting current
scientific bytes.

The single profiled diagnostic completed successfully, including the actual
`TypedReportContract.admit` call with the real resolver and semantic validator.
No production source changed in this packet. No native scientific work was
dispatched, no model ran, and no full Workflow or capability acceptance is claimed.

## Experiment and retained evidence

Input was exactly
`../tool_graders_protein_structure_workflow_2026-10-27_410/check007/temporary/pytest/protein-workflow4100`.
The original410 diagnostic and launcher were read completely and retained inside
the executed snapshot.415's diagnostic copies their actual reconstruction and
validation logic, adds named stage clocks and cProfile, and rejects subprocess or
network dispatch. The original Store path continues to identify retained artifacts
and worker operand locations; SQLite uses the detached copied database and enables
`PRAGMA query_only=ON` before context authentication. Original receipt controls are
read in place, without changing their ownership or paths.

The observed form contains one extracted sequence descriptor of length4,
`completed=true`, and no failures. It is a retained successful extraction from a
Workflow that had failed at a later report boundary. It is not a comparison run.
The actual form is2,439 compact JSON bytes; its expanded schema is479,844bytes,
and the saved request is961,364bytes. Those sizes help explain why repeated whole
tree traversal is expensive even with a four-residue sequence.

The bounded execution used20GiB RAM,4GiB scratch, zero swap and no wall-time limit.
The receipt verifies `memory_max=21474836480`, `memory_swap_max=0`,
`runtime_max=infinity`, process-group killing and OOM policy. Observed scratch was
42,692,608bytes. The subprocess/network guard recorded zero blocked attempts.
Executed source hashes, checkout source hashes at run completion, and all original
retained input hashes matched their respective before snapshots. The live410 and412
runs were not touched.

Evidence:

- [Exact commands](COMMANDS.md), [assigned scope](ASSIGNED_SCOPE.md),
  [bounded launcher](run_bounded.py), [instrumented diagnostic](profile_retained.py).
- [Execution request](check001/selected_request.json),
  [verified receipt](check001/receipt.json),
  [diagnostic outcomes](check001/diagnostic.json),
  [stdout](check001/stdout.txt), [stderr](check001/stderr.txt).
- [cProfile binary](check001/diagnostic.prof),
  [all cumulative entries](check001/profile_all_cumulative.txt),
  [all self-time entries](check001/profile_all_tottime.txt),
  [structured summary](check001/profile_summary.json),
  [selected caller edges](check001/selected_callers.json),
  [input summary](check001/retained_input_summary.json).
- [Source before](check001/source_pins_before.json),
  [executed source after](check001/source_pins_after.json),
  [checkout after](check001/checkout_source_pins_after.json),
  [retained input before](check001/retained_input_pins_before.json),
  [retained input after](check001/retained_input_pins_after.json).

## Measured totals and stages

The profile contains155,854,409 function calls,129,318,934 primitive calls,
and48.200176seconds summed self time. The separately measured diagnostic interval
was48.274595seconds wall and49.106171seconds process CPU. The local service receipt
records48.752211seconds, which also contains process startup and final output.

This is one fresh Python process. It is cold with respect to process-local schema
caches; the OS file cache was not reset or controlled. cProfile overhead is included,
and these are not estimates of unprofiled Workflow latency. Timing/profile helper
stdlib startup, snapshot preparation and input hashing precede the measured
interval. Final profile serialization follows it. Imports of production modules
are measured separately below. Stage values come from `perf_counter` and
`process_time`; their boundaries are retained in the diagnostic source.

| Diagnostic stage | Wall seconds | Process CPU seconds |
| --- | ---: | ---: |
| Imports | 0.800880 | 1.638605 |
| Copy retained state | 0.007553 | 0.007554 |
| Initialize detached Store | 0.000788 | 0.000788 |
| Read assignment | 0.001132 | 0.001131 |
| Construct ExecutionEpisodes owner | 1.422193 | 1.422175 |
| Construct authenticated context | 0.928393 | 0.928387 |
| Catalog | 0.000643 | 0.000644 |
| Target | 11.762410 | 11.762301 |
| Selector | 0.087081 | 0.087083 |
| Returns authenticate | 0.798726 | 0.798719 |
| Receipts assignment | 0.000579 | 0.000579 |
| Receipts intent | 1.867719 | 1.867714 |
| Shared assignment bytes | 0.000231 | 0.000231 |
| Construct TypedReportContract | 5.693940 | 5.692173 |
| Actual typed report admission | 24.887866 | 24.887462 |
| Close detached Store | 0.000289 | 0.000290 |

The seven original inspect-step checks accepted. The shared assignment was the
same canonical content plus one newline,549bytes, as in410/check010.

## Cost separation

Cumulative numbers below include descendants and overlap. They must not be added
to one another or interpreted as predicted removable time.

| Measured function | Calls | Self seconds | Cumulative seconds |
| --- | ---: | ---: | ---: |
| `ProteinResultReceipts.completed_receipts` | 3 | 0.000081 | 33.031844 |
| `ProteinResultReceipts.read_completed` | 3 | 0.000011 | 30.664026 |
| `native_protein_structure_contracts._checked` | 293 | 0.086931 | 25.749576 |
| `TypedReportContract.admit` | 1 | 0.001381 | 24.804725 |
| `ProteinResultReceipts._controls` | 3 | 0.000395 | 22.146420 |
| `validate_protein_structure_requested_job` | 26 | 0.000190 | 20.797924 |
| `validate_protein_structure_job` | 58 | 0.001011 | 20.546415 |
| `protein_structure_execution_schema` | 295 | 0.016774 | 16.674157 |
| `communication.plain` | 10,504,651 total /2,534 primitive | 5.531991 | 13.764430 |
| `NativeProteinStructureReturns.authenticate` | 17 | 0.084502 | 12.252475 |
| `copy.deepcopy` | 5,575,438 total /1,664 primitive | 3.883658 | 10.310788 |
| `referencing.Registry.crawl` | 294 | 1.226986 | 8.376868 |
| `Draft202012Validator.check_schema` | 1 | 0.000008 | 5.068304 |

Some table values are rounded; exact values and every function appear in the
retained profile. The top self-time entries also include `isinstance`4.035s,
ABC instance checks2.274s and2.052s, `id`2.187s, dictionary `get`1.764s,
typed-return recursive equality1.537s, `_deepcopy_dict`1.450s, and JSON
`iterencode`1.291s. These shared primitives serve several callers; they are not
independent optimization targets.

**Schema construction and validation.** Every `_checked(value,type_name)` builds
a complete `protein_structure_execution_schema(type_name)`, creates a strict
validator, and validates that payload. The schema builder copies science
definitions, constructs native definitions, hashes an inner resource, deep-copies
the definitions into an outer document, and hashes that document. The public
schema factory ran295times, including two import-time constants. The science
definition accessor ran300times/4.562504s;295came from native `_definitions`.
Direct schema-builder calls into `deepcopy` consumed4.959858s; the science
definition accessor's copies consumed4.550134s. Fresh resolution performed294
registry crawls/8.376868s. This is separate from the once-per-fresh-process closed
parent schema grammar check,5.068304s, under contract construction.

**Copies and JSON.** The largest direct nonrecursive callers of
`communication.plain` were `execution_contracts.canonical`6.877557s,
returns `_commission`2.032394s, returns `_manifest`1.999236s and base
`EpisodeReturnRecords.authenticate`1.989399s. These are tree normalization costs,
not scientific parsing. All standard-library JSON functions together contribute
1.827198s exclusive self time; full `canonical` calls include normalization and
therefore cost more than JSON encoding alone.

**Metadata authority.** The profile deliberately retains actual runtime actions,
original requested jobs, ancestry, scopes, frozen forms, selected receipts and
publication checks. Three `completed_receipts` calls cost33.031844s cumulatively:
target recovery10.864927s, own report groups10.949510s, and own execution facts
11.217406s. Those calls contain the schema/copy work above. Seventeen returns
authentications,54 base authentications and37 commission checks were observed.
This is evidence of repeated traversal, not permission to accept an ID without
its current records. Original metadata authority remains intentionally separate
from scientific byte availability.

**Current scientific byte validation.** One `_verify_artifacts` call took
0.002262s; four `_bytes` calls took0.001824s cumulatively. They checked native
result38,205bytes, sequence4bytes, residue map8,537bytes and structure365bytes,
47,111bytes total. `retained_protein_structure_file` checks metadata and invokes
`materials.artifact_path`, which hashes current file bytes; `_bytes` reads them
again and verifies exact size/hash. This small case supplies no argument for
skipping those checks. No new structure parsing, SVD, scientific calculator or
native worker ran during this diagnostic.

**File I/O and database work.** Selected OS/file primitives contributed
0.031205s exclusive self time, including production imports, fixture copying,
receipt controls and report logs. SQLite primitives contributed0.028902s. All
SHA256 constructor calls together contributed0.0674s self time; most are schema,
record or request hashes, so this must not be relabeled scientific-byte I/O.
These costs are small here and the bytes are small.

The reproducible exclusive category totals are in
`check001/profile_exclusive_categories.json`: jsonschema/referencing function
self time9.305328s; stdlib copying6.535033s; communication normalization5.531991s;
typed-return tree equality2.768616s; JSON1.827198s; selected OS/I/O0.031205s;
SQLite0.028902s; remaining functions22.171902s. These exclusive categories sum to
the profile's self time. They omit descendant costs from containing categories,
so they answer a different question from cumulative call-tree measurements.

## Complete measured consumer paths

The following paths use the frozen source in `check001/source_snapshot`. Function
names identify each responsibility; none is replaced by a successful test callback.

1. `profile_retained.run_diagnostic` constructs `ExecutionEpisodes`,
   `ToolRegistry`, practical resource bindings and
   `NativeProteinStructureResults`/`NativeProteinStructureReturns`.
   `EpisodeReturnRecords.context` constructs `BindingContext` and invokes the
   actual returns authenticator. That calls base context authentication,
   `_manifest`, `_saved_context`, and `_commission` for original ancestry.

2. `ExecutionEpisodes._target` → `_retained_protein_result` →
   `ProteinResultReceipts.completed_receipts` → `read_completed` →
   `_read_completed` → `_completed`. This reconstructs the original result
   context, validates scope/assignment and the selected completed action, reads
   the shared assignment and exact intent/control files, rebuilds `_intent`,
   invokes `_controls`/`_validate`, and matches the actual runtime outcome.
   `_body` validates handoff proof, capture, worker and qualified files;
   `_publication` validates original source/reference payloads, descriptors,
   selected populations, delivery accounting and artifact-family metadata.

3. The nested native-contract path is
   `validate_protein_structure_requested_job` →
   `requested_job_from_protein_structure` → `validate_protein_structure_job` and
   `compile_protein_structure_job` → `validate_protein_structure_job` again.
   Each job validation calls `validate_protein_structure_request`, then
   `validate_input_associations` → `required_input_files` → the same request
   validator again. `_checked` constructs the schema and strict validator at each
   relevant entry. Handoff proof (`PracticalReceiptInformation._qualify` and
   practical assignment validation), capture-plan/bundle validation, and pure
   `protein_structure_source_payload` all consume these public validators.

4. `TypedReportContract.__init__` → `validate_closed_schema` →
   `_compiled_schema_content` → `_compile_closed_schema` → jsonschema's schema
   grammar validation and exact registered protein-field comparison.
   `TypedReportContract.admit` → `communication.validate_form` → exact native
   row and local-schema validation plus semantic reference traversal. Its real
   semantic callback calls `ExecutionEpisodes.validate_report` →
   `NativeProteinStructureReturns.validate_received_report` → `_values`,
   `_own` → `NativeProteinStructureResults.own_fact_groups` → completed receipt
   proof and `_verify_artifacts`, then compares frozen facts. The same
   `ExecutionEpisodes.validate_report` additionally validates the original form
   and calls `ExecutionEpisodes.facts` → native results `facts` → another
   completed receipt proof with `verify_artifacts=False`. Finally, the414
   `admit_recorded_protein_report` boundary preserves the exact authenticated
   custody fields while retaining ordinary audit exclusion elsewhere.

The retained4-residue form contains only the registered patterned protein fields
and the completed flag. Its authority proof occurs in the semantic callback;
the generic resolver's existence alone is not evidence of authorization.

## Candidate seams and required limits

**First: private reusable native schema resources and strict validators.**
The input is the exact unbound type name and fixed schema-definition version;
the output is a private strict validator over the unchanged self-contained
schema resource. `_checked` can use it while still validating the current
payload's original Python types, finite values and all meaningful relationships,
and returning a detached result. Public `protein_structure_execution_schema`
continues to return independently mutable documents with unchanged content and
digests. Binding-specific RequestedProteinJob documents must continue to use
their exact supplied binding values. A type name is a grammar selector; it is
not an authority token. This seam directly targets the295 constructions and294
registry crawls without touching recorded facts.

**Later, only after remeasurement: same-invocation pure job composition.**
`requested_job_from_protein_structure` already holds a freshly validated job but
passes it to a public compiler that validates it again. A private compiler could
consume that local validated value and return argv/environment/outputs, leaving
the public compiler's validation intact. Similarly, `validate_input_associations`
could consume an already validated local request through a private
required-input derivation helper. The observed26 requested-job validations,
58 job validations,32 compiler calls and125 request validations establish these
exact repeated calculations. Reuse must not cross invocations or be granted by
an object ID; every externally supplied mutable value still enters through a
public validator. This packet changes none of these calls.

**Small independent seam: request source names without constructing schemas.**
`ExecutionEpisodes.facts` constructs all four native fact schemas merely to
obtain their keys for empty arrays. That one call cost0.229735s. A shared fixed
source-name definition can supply those keys; consumers requesting schema
documents still receive the full exact registered forms. This does not justify
changing the form's vocabulary, field meanings or selected facts.

**Higher-risk later seam: one local own-report view.**
Inside one synchronous `ExecutionEpisodes.validate_report` invocation, the
original completed receipts feed `_own` and then `facts`. A private explicit
view computed once could supply both groups and generic completion/source facts,
while checking the requested current artifacts once in the same invocation.
The input must include exact context, request/schema, scope and selected use;
the output must remain local, carry no reusable authorization token, and never
survive the call or become a global/provider cache. Every original commission,
actual selected action, exact frozen form and publication relationship remains
validated. Historical metadata reads continue to function after scientific byte
loss; new selected byte uses still fail on loss/mutation. The independent target
call is a separate boundary and is not eliminated by this proposal. This larger
seam should wait until the pure-schema change is measured; no authority change
is implemented or authorized by this report.

## Verification required for the first seam

Root has selected only the first pure-schema seam for its next change. Focused
checks should establish:

- Exact old/new public schema content, canonical digests, local `$ref` and
  content-addressed `$id` structure for each supported type. Exported document
  mutation must not change later documents or private validators.
- Exact strict Python type behavior, including booleans versus integers,
  integer-valued floats, tuples, non-finite numbers, embedded null bytes and
  malformed later `oneOf` branches. The inner resource must keep inheriting the
  strict caller dialect as documented by the existing builder.
- Current payload mutation is revalidated after an earlier successful call.
  Failures do not create a success entry; unknown type names retain the expected
  failure. Concurrent callers must not share mutable per-payload validator state.
- Binding-specific mode/software alternatives remain exact and detached;
  changing a binding does not reuse an earlier binding's schema. No descriptor,
  source, result ID, authorization verdict or scientific-byte result enters a
  reusable cache.
- Existing original-commission, typed-return, artifact-loss/mutation and
  metadata-only historical checks still pass. The actual retained410/check007
  diagnostic remains accepted through real semantic admission, with the same
  recorded form and unchanged original input hashes.
- Repeat this same cProfile harness in a fresh source snapshot after those
  focused checks, and compare counts and separated stage times. Report both
  snapshots; do not infer speedup from overlapping cumulative entries or modify
  the already running410 snapshot.

The profiled run had no failed execution attempt. Two failed read-only SQLite
examination commands and one incorrect source glob are recorded in
`analysis_failures.json`; each was corrected without changing the diagnostic or
its inputs. This packet ran no mutation counterexamples or whole Workflow test.
The immutable objective and all16 design principles were reread verbatim after
substantial source/result examination, then the assigned scope was reread before
this report. The current authority and form contracts were also inspected. Goal
hash and scope remain unchanged.
