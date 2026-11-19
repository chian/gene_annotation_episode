# a105 table_evidence_extraction: blocked, unplaced and misfit items

## BLOCKED-ON-STORE-ACCESS (function, pattern)
- `episode_support/literature/grading/experimental_activity_evidence/literature_required_grading.py::execute` (called by task.py::reason): "library not carried" (uses `store.db`-backed repository, `context.run_id`, `store._require`-style reads; the old `LiteratureContext`).
- `episode_support/literature/storage/experimental_activity_evidence/literature_assay_grading_storage.py::LiteratureAssayGradingRepository`: "library not carried" (constructor and `populate` use `store.db`, `sqlite_master`, `*_operations` ledger, `runtime`-keyed run/episode columns).
- `episode_support/tools/experimental_activity_evidence/tools.py::A105ToolRegistry`: "library not carried" (constructor does `store.db.execute('CREATE TABLE tool_operations ...')`; `_replayed`/`_save` use the ledger).
- `episode_support/findings/experimental_activity_evidence/finding_validity.py::FindingValidity, target_eligible` (credit.py::current_assessments): "library not carried" (sqlite, `store._assessment_write_extent`).
- credit.py::sheets (used by measured_answers, graded_experiment_answers, assembled_answers): old `current_sheet_refs(store, context, provider)` + `Repository.read(ref)` + `fact_cells` (raw tables `literature_*_operations`) -> intended `records.table(<sheet TableDeclaration>).select({...})`; no declared sheet tables exist; raises NotImplementedError where reached (not at the top of credit()).
- messages/final_to_parent.py::cells (selected `literature_quantity_cells`, `literature_assay_grading_cells`, `literature_a105_aggregation_cells`): old `repository.fact_cells(context, sheet_refs, components=requested)` -> intended `records.table(T).select(...)`; raises where a selection reaches it.

## Unplaced old functions / tools
- `source.sequence.scan`, `execution.estimate`: no A105 implementation or schema in the library (no `readers/sequence_operations/experimental_activity_evidence`, registry lacks native statistics); not offered.
- `source.xlsx.sheets`, `source.xlsx.rows`, `image.view`: offered with their schemas, but the A105 tool registry has no implementation (`tools/documents/experimental_activity_evidence/spreadsheet_tools.py` has the `Workbook` class but no `xlsx_native`; the old catalog came from the old services); the tool body raises `NotImplementedError('a105_tool_not_built:<name>')` after the `sheet_key` lock admission.
- Population route (`rate_population`, the `literature.*.populate` operations, the rate cell families of old `to_parent.py`, `scientific_records.py::_population_routes`): not built; only the three cell families the task kinds require are declared.

## Contract misfits
- Old 97308b94c files unreadable: the checkout has no git history; the carry used the intent record, the old-call table and the library (and the sibling A104 table episode's shape). Details of old formulas (credit, validate_received_report) may differ from the old files.
- new field: table_evidence_extraction scope, received_record_refs (assignment), finding.source_claim / source_subject / qualification / assessment_findings (return), requested_* components kept under old names.
- The grader coupling (AGENTS.md "Required literature evidence processing") is in `literature_required_grading.execute`, which needs a grading repository and a `LiteratureContext` of the old form; the episode builds them from `ctx` as the old episode did, and fails there until the library is carried.
- No A105 `validate_form`: not called here (validate_report validates only the episode's own FINDING_FORM).
- completion credit cannot pass its target: a105_experiments counts at most one answer per commissioned experiment; the other completion kinds count at most one answer.

## Not repaired
- Old source unreadable: the checkout is not a git repository here, so bodies of the old credit formula, validate_received_report and source_operations could not be compared with 97308b94c.
- BLOCKED-ON-STORE-ACCESS, library not carried: finding_validity.py, literature_assay_grading_storage.py, tools.py (store.db / sqlite3 / store._assessment_write_extent), reached from credit.py FindingValidity/target_eligible, task.py A105ToolRegistry and LiteratureAssayGradingRepository.
- Tools not built: image_view, source_xlsx_sheets, source_xlsx_rows (a105_tool_not_built:<name>); no library implementation exists.
- Completion credit may pass its target: for a105_experiments the target is credit_unit times the number of experiments, and the old credit formula is kept unchanged.
- New fields: scope, received_record_refs (assignment); finding with source_claim, source_subject, qualification, readings, assessment_findings (return).
- Population route (13 display contexts, rate cell families, _population_routes) is unplaced: population route not built. Its rows in the Carried over table are now labeled "episode function (unplaced)", not machinery.
