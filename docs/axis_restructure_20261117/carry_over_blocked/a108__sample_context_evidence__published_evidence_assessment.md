# published_evidence_assessment (A108): blocked, unplaced and contract misfits

All library paths are under `gene_annotation_episode/episodic_workflow/episode_support/`.

## Process note

The working repository (`/tmp/ramrepo`) has no `.git`; the old files were read with
`git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>` (only this episode's own files). The folder held
the hook-era `episode.py` (class on `LiteratureBinding`), `literature_binding.py`, `literature_credit.py` and
`literature_source.py`; all four were deleted before the new files were written. No tests existed at the old commit or in the
working tree (`retired_tests/a108__sample_context_evidence__published_evidence_assessment.tsv` holds the header only). A
normalized diff of the old files shows this episode and its child `evidence_search_strategy_improvement` differ only in role,
role instruction, assignment version and source field, child role and docstrings; this episode is a private copy of the finished
child's files adapted to those places (credit, yield, tools, summary and return are identical in the old code). No import of the
child folder: its goal, `read_from_parent` and `final_to_parent` were read as data and `msg_to_child` / `read_from_child` written
against them.

## BLOCKED-ON-STORE-ACCESS (function, pattern)

- `findings/sample_context_evidence/finding_validity.py::FindingValidity` and `::target_eligible` (credit.py `current_assessments`): "library not carried" (`sqlite3`, `store._assessment_write_extent`). Intended: `records.current_assessments(scope)`, `records.is_current(ref)` and custody reads.
- `findings/sample_context_evidence/scientific_findings.py::FindingIdentity` (credit.py `lead_dispositions`; task.py `validate_lead` reads through `store.require`): "library not carried" (one private Store method).
- `tools/sample_context_evidence/tools.py::ToolRegistry` (task.py `run_access_tool`: every access and acquisition tool): "library not carried" (`store.db`, private Store methods).
- `literature/storage/literature_grading_storage.py::LiteratureA108GradingRepository` and `literature/storage/sample_context_evidence/literature_aggregation_storage.py::LiteratureA108AggregationRepository` (task.py `repositories`, `populate`, `authorize_source`; messages/internal_summary.py `saved_cells`): "library not carried"; their sheet tables are not declared work tables. `saved_cells` raises `NotImplementedError('blocked_on_store_access:a108_sheet_cells:...: repository.fact_cells -> records.table(T).select')` when the parent requested components and a sheet exists. Old `repository.fact_cells(context, sheets, components=...)` -> intended `records.table(<family TableDeclaration>).select({'sheet': ref})`.
- `literature/grading/sample_context_evidence/literature_required_grading.py::execute` (task.py `reason`): "library not carried"; called with the repository above, fails where the repositories fail.
- `messages/final_to_parent.py` `literature_current_scoring_sheets`: old `literature_sheet_updates.current_scoring_sheets(store, context)` -> intended `records.table(T).select`; raises where selected.
- The grading/aggregation requested-subset check of the old `validate_received_report` (`repository.validate_fact_values`, `available_sheet_refs`, `fact_cells` over this episode's sheets): -> intended `records.table(T).select`; not carried.

## Unplaced old functions

- `decision_presentation.prepare_completed_work` and the return `literature_completed_work` (old `literature_work_report.completed_work`, not in `episode_support/`): selected -> `NotImplementedError('unplaced_old_function:literature_work_report.completed_work')` in messages/final_to_parent.py.
- `literature_examined_source_inputs` (old `literature_source_inputs.own_source_inputs`) and the source metadata of the received-fact display (old `literature_work_report.source_metadata`): modules not in `episode_support/`; not shown in the summary.
- The prompt renderer `render_literature_experimental_prompt` (old `library/literature_experimental_prompt`, used by `decision_completion`): not in `episode_support/` (`literature/rendering/` has no such function). `decide` passes the context to the model unrendered.
- `LiteratureSummary.initial_decision_context` and `LiteratureConfiguration.reference_evidence` / `reference_parent_sources`: the root-only reference-evidence-parent context; this episode is not the annotation role; not carried.
- `LiteratureReferences._within_source` and `_artifact`, and the page branches of `_tool_arguments` and `_validate_page`: only reachable for an assigned page; this episode has no assigned page; not carried.
- The storing of the cells of the child's admitted form in this episode's repositories (`received_form_references` -> `receive_cells`): a write in `read_from_child` (README section 5 item 4); not carried. The cells ride in the report.
- `validate_form` of the A108 axis: none exists. `messages/final_to_parent.py: validate_form` raises `NotImplementedError('validate_form_not_built:a108')`, as the old `validate_report` called it. Consequence: `final_to_parent` raises today and no run of this episode returns until the axis has a `validate_form` (as for its child).
- Not carried, as checks of a commission: the old `_validate_assignment` scope and source-kind checks, `literature_task_original_commission_mismatch`, `literature_task_typed_return_mismatch`, `literature_task_return_components_mismatch`, `literature_task_supplied_yield_binding_mismatch`, the child's `proposed_annotation_ref` equal to the parent's.
- `public.uniprot.search`, `public.uniprot.record`, `material.annotations`, `material.parse`, `material.from_source` of the old tool name lists: the A108 `ToolRegistry.catalog` offers none, so the old catalogue skipped them; not offered.

## Contract misfits

- new field: published_evidence_assessment `scope` (the old request scope) and `received_record_refs` (the old binding-context received records): new fields of `ASSIGNMENT_FORM`.
- new field: published_evidence_assessment `proposed_annotation_subject_refs` and `held_source_custody` are summary keys (not assignment fields) that `msg_to_child` needs to name every record the child reads (decision T5): `msg_to_child` has no `records`, so the summary carries what it names.
- new field: the ChildCall arguments of `evidence_search_strategy_improvement` are `{objective, prior_search_refs, question_context_refs}`; the old model wrote the whole child assignment. The child's `literature_task`, proposed annotation, requested components, scope and received records are copied by `msg_to_child` from this episode's own parent input. `action` rejects, as an invalid model answer, a child call that names a record this episode does not hold (provisional held-record check); `msg_to_child` itself checks nothing.
- new field: the child's selection is derived from the task (`verified_source_leads` -> `literature_source_lead_dispositions`, screening -> `literature_screening_answers`, plus the cell families when components were requested); the old parent wrote the whole return form.
- The old `LiteratureTaskCredit` for an assessment commission caps itself at one answer, so credit is at most `credit_unit` and the completion controller target `credit_unit` is not passed; for screening the same (one answer). No completion-credit-may-pass-target misfit. `verified_source_leads` uses the accumulation controller (credit unbounded).
- Round-trip of the child's returned `finding` shape: `read_from_child` reads `finding['assessment_findings']`, `['committed_record_refs']`, `['graded_sheet_refs']` of the child's declared FINDING_FORM (read from its `final_to_parent.py`); both agree today.
- `episode.py create_binding_tree` (old home factory over the seven A108 bindings) is not carried (machinery; no table of bindings).
