# A108 source_evidence_examination (role `literature_page`)

Source: `git show HEAD:gene_annotation_episode/episodic_workflow/root/a108/sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/<file>` at 97308b94c. Only this folder's own files plus its `grading/` and `scoring/` were read. Child folders were not read for intent. They were diffed against this folder only to record the differences.

Binding class `LiteratureEpisode`. `binding_path = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'`, `commissioning_parent = '.../source_relevance_assessment'`, `roles = ('literature_page',)`, `entry_roles = ()`, `decision_source_type = LiteratureTask`, `decision_prompt_renderer = render_literature_experimental_prompt`. Binding record version `literature_episode_binding_v1`.

## What this episode is for (its goal, in its own words)

- Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_page']`): "Investigate where and how this exact source should be examined. Choose ordinary source operations or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings, tables and footnotes; retained original bytes remain addressable."
- Module doc (`source_contracts.py`): the binding supplies operands, the ordinary operations that are available, source custody, and the commissioned task's private yield binding. "A reading selection is information for an investigation, never a script that this binding executes."
- Episode binding doc: "Private A108 organism and sample context episode binding."
- `LiteratureGoal.instructions` = role instruction + `A108_CONTEXT_TASK` + `A108_READING_TASK` (both from the old shared `a108.library.literature_a108_prompt`, which was not read).
- `LiteratureGoal.planning_context` (shown as `literature_goal_plan` when the assignment carries `literature_task`) = `{objective: request.goal, proposed_annotation_ref, commissioned_result: task, progress_definition: credit_projector(context).as_record(), planning_question: instructions(context)}`.

In short, it examines one assigned source (one page or artifact) for A108 organism/sample-context evidence about a proposed annotation. It answers exactly one commissioned task: verified source leads, an assessment answer, or a screening answer.

## Task and instructions

- `task.py` `LiteratureTask(LiteratureTaskState, LiteratureTaskDecision)` is the old iterative decision source. It contains replay, completion slots, model call journal rows, apply_response and execute. Almost all of it is old-runner machinery. Its own intent:
  - A reason selection whose commit is entirely empty is rejected (`empty_reasoning_commit`). Two cases are exempt: `evidence_processing.kind == 'no_applicable_evidence'`, and a binding whose `reasoning_has_task_content` accepts the selection (a `source_lead`).
  - A reason action runs the binding's `execute_reasoning` (the grading-coupled path) before it falls back to `store.commit_reasoning`.
  - An action that executes but returns invalid or failed still enters the iterator, with its credit taken from `source_credit_view` (AGENTS rule).
  - On a model-call failure the episode records the failure with `record_source_failure` and ends with `SourceEnd('source_failed')`.
  - A delivery resolution (`pending_child_delivery`) must keep `report_update` equal to the current interpretation.
  - Contract-error feedback carries repair text: "closed_top_level_form_required" and "component_native_return_channels_required".
  - Finish without a report contract returns `{credit, pending_handles, **current_report_facts}`. With a report contract it returns `form_with_facts(report_values, schema, facts)`.
- `task_instructions.py` composes the instructions. It takes the base `runtime_prompt.INSTRUCTIONS`, then adds or replaces with the specialist instructions (above), then `REASONING_COMMIT_REQUIREMENT` if reason is permitted, then tool-knowledge and launch-instruction text. It then appends the fixed text for pending_child_delivery/redeliver_report ("Complete that existing acquisition by selecting redeliver_report with a corrected form ... this repair does not select new scientific work"). Under the decision-exchange protocol it replaces the history guidance ("Use request_context exchanges ... Read exact previously received outcomes with the ordinary episode.history tool, view=records ...").

## What it reads from its parent's assignment (`from_parent.py`)

Assignment schema is `_PAGE` (`version: page_assignment_v1`, `source_ref`, `representation` ∈ text/original/stdout/stderr, `artifact_ref`, `question_context_refs[]`, `prior_delivery_refs[]`), plus:
- `literature_task` (goal.task_schema, anyOf):
  - `{kind: verified_source_leads}`
  - `{kind: source_answer, answer_kind: assessment, source_refs[]}`
  - `{kind: source_answer, answer_kind: screening, examined[{source_ref, artifact_ref, start, end}]}`
  - Each takes `version: literature_local_task_v1`, `evidence_axis: A108`, `credit_unit > 0` and an optional `yield_settings{kind, cutoff>=0, uncertainty_alpha∈(0,1)}`.
- `proposed_annotation_ref` (REF).
- The A108 grading requested components and the aggregation requested components (enum from the grading/aggregation storage COMPONENTS).
- Under `private_yield_binding`, `literature_task` and `proposed_annotation_ref` are required and `credit_unit` is removed from the required list. `prepare_assignment` then fills `credit_unit` and `yield_settings` from the owner's `_yield_bindings[task_key]`, and rejects a supplied value that disagrees.
- Validation:
  - the source must be in scope, and `artifact_ref` must equal the source's artifact for that representation;
  - every question-context and prior-delivery ref must be in scope;
  - the child's `proposed_annotation_ref` must equal the parent's;
  - the commissioned task must match the original request: `literature_original_task_credit_required`, `literature_task_original_commission_mismatch` (the request goal, the report_contract, and `message.episode_assignment == assignment`), `literature_task_typed_return_mismatch` (the return schema must carry the x-source for LEADS, `changed_assessment_refs` or SCREENING), `literature_task_return_components_mismatch`, `literature_task_outside_assigned_source`, `literature_task_screening_artifact_mismatch`, and screening spans with end > start.

## Children it may commission

`_CHILDREN['literature_page'] = ('literature_table', 'literature_ordered', 'literature_targeted')`. The preparers and receivers are wired in `episode.py`:

| Child role | Folder | to_child (sends) | from_child (takes back) |
|---|---|---|---|
| literature_table | table_evidence_extraction | `prepare_request`: the child scope (validated within the parent scope); the expanded contract form for this role; a check that every required return source appears exactly once; the parsed initial report validated against the interpretation schema; a check that the role is in the allowed children; launch instructions materialized; `episode_assignment = child binding.prepare_assignment(...)` with op key `run:episode:index` | `receive_report`: the recorded admission references (receipts path), else the progress_provider receive_form, then the references in the admitted form plus the binding's `received_form_references` (A108 grading/aggregation cells and current sheet refs), received as `child_form` or `report_redelivery` |
| literature_ordered | source_coverage_improvement | the same, with role `literature_ordered` | the same |
| literature_targeted | passage_evidence_extraction | the same, with role `literature_targeted` | the same |

The three to_child files are identical apart from the role string, and so are the three from_child files. The assignment the child receives is the child's own `reading_assignment_v1{page, selection}` (see the child intent files). The child validates its `page.source_ref` to be within this parent's assigned `source_ref`.

## Decision state and what it shows the model

Base context (`decision_inputs.build_decision_inputs`) contains:
- goal, scope, working_state, visible_record_refs;
- current_credit and current_evidence_vector (from source_credit_view), investigation_progress when there is a receipt projection, credit_binding;
- time_accounting (journal elapsed view; old runner, and a time view);
- pending_work, last_local_outcome, feedback;
- visual_evidence (the visual_inputs of the latest completed image.view);
- report_deliveries, controller and controller_binding;
- tools (catalog), tool_knowledge, job_episode_options, available_report_facts;
- requested_report_purpose, requested_form, current_report_update, current_report_basis_refs, report_lifecycle;
- the annotation context when the source is scientific, and monitoring_information_credit when present;
- `_completed_work_axis_results` (sheet results for prepare_completed_work).

`task_decision.call` adds:
- resource_context, shared_information_context, launch_instruction_library, selected_launch_instructions;
- child_options;
- the binding's initial_decision_context (empty for this role; it only applies to the root annotation role with reference_parent_sources);
- completed_action_reports (unless literature_completed_work is present);
- execution_expectations, resource_tool_estimates, native_execution_expectations;
- contract_information_profile;
- restored_episode_history;
- under the exchange protocol, the yield table (`decision_yield_table`) and the model snapshot.

Binding `decision_context` (`internal_summary.py`) adds:
- `literature_assignment` (the validated page);
- `literature_source_custody` (version, artifact_ref, text_ref, stdout_ref, stderr_ref, parent_source_refs);
- `own_literature_outcomes`: own outcome metadata for the acquisition and read tools, page size `outcome_page_size`, default 8;
- `literature_history_meaning`: "Own outcome metadata only. ... Source delivery does not establish understanding, absence or resolved science.";
- `literature_examined_source_inputs`;
- `literature_experimental_work = {version: literature_experimental_task_v1, aspect: source_experimental_evidence, evidence_axis: A108}`;
- `literature_received_fact_display`: received reference, term, context, observation, hypothesis and assessment records plus source metadata;
- `literature_owned_population_sources`: own successful population/sheet outputs classified from metadata only, with no cell contents;
- `literature_selected_population_attempt`: the latest own tool action, when it was invalid, failed or error;
- `literature_completed_work` and `literature_current_scoring_sheets` (current_report_facts);
- `literature_goal_plan` (planning_context).

## Tools it offers (`source_operations.py`)

- Permitted common actions: `tool`, `reason`, `child`, `redeliver_report`. There is no wait (`waiting.supports_wait = False`).
- Catalog:
  - The `_A108_ACCESS_TOOLS` that the services catalog provides: state.query, source.read, source.locate, source.sequence.references, image.view, source.archive.members, source.archive.extract, source.xlsx.sheets, source.xlsx.rows, source.pdf.info, source.pdf.text, source.pdf.page, material.annotations, material.parse, material.from_source, execution.estimate.
  - `execution.estimate` is narrowed to its source.xlsx.sheets/rows branches, and dropped if none exist.
  - The population catalog entries (`literature_population_catalog`; executed as `literature.a108_grading.populate` and `literature.a108.aggregate`), with `argument_transport` when a contract-information profile is set.
  - All input schemas are wrapped by `source_location_inputs`.
  - The `public.ncbi.search` database-enum override is dead code here, because public.* acquisition tools are not in the allowed set. `_A108_ACQUISITION_TOOLS` is only used to filter own_outcomes.
- Execution guards:
  - every source_ref, including archive members and the refs nested in population arguments, must lie within the assigned page source (through `parent_source_refs`); otherwise `literature_reading_outside_assigned_source`;
  - source reads are authorized through both the grading and the aggregation repository;
  - `state.query` records are authorized afterwards, before they are returned;
  - text witnesses are materialized for population calls;
  - errors come back as `status: invalid` outcomes with feedback.
- Reasoning (`grading/contextual_interpretation.py`, the coupled A108 grading rule from AGENTS):
  - The reason action schema is the required-grading `action_schema` over the grading repository's population schema. For a `verified_source_leads` task it also takes `source_lead` (lead_schema: proposed_annotation_ref, source_ref, subject_ref, disposition relevant/not_relevant, relevance_rationale, witness).
  - `execute_reasoning` reads the witness span through `source.read`, then in one transaction runs `commit_reasoning` or the required grading `execute`, then `validate_lead`.
  - `validate_lead` checks:
    - the lead is in the original search task;
    - the question and source match;
    - the rationale is not empty;
    - the inputs were received;
    - the subject is anchored in the source;
    - the source is not a search page;
    - the subject anchor lies inside the witness.
  - The grading provider must be `literature.a108.context_grading` (`a108_context_grading_required`).
- `scientific_records`: automatic score judgments are empty, and completing one raises `a108_automatic_judgment_unavailable`.

## How its credit is counted (`credit.py`)

- `credit_kind = 'scientific'`. `credit_view` delegates to `services.scientific_credit_for(self._scientific_credit_invocation, ...)` or `services.scientific_credit`. The invocation passes the original assignment (goal, scope, purpose, schema, initial_report, proposed_annotation_ref) to the workflow's scientific projector `projection_view`, with receipt arguments.
- `credit_projector = LiteratureTaskCredit`. Its policy record is `{kind: literature_local_task_v1, task: A108:<kind>[:<answer_kind>], credit_unit, unit: one_verified_source_for_original_question | one_answer_to_original_commission, revision_credit: False, activity_credit: False, annotation_support: separate}`.
- Credit = `credit_unit × len(items)`, and it must be finite. It is not bounded.
  - Items for verified_source_leads: lead dispositions with `disposition == 'relevant'`, deduplicated per canonical source identity (FindingIdentity). They come from own reason results (`runtime_actions.result.literature_source_lead`) merged in decision order with admitted child forms (`runtime_report_attempts` whose contract x-source is LEADS). Child logs are never read.
  - Items for screening: one answer when own `no_applicable_evidence` reason results with a reason fully cover every requested `examined` span (an interval union per source/artifact). Otherwise none.
  - Items for assessment: the first current retained, target-eligible assessment of `proposed` whose observation lies in `task.source_refs` and has an anchor or visual_anchor. That gives at most one item.
- Guards: `literature_task_credit_commission_mismatch` (run, episode, scope, goal, purpose, schema, initial report, proposed), the annotation must be in scope, and the hypothesis must root in the scope subject_refs (`literature_task_requires_target_annotation`). `task_status` is answered / unanswered / unresolved_contract. The record also carries `source_contributions` and `commission_ref`.

## Continuation (`yield_estimator.py`)

- The continuation task key is `A108:verified_source_leads`, `A108:source_answer:assessment` or `A108:source_answer:screening`.
- Owner declarations, `yield_bindings[key] = {credit_unit, kind, cutoff, uncertainty_alpha}` (exact key set), validated before work.
- verified_source_leads → kind `accumulation`, an old `YieldController(epoch, initial_credit, cutoff, YieldParameters(uncertainty_alpha))`. In the new layout this is the **accumulation** estimator.
- source_answer (assessment/screening) → kind `remaining_commissioned_credit`: `_FiniteLiteratureYieldController` with `maximum_credit = credit_unit`, estimated through `_RemainingCommissionedCredit`:
  - remaining = credit_unit − (initial + Σ history);
  - exact zero once all requested answers are earned;
  - otherwise `estimate_score_yield`, with the next-gain band limited to the remaining amount.
  - In the new layout this is **completion with a target** (target = credit_unit). The limit applies to the forecast, not to credit.
- Settings: `cutoff` ("stops when its available next-credit upper estimate is at or below this cutoff, measured in this task credit unit") and `uncertainty_alpha`. Without `private_yield_binding`, `yield_controller` returns None, which means the runner default.

## What it reports to its parent (`to_parent.py`)

- Fact sources:
  - `literature_a108_grading_cells` and `literature_a108_aggregation_cells` (arrays with RETURN_MEANINGS and report schemas);
  - `literature_screening_answers` (screening_schema: proposed_annotation_ref, disposition const no_applicable_evidence, examined spans, annotation_support const not_assessed);
  - `literature_source_lead_dispositions` (lead_return_schema).
- Facts:
  - the A108 cells for committed and current sheet refs, from tool-origin sources with the matching provider and record version, restricted to the requested components;
  - `literature_completed_work` and `literature_current_scoring_sheets`;
  - screening answers when the task is screening, and lead dispositions when it is leads.
- Validation of the received report: LEADS and SCREENING arrays must equal the saved work exactly (`literature_task_answer_differs_from_saved`). Cell arrays must be exactly the requested subset of the available sheets (`a108_requested_subset_mismatch`, `unrequested_a108_component`, `a108_context_receiver_mismatch`).
- `received_evidence.py`: when receiving from a non-literature role (`role not in ROLES`) it supplies the cell arrays, including empty requested arrays ("Empty means no received cells ... does not infer a biological absence"). It also takes received form references, adds received-evidence tokens, and validates the received report. A literature role (this one) receives nothing through this path.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| __init__.py | 1 | none | none |
| binding_record.py | 16 | binding record: outcome_page_size, private_yield_binding+yield_bindings, reference_parent_sources, contract_information_profile, binding_id | none (source_contracts VERSION) |
| configuration.py | 31 | constructor options and their validation; `reference_evidence` classmethod | composition_information CONTRACT_INFORMATION_PROFILE (via source_contracts) |
| credit.py | 221 | LiteratureTaskCredit counting, lead schema/validation/dispositions, screening answers, assessment answer, credit_view/credit_kind | BindingContext.{as_record,episode_id,path,received_record_refs,request,role,run_id,scope}; communication.plain; domain; numerical YieldController/YieldEstimate/YieldParameters/estimate_score_yield/NumericBand/STATUS_NORMAL (duplicated header, unused here); library.literature_assay_inputs; finding_validity; scientific_findings.FindingIdentity; SQL tables runtime_actions, runtime_report_attempts; services.{scientific_credit_for,scientific_credit,proposed_annotation_for,annotation_task_required,workflow}; workflow.{scientific_projector_for_context,projector_receipt_arguments,projection_view} |
| decision_inputs.py | 36 | which context keys the model sees (see above) | runtime FACT_MEANINGS/FACT_SOURCES/Mapping/_plain/_references_in/json; runtime_actions SQL; self.workflow.{store,working_state,journal,run_id,local_outcome_preview,source_credit_view,receipt_projection,source_credit_binding,pending_work,delivery_status,controller_binding,catalog,knowledge,job_episode_options,extra_report_sources,is_scientific_source,annotation_context,specialist,binding_context,tools,action_schema,delivery_resolution_inputs}; journal.elapsed_view (time accounting) |
| decision_presentation.py | 21 | completed_action_reports unless literature_completed_work; yield table rows | runtime _category_yield_parameters/yield_table/Mapping; episode_work_report.completed_action_reports; self.workflow.controller_binding |
| episode.py | 74 | binding class composition, role guard, child roles, preparer/receiver wiring, contract information profile, context_hook_applies | BindingContext.{role,path}; library.literature_experimental_prompt |
| from_child_passage_evidence_extraction.py | 19 | receive child form references | runtime._references_in; episode_return_records; workflow.{receipts,is_job_source,store,run_id,binding_context,progress_provider,episode_bindings} |
| from_child_source_coverage_improvement.py | 19 | same | same |
| from_child_table_evidence_extraction.py | 19 | same | same |
| from_parent.py | 71 | page assignment schema, task, requested components, yield-binding fill, page validation, same proposed annotation | BindingContext.assignment; services.proposed_annotation_for; library.literature_a108_grading_storage / _aggregation_storage |
| goal.py | 104 | task schema, commissioned_task validation, task key, yield kind, instructions, planning_context | BindingContext.{assignment,request,role}; communication.plain; domain; numerical (duplicated header); library.literature_a108_prompt |
| internal_summary.py | 106 | decision_context, initial_decision_context (root annotation only), owned population sources, latest failed attempt, received fact display | BindingContext.*; services.{own_outcomes,workflow}; workflow.{store,run_id}; SQL runtime_actions and population metadata tables; library.literature_source_inputs/_task_families/_work_report |
| received_evidence.py | 90 | received cells/arrays, tokens, report validation against saved work | BindingContext.*; services.{record_selection,workflow}; library.literature_sheet_updates; method_loop.durable.content_digest; domain.canonical |
| scientific_records.py | 16 | population routes; no automatic judgments | library grading/aggregation storage |
| source_contracts.py | 37 | role list, page/window/table schemas, children, A108 tool sets, role instructions, required grading provider | communication; composition_information; domain; episode_bindings.reference_in_context; library.literature_population_catalog, literature_required_grading |
| source_operations.py | 110 | permitted actions, catalog, execution guards, materialization | BindingContext.*; services.{tool_catalog,execute_tool,read_record}; composition_information.CONTRACT_ARGUMENT_TRANSPORT; literature_contract_error; library.literature_assay_inputs |
| source_references.py | 35 | in-scope require, artifact for representation, within-source ancestry, resolve | services.{reference_in_scope,read_record}; episode_bindings.reference_in_context |
| task.py | 209 | see Task section | runtime (around 25 helpers and exceptions); self.workflow.* (journal, inprocess_replay, execution_binding, completions, selected, completed_unit, next_return, resolve_pending_deliveries, permits_common_action, reasoning_action_schema, store, specialist, binding_context, resolver, validate_report, execute, pending_work, receive_native_outcome, receive_outcome, automatic_score_updates, source_credit_view, retain_shared_grading_results, controller_value, facts, release, pending_handles, episode_bindings, decision_exchanges, run_id); providers.ModelCallError; episode_source_failure; tables runtime_episodes, runtime_actions, runtime_model_calls, runtime_forms |
| task_decision.py | 351 | model call/exchange protocol; literature numerical contract freezing | runtime (around 30 names); providers presentation internals (a108 and root); self.workflow.* (see tsv); receipts decision_input; runtime_model_calls |
| task_instructions.py | 28 | instruction composition and redelivery text | runtime_prompt INSTRUCTIONS/REASONING_COMMIT_REQUIREMENT/DECISION_EXCHANGE_PROTOCOL; library.literature_investigation_prompt; workflow.{specialist,binding_context,permits_common_action,knowledge,launch_instructions,native_event_information,decision_protocol,is_job_source} |
| task_state.py | 108 | initial report values; failed action still enters iterator with credit | runtime Episode/ActionLeaf/EFFECT_VERSION/Record/interpretation_schema/...; self.workflow.{context,grains,execution_handle,execution_backend,archive,store,journal,completions,inprocess_replay,execution_binding,source_credit_view,controller_value,recover_commissions,progress_provider}; episode_source_failure; runtime_actions |
| to_child_passage_evidence_extraction.py | 25 | commission literature_targeted | runtime ContractError/parse_json_object/validate_form/interpretation_schema; workflow.{store,expanded_contract_form,episode_bindings,binding_context,child_initial_report_input,specialist,available_child_roles,annotation_child_roles,services,launch_instructions,run_id} |
| to_child_source_coverage_improvement.py | 25 | commission literature_ordered | same |
| to_child_table_evidence_extraction.py | 25 | commission literature_table | same |
| to_parent.py | 64 | fact sources, facts, current report facts, A108 cells, report validation | BindingContext.*; services.{workflow,read_record}; library literature_sheet_updates/_work_report/_a108_grading_storage/_a108_aggregation_storage/_numerical_contracts |
| waiting.py | 8 | no wait | none |
| yield_estimator.py | 108 | yield-binding validation, remaining-commissioned-credit forecast, controller selection | numerical YieldController/YieldParameters/YieldEstimate/NumericBand/STATUS_NORMAL/estimate_score_yield; BindingContext.role |
| grading/__init__.py | 0 | none | none |
| grading/contextual_interpretation.py | 49 | grading-coupled reasoning schema and execution; source_lead | BindingContext.*; services.workflow.store; literature_contract_error; library.literature_required_grading (via source_contracts) |
| grading/contextual_subscoring.py | 14 | grading repository (LiteratureA108GradingRepository) | library.literature_a108_grading_storage; services.workflow.{store,run_id} |
| scoring/__init__.py | 0 | none | none |
| scoring/contextual_main_sheet.py | 11 | aggregation repository reading grading cells | library.literature_a108_aggregation_storage; services.workflow.{store,run_id} |

The per-file counts are in `runs/carry_over/calls/a108_02.tsv`.

## Differences from its children and similar episodes

- This is the only one of the four with children (table, ordered, targeted) and with `child_request_preparer` and `child_report_receiver`. Its assignment is a bare `page_assignment_v1`. The children take `reading_assignment_v1{page, selection}`.
- In `goal.commissioned_task`, the page is `assignment.get('page', assignment)`: the assignment is itself the page. The children use `get('page', None)`.
- `decision_inputs`, `decision_presentation`, `task_decision`, `task_instructions` and `task_state` are byte-identical in all four episodes. `task.py` differs only in its docstring.
- `credit.py`, `yield_estimator.py`, `to_parent.py`, `received_evidence.py`, `scientific_records.py`, `source_references.py`, `binding_record.py`, `configuration.py` and grading/scoring are identical apart from the package path and role docstrings. All four share the same credit, yield and report intent.
- The A105 sibling has the same tree and pattern; the difference is in the content. Per AGENTS, A108 grades contextual observations under provider `literature.a108.context_grading`, keeps the original observation identities, and allows screening (`no_applicable_evidence`) as the only answer that is not graded. A105 instead grades assay results through their observation-to-assay link. A105 code was not read.
