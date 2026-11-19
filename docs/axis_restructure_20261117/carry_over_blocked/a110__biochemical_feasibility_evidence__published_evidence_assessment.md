# published_evidence_assessment (A110): carry-over items

## BLOCKED-ON-STORE-ACCESS

- credit.py `credit` -> `findings/biochemical_feasibility_evidence/investigation_progress.py::project_finding_progress`
  - pattern: "library not carried" (old call `project_finding_progress(store, ...)` with `store.read_snapshot`, a
    `sqlite3` spool, `store._require`, `store.db` (4 sites) -> intended call with `records`; the call stays as
    written, it is handed `records`).
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
  `literature_sheet_updates`) is not in `episode_support/`. `literature_reaction_cells` and
  `literature_reaction_semantic_cells` are declared as selectable fields of `RETURN_FORM` and raise
  `NotImplementedError('a110_reaction_population_not_built:<name>')` in `final_to_parent` when selected; the native
  observation fact source is not declared (its name lives in the missing module); the tools
  `literature_reaction_populate` and `literature_reaction_source_populate` raise
  `NotImplementedError('a110_reaction_population_not_built:...')` and are not offered.
- parent_context.py `initial_decision_context`, `contract_information_profile`: root reference-evidence parent only /
  old contract information freezing; no place.
- source_custody.py `LiteratureSourceCustody` and its methods: reached only for an assignment with a page; this
  assignment has none.

## contract_misfits

- new field: published_evidence_assessment scope (old request scope), finding_unit (the old scientific credit unit),
  received_record_refs (old binding-context received records) in `ASSIGNMENT_FORM`.
- new field: published_evidence_assessment finding (typed finding: written, interpretation, source_refs, strategies,
  qualification); the old return was the parent's requested form filled from reaction rate fact sources. Also new:
  selectable `commissioned`.
- The old assignment properties of `literature_component_binding.assignment_schema_fields()` are not declared
  (module not in the library): a commission that sends them is refused.
- The old `validate_report` called `validate_form`; the A110 axis has no `validate_form`
  (`NotImplementedError('validate_form_not_built:a110')` would be the call); `final_to_parent.validate_report`
  checks the report against the episode's own `FINDING_FORM` and held sources instead.
- `yield_estimator.py`: the old episode named no estimator; `AccumulationYieldController` chosen (README 7b); its
  settings must carry `cost` above zero and `parameters`.
- `msg_to_child` reads the sources and their artifacts from `summary['held_sources']` (built from
  `view.records.list('source')`) to name every record the child needs; a source the model names that is not held is
  rejected in `action` (provisional held-record check) and otherwise fails the commission with KeyError.
- tests/test_binding.py does not import the child episode (the brief forbids it), so the commission is not checked
  against the child's real forms here; `msg_to_child` builds the child's assignment keys (version,
  question_context_refs, prior_search_refs, scope, finding_unit, received_record_refs) as read from its finished
  `read_from_parent.py`, and `read_from_child` reads the child's `finding` and `assessed` as declared in its
  finished `final_to_parent.py`.
- The old `evidence_search_strategy_improvement` ChildCall arguments (`question_context_refs`, `prior_search_refs`)
  are chosen by the model; the parent's `source_refs` are listed in `literature_source_custody` and passed to the
  child only in `message` (the child's assignment has no field for them).
- Docs: `docs/axis_restructure_20261117/GOAL.md` named in the brief does not exist; not read.
- Environment: git history is in `/home/chia/repos/gene_annotation_episode_disk/.git`; `/home/chia/repos/gene_annotation_episode` has no `.git` (it is a link to `/tmp/ramrepo`). Old files were read with `git -C` there.
