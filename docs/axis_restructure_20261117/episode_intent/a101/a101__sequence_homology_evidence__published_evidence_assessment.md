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
