# a105 source_evidence_examination: blocked, unplaced and contract misfits (19 November 2026)

Every call below is written against its intended custody-aware form, raises `RuntimeError('library_not_carried:...')`
at the point of the call (never at the top of `credit`, of a tool or of a message function) and is reported with its
exact pattern. The same library functions are called by the three child episodes of this episode.

## BLOCKED-ON-STORE-ACCESS

| Function | Pattern (old call -> intended call) |
|---|---|
| `episode_support/tools/experimental_activity_evidence/tools.py::A105ToolRegistry` | library not carried: `A105ToolRegistry(store, ...)` runs `store.db.execute('CREATE TABLE IF NOT EXISTS tool_operations ...')` -> no ledger (the system journals attempts; `ctx.operation_key`); called from `task.py::run_access_tool` |
| `episode_support/literature/grading/experimental_activity_evidence/literature_required_grading.py::execute` | library not carried: `store.commit_reasoning(payload, scope, key, account_owner=(run_id, episode_id))` -> `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)`; `dataclasses.replace(context, received_record_refs=...)` on the old BindingContext operand -> scope and held refs passed as parameters; called from `task.py::grading_execute` (the coupled commit + grading sheets) |
| `episode_support/literature/storage/experimental_activity_evidence/literature_assay_grading_storage.py::LiteratureAssayGradingRepository` | library not carried: `store.db.execute(SELECT/INSERT ... operations_table / sqlite_master / records)` -> declared work tables read with `records.table(T).select` / written with `ctx.store.table(T).put`; called from `task.py::grading_execute`, `credit.py::graded_experiment_answers` |
| `episode_support/literature/storage/experimental_activity_evidence/literature_aggregation_storage.py::LiteratureA105AggregationRepository` | library not carried: same `store.db` operations-table pattern -> work tables; called from `credit.py::assembled_answers`, `task.py::run_population` |
| `episode_support/literature/storage/experimental_activity_evidence/literature_quantity_storage.py::LiteratureQuantityRepository` | library not carried: same pattern; called from `credit.py::measured_answers`, `task.py::run_population` |
| the other 32 repositories of `task.py::POPULATIONS` / `messages/internal_summary.py::FAMILIES` (`literature/storage/experimental_activity_evidence/literature_*_storage.py`, `<Repository>(store, run_id)`) | library not carried: `store.db` operations tables, `sqlite_master`, `INSERT INTO records` -> work tables; called from `task.py::run_population`, `messages/internal_summary.py::family_cells` |
| `episode_support/literature/storage/experimental_activity_evidence/literature_sheet_updates.py::current_sheet_refs`, `current_scoring_sheets` | library not carried: `store.db` (15 sites) -> work tables; called from `credit.py` and `messages/internal_summary.py::report_facts` |
| `episode_support/findings/experimental_activity_evidence/finding_validity.py::target_eligible`, `FindingValidity` | `store._assessment_write_extent(assessment)` -> intended `records.assessment_write_extent(assessment)` (store-access.md "No replacement yet"); `FindingValidity` also keeps a `sqlite3.connect('')` spool; called from `credit.py::current_assessments` |
| `task.py::assay_grading_source_cells` | the per-family repository the assay-grading repository reads while grading (old `_assay_grading_source_cells`): same family pattern |

## Unplaced old functions

After the repair of 19 November 2026 only these old functions have no place:

| Old | Reason |
|---|---|
| prompts/literature_work_report.py::completed_work | SQL over runtime_actions, runtime_observations and runtime_report_attempts (the old journal tables). Its per-action credit marks are the system's journal, which a summary does not see, so no pure re-expression over `view.outcomes` exists |
| internal_summary.py::SourceSummary.initial_decision_context | the root episode's initial context (`reference_evidence_parent`); its guard `context.role != 'annotation' or len(context.path) != 1` is never true in this literature_page episode; the root is outside this job |
| tools `source.sequence.scan`, `image.view`, `source.xlsx.sheets`, `source.xlsx.rows`, `execution.estimate` | the A105 tool library implements none (`A105ToolRegistry.catalog`); the old catalog was the registry's catalog intersected with `_ACCESS_TOOLS`, so the same five are not offered now |

Placed by the repair (private copies, "library candidate", in `messages/internal_summary.py` and `task.py`): the 33
functions of `prompts/literature_experimental_prompt.py` and their helpers, `literature_kinetic_model_render`,
`literature_reference_parent_prompt`, `literature_task_selection` and `literature_task_families` (A105's, because the
library file they were mapped to is A106's), `literature_work_report` (without `completed_work` and the SQL),
`literature_current_results`, `literature_work_results` (`returned_result` and its helpers), the 22 functions that
the library copy of their old file lacks, `own_source_inputs`, `source_metadata`, `prepare_completed_work`,
`rejection_detail`, `source_artifact` and the display contexts of the old `SourceSummary`. The renderer is not wired
into `decide` (see "Not repaired").

## Not repaired

- The decision-prompt renderer and the completed-work and current-result renderers (`prompt_render_literature_experimental_prompt`, `reference_parent_render_reference_evidence_parent_prompt`, `work_report_render_completed_work`, `current_results_render_current_*`) are placed but not wired into `decide`: they render the old decision state (`child_reports`, `lookup_results`, `working_state`, ...), and they need names of the old shared root `root.a105` that have no library counterpart (`text_instructions`, `_band`, `_schema` of `experimental_activity_evidence_prompt`; `CONTRACT_INFORMATION_PROFILE`, `CONTRACT_ARGUMENT_TRANSPORT`, `is_contract_information`, `requested_contract_information` of `composition_information`; `FACT_REFERENCE_PREFIX`, `expand_fact_form`, `ContractInformationError` of `episode_contract_information`; `completed_action_reports` of `episode_work_report`). Each is a `_not_carried(...)` name: any use raises `RuntimeError('library_not_carried:...')`. `decide` keeps showing the structured summary.
- The display contexts of the old population flags are gated by the families the commission requested (a summary has no settings): the contexts that need a family repository (rate, gel, controlled response, endpoint, precision, comparison, window) raise `library_not_carried` through `library_repository`, as `family_cells` does.
- `table_evidence_extraction`'s RETURN_FORM declares no `record_refs` field, so `read_from_child` returns `[]` for `finding_refs` and `sheet_refs` of that slot and the parent's credit cannot count its assessments or sheets. The child folder is read-only in this job; the field is to be added in that child.
- `completed_work`, `initial_decision_context` and the five tools above (see the table).
- BLOCKED-ON-STORE-ACCESS and the contract misfits below are limits of the system and the library, not repaired.

## Contract misfits

- Tool names: a tool name is `[a-z][a-z0-9_]*`, so `source.read` is `source_read` and `literature.assay_grading.populate` is `literature_assay_grading_populate` ("names both sides use are the old names, unchanged" cannot hold for tools).
- Child slot names are the child folder names (`table_evidence_extraction`, `source_coverage_improvement`, `passage_evidence_extraction`); the old roles were `literature_table`, `literature_ordered`, `literature_targeted`.
- `validate_form` is not built for A105: the old `validate_report` called it; it is not called here (no `validate_form_not_built:experimental_activity_evidence` is reached because nothing calls it).
- new field: source_evidence_examination scope (the old episode took the scope from its request).
- new field: source_evidence_examination received_record_refs (the old episode took what it received from its binding context). The parent must name every record this episode reads: the source and its artifact, the sources it derives from, the proposed annotation and its hypothesis, the records of the commissioned task such as sheets, and every record the commissions to its children will name (a passed record does not bring the records it names).
- The 39 other `requested_*` properties of the old assignment schema are declared as plain optional lists (the old enums are the family libraries' COMPONENTS, checked where the family is read); only the three of the task kinds have options.
- The RETURN_FORM declares the cell families as list fields with a shortened meaning, without an item form (the old `report_schema` rows are the family libraries' schemas).
- new field: source_evidence_examination finding.child_returns, finding.child_finding_refs, finding.child_sheet_refs (what the commissioned children returned: the old parent admitted the child forms into its own repositories and held their records through receipt inheritance).
- new field: source_evidence_examination report tool (`sources`: source_ref, statement, qualification): the old report was the parent's declared typed form filled from the model's report update; the model's closing value is now the outcome of the declared `report` tool.
- The old child envelope written by the model (`version`, `page`, `selection`, requested components) is now the `ChildCall` arguments `objective`, `page` (source_ref, representation, artifact_ref) and `selection`; `msg_to_child` adds the page's question-context and prior-delivery records, `literature_task`, `proposed_annotation_ref`, the requested arrays of the families it selects, `scope` and the records. The selected fields are `literature_source_lead_dispositions`, `literature_screening_answers` and the families this episode was asked for (per child: the table reading declares only the quantity, assay-grading and aggregation cells; the ordered reading also `sheet_refs`).
- Required return source `changed_assessment_refs` (old `goal.commissioned_task`, assessment answers): no child declares such a field; the assessments a child committed travel in its `finding` (`assessment_refs` of the targeted-passage reading, `finding_refs` of the ordered reading) and the table reading returns its assessment refs as text (`assessment_findings[].assessment_ref` is a text field, not a `record_refs` field).
- The table evidence extraction child returns no `record_refs` field at all: the parent holds none of its assessments or sheets and its credit cannot count them. Needed in that child: its own `assessment_refs` and `sheet_refs` as `record_refs` fields (reported by whichever side adds them; this episode's `read_from_child` already reads `finding_refs` and `sheet_refs` and returns `[]` for that slot).
- The ordered-reading child's assignment names its passed records `record_refs`; the table and the targeted-passage children name theirs `received_record_refs`, and the ordered reading's `page.question_context_refs` / `prior_delivery_refs` are plain lists where the others are `record_refs`. `msg_to_child` writes each under the child's own field name, and names every record this episode holds in it (the old child inherited the parent's received records through the receipt ledger).
- `internal_summary` cannot see the commission's `selection`, so it reads the cells of every requested family each unit (requested family means a non-empty `requested_*` array); a summary without the settings cannot show the population display contexts.
- Completion credit cannot pass its target: every task kind counts at most `credit_unit` (one answer) or one answer per requested experiment, the target being `credit_unit` times the same number. A child's returned credit is never added to this episode's credit (a parent measures its own).
- `credit.py` raises `RuntimeError('library_not_carried:...')`, not `NotImplementedError`, at the library points (the firm rule on `credit.py`).
- Settings keys read by this episode: `cost` and `parameters` (controller; the accumulation cost must be above zero or the controller never stops), `rate_population` and the old population flags, `tool_registry`, `knowledge_library_directory`.
- A wrong commission fails: a model-chosen child page whose source is not held (or whose artifact differs from this episode's for its own source) fails where the commission is built (`CustodyError` or `literature_reading_<field>_mismatch`); nothing rejects it in `action`.
