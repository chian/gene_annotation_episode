# source_coverage_improvement (A101) — intent of the old files

Episode folder: `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement`

Source read: only this folder's own files at commit `97308b94c` (25 files, 1,262 lines; no `grading/` or `scoring/` subfolder; `tests/` holds only an empty `__init__.py`). Nothing outside the episode tree was read at that commit. Old-runner names per file are counted in `runs/carry_over/calls/a101_04.tsv`.

Old role name in the files: `literature_ordered` (ordered reading of one source). Old binding path: `sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement`. Commissioning parent: `.../source_evidence_examination` (old role `literature_page`).

## What this episode is for

Its goal text (`goal.py`, joined with its role text in `source_contracts.py`), verbatim:

> For A101, identify the actual sequence or region and its aligned homolog before using a source claim. Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database labels, and their applicability to the target distinct and source-grounded.
>
> Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.

So: read one assigned source in document order, window by window, and decide after each read whether to continue, reread, move the window, or interpret what was obtained. The folder name says "source coverage improvement"; the files call the same thing ordered reading.

## Task and instructions

`task_instructions.py` composes the instruction text for each decision, in this order:

1. The base literature instruction text `INSTRUCTIONS`. It is **not** in this folder: it is imported from the old `root/a101/library/literature_investigation_prompt` (placed now at `episode_support/literature/prompts/sequence_homology_evidence/literature_investigation_prompt.py`). The episode's own copy of the intent is therefore the composition, not the base text.
2. The goal text above, appended on a new line (the binding does not set `replaces_default_instructions`).
3. Tool-knowledge instructions, when `tool_knowledge` is in the decision context.
4. Launch-instruction-library instructions, when `launch_instruction_library` is in the decision context.
5. A fixed paragraph, verbatim: "When pending_child_delivery is supplied, the selected child has finished its work but its typed return has not been delivered. Complete that existing acquisition by selecting redeliver_report with a corrected form. Use only the saved child facts and interpretations for this repair and preserve current_report_update. The supplied selection schema describes the available communication operation; this repair does not select new scientific work."
6. Under the `decision_exchange_v1` protocol, the base text's passage from "On a fresh provider conversation," up to "Do not execute native provider tools." is replaced by: "Use request_context exchanges for your own attempt metadata and selected inputs; these create no completed action or observation. Read exact previously received outcomes with the ordinary episode.history tool, view=records and selected decision_indices. That read supplies its own ordinary action observation and does not execute or credit the historical work again."

Unlike the resource episodes, this composer adds no reasoning-commit requirement (`REASONING_COMMIT_REQUIREMENT` is imported but unused) and no wait paragraphs.

Each decision is presented to the model through this episode's own prompt renderer, `render_literature_source_prompt` (registered as `decision_prompt_renderer` in `episode.py`; imported from the old `root/a101/library/literature_source_prompt`, for which the placement tables list no target).

The model's response is `{selection, report_update}`: one selected action, plus the interpretation fields of the parent's form as they stand *before* that action (`task.py: apply_response`). A selection that fails admission creates no unit and gives feedback (`category: action_contract`); a `report_update` that fails admission gives `category: report_format` feedback but the selected work still proceeds.

## What it reads from its parent's assignment

`from_parent.py` admits exactly `reading_assignment_v1`:

| Field | Content |
|---|---|
| `version` | constant `reading_assignment_v1` |
| `page` | `page_assignment_v1`: `source_ref`, `representation` (`text` / `original` / `stdout` / `stderr`), `artifact_ref`, `question_context_refs`, `prior_delivery_refs` |
| `selection` | one byte window: `source_ref`, `representation`, `offset` (>= 0), `limit` (>= 1) |

Checks (each raises; none is repaired):

- the page's source is a `source` record in scope; the artifact that source holds for the page's representation equals `artifact_ref` (`literature_source_artifact_mismatch`); the artifact and every question-context and prior-delivery reference are in scope (`literature_reference_unavailable`);
- the window's `source_ref` equals the page's (`literature_reading_source_mismatch`), its representation equals the page's (`literature_reading_representation_mismatch`), and its offset is not past the artifact's size (`source_offset_out_of_bounds`);
- when the parent is the page episode, the parent's own page assignment is validated (`from_parent_page.py`) and this episode's source must be the parent's source or descend from it through `parent_source_refs` (`literature_reading_outside_assigned_source`);
- an operation key is required (`operation_key_required`).

It also reads from its request: the initial report values and the parent's report contract (purpose and schema).

## Children

None. `source_contracts._CHILDREN['literature_ordered']` is `()`. `permitted_common_actions` still lists `child` and `redeliver_report`, but no child role is declared, so this episode is a leaf.

## Decision state shown to the model

`decision_state.py` (general state) plus `internal_summary.py` (this episode's own part) plus `decision_inputs.py` (extra inputs).

This episode's own part (`internal_summary.py: decision_context`):

- `literature_assignment`: the validated assignment;
- `literature_source_custody`: for the assigned source, `source_ref`, `version`, `artifact_ref`, `text_ref`, `stdout_ref`, `stderr_ref`, `parent_source_refs`;
- `own_literature_outcomes`: the first page (page size 8, from `configuration.py`) of this episode's own outcomes of the acquisition and read tools;
- `literature_history_meaning`: "Read exact prior outcomes through episode.history; source discovery alone is not A101 evidence."

General state: goal, scope, working state, visible record references, current credit, current evidence vector, investigation progress (when shown), credit binding, time accounting (elapsed view, informational), pending work, last outcome (preview) and feedback, visual evidence (the pixels returned by the most recent completed `image.view` action), report deliveries, controller state and binding, tools, tool knowledge, job episode options, available report facts, the parent's requested report purpose and form, current report update and its basis references, the line "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.", and, because this is a scientific episode, the annotation context for its scope.

Extra inputs: resource context, shared-information context, launch-instruction library and selected launch instructions, child options, completed action reports, pending work, execution expectations and resource estimates, native execution expectations and event targets, contract-information profile.

## Tools

`source_operations.py: catalog` offers only these, filtered from the store-wide tool catalogue (`_ACCESS_TOOLS`):

`state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`, `execution.estimate`.

- `execution.estimate` is narrowed to its `source.xlsx.sheets` / `source.xlsx.rows` branches and dropped when it has neither.
- Every input schema passes through `source_location_inputs`.
- No acquisition tool (`public.*`) is offered: this episode reads what it was given. (The `public.ncbi.search` narrowing in the file cannot apply here.)
- Any tool call whose source (or, for `source.archive.extract`, whose archive member's source) is outside the assigned page's source is not executed as asked: it returns an outcome with `status: invalid`, an operation reference, and feedback `category: arguments_or_reference` carrying the contract error code. That invalid outcome is still an outcome of the action.
- `source.locate`, `source.sequence.scan`, `source.sequence.references` and `source.experimental.records` run with the records this episode has received as their permitted records.

Reasoning commits are not part of this episode: `reasoning_action_schema` returns nothing and `execute_reasoning` raises `a101_literature_reasoning_not_commissioned`. Its interpretation travels only in `report_update`. It does not wait (`waiting.py: supports_wait` is false). It does no automatic grading (`scientific_records.py`: no judgments; completing one raises `a101_automatic_judgment_unavailable`).

## Credit

`credit.py`: credit kind `scientific`; the credit is whatever the axis's scientific credit view gives for this episode's context (`services.scientific_credit(context, receiver_selection)`); no projector of its own. `task.py: execute` measures credit after every observed outcome of a selected action and gives the controller that value. An outcome that is not an observation raises an action failure instead. Nothing in these files bounds, clamps or rescales the credit.

## Continuation

`yield_estimator.py` declares nothing: `continuation_task` returns `None` and `yield_controller` returns `None`. The old files name no yield estimator and no settings for this episode; continuation was left to whatever controller the old runner supplied. Which of the three estimators in `yield_control/` (accumulation, bounded quality, completion with a target) and which settings this episode uses is therefore **not stated in the carried-over files** and has to be decided when it is bound.

## What it reports to its parent

`to_parent.py`: no fact sources and no facts of its own. The report is the parent's typed form:

- interpretation fields are the last admitted `report_update` (initially the parent's initial values);
- recorded fact fields are filled at the end (`report_delivery.py: finish`, `form_with_facts`), and the filled form is saved once and reused;
- `validate_report` re-validates the assignment and admits the form against the parent's schema, resolving every reference against what this episode can see.

With no report contract the result is `{credit, pending_handles}`.

`received_evidence.py` is all empty (no child reports to receive).

## Differences from its siblings

- **table_evidence_extraction** (same parent): identical files except (a) the assignment `selection` there is a table selection *or* a byte window, here only a byte window; (b) there `source.xlsx.rows` must use the assigned `sheet_key`, here there is no sheet check; (c) the role sentence of the goal.
- **The targeted-passage sibling** (old role `literature_targeted`, same parent) is named in `source_contracts.py` but its files were not read here.
- **Resource episodes** (`resource_result_acquisition`, `resource_work_submission`): those permit reasoning commits and waiting, carry their base instruction text inside the folder, use operational credit, call the provider directly without a prompt renderer, and do not add annotation context to the decision state.

## File by file

"Old-runner names" lists what must be replaced; exact counts are in `runs/carry_over/calls/a101_04.tsv`. Every file except the two empty `__init__.py` starts from old role checks (`self._role(context.role)`), which exist only because one class once served several roles.

| Old file | Lines | This episode's own intent in it | Old-runner names it uses |
|---|---|---|---|
| `__init__.py` | 0 | none | none |
| `tests/__init__.py` | 0 | none | none |
| `goal.py` | 9 | the A101 goal sentence and the choice of the ordered-reading role sentence | `context.role` (BindingContext); hook `instructions` |
| `source_contracts.py` | 26 | role sentences; assignment shapes `_WINDOW`, `_TABLE`, `_PAGE`; child table (`literature_ordered: ()`); tool lists `_ACCESS_TOOLS`, `_ACQUISITION_TOOLS`, `_READ_TOOLS`; binding version `literature_episode_binding_v1` | imports from old `root.a101.communication` (`ReportBoundaryError`, `plain`, `validate_form`), `root.a101.composition_information` (`CONTRACT_INFORMATION_PROFILE`, unused), `root.a101.domain` (`ContractError`, `REF`, `identity`, `obj`, `source_location_inputs`, `validate_schema`), `root.a101.episode_bindings` (`reference_in_context`); old role table `ROLES` |
| `task_instructions.py` | 18 | the composition order and the two fixed paragraphs quoted above | `source.workflow.specialist`, `.binding_context`, `.knowledge.instructions`, `.launch_instructions.instructions`, `.decision_protocol`; imports from old `root.a101.library.literature_investigation_prompt` (`INSTRUCTIONS`, `DECISION_EXCHANGE_PROTOCOL`, `REASONING_COMMIT_REQUIREMENT`) |
| `configuration.py` | 12 | `outcome_page_size = 8`, must be a positive integer | `services` object held; `_contract_information_profile`, `reference_parent_sources` slots |
| `binding_record.py` | 8 | record of version, binding id and page size | hook `as_record` |
| `episode.py` | 60 | this episode is `literature_ordered` only; not an entry; its task class and prompt renderer; children come from the child table | old binding protocol: `decision_source_type`, `decision_prompt_renderer`, `binding_path`, `commissioning_parent`, `roles`, `entry_roles`, `contract_information_profile`, `allowed_children`, `child_roles`, `context_hook_applies`; `context.role`, `context.path`; import from old `root.a101.library.literature_source_prompt` |
| `from_parent.py` | 54 | the assignment form and every check listed above | `context` / `parent` as BindingContext (`.role`, `.assignment`, `.scope`); `self.services.read_record`; hooks `assignment_schema`, `child_assignment_schema`, `prepare_assignment` |
| `from_parent_page.py` | 17 | the parent's page assignment must itself be valid | `parent.assignment`, `parent.scope` (BindingContext) |
| `source_references.py` | 35 | scope check of references; which artifact a representation means; descent through `parent_source_refs` | `self.services.reference_in_scope`, `self.services.read_record`; `reference_in_context` (old `episode_bindings`); `context.role` |
| `source_operations.py` | 65 | the tool list, the narrowing of `execution.estimate`, the outside-assigned-source guard, the invalid outcome shape, permitted records for four tools, no reasoning | `self.services.tool_catalog`, `self.services.execute_tool`; `context.role`, `.scope`, `.assignment`, `.received_record_refs`; hooks `permitted_common_actions`, `reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`, `catalog`, `execute` |
| `internal_summary.py` | 19 | the four summary fields shown to the model | `self.services.own_outcomes`; `context.role`, `.assignment`, `.scope`, `.episode_id`; hooks `initial_decision_context`, `decision_context` |
| `decision_state.py` | 60 | which fields the model sees; the image-view visual evidence rule; the report-lifecycle sentence | 20 `self.workflow.*` members (`store`, `journal`, `working_state`, `local_outcome_preview`, `source_credit_view`, `source_credit_binding`, `receipt_projection`, `pending_work`, `delivery_status`, `controller_binding`, `catalog`, `knowledge`, `job_episode_options`, `extra_report_sources`, `is_scientific_source`, `annotation_context`, `specialist`, `binding_context`, `tools`, `run_id`); SQL on table `runtime_actions`; `journal.elapsed_view`; `view.model_inputs`, `view.child_reports`, `view.controller_state`; imports from old `root.a101.runtime` (`FACT_MEANINGS`, `FACT_SOURCES`, `_plain`, `_references_in`); `bind_functions` rebinding |
| `decision_inputs.py` | 76 | which extra inputs are added | `self.workflow.*` (`resource_context`, `shared_information_context`, `launch_instructions`, `available_child_roles`, `episode_bindings.initial_decision_context`, `binding_context`, `pending_work`, `execution_expectations`, `job_episodes`, `store`, `resource_estimator`, `native_estimation_context`, `native_event_information`); `request.message` keys `episode_assignment`, `job_assignment`; imports from old `root.a101.runtime` (`child_option_information`), `root.a101.episode_work_report`, `root.a101.hpc_prompt`; `bind_functions` rebinding |
| `task.py` | 214 | response is `{selection, report_update}`; invalid selection makes no unit; report-format failure keeps the work; invalid/failed outcome still enters with its credit; credit measured after each observed outcome | 24 `self.workflow.*` members (`journal`, `store`, `inprocess_replay`, `execution_binding`, `completions`, `completed_unit`, `selected`, `next_return`, `resolve_pending_deliveries`, `action_schema`, `delivery_resolution_inputs`, `decision_exchanges`, `resolver`, `validate_report`, `execute`, `pending_work`, `receive_native_outcome`, `receive_outcome`, `automatic_score_updates`, `source_credit_view`, `retain_shared_grading_results`, `controller_value`, `run_id`, `services.instructions`); tables `runtime_actions`, `runtime_episodes`, `runtime_model_calls`; `_execution_context._ready_owned_child`; imports from old `root.a101.runtime` (21 names), `root.a101.providers` (`ModelCallError`), `root.a101.episode_source_failure`, `root.a101.library.read_mapping_values`; `bind_functions` rebinding |
| `task_decision.py` | 347 | decisions go through this episode's prompt renderer; the exchange protocol (`request_context` lookups before `select_action`) | `self.workflow.*` (`provider`, `specialist`, `journal`, `contract_information_profile`, `validate_contract_information`, `numerical_contracts`, `decision_protocol`, `decision_exchanges`, `freeze_literature_numerical_contracts`, `freeze_contract_information`, `receipts`, `uses_received_record_context`, `history_preview`, `store`, `contract_information_reply`, `controller_binding`, `services.decision_exchange_instructions`, `execute`, `run_id`); table `runtime_model_calls`; imports from old `root.a101.runtime` (30 names, including `yield_table`, `_category_yield_parameters`), old per-axis `root.a101.providers` (4 identity names) and the **old shared root** `root.providers` (7 identity names; never restored); `bind_functions` rebinding |
| `task_state.py` | 115 | starts from the parent's initial report; interpretation schema from the report contract; a failed selected operation is recorded as a failed outcome with credit | `self.workflow.*` (`context`, `grains`, `archive`, `store`, `run_id`, `journal`, `source_credit_view`, `controller_value`, `execution_binding`, `completions`, `inprocess_replay`, `recover_commissions`, `progress_provider`); table `runtime_actions`; `request.message['initial_report']`, `request.report_contract`; imports from old `root.a101.runtime` (`ActionLeaf`, `EFFECT_VERSION`, `Episode`, `Record`, `_json`, `_object`, `_plain`, `interpretation_schema`), `root.a101.episode_source_failure`; `bind_functions` rebinding |
| `to_parent.py` | 21 | no own facts; report is admitted against the parent's schema with reference resolution | `context.role`, `.assignment`, `.scope`; hooks `fact_sources`, `facts`, `current_report_facts`, `validate_report` |
| `received_evidence.py` | 20 | receives nothing | hooks `received_report_sources`, `received_report_facts`, `received_form_references`, `received_evidence_tokens`, `validate_received_report` |
| `report_delivery.py` | 34 | the form is filled once from facts plus the last interpretation and reused; without a contract, credit and pending handles | `self.workflow.*` (`source_credit_view`, `pending_handles`, `episode_bindings.current_report_facts`, `binding_context`, `release`, `journal`, `facts`); table `runtime_forms`; `request.report_contract`; imports from old `root.a101.runtime` (`Record`, `_json`, `form_with_facts`, `json`); `bind_functions` rebinding |
| `scientific_records.py` | 11 | no automatic judgments | hooks `automatic_score_judgments`, `complete_score_judgment` |
| `credit.py` | 15 | credit kind `scientific`; credit from the axis's scientific credit view; no projector | `self.services.scientific_credit`; `context.role`; old hooks `credit_kind`, `credit_view`, `credit_projector` |
| `yield_estimator.py` | 11 | declares no continuation task and no controller | `context.role`; old hooks `continuation_task`, `yield_controller` |
| `waiting.py` | 15 | does not wait | `self.workflow.execution_handle`, `self.workflow.execution_backend.set_suspension`; hooks `supports_wait`, `suspension_changed` |

## Carried over

Folder: this episode's ten files. Files marked UNPLACED are in `carry_over_blocked/a101__sequence_homology_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__source_coverage_improvement.md`. "Library candidate" rows stay in the episode file that uses them.

| old file | name | kind | new place |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding_record.py: the binding's own as_record() |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | the binding's own as_record() (README 3e) |
| configuration.py | LiteratureConfiguration | episode function | values: outcome_page_size -> messages/internal_summary.py OUTCOME_PAGE_SIZE; services held and contract slots are machinery |
| configuration.py | LiteratureConfiguration.__init__ | episode function | outcome_page_size = 8 -> messages/internal_summary.py OUTCOME_PAGE_SIZE (fixed constant); services/_contract_information_profile/reference_parent_sources slots: machinery (services object, contract-information profile, parent-source slot) |
| credit.py | LiteratureCredit | episode function | credit.py credit |
| credit.py | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | LiteratureCredit.credit_view | episode function | credit.py credit (the axis scientific credit view = A101SequenceCredit, private copy of the projector of the axis head read at 97308b94c, library NativeCorrespondenceScoring.read_details called with records; BLOCKED-ON-STORE-ACCESS inside the library) |
| credit.py | LiteratureCredit.credit_projector | episode function | credit.py A101SequenceCredit (private copy; the axis projector was not this episode's hook but its credit is that projector's) |
| decision_inputs.py | LiteratureDecisionInputs | episode function | task.py decide |
| decision_inputs.py | LiteratureDecisionInputs.decision_inputs | episode function | task.py decide: tool_knowledge and launch_instruction_library from settings directories, extend_context; the rest (resource context, shared-information context, selected launch instructions, child options, completed/requested action reports, pending work, execution expectations, resource estimates, native event targets, contract-information profile) not placed, see blocked file |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | old provider patching (_bind_original_task_runtime_providers, bind_functions rebinding) |
| decision_state.py | LiteratureDecisionState | episode function | messages/internal_summary.py internal_summary and task.py decide |
| decision_state.py | LiteratureDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (visual_evidence, action_yields, report, report_lifecycle) and task.py decide (goal, scope, tools, time_accounting, feedback, tool_knowledge); runtime_actions SQL, journal.elapsed_view, workflow.* members, receipts projection, report_deliveries, annotation context: machinery or not placed |
| decision_state.py | _bind_original_task_runtime_providers | machinery | old provider patching (_bind_original_task_runtime_providers, bind_functions rebinding) |
| episode.py | LiteratureEpisode | episode function | episode.py SourceCoverageImprovement |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | old contract-information profile hook |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | old contract-information profile hook |
| episode.py | LiteratureEpisode._role | machinery | old role table check (one class once served several roles) |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} (no child) |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} (no child) |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | old role/path hook of the binding protocol |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | LiteratureAssignment.child_assignment_schema | machinery | the parent's view of the child schema (README 3b C3); the child's own form is ASSIGNMENT_FORM |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (version, page, selection; new fields scope, received_record_refs) |
| from_parent.py | LiteratureAssignment._validate_page | episode function | not placed (UNPLACED): Store checks of the commission (artifact equals the source's artifact for the representation; references in scope); a wrong commission fails |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent (window source/representation/range checks); the artifact-size check (source_offset_out_of_bounds) not placed (UNPLACED) |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; operation_key_required is old runner machinery; the parent-page descent check not placed (UNPLACED); the page-source restriction is carried in task.py within_source |
| from_parent_page.py | OriginalPageAssignment | episode function | not placed (UNPLACED): reads the parent's own assignment |
| from_parent_page.py | OriginalPageAssignment._parent_page_schema | episode function | not placed (UNPLACED): reads the parent's own assignment |
| from_parent_page.py | OriginalPageAssignment._validate_parent_page | episode function | not placed (UNPLACED): validates parent.assignment, which a child cannot read (README 5 item 14) |
| goal.py | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL (text); composed into the instructions by task.py instructions |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | LiteratureSummary.initial_decision_context | machinery | old hook; returned {} |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary: literature_assignment, literature_source_custody, own_literature_outcomes (outcome_page), literature_history_meaning |
| received_evidence.py | LiteratureReceivedEvidence | machinery | child-report receipt hooks; no child |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | child-report receipt hook; no child |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | machinery | child-report receipt hook; no child |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | child-report receipt hook; no child |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | child-report receipt hook; no child |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | machinery | child-report receipt hook; no child |
| report_delivery.py | LiteratureReportDelivery | episode function | messages/final_to_parent.py final_to_parent |
| report_delivery.py | LiteratureReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (the form filled once from facts and the last interpretation: the finding is the last report; credit is completion['credit']); runtime_forms saving, pending_handles and release are machinery |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | old provider patching (_bind_original_task_runtime_providers, bind_functions rebinding) |
| scientific_records.py | LiteratureScientificRecords | machinery | old automatic-judgment hooks; no judgments |
| scientific_records.py | LiteratureScientificRecords.automatic_score_judgments | machinery | old automatic-judgment hook; returned nothing |
| scientific_records.py | LiteratureScientificRecords.complete_score_judgment | machinery | old automatic-judgment hook; raised a101_automatic_judgment_unavailable |
| source_operations.py | LiteratureOperations | episode function | task.py (tools, catalog, offered, run_access_tool) |
| source_operations.py | LiteratureOperations.permitted_common_actions | episode function | task.py offered/TOOLS (tool only; child and redeliver_report do not exist) |
| source_operations.py | LiteratureOperations.reasoning_action_schema | episode function | task.py: no reasoning tool is offered (returned nothing) |
| source_operations.py | LiteratureOperations.reasoning_has_task_content | episode function | task.py: no reasoning tool is offered (returned False) |
| source_operations.py | LiteratureOperations.execute_reasoning | episode function | task.py: no reasoning tool in TOOLS (old: raise a101_literature_reasoning_not_commissioned) |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py catalog, offered, INPUT_SCHEMAS, DESCRIPTIONS, LIBRARY_NAMES (execution_estimate narrowed to the xlsx branches; every schema through source_location_inputs) |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool and the sixteen tool functions (invalid outcome shape; permitted records for four tools = ctx.store.refs()) |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted (schema check and the outside-assigned-source guard) |
| source_references.py | LiteratureReferences | episode function | task.py within_source; library records/received_records.py |
| source_references.py | LiteratureReferences._require | episode function | already in library: episode_support/records/received_records.py read_record_in_scope (called from task.py) |
| source_references.py | LiteratureReferences._artifact | episode function | messages/internal_summary.py representation_artifact (library candidate) |
| source_references.py | LiteratureReferences._within_source | episode function | task.py within_source (library candidate) |
| source_references.py | LiteratureReferences.resolve | machinery | reference_in_context resolver of the old shared root; replaced by records.holds (messages/internal_summary.py report_source_held) |
| task.py | LiteratureTask | episode function | task.py (decide, action, TOOLS) |
| task.py | LiteratureTask.instructions | episode function | task.py instructions |
| task.py | LiteratureTask.next | episode function | task.py decide (the next-unit loop, restore, SourceEnd and replay parts are machinery) |
| task.py | LiteratureTask.apply_response | episode function | task.py action (selection validated against the schema, Rejected feedback; report_update becomes the report tool) |
| task.py | LiteratureTask.execute | episode function | task.py run_access_tool (failed operation = failure_outcome); wait, child and redeliver branches not carried |
| task.py | _bind_original_task_runtime_providers | machinery | old provider patching (_bind_original_task_runtime_providers, bind_functions rebinding) |
| task_decision.py | LiteratureTaskDecision | episode function | task.py decide |
| task_decision.py | LiteratureTaskDecision.decision_completion | machinery | old decision loop / journal of model calls |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py decide (ModelRequest); the call, recording and conversation parts are machinery |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | conversation state (README 3a) |
| task_decision.py | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop (a lookup is a tool; the prompt renderer render_literature_source_prompt has no placed target, UNPLACED: decide sends a structured context) |
| task_decision.py | _bind_original_task_runtime_providers | machinery | old provider patching (_bind_original_task_runtime_providers, bind_functions rebinding) |
| task_instructions.py | instructions | episode function | task.py instructions (INSTRUCTIONS with the history span replaced, goal, tool-knowledge and launch-instruction text); the pending-delivery paragraph is not carried |
| task_state.py | LiteratureTaskState | machinery | checkpoint/restore state |
| task_state.py | LiteratureTaskState.__init__ | machinery | initial report and interpretation schema from the parent's report contract (replaced by the report tool); checkpoint state |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | execution context binding |
| task_state.py | LiteratureTaskState.record_execution_failure | episode function | task.py run_access_tool: a failed selected operation is returned as failure_outcome (library tools/unit_outcomes.py) |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | LiteratureTaskState.restore | machinery | checkpoint/restore |
| task_state.py | LiteratureTaskState.record_effect | machinery | record_effect (README 3e) |
| task_state.py | LiteratureTaskState.checkpoint | machinery | checkpoint/restore |
| task_state.py | _bind_original_task_runtime_providers | machinery | old provider patching (_bind_original_task_runtime_providers, bind_functions rebinding) |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (no fact sources: credit and finding only) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent (no facts of its own) |
| to_parent.py | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py final_to_parent (no facts of its own) |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (assignment agreement, report form, held references); validate_form against the parent schema not carried: the parent writes no form |
| waiting.py | LiteratureWaiting | machinery | wait machinery; this episode does not wait |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait machinery; returned false |
| waiting.py | LiteratureTaskWaiting | machinery | wait/suspension machinery |
| waiting.py | LiteratureTaskWaiting.suspension_changed | machinery | suspension machinery |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | LiteratureYield.continuation_task | machinery | old continuation-task hook; returned None |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller (old returned None = the old runner default; now BoundedQualityYieldController with the projector's native_score_maximum, README 7b) |
