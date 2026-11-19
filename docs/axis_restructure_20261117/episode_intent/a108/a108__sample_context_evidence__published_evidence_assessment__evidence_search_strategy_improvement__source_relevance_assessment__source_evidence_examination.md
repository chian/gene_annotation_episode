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

## Carried over

Written 19 November 2026 from the working tree. The old files could not be read for this carry-over: the repository has no git history in this environment (`git show 97308b94c:<path>` fails), so the table follows the function list `runs/carry_over/functions/a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination.tsv`, the intent record above and the finished carried-over children and sibling axis heads. Each row: old file | name | kind | new place or machinery reason. A row marked "library candidate" is a private copy that stays in the episode file until the library is carried.

| old file | name | kind | new place / machinery reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py and the binding's own as_record(): the system's declaration replaces it; its values are settings (`cost`, `parameters`, `tool_registry`) or constants of the file that uses them |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | binding_record.py and the binding's own as_record(): the system's declaration replaces it; its values are settings (`cost`, `parameters`, `tool_registry`) or constants of the file that uses them |
| configuration.py | LiteratureConfiguration | machinery | constructor options: `outcome_page_size` is OUTCOME_PAGE_SIZE in messages/internal_summary.py, yield bindings are `settings` in yield_estimator.py, the rest is old-runner configuration |
| configuration.py | LiteratureConfiguration.__init__ | machinery | constructor options: `outcome_page_size` is OUTCOME_PAGE_SIZE in messages/internal_summary.py, yield bindings are `settings` in yield_estimator.py, the rest is old-runner configuration |
| configuration.py | LiteratureConfiguration.reference_evidence | machinery | the root-only reference-parent-sources constructor (not this episode); no part carried |
| credit.py | _resolve | episode function | task.py: resolve_aliases (private copy, library candidate) |
| credit.py | lead_schema | episode function | task.py: lead_schema (private copy, library candidate) |
| credit.py | lead_return_schema | episode function | not carried as a function: the lead disposition array of RETURN_FORM (messages/final_to_parent.py: LEADS, a list field) replaces the schema |
| credit.py | validate_lead | episode function | task.py: validate_lead (re-expressed on custody; private copy, library candidate) |
| credit.py | lead_dispositions | episode function | credit.py: lead_dispositions (library candidate) |
| credit.py | screening_schema | episode function | not carried as a function: the screening array of RETURN_FORM (SCREENING, a list field) replaces the schema |
| credit.py | _current_assessments | episode function | credit.py: current_assessments |
| credit.py | screening_answers | episode function | credit.py: screening_answers (library candidate) |
| credit.py | LiteratureTaskCredit | episode function | credit.py: credit, answers, assessment_answers, credit_binding (the projector re-expressed as credit(summary, records)) |
| credit.py | LiteratureTaskCredit.as_record | episode function | credit.py: credit_binding (projector as_record, README 3d: episode content) |
| credit.py | LiteratureTaskCredit.__call__ | episode function | credit.py: credit and answers; the commission-mismatch comparison is a commission check and is not carried |
| credit.py | LiteratureTaskCredit._answers | episode function | credit.py: answers (and assessment_answers) |
| credit.py | LiteratureCredit | machinery | credit_kind/credit_view/credit_projector wiring of services.scientific_credit: replaced by credit() in credit.py |
| credit.py | LiteratureCredit._scientific_credit_invocation | machinery | services.scientific_credit invocation with receipt arguments: replaced by credit() reading records |
| credit.py | LiteratureCredit.credit_kind | machinery | credit_kind 'scientific': replaced by credit.py credit |
| credit.py | LiteratureCredit.credit_view | machinery | credit_view -> services.scientific_credit: replaced by credit.py credit |
| credit.py | LiteratureCredit.credit_projector | machinery | credit_projector selection: replaced by credit.py credit |
| decision_inputs.py | build_decision_inputs | episode function | task.py: decide (context keys) and messages/internal_summary.py: internal_summary; the old-runner keys (journal time accounting view, pending_work, report_lifecycle, delivery, controller binding) are replaced by ctx.clock, the controller yield table and system recording |
| decision_presentation.py | prepare_completed_work | machinery | completed_action_reports / completed-work preparation for the old report machinery; the `literature_completed_work` fact raises where selected (messages/final_to_parent.py) |
| decision_presentation.py | decision_yield_table | episode function | messages/internal_summary.py: action_yields (yield_table from episode_support/records/progress_views.py) |
| episode.py | LiteratureEpisode | episode function | episode.py: class SourceEvidenceExamination(EpisodeBinding) |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | composition-information profile of the old numerical contract machinery; not carried |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | composition-information profile of the old numerical contract machinery; not carried |
| episode.py | LiteratureEpisode._role | machinery | role guard over BindingContext; the binding path is the identity now |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py: CHILD_SLOTS |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py: CHILD_SLOTS |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | hook for the root annotation role (reference parent sources); not this episode |
| episode.py | LiteratureEpisode.child_request_preparer | episode function | messages/msg_to_child.py: msg_to_child |
| episode.py | LiteratureEpisode.child_report_receiver | episode function | messages/read_from_child.py: read_from_child |
| from_child_passage_evidence_extraction.py | receive_report | episode function | messages/read_from_child.py: read_from_child (slot passage_evidence_extraction); the receipts path and progress_provider receive_form are machinery |
| from_child_source_coverage_improvement.py | receive_report | episode function | messages/read_from_child.py: read_from_child (slot source_coverage_improvement); the receipts path and progress_provider receive_form are machinery |
| from_child_table_evidence_extraction.py | receive_report | episode function | messages/read_from_child.py: read_from_child (slot table_evidence_extraction); the receipts path and progress_provider receive_form are machinery |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM, read_from_parent |
| from_parent.py | LiteratureAssignment.child_assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM (the child form is the child own) |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py: ASSIGNMENT_FORM |
| from_parent.py | LiteratureAssignment._validate_page | machinery | Store scope and artifact checks of the page: commission checks, a wrong commission fails where its records are read |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py: commissioned_task (the checks that need no Store or request) |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py: read_from_parent; the yield-binding fill is yield_estimator.py settings |
| goal.py | _yield_kind | episode function | yield_estimator.py: yield_controller (choice of controller) |
| goal.py | _task_key | episode function | messages/read_from_parent.py: task_key (private copy, library candidate) |
| goal.py | task_schema | episode function | messages/read_from_parent.py: task_schema (private copy, library candidate) |
| goal.py | _return_sources | machinery | return-contract source checks against the request report contract: replaced by RETURN_FORM |
| goal.py | _return_components | machinery | return-contract component checks against the request report contract: replaced by RETURN_FORM |
| goal.py | commissioned_task | episode function | messages/read_from_parent.py: commissioned_task (private copy, library candidate); the report-contract checks are not carried |
| goal.py | continuation_task | episode function | yield_estimator.py: yield_controller (task key from the parent input) |
| goal.py | LiteratureGoal | episode function | goal.py: GOAL, UNIT, RESULT |
| goal.py | LiteratureGoal.instructions | episode function | goal.py: GOAL and task.py: instructions |
| goal.py | LiteratureGoal.planning_context | episode function | messages/internal_summary.py: literature_goal_plan |
| grading/contextual_interpretation.py | ContextualInterpretation | episode function | task.py: reason, reason_schema, reasoning_has_task_content |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_action_schema | episode function | task.py: reason_schema |
| grading/contextual_interpretation.py | ContextualInterpretation.reasoning_has_task_content | episode function | task.py: reasoning_has_task_content |
| grading/contextual_interpretation.py | ContextualInterpretation.execute_reasoning | episode function | task.py: reason (grading coupled in the one tool unit) |
| grading/contextual_subscoring.py | ContextualSubscoring | episode function | task.py: repositories (grading repository over episode_support/literature/storage/literature_grading_storage.py: LiteratureA108GradingRepository, already in library) |
| grading/contextual_subscoring.py | ContextualSubscoring._required_grading_repository | episode function | task.py: repositories (grading repository over episode_support/literature/storage/literature_grading_storage.py: LiteratureA108GradingRepository, already in library) |
| grading/contextual_subscoring.py | ContextualSubscoring._a108_grading_repository | episode function | task.py: repositories (grading repository over episode_support/literature/storage/literature_grading_storage.py: LiteratureA108GradingRepository, already in library) |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py: internal_summary |
| internal_summary.py | LiteratureSummary.initial_decision_context | machinery | root annotation role only (reference parent sources); not this episode |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py: internal_summary |
| internal_summary.py | LiteratureSummary._owned_population_task_sources | episode function | messages/internal_summary.py: population_sheets, literature_owned_population_sources |
| internal_summary.py | LiteratureSummary._population_task_context | episode function | messages/internal_summary.py: literature_selected_population_attempt |
| internal_summary.py | LiteratureSummary._received_fact_display_context | episode function | messages/internal_summary.py: received_fact_display |
| received_evidence.py | LiteratureReceivedEvidence | episode function | messages/read_from_child.py: read_from_child and messages/internal_summary.py (the cells of admitted child returns) |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | report source declaration for the old report machinery; RETURN_FORM declares the fields |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | episode function | messages/read_from_child.py: read_from_child (cells of the requested families) |
| received_evidence.py | LiteratureReceivedEvidence._complete_requested_received_arrays | episode function | messages/read_from_child.py: read_from_child (a field not asked for reads as empty) |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | receipts/form reference collection: custody of record_refs fields replaces it |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | received-evidence tokens of the old receipts bookkeeping |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | episode function | messages/final_to_parent.py: validate_report (answers equal the saved work) |
| scientific_records.py | LiteratureScientificRecords | machinery | old scientific-records hook; its two methods are listed below |
| scientific_records.py | LiteratureScientificRecords._population_routes | episode function | task.py: POPULATION_NAMES and the two population tools (library: literature_population_catalog) |
| scientific_records.py | LiteratureScientificRecords.automatic_score_judgments | machinery | old automatic-judgment hook: empty for A108, nothing to carry |
| scientific_records.py | LiteratureScientificRecords.complete_score_judgment | machinery | old automatic-judgment hook: raised a108_automatic_judgment_unavailable, nothing to carry |
| scoring/contextual_main_sheet.py | ContextualMainSheet | episode function | task.py: repositories (aggregation repository over episode_support/literature/storage/sample_context_evidence/literature_aggregation_storage.py, already in library) |
| scoring/contextual_main_sheet.py | ContextualMainSheet._a108_aggregation_repository | episode function | task.py: repositories (aggregation repository over episode_support/literature/storage/sample_context_evidence/literature_aggregation_storage.py, already in library) |
| source_contracts.py | _a108_population_catalog | episode function | already in library: episode_support/literature/forms/sample_context_evidence/literature_population_catalog.py: population_catalog |
| source_contracts.py | _required_grading_logic | episode function | already in library: episode_support/literature/grading/sample_context_evidence/literature_required_grading.py (action_schema, execute) |
| source_operations.py | LiteratureOperations | episode function | task.py: the access tools, populate tools, run_access_tool, catalog |
| source_operations.py | LiteratureOperations.permitted_common_actions | machinery | permitted actions tool/reason/child/redeliver_report: tools and child slots are declared, redeliver_report is machinery |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py: catalog, offered, selection_schema |
| source_operations.py | LiteratureOperations.execute | episode function | task.py: run_access_tool, populate, reason |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py: admitted, authorize_source, population_sources |
| source_operations.py | LiteratureOperations._materialize_text_arguments | episode function | task.py: populate (library: materialize_text_witness_inputs) |
| source_references.py | LiteratureReferences | episode function | task.py: within_source (the page source ancestry) and library read_record_in_scope |
| source_references.py | LiteratureReferences._require | episode function | task.py: within_source (library read_record_in_scope) |
| source_references.py | LiteratureReferences._artifact | episode function | messages/internal_summary.py: representation_artifact |
| source_references.py | LiteratureReferences._within_source | episode function | task.py: within_source |
| source_references.py | LiteratureReferences.resolve | machinery | reference resolution over the old binding context; held records are read through custody |
| task.py | LiteratureTask | machinery | old decision source (replay, completion slots, model-call journal rows, apply_response, execute): replaced by task.py decide/action/tools and the system loop; its own intent (empty-commit rejection, grading-coupled reason, a returned invalid outcome entering the iterator) is carried in task.py: action, reason, empty_commit |
| task.py | LiteratureTask.next | machinery | old decision source (replay, completion slots, model-call journal rows, apply_response, execute): replaced by task.py decide/action/tools and the system loop; its own intent (empty-commit rejection, grading-coupled reason, a returned invalid outcome entering the iterator) is carried in task.py: action, reason, empty_commit |
| task.py | LiteratureTask.apply_response | machinery | old decision source (replay, completion slots, model-call journal rows, apply_response, execute): replaced by task.py decide/action/tools and the system loop; its own intent (empty-commit rejection, grading-coupled reason, a returned invalid outcome entering the iterator) is carried in task.py: action, reason, empty_commit |
| task.py | LiteratureTask.execute | machinery | old decision source (replay, completion slots, model-call journal rows, apply_response, execute): replaced by task.py decide/action/tools and the system loop; its own intent (empty-commit rejection, grading-coupled reason, a returned invalid outcome entering the iterator) is carried in task.py: action, reason, empty_commit |
| task.py | LiteratureTask.finish | machinery | old decision source (replay, completion slots, model-call journal rows, apply_response, execute): replaced by task.py decide/action/tools and the system loop; its own intent (empty-commit rejection, grading-coupled reason, a returned invalid outcome entering the iterator) is carried in task.py: action, reason, empty_commit |
| task_decision.py | LiteratureTaskDecision | episode function | task.py: decide and action (the class itself is the old decision machine) |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py: decide (ModelRequest) and action; the journal rows and snapshot are machinery |
| task_decision.py | LiteratureTaskDecision.instructions | episode function | task.py: instructions |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | completion slots of the old decision journal |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | provider conversation key of the old model-call journal |
| task_decision.py | LiteratureTaskDecision.interpretation_context | episode function | task.py: decide (context) |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop (exchange_decision) |
| task_instructions.py | instructions | episode function | task.py: instructions (the pending-delivery, redeliver_report and exchange paragraphs are not carried: those actions do not exist) |
| task_state.py | LiteratureTaskState | machinery | old task state container (replay, completion slots, checkpoint); the summary is internal_summary(view) |
| task_state.py | LiteratureTaskState.__init__ | machinery | old task state container (replay, completion slots, checkpoint); the summary is internal_summary(view) |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | checkpoint/restore/suspension/effect recording of the old runner |
| task_state.py | LiteratureTaskState.suspension_changed | machinery | checkpoint/restore/suspension/effect recording of the old runner |
| task_state.py | LiteratureTaskState.record_execution_failure | episode function | task.py: run_access_tool / failure_outcome (a failed selected operation is returned as the unit outcome and enters the iterator) |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | checkpoint/restore/suspension/effect recording of the old runner |
| task_state.py | LiteratureTaskState.restore | machinery | checkpoint/restore/suspension/effect recording of the old runner |
| task_state.py | LiteratureTaskState.record_effect | machinery | checkpoint/restore/suspension/effect recording of the old runner |
| task_state.py | LiteratureTaskState.checkpoint | machinery | checkpoint/restore/suspension/effect recording of the old runner |
| to_child_passage_evidence_extraction.py | prepare_request | episode function | messages/msg_to_child.py: msg_to_child (slot passage_evidence_extraction); the expanded contract form, parsed-report validation, role check and operation key are machinery or a commission check |
| to_child_source_coverage_improvement.py | prepare_request | episode function | messages/msg_to_child.py: msg_to_child (slot source_coverage_improvement); the expanded contract form, parsed-report validation, role check and operation key are machinery or a commission check |
| to_child_table_evidence_extraction.py | prepare_request | episode function | messages/msg_to_child.py: msg_to_child (slot table_evidence_extraction); the expanded contract form, parsed-report validation, role check and operation key are machinery or a commission check |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py: RETURN_FORM, final_to_parent |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM (selectable fields under the old fact-source names) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py: final_to_parent |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py: literature_completed_work and literature_current_scoring_sheets (raise where selected) |
| to_parent.py | LiteratureReport._a108_fact_sources | episode function | messages/final_to_parent.py: RETURN_FORM |
| to_parent.py | LiteratureReport._a108_facts | episode function | messages/internal_summary.py: saved_cells, grading_cells, aggregation_cells and messages/final_to_parent.py |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py: validate_report |
| waiting.py | LiteratureWaiting | machinery | wait support (supports_wait was False): no wait exists here |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait support (supports_wait was False): no wait exists here |
| yield_estimator.py | validate_yield_bindings | machinery | owner yield-binding declarations check: the controllers own checks replace it |
| yield_estimator.py | _RemainingCommissionedCredit | machinery | old remaining-commissioned-credit estimator: CompletionYieldController with target credit_unit (README 7b) |
| yield_estimator.py | _RemainingCommissionedCredit.__call__ | machinery | old estimator: replaced by CompletionYieldController (yield_estimator.py) |
| yield_estimator.py | _RemainingCommissionedCredit.as_record | machinery | old estimator as_record: replaced by the system declaration |
| yield_estimator.py | _private_yield_controller | episode function | yield_estimator.py: yield_controller |
| yield_estimator.py | _FiniteLiteratureYieldController | machinery | old finite controller: CompletionYieldController (README 7b) |
| yield_estimator.py | _FiniteLiteratureYieldController.__init__ | machinery | old finite controller: CompletionYieldController |
| yield_estimator.py | _FiniteLiteratureYieldController.transitioned | machinery | old finite controller: CompletionYieldController |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py: yield_controller |
| yield_estimator.py | LiteratureYield.continuation_task | episode function | messages/read_from_parent.py: task_key (parent_input) read by yield_estimator.py |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py: yield_controller |
