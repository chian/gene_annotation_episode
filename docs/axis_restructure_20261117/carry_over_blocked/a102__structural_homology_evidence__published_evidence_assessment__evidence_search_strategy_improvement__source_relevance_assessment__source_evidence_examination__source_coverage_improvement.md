# a102 source_coverage_improvement (old role literature_ordered): blocked, unplaced and misfit items

Carried 19 November 2026. Tests: 10 passed (run `runs/cov_a102_07_u046_3`).

## BLOCKED-ON-STORE-ACCESS (library not carried)

| function | pattern |
|---|---|
| `episode_support/tools/structural_homology_evidence/tools.py::ToolRegistry` (called in `task.py run_access_tool`: `ToolRegistry(ctx.store, ...).execute_async(...)`) | library not carried (31 `store.db` / private-method sites; `evidence_operations.py` 10) |
| `episode_support/findings/structural_homology_evidence/finding_validity.py::FindingValidity`, `target_eligible` (called in `credit.py current_assessments`) | library not carried (`store._assessment_write_extent`, `sqlite3.connect('')` spool) -> intended `records.record_coverage(row)` / `records.is_current(ref)` / `records.current_assessments(scope)` |
| `episode_support/findings/structural_homology_evidence/scientific_findings.py::FindingIdentity` (called in `credit.py lead_dispositions`) | library not carried (`store._require(ref, kinds)`) -> intended `records.require(ref, kinds)` |
| `episode_support/literature/grading/literature_task_credit.py` (`lead_schema` is imported by `task.py`; the rest of the module is not called) | library not carried (10 raw-Store sites); only the pure `lead_schema` is used |

## Unplaced old functions

| old | reason |
|---|---|
| `structural_sheet_operations.py` `literature_structure_repository`, `_population_routes`; `source_operations.py` `_materialize_text_arguments`; `to_parent.py` `_rate_facts`, `_rate_fact_sources`; `internal_summary.py` population-context functions | The structure population route (`LiteratureStructureRepository`, `population_route`, `population_catalog_entry`, `fact_source_definition`, `assignment_component_schema`, `population_task_metadata_specs`) is not in `episode_support/` (found no module of those names). `task.py literature_structure_populate`, `decide` with `structure_population` set and `final_to_parent` selecting `literature_structure_cells` raise `NotImplementedError('literature_structure_population_not_built')`. |
| `to_parent.py validate_report` -> `validate_form(form, original_schema, resolver)` | A102 has no `validate_form`: `messages/final_to_parent.py validate_report` raises `NotImplementedError('validate_form_not_built:A102')` after the checks it can make, so `final_to_parent` always raises until A102 has one. |
| `source_interpretation.py` `validate_lead` (library `literature_task_credit.validate_lead` takes the old binding context) | a private copy over held records is `task.py validate_source_lead` (library candidate). |

## Contract misfits

- Not carried as a commission check (rule 1): the child's re-validation of the commissioning `literature_page` parent's page assignment (`commissioning_page_assignment.py`, `_within_source` of the parent's source) and of `page` against the scope. The page and records come in the child's own assignment.
- new field: source_coverage_improvement scope (Store scope of the commission; old: request scope)
- new field: source_coverage_improvement received_record_refs (the source, its artifact, the sources it derives from, the proposed annotation; old: binding-context received records)
- new field: source_coverage_improvement finding (the interpretation the model writes with the `report` tool; the old form was written by the parent)
- completion credit may pass its target: not for this episode. Source answers return at most one answer, so credit is at most one `credit_unit`; `verified_source_leads` accumulates.
- The yield settings (`cost`, `parameters`) are read from `settings` as the sibling `fact_extraction` example does; the old `kind`/`cutoff`/`uncertainty_alpha` task declaration is mapped by task kind (leads: accumulation; source answer: completion with `task['credit_unit']`).
- The old assignment check that the window offset is within the artifact size is in `messages/internal_summary.py` (it needs `records`, which `read_from_parent` does not have); a bad offset fails the run at the first summary.
- Old `redeliver_report` and `child` permitted actions are not carried (redelivery deleted; no child).
