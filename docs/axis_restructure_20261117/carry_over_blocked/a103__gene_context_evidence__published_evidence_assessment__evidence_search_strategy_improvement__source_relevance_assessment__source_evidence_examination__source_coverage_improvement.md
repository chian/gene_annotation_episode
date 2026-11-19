# Blocked, unplaced and misfit items: A103 source_coverage_improvement (19 November 2026)

## blocked_on_store_access

- `episode_support/tools/gene_context_evidence/tools.py::ToolRegistry` (called in `task.py` `tool_catalog` and `_access` as `ToolRegistry(ctx.store)`, then `.catalog(scope)` and `.execute_async(...)`). Pattern: "library not carried". Old call `ToolRegistry(store)` runs `store.db.execute(CREATE TABLE tool_operations ...)`, `store.path / 'cache'`, and `execute_async` reads `tool_operations` through `store.db`. Intended: `ToolRegistry(ctx.store)` over the custody operations only; the operation ledger is the system's attempts journal (`ctx.operation_key`). The call stays as written.
- `episode_support/grading/gene_context_evidence/credit.py::A103ContextCredit` (called in `credit.py` as `A103ContextCredit()(records, scope, known_record_refs=records.refs())`). Pattern: "library not carried". Old: `received_attachments(store, known)` and `received_measurement(store, ref)` read the tables `a103_attachments`, `a103_publications`, `a103_bindings` with `store.db.execute(...)`; `component_assessment_dependencies.assigned_annotation` uses `store._assessment_write_extent`. Intended: declared work tables read with `records.table(T).select(...)` and custody-aware reads. The call stays as written; `credit.py` is real code that raises where the library fails.

## unplaced_old_functions

- `from_parent.py::SourceAssignment._validate_page`: checks of the commission against the Store (source artifact of the named representation equals `artifact_ref`; the context and prior-delivery refs are in scope). A wrong commission fails at form admission and custody; not carried.
- `from_parent.py::SourceAssignment._validate_assignment`: the offset-bound check (`source_offset_out_of_bounds`) needs the artifact's `size` from the Store and `read_from_parent` has no records; not carried. The schema constraints and the window's source and representation agreement with the page are carried in `read_from_parent`.
- `from_parent.py::SourceAssignment.prepare_assignment` and `parent_page_custody.py` (`_parent_page_schema`, `_validate_parent_page`): re-validation of the commissioning parent's own page assignment and `literature_reading_outside_assigned_source` against it (README 5 item 14; a check of a commission). The tool-time restriction of every operation to the assigned source (`task.py _within_source`) is carried.
- `source_references.py::SourceReferences._artifact`: only used by the dropped page-artifact check.
- `task_presentation.py::_guidance` and `render_requested_return`: the guidance came from the old parent request; the parent now passes `gene_context_evidence` and the episode shows its `assignment` parts.
- `decision_inputs`: resource context, shared-information context, launch-instruction library and selected launch instructions, execution expectations, job execution options, resource estimates, native execution expectations and event targets, requested-action history are not carried: nothing supplies them and the leaf offers no job or HPC tool.
- `source_interpretation.py` (reasoning action), `scientific_records.py` (automatic judgments): neither was offered; nothing to carry.

## contract_misfits

- new field: source_coverage_improvement scope (assignment; the old episode took the Store scope from its request)
- new field: source_coverage_improvement received_record_refs (assignment, `record_refs`; the old episode read `context.received_record_refs`). The parent must name the source, its artifact and the sources it derives from (`parent_source_refs`), because a pass carries only the records named.
- new field: source_coverage_improvement finding (return; the old episode returned the parent's requested form filled from the model's report update and had no fact sources). The episode declares its own finding form (`source_claim`, `source_subject`, `qualification`, `target_correspondence`, `windows`) and a `report` tool for the model's finding; the parent writes no return form (rule 5).
- Tool names cannot contain dots: library names (`source.read`, ...) are carried as `source_read`, ...; outcomes keep the library's shape. `action` wraps the model's operands into an envelope (`arguments`, `scope`, `source_ref`) so the tool can apply the old source restriction and still return an `invalid` outcome that enters the iterator.
- Settings the episode reads: `cost` and `parameters` (yield controller).
- The old controller was the old runner's default (None). Bounded-quality is chosen because `A103ContextCredit` declares `yield_method = 'bounded_quality'` with `native_score_maximum = 1.0` (README 7b).
- A103 has `validate_form` but it cannot check the episode's own free-text finding (closed report schema); `validate_report` checks the finding against the episode's own schema and the held cited sources.
- The old `selection` was one window (`_WINDOW`); `ASSIGNMENT_FORM.selection` is that one window record, unchanged.
