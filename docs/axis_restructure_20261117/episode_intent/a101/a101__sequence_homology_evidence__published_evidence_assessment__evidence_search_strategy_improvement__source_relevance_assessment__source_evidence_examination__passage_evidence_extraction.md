# passage_evidence_extraction (A101): intent carried over from commit 97308b94c

| | |
|---|---|
| Folder | `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction/` |
| Binding path | `sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction` |
| Old role name | `literature_targeted` |
| Commissioned by | `.../source_evidence_examination` (old role `literature_page`) |
| Children | none (a leaf) |
| Old files | 24 Python files, 1,262 lines, plus an empty `tests/__init__.py` |

## What this episode is for

Its goal, in its own words (`goal.py` with `source_contracts.py`):

> For A101, identify the actual sequence or region and its aligned homolog before using a source claim. Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database labels, and their applicability to the target distinct and source-grounded.
>
> Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.

In short: it is handed specific passages of one source and extracts what they actually say for the question, reading around them as needed, and never joining separate spans into one quotation.

## Task and instructions

One unit is one model-selected tool call. There is no reasoning-commit action in this episode, and it has no child to commission.

The instructions given to the model are composed in `task_instructions.py`, in this order:

1. The base literature investigation text `INSTRUCTIONS` ("You own an iterative scientific annotation improvement, not a tool itinerary. ...").
2. This episode's goal text above, appended.
3. The tool-knowledge text, when tool knowledge is in the context.
4. The launch-instruction text, when the launch-instruction library is in the context.
5. The paragraph on a pending child delivery (`redeliver_report`). It is in the file but cannot arise here, because this episode has no child.
6. Under the exchange protocol, the old history guidance is replaced by: use `request_context` exchanges for its own attempt metadata (these create no completed action or observation), and read earlier outcomes with the `episode.history` tool.

## What it reads from its parent's assignment

Assignment form (`from_parent.py`), version `reading_assignment_v1`, all fields required:

| Field | Meaning | Check |
|---|---|---|
| `version` | constant `reading_assignment_v1` | exact |
| `page` | the source being read, a full `page_assignment_v1`: `source_ref`, `representation`, `artifact_ref`, `question_context_refs`, `prior_delivery_refs` | source a source record in scope; artifact equal to the source's artifact for the representation (`literature_source_artifact_mismatch`) and in scope; every ref in scope |
| `selection.spans` | the passages to investigate: one or more windows, each `source_ref`, `representation`, `offset` (0 or more), `limit` (1 or more) | each window names the page's source (`literature_reading_source_mismatch`) and the page's representation (`literature_reading_representation_mismatch`), and starts at or before the artifact's size (`source_offset_out_of_bounds`) |

Checked against the parent as well (`from_parent_page.py`; of the four episodes read here only this leaf has one): the parent's own page assignment is validated again, and this episode's page source must be the parent's page source or derived from it through `parent_source_refs`; otherwise `literature_reading_outside_assigned_source`. A non-empty operation key is required.

It also reads from the commissioning request: the goal; the Store scope; the report contract (requested form and its purpose); `initial_report` (the starting report values); and the launch instructions selected for it.

## Children

None. `_CHILDREN['literature_targeted']` is empty, the folder has no to_child or from_child file, and `episode.py` has no child wiring.

## Decision state and what the model is shown

State the decision source keeps between decisions (`task_state.py`): the number of model calls made; the last feedback (why the last response or action was invalid or failed); the last own outcome and its decision index; the current report values (starting from the parent's `initial_report`); the record refs the current report is based on; the interpretation schema derived from the parent's report contract.

Shown to the model at every decision (`decision_state.py`, `decision_inputs.py`, `task_decision.py`):

- `goal`, `scope`, `working_state`, and `visible_record_refs` (every record ref found in the working state, the last outcome, visual evidence and the report forms, limited to the episode's scope).
- `current_credit`, `current_evidence_vector` (the credit view's components), `credit_binding` (what the credit measures), and `investigation_progress` (retained finding count, inactive dependencies, detail pages) when the episode has a receipt projection.
- `last_local_outcome` (a preview of its last own outcome) and `feedback`.
- `visual_evidence`: the pixels returned by its last completed `image.view`.
- `pending_work`, `report_deliveries`, and, when a child's return is undelivered, `pending_child_delivery`.
- `controller` (controller state) and `controller_binding` (the continuation settings in force); under the exchange protocol also a table of its own action yields.
- `time_accounting`: an elapsed-time view of the episode. It is information only; nothing in these files stops on it.
- `tools` (the catalog below), `tool_knowledge`, `job_episode_options`, `child_options` (text describing the children it may commission).
- `available_report_facts` (`credit` as a number, the other fact sources as reference arrays), `requested_report_purpose` and `requested_form` (the parent's report contract), `current_report_update`, `current_report_basis_refs`, and the line "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment."
- The reports of its children so far, and the annotation context for the scope (proposed annotations).
- `completed_action_reports` (what its completed actions returned), and `restored_episode_history` when the provider conversation is fresh.
- `resource_context`, `shared_information_context`, `launch_instruction_library`, `selected_launch_instructions`, and, when configured, `execution_expectations`, `job_execution_options`, `resource_tool_estimates`, `native_execution_expectations`, `native_event_targets`, `requested_action_history`.
- This episode's own summary, described next.

For this leaf the child-related entries above (child options, child reports, pending child delivery) are always empty or absent.

This episode's own summary (`internal_summary.py`), added to every decision:

- `literature_assignment`: the validated reading assignment (the page and the selected spans).
- `literature_source_custody`: one row for the page's source: `source_ref`, `version`, `artifact_ref`, `text_ref`, `stdout_ref`, `stderr_ref`, `parent_source_refs`.
- `own_literature_outcomes`: the first 8 (`outcome_page_size`) of its own acquisition and read outcomes.
- `literature_history_meaning`: "Read exact prior outcomes through episode.history; source discovery alone is not A101 evidence."

## Tools it offers

Action kinds: `source_operations.py` lists `tool`, `child`, `redeliver_report`, but only `tool` can be used, because the episode has no child.

Tools are the ones below that the scope's tool catalog actually has:

- **Access (15):** `state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`, `source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`, `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`, `execution.estimate`.
- **No acquisition tools.** This episode cannot search or fetch new sources.

Adjustments: `execution.estimate` is offered only for `source.xlsx.sheets` and `source.xlsx.rows` (and dropped when neither branch exists); every input schema is passed through `source_location_inputs`. The `public.ncbi.search` adjustment is still in the file but can never apply.

**Held to the assigned source, not to the assigned spans.** Any tool call that names a source must name the page's source or a source derived from it through `parent_source_refs`; otherwise it is rejected with `literature_reading_outside_assigned_source`. Within that source it may read any window, which is what lets it "read neighboring context, qualifications or alternative passages".

Execution: the arguments are admitted against the offered schema. A contract error at that point (a tool that is not offered, `tool_not_available_to_a101_literature_role`, or a source outside the assignment) is returned as an `invalid` outcome with `arguments_or_reference` feedback, and that outcome still enters the iterator. `source.locate`, `source.sequence.scan`, `source.sequence.references` and `source.experimental.records` are authorized over the record refs the episode has received.

## How its credit is counted

- Credit kind is `scientific` (`credit.py`). The value is the axis's scientific credit view for this episode (`services.scientific_credit(context, receiver_selection)`); the episode has no projector and no score judgments of its own (`scientific_records.py`: none, and completing one raises `a101_automatic_judgment_unavailable`).
- After every own action whose outcome counts as observed, the credit view is read again and its `credit` is recorded with the action and passed to the controller as that unit's input (`task.py`). A unit that fails while executing is recorded as a `failed` outcome and still enters the iterator with the credit measured after it (`task_state.py`). A response that fails admission creates no unit.
- Nothing in these files bounds, clamps or rescales the credit.
- What a child's return does to the credit is not in these files: the from_child file only records which record refs the child's report delivered; the credit is whatever the axis credit view says afterwards.

## Continuation

- `yield_estimator.py` chooses nothing: `continuation_task` and `yield_controller` both return None, so the old runner's default controller applied. The only traces of it here are `self.workflow.controller_binding` and `_category_yield_parameters(...)`, both old shared code that was not read.
- The episode's files therefore do not say which of the three estimators (accumulation, bounded quality, completion with a target) it used, nor any setting for it. This has to be decided for this episode and supplied through the `continuation` settings keyed by its binding path. The only evidence in its own files is that its credit is the accumulating axis scientific credit.
- The only setting the episode owns is `outcome_page_size` = 8 (`configuration.py`).
- Waiting is not supported (`waiting.py`).

## What it reports to its parent

- With a report contract (the normal case): the parent's requested form, filled from the model's latest admitted `report_update` (its interpretations) together with the report facts, saved once and returned as `{'form': ...}` (`report_delivery.py`). The form's fields are whatever the parent asked for when it commissioned the episode; the parent composed that form from its own model's selection.
- This episode contributes no report facts of its own (`to_parent.py`: `fact_sources`, `facts`, `current_report_facts` are all empty).
- Before delivery the report is validated: the assignment must still be valid and every reference in the form must resolve in this episode's context.
- Without a report contract: `{'credit': <current credit>, 'pending_handles': ...}`.

## How it differs from its relatives

- **Own to this episode:** the goal sentence about source-bound passages and never concatenating spans; the assignment `reading_assignment_v1` with its selected spans and their three checks; `from_parent_page.py`, which re-validates the parent's page (of the four episodes read here only this one has that file; the folder listing shows its two siblings each have one too); being a leaf.
- **Different from its parent `source_evidence_examination`:** no children; the assignment wraps the page and adds spans; its page is checked against the parent's page. The tools and the source restriction are the same.
- **Different from `source_relevance_assessment` and `evidence_search_strategy_improvement`:** no acquisition tools; held to one source.
- **Its siblings** `table_evidence_extraction` and `source_coverage_improvement` were not read (other folders). From this folder's `source_contracts.py`: the table sibling's goal is about a selected table or sheet (rows, headers, conditions, footnotes), and an unused `_TABLE` schema here is presumably its selection; the ordered sibling's goal is reading the source in document order with byte continuations. This episode's selection is a list of spans instead.
- **Identical in all four folders apart from the role name and module path:** `binding_record.py`, `configuration.py`, `credit.py`, `decision_inputs.py`, `decision_state.py`, `received_evidence.py`, `report_delivery.py`, `scientific_records.py`, `source_contracts.py`, `source_references.py`, `task.py`, `task_decision.py`, `task_instructions.py`, `task_state.py`, `to_parent.py`, `waiting.py`, `yield_estimator.py`. Credit, continuation, report delivery, decision state and the decision loop are therefore the same text in the four.

## File by file

Read at commit `97308b94c`, only the files directly in this episode's folder. `tests/` holds only an empty `__init__.py`. Counts are occurrences in the file; the same counts are in `runs/carry_over/calls/a101_03.tsv`, one row per name.

| Old file | Lines | This episode's own intent in it | Old-runner names it uses (×uses) |
|---|---|---|---|
| `binding_record.py` | 8 | Binding record: version `literature_episode_binding_v1`, binding id = this episode's path, configuration `outcome_page_size`. | **defined for the old runner to call:** `as_record` |
| `configuration.py` | 12 | One setting, `outcome_page_size` = 8 (a positive integer, else `positive_a101_literature_outcome_page_size_required`): how many of its own outcomes are shown per decision. `_contract_information_profile` and `reference_parent_sources` are fixed to None (no contract-information profile). | **per-axis services provider:** `services×1` |
| `credit.py` | 15 | Credit kind `scientific`. The credit is the axis scientific credit view for this episode and receiver selection (`services.scientific_credit`). No projector of its own. Nothing is bounded or rescaled. | **BindingContext (context / parent):** `role×2`<br>**per-axis services provider:** `services.scientific_credit×1`<br>**defined for the old runner to call:** `credit_kind, credit_projector, credit_view` |
| `decision_inputs.py` | 76 | No episode-specific text. Adds to the decision context: resource context, shared-information context, launch-instruction library and the launch instructions selected in the assignment, child options text, completed-action reports, requested-action history (HPC context only), pending work, execution expectations and job execution options, resource estimates, native event targets. Same text in all four episodes apart from the module path. | **self.workflow / workflow:** `available_child_roles×1, binding_context×2, episode_bindings.initial_decision_context×1, execution_expectations×1, job_episodes×2, job_episodes.jobs×1, job_episodes.prospective_execution_classes×1, job_episodes.prospective_execution_options×1, launch_instructions.context×1, launch_instructions.materialize×1, native_estimation_context×1, native_event_information×1, native_event_information.read×1, pending_work×1, resource_context×1, resource_estimator×2, resource_estimator.estimate_context×2, shared_information_context×1, store×2`<br>**old request / view members:** `EpisodeRequest.message.as_record×2, EpisodeRequest.message[episode_assignment]×1, EpisodeRequest.message[job_assignment]×1`<br>**from root.a101.runtime:** `Mapping×1, child_option_information×1`<br>**from root.a101.episode_work_report:** `completed_action_reports×2, requested_action_history×2`<br>**from root.a101.hpc_prompt:** `is_hpc_context×1`<br>**from root.a101.library.live_runtime_functions:** `bind_functions×1`<br>**from root.a101:** `runtime×1`<br>**rebinding:** `_bind_original_task_runtime_providers` (methods rebound to the old runtime module globals)<br>**defined for the old runner to call:** `decision_inputs` |
| `decision_state.py` | 60 | What the model is shown at each decision (listed in the section above). Contains a root-only branch (`annotation_axis_credit`) that never applies to this episode. Same text in all four episodes apart from the module path. | **self.workflow / workflow:** `annotation_context×1, binding_context×1, catalog×1, controller_binding×1, delivery_status×1, extra_report_sources×1, is_scientific_source×1, job_episode_options×1, journal.db×1, journal.elapsed_view×1, journal.row×1, knowledge.context×1, local_outcome_preview×1, pending_work×1, receipt_projection×1, run_id×1, source_credit_binding×1, source_credit_view×1, specialist×1, specialist().decision_context×1, store×1, store.get×1, store.read_snapshot×1, tools×1, working_state×1`<br>**journal tables:** `runtime_actions×2`<br>**old request / view members:** `EpisodeRequest.goal.as_record×1, EpisodeRequest.report_contract×2, EpisodeRequest.report_contract.decision×1, EpisodeRequest.report_contract.schema×1, SourceView.child_reports×2, SourceView.controller_state×1, SourceView.model_inputs×1`<br>**from root.a101.runtime:** `FACT_MEANINGS×1, FACT_SOURCES×1, Mapping×3, _plain×2, _references_in×1, json×2`<br>**from root.a101.library.live_runtime_functions:** `bind_functions×1`<br>**from root.a101:** `runtime×1`<br>**rebinding:** `_bind_original_task_runtime_providers` (methods rebound to the old runtime module globals)<br>**defined for the old runner to call:** `decision_state` |
| `episode.py` | 60 | Joins the parts. Old role `literature_targeted`; `binding_path` and `commissioning_parent` (`.../source_evidence_examination`); not an entry role; a leaf: no children, no to_child or from_child wiring; adds `OriginalPageAssignment` (from_parent_page.py); prompt renderer `render_literature_source_prompt`; no contract-information profile. | **BindingContext (context / parent):** `path×1, role×4`<br>**from root.a101.library.literature_source_prompt:** `render_literature_source_prompt×1`<br>**defined for the old runner to call:** `allowed_children, binding_path, child_roles, commissioning_parent, context_hook_applies, contract_information_configuration, contract_information_profile, decision_prompt_renderer, decision_source_type, entry_roles, roles` |
| `from_parent_page.py` | 17 | Of the four episodes read here only this leaf has it (its two siblings' folders list one too): re-validates the commissioning parent's own page assignment (`page_assignment_v1`, source, artifact, refs) so the child's page can be checked against it. | **BindingContext (context / parent):** `assignment×1, scope×1`<br>**via .source_contracts from root.a101.domain:** `ContractError×0, obj×0, validate_schema×1`<br>**via .source_contracts from root.a101.communication:** `plain×1` |
| `from_parent.py` | 54 | Assignment `reading_assignment_v1`: `page` (a `page_assignment_v1`) and `selection.spans` (at least one window: source_ref, representation, offset, limit). The page is validated as in the parent; every span must name the page's source (`literature_reading_source_mismatch`) and representation (`literature_reading_representation_mismatch`) and start at or before the artifact's size (`source_offset_out_of_bounds`). When the parent is a page examination, the child's page source must lie within the parent's page source (`literature_reading_outside_assigned_source`). A non-empty operation key is required. | **BindingContext (context / parent):** `role×1`<br>**per-axis services provider:** `services.read_record×1`<br>**via .source_contracts from root.a101.domain:** `ContractError×6, obj×2, validate_schema×1`<br>**via .source_contracts from root.a101.communication:** `plain×2`<br>**defined for the old runner to call:** `assignment_schema, child_assignment_schema, prepare_assignment` |
| `goal.py` | 9 | The A101 literature sentence plus this episode's own goal sentence, "Investigate the supplied source-bound passages for the assigned question ..." (quoted in full above). | **BindingContext (context / parent):** `role×1`<br>**defined for the old runner to call:** `instructions` |
| `__init__.py` | 0 | Empty. | none |
| `internal_summary.py` | 19 | Shown at each decision: the validated reading assignment (page and spans); custody of the page's source (version, artifact_ref, text_ref, stdout_ref, stderr_ref, parent_source_refs); the first `outcome_page_size` of its own acquisition and read outcomes; the line "Read exact prior outcomes through episode.history; source discovery alone is not A101 evidence." | **BindingContext (context / parent):** `assignment×1, episode_id×1, role×1, scope×2`<br>**per-axis services provider:** `services.own_outcomes×1`<br>**via .source_contracts from root.a101.communication:** `plain×1`<br>**defined for the old runner to call:** `decision_context, initial_decision_context` |
| `received_evidence.py` | 20 | This episode adds no received-report sources, facts, references or evidence tokens of its own and does not validate a received child report beyond its typed form (every hook returns empty or None). | **defined for the old runner to call:** `received_evidence_tokens, received_form_references, received_report_facts, received_report_sources, validate_received_report` |
| `report_delivery.py` | 34 | The final report: with a report contract, the parent's requested form filled from the model's current report update (its interpretations) and the report facts (`form_with_facts`), saved once and returned as `{'form': ...}`; without a contract, `{'credit', 'pending_handles'}` plus current report facts. Same text in all four episodes. | **self.workflow / workflow:** `binding_context×1, episode_bindings.current_report_facts×1, facts×1, journal.row×1, journal.save×1, pending_handles×1, release×2, source_credit_view×1`<br>**journal tables:** `runtime_forms×2`<br>**old request / view members:** `EpisodeRequest.report_contract×1, EpisodeRequest.report_contract.schema×1`<br>**from root.a101.runtime:** `Record×2, _json×2, form_with_facts×1, json×1`<br>**from root.a101.library.live_runtime_functions:** `bind_functions×1`<br>**from root.a101:** `runtime×1`<br>**rebinding:** `_bind_original_task_runtime_providers` (methods rebound to the old runtime module globals)<br>**defined for the old runner to call:** `finish` |
| `scientific_records.py` | 11 | No automatic score judgments (`[]`); completing one raises `a101_automatic_judgment_unavailable`. | **via .source_contracts from root.a101.domain:** `ContractError×1`<br>**defined for the old runner to call:** `automatic_score_judgments, complete_score_judgment` |
| `source_contracts.py` | 26 | The literature family's constants, copied identically into each of the four folders: version `literature_episode_binding_v1`; the seven old role names; schemas `_REFERENCES`, `_REPRESENTATION` (text / original / stdout / stderr), `_WINDOW` (source_ref, representation, offset, limit), `_TABLE`, `_PAGE` (`page_assignment_v1`); the child table `_CHILDREN`; tool lists `_ACCESS_TOOLS` (15), `_ACQUISITION_TOOLS` (7), `_READ_TOOLS` (8); `_ROLE_INSTRUCTIONS` for all seven roles. This episode uses only its own entries (quoted in the sections above); the other roles' entries are its relatives' text. | **from root.a101.communication:** `ReportBoundaryError×0, plain×0, validate_form×0`<br>**from root.a101.composition_information:** `CONTRACT_INFORMATION_PROFILE×0`<br>**from root.a101.domain:** `ContractError×0, REF×5, identity×2, obj×4, source_location_inputs×0, validate_schema×0`<br>**from root.a101.episode_bindings:** `reference_in_context×0` |
| `source_operations.py` | 65 | Action kinds offered: tool, child, redeliver_report (the last two are listed although this episode has no child). No reasoning action (`a101_literature_reasoning_not_commissioned`). Tools: the access list only (no acquisition tools); `execution.estimate` limited to `source.xlsx.sheets` / `source.xlsx.rows`; inputs projected through `source_location_inputs`. Every tool call naming a source must stay within the assigned page's source, else `literature_reading_outside_assigned_source`; the assigned spans do not restrict which windows it may read. Invalid arguments return an `invalid` outcome with `arguments_or_reference` feedback. Source-locating tools are authorized over the episode's received record refs. | **BindingContext (context / parent):** `assignment×1, received_record_refs×1, role×2, scope×5`<br>**per-axis services provider:** `services.execute_tool×1, services.tool_catalog×1`<br>**via .source_contracts from root.a101.domain:** `ContractError×4, identity×1, source_location_inputs×1, validate_schema×1`<br>**via .source_contracts from root.a101.communication:** `plain×3`<br>**defined for the old runner to call:** `catalog, execute, execute_reasoning, permitted_common_actions, reasoning_action_schema, reasoning_has_task_content` |
| `source_references.py` | 35 | `_require`: a reference must be in scope (and in the named namespace), else `literature_reference_unavailable`. `_artifact`: the artifact of a source for a representation (original: `artifact_ref`; text: `text_ref` or `artifact_ref`; otherwise `<representation>_ref`). `_within_source`: a source lies within a root source through `parent_source_refs`. `resolve`: report reference resolution in this episode's context. Same text in all four episodes. | **BindingContext (context / parent):** `role×1`<br>**per-axis services provider:** `services×1, services.read_record×1, services.reference_in_scope×1`<br>**via .source_contracts from root.a101.domain:** `ContractError×1`<br>**via .source_contracts from root.a101.episode_bindings:** `reference_in_context×1`<br>**defined for the old runner to call:** `resolve` |
| `task_decision.py` | 347 | No episode-specific text. The recorded model call; the optional `request_context` / `select_action` exchange (lookups of child options, composition information and the episode's own earlier attempts) that creates no unit and no observation; the model is shown a table of its own action yields; the prompt is rendered by the episode's `decision_prompt_renderer`. Same text in all four episodes. | **self.workflow / workflow:** `contract_information_profile×1, contract_information_reply×1, controller_binding×1, decision_exchanges×1, decision_exchanges.measure×1, decision_exchanges.prepare×1, decision_exchanges.resolve_lookup×1, decision_exchanges.respond×1, decision_exchanges.rows×4, decision_protocol×3, execute×1, freeze_contract_information×1, freeze_literature_numerical_contracts×1, history_preview×1, journal×2, journal.measure×2, journal.row×2, journal.save×4, numerical_contracts×1, provider×3, provider.complete×1, receipts×2, receipts.receive×2, run_id×1, services.decision_exchange_instructions×1, specialist×2, store×1, store.get×1, uses_received_record_context×2, validate_contract_information×5`<br>**journal tables:** `runtime_model_calls×8`<br>**from root.a101.runtime:** `CONTRACT_INFORMATION_OPERATIONS×1, DECISION_CONTEXT_VERSION×2, DECISION_EXCHANGE_PROTOCOL×5, Draft202012Validator×1, Mapping×3, ValidationError×5, WorkflowError×14, _ASSIGNMENT_TRANSPORT×1, _action_generation_schema×2, _category_yield_parameters×1, _digest×1, _json×14, _object×3, _plain×2, _recorded_action_generation_schema×1, _recorded_assignment_transport×1, _references_in×1, apply_state_frame×1, child_option_information×1, composition_lookup_schema×2, instructional_model_context×4, is_contract_information×1, json×3, lookup_attempts×1, model_snapshot×2, requested_contract_information×2, schema_failure_diagnostic×2, sqlite3×1, state_frame×1, yield_table×1`<br>**from root.a101.providers:** `_ORIGINAL_MODEL_COMPLETE×1, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION×1, _ORIGINAL_MODEL_INSTANCE_DICT×2, _ORIGINAL_DECLARED_PRESENTATION×1`<br>**from root.providers:** `_ORIGINAL_MODEL_COMPLETE×1, _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION×2, _ORIGINAL_MODEL_COMPLETE_SERIAL×1, _ORIGINAL_MODEL_INSTANCE_DICT×2, _ORIGINAL_MODEL_SESSION_TYPE×3, _ORIGINAL_SESSION_COMPLETE×1, _ORIGINAL_SESSION_PRESENTATION×1`<br>**from root.a101.library.live_runtime_functions:** `bind_functions×1`<br>**from root.a101:** `runtime×1`<br>**rebinding:** `_bind_original_task_runtime_providers` (methods rebound to the old runtime module globals)<br>**defined for the old runner to call:** `call, conversation_key, decision_completion, exchange_decision, exchange_response, exchange_schema, interpretation_context, validate_contract_exchange_history, validate_contract_exchange_request` |
| `task_instructions.py` | 18 | Instruction composition: base `INSTRUCTIONS` (literature investigation prompt) + this episode's goal text (goal.py, appended) + tool-knowledge text + launch-instruction text + the paragraph on repairing a pending child delivery with `redeliver_report`. Under the exchange protocol the old history guidance is replaced by the `request_context` / `episode.history` paragraph. Same text in all four episodes. | **self.workflow / workflow:** `binding_context×1, decision_protocol×1, knowledge.instructions×1, launch_instructions.instructions×1, specialist×1, specialist().instructions×1, specialist().replaces_default_instructions×1`<br>**from root.a101.library.literature_investigation_prompt:** `DECISION_EXCHANGE_PROTOCOL×1, REASONING_COMMIT_REQUIREMENT×0, INSTRUCTIONS×4`<br>**defined for the old runner to call:** `instructions` |
| `task.py` | 214 | No episode-specific text. The decision loop: ask the model; admit the selection (an invalid one gives feedback and creates no unit); admit the report update against the interpretation schema (an invalid update gives `report_format` feedback while the selected work proceeds); execute the tool; record the outcome, including an invalid or failed one, and measure credit after it; a model call failure ends the source as `source_failed`. Carries feedback branches for tools and children this episode does not have (`reads.map`, `bvbrc_minhash_result_selector_v2`, `component_native_return_channels_required`). Same text in all four episodes. | **self.workflow / workflow:** `action_schema×1, automatic_score_updates×1, completed_unit×3, completions.slot×2, completions.stage×1, controller_value×2, decision_exchanges×2, decision_exchanges.rows×1, delivery_resolution_inputs×1, execute×1, execution_binding×7, inprocess_replay×2, inprocess_replay.capture×1, inprocess_replay.unit×1, journal×1, journal.measure×1, journal.row×7, journal.save×3, next_return×1, pending_work×1, receive_native_outcome×1, receive_outcome×1, resolve_pending_deliveries×1, resolver×1, retain_shared_grading_results×1, run_id×2, selected×3, services.instructions×1, source_credit_view×1, store×1, store.transaction×6, validate_report×1`<br>**journal tables:** `runtime_actions×8, runtime_episodes×1, runtime_model_calls×2`<br>**old request / view members:** `EpisodeRequest.message.as_record×1, EpisodeRequest.message[job_assignment]×1, execution_context._ready_owned_child×1, SourceView.units_consumed×4`<br>**from root.a101.runtime:** `ActionFailure×1, ContractError×2, ContractInformationError×1, Draft202012Validator×2, EventTargetError×1, Mapping×7, ReportBoundaryError×1, ReportRedelivery×2, SourceEnd×2, ValidationError×3, WorkflowError×2, _decode_recorded_action_response×1, _json×5, _plain×1, _wait_target_feedback×1, inspect×1, json×8, nullcontext×5, observes_action_outcome×1, schema_failure_diagnostic×1, validate_form×1`<br>**from root.a101.providers:** `ModelCallError×1`<br>**from root.a101.episode_source_failure:** `record_source_failure×1`<br>**from root.a101.library.read_mapping_values:** `parameter_schema_failure×1`<br>**from root.a101.library.live_runtime_functions:** `bind_functions×1`<br>**from root.a101:** `runtime×1`<br>**rebinding:** `_bind_original_task_runtime_providers` (methods rebound to the old runtime module globals)<br>**defined for the old runner to call:** `apply_response, execute, instruction_composer, instructions, next` |
| `task_state.py` | 115 | The decision source's state: call count, feedback, last outcome and its index, report values (starting from the parent's `initial_report`), report basis refs, and the interpretation schema taken from the report contract (an empty object without one). A failed tool or reason unit is recorded as a `failed` outcome and still enters the iterator with its credit. The rest is old checkpoint and restore machinery. Same text in all four episodes. | **self.workflow / workflow:** `archive.store×1, completions.checkpoint_source×1, completions.record_decision_effect×1, completions.restore_source×1, completions.stage×1, context×1, controller_value×1, execution_binding×4, grains×1, inprocess_replay×5, inprocess_replay.capture×1, inprocess_replay.unfinished×1, journal.row×3, journal.save×2, progress_provider×1, progress_provider.flush_notifications×1, recover_commissions×1, run_id×1, source_credit_view×1, store×1, store.transaction×1`<br>**journal tables:** `runtime_actions×5`<br>**old request / view members:** `EpisodeRequest.message.as_record×1, EpisodeRequest.message[initial_report]×1, EpisodeRequest.report_contract×1, EpisodeRequest.report_contract.schema×1`<br>**from root.a101.runtime:** `ActionLeaf×1, EFFECT_VERSION×1, Episode×1, Record×1, _json×2, _object×1, _plain×1, interpretation_schema×1, json×4`<br>**from root.a101.episode_source_failure:** `record_source_failure×1`<br>**from root.a101.library.live_runtime_functions:** `bind_functions×1`<br>**from root.a101:** `runtime×1`<br>**rebinding:** `_bind_original_task_runtime_providers` (methods rebound to the old runtime module globals)<br>**defined for the old runner to call:** `bind_execution_context, checkpoint, record_effect, record_execution_failure, restore, restore_checkpoint` |
| `to_parent.py` | 21 | No report fact sources and no facts of its own (`{}`). Report validation: the assignment is still valid, the form is valid against the parent's schema with references resolved in this episode's context, then the (no-op) received-report validation. | **BindingContext (context / parent):** `assignment×1, role×2, scope×1`<br>**via .source_contracts from root.a101.communication:** `validate_form×1`<br>**defined for the old runner to call:** `current_report_facts, facts, fact_sources, validate_report` |
| `waiting.py` | 15 | Waiting is not supported (`supports_wait` is False). The source forwards a suspension condition to the execution backend. | **self.workflow / workflow:** `execution_backend.set_suspension×1, execution_handle×2`<br>**defined for the old runner to call:** `supports_wait, suspension_changed` |
| `yield_estimator.py` | 11 | No continuation task and no yield controller of its own (both return None): continuation was left to the old runner's default. | **BindingContext (context / parent):** `role×2`<br>**defined for the old runner to call:** `continuation_task, yield_controller` |

## Old-runner machinery to replace

- **Every hook takes an old role name.** Each binding method starts with `self._role(context.role)`, and children are looked up by old role name (`literature_strategy`, `literature_search`, `literature_page`, `literature_table`, `literature_ordered`, `literature_targeted`). The new contract names bindings by path and children by slot.
- **`self.workflow.*`** is used in `decision_inputs.py`, `decision_state.py`, `report_delivery.py`, `task.py`, `task_decision.py`, `task_instructions.py`, `task_state.py`, `waiting.py` and the to_child / from_child files (as the `workflow` argument).
- **`BindingContext`** (`context.role`, `.assignment`, `.scope`, `.path`, `.episode_id`, `.received_record_refs`; `parent.role`, `.assignment`, `.scope`) is the argument of every binding hook.
- **Per-axis services provider** (`self.services`): `scientific_credit`, `own_outcomes`, `tool_catalog`, `execute_tool`, `reference_in_scope`, `read_record`.
- **Journal tables read or written directly:** `runtime_actions`, `runtime_model_calls`, `runtime_episodes`, `runtime_forms`, `runtime_report_attempts`.
- **Module rebinding:** six files end by rebinding their methods into the old `root.a101.runtime` module's globals (`_bind_original_task_runtime_providers` with `bind_functions`).
- **Provider identity checks:** `task_decision.py` `decision_completion` compares the provider against `_ORIGINAL_MODEL_*` objects from `root.a101.providers` and the old shared `root.providers` before calling it with the literature prompt renderer.

Names from the deleted runner whose definitions a search of today's packages no longer finds: `reference_in_context`, `child_option_information`, `render_literature_source_prompt`, `record_source_failure`, `completed_action_reports`, `requested_action_history`, `is_hpc_context`, `child_role_for_delivery`, `EpisodeReturnRecords`, `bind_functions`, `_references_in`, `yield_table`, `lookup_attempts`, `state_frame`, `apply_state_frame`, `model_snapshot`, `instructional_model_context`, `composition_lookup_schema`, `observes_action_outcome`, `_action_generation_schema`, `WorkflowError`, `CONTRACT_INFORMATION_PROFILE`.

Library pieces these files use that a definition search finds today (not checked to be the same code):

| Name | Found in |
|---|---|
| `obj`, `validate_schema`, `identity`, `source_location_inputs`, `REF` | `gene_annotation_episode/episodic_workflow/episode_support/records/sequence_homology_evidence/domain.py` |
| `ContractError` | `gene_annotation_episode/domain.py` |
| `plain`, `validate_form`, `interpretation_schema`, `form_with_facts`, `ReportBoundaryError` | `gene_annotation_episode/episodic_workflow/episode_support/forms/sequence_homology_evidence/communication.py` |
| `schema_failure_diagnostic`, `parse_json_object` | `gene_annotation_episode/episodic_workflow/episode_support/forms/sequence_homology_evidence/boundary_validation.py` |
| `INSTRUCTIONS`, `DECISION_EXCHANGE_PROTOCOL`, `REASONING_COMMIT_REQUIREMENT` | `gene_annotation_episode/episodic_workflow/episode_support/literature/prompts/sequence_homology_evidence/literature_investigation_prompt.py` |
| `parameter_schema_failure` | `gene_annotation_episode/episodic_workflow/episode_support/records/read_mapping_values.py` |
| `ModelCallError` | `gene_annotation_episode/model_provider.py` |
| `EventTargetError` | `method_loop/durable.py` |

## Carried over

Every old function, class and method of this episode at 97308b94c (`runs/carry_over/functions/a101__sequence_homology_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination__passage_evidence_extraction.tsv`), and where it is now. `episode function` rows name the new file and member; `machinery` rows give the reason.

| old file | name | kind | new place or reason |
|---|---|---|---|
| binding_record.py | LiteratureBindingRecord | machinery | binding record class (version, binding id, configuration): old runner's binding_record; the system records the binding |
| binding_record.py | LiteratureBindingRecord.as_record | machinery | the binding's own as_record(): deleted (README 3e) |
| configuration.py | LiteratureConfiguration | episode function | settings: outcome_page_size -> messages/internal_summary.py OUTCOME_PAGE_SIZE = 8; the services provider, contract-information profile and reference_parent_sources (fixed None) are old-runner wiring and not carried |
| configuration.py | LiteratureConfiguration.__init__ | episode function | messages/internal_summary.py OUTCOME_PAGE_SIZE (value 8; the positive-integer check is on a constant and not carried); services/contract-information attributes: machinery |
| credit.py | LiteratureCredit | episode function | credit.py credit and A101SequenceCredit (private copy of the head's projector at 97308b94c, over library NativeCorrespondenceScoring.read_details) |
| credit.py | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d) |
| credit.py | LiteratureCredit.credit_view | episode function | credit.py credit: A101SequenceCredit().read_details(records, summary['scope'], known_record_refs=records.refs(), details_limit=0, details_offset=0)['credit'] (library read_details not carried: blocked) |
| credit.py | LiteratureCredit.credit_projector | machinery | returned None (no projector of its own); nothing to carry |
| decision_inputs.py | LiteratureDecisionInputs | episode function | task.py decide (context additions) |
| decision_inputs.py | LiteratureDecisionInputs.decision_inputs | episode function | task.py decide: feedback, action_yields (summary), tool_knowledge (via extend_context); resource/shared-information/launch-instruction/job/child/pending-work/native-event/requested-action-history contexts are not carried (no such tool or child in this episode; pending work and child options are machinery) |
| decision_inputs.py | _bind_original_task_runtime_providers | machinery | provider patching |
| decision_state.py | LiteratureDecisionState | episode function | task.py decide + messages/internal_summary.py |
| decision_state.py | LiteratureDecisionState.decision_state | episode function | task.py decide (goal, scope, tools, time_accounting, current_report_update) and messages/internal_summary.py; credit view, controller binding, journal views, pending work, delivery status, child reports: machinery or not carried (credit view: see credit) |
| decision_state.py | _bind_original_task_runtime_providers | machinery | provider patching |
| episode.py | LiteratureEpisode | episode function | episode.py PassageEvidenceExtraction |
| episode.py | LiteratureEpisode.contract_information_configuration | machinery | contract-information profile (old shared root content freezing) |
| episode.py | LiteratureEpisode.contract_information_profile | machinery | contract-information profile (old shared root content freezing) |
| episode.py | LiteratureEpisode._role | machinery | old role-name check; each role is its own episode |
| episode.py | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS = {} |
| episode.py | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS = {} |
| episode.py | LiteratureEpisode.context_hook_applies | machinery | old hook dispatch by role |
| from_parent.py | LiteratureAssignment | episode function | messages/read_from_parent.py |
| from_parent.py | LiteratureAssignment.child_assignment_schema | machinery | the parent's view of the child's schema: the parent writes its own text (README 3b C3) |
| from_parent.py | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (version, page, selection, plus new fields scope, received_record_refs) |
| from_parent.py | LiteratureAssignment._validate_page | episode function | not carried: it checks the commission against the Store (page artifact equals the source's artifact for the representation, refs in scope); a wrong commission fails (rule 1) -- listed in unplaced_old_functions |
| from_parent.py | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py read_from_parent: spans non-empty, each span names the page source and representation (the checks that need no Store); the source_offset_out_of_bounds check needs the artifact size from the Store and is not carried (unplaced) |
| from_parent.py | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; the operation-key check is machinery; the within-parent-page check needs the parent's assignment and is not carried (unplaced) |
| from_parent_page.py | OriginalPageAssignment | episode function | not carried (unplaced): re-validates the parent's own page assignment, which a child cannot read (README 5 item 14) |
| from_parent_page.py | OriginalPageAssignment._parent_page_schema | episode function | not carried (unplaced): see OriginalPageAssignment |
| from_parent_page.py | OriginalPageAssignment._validate_parent_page | episode function | not carried (unplaced): see OriginalPageAssignment |
| goal.py | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | LiteratureGoal.instructions | episode function | goal.py GOAL (the A101 sentence plus this episode's own goal text); task.py instructions appends it |
| internal_summary.py | LiteratureSummary | episode function | messages/internal_summary.py |
| internal_summary.py | LiteratureSummary.initial_decision_context | episode function | messages/internal_summary.py (returned {}: nothing to carry) |
| internal_summary.py | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary: literature_assignment, literature_source_custody (view.records.get), own_literature_outcomes (outcome_page over view.outcomes, 8 per page), literature_history_meaning |
| received_evidence.py | LiteratureReceivedEvidence | machinery | received-report hooks (all empty): receipts/child-return machinery |
| received_evidence.py | LiteratureReceivedEvidence.received_report_sources | machinery | received-report hook returning empty/None: receipt and child-return machinery (no child here) |
| received_evidence.py | LiteratureReceivedEvidence.received_report_facts | machinery | received-report hook returning empty/None: receipt and child-return machinery (no child here) |
| received_evidence.py | LiteratureReceivedEvidence.received_form_references | machinery | received-report hook returning empty/None: receipt and child-return machinery (no child here) |
| received_evidence.py | LiteratureReceivedEvidence.received_evidence_tokens | machinery | received-report hook returning empty/None: receipt and child-return machinery (no child here) |
| received_evidence.py | LiteratureReceivedEvidence.validate_received_report | machinery | received-report hook returning empty/None: receipt and child-return machinery (no child here) |
| report_delivery.py | LiteratureReportDelivery | machinery | report delivery: saved runtime_forms, form_with_facts, release; the report is messages/final_to_parent.py final_to_parent (system-run) |
| report_delivery.py | LiteratureReportDelivery.finish | machinery | report delivery: saved runtime_forms, form_with_facts, release; the report is messages/final_to_parent.py final_to_parent (system-run) |
| report_delivery.py | _bind_original_task_runtime_providers | machinery | provider patching |
| scientific_records.py | LiteratureScientificRecords | machinery | old runner score-judgment hook (returned no judgments / raised a101_automatic_judgment_unavailable); this episode has none |
| scientific_records.py | LiteratureScientificRecords.automatic_score_judgments | machinery | old runner score-judgment hook (returned no judgments / raised a101_automatic_judgment_unavailable); this episode has none |
| scientific_records.py | LiteratureScientificRecords.complete_score_judgment | machinery | old runner score-judgment hook (returned no judgments / raised a101_automatic_judgment_unavailable); this episode has none |
| source_operations.py | LiteratureOperations | episode function | task.py (catalog, run_access_tool, admitted) |
| source_operations.py | LiteratureOperations.permitted_common_actions | machinery | action kinds tool/child/redeliver_report: no child, no redelivery; the unit kinds are the declared tools |
| source_operations.py | LiteratureOperations.reasoning_action_schema | machinery | returned None: no reasoning commit in this episode |
| source_operations.py | LiteratureOperations.reasoning_has_task_content | machinery | returned False: no reasoning commit in this episode |
| source_operations.py | LiteratureOperations.execute_reasoning | machinery | raised a101_literature_reasoning_not_commissioned: no reasoning action exists here |
| source_operations.py | LiteratureOperations.catalog | episode function | task.py DESCRIPTIONS, INPUT_SCHEMAS, offered, catalog (the 15 access tools; execution.estimate only with timing statistics) |
| source_operations.py | LiteratureOperations.execute | episode function | task.py run_access_tool and the 15 access tools (invalid outcome for a contract error; held-record authorization via ctx.store.refs()) |
| source_operations.py | LiteratureOperations._tool_arguments | episode function | task.py admitted, within_source |
| source_references.py | LiteratureReferences | episode function | task.py within_source; library records/received_records.py read_record_in_scope |
| source_references.py | LiteratureReferences._require | episode function | already in library: records/received_records.py read_record_in_scope (called in task.py) |
| source_references.py | LiteratureReferences._artifact | episode function | not carried (unplaced): its only use was the dropped page-artifact check |
| source_references.py | LiteratureReferences._within_source | episode function | task.py within_source (private copy, over read_record_in_scope) |
| source_references.py | LiteratureReferences.resolve | episode function | messages/final_to_parent.py validate_report (references held: records.holds, computed in internal_summary report_source_held) |
| task.py | LiteratureTask | episode function | task.py decide, action, tools |
| task.py | LiteratureTask.instructions | episode function | task.py instructions |
| task.py | LiteratureTask.next | episode function | task.py decide |
| task.py | LiteratureTask.apply_response | episode function | task.py action (decode_response, validate against the offered schema, Rejected with rejection_feedback); the report_update admission is the report tool; journal rows, resolver, replay: machinery |
| task.py | LiteratureTask.execute | episode function | task.py tools (run_access_tool, report); journal/receipt/credit bookkeeping and ActionFailure: machinery |
| task.py | _bind_original_task_runtime_providers | machinery | provider patching |
| task_decision.py | LiteratureTaskDecision | episode function | task.py decide |
| task_decision.py | LiteratureTaskDecision.decision_completion | episode function | task.py decide (ModelRequest role REASONING, context, strict generation_schema); provider identity checks and journal rows: machinery |
| task_decision.py | LiteratureTaskDecision.call | episode function | task.py decide; the recorded model call is the system's |
| task_decision.py | LiteratureTaskDecision.conversation_key | machinery | conversation state |
| task_decision.py | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange interpretation context |
| task_decision.py | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange loop |
| task_decision.py | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_decision.py | _bind_original_task_runtime_providers | machinery | provider patching |
| task_instructions.py | instructions | episode function | task.py instructions (base text, goal, tool knowledge; the request_context/history span replaced with replace_span; the pending-delivery paragraph not carried: no redelivery) |
| task_state.py | LiteratureTaskState | machinery | decision source state (call count, feedback, last outcome, report values): the loop's view and messages/internal_summary.py hold what is episode content |
| task_state.py | LiteratureTaskState.__init__ | machinery | decision source state; the report values and basis are the latest report outcome in internal_summary |
| task_state.py | LiteratureTaskState.bind_execution_context | machinery | old execution binding |
| task_state.py | LiteratureTaskState.record_execution_failure | episode function | task.py run_access_tool: an exception of a selected operation becomes a failed outcome via library failure_outcome (category episode_execution, cause_code selected_operation_failed); journal rows: machinery |
| task_state.py | LiteratureTaskState.restore_checkpoint | machinery | checkpoint/restore |
| task_state.py | LiteratureTaskState.restore | machinery | checkpoint/restore |
| task_state.py | LiteratureTaskState.record_effect | machinery | record_effect |
| task_state.py | LiteratureTaskState.checkpoint | machinery | checkpoint/restore |
| task_state.py | _bind_original_task_runtime_providers | machinery | provider patching |
| to_parent.py | LiteratureReport | episode function | messages/final_to_parent.py |
| to_parent.py | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (empty fact sources; credit and finding declared) |
| to_parent.py | LiteratureReport.facts | episode function | messages/final_to_parent.py final_to_parent (no facts of its own) |
| to_parent.py | LiteratureReport.current_report_facts | machinery | report facts without a report contract: delivery machinery |
| to_parent.py | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (assignment agreement, form admission, references held); validate_form against the parent's schema is not called (see contract_misfits) |
| waiting.py | LiteratureWaiting | machinery | wait/suspension machinery (supports_wait False; suspension forwarding) |
| waiting.py | LiteratureWaiting.supports_wait | machinery | wait/suspension machinery (supports_wait False; suspension forwarding) |
| waiting.py | LiteratureTaskWaiting | machinery | wait/suspension machinery (supports_wait False; suspension forwarding) |
| waiting.py | LiteratureTaskWaiting.suspension_changed | machinery | wait/suspension machinery (supports_wait False; suspension forwarding) |
| yield_estimator.py | LiteratureYield | episode function | yield_estimator.py |
| yield_estimator.py | LiteratureYield.continuation_task | machinery | continuation_task returned None: no declaration |
| yield_estimator.py | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller (BoundedQualityYieldController, maximum = projector native_score_maximum 1.0, README 7b) |

Library candidates: none (every episode function either stays in its episode file or calls a library function that already exists: `read_record_in_scope`, `outcome_page`, `yield_table`, `time_accounting`, `extend_context`, `rejection_feedback`, `replace_span`, `failure_outcome`, `generation_schema`/`decode_response`, `ToolRegistry`, `ToolKnowledge`).
