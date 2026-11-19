# table_evidence_extraction (A106): blocked, unplaced and contract misfits

## BLOCKED-ON-STORE-ACCESS

- function = `gene_annotation_episode/episodic_workflow/episode_support/tools/perturbation_evidence/tools.py::ToolRegistry`, pattern = "library not carried". `task.py run_access_tool` calls `ToolRegistry(ctx.store, **settings['tool_registry']).execute_async(name, arguments, scope=..., operation_key=ctx.operation_key, permitted_record_refs=...)`. Old call -> intended call: `store.db` tool_operations ledger -> deleted (the system journals units; `ctx.operation_key`); `store._require(ref, kinds)` -> `store.require(ref, kinds)`; `store.path` temp/cache -> scratch-directory operation (no replacement yet).
- function = `.../episode_support/findings/perturbation_evidence/finding_validity.py::FindingValidity` and `::target_eligible` (called by `credit.py current_assessments`), pattern = "library not carried". Old call -> intended call: `sqlite3.connect('')` spool and `store._assessment_write_extent(assessment)` -> a custody-limited `_assessment_write_extent` operation (store-access.md "No replacement yet").
- function = `.../episode_support/findings/perturbation_evidence/scientific_findings.py::FindingIdentity` (called by `credit.py lead_dispositions`), pattern = "library not carried". Old call -> intended call: `store._require(ref, {...})` -> `store.require(ref, {...})`; `store._record_roots(...)` -> a custody-limited `_record_roots` operation (no replacement yet).
- `task.py reason` calls `store.commit_reasoning(commit, scope, ctx.operation_key)` and `store.transaction()` on ctx.store as written (carried as in the sibling passage_evidence_extraction); whether the custody-aware store offers them is not verified by a run.
- function = `.../episode_support/literature/grading/literature_task_credit.py::validate_lead` / `::lead_dispositions` / `::screening_answers` (old forms), pattern = "library not carried"; not called: the episode carries private re-expressions (`task.py validate_source_lead`, `credit.py lead_dispositions` / `screening_answers`; library candidates). Old call -> intended call: `store._require` -> `store.require`; runtime_* reads -> the view's `outcomes`.

## UNPLACED OLD FUNCTIONS

- Rate-population route (rows marked UNPLACED in the Carried over table): `scientific_records.py` (all), `source_contracts.py _required_grading_logic` / `_population_catalog`, `source_operations.py _materialize_text_arguments` and the populate branch of `execute`, `received_evidence.py` (all but `validate_received_report`), `to_parent.py _rate_fact_sources` / `_rate_facts`, `internal_summary.py` display contexts, `decision_presentation.py prepare_completed_work`, `goal.py _return_components`, `grading/intervention_assessment.py`, `scoring/intervention_main_sheet.py`. No populate tool (including `literature.a106.finalize`) is offered, no requested_* property is declared, no fact cell is returned. The A106 sub-score text is no longer joined into GOAL (it named `literature.a106.finalize`, not offered).
- `source_operations.py prepare_analysis_contract`: needs the old execution binding of the BV-BRC service; no such tool.
- `from_parent.py _validate_page`, Store checks of `_validate_assignment` (offset within artifact size), `from_parent_page.py`, `source_references.py _artifact`/`resolve`: they read the Store or the parent's page assignment; a wrong commission fails.
- Screening credit: `screening_answers` reads `evidence_processing.kind=no_applicable_evidence` declarations that only the assay-grading reason schema offers; the `reason` schema here has none, so a screening commission earns no credit (as in the old default).
- Called where the old A106 required-grading logic was None: nothing raises NotImplementedError('validate_form_not_built:a106'); this episode calls no validate_form.

## CONTRACT MISFITS

- new field: table_evidence_extraction scope (assignment; the old episode took the Store scope from its request)
- new field: table_evidence_extraction received_record_refs (assignment, record_refs; the old episode read context.received_record_refs). The parent must name the source, its artifact, the sources it derives from, the proposed annotation and, for a lead, the lead's reference subject.
- new field: table_evidence_extraction finding (return; the old episode returned the parent-written form): `written`, `interpretation`, `passages`, `qualification` plus a `report` tool for the model's closing text. A106 is not an A105/A108 episode, so no grader sheet is coupled.
- The old `selection` was `anyOf [table, window]`; a RecordForm has one field set, so `selection` is one record whose table-only (`sheet_key`, `header_row`, `where`) and window-only (`representation`) fields are optional, and `read_from_parent` requires the fields of the shape the selection is. Old null `header_row` / `where` / `where.column` are omitted fields (the form has no null).
- Tool names cannot contain dots: library names (`source.read`, ...) are carried as `source_read`, ... (`LIBRARY_NAMES` in `task.py`).
- `action` wraps tool arguments in an envelope `{'arguments', 'scope', 'page_source_ref', 'proposed_annotation_ref', 'selection'}` so tools (handed no summary) apply the page-source restriction and the sheet_key rule.
- Settings read: `cost`, `parameters`, optional `tool_registry`, optional `knowledge_library_directory`.
- The old no-private-binding case is not carried: the controller is accumulation for verified_source_leads, completion (target `credit_unit`) otherwise.
- completion credit may pass its target: not expected; assessment/screening count at most one answer and the target is `credit_unit`.
- Environment: the repository root has no `.git`; old code was read with `git -C /home/chia/repos/gene_annotation_episode_disk show 97308b94c:<path>`. The sibling passage_evidence_extraction (same old code) was used as the shape of the shared pieces, copied privately (no import).

## Not repaired

- Rate-population route (69 rows UNPLACED in the Carried over table; scientific_records, received_evidence, intervention_assessment, intervention_main_sheet, display contexts, prepare_completed_work, _return_components, _rate_fact_sources/_rate_facts, _required_grading_logic/_population_catalog, _materialize_text_arguments): rebuilding it needs the populate tools and library functions that still use the old Store (store.db, store._require, store._record_roots, store._assessment_write_extent: "library not carried") and new library files, which this step may not create or edit. Left unplaced and reported.
- goal.py: repaired by dropping the A106 sub-score TASK text (it named literature.a106.finalize, not offered) from GOAL. Goal now matches the offered tools.
- ToolRegistry, FindingValidity, FindingIdentity, literature_task_credit: library not carried (see above); screening credit unreachable follows from the unbuilt route; prepare_analysis_contract: no BV-BRC execution binding in the new system.
