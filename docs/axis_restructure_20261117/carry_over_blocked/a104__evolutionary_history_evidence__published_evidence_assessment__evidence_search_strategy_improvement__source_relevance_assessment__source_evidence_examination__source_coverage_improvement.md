# source_coverage_improvement (A104): blocked, unplaced and contract misfits

## BLOCKED-ON-STORE-ACCESS

All library calls below are "library not carried" (the library still uses the old Store forms); the episode's calls stay as written.

- function = `episode_support/tools/evolutionary_history_evidence/tools.py::ToolRegistry`, pattern = "library not carried". `task.py` `_access` / `tool_catalog` call `ToolRegistry(ctx.store).catalog/execute_async(...)`. Old forms: `store.db.execute("CREATE TABLE IF NOT EXISTS tool_operations ...")`, `store.path/'cache'/'minimap2'`, `self.store._require(...)`. Intended: ledger deleted (the system journals units; `ctx.operation_key`); `store._require(ref, kinds)` -> `ctx.store.require(ref, kinds)`; cache path -> a service.
- function = `episode_support/findings/evolutionary_history_evidence/finding_validity.py::FindingValidity` (and `target_eligible`), pattern = "library not carried" (own `sqlite3` spool; called by `credit.py current_assessments`).
- function = `episode_support/findings/evolutionary_history_evidence/scientific_findings.py::FindingIdentity`, pattern = "library not carried" (`store._require(ref, ...)` -> `records.require(ref, ...)`; called by `credit.py lead_dispositions`).
- function = `episode_support/literature/grading/literature_task_credit.py::validate_lead`, pattern = "library not carried": old call `validate_lead(store, context, lead, outcome)` reading `store._require` and `store.db` `runtime_actions` -> intended `validate_lead(ctx.store, task, proposed, ctx.store.refs(), lead, outcome)`. `task.py _validated_lead` raises `NotImplementedError('library_not_carried:literature_task_credit.validate_lead')` where it would be called (a `source_lead` of a `verified_source_leads` task that was committed).
- Credit for the three A105 task kinds (`source_answer` measurement, `a105_experiments`, `a105_assembly`): library `literature/grading/literature_credit_policy.py` (`measured_answers`, `graded_experiment_answers`, `assembled_answers`) takes the old binding and binding context. `credit.py answers` raises `ValueError('literature_task_kind_not_carried:<task_key>')` at that point, not at the top of `credit()`.

## UNPLACED OLD FUNCTIONS

- `assignment_fields.py LiteratureAssignmentFields._assignment_fields` (requested_*_components/views/component_keys properties) and the `configuration.py` population flags: exist only under the old `rate_population` configuration (off by default); not built, a commission that sends one is refused by ASSIGNMENT_FORM.
- Old `from_parent.py` Store-bound checks (page artifact equals source artifact, references in scope, source_offset_out_of_bounds): checks of a commission against the Store; a wrong commission fails (no check carried).
- Population display contexts / tools / text-witness materialization / admission of the old files.

## CONTRACT MISFITS

- new field: source_coverage_improvement scope (assignment)
- new field: source_coverage_improvement received_record_refs (assignment)
- new field: source_coverage_improvement finding (return; typed finding with source claim, subject, qualification, target correspondence and windows; a new field because the old form was written by the parent)
- The A104 axis has no usable `validate_form` for free-text findings (strings need a declared semantic type); `validate_report` checks the finding with the episode's own `RecordForm`/schema, the assignment agreement and held references.
- Tool names cannot contain dots: `source_read`, ... name the registry operations `source.read`, ... (`ACCESS` in task.py).
- `action` wraps arguments in an envelope `{arguments, scope, source_ref}` so a tool (handed no summary) can apply the source restriction and return an `invalid` outcome that enters the iterator.
- Settings read: `cost` and `parameters` (yield controller).
- Controller: `AccumulationYieldController` for `verified_source_leads`, else `CompletionYieldController` with target `credit_unit` (times number of experiments for `a105_experiments`). completion credit may pass its target: credit is `credit_unit` times the number of answers (assessment: first answer only; screening: one; a105 kinds not carried), so for the carried kinds it equals the target at most; for `a105_experiments` the unit count would be defined by the uncarried library count.
- Old tests of this episode: none. `git ls-tree -r 97308b94c` lists no file under this episode's `tests/` at that commit, so nothing was dropped and the retired-tests file has only its header; the tests/ file present is real and passes.

## UNPLACED OLD FUNCTIONS (rows of the Carried over table not listed above)

- `population_routes.py`, `population_task_context.py`, `numerical_report_facts.py`, `report_field_contracts.py`, `source_text_inputs.py`, `report_facts.py LiteratureReportFacts.current_report_facts` and the population rows of `contracts.py` (`_population_catalog`, `_required_grading_logic`): the old `rate_population` / `assay_grading_population` route (off by default, and `assay_grading_population` requires `rate_population`); not built.
- `source_custody.py _artifact` and `_validate_page`, `parent_page_contract.py _validate_parent_page_assignment`, `parent_context.py initial_decision_context`, `from_parent.py _validate_assignment` (offset within artifact size) and `prepare_assignment` re-validation: checks of a commission or the parent's context against the Store; a wrong commission fails, no check is carried.

## Not repaired

- Required grading (`evidence_grading.py::execute`, `scientific_interpretation.py::_required_grading_repository`, `contracts.py::_required_grading_logic`) is not carried. Checked against `git show 97308b94c`: the old `_required_grading_repository` returns a grading repository only when `assay_grading_population` is set (default `False`, and it requires `rate_population`); otherwise `execute_reasoning` is a plain `Store.commit_reasoning`, which `task.py reason` carries. The grading path needs the population repository (`repository.populate`, `population_schema`, `_assay_grading_repository`), the grading selector and `materialize_text_witness_inputs`, none of which exists in `episode_support/` in the final form, and this A104 episode is not an A105/A108 evidence episode. Building it would be new design inside this step, so it is left as a limit, not worked around. credit.py therefore credits assessment and screening answers without a sheet, as the old default did.
- `task.py _validated_lead` (library `validate_lead` not carried) and the library-not-carried calls above are contract/system limits, listed under BLOCKED-ON-STORE-ACCESS.
