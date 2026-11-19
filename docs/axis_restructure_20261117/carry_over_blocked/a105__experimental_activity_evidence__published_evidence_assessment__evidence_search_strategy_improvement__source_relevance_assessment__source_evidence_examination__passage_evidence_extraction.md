# a105 passage_evidence_extraction: blocked, unplaced and contract misfits (19 November 2026)

Every call below is written against its intended custody-aware form, raises `RuntimeError('library_not_carried:...')`
at the point of the call (never at the top of `credit` or of a tool) and is reported with its exact pattern.

## BLOCKED-ON-STORE-ACCESS

| Function | Pattern (old call -> intended call) |
|---|---|
| `episode_support/tools/experimental_activity_evidence/tools.py::A105ToolRegistry` | library not carried: `A105ToolRegistry(store, ...)` runs `store.db.execute('CREATE TABLE IF NOT EXISTS tool_operations ...')` -> no ledger (the system journals attempts; `ctx.operation_key`); called from `task.py::run_access_tool` |
| `episode_support/literature/grading/experimental_activity_evidence/literature_required_grading.py::execute` | library not carried: `store.commit_reasoning(payload, scope, key, account_owner=(run_id, episode_id))` -> `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)`; `dataclasses.replace(context, received_record_refs=...)` on the old BindingContext operand -> scope and held refs passed as parameters; called from `task.py::grading_execute` (the coupled commit + grading sheets) |
| `episode_support/literature/storage/experimental_activity_evidence/literature_assay_grading_storage.py::LiteratureAssayGradingRepository` | library not carried: `store.db.execute(SELECT/INSERT ... operations_table / sqlite_master / records)` -> declared work tables read with `records.table(T).select` / written with `ctx.store.table(T).put`; called from `task.py::grading_execute`, `credit.py::graded_experiment_answers` |
| `episode_support/literature/storage/experimental_activity_evidence/literature_aggregation_storage.py::LiteratureA105AggregationRepository` | library not carried: same `store.db` operations-table pattern -> work tables; called from `credit.py::assembled_answers`, `task.py::run_population` |
| `episode_support/literature/storage/experimental_activity_evidence/literature_quantity_storage.py::LiteratureQuantityRepository` | library not carried: same pattern; called from `credit.py::measured_answers`, `task.py::run_population` |
| the other 32 repositories of `task.py::POPULATIONS` / `messages/internal_summary.py::FAMILIES` (`literature/storage/experimental_activity_evidence/literature_*_storage.py`, `<Repository>(store, run_id)`) | library not carried: `store.db` operations tables, `sqlite_master`, `INSERT INTO records` -> work tables; called from `task.py::run_population`, `messages/internal_summary.py::family_cells` |
| `episode_support/literature/storage/experimental_activity_evidence/literature_sheet_updates.py::current_sheet_refs`, `current_scoring_sheets` | library not carried: `store.db` (15 sites) -> work tables; called from `credit.py` and `messages/internal_summary.py::report_facts` |
| `episode_support/findings/experimental_activity_evidence/finding_validity.py::target_eligible`, `FindingValidity` | `store._assessment_write_extent(assessment)` -> intended `records.assessment_write_extent(assessment)` (store-access.md "No replacement yet"); `FindingValidity` also keeps a `sqlite3.connect('')` spool; called from `credit.py::current_assessments` |
| `task.py::assay_grading_source_cells` | the per-family repository the assay-grading repository reads while grading (old `_assay_grading_source_cells`): same family pattern |

## Unplaced old functions

| Old | Reason |
|---|---|
| `decision_presentation.py::prepare_completed_work` | its `completed_action_reports` (root.a105.episode_work_report) has no module in the library; the completed-action reports are not shown |
| `internal_summary.py::_owned_population_task_sources`, `_population_task_context` | SQL on the old operations tables and `runtime_actions`, and the run's flags, which a summary does not have |
| `internal_summary.py::_concentration_window_display_context`, `_measurement_comparison_display_context`, `_summary_precision_display_context`, `_endpoint_signal_display_context`, `_controlled_response_bindings`, `_gel_bindings`, `_gel_display_context`, `_received_fact_display_context`, `_native_rate_display_context`, `_native_rate_domain_display_context`, `_native_rate_meaning_display_context` | they show the possessed rows of the family repositories (old Store form) and need the run's flags; `internal_summary` has no settings and `decide` has no records |
| `literature_source_inputs.own_source_inputs`, `literature_work_report.completed_work`, `literature_source_access.rejection_detail`, `literature_task_selection` (old `root/a105/library` names) | no module of that name in the library after the 18 November placement: `literature_examined_source_inputs` and `literature_completed_work` are not shown; the `detail` of `literature_reading_outside_assigned_source` carries the reference only |
| `source_references.py::LiteratureReferences._artifact` | no caller in the old episode files |
| tools `source.sequence.scan`, `image.view`, `source.xlsx.sheets`, `source.xlsx.rows`, `execution.estimate` | the A105 tool library implements none (`A105ToolRegistry.catalog`); the old catalog was the registry's catalog intersected with `_ACCESS_TOOLS`, so the same five are not offered now |

## Contract misfits

- Tool names: a tool name is `[a-z][a-z0-9_]*`, so `source.read` is `source_read` and `literature.assay_grading.populate` is
  `literature_assay_grading_populate` ("names both sides use are the old names, unchanged" cannot hold for tools).
- `validate_form` is not built for A105: the old `validate_report` called it; it is not called here (no `validate_form_not_built:experimental_activity_evidence` is reached because nothing calls it).
- new field: passage_evidence_extraction scope (the old episode took the scope from its request).
- new field: passage_evidence_extraction received_record_refs (the old episode took what it received from its binding context). The parent must name every record this episode reads (the page source and its artifact, the sources it derives from, the proposed annotation and its hypothesis, the records of the commissioned task such as sheets): a passed record does not bring the records it names.
- The 39 other `requested_*` properties of the old assignment schema are declared as plain optional lists (the old enums are the family libraries' COMPONENTS, checked where the family is read); only the three of the task kinds have options.
- The RETURN_FORM declares the cell families as list fields with a shortened meaning, without an item form (the old `report_schema` rows are the family libraries' schemas).
- The coupling of grading and interpretation (AGENTS.md) is unconditional: the old `assay_grading_population` flag (default false, kept false in `task.population_entries`) no longer gates it; the flag now only gates the `literature.assay_grading.populate` and `literature.a105.aggregate` operations offered with `rate_population`.
- `internal_summary` cannot see the commission's `selection`, so it reads the cells of every requested family each unit (requested family means a non-empty `requested_*` array); a summary without the settings cannot show the population display contexts.
- Completion credit cannot pass its target: every task kind counts at most `credit_unit` (one answer) or one answer per requested experiment, the target being `credit_unit` times the same number.
- `credit.py` raises `RuntimeError('library_not_carried:...')`, not `NotImplementedError`, at the library points (the firm rule on `credit.py`).
- settings keys read by this episode: `cost` and `parameters` (controller), `rate_population` and the old population flags, `tool_registry`, `knowledge_library_directory`.

## Not repaired

- `literature_completed_work` is declared selectable but has no producer: `literature_work_report.completed_work` has no module in the library (BLOCKED, library not carried). `final_to_parent` now raises `ValueError('literature_report_fact_not_available:<name>')` when a selected report fact is not in the summary, and `report_facts` raises `library_not_carried` when assay grading components are requested, so selection fails explicitly instead of with a KeyError.
- BLOCKED-ON-STORE-ACCESS (library not carried): `A105ToolRegistry` (access tools), `literature_required_grading.execute` (grading sheet), the family repositories (`run_population`, `library_repository`, `family_cells`, `report_facts`), `current_assessments` (`store._assessment_write_extent`).
- Not placed (contract limit): the population display-context functions and `decision_presentation.prepare_completed_work`; tools `source.sequence.scan`, `image.view`, `source.xlsx.sheets`, `source.xlsx.rows`, `execution.estimate` are not in the library.
