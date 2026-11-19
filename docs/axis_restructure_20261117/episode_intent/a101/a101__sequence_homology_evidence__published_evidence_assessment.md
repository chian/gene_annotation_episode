# a101 / sequence_homology_evidence / published_evidence_assessment

Source: the episode's own files at commit `97308b94c`
(`git show HEAD:gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/published_evidence_assessment/<file>`).
The child-episode folder `evidence_search_strategy_improvement/` and `tests/` are not covered here. Old binding class
`LiteratureEpisode`; decision source `LiteratureTask`; prompt renderer `render_literature_source_prompt`.

## Purpose (goal, in its own words)

Role `literature` (also an entry role). `goal.py`:

> For A101, identify the actual sequence or region and its aligned homolog before using a source claim. Keep
> alignment coverage, residue or domain correspondence, characterized homolog measurements, database labels, and
> their applicability to the target distinct and source-grounded.
>
> Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches
> and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.

## Task and instructions

`task_instructions.instructions` starts from the a101 `library.literature_investigation_prompt.INSTRUCTIONS` and
appends the goal above (the default instructions are not replaced). It then adds tool knowledge, launch
instructions, the pending_child_delivery repair paragraph and the decision-exchange history replacement. It
imports `REASONING_COMMIT_REQUIREMENT` but never appends it, and it has no wait guidance. `task.py` is the common
loop, identical in content to local_job_execution's, including automatic score updates and
retain_shared_grading_results. `task_decision.decision_completion` calls the provider through
`complete_with_presentation(prompt_renderer=render_literature_source_prompt)`.

## What it reads from its parent's assignment

- Parent: `sequence_homology_evidence`.
- Assignment `literature_assignment_v1`: `{version, question_context_refs, source_refs}`. Every ref must be in scope,
  and source_refs must be `source` records.
- `prepare_assignment` requires an operation_key. A `literature_page` parent branch exists for the other literature
  roles, but it is unreachable here because the role is fixed to `literature`.

## Children

- `literature_strategy` (folder `evidence_search_strategy_improvement`) is the only child (`_CHILDREN['literature']`).
- To the child (`to_child_evidence_search_strategy_improvement.prepare_request`):
  - the child scope is validated within the parent scope;
  - the expanded typed report contract (schema + declaration) is built;
  - every source in the child binding's `required_return_sources` must appear exactly once in that schema;
  - the parent's initial report values are validated against the interpretation schema;
  - the role must be one the parent may commission;
  - the launch instructions are materialized;
  - the child assignment is prepared through the child's own binding
    (`prepare_assignment(..., operation_key=<run>:<episode>:<index>)`).
- From the child (`from_child_evidence_search_strategy_improvement.receive_report`):
  - the recorded admission references, when receipts exist;
  - the progress provider receives the form;
  - the references inside the admitted form plus `received_form_references`;
  - native timing receipts (`runtime_report_attempts.timing_receipts`) when native timing information is present;
  - the receipts receive the references as `child_form` or `report_redelivery`;
  - the tool attributions.
- `create_binding_tree` builds this binding and its six descendant literature bindings (strategy → source relevance →
  source evidence examination → table / source coverage / passage) from one shared configuration.

## Decision state shown to the model

The common decision_state, plus (for a scientific source) proposed_annotations and annotation_comparisons in
annotation-axis mode, or annotation_context. `internal_summary.decision_context` adds literature_assignment,
literature_source_custody (version, artifact/text/stdout/stderr refs, parent_source_refs), own_literature_outcomes
(the first page of `outcome_page_size` over acquisition and read tools), and literature_history_meaning "Read exact
prior outcomes through episode.history; source discovery alone is not A101 evidence." It has no initial decision
context. `decision_inputs` is identical in content to local's.

## Tools offered

The ordinary tool catalog filtered to:

- access: `state.query`, `source.read`, `source.locate`, `source.sequence.scan`, `source.sequence.references`,
  `source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`,
  `source.xlsx.sheets`, `source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`, and
  `execution.estimate` (only its xlsx branches);
- acquisition: `public.literature.search`, `public.literature.read`, `public.literature.sequence_identity`,
  `public.ncbi.search` (database restricted to pubmed), `public.pmc.versions`, `public.pmc.files`,
  `public.pmc.asset`.

The input schemas go through `source_location_inputs`. Locate, sequence and experimental tools get
`permitted_record_refs` = the received records. Common actions: tool, child and redeliver_report. There is **no
reasoning action**: `execute_reasoning` raises `a101_literature_reasoning_not_commissioned`, and
`reasoning_action_schema` is None. There are no automatic score judgments
(`a101_automatic_judgment_unavailable`), and wait is not supported.

## Credit

`credit_kind` = `scientific`. `credit_view` = `services.scientific_credit(context, receiver_selection)`, the
caller-bound projector. `credit_projector` returns None, so the episode has no projector of its own.

## Continuation

None of its own: `continuation_task` and `yield_controller` return None, so the caller's configured controller
decides. No estimator or settings are named in these files.

## Report to parent

It has no fact sources and no facts of its own (`to_parent` returns `{}`), and no received report sources or facts.
`validate_report` re-validates the assignment and checks that every form reference resolves (`reference_in_context`).
`finish` saves the form built from the report values and the workflow facts.

## Differences from similar episodes

- This a101 copy is a deliberately reduced literature binding. Compared with the general literature family
  (`ROLES`, `_ROLE_INSTRUCTIONS` for all seven roles are still carried in `source_contracts.py`), it drops reasoning
  commits, automatic judgments, received evidence and report facts, private yield, and the experimental database
  acquisition tools. It adds the A101 homolog-identity goal sentence.
- Its decision_state is local's plus the scientific annotation context. Its task_decision is local's plus the
  presentation renderer. Its task is identical in content to local's.

## Per-file table

| Old file | Lines | This episode's own intent | Old-runner names used (count) |
|---|---|---|---|
| __init__.py | 0 | Empty package marker. | none |
| binding_record.py | 8 | Binding record id `sequence_homology_evidence/published_evidence_assessment`, VERSION `literature_episode_binding_v1`, configuration outcome_page_size. | none |
| configuration.py | 12 | outcome_page_size (default 8, positive int); no contract-information profile; no reference parent sources. | none |
| credit.py | 15 | credit_kind 'scientific'; credit_view = services.scientific_credit (caller projector); credit_projector None (no own projector). | `self.services.scientific_credit` (1) |
| decision_inputs.py | 76 | Identical in content to local_job_execution's decision_inputs. | `import:a101.episode_work_report` (2), `import:a101.hpc_prompt` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (2), `self.workflow.episode_bindings` (1), `self.workflow.execution_expectations` (1), `self.workflow.job_episodes` (2), `self.workflow.launch_instructions` (2), `self.workflow.native_estimation_context` (1), `self.workflow.native_event_information` (2), `self.workflow.pending_work` (1), `self.workflow.resource_context` (1), `self.workflow.resource_estimator` (4), `self.workflow.shared_information_context` (1), `self.workflow.store` (2) |
| decision_state.py | 60 | As local_job_execution plus, for a scientific source, proposed_annotations / annotation_comparisons (annotation-axis mode) or annotation_context. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.annotation_context` (1), `self.workflow.binding_context` (1), `self.workflow.catalog` (1), `self.workflow.controller_binding` (1), `self.workflow.delivery_status` (1), `self.workflow.extra_report_sources` (1), `self.workflow.is_scientific_source` (1), `self.workflow.job_episode_options` (1), `self.workflow.journal` (3), `self.workflow.knowledge` (1), `self.workflow.local_outcome_preview` (1), `self.workflow.pending_work` (1), `self.workflow.receipt_projection` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_binding` (1), `self.workflow.source_credit_view` (1), `self.workflow.specialist` (1), `self.workflow.store` (3), `self.workflow.tools` (1), `self.workflow.working_state` (1), `table:runtime_actions` (2) |
| episode.py | 78 | Role `literature` (entry role), commissioning parent `sequence_homology_evidence`; child roles from _CHILDREN['literature'] = ('literature_strategy',); child request preparer / report receiver for literature_strategy; prompt renderer render_literature_source_prompt; contract information only if configured (never here); create_binding_tree assembles this binding plus six descendant literature bindings with one shared configuration. | `import:a101.library.literature_source_prompt` (1) |
| from_child_evidence_search_strategy_improvement.py | 43 | receive_report: admitted child form -> recorded-admission refs (receipts), progress provider receipt of the form, references in the form + episode_bindings.received_form_references, native timing receipts from runtime_report_attempts, receipts.receive(child_form/report_redelivery), tool attributions. | `import:a101.delivery_counterpart` (1), `import:a101.episode_return_records` (1), `import:a101.runtime` (1), `self.workflow.binding_context` (4), `self.workflow.episode_bindings` (1), `self.workflow.is_job_source` (2), `self.workflow.job_episodes` (2), `self.workflow.native_timing_information` (1), `self.workflow.progress_provider` (4), `self.workflow.receipts` (3), `self.workflow.receive_tool_attributions` (1), `self.workflow.run_id` (6), `self.workflow.specialist` (1), `self.workflow.store` (7), `table:runtime_report_attempts` (2) |
| from_parent.py | 45 | assignment_schema always `literature_assignment_v1` {version, question_context_refs, source_refs}; _validate_assignment checks every ref in scope (source refs must be sources); prepare_assignment requires operation_key. | none |
| goal.py | 9 | Own goal text: "For A101, identify the actual sequence or region and its aligned homolog before using a source claim. Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database labels, and their applicability to the target distinct and source-grounded." + role instruction "Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration." | none |
| internal_summary.py | 19 | decision_context: literature_assignment, literature_source_custody (version/artifact/text/stdout/stderr/parent refs), own_literature_outcomes (page of outcome_page_size over acquisition+read tools), literature_history_meaning "source discovery alone is not A101 evidence". | `self.services.own_outcomes` (1) |
| received_evidence.py | 20 | No received report sources/facts/tokens; no received report validation. | none |
| report_delivery.py | 34 | Identical in content to local_job_execution's finish. | `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.binding_context` (1), `self.workflow.episode_bindings` (1), `self.workflow.facts` (1), `self.workflow.journal` (2), `self.workflow.pending_handles` (1), `self.workflow.release` (2), `self.workflow.source_credit_view` (1), `table:runtime_forms` (2) |
| scientific_records.py | 11 | No automatic score judgments; completing one raises `a101_automatic_judgment_unavailable`. | none |
| source_contracts.py | 26 | VERSION, ROLES (literature family), schemas (_REFERENCES, _WINDOW, _TABLE, _PAGE), _CHILDREN tree, _ACCESS_TOOLS, _ACQUISITION_TOOLS (no experimental database tools), _READ_TOOLS, _ROLE_INSTRUCTIONS for all seven literature roles. | `import:a101.communication` (1), `import:a101.composition_information` (1), `import:a101.domain` (1), `import:a101.episode_bindings` (1) |
| source_operations.py | 66 | permitted_common_actions ('tool','child','redeliver_report') - no reasoning action; reasoning schema None, execute_reasoning raises `a101_literature_reasoning_not_commissioned`. Catalog: access + acquisition tools from services.tool_catalog (ncbi search restricted to pubmed; execution.estimate only for xlsx branches), with source_location_inputs. Execute via services.execute_tool, with permitted_record_refs for locate/sequence/experimental tools; page assignments confine reads to the assigned source lineage. | `self.services.execute_tool` (1), `self.services.tool_catalog` (1) |
| source_references.py | 35 | _require (scope check + read_record), _artifact per representation, _within_source (parent_source_refs lineage), resolve via reference_in_context. | `self.services.read_record` (1), `self.services.reference_in_scope` (1) |
| task.py | 214 | Identical in content to local_job_execution's task (class names differ). | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.library.read_mapping_values` (1), `import:a101.providers` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.action_schema` (1), `self.workflow.automatic_score_updates` (1), `self.workflow.completed_unit` (3), `self.workflow.completions` (3), `self.workflow.controller_value` (2), `self.workflow.decision_exchanges` (3), `self.workflow.delivery_resolution_inputs` (1), `self.workflow.execute` (1), `self.workflow.execution_binding` (7), `self.workflow.inprocess_replay` (4), `self.workflow.journal` (7), `self.workflow.next_return` (1), `self.workflow.pending_work` (1), `self.workflow.receive_native_outcome` (1), `self.workflow.receive_outcome` (1), `self.workflow.resolve_pending_deliveries` (1), `self.workflow.resolver` (1), `self.workflow.retain_shared_grading_results` (1), `self.workflow.run_id` (2), `self.workflow.selected` (3), `self.workflow.services` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (7), `self.workflow.validate_report` (1), `table:runtime_actions` (8), `table:runtime_episodes` (1), `table:runtime_model_calls` (2) |
| task_decision.py | 347 | As local plus decision_completion() routing through complete_with_presentation with render_literature_source_prompt. | `import:a101.library.live_runtime_functions` (1), `import:a101.providers` (2), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `import:providers` (1), `name:bind_functions` (2), `self.workflow.contract_information_profile` (1), `self.workflow.contract_information_reply` (1), `self.workflow.controller_binding` (1), `self.workflow.decision_exchanges` (4), `self.workflow.decision_protocol` (3), `self.workflow.execute` (1), `self.workflow.freeze_contract_information` (1), `self.workflow.freeze_literature_numerical_contracts` (1), `self.workflow.history_preview` (1), `self.workflow.journal` (3), `self.workflow.numerical_contracts` (1), `self.workflow.provider` (3), `self.workflow.receipts` (4), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.specialist` (2), `self.workflow.store` (2), `self.workflow.uses_received_record_context` (2), `self.workflow.validate_contract_information` (5), `table:runtime_model_calls` (8) |
| task_instructions.py | 18 | Own composer over the a101 literature_investigation_prompt INSTRUCTIONS: specialist goal appended (not replacing), tool knowledge, launch instructions, repair guidance, exchange history; no reasoning-commit requirement and no wait guidance. | `import:a101.library.literature_investigation_prompt` (1), `self.workflow.binding_context` (1), `self.workflow.decision_protocol` (1), `self.workflow.knowledge` (1), `self.workflow.launch_instructions` (1), `self.workflow.specialist` (1) |
| task_state.py | 115 | Identical in content to local_job_execution's task state (class name differs). | `import:a101.episode_source_failure` (1), `import:a101.library.live_runtime_functions` (1), `import:a101.runtime` (1), `import:a101.runtime(module)` (1), `name:bind_functions` (2), `self.workflow.archive` (1), `self.workflow.completions` (4), `self.workflow.context` (1), `self.workflow.controller_value` (1), `self.workflow.execution_binding` (4), `self.workflow.grains` (1), `self.workflow.inprocess_replay` (7), `self.workflow.journal` (5), `self.workflow.progress_provider` (2), `self.workflow.recover_commissions` (1), `self.workflow.run_id` (1), `self.workflow.source_credit_view` (1), `self.workflow.store` (2), `table:runtime_actions` (5) |
| to_child_evidence_search_strategy_improvement.py | 33 | prepare_request for child role literature_strategy: validate child scope within parent scope, expand contract form, require child's required_return_sources exactly once, parse/validate initial report, check role allowed, materialize launch instructions, prepare child assignment through the child's binding. | `import:a101.runtime` (1), `self.workflow.annotation_child_roles` (1), `self.workflow.available_child_roles` (1), `self.workflow.binding_context` (4), `self.workflow.child_initial_report_input` (1), `self.workflow.episode_bindings` (3), `self.workflow.expanded_contract_form` (1), `self.workflow.launch_instructions` (1), `self.workflow.run_id` (1), `self.workflow.services` (1), `self.workflow.specialist` (1), `self.workflow.store` (1) |
| to_parent.py | 21 | No fact sources and no facts of its own; validate_report re-validates the assignment and the form references. | none |
| waiting.py | 15 | supports_wait False; LiteratureTaskWaiting.suspension_changed marks external backend suspension. | `self.workflow.execution_backend` (1), `self.workflow.execution_handle` (2) |
| yield_estimator.py | 11 | continuation_task None and yield_controller None: no private continuation; the caller's configured controller decides. | none |

Old-runner names are counted per file: `self.workflow.<member>` (also `source.workflow` and `workflow.` in module functions), `self.services.<member>`, journal/receipt table names, imports from old shared-root modules (`import:<module>`), and old yield/rebinding names (`name:`). No `BindingContext` literal occurs in these files; the old binding context arrives through `self.workflow.binding_context(...)`. The same rows are in `runs/carry_over/calls/a101_02.tsv`.

## Carried over

One row per function of the old episode files at 97308b94c (`runs/carry_over/functions/a101__sequence_homology_evidence__published_evidence_assessment.tsv`). Columns: old file, kind, name (copied), classification (machinery or episode function), new place or machinery reason. The episode folder is `gene_annotation_episode/episodic_workflow/root/a101/sequence_homology_evidence/published_evidence_assessment/`.

| old file | kind | name | classification | new place / reason |
|---|---|---|---|---|
| binding_record.py | class | LiteratureBindingRecord | machinery | the binding's own as_record() and binding record id/version: system record of the binding, not carried |
| binding_record.py | method | LiteratureBindingRecord.as_record | machinery | the binding's own as_record() and binding record id/version: system record of the binding, not carried |
| configuration.py | class | LiteratureConfiguration | episode function | messages/internal_summary.py OUTCOME_PAGE_SIZE = 8 (the fixed value outcome_page_size; the positive-int check is dropped with the constructor; services and contract-information profile are old-runner values) |
| configuration.py | method | LiteratureConfiguration.__init__ | episode function | messages/internal_summary.py OUTCOME_PAGE_SIZE = 8 (the fixed value outcome_page_size; the positive-int check is dropped with the constructor; services and contract-information profile are old-runner values) |
| credit.py | class | LiteratureCredit | episode function | credit.py (credit, A101SequenceCredit) |
| credit.py | method | LiteratureCredit.credit_kind | machinery | credit_kind is deleted (README 3d): the credit is one number from credit.py |
| credit.py | method | LiteratureCredit.credit_view | episode function | credit.py credit(summary, records): the scientific credit projector over the held records (old services.scientific_credit) |
| credit.py | method | LiteratureCredit.credit_projector | episode function | credit.py A101SequenceCredit: private copy of the axis head's projector (git show 97308b94c native_correspondence_credit.py), called with this episode's scope and records.refs(); library candidate |
| decision_inputs.py | class | LiteratureDecisionInputs | episode function | task.py decide (context assembly) |
| decision_inputs.py | method | LiteratureDecisionInputs.decision_inputs | episode function | task.py decide: child_options, tool_knowledge (ctx.settings knowledge_library_directory); resource, shared-information, launch-instruction, pending-work, execution-expectation, resource-estimate, native-event and completed-action-report parts have no home in this episode (no job or launch tool; unplaced, see blocked file) |
| decision_inputs.py | function | _bind_original_task_runtime_providers | machinery | provider patching |
| decision_state.py | class | LiteratureDecisionState | episode function | messages/internal_summary.py and task.py decide (decision state) |
| decision_state.py | method | LiteratureDecisionState.decision_state | episode function | messages/internal_summary.py internal_summary (assignment, scope, outcomes, child reports, report, yield table) and task.py decide (goal, scope, tools, time_accounting from ctx.clock, feedback, action_yields, tool_knowledge); working_state/visible_record_refs/visual_evidence/report_deliveries/annotation context parts were old-runner or journal reads (runtime_actions, receipts, delivery_status) and are not carried |
| decision_state.py | function | _bind_original_task_runtime_providers | machinery | provider patching |
| episode.py | class | LiteratureEpisode | episode function | episode.py PublishedEvidenceAssessment (the one class) |
| episode.py | method | LiteratureEpisode.contract_information_configuration | machinery | contract-information freezing (README 5 item 16): the profile was never configured for this episode |
| episode.py | method | LiteratureEpisode.contract_information_profile | machinery | contract-information freezing: never applied here |
| episode.py | method | LiteratureEpisode._role | machinery | role check of a one-role binding: each role is its own episode now |
| episode.py | method | LiteratureEpisode.allowed_children | episode function | task.py CHILD_SLOTS |
| episode.py | method | LiteratureEpisode.child_roles | episode function | task.py CHILD_SLOTS (literature_strategy -> slot evidence_search_strategy_improvement) |
| episode.py | method | LiteratureEpisode.context_hook_applies | machinery | hook-era context hook selection |
| episode.py | method | LiteratureEpisode.child_request_preparer | episode function | messages/msg_to_child.py msg_to_child |
| episode.py | method | LiteratureEpisode.child_report_receiver | episode function | messages/read_from_child.py read_from_child |
| episode.py | function | create_binding_tree | machinery | home factory / binding tree assembly: deleted (C1) |
| from_child_evidence_search_strategy_improvement.py | function | receive_report | episode function | messages/read_from_child.py read_from_child (the child's credit and finding); recorded-admission refs, progress-provider receipt, runtime_report_attempts timing receipts, receipts.receive and tool attributions are machinery (custody and recording are the system's) |
| from_parent.py | class | LiteratureAssignment | episode function | messages/read_from_parent.py ASSIGNMENT_FORM and read_from_parent |
| from_parent.py | method | LiteratureAssignment.child_assignment_schema | machinery | parent-side schema of a child's assignment: the parent writes its own schema in task.py (STRATEGY) and the child declares its form (C3) |
| from_parent.py | method | LiteratureAssignment.assignment_schema | episode function | messages/read_from_parent.py ASSIGNMENT_FORM (version literature_assignment_v1, question_context_refs, source_refs) |
| from_parent.py | method | LiteratureAssignment._validate_page | episode function | not placed: a Store check of a page commission; unreachable here (role fixed to literature) and a wrong commission fails (blocked file) |
| from_parent.py | method | LiteratureAssignment._validate_assignment | episode function | messages/read_from_parent.py (schema); the Store part (every ref in scope, source_refs are sources) is a check of the commission against the Store: not carried (blocked file); the source-kind check is made by internal_summary's records.require(ref, {'source'}) |
| from_parent.py | method | LiteratureAssignment.prepare_assignment | episode function | messages/read_from_parent.py read_from_parent; the operation_key check and the literature_page branch are not carried (unreachable here; the system gives ctx.operation_key) |
| goal.py | class | LiteratureGoal | episode function | goal.py GOAL |
| goal.py | method | LiteratureGoal.instructions | episode function | goal.py GOAL (A101 sentence plus the literature role sentence); task.py instructions appends GOAL |
| internal_summary.py | class | LiteratureSummary | episode function | messages/internal_summary.py internal_summary |
| internal_summary.py | method | LiteratureSummary.initial_decision_context | episode function | none to carry: it returned {} (no initial decision context) |
| internal_summary.py | method | LiteratureSummary.decision_context | episode function | messages/internal_summary.py internal_summary (literature_assignment, literature_source_custody via view.records.require, own_literature_outcomes via outcome_page, literature_history_meaning) |
| received_evidence.py | class | LiteratureReceivedEvidence | episode function | none to carry: no received report sources, facts, form references or evidence tokens, and no received report validation (all returned {} or None); RETURN_FORM of the child carries its own fields |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_sources | episode function | none to carry: no received report sources, facts, form references or evidence tokens, and no received report validation (all returned {} or None); RETURN_FORM of the child carries its own fields |
| received_evidence.py | method | LiteratureReceivedEvidence.received_report_facts | episode function | none to carry: no received report sources, facts, form references or evidence tokens, and no received report validation (all returned {} or None); RETURN_FORM of the child carries its own fields |
| received_evidence.py | method | LiteratureReceivedEvidence.received_form_references | episode function | none to carry: no received report sources, facts, form references or evidence tokens, and no received report validation (all returned {} or None); RETURN_FORM of the child carries its own fields |
| received_evidence.py | method | LiteratureReceivedEvidence.received_evidence_tokens | episode function | none to carry: no received report sources, facts, form references or evidence tokens, and no received report validation (all returned {} or None); RETURN_FORM of the child carries its own fields |
| received_evidence.py | method | LiteratureReceivedEvidence.validate_received_report | episode function | none to carry: no received report sources, facts, form references or evidence tokens, and no received report validation (all returned {} or None); RETURN_FORM of the child carries its own fields |
| report_delivery.py | class | LiteratureReportDelivery | episode function | messages/final_to_parent.py final_to_parent |
| report_delivery.py | method | LiteratureReportDelivery.finish | episode function | messages/final_to_parent.py final_to_parent (credit from completion, finding from the report); runtime_forms saving, pending_handles, release and Record wrappers are machinery |
| report_delivery.py | function | _bind_original_task_runtime_providers | machinery | provider patching |
| scientific_records.py | class | LiteratureScientificRecords | episode function | none to carry: no automatic score judgments; completing one raised a101_automatic_judgment_unavailable (no tool of this episode produces one) |
| scientific_records.py | method | LiteratureScientificRecords.automatic_score_judgments | episode function | none to carry: no automatic score judgments; completing one raised a101_automatic_judgment_unavailable (no tool of this episode produces one) |
| scientific_records.py | method | LiteratureScientificRecords.complete_score_judgment | episode function | none to carry: no automatic score judgments; completing one raised a101_automatic_judgment_unavailable (no tool of this episode produces one) |
| source_operations.py | class | LiteratureOperations | episode function | task.py (tools, catalog, instructions) |
| source_operations.py | method | LiteratureOperations.permitted_common_actions | episode function | task.py selection_schema: tool and child only (no reasoning action, no redeliver_report: machinery) |
| source_operations.py | method | LiteratureOperations.reasoning_action_schema | episode function | none to carry: it returned None (no reasoning action in selection_schema) |
| source_operations.py | method | LiteratureOperations.reasoning_has_task_content | episode function | none to carry: it returned False (no reasoning action) |
| source_operations.py | method | LiteratureOperations.execute_reasoning | episode function | none to carry: a101_literature_reasoning_not_commissioned (no reasoning action is offered, so nothing reaches it) |
| source_operations.py | method | LiteratureOperations.catalog | episode function | task.py DESCRIPTIONS, INPUT_SCHEMAS, offered, catalog (ncbi restricted to pubmed; execution.estimate only its xlsx branches); tool descriptions and schemas are the tool library's text re-stated; library candidate |
| source_operations.py | method | LiteratureOperations.execute | episode function | task.py run_access_tool and the 22 tool functions (library ToolRegistry.execute_async with permitted_record_refs for locate/sequence/experimental tools) |
| source_operations.py | method | LiteratureOperations._tool_arguments | episode function | task.py admitted (schema check; the page-source restriction never applied: no page); an invalid argument is an invalid outcome that enters the iterator |
| source_references.py | class | LiteratureReferences | episode function | messages/internal_summary.py (custody) and task.py action (held-record check) |
| source_references.py | method | LiteratureReferences._require | episode function | records.require / records.holds (custody replaces reference_in_scope + read_record) |
| source_references.py | method | LiteratureReferences._artifact | episode function | not placed: only used by the page check (blocked file) |
| source_references.py | method | LiteratureReferences._within_source | episode function | not placed: only used by the page-source restriction, never applicable here (blocked file) |
| source_references.py | method | LiteratureReferences.resolve | machinery | reference resolution for validate_form in the old report path (reference_in_context): custody (records.holds) replaces it |
| task.py | class | LiteratureTask | episode function | task.py decide, action and tools |
| task.py | method | LiteratureTask.instructions | episode function | task.py instructions |
| task.py | method | LiteratureTask.next | machinery | the old decision loop (source_failed, in-process replay, completions, pending deliveries, exchange): the system's loop; the model call is decide's ModelRequest |
| task.py | method | LiteratureTask.apply_response | episode function | task.py action (validate the answer, Rejected with rejection_feedback); report-update validation and ReportRedelivery are machinery |
| task.py | method | LiteratureTask.execute | machinery | unit execution, journal rows, credit and controller value: the system's; the tool call is a ToolCall; automatic_score_updates, receive_outcome, retain_shared_grading_results are machinery or not applicable |
| task.py | function | _bind_original_task_runtime_providers | machinery | provider patching |
| task_decision.py | class | LiteratureTaskDecision | episode function | task.py decide (model request) and its rendering |
| task_decision.py | method | LiteratureTaskDecision.decision_completion | machinery | provider patching around complete_with_presentation: the system calls the provider; the prompt rendering is the episode's ModelRequest.context |
| task_decision.py | method | LiteratureTaskDecision.call | machinery | model call recording, saved-request checks, contract-information, exchange: the system records model calls |
| task_decision.py | method | LiteratureTaskDecision.conversation_key | machinery | conversation state (deleted, README 3a) |
| task_decision.py | method | LiteratureTaskDecision.interpretation_context | machinery | decision-exchange context after lookups (a lookup is a tool now) |
| task_decision.py | method | LiteratureTaskDecision.exchange_schema | machinery | decision-exchange loop |
| task_decision.py | method | LiteratureTaskDecision.exchange_response | machinery | decision-exchange loop |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_request | machinery | decision-exchange saved-request check |
| task_decision.py | method | LiteratureTaskDecision.validate_contract_exchange_history | machinery | decision-exchange saved-request check |
| task_decision.py | method | LiteratureTaskDecision.exchange_decision | machinery | decision-exchange loop |
| task_decision.py | function | _bind_original_task_runtime_providers | machinery | provider patching |
| task_instructions.py | function | instructions | episode function | task.py instructions(*, knowledge): the literature investigation INSTRUCTIONS with the history span replaced (replace_span), the goal appended, tool knowledge when offered; the launch-instruction text, the pending_child_delivery paragraph and the request_context replacement are not carried (no such action or tool) |
| task_state.py | class | LiteratureTaskState | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.__init__ | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.bind_execution_context | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.record_execution_failure | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.restore_checkpoint | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.restore | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.record_effect | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | method | LiteratureTaskState.checkpoint | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| task_state.py | function | _bind_original_task_runtime_providers | machinery | task state, failure recording, checkpoint and restore: the system's view, outcomes and resume (record_execution_failure's failure outcome is task.py run_access_tool via failure_outcome) |
| to_child_evidence_search_strategy_improvement.py | function | prepare_request | episode function | messages/msg_to_child.py msg_to_child (the strategy assignment, scope, held records); scope validation, expanded report contract, required return sources, initial report, role check, launch-instruction materialization and prepare_assignment are checks or construction of the commission by the old runner: not carried (a wrong commission fails) |
| to_parent.py | class | LiteratureReport | episode function | messages/final_to_parent.py RETURN_FORM (no fact sources: only credit and finding) |
| to_parent.py | method | LiteratureReport.fact_sources | episode function | messages/final_to_parent.py RETURN_FORM (no fact sources: only credit and finding) |
| to_parent.py | method | LiteratureReport.facts | episode function | messages/final_to_parent.py RETURN_FORM (no fact sources: only credit and finding) |
| to_parent.py | method | LiteratureReport.current_report_facts | episode function | messages/final_to_parent.py RETURN_FORM (no fact sources: only credit and finding) |
| to_parent.py | method | LiteratureReport.validate_report | episode function | messages/final_to_parent.py validate_report (the report is a valid FINDING_FORM, every reference held); the assignment re-validation reads the Store and is not carried |
| waiting.py | class | LiteratureWaiting | machinery | wait/suspension machinery (supports_wait was False) |
| waiting.py | method | LiteratureWaiting.supports_wait | machinery | wait machinery (False: no wait tool in this episode) |
| waiting.py | class | LiteratureTaskWaiting | machinery | suspension machinery |
| waiting.py | method | LiteratureTaskWaiting.suspension_changed | machinery | external-backend suspension marking |
| yield_estimator.py | class | LiteratureYield | episode function | yield_estimator.py yield_controller |
| yield_estimator.py | method | LiteratureYield.continuation_task | machinery | continuation_task returned None (the caller's controller decided); a declaration lookup of the old runner |
| yield_estimator.py | method | LiteratureYield.yield_controller | episode function | yield_estimator.py yield_controller: BoundedQualityYieldController over the A101 projector's declared maximum (README 7b); the old None meant the caller's configured controller |
