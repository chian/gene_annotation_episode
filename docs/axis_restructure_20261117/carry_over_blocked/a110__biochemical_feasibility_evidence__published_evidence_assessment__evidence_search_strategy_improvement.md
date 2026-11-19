# evidence_search_strategy_improvement (A110): carry-over items

## BLOCKED-ON-STORE-ACCESS

- credit.py `credit` -> `findings/biochemical_feasibility_evidence/investigation_progress.py::project_finding_progress`
  - pattern: "library not carried" (old call `project_finding_progress(store, ...)` with `store.read_snapshot`, a
    `sqlite3` spool, `store._require`, `store.db` -> intended call with `records`; the call stays as written, it is
    handed `records`).
- task.py `run_library_tool` -> `tools/biochemical_feasibility_evidence/tools.py::ToolRegistry`
  - pattern: "library not carried" (`ToolRegistry(store, ...)` runs `store.db.execute('CREATE TABLE IF NOT EXISTS
    tool_operations ...')` and its operations use `store.db`, 18 sites -> intended: handed `ctx.store`, custody
    operations and a declared work table for `tool_operations`; the call stays as written with `ctx.store`).

## unplaced_old_functions

- contracts.py `_population_catalog`: needs `literature_component_binding.population_catalog_entries` (A110), not in `episode_support/`.
- initial_information.py `initial_information`: reads the old `catalog.readers(<binding_path>, context)` and
  `execution_initial_information.presentation.resource_information`, which are not in `episode_support/`.
- received_execution_information.py `received_execution_information`: result-reader selection of the old catalog
  (`catalog.configured/received`); no counterpart in the new form.
- task_presentation.py `present_source_context`: renders the literature experimental task prompt from the old state
  frames (deleted conversation state) through `literature_source_presentation`, which is not in `episode_support/`;
  `decide` passes the context in `ModelRequest.context`.
- source_operations.py `_materialize_text_arguments`: needs `literature_assay_inputs.materialize_text_witness_inputs`
  of A110 and the reaction repository (not in the library); part of the reaction population route.
- internal_summary.py `_owned_population_task_sources`, `_population_task_context`, `facts`; numerical_report_facts.py
  (2 classes/methods); reaction_records.py (3); received_reports.py (7 rows): the reaction population library
  (`literature_component_binding`, `reaction_population`, `reaction_source_selection`, `literature_assay_inputs` of
  A110, `literature_reaction_storage`, `reaction_native_observations`, `reaction_population_contracts`,
  `literature_sheet_updates`) is not in `episode_support/`; the reaction fact sources are not declared in
  `RETURN_FORM`; the tools `literature_reaction_populate` and `literature_reaction_source_populate` raise
  `NotImplementedError('a110_reaction_population_not_built:...')` and are not offered.
- parent_context.py `initial_decision_context`, `contract_information_profile`: root reference-evidence parent only /
  old contract information freezing; no place.
- source_custody.py `LiteratureSourceCustody` and its methods: reached only for an assignment with a page; this
  assignment has none.

## contract_misfits

- new field: evidence_search_strategy_improvement scope (old request scope), finding_unit (the old scientific
  credit unit), received_record_refs (old binding-context received records) in `ASSIGNMENT_FORM`.
- new field: evidence_search_strategy_improvement finding (typed finding: written, interpretation, source_refs,
  assessments, qualification); the old return was the parent's requested form filled from reaction rate fact sources.
- The old assignment properties of `literature_component_binding.assignment_schema_fields()` are not declared
  (module not in the library): a commission that sends them is refused.
- The old `validate_report` called `validate_form`; the A110 axis has no `validate_form`
  (`NotImplementedError('validate_form_not_built:a110')` would be the call); `final_to_parent.validate_report`
  checks the report against the episode's own `FINDING_FORM` and held sources instead.
- `yield_estimator.py`: the old episode named no estimator; `AccumulationYieldController` chosen (README 7b); its
  settings must carry `cost` above zero and `parameters`.
- `msg_to_child` reads the sources and their artifacts from `summary['held_sources']` (built from
  `view.records.list('source')`) to name every record the child needs; a source the model names that is not held fails the commission with KeyError (no check in `action` on the child call).
- tests/test_binding.py does not import the child episode (the brief forbids it), so the commission is not checked
  against the child's real forms here; `msg_to_child` builds the child's assignment keys (version, question_context_refs,
  search_result_refs, scope, finding_unit, received_record_refs) as read from its finished `read_from_parent.py`.
- The assignment's `prior_search_refs` are listed in `literature_source_custody` and passed to the child only in
  `message` (the child's assignment has no field for them); the old custody list was empty for this assignment.

## Not repaired

- credit.py: `project_finding_progress` (library findings/biochemical_feasibility_evidence/investigation_progress.py) still takes `store` in the old form; pattern "library not carried". Fails at run time until carried.
- task.py `run_library_tool`: ToolRegistry(ctx.store, ...) from tools/biochemical_feasibility_evidence/tools.py uses store.db; pattern "library not carried".
- `literature_reaction_populate` / `literature_reaction_source_populate`: raise NotImplementedError('a110_reaction_population_not_built:...'); library modules not in episode_support; reaction cells, native observations and A110 component assignment fields not declared.
- yield_estimator: parent_input is accepted and unused (no commissioned quantity in the old episode).
