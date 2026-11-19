# source_evidence_examination (A108): blocked, unplaced and contract misfits

All library paths are under `gene_annotation_episode/episodic_workflow/episode_support/`.

## Process note

The old files of this episode could not be read: the repository in this environment has no git history
(`git show 97308b94c:<path>` fails, no `.git` directory). The folder was carried from the intent record
(`episode_intent/a108/...source_evidence_examination.md`), the function list `runs/carry_over/functions/...tsv`, the finished
carried-over children of this folder (read as data), and the finished A103 sibling head (shape of the parent: slots,
`msg_to_child`, `read_from_child`). Wording of the old role instruction is from the intent record. Anything the intent record
did not state was not reconstructed. The earlier port stub `episode.py` (class on `LiteratureBinding`) was deleted; no
other hook-era file was in the folder.

## BLOCKED-ON-STORE-ACCESS (function, pattern)

- `findings/sample_context_evidence/finding_validity.py::FindingValidity` and `::target_eligible` (credit.py: `current_assessments`): "library not carried" (`store.db`, `store._assessment_write_extent`). Intended: `records.current_assessments(scope)`, `records.is_current(ref)` and custody reads.
- `findings/sample_context_evidence/scientific_findings.py::FindingIdentity` (credit.py: `lead_dispositions`): "library not carried" (one raw Store site).
- `tools/sample_context_evidence/tools.py::ToolRegistry` (task.py: `run_access_tool`): "library not carried" (16 raw Store sites).
- `literature/storage/literature_grading_storage.py::LiteratureA108GradingRepository` and `literature/storage/sample_context_evidence/literature_aggregation_storage.py::LiteratureA108AggregationRepository` (task.py: `repositories`, `populate`, `authorize_source`; messages/internal_summary.py `saved_cells`): their sheet tables are not declared work tables. `saved_cells` raises `NotImplementedError('blocked_on_store_access:a108_sheet_cells:...: repository.fact_cells -> records.table(T).select')` when the parent requested components and a sheet exists. Old call `repository.fact_cells(context, sheets, components=...)` -> intended `records.table(<family TableDeclaration>).select({'sheet': ref})`.
- `literature/grading/sample_context_evidence/literature_required_grading.py::execute` (task.py: `reason`): called with the repository above; the coupled commit and sheet save is inside one `ctx.store.transaction()` for a source lead. Fails where the repositories fail.
- final_to_parent `literature_current_scoring_sheets`: old `literature_sheet_updates.current_scoring_sheets(store, context)` -> intended `records.table(T).select`; raises where selected.

## Unplaced old functions

- `decision_presentation.prepare_completed_work` and the fact `literature_completed_work` (old `literature_work_report.completed_work`, not in `episode_support/`): selected -> `NotImplementedError('unplaced_old_function:literature_work_report.completed_work')` in messages/final_to_parent.py.
- `literature_examined_source_inputs` (old `literature_source_inputs.own_source_inputs`) and the source metadata of the received-fact display: modules not in `episode_support/`; not shown in the summary.
- `validate_form` of the A108 axis: none exists. `messages/final_to_parent.py: validate_form` raises `NotImplementedError('validate_form_not_built:a108')`, as the old `validate_report` called it. Consequence: `final_to_parent` raises today and no run of this episode returns until the axis has a `validate_form` (the three children behave the same).
- Not carried, as checks of a commission: the old `_validate_page` Store checks, `literature_task_original_commission_mismatch`, `literature_task_typed_return_mismatch`, `literature_task_return_components_mismatch`.

## Contract misfits

- new field: source_evidence_examination scope, received_record_refs (ASSIGNMENT_FORM; the old episode took them from its request and binding context).
- new field: source_evidence_examination finding (RETURN_FORM: typed investigation finding; the old form was written by the parent). Child findings are in three different forms (table: `assessment_findings`; ordered: `findings`; targeted: `assessment_refs` only), so `read_from_child` branches on the slot.
- The passage child (`passage_evidence_extraction`) declares the cell fields but raises where they are selected. `msg_to_child` therefore never selects cells from it; a parent that requests A108 components gets cells only from the table and ordered children and its own sheets.
- Every selection and every nested `record_refs` field of a child's `finding` (`committed_record_refs`, `graded_sheet_refs`, `assessment_refs`) is assumed to be passed in custody; the parent's assessment credit reads the children's committed assessments through `records`.
- completion credit may pass its target: not for `source_answer` (assessment gives at most one item, screening one, so credit is at most `credit_unit` = target). `verified_source_leads` is accumulation and has no target.
- A108 screening credit counts the own `no_applicable_evidence` declarations only, as the old credit did; a child's screening answer is returned but not counted.
- The old `yield_settings` of the task and the owner's yield bindings are the episode's `settings` (`cost`, `parameters`); the old case "no private yield binding -> runner default" does not exist.
- No tests existed in the folder; no old test was brought back. `retired_tests/...source_evidence_examination.tsv` holds only the header.
