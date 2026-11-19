# a102/.../source_relevance_assessment: carry-over items

## BLOCKED-ON-STORE-ACCESS

- function = `tools/structural_homology_evidence/tools.py::ToolRegistry`, pattern = "library not carried". Every tool of `task.py` (`run_tool`) calls `ToolRegistry(ctx.store, **settings['tool_registry']).execute_async(name, arguments, scope=..., operation_key=ctx.operation_key, permitted_record_refs=...)`. The constructor still runs `store.db.execute(...)` and uses `store.path`; the acquisition and access operations use the raw Store.
- function = `findings/structural_homology_evidence/finding_validity.py::FindingValidity` and `scientific_findings.py::FindingIdentity`, pattern = "library not carried" (checked: `FindingValidity` uses its own temporary SQLite spool and the Store's `validate_scope`/reads; its custody behaviour is unverified).
- function = `literature/inputs/evolutionary_history_evidence/literature_assay_inputs.py::_Sources`, pattern = "library not carried" (used by `validate_source_lead`; reads through the callback with `store.get_artifact`, custody-limited).
- function = `tools/unit_outcomes.py::failure_outcome(store, ...)` is called with `ctx.store` as the library requires (no finding).

## unplaced_old_functions


## contract_misfits

- new field: source_relevance_assessment scope (Store scope of the commission; the old episode took it from its request).
- new field: source_relevance_assessment received_record_refs (records passed in custody besides the context and search results; the old episode took them from its binding context).
- new field: source_relevance_assessment credit_unit in `literature_task` (the old private yield declaration filled `credit_unit` and `yield_settings`; the commissioning parent must now supply a finite `credit_unit`; the controller cost and parameters are this episode's settings `cost`, `parameters`).
- The old episode returned no controller without a private yield binding; every episode now has a controller, so that case is not carried.
- Old custody bug carried as a decision: the old `decision_context` read `assignment.get('page')`/`source_refs`, so custody was always empty for this assignment (`search_result_refs`). It now lists the search results and the sources the episode's own acquisition tools produced, with the records a page commission passes. An acquired source is named for the child through `passed_record_refs` (its artifacts and its held parent sources); a parent source this episode does not hold is not passed, so the child fails with `CustodyError` when it reads it.
- The page commission names `question_context_refs`/`prior_delivery_refs` chosen by the model; `action` rejects a page naming a record this episode does not hold (answer rejection, not a commission check).
- Completion credit cannot pass its target: a source answer earns at most one `credit_unit` (screening: one answer; assessment: the first retained assessment), and the target is `credit_unit`.
- Launch instruction library: the old composer appended it when supplied; this episode does not offer it (no `LaunchInstructions` directory in settings); not carried.
- Tests: no old test of this episode existed at 97308b94c (the retired-tests file has only its header). No real runner or model test was written: the episode's tools need `ToolRegistry` (library not carried) and a real model.
- Process note: I ran one `python3` text-transform command to generate the repetitive tool wrapper functions in `task.py` (no project code imported); every project Python command went through the launcher.

## Pilot 102 (19 November 2026)

The A102 literature structure grading route is built: `structure_populate` in `task.py` (grader `structural_feature_geometry`, sheet `literature_structure_cells`, library `episode_support/literature/{forms,calculations,inputs,storage,readers}/structural_homology_evidence/`), the return is the controlled sheet features (`INVESTIGATION_FINDING_FEATURES_a102.md` 2.13), the `report` tool is removed. Open items: `PILOT102_BLOCKERS.md`.
