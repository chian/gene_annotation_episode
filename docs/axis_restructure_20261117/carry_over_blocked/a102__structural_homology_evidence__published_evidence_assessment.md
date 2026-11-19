# a102/structural_homology_evidence/published_evidence_assessment: carry-over items

## BLOCKED-ON-STORE-ACCESS

- function = `tools/structural_homology_evidence/tools.py::ToolRegistry`, pattern = "library not carried". Every tool of `task.py` (`run_tool`) calls `ToolRegistry(ctx.store, **settings['tool_registry']).execute_async(name, arguments, scope=..., operation_key=ctx.operation_key, permitted_record_refs=...)`. The constructor still runs `store.db.execute(...)` and uses `store.path`; the acquisition and access operations use the raw Store.
- function = `findings/structural_homology_evidence/finding_validity.py::FindingValidity` and `findings/structural_homology_evidence/scientific_findings.py::FindingIdentity`, pattern = "library not carried" (`FindingValidity` uses its own temporary SQLite spool and the Store's `validate_scope`/reads; its custody behaviour is unverified).
- function = `literature/inputs/evolutionary_history_evidence/literature_assay_inputs.py::_Sources`, pattern = "library not carried" (used by `validate_source_lead`; reads through the callback with `store.get_artifact`, custody-limited).
- `tools/unit_outcomes.py::failure_outcome(store, ...)` is called with `ctx.store` as the library requires (no finding).

## unplaced_old_functions

- `SourceFromParent._validate_page`, `SourceSourceReferences._within_source`: the page branches (page artifact checks, bounded reads to an assigned page source) serve the page role; this assignment has no `page`, so they are unreachable here.

## contract_misfits

- new field: published_evidence_assessment scope (Store scope of the commission; the old episode took it from its request).
- new field: published_evidence_assessment received_record_refs (records passed in custody besides the context and the assigned sources, including the proposed annotation and the artifacts of the assigned sources; the old episode took them from its binding context).
- new field: published_evidence_assessment credit_unit in `literature_task` (the old private yield declaration filled `credit_unit` and `yield_settings`; the commissioning parent must now supply a finite `credit_unit`; the controller cost and parameters are this episode's settings `cost`, `parameters`).
- new field: evidence_search_strategy_improvement (child) is commissioned with `scope` and `received_record_refs` by this episode's `msg_to_child`; `scope` comes from this episode's parent input, the records from the model's chosen strategy plus the custody entries.
- The old model filled the child's whole `strategy_assignment_v1`; now the model names only `question_context_refs` and `prior_search_refs` (`strategy` argument of the `literature_strategy` child call) and `msg_to_child` copies the commissioned task, proposed annotation, requested components and scope from the summary.
- The old `literature_task` and `proposed_annotation_ref` were required only with `private_yield_binding`; every episode now has a controller built from the task, so both are always required. The case without a private yield binding (no controller of its own) is not carried.
- Old custody: the old `decision_context` read `assignment.get('page')`/`source_refs`; custody now lists the assigned sources and the sources the episode's own acquisition tools produced, with the records a strategy commission passes (`passed_record_refs`: the source, its artifacts, its held parent sources). A parent source this episode does not hold is not passed, so the child fails with `CustodyError` when it reads it.
- The strategy commission names `question_context_refs`/`prior_search_refs` chosen by the model; `action` rejects a strategy naming a record this episode does not hold (answer rejection, not a commission check). A prior search source this episode holds no custody entry for makes `msg_to_child` raise `KeyError`.
- Completion credit cannot pass its target: a source answer earns at most one `credit_unit` (screening: one answer; assessment: the first retained assessment), and the target is `credit_unit`.
- Launch instruction library: the old composer appended it when supplied; this episode does not offer it; not carried.
- Hook-era files deleted: `literature_binding.py` (class `LiteratureBinding`), `literature_source.py` (class `LiteratureSource`) and `tests/test_literature_link.py`. The axis-head file `structural_homology_evidence/contract_binding.py` (not this episode's folder) still names `literature_binding.LiteratureBinding` in its docstring and comments, and its tests may still link the deleted classes; it is for the axis head's carry-over to resolve.
- Tests: no real runner or model test was written: the tools need `ToolRegistry` (library not carried) and a real model. `tests/test_binding.py` imports the episode (class-definition checks), checks the ten-file folder, the import rule by ast, the forms, the commission, the credit and controller on real data, and that the structure route and the report validator raise where they are not built.

## Not repaired

- `ToolRegistry(ctx.store, ...)` (library `tools/structural_homology_evidence/tools.py` still uses `store.db`/`store.path`): library not carried.
- Private `_Sources` import from `literature_assay_inputs`: library not carried.
- Completion credit cannot pass its target for a source answer: stated in contract_misfits, no change.
- Axis head `contract_binding.py` and other a10x folders still name the old shared class: another episode's carry-over.

## Pilot 102 (19 November 2026)

The A102 literature structure grading route is built: `structure_populate` in `task.py` (grader `structural_feature_geometry`, sheet `literature_structure_cells`, library `episode_support/literature/{forms,calculations,inputs,storage,readers}/structural_homology_evidence/`), the return is the controlled sheet features (`INVESTIGATION_FINDING_FEATURES_a102.md` 2.13), the `report` tool is removed. Open items: `PILOT102_BLOCKERS.md`.
