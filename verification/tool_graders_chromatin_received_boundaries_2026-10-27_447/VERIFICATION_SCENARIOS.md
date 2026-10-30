# Executable verification specification for447

These scenarios were not executed in this planning task. A/B coding owners run
their new tests only through the existing `local_jobs`/`native_lifecycle` test
lifecycle:20GiB RAM,4GiB scratch,zero swap,no wall allocation. Preserve immutable
source/interpreter pins, the original handle, failed attempts and native outcome.
Host/full Workflow checks belong to root's separate integration workload. A
passing strict host double is authority-boundary evidence only.

## Shared concrete fixture setup

Use actual `Store(tmp_path / "store")`, `Journal(store, run_id)` and
`EpisodeReceipts(store, run_id)`. They create the ordinary
`store/state.sqlite3`, `runtime_episodes`, `runtime_actions`,
`runtime_forms`, `runtime_report_attempts`, `runtime_record_receipts` and
`runtime_receipt_inheritance` records. Do not replace SQL or Store with a dict.

Create a tiny DNA problem through `store.create_problem(raw_sequence="ACGTACGT",
molecule="dna")` and use its actual subject reference in scope. Add a second
target when testing foreign scope. Register each input/metadata source with
`store.artifact(raw)` and `store.put("source", {"provider": "fixture.chromatin",
"accession": null, "uri": null, "artifact_ref": artifact, "text_ref": null,
"request_ref": null, "version": null, "retrieved_at": null}, origin="caller")`.
These are authored test inputs, not observed native science.

Use `EpisodeRef(run_id, path).episode_id`; ordinary path examples are:

```text
(("annotation", "root"),)
(("annotation", "root"), ("scientific_process", "child_0"))
(("annotation", "root"), ("scientific_process", "child_0"), ("results", "child_0"))
```

Build actual `EpisodeGoal`, `EpisodeRequest`, `Record` and `TypedReportContract`
records as in `tests/test_genomic_overlap_returns.py:RuntimeFixture`, changing
only the scientific records/host under test. `EpisodeReceipts.bind` precedes
construction; put its exact returned manifest into
`request.message.knowledge_inheritance`. Persist `runtime_episodes` through
`Journal.save`. Persist each actual parent commission action with its original
scope, purpose, `schema_json`, role and assignment; child suffix must equal
`child_<decision_index>`. For new unsaved construction, intentionally delay only
the child episode/action records that the ordinary constructor has not written.

Use the exact registered source schemas from `chromatin_fact_sources()` under
arbitrary parent-chosen field names. A successful result return is represented
by the actual frozen source arrays in `runtime_forms.facts`, exact
`form_with_facts` result in `runtime_forms.form`, and a successful
`runtime_report_attempts` record containing the actual contract, same form,
child identity, delivery identity and `failure=NULL`. Invoke B admission with
`f"{run_id}:{parent.episode_id}:{decision_index}:typed_form"`; then call
`receipts.receive(parent.episode_id, returned_refs, kind="child_form",
source_index=decision_index)` as the real runtime does. Failure/replay tests must
mutate these actual records, not only method arguments.

The strict host double must require an actual matching completed
`runtime_actions` row selecting `execution.results.collect` with `{}` and its
registered original outcome. Its `completed_saved_bundle_origins` returns every
actual matching `{"episode_id": ..., "operation_key": ...}` record. It records calls to
`verify_artifacts`; `False` never opens scientific files. It must reject changed
context/action/outcome instead of returning convenient canned facts regardless
of records. Clearly label it synthetic, as the overlap test does.

Populate at least two bundle table positions with identical bytes. Construct
real artifact metadata with `store.artifact`, yielding one content path and
one artifact row but duplicate identities in `SavedSheetBundle.tables`.
Separately include differing table identities so reordering can be tested.
Every identity's format and SHA naming must pass the actual pure return view.
Boundary-only payload fixtures may be explicitly synthetic; actual valid NPY
and C3-produced ContactSheet/WorkerCapture records are mandatory in root's host
and assembled path tests. A schema-valid table label does not prove a native
table was parsed.

## A: original supplied-input authority cases

Implement in `tests/test_chromatin_interaction_operands.py`.

| ID | Concrete action | Required result |
|---|---|---|
| A01 | Build a C3-valid requested Cooler job with contact and element source/file pairs, all metadata reference fields listed in CONTRACT section3, and actual canonical Store paths; receive them through root initial receipts | Return exactly the documented first-occurrence reference order; no Store writes or byte access |
| A02 | Use insulation-only request with `elements=None`; empty metadata lists; both ReferenceSpec.source_ref values nullable where applicable | Accept the exact present inputs; no imaginary BED, reference dictionary, sample or zero uncertainty |
| A03 | Keep valid source/file records in Store but remove the exact source receipt, then separately remove artifact receipt; set callback to True and add reference to BindingContext.received_record_refs | Both reject `chromatin_input_input_not_received`; hints/callback do not grant authority |
| A04 | Change run, episode ID, path, role, saved request, assignment or scope one at a time; point a child's manifest to a different parent with useful receipts | Context/parent conflicts reject before execution or input byte access |
| A05 | Remove/alter knowledge inheritance; create a cyclic inheritance chain; reconstruct after a later parent receipt | Reject missing/altered/cyclic authority; reconstruction keeps the original prefix and excludes later input |
| A06 | Callback returns False, then 1, then arbitrary object | False is protected denial; non-bool/non-None is invalid callback result; neither is converted to missing scientific data |
| A07 | Source A points to artifact A, but contact/element identity/binding uses B; repeat with same format/size and different hash | Reject exact source/file mismatch; no first-file or matching-size inference |
| A08 | Change declared SHA, artifact ID, size, bool-as-size, format, input key, binding order or canonical path; add/repeat an input key | Existing C1/C3 or A validation rejects precisely; no path resolution/staging |
| A09 | Keep source/reference metadata globally scoped; receive it for the root without attaching it to target | Access may succeed without inventing target relationship; an actual scoped record outside the assigned scope must fail |
| A10 | Put foreign `sample_key` in contact links or dependence groups; foreign input/population in uncertainty; foreign attribute target; duplicate element occurrence/contig | Reject structural metadata joins; reference-looking strings in gene_key/specimen_key/assembly_label/attribute path are never traversed |
| A11 | Duplicate contact/element artifact bytes or share one metadata source across several roles | Return each handle once but preserve the original request's distinct source/input/metadata roles; no association deduplication |
| A12 | Remove contact/element content at `<store>/artifacts/<sha[:2]>/<sha>` after registering/receiving it; repeat by replacing bytes with same-sized wrong contents | Metadata-only A still succeeds for original selected identities; the later native driver separately records unavailable/mismatched staging when actually selected |
| A13 | Patch `Store.get_artifact`, `materials.artifact_path`, `retained_native_file`, HDF5/BED readers, filesystem artifact open/hash, network and subprocess entry points to fail | All A success/authority-negative cases remain independent of those paths; no source bytes are inspected |
| A14 | Pass an unrelated request, then malformed `native_chromatin_interactions` key present | Unrelated returns []; present malformed request rejects, never silently opts out |

For A12, save SQL metadata and receipt snapshots before/after. A must leave all
unchanged. The subsequent driver run is a separate bounded integration test;
do not claim it occurred merely because A's check passed.

## B: actual return, compound bundle and origin cases

Implement in `tests/test_chromatin_interaction_returns.py`.

| ID | Concrete action | Required result |
|---|---|---|
| B01 | Results child returns all three exact sources to scientific parent, which closes and returns them to annotation | Values unchanged at both immediate edges; admitted refs are exact sheet plus all tables; origins name the real result collect action |
| B02 | Parent requests projection only; private worker output contains a valid sheet/tables/components/diagnostics | No saved bundle, artifact receipt or resolver permission leaks; `source_sheet_sha256` grants nothing |
| B03 | Parent requests failures only; Failure points at a private sheet/table in artifact_ref/partial_artifact_refs | Located failure is received; neither saved operand nor arbitrary artifact access follows |
| B04 | Return one proper bundle; select sheet alone, a missing table, an extra table, a reordered list, changed format/size, or splice identities from a second bundle | Every changed bundle rejects; independent receipt of component handles is insufficient |
| B05 | Return bundle with identical table identities at two positions for different table keys/populations | Exact two associations survive in the public bundle and host descriptor witness; receipt insertion deduplicates only the handle; deleting one position rejects |
| B06 | Private sibling or unrequested grandchild has the desired exact bytes; ancestor has generic Store/scope access and forged ordinary receipt handles | Resolver and selected bundle authentication deny; only exact forms at every immediate boundary count |
| B07 | Two authorized completed collect actions publish identical entire bundles | One public fact row may remain after representation deduplication; all exact `{episode_id,operation_key}` origin records remain; no arbitrary first origin |
| B08 | Same bundle from two completed actions in one result episode, or from two result episodes | Both action identities retained; altered/missing/uncompleted action is never accepted because its neighbor exists |
| B09 | A later identical bundle arrives from another result origin after scientific forwarding was frozen | Closed forwarding preserves its original origin set; newer direct receiver can use its own later delivery; old facts/history unchanged |
| B10 | Construct a saved-result child, then deliver a delayed lower-index result to its parent | Child's captured received_report_prefix excludes the later arrival despite lower decision_index; new child can use the later delivery |
| B11 | Change run, immediate parent, scope, child path, result assignment, purpose, schema or selected role; retain syntactically valid forms | Original commission/runtime checks reject; cross-run equal hashes are not authorization |
| B12 | Change frozen form values, fact arrays, aliases, witness form/contract digest, delivery_ref or child id | Reject exact frozen/provenance conflict; no re-reading latest facts to repair history |
| B13 | Closed received array is extended by later independent delivery | Historical validation accepts only unchanged frozen ordered subset; reordered rows, invented duplicate rows or new values reject |
| B14 | Build corrected explicit redelivery using runtime_model_calls and original delivery_ref, then a successful new attempt | Exact new requested frozen facts can be admitted through existing mechanism; no new runtime action/observation; old failed or successful attempt retained |
| B15 | Put bundle only in a staged disk result receipt, omit runtime action result or change it to status selection | Host proof rejects; possession of private control files is not completed-action authority |
| B16 | Remove sheet and all table content files after actual admission, leaving metadata/control/runtime records; patch all scientific reads to fail | `facts`, closure replay, `record_admission`, `resolve_received`, exact origins and selected bundle authentication keep original answers without byte reads |
| B17 | After B16 choose a new saved computation using the same authorized bundle | Authority remains valid; separate host/worker current-byte qualification reports located unavailable input. No producer reopen, reacquisition, retry or old-history mutation |
| B18 | Delete/corrupt a required SQL metadata row or immutable completed-action control, leaving scientific bytes intact | Authority fails; scientific byte availability cannot replace missing original records |
| B19 | Supply bad admission operation grammar (`:01:`, foreign run/parent, wrong suffix), missing/failed return, or a form differing from that attempt | `record_admission` rejects and inserts no receipt itself; surrounding transaction rolls back |
| B20 | Use unsupported owner roles/namespaces; alter registered schema; two fields claim one source with unequal values | Reject owner/namespace/schema/value conflict; unrelated ordinary sources retain normal behavior |
| B21 | Call facts_for_closure on a scientific receiver; instrument Store.read_snapshot; then attempt schema projection of private prefix | Snapshot is used, exact existing prefix shape is saved privately, no registered fact source/model field/receipt/observation added |
| B22 | Unsaved child is constructed against exact frozen manifest, then repeat with prior own action/form or alternate parent | Legitimate construction works without creating new records; spoofed construction fails closed |

Use `tests/test_genomic_overlap_returns.py` only as a fixture-mechanics reference.
Do not import its overlap Projection, single-file saved values, comparison keys,
failure fields or scientific assumptions into chromatin tests.

## Host and full-path verification handoff to root

The host must test against real C3 WorkerCapture/WorkerResult and Store files,
then the ordinary Workflow/shared method_loop. Separate these categories from
the B strict-double suite.

1. Freeze a selected real native plan, original practical start/handoff and
   terminal/quiescent closure;446 captures the exact attempt. C3 worker emits a
   sheet, every role descriptor and explicit table-key outputs, full components,
   selected projection and diagnostics. Check the host publishes only captured,
   semantically joined outputs from that completed selected collect action.
2. Corrupt each join independently: request/contact source/input identity,
   metadata sample/input/population links, population order, descriptor role,
   table_key, declaration format/digest/size, captured output identity, component
   table order, projection sheet SHA/parameters/population/fields and selector.
   No schema-only, filename-only or same-size match is a qualified publication.
3. Produce two real populations sharing byte-identical empty cell-state tables.
   Verify every declaration/descriptor/bundle association, each unique Store
   byte object, typed return, later selected saved worker and reconstructed
   context. Delete one table occurrence from the bundle: authority must reject
   even though the remaining bytes happen to suffice for a careless loader.
4. Use actual zero-contact native input with known nonempty bins and complete
   read evidence. Retained contact0 and expected0 produce undefined fold with
   `zero_denominator`, not a failed matrix read. For positive expectation,
   observed contact0 produces fold0. A missing native population, absent
   requested weights, lost table or unestablished pair population produces
   qualified null/extent failure, not an empty successful projection or matrix.
   Preserve a complete independent population alongside a partial one.
5. Preserve original returned bundle after deleting producer paths and input
   paths. Recalculate from retained sheet/tables with changed explicit threshold;
   verify no native producer, network, source resolver or software refresh. Then
   remove one retained table and select another calculation: original returns
   and completed credit stay fixed, while this new action records its failure.
6. Return the same whole bundle from different original handoffs/resources/runs
   and from repeated results of one handoff. The saved selector's handoff must
   identify the exact common target of relevant authenticated origins; mismatch
   cannot be resolved by picking a favorable first row. Duplicate delivery or
   repeated calculation cannot fabricate a new acquired scientific population.
7. Exercise shared `ExecutionEpisodes.initial_references` and
   `Workflow._receive_form`: sheet and every table receipt reaches the receiver;
   unrequested components, source input copies, diagnostics, native bundle and
   sibling artifacts stay outside that return. Add a broadly scoped source that
   references a private result artifact: provider denial must defeat fallback.
8. Snapshot original runtime actions, observations, estimation contexts,
   forms/prefixes and practical completion proof. Replay after data loss and
   after late delivery. Original facts, final actual gain and closed histories
   remain unchanged. A newly completed practical assignment sets future expected
   credit to exact0 through its existing controller comparison with no extra
   synthetic zero action. Scientific nulls do not introduce a scientific gate.
9. Stop/reconstruct a selected result operation with staged controls but no
   committed runtime outcome. Resume the original worker reservation and commit
   once. No second native/worker invocation or artifact-only authority. Failure
   remains specific if original controls no longer qualify.

Report counts and what actually ran separately: source inspection, synthetic
authority fixtures, genuine native-format fixture parsing, deterministic numeric
checks, live local producer/worker execution and ordinary typed episode return.
No scenario here authorizes an unrelated resource, hidden retry, full matrix
prompt dump, new annotation score or literature grading.
