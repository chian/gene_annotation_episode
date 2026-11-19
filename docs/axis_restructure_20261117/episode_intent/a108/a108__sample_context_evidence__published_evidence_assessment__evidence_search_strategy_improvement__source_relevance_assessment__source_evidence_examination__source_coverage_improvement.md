# A108 source_evidence_examination / source_coverage_improvement (role `literature_ordered`)

Source: `git show HEAD:gene_annotation_episode/episodic_workflow/root/a108/sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement/<file>` at 97308b94c. Only this folder's own files and its `grading/` and `scoring/` were read. Every file was also diffed against the parent `source_evidence_examination` folder. Where this file says "as parent", the text is identical apart from the package path and role string. The full detail is in the parent's intent file, `a108__sample_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination.md`.

Binding class `LiteratureEpisode`. `binding_path = '.../source_evidence_examination/source_coverage_improvement'`, `commissioning_parent = '.../source_relevance_assessment/source_evidence_examination'`, `roles = ('literature_ordered',)`, `entry_roles = ()`, `decision_source_type = LiteratureTask`, `decision_prompt_renderer = render_literature_experimental_prompt`.

## What this episode is for (its goal, in its own words)

- Role instruction (`source_contracts._ROLE_INSTRUCTIONS['literature_ordered']`): "Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes."
- Instructions are this role instruction + `A108_CONTEXT_TASK` + `A108_READING_TASK` (old shared `a108.library.literature_a108_prompt`).
- Reads the assigned source in document order from a given window and decides whether to continue, reread or change the window. The parent commissions it as `literature_ordered` (the "ordered-reading investigation").

## Task and instructions

`task.py` is the same as the parent's apart from its docstring. `task_state.py`, `task_decision.py`, `task_instructions.py`, `decision_inputs.py` and `decision_presentation.py` are byte-identical to the parent's. That covers the old iterative decision source, the empty-reasoning rejection, grading-coupled reasoning, failed actions entering the iterator with credit, `SourceEnd('source_failed')` on a model-call failure, and the redelivery/exchange instruction text.

## What it reads from its parent's assignment (`from_parent.py`, 111 lines)

- Schema: `obj({version: const 'reading_assignment_v1', page: _PAGE, selection: _WINDOW})`. On top of that come the same `literature_task` (goal.task_schema), `proposed_annotation_ref` and A108 grading/aggregation requested-component properties as the parent. These are required under `private_yield_binding`, with `credit_unit` and `yield_settings` filled from the owner's `yield_bindings`.
- Selection: one `_WINDOW{source_ref, representation, offset>=0, limit>=1}`, the starting window for document-order reading.
- Window checks: each window's `source_ref` must equal `page.source_ref` (`literature_reading_source_mismatch`). If the window has a representation, it must equal the page's (`literature_reading_representation_mismatch`), and `offset` must be at most the artifact size (`source_offset_out_of_bounds`).
- `page` is validated as the parent's is: source in scope, artifact matching the representation, context and prior-delivery refs in scope.
- When the commissioning parent's role is `literature_page`, the binding validates the parent's own page assignment (`_parent_page_schema` / `_validate_parent_page`). It then requires this child's `page.source_ref` to lie within the parent's assigned source (`literature_reading_outside_assigned_source`). This check exists only in the children.
- The proposed annotation must equal the parent's.
- `goal.commissioned_task` takes `assigned_page = assignment.get('page', None)` (the parent uses the assignment itself). Task source refs and screening spans must be on this page's source and artifact.

## Children it may commission

None. `_CHILDREN = {'literature_ordered': ()}`, and `episode.py` has no `child_request_preparer` or `child_report_receiver` and no to_child/from_child files. `permitted_common_actions` still lists `'child'` as the parent's does, but `child_roles` returns an empty tuple.

## Decision state and what it shows the model

As parent. `internal_summary.decision_context` uses `page = assignment.get('page')`, so `literature_assignment` is the whole `reading_assignment_v1` (page + selection), and custody covers the page source. The keys `own_literature_outcomes`, `literature_history_meaning`, `literature_examined_source_inputs`, `literature_experimental_work` (aspect `source_experimental_evidence`, A108), `literature_received_fact_display`, `literature_owned_population_sources`, `literature_selected_population_attempt`, `literature_completed_work` / `literature_current_scoring_sheets` and `literature_goal_plan` (when `literature_task` is present) are all as in the parent.

## Tools it offers (`source_operations.py`, 110 lines)

As parent: the `_A108_ACCESS_TOOLS` subset of the services catalog, `execution.estimate` narrowed to xlsx, the population catalog (A108 grading populate and aggregate), and `source_location_inputs`. All reads must stay within `page.source_ref`. There is no wait. Reasoning goes through `grading/contextual_interpretation.py`, identical to the parent's: the required-grading action schema, `source_lead` for verified_source_leads tasks, `validate_lead`, and the provider `literature.a108.context_grading`.

## How its credit is counted

`credit.py` is as parent. `LiteratureTaskCredit` counts `credit_unit × answered items`, finite and unbounded:
- verified_source_leads: relevant lead dispositions per canonical source, from own reason results and admitted child forms;
- screening: one item when own `no_applicable_evidence` spans cover every requested span;
- assessment: at most one current retained, target-eligible assessment anchored in `task.source_refs`.

`credit_kind = 'scientific'`, and the credit view goes through `services.scientific_credit_for` and the workflow projector.

## Continuation

`yield_estimator.py` is as parent. The task keys are `A108:verified_source_leads` → **accumulation**, and `A108:source_answer:{assessment,screening}` → `remaining_commissioned_credit`, which is **completion with a target** (target = `credit_unit`). Settings are `{credit_unit, kind, cutoff, uncertainty_alpha}` per task key. Without `private_yield_binding` there is no private controller.

## What it reports to its parent

`to_parent.py` and `received_evidence.py` are as parent. It reports `literature_a108_grading_cells`, `literature_a108_aggregation_cells` (requested components only), `literature_screening_answers` (screening tasks), `literature_source_lead_dispositions` (lead tasks), `literature_completed_work` and `literature_current_scoring_sheets`. The report must equal the saved work and the requested sheet subset. The parent's `from_child_source_coverage_improvement.py` receives it, and the A108 cells reach the parent through `received_form_references`.

## File by file

| Old file | Lines | This episode's own intent | Old-runner names used |
|---|---|---|---|
| __init__.py | 1 | none | none |
| binding_record.py | 16 | as parent (binding_id = this path) | none |
| configuration.py | 31 | as parent | composition_information CONTRACT_INFORMATION_PROFILE |
| credit.py | 221 | as parent | as parent: BindingContext.*, communication, domain, numerical yield names, library.literature_assay_inputs, finding_validity, scientific_findings, runtime_actions/runtime_report_attempts SQL, services.{scientific_credit_for,scientific_credit,proposed_annotation_for,annotation_task_required,workflow}, workflow.{scientific_projector_for_context,projector_receipt_arguments,projection_view} |
| decision_inputs.py | 36 | identical | as parent (self.workflow.* context builders, runtime FACT_*, runtime_actions) |
| decision_presentation.py | 21 | identical | runtime _category_yield_parameters/yield_table; episode_work_report; self.workflow.controller_binding |
| episode.py | 62 | role guard `literature_ordered`, no children, no preparers/receivers | BindingContext.{role,path}; library.literature_experimental_prompt |
| from_parent.py | 111 | reading_assignment_v1 with selection _WINDOW; window checks; within parent's page source | BindingContext.{assignment,role,scope} and parent.{role,assignment,scope}; services.{read_record,proposed_annotation_for}; library grading/aggregation storage |
| goal.py | 104 | as parent, with `assignment.get('page', None)` | BindingContext.{assignment,request,role}; communication; domain; numerical (duplicated header); library.literature_a108_prompt |
| internal_summary.py | 106 | as parent, with `page = assignment.get('page')` | BindingContext.*; services.{own_outcomes,workflow}; workflow.{store,run_id}; runtime_actions SQL; library.literature_source_inputs/_task_families/_work_report |
| received_evidence.py | 90 | as parent | BindingContext.*; services.{record_selection,workflow}; library.literature_sheet_updates; method_loop.durable; domain.canonical |
| scientific_records.py | 16 | as parent | library grading/aggregation storage |
| source_contracts.py | 37 | `_CHILDREN = {'literature_ordered': ()}`; own role instruction | communication; composition_information; domain; episode_bindings.reference_in_context; library.literature_population_catalog, literature_required_grading |
| source_operations.py | 110 | as parent with `page = assignment.get('page')` | BindingContext.*; services.{tool_catalog,execute_tool,read_record}; composition_information.CONTRACT_ARGUMENT_TRANSPORT; literature_contract_error; library.literature_assay_inputs |
| source_references.py | 35 | as parent | services.{reference_in_scope,read_record}; episode_bindings.reference_in_context |
| task.py | 209 | as parent | as parent (runtime helpers, self.workflow.* runner, providers.ModelCallError, episode_source_failure, runtime_episodes/actions/model_calls/forms) |
| task_decision.py | 351 | identical | as parent (runtime exchange helpers, providers internals, self.workflow.*, receipts, runtime_model_calls) |
| task_instructions.py | 28 | identical | runtime_prompt; library.literature_investigation_prompt; workflow.* |
| task_state.py | 108 | identical | runtime Episode/ActionLeaf/...; self.workflow.* replay/completions; episode_source_failure; runtime_actions |
| to_parent.py | 64 | as parent | BindingContext.*; services.{workflow,read_record}; library literature_sheet_updates/_work_report/_a108_grading_storage/_a108_aggregation_storage/_numerical_contracts |
| waiting.py | 8 | no wait | none |
| yield_estimator.py | 108 | as parent | numerical YieldController/YieldParameters/YieldEstimate/NumericBand/STATUS_NORMAL/estimate_score_yield; BindingContext.role |
| grading/__init__.py | 0 | none | none |
| grading/contextual_interpretation.py | 49 | as parent | BindingContext.*; services.workflow.store; literature_contract_error |
| grading/contextual_subscoring.py | 14 | as parent | library.literature_a108_grading_storage; services.workflow.{store,run_id} |
| scoring/__init__.py | 0 | none | none |
| scoring/contextual_main_sheet.py | 11 | as parent | library.literature_a108_aggregation_storage; services.workflow.{store,run_id} |

The per-file counts are in `runs/carry_over/calls/a108_02.tsv` (episode `source_coverage_improvement`).

## Differences from the parent and siblings

- Only `from_parent.py` (the selection shape), `source_contracts.py` (role instruction, no children), `episode.py` (no child wiring) carry content that differs from the parent. Credit, yield, reporting, grading and the decision machinery are the same in all four.
- The three children differ from one another only in role, instruction and selection: targeted takes `selection.spans[]` of `_WINDOW` (minItems 1), ordered takes one `_WINDOW`, and table takes `anyOf[_TABLE, _WINDOW]`, with the table child alone enforcing the `sheet_key` match.
