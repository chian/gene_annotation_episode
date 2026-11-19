# a102/structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement: carry-over items

## BLOCKED-ON-STORE-ACCESS

- function = `tools/structural_homology_evidence/tools.py::ToolRegistry`, pattern = "library not carried". Every tool of `task.py` (`run_tool`) calls `ToolRegistry(ctx.store, **settings['tool_registry']).execute_async(name, arguments, scope=..., operation_key=ctx.operation_key, permitted_record_refs=...)`. The constructor still runs `store.db.execute(...)` and uses `store.path`; the acquisition and access operations use the raw Store.
- function = `findings/structural_homology_evidence/finding_validity.py::FindingValidity` and `scientific_findings.py::FindingIdentity`, pattern = "library not carried" (`FindingValidity` uses its own temporary SQLite spool and the Store's `validate_scope`/reads; its custody behaviour is unverified).
- function = `literature/inputs/evolutionary_history_evidence/literature_assay_inputs.py::_Sources`, pattern = "library not carried" (used by `validate_source_lead`; reads through the callback with `store.get_artifact`, custody-limited).
- `tools/unit_outcomes.py::failure_outcome(store, ...)` is called with `ctx.store` as the library requires (no finding).

## unplaced_old_functions

- `SourceSourceReferences._within_source`: bounded reads to an assigned page source; this assignment has no `page`, so the function is unreachable here.

## contract_misfits

- new field: evidence_search_strategy_improvement scope (Store scope of the commission; the old episode took it from its request).
- new field: evidence_search_strategy_improvement received_record_refs (records passed in custody besides the context and prior search results; the old episode took them from its binding context).
- new field: evidence_search_strategy_improvement credit_unit in `literature_task` (the old private yield declaration filled `credit_unit` and `yield_settings`; the commissioning parent must now supply a finite `credit_unit`; the controller cost and parameters are this episode's settings `cost`, `parameters`).
- new field: source_relevance_assessment (child) is commissioned with `scope` and `received_record_refs` by this episode's `msg_to_child`; both come from this episode's own parent input (scope) and from the model's chosen search plus the custody entries (records).
- The old model filled the child's whole `search_assignment_v1`; now the model names only `question_context_refs` and `search_result_refs` (`search` argument of the `literature_search` child call) and `msg_to_child` copies the commissioned task, proposed annotation, requested components and scope from the summary.
- The old episode returned no controller without a private yield binding; every episode now has a controller, so that case is not carried.
- Old custody bug carried as a decision: the old `decision_context` read `assignment.get('page')`/`source_refs`, so custody was always empty for this assignment (`prior_search_refs`). It now lists the prior search results and the sources the episode's own acquisition tools produced, with the records a search commission passes. An acquired source is named for the child through `passed_record_refs` (its artifacts and its held parent sources); a parent source this episode does not hold is not passed, so the child fails with `CustodyError` when it reads it.
- The search commission names `question_context_refs`/`search_result_refs` chosen by the model; `action` rejects a search naming a record this episode does not hold (answer rejection, not a commission check). A search-result ref this episode holds no custody entry for makes `msg_to_child` raise `KeyError`.
- Completion credit may pass its target: a source answer earns at most one `credit_unit`, and CompletionYieldController stops when credit reaches the target (no clamp, no second stop test) (screening: one answer; assessment: the first retained assessment), and the target is `credit_unit`.
- Launch instruction library: the old composer appended it when supplied; this episode does not offer it; not carried.
- Tests: no old test of this episode existed at 97308b94c (the retired-tests file has only its header). No real runner or model test was written: the episode's tools need `ToolRegistry` (library not carried) and a real model.

## Not repaired


## Pilot 102 (19 November 2026)

The A102 literature structure grading route is built: `structure_populate` in `task.py` (grader `structural_feature_geometry`, sheet `literature_structure_cells`, library `episode_support/literature/{forms,calculations,inputs,storage,readers}/structural_homology_evidence/`), the return is the controlled sheet features (`INVESTIGATION_FINDING_FEATURES_a102.md` 2.13), the `report` tool is removed. Open items: `PILOT102_BLOCKERS.md`.
