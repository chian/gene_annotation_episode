# source_evidence_examination (A110): blocked, unplaced and misfits

Episode: `biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination`

## BLOCKED-ON-STORE-ACCESS

| Function | Pattern (old call -> intended call) |
|---|---|
| `findings/biochemical_feasibility_evidence/investigation_progress.py::project_finding_progress` (called by `credit.py`) | library not carried: `project_finding_progress(store, ...)` uses `store.read_snapshot` of the raw Store, a `sqlite3` spool, `store._require` and `store.db`; the call stays as written with `records` until the function is carried |
| `tools/biochemical_feasibility_evidence/tools.py::ToolRegistry` (called by the access tools of `task.py`) | library not carried: `ToolRegistry(store, ...)` is built over the raw Store; the call stays as written with `ctx.store` |

## Unplaced old functions

| Old | Reason |
|---|---|
| `initial_information.py::initial_information` | reads the old `catalog.readers(...)` and `execution_initial_information.presentation.resource_information`; neither exists in `episode_support` or the new form |
| `received_execution_information.py::received_execution_information` | selects result readers from the old `catalog` (`configured`/`received`); no counterpart in the new form |
| `task_presentation.py::present_source_context` | renders the literature experimental TASK prompt from reconstructed state frames; `render_literature_experimental_prompt` / `is_literature_experimental_context` (`literature_source_presentation`) and `decision_context.apply_state_frame` are not in `episode_support`; the state frames are deleted conversation state |
| `internal_summary.py::LiteratureSummary._owned_population_task_sources` | classified population sheets through `store.db`/`sqlite_master` on library tables; needs `literature_task_selection.population_task_metadata_specs` (not in library) |
| `internal_summary.py::LiteratureSummary._population_task_context` | reads `runtime_actions` through `store.db` (old runner) and the owned population sources |
| `source_operations.py::_materialize_text_arguments` | needs `literature_assay_inputs.materialize_text_witness_inputs` of A110 and the reaction repository (not in library) |
| `numerical_report_facts.py::_rate_fact_sources`, `_rate_facts` | need `literature_component_binding`, `reaction_population_contracts`, `reaction_native_observations`, `literature_sheet_updates` and the reaction repository (not in library); no reaction fact source is declared in `RETURN_FORM` |
| `reaction_records.py::literature_reaction_repository`, `_population_routes` | `LiteratureReactionRepository` (`literature_reaction_storage`) and `population_routes` are not in library |
| `received_reports.py` (`received_report_facts`, `_complete_requested_received_arrays`, `received_form_references`, `received_evidence_tokens`, `validate_received_report`) | the reaction cells and native rows are not returned by any child (children declare no reaction fact sources); the reaction repository is not in library |
| tools `literature.reaction.populate`, `literature.reaction.source.populate` | declared in `task.py` as `literature_reaction_populate` and `literature_reaction_source_populate`, raise `NotImplementedError('a110_reaction_population_not_built:...')`, not offered to the model |

## Contract misfits

- A110 has no `validate_form` (`forms/biochemical_feasibility_evidence/communication.py` has `plain` only): the old `validate_report` call to `validate_form(form, original_schema, resolver)` is not written; `final_to_parent.validate_report` admits the finding against its own `FINDING_FORM` and checks held sources. `NotImplementedError('validate_form_not_built:biochemical_feasibility_evidence')` is not raised because the form is declared and admitted by `RecordForm`; reported here.
- new field: source_evidence_examination scope (record) in `ASSIGNMENT_FORM`; the old episode took the scope from its request.
- new field: source_evidence_examination finding_unit (number) in `ASSIGNMENT_FORM`; the old episode took its credit unit from `services.scientific_credit`.
- new field: source_evidence_examination received_record_refs (record_refs) in `ASSIGNMENT_FORM`; the old episode took the records it received from its binding context.
- new field: source_evidence_examination examined (list, selectable) in `RETURN_FORM`; `finding.investigations` is the typed finding of this episode (the old form was written by the parent).
- new field: source_evidence_examination report arguments `source_refs` (report tool): the sources the interpretation rests on, held-checked in `action`.
- new field: table_evidence_extraction `kind` in the table selection (child side, already declared by the child): the parent's table argument schema carries `kind` (`table` or `window`).
- The old assignment schema's properties from `literature_component_binding.assignment_schema_fields()` (requested reaction components, native positions) are not declared in `ASSIGNMENT_FORM`: the module is not in the library, and the three children do not declare them either. A commission that sends one is refused by the form.
- Held records and credit: the old parent had no reasoning action (permitted common actions: tool, child, redeliver_report), and none of the three children declares a `record_refs` field in its `RETURN_FORM` (they return `credit` and `finding` only, plus the table child's `reads`), so this episode holds no assessment of its own and `credit.py` (retained findings among held assessments) stays at its initial value. new field: passage_evidence_extraction / source_coverage_improvement / table_evidence_extraction `assessment_refs` (record_refs): the assessments each child committed, returned in custody, so that the parent's own scientific credit (old `services.scientific_credit` over received findings) has records to count. Not added by this episode (children are read-only here).
- The accumulation controller needs a cost above zero in the `continuation` settings for this binding path (`settings['cost']`, `settings['parameters']`); with credit constant the controller stops once its forecast falls to the cost.
- `messages/read_from_parent.py` is the only place the assignment is read; `yield_estimator.py` does not read `parent_input` (the old episode named no estimator: README 7b, accumulation).
- A test reads each real child form through `importlib` by module name to check that `msg_to_child` builds an admitted commission; it contains no import statement of another episode.

## Not repaired

- BLOCKED-ON-STORE-ACCESS, credit.py: project_finding_progress(records, scope, policy, known_assessment_refs=...) -> library investigation_progress.py is still raw-Store form (sqlite3, store._require, store.read_snapshot); library not carried. credit() cannot be exercised by a real test until it is carried.
- BLOCKED-ON-STORE-ACCESS, task.py run_access_tool: ToolRegistry(ctx.store, ...) -> library tools/biochemical_feasibility_evidence/tools.py is still raw-Store form; library not carried.
- Contract/design limit: no child returns record_refs and the episode has no reasoning tool, so known_assessment_refs stays empty and credit stays at its initial value.
- Reaction-population library not in episode_support: the two population tools raise NotImplementedError('a110_reaction_population_not_built:...').
- Test of the commission against the real child forms was removed: it could only run by importing the child episode folders from this folder's tests. The commission is now checked against this episode's own side only.
