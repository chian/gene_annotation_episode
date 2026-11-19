# source_relevance_assessment (A108): blocked, unplaced and contract misfits

All library paths are under `gene_annotation_episode/episodic_workflow/episode_support/`.

## Process note

The working repository (`/tmp/ramrepo`) has no `.git`; the old files were read with
`git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` (only this episode's own files). The folder had
only the hook-era stub `episode.py` (class on `LiteratureBinding`, deleted) and `__init__.py`; no tests existed. This episode is
a private copy of its finished child `source_evidence_examination` (same literature machinery, per the intent record) adapted to
the search assignment, the acquisition tools and the one child slot; the child's task, credit, summary and return files were read
as shape.

## BLOCKED-ON-STORE-ACCESS (function, pattern)

- `findings/sample_context_evidence/finding_validity.py::FindingValidity` and `::target_eligible` (credit.py `current_assessments`): "library not carried" (`sqlite3`, `store._assessment_write_extent`). Intended: `records.current_assessments(scope)`, `records.is_current(ref)` and custody reads.
- `findings/sample_context_evidence/scientific_findings.py::FindingIdentity` (credit.py `lead_dispositions`; task.py `validate_lead` reads through `store.require`): "library not carried" (one private Store method).
- `tools/sample_context_evidence/tools.py::ToolRegistry` (task.py `run_access_tool`: every access and acquisition tool): "library not carried" (`store.db`, private Store methods).
- `literature/storage/literature_grading_storage.py::LiteratureA108GradingRepository` and `literature/storage/sample_context_evidence/literature_aggregation_storage.py::LiteratureA108AggregationRepository` (task.py `repositories`, `populate`, `authorize_source`; messages/internal_summary.py `saved_cells`): their sheet tables are not declared work tables. `saved_cells` raises `NotImplementedError('blocked_on_store_access:a108_sheet_cells:...: repository.fact_cells -> records.table(T).select')` when the parent requested components and a sheet exists. Old `repository.fact_cells(context, sheets, components=...)` -> intended `records.table(<family TableDeclaration>).select({'sheet': ref})`.
- `literature/grading/sample_context_evidence/literature_required_grading.py::execute` (task.py `reason`): called with the repository above; fails where the repositories fail.
- `messages/final_to_parent.py` `literature_current_scoring_sheets`: old `literature_sheet_updates.current_scoring_sheets(store, context)` -> intended `records.table(T).select`; raises where selected.
- The grading/aggregation subset check of the old `validate_received_report` (`repository.validate_fact_values`, `available_sheet_refs`, `fact_cells` over the parent's sheets): -> intended `records.table(T).select`; not carried.

## Unplaced old functions

- `decision_presentation.prepare_completed_work` and the return `literature_completed_work` (old `literature_work_report.completed_work`, not in `episode_support/`): selected -> `NotImplementedError('unplaced_old_function:literature_work_report.completed_work')` in messages/final_to_parent.py.
- `literature_examined_source_inputs` (old `literature_source_inputs.own_source_inputs`) and the source metadata of the received-fact display (old `literature_work_report.source_metadata`): modules not in `episode_support/`; not shown in the summary.
- `decision_completion`'s prompt renderer `render_literature_experimental_prompt` (old `library/literature_experimental_prompt`): not in `episode_support/` (`episode_support/literature/rendering/` has no such function). `decide` passes the context to the model unrendered.
- `LiteratureSummary.initial_decision_context` and `LiteratureConfiguration.reference_evidence` / `reference_parent_sources`: the root-only reference-evidence-parent context; this episode is not the annotation role; not carried.
- `LiteratureReferences._within_source` and `_artifact`, and the page branches of `_tool_arguments` and `_validate_page`: only reachable for an assigned page; the search assignment has no page; not carried.
- The storing of the cells of the child's admitted form in this episode's repositories (`received_form_references` -> `receive_cells`): a write in `read_from_child` (README section 5 item 4); not carried. The cells ride in the report.
- `validate_form` of the A108 axis: none exists. `messages/final_to_parent.py: validate_form` raises `NotImplementedError('validate_form_not_built:a108')`, as the old `validate_report` called it. Consequence: `final_to_parent` raises today and no run of this episode returns until the axis has a `validate_form` (the child behaves the same).
- Not carried, as checks of a commission: the old `_validate_assignment` scope checks, `literature_task_original_commission_mismatch`, `literature_task_typed_return_mismatch`, `literature_task_return_components_mismatch`, `literature_task_supplied_yield_binding_mismatch`, the child's `proposed_annotation_ref` equal to the parent's.
- `public.uniprot.search` and `public.uniprot.record` and `material.annotations` / `material.parse` / `material.from_source` of the old tool name lists: the A108 `ToolRegistry.catalog` offers none of them, so the old catalogue skipped them; not offered.

## Contract misfits

- new field: source_relevance_assessment scope (the old request scope), received_record_refs (the old binding-context received records): both new fields of `ASSIGNMENT_FORM`, as in the child.
- new field: source_relevance_assessment proposed_annotation_subject_refs / held_source_custody are summary keys (not assignment fields) that `msg_to_child` needs to name every record the child reads (decision T5): `msg_to_child` has no `records`, so the summary carries what it names.
- new field: the ChildCall arguments of `source_evidence_examination` are `{objective, page}`; the old model wrote the whole child assignment. The child's `literature_task` is the parent's task narrowed to the page source by `msg_to_child` (the child's own `commissioned_task` refuses a task outside its source).
- The source custody the old context listed was `assignment['source_refs']`, which a search assignment does not have (an empty list). The summary lists `search_result_refs` and the task's `source_refs`, because the model needs the artifact refs to fill the page of a child commission.
- Completion credit does not pass its target: credit is `credit_unit * len(answers)` and an assessment or screening task has at most one answer. (No `completion credit may pass its target` item.)
- Every run of this episode ends in `final_to_parent` with `NotImplementedError('validate_form_not_built:a108')` until the A108 axis has a `validate_form`.
- Accumulation (verified_source_leads) needs a cost above zero in the episode's settings (`settings['cost']`) or its controller never stops.
