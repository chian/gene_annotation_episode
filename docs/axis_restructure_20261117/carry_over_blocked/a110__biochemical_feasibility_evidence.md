# a110/biochemical_feasibility_evidence: blocked, unplaced and misfit items (19 November 2026)

Folder: `gene_annotation_episode/episodic_workflow/root/a110/biochemical_feasibility_evidence/` (head files only). Import of `episode.py` and `tests/test_episode.py` pass (run `runs/cov_a110_01_u176_2`). A real run of this episode cannot start yet: the first unit it offers is the lookup `process_entry`, which raises (the process library and tool library have no placed module), and `credit` at the initial summary calls a library family that is still in its old form.

## BLOCKED-ON-STORE-ACCESS (library not carried; the call stays as written)

| function | pattern |
|---|---|
| `episode_support/findings/biochemical_feasibility_evidence/investigation_progress.py::ScientificFindingProgress.read_details` and `project_finding_progress` (called in `credit.py` `finding_progress`, hence `credit` and `messages/internal_summary.py`) | library not carried: `store._require(ref, {'assessment'})`, `store.db.execute('SELECT record_ref FROM current_revisions ...')`, `store.read_snapshot()` (not offered on `records`), a spool `sqlite3` connection, and the private helpers of `finding_validity.py` / `scientific_findings.py` (`_assessment_write_extent`, `_record_roots`, `_assert_library_write_scope`). Intended: `records.require`, `records.is_current(ref)` / `records.current_assessments(scope)`, `records.list('assessment', scope)` |
| `episode_support/tools/biochemical_feasibility_evidence/tools.py::ToolRegistry` (called in `task.py` `tool_catalog` and `scientific_tool`) | library not carried: the constructor runs `store.db.execute('CREATE TABLE IF NOT EXISTS tool_operations ...')` and `store.db.commit()`; the operations use raw `store.db`, `store._require`, `store.path` artifact files; intended `ctx.store` operations of store-access.md; the `tool_operations` ledger is replaced by `ctx.operation_key` |
| `episode_support/jobs/sequence_and_context_sources/component_axis_native_hpc.py::received_components`, `execution_findings` (called in `task.py` `received_evidence`) | library not carried: `store.db` over the `component_axis_native_*` tables (`CREATE TABLE`, `sqlite_master`, `INSERT OR IGNORE`); intended: declared work tables read with `records.table(T).select(...)` |

## Unplaced old functions (no placed module; the use raises explicitly where it is reached)

| old | reason |
|---|---|
| `biochemical_feasibility_evidence_library` (`library.resolve`, `evidence_axis_instruction_view`) and `evidence_axis_instructions.instruction_view` | `module_of_that_name_now` is none; used by `task.py` `process_entry` (raises `old_module_not_placed:...`) |
| tool library (`resolve_tool_info`, `resolve_invocations`), `scientific_tool_retrieval` | no module; `process_entry`, `process_revise` |
| `biochemical_feasibility_evidence_records` (`SELECTION_VERSION`, `validate_selection`, `validate_child_selection`, `scientific_digest`, `scientific_invocation_ref`, `validate_revision_origin`) | no module; `process_revise` raises; the selection version is any text in `messages/read_from_parent.py` |
| `execution_planning` (`read`, `catalog`) | no module; `process_execution` raises |
| `a110_qualification` (`FACT_SOURCE`, `received`, `fact_sources`) | no module: the qualification fact source is not declared in `RETURN_FORM`; `to_parent.qualification_facts`, `internal_summary.received_qualification_context` raise in `received_evidence` |
| `component_axis_reports` (`current_scoring_sheets`, `received_reports`, `mark_native_execution`, `report_axis`, `resolve_report`, `validate_native_return_channels`, `SCORING_FACT`) | no module: the scoring sheets fact is not declared in `RETURN_FORM` (`current_report_facts`, `_component_scoring_facts` raise in `received_evidence`); `_validate_component_axis_report` has no JSON-schema report to validate any more |
| `component_axis_execution_context.prepared_assignments` | no module; `received_evidence` raises |
| `biochemical_feasibility_evidence_reports` (`build_process_result`, `merge_process_results`, `project_process_result`, `validate_process_result`, `report_sources`) | no module; selecting `biochemical_feasibility_evidence_results` raises `old_module_not_placed:...` |
| `component_axis_workflow` (`INSTRUCTIONS['A110']`, `finding_progress`, `task_context`) | no module. The A110 axis guidance, `TASKS`/`task_context` and the finding unit 1 were taken from the earlier port's copy `axis_task_context.py` in this folder before it was deleted (it was a working-tree file of this folder, not the old shared root) |
| `library.scientific_decision_presentation` (`render_episode_steering`, `_section`, `_table`, `_values`, ...), `library.execution_initial_information.presentation`, the old result-reader catalog (`catalog.readers`, `catalog.received`) | no module: `initial_information` and `received_execution_information` are not carried (unplaced); the TASK prompt is `task.prompt_sections` as structured sections; the steering content is credit, the yield table and the time accounting in the decision context |
| old workflow services (`resource_context`, `shared_information_context`, `child_option_information`) and the common catalogue entries `process.search`, `process.entry` (library lookups), `process.sources`, `process.tools`, `shared.request_information`, `shared.publish_information`, `shared.resolve_information_need`, `shared.read_information`, `shared.list_information`, `episode.annotation_score`, `episode.monitoring_information`, `episode.estimate_wait` | services of the old runner, no old function in this folder and no placed home; not offered. `episode.history` and `episode.credit` are in the decision context |

## Contract misfits

- new field: biochemical_feasibility_evidence scope
- new field: biochemical_feasibility_evidence received_record_refs
- new field: execution_job_submission record_refs (filled by this head, declared by the child)
- new field: execution_job_submission handoff_unit
- new field: execution_job_submission acquired_record_unit
- new field: execution_job_submission scientific_task
- new field: execution_result_acquisition resource_kind
- new field: execution_result_acquisition acquired_record_unit
- new field: execution_progress_assessment information_unit
- new field: hpc_work_planning scope
- new field: hpc_work_planning input_refs
- new field: published_evidence_assessment scope
- new field: published_evidence_assessment finding_unit
- new field: published_evidence_assessment received_record_refs
- `proposed_annotation_ref` was text (optional, required whenever yield bindings are configured); it is a `record_refs` field holding exactly one reference, required, so that the hypothesis is passed in custody. `evidence_refs` is `record_refs` for the same reason.
- `SELECTION_VERSION` lives in an unplaced module: the selection `version` is any non-empty text; the library resolution of the selection is a check of a commission and is not carried.
- The A110 finding unit is the constant 1 (`finding_progress()` of the old `component_axis_workflow`, as the earlier port's copy had it); the assignment's `context.evidence_task.credit_unit` is validated when present and, as in the old A110 `task_projector`, not read as the unit.
- `final_to_parent` always raises `NotImplementedError('validate_form_not_built:a110')` after the recorded-fact checks (A110 has no `validate_form`); every A110 child does the same, so no A110 Episode returns until it is built.
- Old return facts not declared because the module that named them has no placed home: the A110 qualification source and the component scoring sheets fact; the library `report_sources` other than `committed_record_refs`.
- Selectable facts of a child that are not offered to the model because selecting them raises in the child: `execution_result_origin` (launch and results), `literature_reaction_cells`, `literature_reaction_semantic_cells`. The old A110 axis guidance still tells the model to ask the literature child for the reaction cells.
- The A110 axis guidance text was reworded where it described removed mechanisms: the parent-written closed return schema and `episode.return_contract` sentences of `_NATIVE_RETURN_GUIDANCE` became "select these facts when commissioning it"; the `shared.*` sentences of `scientific_guidance` and the wait and report-form sentences of `_TASK_TEXT` were dropped. `task_context(name)` (the identity check of `a110_task`) keeps its old text unchanged, including its sentence about `shared.*`, because the commissioner builds the same record.
- `yield_estimator.py` reads `settings['yield_bindings']` (the old `yield_bindings` mapping `{task: {kind, cutoff, parameters, credit_definition}}`), not a flat `cutoff`/`parameters`; the caller of `link` sets the binding's `continuation` entry that way, plus `child_roles`, `handoff_unit`, `acquired_record_unit`, `information_unit`, `tool_registry` and the optional directories. A cost of zero never stops the accumulation controller.
- The first two units the task offers are lookups (`process_entry`, `received_evidence`), both of which raise today.
- `root/axes.py` (outside this job) still imports the deleted hook-era modules of this folder (`home`, `head_episode`, `runtime_contract`, `unit_source`); it breaks until the root is carried.
- No A105/A108 evidence-processing sheet applies to A110, so none is coupled in the action.
- Process note: `/home/chia/repos/gene_annotation_episode` has no `.git`; old files were read with `git show 97308b94c:<path>` from `/home/chia/repos/gene_annotation_episode_disk` (read only). One `git grep` for the names of two fact sources also listed lines of the old shared root (`a110_qualification.py`, `component_axis_reports.py`); those strings were not used.

## Not repaired

- credit/internal_summary/yield_controller: investigation_progress.py in episode_support still old store form (BLOCKED-ON-STORE-ACCESS, library not carried).
- tool_catalog/scientific_tool: episode_support/tools/biochemical_feasibility_evidence/tools.py ToolRegistry (library not carried).
- received_evidence: component_axis_native_hpc (library not carried); process_entry/process_revise/process_execution and scoring-sheet reads: old modules not placed.
- final_to_parent: validate_form_not_built:a110 (no A110 validate_form).
- RETURN_FORM lacks qualification, component scoring sheets, execution_result_origin and literature_reaction_* facts (contract misfit).
