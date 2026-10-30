# Proposed boundaries, not an implementation authorization

The immutable goal and its entire DESIGN PRINCIPLES block were reread after the source examination and before these conclusions. The source inventory is evidence, not a replacement goal. No production, test, design or permanent instruction file was changed. Existing literature roles and the local example are inventoried because they are model callers; this proposal does not implement literature graders or add their work to the tool-grader goal.

The governing requirements are:

> JSON is structured storage and an intermediate representation, not the complete model prompt.

> TASK contains detailed recurring instructions describing the actual assignment, objects, choices and constraints.

> STEERING contains concise decision-relevant facts and tables from received information and the episode’s own prior work.

> Do not shorten TASK merely to make STEERING concise.

The three construction slots remain exactly `evidence_axis`, `thought_pattern`, `child_tool_info`. No scoring sheet, deterministic function or annotation-credit formula is redesigned. Parent-to-child information contains the assigned task and necessary supplied facts; never parent yield history or private reasoning. The child tracks its own assignment. Monitoring uses resource-type instructions and actual operation/status/extractor information, not per-tool LLM judgment prompts. Internal lookups before action completion create neither completed turns nor credit.

## Observed implementation

`providers.ModelConnection` owns one `_SessionConnection` per episode/provider role; both the root caller and durable child worker instantiate it. Its native app-server `thread/start` uses fixed base/developer instructions, and each `turn/start` receives `input[0].text` plus a separate output schema. FAST is a model allocation, not an episode role. The current provider API does not receive the actual episode role explicitly.

`_SessionConnection._presentation` recognizes only a `scientific_process.evidence_axis.instruction_status == published_investigation_instructions` state. It reconstructs that state and calls `render_scientific_process_prompt`. Every other input is `json.dumps(context, allow_nan=False)`. A delta for those other roles is sent as delta JSON, and an internal lookup is sent as lookup JSON; neither supplies a rebuilt detailed task.

The source has 19 main Workflow role names and 25 role/binding instruction contracts, plus two FAST retrieval contracts and four roles in the separate local example. The 31 detailed rows are in `TEMPLATE_INVENTORY.json`; all are indexed in `BOUNDARY_TABLE.md`. Different binding generations are counted separately; delegation to an identical producer is not. The five frame shapes, sixteen same-decision lookup/feedback shapes, and four communication projections are also named separately. Those shapes are not new episodes or 25 independent scientific workflows.

`DecisionSource.next` collects the assignment, own state, admitted direct-child forms, tool contracts, controller state and optional timing/resource inputs. `DecisionSource.call` adds the frozen selected launch sections, allowed child information and binding-supplied initial context. `exchange_decision` supplies category yields and frozen full/restored state, servicing lookups before any action is selected. `model_snapshot` already strips raw controller score history and raw waiting histories. The machinery is reusable; it is not currently a universal text renderer.

`Workflow.selected` validates the explicit parent commission, narrows scope, compiles the original typed form, prepares its assignment and calls `build`. `commission_child` retains that original request for independent execution. `EpisodeGoal.child` preserves root `task_context` as a host fact. A renderer should select only root-context information necessary for the assigned child; it must not copy the parent's entire task just because that lineage record exists.

There is another origin distinction: `EpisodeReceipts.bind` freezes the parent's receipt prefix, and `selection` walks those inherited prefixes plus the child's own receipts. `Workflow.working_state` passes that selection to `Store.reasoning_view` only when the chosen scientific projector requires receipt projection; otherwise it supplies scoped Store records without a receipt filter. Thus `working_state` cannot universally be labeled "new information this child obtained" or "only explicit assignment facts." A renderer must distinguish supplied/inherited material from own contributions and select what the child's task needs. This inventory does not change the baseline, record access or credit formula to solve a presentation problem.

`DecisionSource.finish` and `form_with_facts` combine the child's last admitted interpretation with recorded facts, followed by the original report validation/admission. `receive_form` records what the receiving parent actually got, and `EpisodeView.model_inputs` exposes only admitted direct-child reports. This is not another model prompt/composer boundary. The parent's unchanged TASK and relevant returned facts should meet only in that parent's next text rendering.

The modern results path is worth distinguishing precisely: `ExecutionEpisodes.decision_context` supplies `execution_assignment`, `execution_progress`, `execution_target`, `execution_target_description` and optional `own_bvbrc_values`. It does **not** call `APIServiceExecution.decision_context` for the results role. That API callback is used for `launch_api`. A renderer expecting the launch API fields on results would silently miss actual data.

Two instruction-level issues require template review in addition to replacing JSON: the generic annotation prose offers an ordinary tool even when `restricted_root` removes those actions, and `MonitorEpisodes`/legacy `ResourceEpisodes` append to base scientific prose instead of replacing it. The inventory does not remove actions, alter ownership or fix this by inventing a scheduler.

## Common interface proposed for discussion

Each row names a pure function of the form:

```python
render_<row>(
    state: Mapping[str, object],
    instructions: str,
    *,
    lookup_results: Sequence[Mapping[str, object]] = (),
) -> str
```

The function builds detailed TASK and selected STEERING independently, then concatenates their rendered text. It reads no Store, network, native output, model or estimator. Typed scientific records, sheets, calculators, numerical observations and response schemas remain outside it. It can mechanically present values already supplied; it cannot decide what biological result is true or fit a new estimate.

A host-only dispatch identity is needed. A possible exact interface is:

```python
PromptBoundaryV1(template_id: str, episode_role: str, binding_id: str)
RenderedPrompt(task_text: str, steering_text: str, model_text: str)

present_request(
    boundary: PromptBoundaryV1,
    instructions: str,
    context: Mapping[str, object],
    previous_state: Mapping[str, object] | None,
) -> tuple[RenderedPrompt, Mapping[str, object] | None]
```

This is a proposed host presentation contract, not a fourth construction slot, episode type or new model field. `DecisionSource.path[-1][0]` and the actual bound specialist identify it; FAST retrieval and the separate example name their own contract. It must be recorded alongside the saved request for replay, not guessed from arbitrary payload keys or a provider `role` argument that only says FAST/REASONING. How the provider accepts that extra host metadata is owned by the dispatcher workload and must include existing injected-provider callers in verification. No model schema or saved observation is silently rewritten.

The host reducer applies `apply_state_frame` for every known template, not only the published-science branch. It retains one current authoritative state per episode/provider-role, obtains current lookup replies separately, and feeds the whole reconstructed task to the selected renderer on bootstrap, delta, lookup and restoration. It does not create a new history or execute a lookup automatically. Native compaction invalidates incremental transport state as now; reconstruction uses the frozen original snapshot and answered public exchanges. Selected pixels retain the existing attach-on-supplying-frame rule and are not repeatedly attached on lookups.

The native conversation's developer instructions stay stable for its lifetime. Frame-protocol prose must be normalized for text presentation across supported templates, as `text_instructions` currently does only for published science. The complete detailed task goes into each actual model input; native thread history is not its sole copy.

## Nonoverlapping implementation ownership

These workloads can be independent only after their concrete templates receive the user's running feedback. They are proposed file ownership, not a request to start editing while the root freeze is active.

| Workload | Exclusive proposed files | Input contract and exact dependencies | Output/verification handoff |
| --- | --- | --- | --- |
| Host dispatch and durable presentation | `providers.py`, `runtime.py` prompt-dispatch additions only, `scientific_tool_retrieval.py` dispatch metadata only, `local_example/workflow.py` dispatch metadata only; new `prompt_exchange.py` | Original saved instructions/context/output schema; `PromptBoundaryV1`; `apply_state_frame`; `conversation_key`; `decision_exchanges.restoration.snapshot` and public replies | Actual `turn/start` text for every registered semantic row; fixed developer instructions; same output schema; restoration and pixels tests. Owns central routing edits so no renderer worker touches them. |
| Mechanical text and own-history projection | new `prompt_text.py`, `prompt_lookup.py`; tests for these only | Exact own `action_yields.rows`, controller band fields, lookup replies, closed schema fields and pagination; no estimator refit | Schema-to-table and value-to-table mechanics; each lookup's semantics remain explicit. Return pure text. Supplies shared mechanics, never generic task wording. |
| Root annotation and legacy scoped improvement | new `annotation_prompt.py`, `improvement_prompt.py` | `goal.objective/scope`, actual `action_schema` alternatives, current received scientific records, `requested_form`, `annotation_score` distinct from `current_credit` | Separate direct tasks and current facts. Verify restricted root does not claim ordinary execution capabilities and children receive no root history. |
| Published/scientific compatibility task | existing `scientific_process_prompt.py`; new `scientific_legacy_prompt.py`; matching prompt tests | `scientific_process` selected axis/thought/tool bodies, current selector versions, assignment fields, original return schema and exact option pins | Preserve published full task and current formulas; add explicit legacy presentation without changing stored selection meaning. Evidence-axis sheets stay separate. |
| Execution-approach selection | new `launch_prompt.py` | `execution_launch_assignment_v1.requests/immutable_input_versions/constraints`; `execution_resource_capabilities/initial_information`; original handoff returns | Concrete permitted requests, duration support, actual attempts and returned handoffs. Does not select a resource for the episode. |
| API execution | new `api_execution_prompt.py` | `api_service_assignment_v1` or legacy API assignment; `api_request`, `api_received_progress`; exact actual catalog; legacy prepared/job/completion fields | Generic service task with actual operation information; preparation/submission/immediate response/async job remain distinct. No per-tool judge. |
| Local and HPC practical execution | new `practical_execution_prompt.py` | `ASSIGNMENT_SCHEMA`, `practical_working_context/progress/completion/current_inventory`; local versus HPC `operation_catalog` | Two role-specific tasks sharing mechanics; retain selected resource/workspace/account/allocation and explicit retry identity. Do not alter exact-zero practical completion. |
| Recursive monitoring | new `monitor_prompt.py` | `_ASSIGNMENT`, target description including `selected_observation_schema`, actual delivered progress/log snapshots and direct dependencies | Resource-type monitoring task with actual operation/extractor information; concise measured status/timing/changed facts. No liveness-to-productivity inference or polling itinerary. |
| Results acquisition | new `results_prompt.py` | `execution_results_assignment_v1.selector/handoff_ref`; actual `execution_target_description/progress`; partial result and requirement facts; native/API/HMMER catalog | Artifact/format/requirement/native-score acquisition task; preserve selected numerical projection and typed returns. No scientific acceptance judgment or formula edits. |
| Typed child-return presentation | new `received_form_prompt.py`; existing `alignment_result_presentation.py` only if this work owns its changes | Admitted form plus original parent schema/purpose; selected numerical values/units/populations/requirements; actual callable IDs separately | Small receiver-specific tables without parsing sheets or composing reports. Preserve exact numeric values and meaningful associations; never change parent TASK. |
| FAST tool-information selection | new `tool_retrieval_prompt.py` | `investigation`, actual available catalog, v1/v2 selection schema | Two exact selection contracts; no parent history, resource choice, invented tool metadata or new action credit. |
| Existing compatibility contexts | new `resource_adapter_prompt.py`, `homology_job_prompt.py`; no changes to scientific operations | Exact legacy assignments/handoffs and job schemas listed per row | Source-present compatibility templates; no claim of current resource deployment. |
| Existing literature and local example inventory | no tool-grader production implementation assigned | Seven existing literature assignments and four example contexts in inventory | Root may separately scope their rendering if necessary for universal presentation. No literature grader, new episode or adoption of example scheduling behavior. |

The only common prerequisites for an individual renderer are its explicitly listed state fields, shared mechanical helper signatures and dispatcher registration contract. A missing native format or live resource blocks that operation's verified data, not all prompt families. A renderer can be reviewed and tested against retained records without claiming live execution.

## Identifier treatment

Tracking IDs must stay outside the prompt, but current schemas also require exact opaque operands. These are not interchangeable cases:

* A `target_handle` is needed for selected monitor/wait work; an internal commission hash or native process PID generally is not.
* A `source_ref`, `support_receipt_ref`, `handoff_ref`, source byte window or native object locator can be a real operation operand. Keep its exact callable meaning where needed. Do not turn it into a narrative label that can no longer be supplied to the operation.
* `scientific_process_option_ref_v1.library_id/entry_sha256`, selected launch instruction pins and `revision_origin` currently must be copied into selected child assignments. A blanket hash filter would break the unchanged contracts. Either show them once in an explicitly identified exact-operand table or later define a separate authorized host mapping; this plan does not silently change the response schema.
* `goal_id`, episode/run IDs, frame revisions, controller epoch/fit diagnostics, transport configuration and unselected custody hashes do not guide the scientific decision and remain host-only.
* Existing alignment return labels are a presentation projection of already admitted numerical facts. They do not prove that all returned identifiers can be removed for all receivers; an exact reference needed for a next operation remains an operand.

## Verification actually performed and proposed

`inspect_boundaries.py` made 24 controlled calls through the real `_SessionConnection.complete` and captured native `turn/start` dispatch. It used nine original saved full contexts from the closed MSA run and fifteen explicitly synthetic bootstrap/update/lookup envelopes around those exact retained states. It used no inference, network, native execution, Workflow/controller run or active Store. All five role fixtures exercised the real provider branch. Published scientific calls rendered text; annotation, launch, launch_api and results exactly matched JSON serialization. 308 production/method_loop source files and fourteen original closed-run files hashed unchanged. These are observations of the current gap, not passing implementation tests.

The original retained run is `verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/runs/msa_dna-_7cous9_`. Its provenance says retained native byte examples, controlled loopback HTTP and scripted decisions; no new native scientific execution, live BV-BRC or configured model. `RUN_TERMINAL_023.json` records Workflow closure and a source-addition guard error before four final pytest assertions ran. Do not call the entire original pytest run passing. Later recorded-prompt checks are separate evidence, not native provider dispatch for all roles.

Existing `tests/test_published_axis_workflow.py::test_actual_workflow_lookup_inspection_typed_return_and_text_reconstruction` provides stronger narrow evidence: it replays actual published scientific child `decision_bootstrap`, `decision_update` and `decision_lookup_result` calls through `CapturedTransport`, then reconstructs a fresh bootstrap with restored public lookups. It does not establish annotation, launch, API, results, monitoring or FAST rendering. `test_decision_provider_frames.py` currently asserts JSON for generic frames; those assertions encode current behavior and will need an explicitly scoped prospective update, not reinterpretation as compliance.

For each semantic row, future verification must cross the real provider dispatch and compare the actual text, not just call a renderer in isolation. Verify initial/delta/lookup/restoration, one appropriate admitted child result, an actionable failure/partial state, exact numeric values/units/missing states, unchanged typed output schema, callable references and no tracking leakage. Run full Workflow ownership→selected native artifact→typed report tests separately. Native inference and live resource claims require their own evidence; transport fixtures establish neither.

No currently running tests were stopped. No scientific metrics, controllers, scoring sheets, tool parsers or resource behavior changed. All proposed templates remain subject to source-specific user review; no template is declared settled merely because its data contract is named.
