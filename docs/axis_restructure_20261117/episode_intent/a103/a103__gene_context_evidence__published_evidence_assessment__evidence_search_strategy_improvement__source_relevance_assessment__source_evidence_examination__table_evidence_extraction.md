# A103 table_evidence_extraction: intent carried over from 97308b94c

Episode path: `a103/gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction`
Old role name: `literature_table`. Old class: `LiteratureEpisode` (episode.py), decision source `SourceInvestigationTask` (task.py).
Source: `git show 97308b94c:gene_annotation_episode/episodic_workflow/root/<path>/<file>`. Only files directly in this folder were read; it has no grading/ or scoring/ subfolder.

## What it is for (goal, in its own words)

goal.py, `instructions()`:

> For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their source and scope.
>
> Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.

In short, it reads one selected table or sheet in one source. It picks rows, headers, conditions and footnotes, rereads when outcomes call for it, and returns what the table actually says about gene context, tied to its source.

## Task and instructions

- The task instructions are the common `INSTRUCTIONS` text in task_instructions.py (about 150 lines, copied into this episode). It covers iterative scientific improvement, not a tool itinerary; text and visual extraction anchors; source-bound observations; `investigation_finding`; `same_source_claim_as_ref` and `replaces_refs`; extent_basis and context_allocation; report_update timing; redeliver_report; history reads; and "Do not execute native provider tools".
- `instructions(source, context)` composes them in this order:
  1. the job-episode text, or `INSTRUCTIONS`;
  2. the specialist's instructions (the goal text above), appended or replacing;
  3. `REASONING_COMMIT_REQUIREMENT`, only if `reason` is permitted. It is not permitted here, so this text is never added;
  4. tool knowledge instructions and the launch-library instructions, when they are in the context;
  5. the pending_child_delivery repair text;
  6. the wait text, only if `wait` is permitted (it is not);
  7. the native-event text.
  
  Under `decision_exchange_v1`, the history paragraph is replaced by the request_context/episode.history paragraph.
- The prompt is rendered by `render_receiver_prompt` (task_presentation.py). It shows these sections: TASK, Assigned work, Fixed scope, Caller constraints, Parent constraints, Parent-supplied context, Parent-selected evidence operands, Supplied material and scoped access, Callable supplied Sources, guidance (evidence axis, thought pattern, child tool info, annotation support routes), assigned launch manuals, Callable operations and their operands, permitted children, child options, and the requested return form with fact meanings. Episode steering follows. task_presentation_policy.py picks the renderer per decision frame: HPC, published-scientific, API launch, selected execution, monitor, or receiver. Otherwise it falls back to JSON.

## What it reads from its parent's assignment

from_parent.py `assignment_schema` is a closed `reading_assignment_v1`:
- `page`: `page_assignment_v1` = {`source_ref`, `representation` (text|original|stdout|stderr), `artifact_ref`, `question_context_refs[]`, `prior_delivery_refs[]`}.
- `selection`: one of two shapes:
  - a table selector `_TABLE` = {`source_ref`, `sheet_key`, `offset`, `limit`, `header_row` (int>=1 or null), `where` ({`column` A-Z letters or null, `match` equals|contains, `value`, `case_sensitive`} or null)};
  - a byte window `_WINDOW` = {`source_ref`, `representation`, `offset`, `limit`}.

Validation (`_validate_assignment`, `_validate_page`):
- The source is in scope.
- The page's artifact matches the source's representation artifact (`literature_source_artifact_mismatch`).
- The artifact and every question-context/prior-delivery ref are in scope.
- The selection's source equals the page source (`literature_reading_source_mismatch`) and its representation equals the page representation.
- A window offset must not exceed the artifact size (`source_offset_out_of_bounds`).

`prepare_assignment` requires a non-empty `operation_key`. When the parent role is `literature_page` (source_evidence_examination), the selected source must descend from the parent's assigned page source (`literature_reading_outside_assigned_source`). The parent's page is validated by parent_page_custody.py against `_PAGE`.

From the request it also takes `message.initial_report`, which becomes the initial `report_values`, and `report_contract`, which gives the interpretive schema, the purpose and the requested form. It also takes `message.episode_assignment.launch_instructions` and `message.job_assignment`.

## Children

None. `_CHILDREN['literature_table'] == ()`. It is a leaf. Its received_evidence.py hooks all return empty values.

## Decision state and what it shows the model

decision_state.py builds `view.model_inputs({...})` with these fields:
- `goal`, `scope`, `working_state`, `visible_record_refs`;
- `current_credit`, `current_evidence_vector` (`axis_components`), `investigation_progress` (retained_finding_count, inactive_dependencies, detail_pages; only when receipt projection is on), `credit_binding`;
- `time_accounting`, `pending_work`, `last_local_outcome` (preview), `feedback`, `visual_evidence` (the last completed `image.view`), `report_deliveries`;
- `controller` (state) and `controller_binding`;
- `tools`, `tool_knowledge`, `job_episode_options`, `available_report_facts`;
- `requested_report_purpose`, `requested_form`, `current_report_update`, `current_report_basis_refs`, `report_lifecycle`.

The state also carries:
- the annotation context, or the annotation-axis variant;
- monitoring-information credit, when present;
- the specialist `decision_context` (internal_summary.py): `literature_assignment`, `literature_source_custody` (version, artifact/text/stdout/stderr refs, parent_source_refs per source), `own_literature_outcomes` (own acquisition+read tool outcomes, first `outcome_page_size`=8), and `literature_history_meaning` ("Read exact prior outcomes through episode.history; source discovery alone is not A103 evidence.");
- `_completed_work_axis_results` (a103_sheet, target_sheets, tool_attachments, source_contributions);
- `available_report_facts`, taken from the tool contract catalogue.

decision_inputs.py then adds:
- resource_context and shared_information_context;
- the launch_instruction_library and selected_launch_instructions;
- child_options and the initial binding context;
- completed_action_reports, and the HPC requested_action_history;
- execution_expectations for `literature_table`, with resource and native estimates;
- native_event_targets and the contract_information_profile.

The model may answer with `request_context` lookups (child_options, composition_information, own attempts) before it selects an action (decision_exchange.py).

## Tools offered

source_operations.py offers only `_ACCESS_TOOLS` that the services catalogue also has: `state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`, `execution.estimate`.

Rules on these tools:
- `execution.estimate` is cut down to its `source.xlsx.sheets` and `source.xlsx.rows` branches. If neither exists, it is dropped.
- Inputs go through `source_location_inputs`.
- Every tool's source must stay within the assigned page source. For archive extraction, the member's source is the one checked.
- `source.xlsx.rows` must use the assigned `sheet_key` (`literature_table_sheet_mismatch`).
- locate, sequence.scan, sequence.references and experimental.records run only on `context.received_record_refs`.

Common actions are `tool`, `child` and `redeliver_report`, but there are no children, so `child` is never usable. There is no `reason` action: source_interpretation.py returns no reasoning schema and raises `a103_literature_reasoning_not_commissioned`. The interpretation is carried only in `report_update`.

## Credit

credit.py sets `credit_kind = 'scientific'`. The view is `services.scientific_credit(context, receiver_selection)`, with no projector. In task.py, credit is read after an observed outcome as `source_credit_view(self)['credit']`. A wait action would use the last observed credit, but waiting is not supported here. Credit is stored as given, with no bounding. scientific_records.py: no automatic score judgments (`a103_automatic_judgment_unavailable`).

## Continuation

yield_estimator.py returns `continuation_task` = None and `yield_controller` = None. The episode defines no continuation of its own. In the old runner it ran under the runner's `controller_binding`, using `_category_yield_parameters` for the yield table shown to the model. Which of the three `yield_control/` estimators to use, and with what settings, is not stated in this episode's files. The new port has to choose it. Because the credit is a scientific-findings view, accumulation is the closest fit, but that is not recorded intent.

## What it reports to its parent

to_parent.py: no fact sources and no facts. `validate_report` re-validates the assignment and resolves every form reference in this episode's context.

report_delivery.py `finish`:
- Without a report contract, the result is {credit, pending_handles, current report facts}.
- Otherwise the closing form is the parent's form, filled with the latest admitted interpretations (`report_values`) and the closing facts. It is saved once and reused on replay.

The parent (source_evidence_examination) owns the receiving side.

## Differences from similar episodes

- Sibling `passage_evidence_extraction` (`literature_targeted`) is a file-for-file copy, with three differences:
  - its selection is `{spans: [_WINDOW, ...]}` (minItems 1) instead of `_TABLE | _WINDOW`;
  - it validates every span;
  - it has no `literature_table_sheet_mismatch` check.
- Its role instruction text differs too (targeted passages: no concatenated quotations).
- Compared with the resource episodes in this batch, this episode permits no `reason` or `wait`. It uses the presentation renderer (`complete_with_presentation`), has scientific rather than operational credit, has page-size configuration, and has an explicit yield_estimator file that returns None.

## Files at 97308b94c

| Old file | Lines | This episode's own intent | Old-runner names used (name x count; wf. = self.workflow.) |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| action_policy.py | 16 | Old role must be one of the seven literature ROLES; permits only `tool`, `child`, `redeliver_report` (no `reason`, no `wait`). | BindingContext:context.role×1 |
| binding_record.py | 8 | Record `literature_episode_binding_v1`, binding id = this path, configuration `outcome_page_size`. | none |
| call.py | 79 | Decision call: replay of saved request/response, contract-information and literature-numerical-contract checks, receipts of visible refs, exchange protocol vs single call, `restored_episode_history` on fresh session. Intent: one model decision per unit, replay-identical. | import:a103.runtime×1, journal_table:runtime_model_calls×5, runtime._action_generation_schema×1, runtime._ASSIGNMENT_TRANSPORT×1, runtime.DECISION_EXCHANGE_PROTOCOL×5, runtime._digest×1, runtime.instructional_model_context×1, runtime._json×4, runtime.json×2, runtime._recorded_assignment_transport×1, runtime.WorkflowError×5, wf.contract_information_profile×1, wf.decision_exchanges×1, wf.decision_protocol×3, wf.freeze_contract_information×1, wf.freeze_literature_numerical_contracts×1, wf.history_preview×1, wf.journal×1, wf.numerical_contracts×1, wf.provider×1, wf.receipts×4, wf.services×1, wf.uses_received_record_context×2, wf.validate_contract_information×2 |
| child_commissioning.py | 13 | Leaf: `_CHILDREN['literature_table'] == ()`. | BindingContext:parent.role×2 |
| configuration.py | 16 | `outcome_page_size` (default 8, positive int, else `positive_a103_literature_outcome_page_size_required`); no contract-information profile. | none |
| credit.py | 16 | Credit kind `scientific`; credit view = `services.scientific_credit(context, receiver_selection)`; no projector. | services.scientific_credit×1 |
| decision_contracts.py | 35 | Exchange envelope: `request_context` (lookup) or `select_action` (selection + report_update), exact key sets. | import:a103.runtime×1, runtime.composition_lookup_schema×2, runtime.Draft202012Validator×1, runtime._object×3 |
| decision_exchange.py | 115 | Pending-decision exchange loop: lookups `child_options`, `composition_information`, own attempts; invalid responses become feedback; published refs from lookups join visible refs. | import:a103.runtime×1, journal_table:runtime_model_calls×2, runtime._action_generation_schema×1, runtime._category_yield_parameters×1, runtime.child_option_information×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×2, runtime._json×2, runtime.lookup_attempts×1, runtime.Mapping×3, runtime.model_snapshot×1, runtime._plain×2, runtime._references_in×1, runtime.requested_contract_information×1, runtime.schema_failure_diagnostic×2, runtime.sqlite3×1, runtime.state_frame×1, runtime.ValidationError×4, runtime.yield_table×1, wf.controller_binding×1, wf.decision_exchanges×1, wf.execute×1, wf.journal×1, wf.run_id×1, wf.services×1, wf.store×2, wf.validate_contract_information×1 |
| decision_inputs.py | 65 | Adds resource/shared-information context, launch instruction library + selected instructions, child options, initial binding context, `completed_action_reports`, HPC history, pending work, execution expectations for role `literature_table`, resource/native estimates, native event targets. | EpisodeRequest:request.message×2, import:a103.episode_work_report×2, import:a103.library.hpc_prompt×1, import:a103.runtime×1, runtime.child_option_information×1, runtime.Mapping×1, wf.available_child_roles×1, wf.binding_context×2, wf.episode_bindings×1, wf.execution_expectations×1, wf.job_episodes×2, wf.launch_instructions×2, wf.native_estimation_context×1, wf.native_event_information×2, wf.pending_work×1, wf.resource_context×1, wf.resource_estimator×4, wf.shared_information_context×1, wf.store×2 |
| decision_provider.py | 17 | Model call as role `REASONING`; uses presentation renderer `render_receiver_prompt` when provider supports it. | import:a103.runtime×1, wf.provider×2, wf.specialist×1 |
| decision_state.py | 48 | What the model sees (see Decision state section). | EpisodeRequest:request.goal×1, EpisodeRequest:request.report_contract×4, import:a103.runtime×1, journal_table:runtime_actions×1, method_view:view.child_reports×2, method_view:view.controller_state×1, method_view:view.model_inputs×1, runtime.FACT_MEANINGS×1, runtime.FACT_SOURCES×1, runtime.json×2, runtime.Mapping×3, runtime._plain×2, runtime._references_in×1, wf.annotation_context×1, wf.binding_context×1, wf.catalog×1, wf.controller_binding×1, wf.delivery_status×1, wf.extra_report_sources×1, wf.job_episode_options×1, wf.journal×3, wf.knowledge×1, wf.local_outcome_preview×1, wf.pending_work×1, wf.receipt_projection×1, wf.run_id×1, wf.source_credit_binding×1, wf.source_credit_view×1, wf.specialist×1, wf.store×3, wf.tools×1, wf.working_state×1 |
| episode.py | 33 | Composition of the binding; `binding_path`, `commissioning_parent` = source_evidence_examination, `roles=('literature_table',)`, `entry_roles=()` (never an entry), prompt renderer. | none |
| from_parent.py | 56 | Assignment `reading_assignment_v1` = {page: page_assignment_v1, selection: table selector or byte window}; validates source/artifact identity, refs in scope, selection source = page source, representation, offset <= artifact size; requires `operation_key`; under a `literature_page` parent the reading must stay within the assigned source. | BindingContext:parent.assignment×1, BindingContext:parent.role×2, BindingContext:parent.scope×1, services.read_record×1 |
| goal.py | 9 | A103 goal text + `literature_table` role instruction (quoted above). | none |
| internal_summary.py | 18 | Per-decision context: validated assignment, source custody rows, own acquisition/read outcomes (first `outcome_page_size`), history meaning text. | BindingContext:context.assignment×1, BindingContext:context.episode_id×1, BindingContext:context.scope×2, services.own_outcomes×1 |
| parent_page_custody.py | 20 | Validates the parent's page assignment against `_PAGE`. | none |
| received_evidence.py | 20 | Receives nothing: no report sources/facts/form refs/tokens; no received-report validation. | none |
| report_delivery.py | 25 | At finish: without report contract returns credit + pending handles + facts; else saved form or facts+interpretations filled into parent form; saved once; release. | EpisodeRequest:request.report_contract×2, import:a103.library.private_policy_call×1, import:a103.library.report_fact_assembly×1, import:a103.runtime×1, journal_table:runtime_forms×2, runtime.form_with_facts×1, runtime._json×2, runtime.json×1, runtime.Record×2, wf.binding_context×1, wf.episode_bindings×1, wf.facts×1, wf.journal×2, wf.pending_handles×1, wf.release×2, wf.source_credit_view×1 |
| saved_decision_exchange.py | 81 | Authenticates saved exchange requests/frames/history against original records on replay. | import:a103.runtime×1, journal_table:runtime_model_calls×1, runtime.apply_state_frame×1, runtime.CONTRACT_INFORMATION_OPERATIONS×1, runtime.DECISION_CONTEXT_VERSION×1, runtime.instructional_model_context×1, runtime.is_contract_information×1, runtime._json×8, runtime.json×1, runtime.model_snapshot×1, runtime._recorded_action_generation_schema×1, runtime.requested_contract_information×1, runtime.ValidationError×1, runtime.WorkflowError×9, wf.contract_information_reply×1, wf.decision_exchanges×2, wf.journal×1, wf.validate_contract_information×2 |
| scientific_records.py | 11 | No automatic score judgments; completing one raises `a103_automatic_judgment_unavailable`. | none |
| source_contracts.py | 26 | Constants: ROLES, `_WINDOW`, `_TABLE` (sheet_key, offset, limit, header_row, where{column,match,value,case_sensitive}), `_PAGE`, `_CHILDREN`, tool lists `_ACCESS_TOOLS`/`_ACQUISITION_TOOLS`/`_READ_TOOLS`, `_ROLE_INSTRUCTIONS`. | import:a103.communication×1, import:a103.composition_information×1, import:a103.domain×1, import:a103.episode_bindings×1 |
| source_interpretation.py | 14 | No reasoning action schema; `execute_reasoning` raises `a103_literature_reasoning_not_commissioned`. | none |
| source_operations.py | 52 | Tool catalogue = `_ACCESS_TOOLS` only; `execution.estimate` cut to xlsx sheets/rows branches; source-location inputs; argument validation; locate/scan/references/experimental tools authorized only on received refs; reading must stay within assigned source; `source.xlsx.rows` sheet must equal the assigned `sheet_key`. | BindingContext:context.assignment×1, BindingContext:context.received_record_refs×1, BindingContext:context.scope×5, services.execute_tool×1, services.tool_catalog×1 |
| source_references.py | 35 | Reference-in-scope check, representation -> artifact, ancestry walk over `parent_source_refs`, resolve. | BindingContext:context.role×1, services.read_record×1, services.reference_in_scope×1 |
| task.py | 199 | Unit loop: replay/restore, decision, `apply_response` (selection validated, report_update admitted against interpretive schema), `execute` (tool/reason/wait), credit after observed outcome. | EpisodeRequest:request.message×1, import:a103.episode_source_failure×1, import:a103.library.action_contracts×1, import:a103.library.private_policy_call×1, import:a103.providers×1, import:a103.runtime×1, journal_table:runtime_actions×8, journal_table:runtime_episodes×1, journal_table:runtime_model_calls×2, method_view:view.units_consumed×4, runtime.ActionFailure×1, runtime.ContractInformationError×1, runtime._decode_recorded_action_response×1, runtime.Draft202012Validator×2, runtime.EventTargetError×2, runtime.inspect×1, runtime._json×5, runtime.json×8, runtime.Mapping×2, runtime.nullcontext×5, runtime.observes_action_outcome×1, runtime.ReportBoundaryError×1, runtime.ReportRedelivery×2, runtime.schema_failure_diagnostic×1, runtime.SourceEnd×2, runtime.validate_form×1, runtime.ValidationError×2, runtime._wait_target_feedback×2, runtime.WorkflowError×2, wf.action_schema×1, wf.automatic_score_updates×1, wf.binding_context×1, wf.completed_unit×3, wf.completions×3, wf.controller_value×2, wf.decision_exchanges×3, wf.delivery_resolution_inputs×1, wf.execute×1, wf.execution_binding×7, wf.inprocess_replay×4, wf.journal×7, wf.last_observed_credit×1, wf.next_return×1, wf.pending_work×1, wf.perform_selected_wait×1, wf.receive_native_outcome×1, wf.receive_outcome×1, wf.resolve_pending_deliveries×1, wf.resolver×1, wf.retain_shared_grading_results×1, wf.run_id×3, wf.selected×3, wf.source_credit_view×1, wf.specialist×1, wf.store×8, wf.validate_report×1 |
| task_instructions.py | 26 | Full common INSTRUCTIONS text + composition (specialist instructions, reasoning rule only if `reason` permitted, tool knowledge, launch library, pending delivery, wait text, exchange-protocol history text). | wf.binding_context×1, wf.decision_protocol×1, wf.is_job_source×1, wf.job_episodes×1, wf.knowledge×1, wf.launch_instructions×1, wf.native_event_information×1, wf.permits_common_action×3, wf.specialist×1 |
| task_presentation.py | 171 | Renders TASK prompt: assigned work, scope, constraints, parent context/evidence, material, callable Sources, guidance, launch manuals, operations + operands, child options, requested return form + fact meanings. | import:a103.gene_context_evidence_prompt×1 |
| task_presentation_policy.py | 69 | Chooses renderer (HPC, published-scientific, API launch, selected execution, monitor, receiver) from decision frames; JSON fallback otherwise. | import:a103.decision_context×1, import:a103.execution_prompt×1, import:a103.gene_context_evidence_prompt×2, import:a103.library.hpc_prompt×1, import:a103.library.monitor_prompt×1, import:a103.native_profile_presentation×1 |
| task_state.py | 108 | Episode state fields, initial report from parent, interpretive schema, restore/checkpoint, execution-failure recording as failed own action. | import:a103.episode_source_failure×1, import:a103.runtime×1, journal_table:runtime_actions×5, runtime.ActionLeaf×1, runtime.EFFECT_VERSION×1, runtime.Episode×1, runtime.interpretation_schema×1, runtime._json×2, runtime.json×4, runtime._object×1, runtime._plain×1, runtime.Record×1, wf.archive×1, wf.completions×4, wf.controller_value×1, wf.execution_binding×4, wf.inprocess_replay×7, wf.journal×5, wf.progress_provider×2, wf.recover_commissions×1, wf.run_id×1, wf.source_credit_view×1, wf.store×2, workflow.context(param)×1, workflow.grains(param)×1 |
| task_suspension.py | 9 | Forwards suspension condition to execution backend. | wf.execution_backend×1, wf.execution_handle×2 |
| to_parent.py | 21 | No fact sources/facts; report validation = assignment re-validated + form refs resolved in context. | BindingContext:context.assignment×1, BindingContext:context.scope×1 |
| waiting.py | 8 | `supports_wait = False`. | none |
| yield_estimator.py | 12 | `continuation_task` and `yield_controller` both None: no own continuation definition. | none |

## Carried over

One row per row of `runs/carry_over/functions/a103__gene_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__table_evidence_extraction.tsv`. Old file names are the files at 97308b94c. Library pieces named are existing `episode_support/` functions called by this episode; none was added or moved. Pieces without a home in this episode are marked "unplaced" and listed in `carry_over_blocked/`.

| old file | name | kind | new place or machinery reason |
|---|---|---|---|
| action_policy.py | SourceActionPolicy | machinery | old class shell of the old runner; its methods have their own rows |
| action_policy.py | SourceActionPolicy._role | machinery | old runner role check of the seven literature roles; the class-definition checks and the binding path replace it |
| action_policy.py | SourceActionPolicy.permitted_common_actions | machinery | old runner action-kind permission (tool, child, redeliver_report); task.py offers tool units only (decide/action) |
| binding_record.py | SourceEpisodeBindingRecord | machinery | binding_record.py / the binding's own as_record() (README 3e) |
| binding_record.py | SourceEpisodeBindingRecord.as_record | machinery | binding_record.py / the binding's own as_record() (README 3e) |
| call.py | SourceTaskCall | machinery | old decision call: replay of saved requests, contract-information checks, receipts, exchange protocol |
| call.py | SourceTaskCall.call | machinery | old decision call: replay of saved requests, contract-information checks, receipts, exchange protocol |
| call.py | SourceTaskCall.instructions | machinery | old decision call: replay of saved requests, contract-information checks, receipts, exchange protocol |
| child_commissioning.py | SourceChildCommissioning | episode function | task.py CHILD_SLOTS = {} (a leaf: _CHILDREN was empty) |
| child_commissioning.py | SourceChildCommissioning.allowed_children | episode function | task.py CHILD_SLOTS = {} (a leaf: _CHILDREN was empty) |
| child_commissioning.py | SourceChildCommissioning.child_roles | episode function | task.py CHILD_SLOTS = {} (a leaf: _CHILDREN was empty) |
| configuration.py | SourceEpisodeConfiguration | machinery | old class shell of the old runner; its methods have their own rows |
| configuration.py | SourceEpisodeConfiguration.__init__ | episode function | messages/internal_summary.py OUTCOME_PAGE_SIZE = 8 (the old outcome_page_size default) |
| configuration.py | SourceEpisodeConfiguration.contract_information_configuration | machinery | contract-information exchange configuration of the old decision exchange |
| configuration.py | SourceEpisodeConfiguration.contract_information_profile | machinery | contract-information profile of the old decision exchange |
| credit.py | SourceInvestigationCredit | machinery | old class shell of the old runner; its methods have their own rows |
| credit.py | SourceInvestigationCredit.credit_kind | machinery | credit-kind declaration of the old runner; credit.py credit is the scientific A103 credit |
| credit.py | SourceInvestigationCredit.credit_view | episode function | credit.py credit (the old services.scientific_credit view over the records this Episode holds; library grading/gene_context_evidence/credit.py::A103ContextCredit) |
| credit.py | SourceInvestigationCredit.credit_projector | episode function | credit.py credit (A103ContextCredit, library) |
| decision_contracts.py | SourceDecisionContracts | machinery | decision-exchange envelope (request_context / select_action) |
| decision_contracts.py | SourceDecisionContracts.exchange_schema | machinery | decision-exchange envelope (request_context / select_action) |
| decision_contracts.py | SourceDecisionContracts.exchange_response | machinery | decision-exchange envelope (request_context / select_action) |
| decision_exchange.py | SourceDecisionExchange | machinery | decision-exchange loop (exchange_decision) |
| decision_exchange.py | SourceDecisionExchange.interpretation_context | machinery | context frame of the old decision-exchange loop |
| decision_exchange.py | SourceDecisionExchange.exchange_decision | machinery | decision-exchange loop (exchange_decision) |
| decision_inputs.py | SourceTaskDecisionInputs | episode function | task.py decide / present (context, tools, launch-instruction library and tool knowledge from settings); resource, shared-information, child-option, HPC, execution-expectation and native-event pieces are unplaced (no job, launch or child tool here) |
| decision_inputs.py | SourceTaskDecisionInputs.decision_inputs | episode function | task.py decide / present (context, tools, launch-instruction library and tool knowledge from settings); resource, shared-information, child-option, HPC, execution-expectation and native-event pieces are unplaced (no job, launch or child tool here) |
| decision_provider.py | SourceDecisionProvider | machinery | old class shell of the old runner; its methods have their own rows |
| decision_provider.py | SourceDecisionProvider.conversation_key | machinery | provider conversation key of the old runner |
| decision_provider.py | SourceDecisionProvider.complete_decision | episode function | task.py decide: ModelRequest('REASONING', instructions, context, output_schema); the presentation renderer is task.py present |
| decision_state.py | SourceTaskDecisionState | episode function | task.py decide (goal, scope, assignment, custody, own outcomes, report, visual evidence, time, yield table) and messages/internal_summary.py; annotation context, credit binding, receipt projection and report deliveries are unplaced |
| decision_state.py | SourceTaskDecisionState.decision_state | episode function | task.py decide (goal, scope, assignment, custody, own outcomes, report, visual evidence, time, yield table) and messages/internal_summary.py; annotation context, credit binding, receipt projection and report deliveries are unplaced |
| episode.py | LiteratureEpisode | episode function | episode.py TableEvidenceExtraction |
| from_parent.py | SourceAssignment | machinery | old class shell of the old runner; its methods have their own rows |
| from_parent.py | SourceAssignment.child_assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (schema of the assignment) |
| from_parent.py | SourceAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM, PAGE_FORM, WINDOW_FORM, TABLE_FORM |
| from_parent.py | SourceAssignment._validate_page | episode function | unplaced: Store check of the commission (artifact against source, refs in scope); a wrong commission fails |
| from_parent.py | SourceAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (source, representation and range checks that need no Store); offset against artifact size unplaced |
| from_parent.py | SourceAssignment.prepare_assignment | episode function | unplaced: the parent-side commission preparation (operation_key, within-parent-page check); it reads the parent assignment, which a child cannot read; task.py within_source/admitted carries the tool-level restriction |
| goal.py | SourceInvestigationGoal | machinery | old class shell of the old runner; its methods have their own rows |
| goal.py | SourceInvestigationGoal.instructions | episode function | goal.py GOAL |
| internal_summary.py | SourceInvestigationSummary | machinery | old class shell of the old runner; its methods have their own rows |
| internal_summary.py | SourceInvestigationSummary.initial_decision_context | machinery | initial binding context of the old runner; internal_summary takes the parent input from the view |
| internal_summary.py | SourceInvestigationSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment -> assignment, literature_source_custody -> source_custody, own_literature_outcomes, literature_history_meaning) |
| parent_page_custody.py | ParentPageCustody | machinery | old class shell of the old runner; its methods have their own rows |
| parent_page_custody.py | ParentPageCustody._parent_page_schema | episode function | unplaced: validates the parent's own page assignment, which a child cannot read |
| parent_page_custody.py | ParentPageCustody._validate_parent_page | episode function | unplaced: validates the parent's own page assignment, which a child cannot read |
| received_evidence.py | SourceReceivedEvidence | machinery | received-report hooks of the old runner; all returned empty for this leaf (no child) |
| received_evidence.py | SourceReceivedEvidence.received_report_sources | machinery | received-report hooks of the old runner; all returned empty for this leaf (no child) |
| received_evidence.py | SourceReceivedEvidence.received_report_facts | machinery | received-report hooks of the old runner; all returned empty for this leaf (no child) |
| received_evidence.py | SourceReceivedEvidence.received_form_references | machinery | received-report hooks of the old runner; all returned empty for this leaf (no child) |
| received_evidence.py | SourceReceivedEvidence.received_evidence_tokens | machinery | received-report hooks of the old runner; all returned empty for this leaf (no child) |
| received_evidence.py | SourceReceivedEvidence.validate_received_report | machinery | received-report hooks of the old runner; all returned empty for this leaf (no child) |
| report_delivery.py | SourceTaskReportDelivery | machinery | old class shell of the old runner; its methods have their own rows |
| report_delivery.py | SourceTaskReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (credit and finding); the saved parent form, pending handles and release are old report-form machinery |
| saved_decision_exchange.py | SourceSavedDecisionExchange | machinery | replay authentication of saved decision exchanges |
| saved_decision_exchange.py | SourceSavedDecisionExchange.validate_contract_exchange_request | machinery | replay authentication of saved decision exchanges |
| saved_decision_exchange.py | SourceSavedDecisionExchange.validate_contract_exchange_history | machinery | replay authentication of saved decision exchanges |
| scientific_records.py | SourceScientificRecords | machinery | old class shell of the old runner; its methods have their own rows |
| scientific_records.py | SourceScientificRecords.automatic_score_judgments | machinery | automatic score judgments hook of the old runner (this episode had none) |
| scientific_records.py | SourceScientificRecords.complete_score_judgment | machinery | score judgment hook of the old runner; it only raised a_103_automatic_judgment_unavailable |
| source_interpretation.py | SourceInterpretation | machinery | old class shell of the old runner; its methods have their own rows |
| source_interpretation.py | SourceInterpretation.reasoning_action_schema | machinery | reasoning-commit action schema; this episode has no reason action |
| source_interpretation.py | SourceInterpretation.reasoning_has_task_content | machinery | reasoning-commit hook; no reason action |
| source_interpretation.py | SourceInterpretation.execute_reasoning | machinery | reasoning-commit hook; it only raised a103_literature_reasoning_not_commissioned |
| source_operations.py | SourceOperations | machinery | old class shell of the old runner; its methods have their own rows |
| source_operations.py | SourceOperations.catalog | episode function | task.py catalog (access tools only, execution.estimate cut to its workbook branches, source_location_inputs); tool_catalog tool |
| source_operations.py | SourceOperations.execute | episode function | task.py run_access_tool and the access tools (state_query ... execution_estimate); library tools/gene_context_evidence/tools.py::ToolRegistry |
| source_operations.py | SourceOperations._tool_arguments | episode function | task.py admitted (schema, source within the assigned page source, sheet_key guard) |
| source_references.py | SourceReferences | machinery | old class shell of the old runner; its methods have their own rows |
| source_references.py | SourceReferences._require | episode function | already in library: episode_support/records/received_records.py::read_record_in_scope (called by task.py) |
| source_references.py | SourceReferences._artifact | episode function | messages/internal_summary.py representation_artifact |
| source_references.py | SourceReferences._within_source | episode function | task.py within_source |
| source_references.py | SourceReferences.resolve | machinery | reference resolution is custody (records.get / ctx.store.get) |
| task.py | SourceInvestigationTask | machinery | old class shell of the old runner; its methods have their own rows |
| task.py | SourceInvestigationTask.next | episode function | task.py decide (the unit choice and prompt); replay/restore parts are machinery |
| task.py | SourceInvestigationTask.apply_response | episode function | task.py action (the model answer to one tool call or Rejected); the report update is the report tool |
| task.py | SourceInvestigationTask.execute | episode function | task.py run_access_tool, the access tools and report; wait and reason branches are not carried |
| task_instructions.py | instructions | episode function | task.py instructions |
| task_presentation.py | _text | episode function | task.py section (text/JSON body of a prompt section) |
| task_presentation.py | render_requested_return | episode function | task.py present, section Return (FINDING_FORM) |
| task_presentation.py | _goal | episode function | task.py present, section Assigned work |
| task_presentation.py | _guidance | episode function | unplaced: evidence-axis, thought-pattern, child-tool and annotation-support guidance and launch manuals; no home in this episode (no child, no launch) |
| task_presentation.py | _source_operands | episode function | task.py source_operands |
| task_presentation.py | _task | episode function | task.py present |
| task_presentation.py | render_receiver_prompt | episode function | task.py present |
| task_presentation_policy.py | _ordinary_runtime_receiver_context | machinery | receiver-context selector of the old decision frames |
| task_presentation_policy.py | present_source_task | machinery | renderer selector per decision frame (HPC, monitor, launch ...); the receiver renderer it chose is task.py present |
| task_state.py | SourceTaskState | machinery | old class shell of the old runner; its methods have their own rows |
| task_state.py | SourceTaskState.__init__ | machinery | old runner state fields |
| task_state.py | SourceTaskState.bind_execution_context | machinery | execution binding of the old runner |
| task_state.py | SourceTaskState.record_execution_failure | episode function | task.py run_access_tool: a failed selected operation is the unit outcome (library tools/unit_outcomes.py::failure_outcome) |
| task_state.py | SourceTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.restore | machinery | checkpoint/restore |
| task_state.py | SourceTaskState.record_effect | machinery | effect recording of the old runner |
| task_state.py | SourceTaskState.checkpoint | machinery | checkpoint/restore |
| task_suspension.py | SourceTaskSuspension | machinery | old class shell of the old runner; its methods have their own rows |
| task_suspension.py | SourceTaskSuspension.suspension_changed | machinery | suspension forwarding to the old execution backend |
| to_parent.py | SourceInvestigationReport | machinery | old class shell of the old runner; its methods have their own rows |
| to_parent.py | SourceInvestigationReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (no fact sources: only credit and finding) |
| to_parent.py | SourceInvestigationReport.facts | episode function | messages/final_to_parent.py final_to_parent (no facts: only credit and finding) |
| to_parent.py | SourceInvestigationReport.current_report_facts | machinery | report-facts accessor of the old report-form machinery |
| to_parent.py | SourceInvestigationReport.validate_report | episode function | messages/final_to_parent.py validate_report (called by final_to_parent) |
| waiting.py | SourceInvestigationWaiting | machinery | old class shell of the old runner; its methods have their own rows |
| waiting.py | SourceInvestigationWaiting.supports_wait | machinery | wait support flag (False); this episode has no wait |
| yield_estimator.py | SourceInvestigationYield | machinery | old class shell of the old runner; its methods have their own rows |
| yield_estimator.py | SourceInvestigationYield.continuation_task | machinery | old default continuation (None); yield_estimator.py chooses BoundedQualityYieldController |
| yield_estimator.py | SourceInvestigationYield.yield_controller | episode function | yield_estimator.py yield_controller (BoundedQualityYieldController, maximum A103ContextCredit.native_score_maximum) |
