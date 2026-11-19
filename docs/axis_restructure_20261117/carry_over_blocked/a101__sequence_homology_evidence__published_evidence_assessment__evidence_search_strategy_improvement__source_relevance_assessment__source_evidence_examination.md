# source_evidence_examination (A101): blocked, unplaced and contract misfits

## BLOCKED-ON-STORE-ACCESS

- function = `gene_annotation_episode/episodic_workflow/episode_support/tools/sequence_homology_evidence/tools.py::ToolRegistry`, pattern = "library not carried". `task.py run_access_tool` calls `ToolRegistry(ctx.store, **settings['tool_registry']).execute_async(name, arguments, scope=..., operation_key=ctx.operation_key, permitted_record_refs=...)`. Old call -> intended call: `store.db` tool_operations ledger -> deleted (the system journals units; `ctx.operation_key`); `store._require(ref, kinds)` -> `store.require(ref, kinds)`; `store.path / 'cache'` -> a service.
- function = `.../episode_support/readers/sequence_homology_evidence/source_locations.py::received_source` (called by `ToolRegistry` for source.locate), pattern = "library not carried".
- function = `.../episode_support/records/documents/sequence_homology_evidence/materials.py::source_window_selection` (called by `ToolRegistry._check_source_bytes`), pattern = "library not carried".
- function = `.../episode_support/grading/sequence_alignment/native_correspondence.py::NativeCorrespondenceScoring.read_details` (called by `credit.py credit`), pattern = "library not carried". Old call -> intended call: `store.read_snapshot()`, `store.db.execute('SELECT query_ref FROM homology_result_snapshots ...')`, `store.db.execute('SELECT result FROM tool_operations ...')` -> custody reads (`records.table(...)` / work table); `store.get` -> `records.get`. credit.py is real code and calls it with `records`.

## UNPLACED OLD FUNCTIONS

- `from_parent.py _validate_page` (page artifact equals the source's artifact for the representation; refs in scope): a check of the commission against the Store; a wrong commission fails (rule 1) and `read_from_parent` has no records.
- `source_references.py LiteratureReferences._artifact`: its only use was the dropped page-artifact check.
- `to_child_*.py prepare_request` parts: child scope validation inside the episode's scope (`store.validate_scope(selection['scope'], parent_scope=...)`), the model-composed report schema/declaration, initial report, launch-instruction materialization, allowed-role check, and the child's `prepare_assignment` within-source check. The child declares its own return; a wrong commission fails.
- `decision_inputs.py` context pieces without a home here: resource context, shared-information context, launch-instruction library and selected launch instructions, pending work, execution expectations, job execution options, resource tool estimates, native event targets, requested-action history. No job, launch or acquisition tool exists in this episode. (The old `child_option_information` is not in today's library; `task.py CHILD_OPTIONS` is written from the old role sentences.)
- `redeliver_report` action and the pending-child-delivery text: old-runner machinery (repair of an undelivered child report).

## CONTRACT MISFITS

- new field: source_evidence_examination scope (assignment; the old episode took the Store scope from its request)
- new field: source_evidence_examination received_record_refs (assignment, `record_refs`; the old episode read `context.received_record_refs`). The parent must name the source, its artifact and the sources it derives from (`parent_source_refs`), because a pass carries only the records named.
- new field: source_evidence_examination finding (return; the old episode returned the parent's requested form filled from the model's report update and had no fact sources). The episode declares its own finding form (`written`, `interpretation`, `readings`, `qualification`) and a `report` tool. It declares no selectable return field (no old fact source).
- The model no longer supplies the child's `page` and `scope` (the old `selection['assignment']` and `selection['scope']`): the child's page is this episode's page and its scope this episode's scope. A child page of a source derived from this page's source (for example an extracted archive member) is therefore not commissionable; `msg_to_child` has no records to check a derived page and a model-named scope has no custody-aware validation here.
- The commission passes every record this episode holds (`summary['held_record_refs']`, `records.refs()`) as the child's `received_record_refs`, since a pass carries only the records named and `msg_to_child` cannot read the Store.
- The children return no `record_refs` field (their return forms declare only `credit` and `finding`), so records a child produced or read are not held by this episode and do not enter its credit (`read_details(records, ..., known_record_refs=records.refs())`). The old credit view read the axis credit after the child's report recorded its refs as received. The child and this parent must agree on a record-refs return field for the credit to see child work.
- A101's `validate_form` (closed report schema) admits no free-text strings, so the old `validate_report` call `validate_form(form, schema, resolver)` cannot validate this episode's finding; `validate_report` checks the finding with the episode's own `RecordForm` and the held references.
- Tool names cannot contain dots: the library names (`source.read`, ...) are carried as `source_read`, ... (`LIBRARY_NAMES` in `task.py`).
- The tool arguments the model fills are wrapped by `action` into an envelope `{'arguments', 'scope', 'page_source_ref'}` so that the tool, which is handed no summary, can apply the old source restriction and still return an `invalid` outcome that enters the iterator.
- Settings the episode reads: `cost` and `parameters` (yield controller), optional `tool_registry` (keyword arguments of `ToolRegistry`; `native_statistics` there makes `execution_estimate` available), optional `knowledge_library_directory`.
- The old controller was the old runner's default (None); the bounded-quality controller is chosen because the A101 projector declares yield_method bounded_quality with native_score_maximum 1.0 (README 7b).
- A101SequenceCredit was called with the old assignment (for the assigned annotation); this assignment names none, so `read_details` is called with no assignment.
- `docs/axis_restructure_20261117/GOAL.md` named in the job does not exist.
- The `/home/chia/repos/gene_annotation_episode` path is a ramdisk copy without `.git`; old code was read through `/home/chia/repos/gene_annotation_episode_disk` (read-only `git show 97308b94c:`).
