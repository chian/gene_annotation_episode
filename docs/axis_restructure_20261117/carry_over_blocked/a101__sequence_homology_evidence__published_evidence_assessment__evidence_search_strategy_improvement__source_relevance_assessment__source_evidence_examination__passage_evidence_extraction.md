# passage_evidence_extraction (A101): blocked, unplaced and contract misfits

## BLOCKED-ON-STORE-ACCESS

- function = `gene_annotation_episode/episodic_workflow/episode_support/tools/sequence_homology_evidence/tools.py::ToolRegistry`, pattern = "library not carried". The tools in `task.py` (`run_access_tool`) call `ToolRegistry(ctx.store, **settings['tool_registry']).execute_async(name, arguments, scope=..., operation_key=ctx.operation_key, permitted_record_refs=...)`. Today `ToolRegistry.__init__` runs `store.db.execute("CREATE TABLE IF NOT EXISTS tool_operations ...")` and uses `store.path / 'cache' / 'minimap2'`; `_execute_operation_async` reads and writes `tool_operations` through `store.db`; `_check_source_bytes` calls `store._require(...)`. Old call -> intended call: `store.db` tool_operations ledger -> deleted (the system journals units; `ctx.operation_key`); `store._require(ref, kinds)` -> `store.require(ref, kinds)`; `store.path / 'cache'` -> a service.
- function = `.../episode_support/readers/sequence_homology_evidence/source_locations.py::received_source` (called by `ToolRegistry` for source.locate), pattern = "library not carried" (old Store calls inside the registry's source readers).
- function = `.../episode_support/records/documents/sequence_homology_evidence/materials.py::source_window_selection`, pattern = "library not carried" (called by `ToolRegistry._check_source_bytes`).

- function = `.../episode_support/grading/sequence_alignment/native_correspondence.py::NativeCorrespondenceScoring.read_details` (called by `credit.py credit`), pattern = "library not carried". Old call -> intended call: `store.read_snapshot()`, `store.db.execute('SELECT query_ref FROM homology_result_snapshots ...')`, `store.db.execute('SELECT result FROM tool_operations ...')` -> custody reads (`records.table(...)`/work table); `store.get` -> `records.get`. credit.py is real code and calls it with `records`.

## UNPLACED OLD FUNCTIONS

- `from_parent.py _validate_page` (page artifact equals the source's artifact for the representation; refs in scope) and the `source_offset_out_of_bounds` check of `_validate_assignment`: checks of the commission against the Store; a wrong commission fails (rule 1), and `read_from_parent` has no records.
- `from_parent.py prepare_assignment` within-parent-page check (`literature_reading_outside_assigned_source` against the parent's page) and `from_parent_page.py` (`OriginalPageAssignment`, `_parent_page_schema`, `_validate_parent_page`): they read the parent's own assignment, which a child cannot read (README 5 item 14). The tool-level restriction to the page source (`task.py within_source`) is carried.
- `source_references.py LiteratureReferences._artifact`: its only use was the dropped page-artifact check.
- `decision_inputs.py` context pieces without a home here: resource context, shared-information context, launch-instruction library and selected launch instructions, child options, pending work, execution expectations, job execution options, resource tool estimates, native event targets, requested-action history. This episode has no job, launch or child tool; settings-driven tool knowledge is carried.

## CONTRACT MISFITS

- new field: passage_evidence_extraction scope (assignment; the old episode took the Store scope from its request)
- new field: passage_evidence_extraction received_record_refs (assignment, `record_refs`; the old episode read `context.received_record_refs`). The parent must name the source, its artifact and the sources it derives from (`parent_source_refs`), because a pass carries only the records named.
- new field: passage_evidence_extraction finding (return; the old episode returned the parent's requested form filled from the model's report update and had no fact sources). The episode declares its own finding form (`written`, `interpretation`, `passages`, `qualification`) and a `report` tool for the model's closing text. The old parent-written form cannot be carried (rule 5).
- A101's `validate_form` (closed report schema) admits no free-text strings (every string needs a declared semantic format), so the old `validate_report` call `validate_form(form, schema, resolver)` cannot validate this episode's finding; `validate_report` checks the finding with the episode's own `RecordForm`, the assignment agreement and the held references.
- The old `source_references._require`/`resolve` resolved references through `reference_in_context` (old shared root); the held check is `records.holds` (computed in `internal_summary` as `report_source_held`).
- Tool names cannot contain dots: the library names (`source.read`, ...) are carried as `source_read`, ... (`LIBRARY_NAMES` in `task.py`); the outcomes the registry returns keep the library's shape.
- The tool arguments the model fills are wrapped by `action` into an envelope `{'arguments', 'scope', 'page_source_ref'}` so that the tool, which is handed no summary, can apply the old source restriction and still return an `invalid` outcome that enters the iterator, as the old `execute` did.
- Settings the episode reads: `cost` and `parameters` (yield controller, as `fact_extraction`), optional `tool_registry` (keyword arguments of `ToolRegistry`; `native_statistics` there makes `execution_estimate` available), optional `knowledge_library_directory`.
- The old controller was the old runner's default (None); the bounded-quality controller is chosen because the A101 projector declares yield_method bounded_quality with native_score_maximum 1.0 (README 7b).
- A101SequenceCredit was called with the old assignment (for the assigned annotation, `proposed_annotation_ref`); this episode's assignment names none, so read_details is called with assignment=None.
