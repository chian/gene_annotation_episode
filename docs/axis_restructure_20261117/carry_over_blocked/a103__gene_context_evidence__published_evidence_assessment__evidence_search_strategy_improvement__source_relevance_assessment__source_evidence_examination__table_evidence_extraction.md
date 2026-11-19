# table_evidence_extraction (A103): blocked, unplaced and contract misfits

## BLOCKED-ON-STORE-ACCESS

- function = `gene_annotation_episode/episodic_workflow/episode_support/tools/gene_context_evidence/tools.py::ToolRegistry`, pattern = "library not carried". `task.py` `run_access_tool` and `tool_catalog` call `ToolRegistry(ctx.store, **settings['tool_registry'])` (`.catalog(scope)`, `.execute_async(...)`). `ToolRegistry.__init__` runs `store.db.execute("CREATE TABLE IF NOT EXISTS tool_operations ...")` and uses `store.path / 'cache' / 'minimap2'`; its operations read and write `tool_operations` through `store.db` (14 `store.db`/`store.path` sites). Old call -> intended call: `store.db` tool_operations ledger -> deleted (the system journals units; `ctx.operation_key`); `store.path / 'cache'` -> a service.
- function = `.../episode_support/records/gene_context_evidence/attachments.py::received_attachments` and `.../records/gene_context_evidence/publication.py::received_measurement`, pattern = "library not carried". Both are called by `grading/gene_context_evidence/credit.py::A103ContextCredit.read_details` (called by `credit.py credit` with `records`) and read `store.db.execute('SELECT ... FROM a103_attachments / a103_publications / a103_bindings')` plus `sqlite_master`. Old call -> intended call: `store.db` SELECT on `a103_attachments`, `a103_publications` -> `records.table(<declaration>).select(...)` over a declared work table. `credit.py` is real code and calls the projector with `records`; it fails inside the library until those are carried.
- function = `.../episode_support/grading/gene_context_evidence/credit.py::A103ContextCredit.read_details`, pattern = "library not carried" (uses `store.read_snapshot()` and `store.validate_scope`, which `records` offers, but reaches the two readers above).

## UNPLACED OLD FUNCTIONS

- `from_parent.py _validate_page` and the `source_offset_out_of_bounds` check of `_validate_assignment`: Store checks of the commission (artifact against source representation, refs in scope, offset against artifact size); a wrong commission fails (rule 1) and `read_from_parent` has no records.
- `from_parent.py prepare_assignment` (operation_key, within-parent-page check) and `parent_page_custody.py` (`_parent_page_schema`, `_validate_parent_page`): they read the parent's own assignment, which a child cannot read. The tool-level restriction to the page source (`task.py within_source`, `admitted`) is carried.
- `task_presentation.py _guidance`: evidence-axis, thought-pattern, child-tool-info and annotation-support guidance and assigned launch manuals; no home (no child, no launch).
- `decision_inputs.py` context pieces without a home here: resource context, shared-information context, selected launch instructions, child options, completed/requested action reports, pending work, execution expectations, resource and native estimates, native event targets, contract-information profile. Tool knowledge and the launch-instruction library listing are carried from settings directories.
- `decision_state.py` pieces without a home: annotation context, current credit / evidence vector / credit binding, receipt projection, report deliveries, job episode options.

## CONTRACT MISFITS

- new field: table_evidence_extraction scope (assignment; the old episode took the Store scope from its request)
- new field: table_evidence_extraction received_record_refs (assignment, `record_refs`; the old episode read `context.received_record_refs`). The parent must name the source, its artifact and the sources it derives from, since a pass carries only the records named.
- new field: table_evidence_extraction finding (return; the old episode returned the parent's requested form filled from the model's report update and had no fact sources). Own typed A103 finding form (`source_claim`, `source_subject`, `qualification`, `target_correspondence`, `readings`) and a `report` tool for the model's finding. A103 is not an A105/A108 episode, so no saved subscoring sheet applies.
- The old assignment `selection` was `anyOf` a table selection or a byte window; forms have no union and no null. `selection` is one open `record` field, admitted by `read_from_parent` against TABLE_FORM or WINDOW_FORM (a `sheet_key` selects the table form); a null `header_row`, `where` or `where.column` is the field omitted.
- Tool names cannot contain dots: library names (`source.read`, ...) are carried as `source_read`, ... (`ACCESS` in `task.py`). `tool_catalog` is a new first lookup tool (the old services tool catalogue).
- `action` wraps the model's arguments into an envelope `{'arguments', 'scope', 'source_ref', 'sheet_key'}` so that the tool, which is handed no summary, can apply the source restriction and the sheet guard and still return an `invalid` outcome that enters the iterator.
- `final_to_parent` raises `a103_table_evidence_finding_not_reported` when the controller stops the Episode before any finding was reported (no fallback value).
- Settings the episode reads: `cost` and `parameters` (yield controller), optional `tool_registry`, `knowledge_library_directory`, `launch_instruction_directory`.
- The old controller was the old runner's default (None); the bounded-quality controller is chosen because `A103ContextCredit` declares yield_method bounded_quality with native_score_maximum 1.0 (README 7b).
- `A103ContextCredit` is called with `assignment=None`: this assignment names no proposed annotation.
- Old tests: this episode had none at 97308b94c and the working tree held none, so the retired-tests file has only its header.
