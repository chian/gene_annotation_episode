# Scientific-parent API forecasts before a first launch commission

Status: **UNADOPTED DESIGN ONLY**. Prepared 2026-10-22 for root review. This document authorizes no implementation, caller configuration, scientific action or resource selection. No 003 source, tests, configuration or saved state were changed for this proposal. A later 004 checkout requires root's recorded adoption of the exact proposal and corrections.

The inspected source is `/tmp/gene-annotation-hmmer-api-20261022-003`, implementation source pin `cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623`. `READSET.json` pins the actual files behind this plan. The immutable goal, current AGENTS/GOAL and episode/time-estimation design remain authoritative. Scope016 explicitly left this scientific-parent planning path open; scopes017–025 preserve its already implemented assigned-Launch/API behavior.

## Proposed increment

Make an API branch available through the **existing real `execution.estimate` tool**, only through a new explicit caller factory, before freezing the scientific callable map. A scientific episode may select that ordinary information action with a real registered subject, explicit algorithm, database, parameters, API candidate and constraints. Its next decision receives the original recorded API forecast before it decides whether or how to commission its first Launch.

This supplies an available informed path. It does not force the first decision to use the tool, enumerate proposed searches, choose a candidate, require an experiment or ensure that every scientific episode obtains a forecast. An episode without a proposed real request has no fabricated forecast. A constructed scientific child must actually receive `execution.estimate` in its retrieved, parent-selected `selection.tools`; the common runtime must not make it available outside that selection.

Keep the API report source and schema from003 exactly: `api_reported_execution_forecasts`, `API_REPORT_ESTIMATE_SCHEMA`, phase `remote_protein_homology_search`, measure `hmmer_reported_search_elapsed_seconds`, unit `logical_provider_job_reported_result`, compatibility `same_exposed_technical_configuration_unknown_remote_revision`. No additional score, numeric report source, continuation rule or waiting input is introduced. The optional forecast action records one ordinary own-action observation with the existing controller and credit behavior; it creates no measured timing information contribution.

## Why this seam

| Candidate | Actual trace | Decision |
| --- | --- | --- |
| Extend `execution.estimate` with an explicit API branch | `ToolRegistry.catalog` owns this name; `WorkflowServices` resolves the actual registry; `ScientificToolLibrary` freezes full contracts; ordinary operation replay already persists results. | Adopt this seam, conditional on a new explicit planner binding. Preserve all old native branches. |
| Add `execution.estimate_api` as a runtime helper | It would need an additional primitive identity and must still enter the actual frozen map. A runtime-only helper would be absent from constructed scientific selections. | Reject for this increment. |
| Reuse `api_search.*` as scientific primitives | These exist only inside `HmmerServiceResourceAdapter.catalog` for an assigned resource episode, and operate on its existing order/assignment. | Reject; these are not real scientific-parent registry tools. |
| Add automatic forecasts to every scientific decision | No current scientific proposal owner supplies algorithm/database/parameters/subject for an unselected request. Native prospective enumeration is not an API proposal contract. | Reject; this would invent configurations or choose candidates. |
| Pretend the parent is a Launch `BindingContext` | `qualify_launch` requires assigned resource semantics and can lead to order creation on child preparation. | Reject. Extract pure request/constraint preparation and reuse it explicitly. |

## Exact callable and availability

Add proposed public factory `bind_assembled_services_with_public_search_timing_planning`. Its complete keyword signature mirrors `bind_assembled_services_with_public_search_timing` and the existing assembled operands. It requires `tool_registry` and `tool_catalog` through `episode_service_inputs='actual_tool_registry_v1'`, explicit `public_search_registry`, actual `ApiTimingBinding`, and actual `ResourceToolEstimator.with_reported_results()`. It supplies no resource ID, paths, unit, allocation, algorithm, database, model or sequence default beyond the existing selected tool's parameter/page defaults.

The caller's saved service definition must distinguish this opt-in, for example with exact marker `api_execution_planning: {version: 'hmmer_api_execution_planning_v1', callable: 'execution.estimate', target: 'public.hmmer.search'}` in its explicitly supplied definition. That marker is configuration identity, not an automatic policy. Existing factories and their saved descriptors keep their current output shapes.

Proposed planner owner: `ApiExecutionPlanner(store, *, run_id, ports, timing, resource_estimator)` in new `api_execution_planning.py`. Exact types and equality checks precede attachment: `ports` is actual `PublicSearchPorts`; operations/publisher/registry tool instance have the same Store; operations.remote_searches is the actual tool registry's remote_searches; timing is its exact operations.timing owner and its Store/run/registry agree; the estimator is the supplied v3 object. Use public owner records/accessors only. Do not depend on private ledger/history tables.

Proposed `ToolRegistry.bind_api_execution_planner(planner)` accepts that actual type, verifies its exact ToolRegistry/Store/client/registry identity, and attaches it. Repeating attachment with the same complete immutable descriptor is idempotent; a differing descriptor rejects with an identity conflict. After validating the supplied actual object, an equal-descriptor attachment replaces the old Python handle and returns the supplied object. This matters because existing composition reopens equivalent factory ports/ledger as new objects: the composed API adapter, timing_reader and final registry planner must all use the supplied composed ports/timing instance, not retain the earlier factory object's handles. No mutable planner cache survives that replacement; the frozen map bytes remain equal. No transport, order, submission, result acquisition, measurement export or choice occurs at attachment. An attached registry is owned by that run; sharing it between distinct runs is rejected, consistent with the planner's run-bound owner.

Factory ordering is essential:

1. Compare Workflow's supplied `tool_catalog` with `tool_registry.catalog()` before attachment, using the actual full contract map. Reject a stale/foreign supplied map. On identical reattachment, compare against that registry's current actual map instead.
2. Bind the same existing timing statistics, ledger and `PublicSearchPorts` as003, then construct and attach the planner.
3. Recompute `tool_registry.catalog()` and pass **that actual post-attachment map** to `_bind_assembled_services` / `prepare_scientific_binding` before `ScientificToolLibrary.freeze`.
4. Bind the existing resources, credit and progress owners. No caller-provided map fragment may stand in for the recomputed registry catalog.

`ToolRegistry.catalog` has one `execution.estimate` entry. If only native statistics are bound, its description/schema/configuration remain exactly old. If the API planner is attached, append the API input branch to the current `anyOf`; if no native statistics exist, include only that API branch. Copy `arguments` verbatim from the actual target's registry `input_schema`, including domain.REF's ID/alias pattern and description; assert exact schema equality rather than rebuilding a broader reference schema. The API branch's `resource_selection` is an exact closed const of the caller's actual API selection. Add its actual planner `configuration` to the catalog only in this opt-in. This makes availability and owner identity visible to the real map/retriever and prevents exposing a branch without its actual callable owner. Preserve the `anyOf` shape because literature filters existing native workbook branches by `branch.properties.tool.const`.

The existing semantic `process.tools` operation must see this real full map and return actual selected names. It still makes only a retrieval decision. `ScientificProcessEpisodes._tool_resolution` must continue requiring exact selected contract equality. No retriever prompt, process definition, child-selection rule or unconditional common tool changes are required.

## Exact parent input

`SCHEMAS.json` contains the proposed complete input/output schemas, their fixed source constants and copied unchanged003 forecast schema. `$defs.api_estimate_input_template` uses an explicit documented placeholder only for the caller's actual selection; code must instantiate that placeholder with the exact bound registry selection, not leave it symbolic.

The API `execution.estimate` branch is a closed object with all five fields required:

```
tool: 'public.hmmer.search'
arguments: the actual existing public.hmmer.search input schema
resource_selection: exact actual API candidate selection
constraints: the closed supported API constraint object
immutable_input_versions: array of the existing INPUT_VERSION_SCHEMA
```

`arguments` requires `subject_ref`, `algorithm` (`phmmer` or `hmmscan`) and nonempty `database`. `parameters` and `page_size` retain the exact current ordinary tool optionality and defaults (`{}` and50). Parent-supplied nondefault settings must be supplied explicitly. All original supplied arguments, including omitted versus explicit defaults, remain recorded. No new caller-provided query length, raw FASTA, release or implementation version field is accepted.

`resource_selection` names the caller's actual bound resource ID, `kind='api'`, exact registry capability ref, and the four unknown allocation values as null. It identifies the candidate being estimated; it does not commission or constrain the episode to select that candidate later. `constraints` supports only the existing API keys: resource_id, kind, allowed_resource_ids, allowed_kinds, cpu, memory_bytes, scratch_bytes, wall_seconds. Its explicit allowed lists must contain the candidate; individual resource/kind values must agree; allocation constraints must agree with unknown/null allocation. An incompatible requested allocation yields the current structured argument/resource failure rather than silently substituting a resource. An empty constraint object leaves choice open.

`immutable_input_versions` is explicit, including `[]` when the parent supplies none. Reuse existing scope/version/content digest checks. Do not infer a remote version or fabricate an input pin. The parent supplies its real proposed subject and settings after receiving actual information; this plan does not choose the fixed gene's product, an algorithm or a database for it.

## One shared operand preparation

Introduce pure module `hmmer_request_preparation.py`, with proposed contract:

```
prepare_hmmer_request(arguments, *, sequence_symbols, scope)
    -> PreparedHmmerRequest(arguments, normalized_arguments, request, query_fasta)
qualify_api_candidate(store, *, scope, selection, constraints,
                      immutable_input_versions) -> None
```

`PreparedHmmerRequest` is an immutable in-process value, not a new durable record or episode. `arguments` preserves original supplied keys. `normalized_arguments` has exactly subject_ref, algorithm, database, parameters, page_size. `request` is the actual closed11-field HMMER request from `provider_jobs.build_search_request`; `query_fasta` is the exact submitted UTF-8 string. Both the original public tool input schema and existing assignment checks govern accepted input; reject nonfinite numbers before canonicalization with a structured argument failure.

Preparation calls the supplied actual sequence accessor for the exact registered reference and scope, uses `>` + actual subject ID + newline + actual symbols, and calls the existing sole normalizer `build_search_request(provider='hmmer', ...)`. Sequence length and both hashes are measured from these actual bytes/symbols. Do not infer them from gene labels or pass scientific identifiers into shared history features.

Use this helper in all three affected paths: (1) actual `ToolRegistry._acquire_async('public.hmmer.search')`, (2) the new planner via actual `PublicSearchPorts.sequence_symbols`, and (3) fresh `ApiSearchInformationReader.request_for_assignment`. Keep the existing-job branch's saved request/FASTA/order qualification unchanged. The ordinary actual dispatch must use the returned exact FASTA and normalized arguments, then retain the present molecule metadata on its snapshot. The selected API order path must use the same exact returned request/FASTA. `provider_jobs.build_search_request` itself and provider transport remain unchanged.

Extract the current reader `_versions`/`_constraints` implementations into `qualify_api_candidate` and have both the reader and planner delegate, preserving their original accepted meanings/errors. Do not construct a fake Launch context. `ApiReportedStatistics._features` remains the sole technical-class boundary. For example, nonempty taxonomy filters remain a valid selected search but produce explicit unsupported timing statistics; estimation cannot forbid that work.

## Closed result and capture semantics

Keep the standard ordinary tool envelope (status, operation_ref, record_refs, result, feedback and existing optional fields). On a successful information operation, `record_refs=[]`; `result` has exactly:

```
version: 'api_execution_proposal_estimate_v1'
tool: 'public.hmmer.search'
arguments: original arguments
normalized_arguments: actual five-field normalized arguments
scope_sha256: SHA256(canonical(actual normalized scope))
resource_selection: original exact candidate
constraints: original constraints
immutable_input_versions: original explicit pins
request: actual11-field normalized HMMER request
request_sha256: SHA256(canonical(request))
api_reported_execution_expectations: [original ApiReportedStatistics.capture(request)]
api_reported_execution_forecasts: original estimate_reported_context(capture) rows
api_execution_options: existing api_execution_option_v1 rows
api_timing_planning_disposition: existing closed TimingDispositionV1
```

No execution_handoff, order/job/remote UUID, acquisition receipt, observation time or duration measurement is fabricated. B's `proposal_ref` remains the execution-class identity currently emitted by v3; it must not be described as a unique biological request or commission identity. Different biological requests can intentionally share the same exposed technical class. Their exact local request is distinguished by `request_sha256`, scope, explicit pins and standard selected-operation journal identity. These request identifiers remain local and never enter shared statistical observations.

Planner `estimate(arguments, *, scope)` prepares/qualifies exactly once, calls `timing.statistics.capture(request)` exactly once and `resource_estimator.estimate_reported_context(capture)`. It forms options by the same fields/rules as003 `HmmerServiceResourceAdapter.decision_context`; factor a small pure option/result builder if useful, without changing that adapter's output. No re-export recovery or current-condition recapture occurs in this information tool. Capture may persist an immutable expectation snapshot in the already configured existing shared history, as its present API does; it creates no missing history/schema, condition, measurement or scientific record.

Available empty history yields known zero support and null duration. Missing/locked history/schema and unsupported technical configuration retain original capture codes and closed unavailable/invalid forecasts, without becoming a work gate. Valid search arguments with an ordinary unavailable or explicit invalid_statistics capture still produce a completed information-tool result. The disposition code is the capture code when already allowed by existing TimingDispositionV1; explicit capture code `invalid_statistics` maps to existing `timing_binding_unavailable` in that disposition only, because its closed code set does not contain `invalid_statistics`. The capture and forecast retain their original invalid-statistics meanings. A malformed nonconforming capture body produces a specific structured invalid-statistics tool failure rather than widening the closed result, rewriting a snapshot or publishing untyped content. Invalid references/scope/constraints/versions retain the existing ordinary structured invalid/failed outcome. No forecast failure commissions, suppresses or cancels any selected job. No attempt is made to guess remote allocation, build, database release, corpus digest or corpus size.

Validate the result against its closed schema before persistence. Beyond schema validation, verify normalized request digest, scope digest, exact candidate owner, original argument normalization, capture class identity, expectation content-addressed ref, row projection from the **original capture**, and options/disposition relationships. Result read validation must use the original journaled request/capture, never current sequence bytes/history/conditions. A malformed capture raises `ContractError('invalid_api_execution_statistics')`; malformed or inconsistent original local proposal payload raises `ContractError('api_execution_proposal_conflict')`. These codes pass through the existing ordinary structured feedback path; a plain ValueError would collapse to generic invalid_tool_input. Known candidate/version failures retain their existing specific codes by wrapping them as ContractError at the new tool boundary, without changing the reader's existing ValueError behavior. The copied schemas document the existing typed snapshot fields without widening shared statistics or communication.

## Dispatch, journal and prechoice context

In `ToolRegistry._execute_operation_async`, branch `execution.estimate` by the selected `args['tool']`. The actual API target dispatches to the attached planner; native targets continue to `_estimate_native`. `_perform` continues returning the prepared result and no scientific records. Do not send API arguments into the current `_estimate_native` nonalignment/workbook `else` branch.

Use the existing `tool_operations` idempotency protocol. Same operation_key/name/arguments/scope returns the saved exact original envelope; different work rejects. A crash after a shared capture but before local save can leave an unused immutable shared expectation snapshot, as with existing estimation, but cannot create a job or measured contribution. Once the tool operation is saved, recovery into runtime_actions must reuse that exact payload and must not recapture history.

`Workflow.execute` presently assumes any completed `execution.estimate` has `result.execution_expectations`, a native-only field. Add an API-version/target discriminator first, tied to the actual selected tool arguments: selected name must be execution.estimate, selected arguments.tool and result.tool must both be public.hmmer.search, result.version must be api_execution_proposal_estimate_v1, and result.arguments/candidate/constraints/versions must equal the actual selected input. A tagged arbitrary payload cannot enter this branch. For API results, copy the original API capture/forecast/options/disposition onto the runtime action at their existing separate top-level names; leave native arrays/fields untouched. The existing final API context-copy loop must retain newly produced API fields instead of overwriting them with an older preselection context. Other tools still retain the original selected-decision API snapshot as003 does.

Add proposed helper `Workflow.api_execution_planning_context(source, *, before_decision_index)` or equivalent private pure journal projector. It is enabled only by this actual planner binding and only reads the caller's own completed `execution.estimate` actions with nested version/target `api_execution_proposal_estimate_v1/public.hmmer.search`, matching run, episode and the original fixed scope. Select the latest such explicit proposal, including an unavailable result, not the newest available forecast from a different request. Read its saved original tool payload and verify the closed integrity relationships above; no private child history, shared history scan, scientific source scan or new Store policy.

For a new decision, `DecisionSource.call` merges that helper's original result under `api_execution_proposal`, and its existing API capture/forecast/options/disposition fields into context **inside the unsaved-decision branch**. This also covers actual direct callers of call(), not only next(). An existing saved runtime_model_calls request remains authoritative and is returned byte-for-byte without injection, repair or recapture. The original proposal is explicitly labeled with its arguments and candidate; it is not silently rebound to a later revised job. A newer explicit estimate changes future context; older proposals remain addressable through existing own history.

No API proposal exists before the parent supplies real operands. The parent may select one estimate, inspect its outcome, revise, select another action, commission Launch, or yield under its unchanged controller. When it commissions Launch, its actual model-call request already contains the API forecast; the saved request plus original runtime action establish which facts preceded that choice. Do not extend native-only commission `expectation_snapshot_refs` to these provider intervals. Scope003 Launch and launch_api later capture their own original assigned-work/pre-POST forecasts; those later snapshots can differ and never replace the parent's earlier one.

## Typed facts, custody and credit

The existing003 separate `reported_report_source()` / `api_reported_execution_forecasts` remains the only new timing forecast report source. `recorded_api_forecasts` reads top-level saved own-action/context arrays; `api_forecast_reference` resolves own declarations or received declared typed forms; `validate_recorded_estimates` enforces original row values. The new selected tool's original top-level arrays therefore join these actual consumers without schema unions, source renaming or a new report composer. A scientific child can return these rows only through its parent's explicitly requested existing typed source. Parent reference admission/redelivery/row tampering and cross-episode isolation remain the existing boundary and require joined tests.

A forecast is an expectation over prior typed global observations. It is not a new provider reported-duration witness, a received timing source, or scientific evidence. This action does not publish `episode.hmmer_reported_timing`, add api_timing_refs, create native execution receipts, alter the single monitoring-information union/baseline or earn an invented monitoring credit. Later actual selected API result acquisition continues through003 custody/publication and earns credit only as presently bound. Scientific/operational projectors and controllers stay exact; no new local observation is created by context projection or capture refresh.

The parent's received forecast is not a pending-work wall-time prediction. Do not change WaitInputs, wait estimation, commission expectation namespaces, local yield units, successful-duration interpretation, outcome reliability, continuation numerics or action ordering. Preserve all original API/native semantics.

## Saved reconstruction and default compatibility

Save proposed planner descriptor exactly as:

```
version: 'hmmer_api_execution_planner_v1'
ledger: complete existing ApiTimingLedger.as_record()
resource_estimator: exact supplied v3 estimator.as_record()
callable: 'execution.estimate'
target: 'public.hmmer.search'
preparation_version: 'hmmer_request_preparation_v1'
implementation_sha256: SHA256(new api_execution_planning.py bytes)
preparation_sha256: SHA256(new hmmer_request_preparation.py bytes)
```

Add `hmmer_service_resource_adapter_v3` only for planning-enabled resource assembly, preserving its current v2 fields and adding `api_execution_planning` with that descriptor. `bind_resource_services` accepts an explicit optional planner and passes it into the API adapter; default None emits exactly current descriptors. `episode_composition` recognizes v3, obtains exact public ports/timing through the existing `WorkflowServices.public_search_ports` resolver, checks the supplied v3 estimator, reconstructs the exact planner and idempotently attaches it through a narrow new service binding method. Compare the complete adapter/planner record. An exact owner mismatch rejects before any work. Transient custody availability retains the existing same-shape ledger behavior and cannot create a fallback owner.

This descriptor is authority for direct saved service reconstruction. The new explicit factory attaches before scientific map freeze on normal root and worker construction; composition's v3 branch supplies the same actual attachment for saved direct descriptors. Both routes must finish before any real map resolution or model decision. Expose the exact planner from composition only if runtime requires it; do not introduce an arbitrary callable in a durable record.

`PolicyBindings.resource_estimator` from scope022 already preserves the caller's explicit v3 estimator through fixed_case root/resume/detached worker. The saved policy marker/source pins and service definition describe the chosen new factory. No policy schema or worker transport change is needed. The worker builds actual tools, compares their **base** `resource_binding()` with `initial_tool_resources`, then invokes the same caller factory and compares saved specialist descriptors/projectors/maps. Do not put this post-factory planner into base `ToolRegistry.resource_binding()` or the earlier comparison would fail on legitimate reconstruction. Its authority is the explicit service definition, planner descriptor and actual frozen tool contract instead.

Default/no-API, public-search-without-timing and timing-only003 factories keep identical catalogs, signatures, descriptors, report sources and behavior. Old native `execution.estimate` payloads, recorded requests and replay are exact. Opening an old frozen map using the new opt-in factory is a deliberate binding mismatch; do not silently widen that run's callable map. A new run/checkpoint under the explicitly accepted004 source is required for the new feature. Existing003 scientific publications/pins/state are untouched.

ToolKnowledge is frozen earlier than the service factory and currently has no `execution.estimate` or API HMMER guide. For this bounded increment, preserve the default knowledge library exactly. Put the short invocation/semantics/failure information in the actual opt-in catalog contract; it is available to process.tools and reasoning. Do not add a manual after freeze or claim an attached guide exists. A future caller-supplied knowledge library must be selected before Workflow construction and pinned by existing mechanisms; it is not required or fabricated here. This is a tool addition within the current generic scientific process, not a new process or whole episode.

## Proposed004 implementation ownership

Freeze the following three contracts before parallel edits: (a) PreparedHmmerRequest and qualify_api_candidate, (b) planner descriptor/method/output schema, (c) runtime top-level projection/context rules. No worker may privately redefine a shared type or access another owner's private tables. Scope expansion must name the actual uncovered consumer before edits.

| Owner | Exact proposed source files | Exact proposed tests | Contract to other owners |
| --- | --- | --- | --- |
| P: preparation and actual tool dispatch | NEW `hmmer_request_preparation.py`; `tools.py`; `hmmer_resource_information.py` | NEW `tests/test_api_execution_preparation.py`; NEW `tests/test_api_execution_tool.py` | Pure shared preparation and candidate validation; `ToolRegistry.bind_api_execution_planner`; actual conditional catalog/dispatch and idempotent replay. Import planner type locally to avoid a cycle. |
| B: planner and explicit binding/reconstruction | NEW `api_execution_planning.py`; `assembled_service_setup.py`; `resource_service_setup.py`; `hmmer_resource_adapter.py`; `episode_composition.py`; `episode_services.py` (binding access only) | NEW `tests/test_api_execution_planning_binding.py` | Planner exact type/descriptor, estimate method and closed payload; new explicit factory before map freeze; adapterv3 and exact same-owner reopen. No runtime loop edits. |
| R: recorded context and runtime consumer | `runtime.py` only, with a private helper or NEW `api_execution_planning_context.py` if justified before coding | NEW `tests/test_api_execution_planning_runtime.py` | API/native discriminator; original result arrays; own original proposal in unsaved prechoice context; preserve replay/defaults/controllers. No forecast schema edits. |
| Root: connected evidence | No production source unless a separately scoped actual consumer defect is found | NEW `tests/test_api_execution_planning_connected.py`; NEW `tests/test_api_execution_planning_reconstruction.py` | Join actual registry→retrieval→constructed scientific parent→estimate→pre-first-Launch context→commission→typed facts and real scripted detached fixed_case reconstruction. |

No proposed edits to api_reported_statistics.py, api_timing_records.py, run_statistics.py, resource_estimation.py, communication.py, generation_schema, method_loop, native timing/projectors, numerical controllers, waits, case_execution.py, tool_configuration.py, independent_execution.py, scientific tool library/retriever/process selection, literature filtering or default knowledge files. Those are inspected compatibility consumers, not speculative expansion points.

## Required later verification

1. Preserve first failures and source/test pins. Static schema checks alone do not prove the path. Assert no transport/order/intent/witness/publication/controller calls during factory or estimation; the configured existing history capture is the only statistical snapshot write.
2. Shared preparation: actual registered operands and scope coverage; actual lower/whitespace sequence normalization, submitted FASTA bytes, omitted/explicit defaults, parameters, explicit versions and out-of-scope rejection. Compare planned request to actual ordinary search and API-order request using local fixture transport only. Unsupported nonempty taxonomy filter still allows the actual search and returns explicit unavailable forecast.
3. Availability/map: native-only catalogs exactly equal003; API-only registry gets only the API branch; mixed map preserves every native branch; stale/foreign/full-map conflicts reject. Literal and scripted semantic retrievers see the actual extended contract; constructed scientific selection with no execution.estimate cannot execute it. Literature's workbook-only filter still works unchanged.
4. Typed estimate/result: known empty support, missing/locked/history-schema cases, two conditions, invalid statistics, exact explicit arguments/request/class/options/digests. No null/unknown becomes zero runtime or reliability. Same operation replay after history growth returns exact old envelope. Different operation may learn; old snapshots remain byte-equal.
5. Actual scientific decision path: a scripted generic scientific parent explicitly proposes a real request, selects execution.estimate, then receives the original payload and forecast at its next REASONING call **before its first Launch commission**. Assert no order/POST before that commission, no model composer and unchanged one-observation/controller scalars. Parent can revise or choose other work; no forced first-slot selection.
6. Source/ref boundary: parent-defined API forecast form accepts exact recorded rows, rejects field/ref tampering, unreceived private child rows and cross-scope/episode source use. Redelivery earns no new information. No measured duration receipt/score is created by forecasting. Ordinary biology, native timing supplementation and already implemented API monitoring union remain unchanged.
7. Replay: saved decision schema/context wins over today's library/history; next new decision uses only latest own explicit proposal. A later Launch/launch_api snapshot can differ from the earlier scientific snapshot while both originals remain exact. API fields never enter native resource_tool_estimates/commission expectation refs/wait inputs.
8. Actual fixed_case root/resume/detached worker: explicit v3 PolicyBindings, new caller factory, real frozen full map, scripted FAST/REASONING and local fixture transport only. Assert same Store/client/registry/ledger/planner/estimator authorities, including actual Python identity of the final composed ports/timing used by adapterv3, timing_reader and ToolRegistry planner; assert original action replay and future learning across another actual caller. Mismatched saved owner/map/implementation/resource configuration rejects without work. Preserve source pin and retained worker/journal artifacts.
9. Run narrowly selected existing compatibility tests that do not execute native jobs; inspect node IDs first. Any actual native engineering execution requires separately stated root authorization. No active scientific workspace, configured-model session, public endpoint or original unregistered actualservice job is part of these tests.

## Evidence and limits of this planning pass

This pass performed read-only source/document inspection, a separate read-only callable-map review, and local artifact generation/schema-structure checks. It did not instantiate a Store, factory, planner, Workflow, history, transport or worker, and ran no application test, HTTP request, configured model, native job or scientific investigation. JSON schemas here are proposed documentation; no application schema was changed. Actual scientific behavior remains unverified until a later adopted implementation and its distinct demonstration.

The real parent's proposed subject, algorithm, database, parameters, candidate, versions and constraints are intentionally not chosen here. Existing bound003 caller objects can be used only after the caller explicitly supplies the new factory/definition for a new run; this plan does not claim they have been adopted or configured. The only outstanding decision requested from root is adoption or correction of this exact design before004 coding.
