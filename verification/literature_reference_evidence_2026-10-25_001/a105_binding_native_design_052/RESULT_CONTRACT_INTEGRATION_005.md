#052 native binding integration: implemented contract005

This implements one selected native operation inside the existing LiteratureEpisodes. It does not settle a new scientific TASK, provide a source covariance/model reader, calculate target-transfer credit, add an axis or sheet, or route experiments automatically. It remains the same052 workload accepted in PROPOSAL_001 and first-stage RESULT_CONTRACT_003. Scientific TASK constants and the controller are unchanged.

## Selected action and actual source input

`literature.binding.interaction.populate` is the nineteenth population catalog operation. Its closed source selection is the immutable003 `binding_interaction_arguments_schema()` and `read_binding_interaction_inputs(arguments, read_source=...)` contract. The input includes the common parameter-kind interpretation, four separately selected original-image cells, each role's own source meanings/physical-fit nomination/uncertainty selection, image-to-original mapping nominations, and six relationship interpretations. The four roles are the two source molecular forms crossed with the two ligands. A source cell is not a physical fit.

C7 adds only the operation/schema, `requested_binding_interaction_components`, typed namespace, dependency fingerprints, new dispatch/provider route and source authorization. The lazy services accessor returns `LiteratureBindingInteractionRepository`. The repository authenticates every selected source's actual receipt, scope and assigned-page ancestry before any source bytes. A mapped image's declared original must be in the actual source parent graph and be separately received. Bytes must match their content-addressed artifact identity. Unauthorized/unreceived references fail the action; authorized local read/decode/witness failures remain local extraction partials.

Only a `calculation_input_status == ready` extraction calls the frozen053 calculator, with `model=None`. Unknown/conflicting/source-unavailable common kind never chooses IC50 or Hill Kd as a fallback. Unknown unit retains raw numerical representation independently of unavailable canonical nM. Source ambiguous candidates retain alternatives rather than an average or a selected best value. CI endpoints/confidence level are independently nullable; unresolved uncertainty stays distinct from `unreported`. Qualified counts are not upgraded to exact counts. No word-count capability is introduced.

## Durable payload and custody

One transaction publishes the complete extraction, optional actual calculator result, all eight native cells, request and assignment, source metadata/ancestry snapshots, definition/relationship/cell/physical-fit bindings, dependency fingerprints, original operation outcome and record roster. The repository uses its own operations/received/delivery-binding tables and inherits base044's original runtime form/contract and owner-versus-admitted-subset authentication without changing base044.

Text binding anchors contain the genuine full UTF-8 span, actual source/artifact, offsets and exact quote. Long labels are bounded previews; full quotes remain in anchors and payloads. Image transcription/cell bindings have `anchor=None`. Their accession identities bind the complete source selection/result, actual source metadata, original image mapping/geometry, and investigating-episode interpretation attribution. Original request/episode identity remains in the immutable saved source's request artifact. Full raw labels, quotations, failures and numerical source representations stay in the saved payload; typed returns use finite strings and actual record references.

`read(sheet_ref)` authenticates the source/request/payload content identities, actual original selected operation and outcome, source metadata/ancestry, dependency bytes, original source associations, numerical field types, estimate/physical owner keys, native cell copies, and exact binding-record roster. It does not open experimental artifacts, decode images, invoke the source reader/calculator/model, admit receipts or project credit. The separate validator checks retained associations and finite meanings; it does not reparse expressions or recompute contrasts. The original immutable selected outcome supplies numerical truth.

## Eight public numerical meanings

The sole public projection family is `literature_binding_interaction_cells` with evaluation scope `source_binding_discrimination_interaction`. See RETURN_SCHEMA_005.json for every closed field/type/enum. Selection permits exactly:

| Component | Numerical meaning |
| --- | --- |
| parameter_rr | Actual selected reference-form/reference-ligand parameter in canonical nM when available |
| parameter_rt | Actual selected reference-form/test-ligand parameter in canonical nM when available |
| parameter_tr | Actual selected test-form/reference-ligand parameter in canonical nM when available |
| parameter_tt | Actual selected test-form/test-ligand parameter in canonical nM when available |
| reference_subject_ratio | p_rt / p_rr |
| test_subject_ratio | p_tt / p_tr |
| interaction_ratio | (p_rt / p_rr) / (p_tt / p_tr) |
| log_interaction | Natural logarithm of interaction_ratio, evaluated by the actual048/053 calculator |

These are dependent representations of this source experiment, not independent support. Printed limits have `value=None`, a separate threshold and direction. Raw limits use `bound_kind=printed_limit`; derived limit arithmetic uses `reported_limit_arithmetic`. Neither is a confidence/true-parameter bound. Four model-dependent cells remain in the private calculator snapshot but cannot be selected on this route: every public row declares `model_reader_capability=unimplemented` and `model_input_status=not_supplied_by_native_operation`. That is an implementation status, not a finding about the paper.

Each public row carries the requested cell, finite common-kind/input/model states, six finite relationship interpretations and witness refs, and all four roles' source selection/parse/kind states, definition/physical-fit/cell witness refs and authenticated location sidecars. It preserves actual per-role kinds even when common kind is unknown or another role mismatches it. Nested source failure causes survive separately from an actual calculator's `missing_operand:<role>` reason.

Only the raw component matching a role authorizes that role's `values.delivery_status=requested` and its native/canonical measurement, candidate values, canonical partial uncertainty, native interval endpoints and native scalar values. Every other role in that row has those fields set to null with `not_requested`. Every derived row sets all four roles' numerical expansions to null. Metadata/witness references remain available; a receiver receives exactly the admitted subset and cannot recover unadmitted raw rows from mere possession of the sheet reference.

Concrete projection examples, generated from actual repository calls, are recorded in PROJECTION_EXAMPLES_005.json:

- Unknown common kind: parameter_rr still reports5 nM with actual role-kind IC50; interaction_ratio has no value and reason `common_parameter_kind_unknown`. No calculator input/call is fabricated.
- Unknown rr unit: main raw cell has null value/unit; only requested rr expansion retains native5 and canonical null. Derived operand expansions remain null.
- Mismatched rr kind: actual Hill Kd raw5 remains available while common-kind IC50 and `parameter_kind_mismatch` remain explicit; affected derived cells use the actual calculator unavailable reason.
- CI known endpoints/unknown confidence level, missing SD magnitude, whole unresolved uncertainty, ambiguous/unreadable/n.d., qualified count and source-cell rereading conflicts are tested through saved typed projections.

## Mechanical display and ordinary accounting

The shared renderer adds only family grouping/masking and a call to052's dedicated helper.055's separately authorized kinetic count display is an explicitly recorded overlay. The binding helper renders only the admitted numerical components, actual finite meaning/status fields and source definitions that do not overlap retained numerical locations. Broad overlapping text/image labels and unresolved-location labels are masked per actual source; unrelated labels and disjoint authenticated image definitions remain available. Explicit later source reads remain authorized.

For a matching requested raw row, the helper displays scalar/interval endpoint status, relation, approximation, percent and qualification-origin fields beside retained values. It displays interval unit relationship, native unit witness, canonical unit/status, including an explicit interval unit when the parameter unit is missing. Derived-only rows show no native/canonical/candidate/uncertainty/count values. The actual provider transport tests distinguish `at least73` (qualified/ge, not exact73) and `about95%` (approximate/percent, unknown canonical confidence level).

Actual selected nested Episodes and actual C4 admission are tested. One selected population contributes one ordinary own-action observation; source parsing, deterministic calculation, rendering, receipt retries and reconstruction add none. The nested controlled run has one population, two typed deliveries, five actual selected-action observations and credit0. C4 checks interruption rollback, original form/contract authentication and rejection of an expanded subset even with a forged digest. Direct SQLite `mode=ro` reopen occurs before the first scientific projection, with experimental bytes/image decoding/reader/calculator/receive/repricing forbidden and the whole SQL dump unchanged.

## Review artifacts and verification scope

Stage004 preserves129 passing tests and two stale catalog-count failures (`18` versus released `19`), plus its full before/after generation. Parent explicitly released the sole existing-test compatibility assertion edit; its complete244-line baseline/hash is retained.005 separately fixes the parent-reproduced scalar display gap in the owned helper/new integration tests. No frozen003 input reader/test,049 visual reader,053 calculator,050 snapshots, base044, runtime, Store, controller or TASK is edited.

IMPLEMENTATION_INTEGRATION_005.patch contains052-owned changes, including the one-line compatibility edit. AUTHORIZED_RENDERER_055_DELTA_005.patch is the separately owned shared-renderer overlay. SNAPSHOT_HASHMAP_005 and PATCH_RECONSTRUCTION_005 distinguish052 patch bytes from actual joined snapshot bytes. The terminal005 receipt identifies the exact selected command, exit result, before/after hashes and any external drift. Controlled synthetic code-path tests do not establish real-paper transcription truth, model judgment, covariance/model source reading or entire A105 completion.
