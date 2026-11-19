# source_relevance_assessment (A110): carry-over items

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
  (3 functions); reaction_records.py (3 functions); received_reports.py (6 methods): the reaction population library
  (`literature_component_binding`, `reaction_population`, `reaction_source_selection`, `literature_assay_inputs` of
  A110, `literature_reaction_storage`, `reaction_native_observations`, `reaction_population_contracts`,
  `literature_sheet_updates`) is not in `episode_support/`; the reaction fact sources are not declared in
  `RETURN_FORM`; the tools `literature_reaction_populate` and `literature_reaction_source_populate` raise
  `NotImplementedError('a110_reaction_population_not_built:...')` and are not offered.
- source_custody.py `LiteratureSourceCustody` and `_within_source`: reached only for an assignment with a page; this
  assignment has none, so they are never reached for this episode.

## contract_misfits

- new field: source_relevance_assessment scope (old request scope), finding_unit (the old scientific credit unit),
  received_record_refs (old binding-context received records) in `ASSIGNMENT_FORM`.
- new field: source_relevance_assessment finding (the typed finding: written, interpretation, source_refs,
  examinations, qualification); the old return was the parent's requested form filled from reaction rate fact sources.
- The old assignment properties of `literature_component_binding.assignment_schema_fields()` are not declared
  (module not in the library): a commission that sends them is refused.
- The old `validate_report` called `validate_form`; the A110 axis has no `validate_form`
  (`NotImplementedError('validate_form_not_built:a110')` would be the call); `final_to_parent.validate_report`
  checks the report against the episode's own `FINDING_FORM` and held sources instead.
- `yield_estimator.py`: the old episode named no estimator; `AccumulationYieldController` chosen (README 7b); its
  settings must carry `cost` above zero and `parameters`.
- tests/test_binding.py imports the real child's episode module (importlib) to admit the commission against the
  child's real forms; episode code imports nothing from the child.
- `msg_to_child` reads the sources and their artifacts from `summary['held_sources']` (built from
  `view.records.list('source')`) to name every record the child needs; a source the model names that is not held is
  not checked in `action`; the commission fails with KeyError.

## Not repaired

- credit.py: `project_finding_progress` (episode_support/findings/biochemical_feasibility_evidence/investigation_progress.py) still takes a `store` and uses store._require and an sqlite3 spool; library not carried (BLOCKED-ON-STORE-ACCESS, pattern "library not carried").
- task.py: `ToolRegistry(ctx.store, ...)` over episode_support/tools/biochemical_feasibility_evidence/tools.py, which still uses store.db; library not carried.
- The A110 reaction population library is not in episode_support; the two populate tools raise NotImplementedError('a110_reaction_population_not_built:...') and the old reaction-cell report is not returned (unplaced old functions listed above).
