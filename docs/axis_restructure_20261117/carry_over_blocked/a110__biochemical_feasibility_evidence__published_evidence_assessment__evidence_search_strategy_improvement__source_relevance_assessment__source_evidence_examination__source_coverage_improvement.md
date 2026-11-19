# source_coverage_improvement (A110): blocked, unplaced and misfit items

## BLOCKED-ON-STORE-ACCESS (library not carried)

- function = episode_support/findings/biochemical_feasibility_evidence/investigation_progress.py::project_finding_progress, pattern = "library not carried" (uses store.read_snapshot, a sqlite3 spool, store._require, store.db; old call `project_finding_progress(store, scope, policy, known_assessment_refs=...)` -> intended call with `records`). Called in credit.py as written.
- function = episode_support/tools/biochemical_feasibility_evidence/tools.py::ToolRegistry, pattern = "library not carried" (store.db tool_operations table, store._require). Called in task.py run_access_tool as `ToolRegistry(ctx.store, ...)`.
- old SQL over population tables through services.workflow.store.db (LiteratureSummary._owned_population_task_sources, _rate_facts, received_cells, current_sheet_refs) -> intended `records.table(T).select(...)` over a declared work table; not written: the reaction route's modules are not in the library (see unplaced).

## Unplaced old functions

- literature.reaction.populate / literature.reaction.source.populate (tools declared in task.py, raise NotImplementedError('a110_reaction_population_not_built:...')): `literature_component_binding`, `reaction_population`, `reaction_source_selection`, `literature_reaction_storage`, `reaction_native_observations` are not in episode_support (A110 `literature_assay_inputs` does not exist; only other axes have a copy).
- LiteratureNumericalReportFacts (_rate_fact_sources, _rate_facts), LiteratureReceivedReports.validate_received_report, LiteratureSummary._owned_population_task_sources and _population_task_context, LiteratureReactionRecords: same missing modules.
- present_source_context: the literature experimental prompt renderer is keyed on the reaction work context that is not built; not carried.

## Contract misfits

- new field: source_coverage_improvement scope, finding_unit, received_record_refs (ASSIGNMENT_FORM; old scope came from the request, old credit unit from services.scientific_credit, old received records from the binding context).
- new field: source_coverage_improvement finding (RETURN_FORM; the old parent wrote the report form): written, interpretation, windows_read, passages, qualification.
- The old reaction fact sources (reaction cells, semantic cells, native observations) and the assignment properties of literature_component_binding.assignment_schema_fields() cannot be declared: their module is not in the library.
- validate_form_not_built:biochemical_feasibility_evidence: the axis has no validate_form; FINDING_FORM.admit is the check of the report's own form.
- Parent side: the commissioning parent (source_evidence_examination) must send assignment keys version, page, selection (one window), scope, finding_unit, received_record_refs; no selection fields exist (RETURN_FORM has only credit and finding).
- Not carried as checks of a commission (rule 1): source_offset_out_of_bounds, page custody (literature_source_artifact_mismatch), parent-source containment.
- Credit: the accumulation controller has no target; credit counts retained findings via project_finding_progress (blocked as above). The cost must be above zero in settings or the Episode never stops.
