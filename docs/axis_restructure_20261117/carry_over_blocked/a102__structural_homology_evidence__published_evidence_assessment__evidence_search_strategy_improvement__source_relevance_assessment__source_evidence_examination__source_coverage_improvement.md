# a102 source_coverage_improvement (old role literature_ordered): blocked, unplaced and misfit items

Carried 19 November 2026. Tests: 10 passed (run `runs/cov_a102_07_u046_3`).

## BLOCKED-ON-STORE-ACCESS (library not carried)

| function | pattern |
|---|---|
| `episode_support/tools/structural_homology_evidence/tools.py::ToolRegistry` (called in `task.py run_access_tool`: `ToolRegistry(ctx.store, ...).execute_async(...)`) | library not carried (31 `store.db` / private-method sites; `evidence_operations.py` 10) |
| `episode_support/findings/structural_homology_evidence/scientific_findings.py::FindingIdentity` (called in `credit.py lead_dispositions`) | library not carried (`store._require(ref, kinds)`) -> intended `records.require(ref, kinds)` |
| `episode_support/literature/grading/literature_task_credit.py` (`lead_schema` is imported by `task.py`; the rest of the module is not called) | library not carried (10 raw-Store sites); only the pure `lead_schema` is used |

## Unplaced old functions

| old | reason |
|---|---|
| `source_interpretation.py` `validate_lead` (library `literature_task_credit.validate_lead` takes the old binding context) | a private copy over held records is `task.py validate_source_lead` (library candidate). |

## Contract misfits

- Not carried as a commission check (rule 1): the child's re-validation of the commissioning `literature_page` parent's page assignment (`commissioning_page_assignment.py`, `_within_source` of the parent's source) and of `page` against the scope. The page and records come in the child's own assignment.
- new field: source_coverage_improvement scope (Store scope of the commission; old: request scope)
- new field: source_coverage_improvement received_record_refs (the source, its artifact, the sources it derives from, the proposed annotation; old: binding-context received records)
- completion credit may pass its target: not for this episode. Source answers return at most one answer, so credit is at most one `credit_unit`; `verified_source_leads` accumulates.
- The yield settings (`cost`, `parameters`) are read from `settings` as the sibling `fact_extraction` example does; the old `kind`/`cutoff`/`uncertainty_alpha` task declaration is mapped by task kind (leads: accumulation; source answer: completion with `task['credit_unit']`).
- The old assignment check that the window offset is within the artifact size is in `messages/internal_summary.py` (it needs `records`, which `read_from_parent` does not have); a bad offset fails the run at the first summary.
- Old `redeliver_report` and `child` permitted actions are not carried (redelivery deleted; no child).

## Not repaired

System or library limits, not carry-over omissions (all detailed in the sections above):
- access tool registry: library tools.py still uses store.db, store.path, store._require (library not carried).
- credit: FindingValidity, target_eligible and FindingIdentity still in the old Store form (BLOCKED-ON-STORE-ACCESS).
- library lead_schema module still has raw store.db reads; only the pure lead_schema is used.
- commission re-validation not carried by rule (a wrong commission just fails); contract misfit.
- tests over real records or a full run of credit/internal_summary/decide/action: they need a model or the blocked library operations; no fake is written. Added only real tests that run today (credit binding, lead credit with no leads, uncarried task kind).

## Pilot 102 (19 November 2026)

The A102 literature structure grading route is built: `structure_populate` in `task.py` (grader `structural_feature_geometry`, sheet `literature_structure_cells`, library `episode_support/literature/{forms,calculations,inputs,storage,readers}/structural_homology_evidence/`), the return is the controlled sheet features (`INVESTIGATION_FINDING_FEATURES_a102.md` 2.13), the `report` tool is removed. Open items: `PILOT102_BLOCKERS.md`.
