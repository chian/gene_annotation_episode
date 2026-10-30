# Scientific three-slot construction: implementation contracts

This is the historical SL1–SL5 contract and evidence checkpoint. Its in-place
P/T revision policy and scientific_selection port are superseded by
[FP0–FP7](../../docs/FIXED_PROCESS_BOUNDARIES.md). The current v2 mother retains
its original A/P/T, prepares alternative selections for new children and returns
existing per-episode results with explicit provenance. No additional score is
introduced. The historical checklist and verification artifact below are retained
as evidence of the earlier implementation, not proof of the changed behavior.

This plan follows inspection of the actual catalog, mother candidate, common runtime, caller setup and durable request paths. It replaces none of the retained A–I/LIB/TIME/CREDIT/CASE/SCIENCE/VERIFY tracking items. This increment contributes to LIB, D and F; literature implementation remains I. The interrupted whole-process C11–C14 proposal is not resumed.

The previous goal turn was progress: it produced the 42 separately addressable library entries, 208 source links, the all-142-case register and construction examples. Those are content, not runtime construction. This plan specifies the missing application integration.

## Scientific ownership and decisions

One registered recursive role, `scientific_process`, runs the ordinary shared Episode loop. An instance is filled from one A, one P and one T. Combinations are assignment data, never thousands of Python roles. Parent job, scope, evidence, constraints, exact typed return form and its initial interpretation values retain their owners.

A supplies annotation focus and distinctions. Its illustrative enums do not become new report fields, scoring axes or weights. P supplies alternatives, guidance and result-contingent revisions. T supplies evidence-operation information; explicit caller bindings identify actual executable capabilities. Unbound operations remain visibly unavailable. There is no compatibility reviewer, acceptance gate, automatic substitution, action selector, new agent loop or prescribed task order.

The scientific role can invoke itself and the caller-bound literature/launch/monitor/results entry roles. The existing specialist episode structures do not acquire artificial A/P/T selections. In particular, `literature -> strategy -> search -> page -> {table, ordered, targeted}` stays separate.

The user was asked whether P/T revision should stay within an episode or require a new child. Pending contrary steering, this plan uses an explicit recorded P/T revision within the same episode. Initial commissioning, A focus, parent job/form and prior outcomes stay unchanged. No implicit mutable selection is allowed. The revision interface is separate so this choice can be adjusted without changing catalog persistence.

## Fixed records

All persisted values are finite canonical JSON using method_loop.durable semantics. `*_sha256` below means the SHA-256 of canonical JSON unless explicitly named a file-byte hash. Option IDs are library identities, not Store record references. They never enter C1 input_versions or scientific receipts as observations.

```text
ScientificOptionRefV1 = {
 version: scientific_process_option_ref_v1,
 library_id: sha256,
 slot: annotation_distinction | thought_pattern | tools,
 option_id: A<digits> | P<digits> | T<digits>,  # namespace matches slot
 entry_sha256: sha256
}

ScientificSelectionV1 = {
 version: scientific_process_selection_v1,
 annotation_ref: ScientificOptionRefV1[annotation_distinction],
 thought_ref: ScientificOptionRefV1[thought_pattern],
 tool_ref: ScientificOptionRefV1[tools]
}  # all refs name the same frozen library

ScientificAssignmentV1 = {
 selection: ScientificSelectionV1,
 evidence_refs: unique Store-reference strings,
 constraints: finite JSON object,
 context: finite JSON object
}

FilledScientificProcessV1 = {
 version: filled_scientific_process_v1,
 selection: ScientificSelectionV1,
 assignment_sha256: sha256(ScientificAssignmentV1),
 invocation_sha256: sha256({objective, scope, purpose, report_schema, initial_report}),
 mechanics_binding: nonempty caller/mechanics identity object
}

ScientificRevisionV1 = {
 version: scientific_process_revision_v1,
 initial_selection_sha256: sha256(original ScientificSelectionV1),
 previous_selection_sha256: sha256(previous active ScientificSelectionV1),
 selection: ScientificSelectionV1
}  # same original A and library; P/T explicitly chosen anew
```

The original request message gains one optional key, **`scientific_process`**, containing FilledScientificProcessV1. Do not use the old single-process `process_binding` representation. `episode_assignment` remains the actual prepared assignment. The full C1 request hash already covers both; no method_loop commission or closure envelope change is needed.

The invocation digest excludes generated goal/episode IDs and covers the original parent-owned fields exactly. The C1 envelope separately pins ownership and the complete request. The mother checks the invocation and assignment digests against that request on reconstruction.

## SL1: immutable option records and library

Exclusive files: new `gene_annotation_episode/scientific_process_records.py`, `scientific_process_library.py`; new `tests/test_scientific_process_library.py`.

Exports from the record module:

```python
scientific_digest(value) -> str
validate_option_ref(value) -> dict
validate_selection(value) -> dict
validate_filled_process(value) -> dict
validate_revision(value) -> dict
```

Validators check exact versioned record fields, finite JSON, digest shapes, matching ID/slot namespaces and common library identity. They return detached JSON values. Meaningful parent-request comparisons remain in the mother.

```python
ScientificProcessLibrary.freeze(directory, *, source) -> ScientificProcessLibrary
ScientificProcessLibrary(directory)  # reopen original snapshot only
library.as_record() -> {version, library_id, manifest_sha256}
library.headers() -> tuple[compact header]
library.reference(option_id) -> ScientificOptionRefV1
library.resolve(option_ref) -> exact selected entry dict
library.search(*, slot, query, offset, limit) -> {library, entries, offset, limit, next_offset}
library.entry(option_id) -> {option_ref, entry, source_count}
library.sources(*, option_ref, offset, limit) -> {option_ref, rows, offset, limit, next_offset}
library.execute(name, arguments) -> ordinary ToolOutcome
catalog() -> retrieval tool schemas
```

`slot` in search is one of the three slot strings or null for all slots. Literal case-insensitive all-term metadata search is sufficient; retrieval does not choose relevance. Headers include pinned option_ref plus name/description, never whole bodies. Known IDs remain directly addressable through entry. Tool names: `process.search`, `process.entry`, `process.sources`. Source paging uses a full pinned option_ref.

Freeze the research index, each selected entry body and the option/source relationships into `<run>/scientific-process-library/`. Compute runtime pins independently of the research catalog manifest. Retain only headers/index metadata on the live library object. Guidance is already contained in selected entry bodies and participates in entry identity. Per-option source files can support bounded selected reads without keeping the whole source table resident. Validate that index identity, body identity and evidence/source rows agree. Preserve source limits; no raw papers, corpus archives or model calls are needed for freezing.

Freeze is atomic; an existing valid snapshot stays authoritative. Reads detect changed bytes/content before returning. Library outcomes contain empty scientific `record_refs` and `changed_record_refs`, including source-row reads. E-* identifiers are instruction provenance, never target observations or scientific credit.

Tests cover the real 42-entry source, small independent fixtures, a new data-defined entry, direct lookup/search/paging, index/body/source drift, changed original source after freeze, duplicate/malformed references, finite JSON and zero evidence publication. No runtime/mother dependency blocks this workload.

## SL2: caller-bound tool contexts

Exclusive files: new `gene_annotation_episode/scientific_tool_contexts.py`; new `tests/test_scientific_tool_contexts.py`.

Use the JSON pointer `/capability_operations/<zero-based-index>` as operation_id. It is stable only within the pinned T body; combining it with tool_ref identifies the exact declared operation without guessing meaning from prose. No research catalog rewrite or invented semantic operation names are needed.

Caller mapping input:

```text
[
 {tool_ref: ScientificOptionRefV1[tools], operations:[
   {operation_id: /capability_operations/N,
    tools:[{name: exact registry callable name, arguments_schema: object|null}]}
 ]}
]
```

Missing mappings are allowed and explicitly unbound. No implementation is inferred from normalized input/output prose or `confirmed_repository_callables`; a caller can explicitly use those known associations when building its mapping. No script installation/registration occurs.

```python
ScientificToolContexts(library, mappings)
contexts.as_record() -> {version, library, implementation_sha256, mappings}
contexts.resolve(tool_ref, available_catalog) -> {
 version, tool_ref, binding, operations, catalog, unbound_operation_ids
}
```

`binding` is the original caller mapping identity, not a snapshot of changing biological data. Each operation result contains operation_id, its actual available tool_names, unavailable_tool_names and bound/unbound status. `catalog` contains exact registry entries for the available names, with caller restrictions intersected into actual argument schemas. Reused names appear once. Multiple operation-specific restrictions for one name are alternatives inside the actual API constraint; a null restriction leaves the actual API schema intact. It never enlarges a real callable schema.

An empty scientific tool set is information, not an extra runtime rejection gate. Common reasoning/retrieval/history/waiting and permitted process calls still exist. The mother exposes unavailable operation descriptions, not executable schemas for them. Tool knowledge metadata follows the actual callable association; arbitrary knowledge titles do not enable tools.

Tests use the exact SL1 reference/body shapes and fake real-catalog entries. Verify empty/partial availability, missing names, no automatic confirmed-name dispatch, pinned operation pointers, duplicate mappings, caller schema intersection and no mutation of input catalogs. SL1 implementations need not finish before writing/testing resolver fixtures.

## SL3: one scientific mother binding

Exclusive files: new `gene_annotation_episode/scientific_process_episodes.py`, `scientific_process_setup.py`; new `tests/test_scientific_process_episodes.py`. Do not edit runtime.py, existing specialists, old LibraryEpisodes or the slot modules.

```python
ScientificProcessEpisodes(services, *, library, tool_contexts, child_roles)
```

Implements the complete existing EpisodeBinding port for exactly the role `scientific_process`; credit_kind is scientific and uses the caller's existing service projection. Caller child_roles names only actual registered scientific/specialist entry roles and always includes scientific_process itself. They are narrow type alternatives, not an itinerary.

The standard parent-selectable assignment schema is ScientificAssignmentV1. Validate explicit evidence_refs against the supplied scientific scope and preserve them as initial references, so they do not earn new contribution credit. Job objective, scope, purpose, form and initial report remain outside that assignment in the existing parent request.

```python
prepare_invocation(parent, role, inputs, scope, operation_key, *, invocation)
 -> {assignment: ScientificAssignmentV1, scientific_process: FilledScientificProcessV1}
```

`invocation` contains exactly `{objective, purpose, report_schema, initial_report}`; scope is supplied separately. Compile/validate the parent's exact closed form before calling this method. Preparation validates and freezes the selected information; it chooses no A/P/T values, capabilities or scientific action. The mother never installs A's example fields into that form.

The initial request's FilledScientificProcessV1 must survive `Workflow.build` and worker reconstruction. Validate it before constructing model context or projecting initial credit. Primitive execution delegates to services.execute_tool using exact selected operation key/scope and the same narrowed schema. Original report/reference validation uses existing services; no new freehand findings channel or report composer is added.

The decision frame contains:

- A claim_scope, distinctions and unsupported extensions.
- P use_when, live_alternatives, decision_guidance, outcome_contingencies and boundary.
- T operation descriptions/limits and actual bound/unbound operation information.
- The selected references and current revision metadata.
- Existing parent assignment and permitted child roles.

Source-case bodies are separately retrievable instruction provenance, not injected target observations. No automatic compatibility verdict or guessed scientific conclusion is returned.

Common tool whitelist includes the three process retrieval tools, the existing knowledge retrieval tools, and actually available episode history/credit/annotation/monitoring/wait-estimate helpers. The mother catalog adds its own `process.revise` schema alongside selected T primitives. Common action types are tool/reason/child/wait/redeliver_report; no timer cadence or stopping policy is introduced.

`process.revise` input is exactly `{thought_ref, tool_ref}`. It preserves the initial A and same library, validates the new P/T and caller mapping, and returns a completed ordinary ToolOutcome whose result is ScientificRevisionV1. No Store records change. The existing own-action journal persists the revision outcome and ordinary observation; credit remains whatever the unchanged projector observes, normally zero. Repeated selection creates no fictitious contribution. It does not rewrite the commissioned binding or old contexts.

Required additional scientific service port:

```python
services.scientific_selection(context) -> {
 selection: ScientificSelectionV1,
 revision: ScientificRevisionV1|null,
 decision_index: int|null
}
```

The root/runtime implementation reads only this episode's original request and latest completed own process.revise result. It validates the selection against actual selected arguments and prior selection identity. It does not read private child history or poll work. Mother unit tests supply this exact port as a fixture. Fresh turns use this active frame; pending/replayed decisions keep their already saved context/schema.

Setup helper:

```python
prepare_scientific_binding(*, run_directory, source_directory, mappings, child_roles) -> descriptor
```

It freezes/reopens the run catalog and returns an ordinary caller-owned scientific_process binding descriptor. Configuration contains the frozen library descriptor and literal tool mappings/child roles. It starts no model, job or child. Composer uses the actual run directory to reopen the snapshot; the source research directory is not consulted by worker reconstruction.

Tests use SL1/SL2 contract fixtures: differing data-defined P entries instantiate the same class, A/form preservation, schema narrowing, actual selected execution, unavailable operations, inherited references, iterative changing outcomes, explicit revision and separation from existing literature roles. Fixtures prove engineering behavior only.

## SL4: common construction and durable consumers

Owner: coordinator. Exclusive existing files: runtime.py, episode_services.py, episode_composition.py, independent_execution.py; case_execution.py only if an actually traced forwarder needs it. The EpisodeServices protocol also declares the new selection port. Keep old specialists and all three new-module owners' files separate.

1. Known `scientific_process` descriptors reopen the frozen catalog and same mappings in compose_episode_bindings. Add the actual run directory as an explicit optional composer operand; it is required only for this new binding. The complete descriptor enters existing saved episode_bindings before settings_sha256. Python-only implementation pinning is insufficient by itself.
2. New runs that register this scientific branch expose its A/P/T assignment constructor. Remove the raw unfilled `kind:child -> improvement` route for these profiles; direct selection cannot bypass the same rule. Markerless historical profiles retain their exact saved semantics.
3. In selected(), compile the parent's form and initial report before calling prepare_invocation. Preserve the returned scientific_process alongside episode_assignment. Existing bindings still use prepare_assignment. Do not opportunistically run the interrupted C11 single-process constructor.
4. build(..., scientific_process=None) writes that optional field only when supplied, validates it through the scientific mother before any model work/initial projection, and compares the complete immutable request with saved state. Existing markerless requests do not gain fields.
5. Add process retrieval tools only when this scientific library is explicitly bound. They use ordinary action accounting. Apply optional common_tool_names restrictions after runtime helper augmentation. Honor permitted tool and redeliver actions. Execution validates the same final allowed catalog before runtime-common dispatch; hiding a tool only in the displayed schema is insufficient.
6. Supply the scientific_selection read port using authoritative own action/result rows. Original selected arguments, original initial binding, P/T refs and prior-frame digest must agree. Do not add a second selection ledger, synthetic observation or silent change during replay.
7. Preserve relevant execution forecasts, outstanding commitments, pending work, received progress and configured numerical continuation in scientific contexts. A new role label is not permission to omit pre-choice time/resource information. This increment does not invent the still-unresolved numerical wait-gain model or production credit units.
8. open_commission forwards scientific_process from the saved request to build; the existing worker exact-request check remains authoritative. Known standard/case descriptor restoration reopens the original snapshot/mappings. Source-directory changes or later parent knowledge cannot replace the saved inputs. Missing/drifted bindings fail structurally before transport.

No method_loop loop/envelope change, private background loop, second scientific state, new scheduler or allocation policy is planned. C1 already pins the full request. Original closure, parent-form admission, received contributions, completion order, archives and controller paths remain the consumers to verify.

### Integration amendments established by connected code/tests

These changes were identified while joining the agreed module outputs, rather than assumed as prerequisites for the parallel module jobs:

- Forecast-role validation now runs after the actual binding registry is assembled, before provider entry. A scientific profile's tree omits the unreachable legacy improvement parent. Fixed-case PolicyBindings gains optional `execution_planning_roles: tuple[str, ...] | None`; explicit roles are persisted and restored, while None retains the original marker and annotation/improvement default. This is a caller selector, not a new duration or continuation formula.
- Composed/reference-bearing tool argument schemas keep their exact standalone constraints. The host action schema isolates local references with a content-addressed schema resource. Only model transport encodes those arguments as a JSON string; decoding preserves omitted fields and explicit nulls before authoritative validation and execution. Scientific assignments likewise use JSON transport so finite parent context/constraints are preserved. Return forms are unchanged. The converter traverses schema locations, leaving schema-shaped literal data intact. Malformed transport is ordinary action feedback inside the existing validation boundary.
- Own-history metadata recognizes scientific episode_child and wait actions and actual registered child roles. It does not load child conversations or change completed observations.
- The actual receipt-enabled detached fixture exposed an unconditional commit in EpisodeReceipts.bind, which destroyed selected()'s outer savepoint. Binding inheritance now uses Store.transaction for atomic read/prefix/insert and joins the original commissioning transaction. This is a required shared receipt consumer repair, not a new ledger. A rollback check and the actual worker fixture verify this boundary.

## SL5: assembled verification

Coordinator owns new integration tests, separate from each module test file. Tests require the actual Workflow constructor, action schema, execute, durable commissioning/reconstruction, returned form and restart paths, not just a pure formatter.

- Show a parent selects A/P/T and receives the original typed child form after outcome-informed iteration.
- Add a new data-defined option without a new Python episode role; prove narrowed tools/context and unchanged parent form.
- Change P/T through an explicit revision and show only later fresh decisions change; original commission, A, prior rows and observations survive restart.
- Show common-tool dispatch and raw-child routes cannot restore excluded choices.
- Show unbound candidate capabilities remain informational and no wet-lab/script execution is invented.
- Show the original frozen catalog and caller mapping survive parent/worker reconstruction, source changes, interruption around commissioning, and pending model decision replay.
- Show library reads/revisions publish no scientific observations or extra contribution credit; supplied evidence is inherited and repeated returns retain existing exactly-once behavior.
- Preserve separate literature children, numerical controller, pending waits, before-choice duration information and surviving-descendant/closed-history behavior.

After focused module/integration checks, use the actual configured model connection in an isolated fixed-target development workspace only when remaining production bindings and timing/continuation requirements are ready. Do not resume competing roots in investigation_009's shared workspace. A scripted suite does not complete SCIENCE, TIME or VERIFY.

## Development dependency graph and dispatch

SL1 produces validated refs/bodies/snapshot methods. SL2 consumes those JSON shapes and produces narrowed actual catalog data. SL3 consumes the same refs plus SL2 resolution data and the service-selection port. SL4 consumes the filled binding, descriptor and public methods. SL5 consumes all implementations together.

The depended-on outputs are fixed above, so SL1, SL2 and SL3 can code in parallel with fixtures. They do not wait for one another's implementation. The coordinator reads complete affected consumers and implements SL4 in parallel; only connected verification waits for the implementations. No runtime episode nesting relationship is treated as a serial coding dependency.

### Stable increment checklist

- [x] SL1: frozen option records/retrieval and source pins.
- [x] SL2: explicit caller tool-context resolution.
- [x] SL3: common scientific mother and explicit recorded P/T revision.
- [x] SL4: runtime/caller/durable reconstruction consumers.
- [x] SL5: connected engineering evidence and precise remaining production limits.

Keep completed items visible. This checklist is the current LIB integration increment, not a replacement for the full implementation checklist.

Completion evidence is recorded in [RUNTIME_INTEGRATION.md](RUNTIME_INTEGRATION.md)
and [integration_verification.json](integration_verification.json). The eight new
test modules contain 153 passing feature checks, including one actual subprocess
test. Providers, credit units and stopping counts in that test are fixtures.
No configured-model scientific demonstration, production wait-gain formula or
completed production profile is claimed.
