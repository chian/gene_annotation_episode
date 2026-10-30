The controlled return spends most of its saved-body validation time repeating
pure native job validation through original capture, worker-plan and provenance
checks. The proposed first reuse boundary is the successfully validated V3 job
value during one synchronous body validation. Root reviewed and approved this
narrow V3 boundary for a fresh676 implementation owner. Production code is
unchanged by675; the implementation and its performance remain unverified.

One retained `selected_result_host` case from669/668 supplied four controlled
bases. Its physical-target and capture ports are controlled, its native helper
is never executed, and its deterministic worker calls run the real worker.
All actual capture, prepared-result, publication, receipt, fact, frozen-form,
admission and received-reference validators ran unchanged. There was exactly
one acquisition, one observation, one `parse_original` worker call and one
`project_saved` worker call. All later phases reused those retained results.
This is engineering evidence, not an authentic native or biological result.

The profile ran in `bounded529/check133_result_validation675` using explicit
check005 dependencies. The selected policy and verified cgroup are 20 GiB RAM,
4 GiB scratch, zero swap, no wall cap. The runner observed 617,369,600 scratch
bytes. Its single test passed in 84.492 seconds; the service completed in 89.595
seconds. Two separate bounded formatting checks read only the completed profile;
the final one took 0.096 seconds. All three attempts finished with returncode 0,
terminal/quiescent true, unchanged source/dependency/stdlib/binary pins, and no
outside modules or unbound mappings. No native work was rerun, historical Store
was changed, or other attempt was stopped.

Full `.prof`, all-function call/caller JSON, text statistics and fixture/equality
records are in [profile001](profile001/). The bounded summary, exact source pins
and profile hashes are in [analysis001](analysis001/). Original selected
requests, handles, audits, case reports, before/after pins and terminal receipts
are copied under [bounded_receipts](bounded_receipts/), with the original
bounded529 paths preserved in their metadata. These are copies of the completed
attempts; their originals remain intact.

| Profile phase | Elapsed seconds | Process seconds | Function calls |
|---|---:|---:|---:|
| Selected collect |28.190635|25.525290|64,205,632|
| Saved-body validation |8.053127|8.052868|20,353,123|
| Own-fact construction |8.273768|8.273523|20,744,595|
| Child report validation |13.012643|13.011979|30,395,731|
| Immediate-parent admission |12.592121|12.548938|29,572,775|
| Received report and four reference resolutions in the existing frame |9.354901|9.354268|24,910,905|

These are cProfile measurements of one controlled case. Cumulative times
overlap; they must not be added or treated as a measured production speedup.
The last phase intentionally uses the existing `form_reference_validation`
frame: its five `_received_values` requests produce `_received` once. Existing
request-local reuse is already effective there, while the one resulting body
validation still repeats its inner structural checks.

| Dominant saved-body function (profiled source line) | Calls | Cumulative seconds | Self seconds |
|---|---:|---:|---:|
| acquisition:192 `validate_native_blast_utility_capture` |19|7.436052|0.002442|
| result_worker:98 `qualified_utility_context` |16|6.594457|0.000824|
| contracts:238 `validate_native_blast_utility_job` |171|6.053474|0.001972|
| publication:406 `validate_utility_publication` |1|5.173403|0.000364|
| publication:189 `validate_prepared_utility_result` |2|4.986209|0.000486|
| contracts:536 `validate_native_blast_utility_plan` |38|4.959220|0.002133|
| contracts:626 `validate_native_blast_utility_bundle` |19|4.951808|0.002916|
| contracts:326 `compile_native_blast_utility_job` |133|4.790764|0.000553|
| contracts:131 `_schema` |209|4.129157|0.000751|
| publication:144 `_validate_receipt` |4|3.773406|0.000271|
| result_worker:346 `validate_worker_plan` |8|2.519425|0.000484|
| result_worker:543 `validate_worker_manifest` |4|2.476270|0.000167|
| vdb_context:548 `validate_vdb_context_authentication` |6|2.447907|0.000342|

The largest individual self cost is `jsonschema/validators.py:396(descend)`:
393,916 calls,0.843014 self seconds and4.633643 cumulative seconds. Its
`evolve` has237,671 calls and0.394467 self seconds. Repeated offline mount/path
checks also matter:190 `validate_vdb_offline_execution` calls take1.587
cumulative seconds, including8,493 `_overlap` calls taking1.532 seconds. The
complete self-time table and caller edges are in
[PROFILE_SUMMARY.txt](analysis001/PROFILE_SUMMARY.txt).

Parsing is small here: `parse_blast_vdb_extraction` runs once during collect,
taking0.006117 seconds; it does not run in the retained validation phases.
`operation_catalog` costs at most0.000009 seconds per phase.
`blast_utility_fact_sources` does cost0.697973 seconds across15 calls in child
report validation,0.113118 across2 admission calls and0.079883 across2 received
report calls. That is a separate, smaller constructor cost. The dominant work
is repeated original-custody structural traversal, not a parser rerun or the
small operation catalog.

The saved body is70,074 canonical JSON bytes; its capture is45,918 bytes, its
requested form schema225,207 bytes, and its actual form5,339 bytes. The capture
has8 artifact rows, the prepared result9 occurrences, and the projection one
sequence row plus one VDB-context row. The Store has23 artifacts totaling
217,944 bytes. Five retained copies of the native V3 job have exactly one
distinct content value of9,015 canonical JSON bytes. Artifact IDs, individual
sizes, the selected assignment/form, and actual successful resolution decisions
are retained in [equality_and_inputs.json](profile001/equality_and_inputs.json)
and [selected_case.json](profile001/selected_case.json).

Exact profiled source SHA-256 values for the dominant application boundaries:

| File under `gene_annotation_episode/` | SHA-256 |
|---|---|
| `native_blast_utility_contracts.py` |`5e61994672e12f111483db0ede88b8e87cadaad895c594ec330555cb946aea38`|
| `native_blast_utility_acquisition.py` |`7b8c693c3d407ba86d3273ac7602e3058e065f6230c43b5fcf37b53e2d94c49f`|
| `native_blast_utility_result_worker.py` |`47b239686dd8c3489435c3e22647fb395f34d5059c63eacdf2b6023cc676b9f8`|
| `native_blast_utility_result_publication.py` |`352ebc44d02f7f9f128267cbc90ab58e80c5e10d026f154fd1df24e441089454`|
| `native_blast_utility_results.py` |`15d9df70d3635d49df3eeae5471e16f1871a2c9172574168b41a9b3da8983eca`|
| `native_blast_utility_returns.py` |`b22827a2144c95ab5db7e2ff61982c00fa3ac94abdb3becb9ddfedbc33d7e223`|
| `form_reference_validation.py` |`d5185145c1a910ca54566980d0f4286be5a902ce67dc2445bd5b0ae7f57c688a`|

[dominant_source_pins.json](analysis001/dominant_source_pins.json) also pins
the VDB context/execution validators, reference/form consumers, shared result
views and dominant dependency/stdlib files. The complete before/after pin sets
are retained with the bounded receipts. The profiled results module includes
root674's current failure-publication branch; this successful controlled case
does not exercise that branch.

The measured repeated call chain and its consumers are:

1. `_validate_body` authenticates current scope, target, original selected
   action, saved episode assignment, receipt/intent/observation and any saved
   outcome. Its capture port calls actual `_validate_saved`; it then validates
   prepared data and publication and compares exact frozen projection fields.
   No body verdict is proposed for new caching.
2. Direct prepared validation and publication's own prepared validation each
   authenticate captured Store artifacts, stable grading context, original
   worker plan/receipt/manifest, parsed result and VDB authentication proof.
   `_validate_saved` produces3 of the19 capture validations. Qualified-context
   reconstruction produces the other16.
3. The16 `qualified_utility_context` calls come from prepared validation(2),
   proof authentication(6), original worker-plan validation(6), projection
   context(1), and projection authentication(1). Worker manifests revalidate
   their plan. `_projection_authentication` again authenticates the original
   parse receipt and proof. Publication also checks its project receipt,
   unchanged original projection bytes and explicit saved-data/artifact grants.
4. Each capture checks its plan and bundle; bundle checks the plan again.
   Requested-job reconstruction validates a job and compiles it; compilation
   validates it again. Offline-receipt/argv checks compile again. The measured
   job-validator callers are compiler133 calls/4.741432 cumulative seconds and
   requested-job reconstruction38 calls/1.312042 seconds. All tuple, identity,
   selected command, policy, occurrence, original/final measurement and failure
   relationships remain separate checks above that pure job value.
5. `results.facts`, result-reference resolution, completion/credit views and
   retained-access paths use `_own_bodies`, `_receipt` or `read_result`, reaching
   `_validate_body`. `_own_bodies` already keys its existing frame value by
   provider identity and full binding context, including received references.
   Result values are copied from the saved projection; no scoring is repeated.
6. `NativeBLASTUtilityReturns._own_facts` reaches those real facts.
   `validate_received_report` validates field schemas/semantics, frozen facts,
   original own facts or received subsets, and reference kinds.
   `record_admission` first reads the original successful attempt, commission,
   child identity, scope, assignment/schema and frozen child form, then calls
   `_validate_historical`. Scientific ancestors recursively reach their
   received child forms, preserving old frozen subsets when later deliveries
   exist. `_received_values` is already request-local; neither it nor admission
   is proposed as a broader truth cache.
7. `resolve_received` exposes only identifiers present in selected facts and
   references explicitly delivered by those forms. Metadata membership reads
   the original commission/frozen form without granting auxiliary files.
   `retained_reference_access` and `_explicit_grant` retain original receipt
   prefixes, selected actions, child-form grants and namespace checks. A
   source, metadata provenance row, native path or logical occurrence ID does
   not become an artifact-byte grant.
8. Workflow report validation calls registry received-report validation and
   specialist validation; execution-specialist validation also calls
   `validate_form` with the real resolver and own facts. Generic form validation
   creates the existing synchronous frame. Workflow receive runs admission
   inside its receipt transaction through `received_form_references` before
   recording received refs. Scientific-parent closure obtains received facts
   again. These distinct validations explain repeated body entry across phases;
   the proposed lifetime does not join separate workflow operations.

The controlled fixture replaces the physical target lookup with a saved target
copy and has one immediate parent. It therefore omits real
`ExecutionTargetReader.read_target -> _native -> PracticalReceiptInformation`
ancestry. The complete relevant source path checks actual source/receipt bytes,
original assignments/actions/context transitions, resource bindings and
reservation identities; utility status/collect targets recurse to their
original practical receipt with cycle checking. It also calls
`LocalPracticalOperations.validate_assignment`, requested-job validation,
binding acceptance and `validate_native_blast_utility_plan`. Practical outcome
validation can validate its saved plan/bundle again. Those paths reach the same
pure job validator. Pure qualified-context caching alone would omit this
ancestor route. Offline validation compares selected runtime/data path pairs,
so a larger real runtime closure can add work; this investigation did not
measure673's closure or its timing. No claim that the controlled elapsed times
explain all673/672 time is warranted.

The concrete first patch approved by root is restricted to two production
touchpoints, with root retaining674 ownership until explicitly repartitioned:

- In `native_blast_utility_contracts.validate_native_blast_utility_job`, preserve
  `finite_json_copy` on every call. For V3 only, reuse the original successful
  schema-plus-semantic validation result through `form_validation_value`.
  Factor the existing validation body into a private uncached implementation;
  do not alter its checks or exception meanings. V1/V2 stay on their original
  path. The reusable value is solely a detached finite JSON job, not compiled
  argv, a plan, capture, Store verdict, permission, source or returned fact.
- Use a function/version namespace and the entire sorted finite JSON job text
  as the key. Preserve list order and JSON value types; distinguish `true`,1,
  and1.0. Include all software/input/database identities, paths, context
  requests, offline declarations, output selections and metadata because they
  are already in the job. Neither object identity nor a source/artifact ID is
  sufficient. Full text avoids a digest-collision assumption.
- In root-owned `NativeBLASTUtilityResults._validate_body`, enter a fresh
  existing `form_reference_validation()` frame for that one synchronous body
  check. Keep the current implementation as the private framed body. A fresh
  nested frame preserves the existing outer frame's behavior and restores it
  on return. It also covers real physical-target ancestry reached by this body.
  No change to frame implementation, workflow transactions, async collect,
  worker execution, report history or durable records is required.
- Existing `form_validation_value` already deep-copies stored and returned
  values, stores no exception, clears values at exit and marks copied contexts
  inactive. An input change creates a new content key. A returned-dictionary
  mutation cannot poison a private cached value. The assumed constants are
  the implementation and schema definitions during one synchronous call;
  schema/code replacement requires a new validation, not live modification
  inside a frame. Outside a frame the validator continues to run normally.
- Keep Store-aware `_retained`, `_validate_saved`, target/receipt reads,
  selected-action and scope checks, proof authentication, prepared/publication
  checks, frozen forms, commission validation and byte grants live on every
  body/consumer call. These must not use the pure job key. The proposal shares
  none of their verdicts across mutation or workflow operations. It changes no
  controller decision, numerical value, public schema, observation or credit.

This boundary targets6.053474 seconds of cumulative work within the8.053127
second saved-body phase, and6.546626 seconds within12.592121 second admission.
It does not eliminate all higher-level traversal, selected preparation cost,
or form-schema cost. It is deliberately smaller than caching a whole qualified
capture/context. Actual timing and remaining costs must be measured after an
approved implementation; the proposal itself is not a performance result.
V1/V2 caching and the total real-ancestor speedup are not established by this
initial V3 profile.

The baseline test already asserts exact saved-body/facts/form projection
equality, the supplied `ACGT`/4 result, omission of unselected VDB identity,
exact explicit refs and successful actual admission/resolution. It rejects a
forged returned count5 against the original frozen form and a modified original
selector, reusing the same case without preparation. These outcomes are in
[tamper_checks.json](profile001/tamper_checks.json).

The approved patch should add the following focused equivalence/tamper checks;
these are proposed cases, not claims of tests already run against a cache:

| Case | Required result |
|---|---|
| Same copied V3 job repeatedly in one frame, compared with uncached validator | Equal values; expensive original validator runs once; ordinary calls outside frames still validate |
| Change input content or mutate a previously returned dictionary | New content is validated; original cached value is intact; no borrowed object aliases |
| Bool/int/float substitutions; reordered selection lists; changed context request or offline/runtime identity | Distinct key or original rejection, with unchanged error meaning |
| Invalid job twice; separate frames; copied Context used after frame exit | Failures are not cached; each new/inactive lifetime validates again |
| Warm job, then mutate retained artifact bytes while keeping its ID/descriptor | Direct body/prepared validation rejects actual-byte mismatch |
| Change scope, original action/assignment, intent, observation, target ancestor or plan identity | Existing exact custody checks reject, even when the native job content is unchanged |
| Change nested metadata proof/list binding, frozen projection value, commission/schema or returned artifact | Existing proof/form/admission checks reject; restored originals retain exact facts |
| Deliver a source/context/logical identifier without selecting its auxiliary artifact; then forward to scientific ancestor | Namespace and explicit-grant limits remain; no metadata-derived byte access; original frozen subset rules remain |

The diagnostic owner changed only `tests/test_result_validation_cost_675.py`
and its authorized evidence/attempt directories. No production patch,
inventory/count update, formatter exposure or utility-completion claim is part
of this handoff. The single original profile is complete and retained; no
repeat acquisition is needed for review.
