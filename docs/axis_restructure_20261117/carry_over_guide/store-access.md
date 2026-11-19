# Store access in the library: from raw Store calls to custody (19 November 2026)

The owner's rule: library functions never write to the Store or its tables directly. Anything they read or write
goes through custody: the scoped store the system hands the episode (`ctx.store` in a tool; the read-only
`records` in `credit`, `action`, `read_from_child`, `internal_summary`, which has every read of `ctx.store` and
no write), or an operation of it that has custody built in. A library function receives that object as its `store` (or `reader`) argument and calls only what it
offers. It never receives the `Store`, its connection (`store.db`) or its directory (`store.path`).

This page is the mapping for the carry-over, per function family. It does not rewrite the library. The API it
maps to is in `BINDING_CONTRACT.md` ("The Store under custody"); the code is `episode_runtime/store_scope.py`,
`episode_runtime/work_tables.py`, `episode_runtime/scratch.py` and `episode_runtime/work_cache.py`; the worked
examples are `episode_runtime/tests/sheet_library.py` and `episode_runtime/tests/operations_library.py` (one
library function per pattern of the table "System operations built in stage 1", each naming the raw-Store
pattern it stands in for) with the `probe` test episode, run by `episode_runtime/tests/test_system_operations.py`.
`episode_runtime/tests/test_library_boundary.py` fails while a library function module imports the
`Store` class at run time, and prints the number of raw-Store sites left in each function family (lines
`RAW_STORE_SITES ...`), so the numbers of section 1 can be followed down.

## 1. How the library uses the Store today

Counted with `grep` on 19 November 2026 over the non-test files of `episode_support/` (513 of them mention a
`store`). "Sites" are call sites on a `store` object.

| Call | Sites | | Call | Sites |
|---|---|---|---|---|
| `store.db` (raw SQL) | 1,604 in 253 files | | `store.subject_molecule/length/unit` | 201 |
| `store.get` | 1,388 | | `store.path` | 130 |
| `store.artifact` | 696 | | `store.get_input` | 72 |
| `store.get_artifact` | 568 | | `store.map_segments`, `roots`, `sequence_mapping`, `coverage`, `has_exact_mapping` | 174 |
| `store.transaction` | 421 | | scope and mask arithmetic (`scope_covers`, `scope_contains`, `context_mask_overlap`, ...) | 138 |
| `store._require` | 376 | | `store.register_material` | 24 |
| `store.put` | 306 | | `store.problem` | 22 |
| `store.validate_scope` | 257 | | other private helpers (`_unit`, `_caller_source`, `_assessment_write_extent`, `_literature_sheet_updating`, `_in_scope`, `_merge_segments`, `_covered_by`, `_record_roots`, `_assert_library_write_scope`, `_refs`) | 159 |
| `store.reference_subset` | 165 | | `material_*`, `parse_material` | 54 |
| `store.read_snapshot` | 27 | | `current_assessments`, `current_assessment_subset`, `query_records`, `record_coverage`, `scope_coverage`, `commit_reasoning` | 40 |

The raw SQL, by family (sites of `store.db`):

| Family | Sites | What the data is | Class |
|---|---|---|---|
| `literature/` (`storage` 867, `grading` and `inputs` 21) | 888 | scoring sheets and their cells, current-sheet pointers, sheet dependencies, model judgments, grading ledgers (`literature_*_operations`, keyed by run, episode and operation key), sets of what an episode received (`literature_*_received`); also lookups in the Store's `records` table | **records of an Episode's work**: under custody as work tables and Store records |
| `records/` | 365 | nine per-axis copies of the Store's own material implementation (`records/documents/*/materials.py`: the `material_*` and `library_selection_members` tables, `inputs`, `problem`, `artifacts`), and finding and credit projections (`known_findings`, `current_findings`, `grades`, `operands`, `witnesses`) | **Store implementation** (not an episode's business: one copy, with the Store) and **records of an Episode's work** |
| `jobs/` | 194 | registries of provider jobs and their failures (`provider_jobs`, `provider_job_failures`), HPC commission sources, native component requests and actions, and reads of the old runner's `runtime_*` tables | **job state** (a service's own durable state, or work-table rows when it is the Episode's record of a job) and **old-runner machinery** (dropped) |
| `tools/` | 108 | the tool operation ledger (`tool_operations`: 58 sites in 31 files), table-exists checks, lookups in `records` | **replay bookkeeping** (the system's now) and **record access** |
| `acquisition/`, `readers/`, `grading/`, others | 49 | lookups in `records`, `inputs`, `artifacts` | **record access** |

Across families: 149 sites in 133 files query the Store's `records` table directly; 139 sites in 112 files ask
`sqlite_master` whether a table exists; 59 sites in 21 files read `runtime_*` tables; 28 sites read
`store.db.in_transaction`; 14 call `store.db.commit`; 27 create tables with `executescript`.

`store.path` (130 sites) is used for: the file of an artifact (`store.path / "artifacts" / sha[:2] / sha`, about 45
sites); temporary files and directories on the Store's filesystem (about 50); writing a large download straight
into the artifact directory (with a raw `INSERT INTO artifacts`: 14 sites in 14 files); a cache directory (4).

Not in these counts: 125 `self.db` sites in 7 files that keep SQLite files of their own beside the Store
(`run_statistics.py` in three copies, `homology_jobs.py` in two, `episode_receipts.py` in two).

The `register_native_target` and `publish_native_event` calls (9 each) are not Store calls: the object named
`store` there is the native event ledger (`episode_support/jobs/native_event_ledger.py`, `NativeEventLedger`), a
separate SQLite file a detached local job writes from its own process.

One library function module imports the `Store` class at run time today:
`tools/protein_structure/protein_structure_tools.py`, which opens the Store by path in a worker thread
(`Store(store_path)`, lines 482-484). `test_library_boundary.py` fails on exactly this module until it is carried
over. `readers/protein_structure/protein_structure_operands.py` imports `Store` only under `if TYPE_CHECKING:`,
for an annotation; that is not counted, and the line goes when the module is carried.

## 2. The replacement for each pattern

`store` below is the scoped store a tool passes to the library function (`ctx.store`); `reader` is `ctx.store` or
the read-only `records`. Every read finds only what the Episode holds; every write is held by the Episode as
produced by the unit, receipted when its transaction commits.

### Same call, now under custody (no change of name)

| Old | Now | Changed behaviour |
|---|---|---|
| `store.get(ref)`, `store.get_artifact(ref)` | the same | `CustodyError` when the Episode does not hold `ref`. This is the largest change for the library (1,388 `store.get` and 568 `store.get_artifact` sites): a `get` that follows a reference found in another record needs that reference held too. A pass carries only the records named (provisional, decision T5 of `BINDING_CONTRACT.md`): a parent names every record the child's library code will read, and a child every record its parent's will |
| `store.put(kind, record, origin=..., scope=...)` | the same | every record the new record names (its `..._ref`, `..._refs`, `ref`, `dependencies` values) and every subject of `scope` must be readable, else `CustodyError`; no `account_owner=`: interpretation accounts are written by `commit_reasoning` |
| `store.artifact(data, media_type)` | the same | |
| `with store.transaction():`, `with store.read_snapshot():` | the same | what is written inside is receipted on commit; nothing is held after a rollback |
| `store.validate_scope`, `scope_contains`, `scope_covers` | the same | every subject and read selection the scope names must be held |
| `store.normalize_context_mask`, `context_mask_identity`, `context_mask_subset`, `context_mask_overlap`, `footprint_dimension`, `footprint_from_mapping`, `assessment_key` | the same | every subject and read selection the mask names, the target the span names, every subject the mapping's path names must be held (the Store reads them), else `CustodyError` |
| `store.reasoning_schema()` | the same | |
| `store.get_input`, `roots`, `material_errors` | the same | the named record must be held |
| `store.subject_length`, `subject_unit`, `subject_molecule`, `coverage`, `sequence_mapping`, `has_exact_mapping`, `map_segments`, `material_read`, `material_annotations` | the same | the named record must be held, **and every record the Store reads on the way**: a product's or reference's sequence artifact, a feature's parent subjects, the subjects a product's mapping runs over, a material's source and that source's artifact, a parse attempt's material and native source. Else `CustodyError` (the table: `BINDING_CONTRACT.md`, "What a read reaches") |
| `store.material_members`, `material_member` | the same | a collection member, with its packed bytes, is read by an Episode that holds it or its collection |
| `store.parse_material`, `material_header`, `material_reference` | the same, on `ctx.store` only | they write: the Episode holds what they create. `parse_material` requires the material and every record it names to be readable; `material_reference` requires the member's collection and every record the collection names |
| `store.reference_subset(candidates, scope)` | the same | candidates the Episode does not hold are dropped; the scope's subjects must be held |
| `store.query_records(kind, scope, ...)`, `store.reasoning_view(scope, limit)` | the same, without `record_selection=` | the page is selected among the held records; every reference in `references=` must be held |
| `store.list`, `count`, `subjects`, `references`, `targets`, `current_assessments`, `current_annotations`, `iter_current_annotations`, `iter_current_accounts`, `current_assessment_subset` | the same | inventories of **held** records only. `list(kind, scope=None, limit=None, offset=0)` returns every held record unless a `limit` is given (the Store's own `list` stops at 100). The Episode whose unit called `store.create_problem(...)` also holds the problem's own reference (`problem_...`); it is a record of no kind, no inventory lists it, and the problem is read with `store.problem()` |
| `store.record_coverage(row)`, `store.scope_coverage(scope)`, `store.scope_dimension_segments(scope, ref)` | the same | the record `row['id']` (read again from the Store; the rest of `row` is not used), or the scope's subjects, must be held. For an assessment its hypothesis, and for a hypothesis or an observation every subject it names, must be held too |
| "is this assessment still current" by a query on `current_revisions` | `reader.is_current(ref)` | the record must be held |
| `store.register_material(...)` | the same | a `source_ref` must be held; the Episode holds the material and the records it names |
| `store.problem()["subject_refs"]` | the same (or `store.targets()`) | only the subjects the Episode holds |

### Renamed or reshaped

| Old | Now |
|---|---|
| `store._require(ref, kinds, field_path=...)` | `store.require(ref, kinds, field_path=...)` |
| `store._in_scope(ref, store.validate_scope(scope))` | `store.in_scope(ref, scope)` |
| `store.path / "artifacts" / sha[:2] / sha` (to read an artifact's file) | `reader.open_artifact(ref)`: a read-only binary file object of the held artifact. There is no path. A function that must give a file name to an external program copies the bytes into a scratch directory: `scratch.copy_artifact(ref, name)` (next table) |
| `store.db.in_transaction` | `store.in_transaction()` |
| `store.commit_reasoning(payload, scope, key, account_owner=(run_id, episode_id))` | `store.commit_reasoning(payload, scope, ctx.operation_key)`: the system names the owner; every record the payload names must be readable |
| `SELECT data FROM records WHERE record_type=? AND json_extract(data, ...)=?` | `store.list(kind, scope)` (every held record of the kind) filtered in Python, or `store.query_records(kind, scope, references=[...])` for "which records name this reference"; only held records are found |
| a library table of an Episode's work: `CREATE TABLE IF NOT EXISTS ...`, `INSERT`, `UPDATE`, `SELECT` through `store.db` | a declared work table: `T = TableDeclaration(name, columns, key, record_refs)` at module level; `store.table(T).put(values)` writes the Episode's row with that key (the same key again is the next revision of the same row); `reader.table(T).get(row_ref)` and `reader.table(T).select({column: value})` read the held rows. The system fills `run_id`, `episode_id`, `unit`, `operation_key`, `revision`. A row is passed to a child or a parent by naming its `row_...` reference in a `record_refs` field |
| `SELECT 1 FROM sqlite_master WHERE name=...` | deleted: a declared table always exists |
| a `*_operations` ledger asking "did this operation already run?" | deleted: the system journals each unit's attempt. The tool gets `ctx.operation_key` (stable), `ctx.resumed` and `ctx.abandoned` (what the abandoned attempt produced: read it, or take it over with `ctx.store.reclaim(ref)`). A saved outcome the rerun needs is a work-table row keyed by the library's own key |
| a `*_received` table recording what an Episode received | deleted: that is custody. `store.refs()`, `store.receipt(ref)` (`how`, `from`, `producer`), and the child's result in `outcomes` |
| reads of `runtime_episodes`, `runtime_actions`, other `runtime_*` | deleted: old-runner machinery. The Episode's own history is its view (`parent_input`, `outcomes`, `updates`) |
| `NativeEventLedger(...)`, `register_native_target`, `publish_native_event`, `wait_events` | a declared service (job access; none wraps the ledger yet, 21 library modules import it directly); the bytes of a published receipt become a Store record when a tool writes them with `store.artifact` |
| `store.put('native_execution', ...)` and `store._require(ref, {'native_execution'})` | a work-table row: section 4 |

### System operations built in stage 1 (19 November 2026)

Every row here was in the table "No replacement yet" until stage 1 built it. The call sites were read to define
each operation: what they pass is stated in the row. `store` is `ctx.store`; `reader` is `ctx.store` or `records`.
The last four rows (marked stage 1c) were built for the stage 2 blockers `STAGE2_BLOCKERS_lib8.md` (items 1 to 3)
and `STAGE2_BLOCKERS_lib10.md` (item 1).

| Old (sites, non-test) | Now: the exact call | What it does, and its custody |
|---|---|---|
| a temporary file or directory under `store.path`: `tempfile.mkdtemp(dir=store.path)`, `TemporaryDirectory(dir=store.path)`, `mkstemp(dir=store.path)` (about 50 sites: `tools/<axis>/tools.py`, `findings/<axis>/image_evidence.py`, the `materials` copies) | `with store.scratch('label') as scratch:` then `scratch.path / 'name'` | a directory of the running unit, outside custody, removed with its content when the block is left (also by an error). Only inside a tool unit; a unit that ends with one open raises `CustodyError('unit_ended_with_an_open_scratch_directory')`. Nothing in it is a record. What a cut process left is removed when the Episode is next built (resume), before the unit runs again: the rerun gets a new empty directory |
| giving an artifact's file to an external program (`artifact_path(store, ref)` and the `path` it returned) | `scratch.copy_artifact(ref, 'inputs/name')` (returns the `Path` of the copy) | the artifact must be held (`CustodyError`); the copy is checked against the artifact's digest |
| `Store(store_path)` opened in a worker thread (`tools/protein_structure/protein_structure_tools.py:481-486`, 1 site, called at 565 and 925) | `result = await scratch.compute(function, *arguments, **keywords)` | runs `function(*arguments, cancel_event=<threading.Event>, **keywords)` in a worker thread and returns its value. The thread is given files and plain values; `ctx.store` refuses every call from it (`CustodyError('scoped_store_used_outside_the_thread_of_its_unit')`). A cancelled unit sets the event and waits for the thread before the directory is removed. The tool reads the inputs with `copy_artifact` before, and writes the results with `artifact_file` after. `prepare_protein_structure_worker` is rewritten on this in stage 2 (`operations_library.residue_counts` is the pattern) |
| capturing a file into the artifact directory with a raw `INSERT INTO artifacts` (`artifact_file(store, path, media_type)`: 14 sites in 14 files, `readers/<axis>/source_bytes.py` and the nine `records/documents/*/materials.py`) | `store.artifact_file(path, media_type='application/octet-stream')` | one receipted write over the Store's own `gene_annotation_episode.materials.artifact_file` (hashed while copied, never loaded); the Episode holds the artifact as produced; in `with store.transaction():` it is receipted on commit. The fourteen library copies of `artifact_file` are deleted |
| the same, for a download that arrives in chunks or a file object | `store.artifact_stream(stream, media_type='application/octet-stream')`: `stream` is a binary file object or an iterable of `bytes` | as `artifact_file`; the chunks are gathered in a file of the system's own, which is removed |
| `store.path / "cache" / "minimap2"` (4 sites: `tools/<axis>/tools.py`, the `cache_dir` of the aligner configuration) | **a declared service**, not an operation of the store: the episode declares `SERVICES = ('work_cache',)`, the run's caller supplies `{'work_cache': lambda: WorkCache(directory)}` (`episode_runtime.WorkCache`), the tool calls `ctx.services['work_cache'].directory('minimap2')` (a `Path` that persists) | why a service: a cache is no record (nothing an Episode holds, passes or returns), it is shared by every Episode and by later runs, and emptying it changes no result. The scoped store hands out only what custody covers and nothing that outlives the unit; a service is the run's access to what is outside the Store, built once per run and journaled |
| `store.db.commit()` (14 sites, all the same: after `CREATE TABLE IF NOT EXISTS` in a constructor, `tools/<axis>/tools.py` for `tool_operations` and `jobs/service_calls/<axis>/provider_jobs.py` for `provider_jobs` and `provider_job_failures`) | nothing: the statement and its commit are deleted together. The table is a `TableDeclaration` (it always exists; its declaration is recorded with its first committed write), or it is gone (`tool_operations`: the system journals unit attempts). Several writes that must be one step: `with store.transaction():` | there is no `commit`: a single write is a transaction of its own, receipted when it commits; a library function never ends a transaction it did not open (`operations_library.register_job`) |
| `SELECT 1 FROM records WHERE id=?` on the identity a `put` will have, to list what the function created (128 sites: 127 in `literature/storage`, `publish(kind, record)`, and 1 in `literature/inputs`) | `new = not store.holds(candidate)` before the `put` | "created" now means new to the Episode: the write is content-addressed, so writing content another Episode wrote returns the same reference, held as produced by this unit, without reading anyone's record (`operations_library.publish`) |
| "was this already fetched or computed by anyone": a lookup of another Episode's source record | `data = ctx.services['work_cache'].get(namespace, key)`; when `None`, do the work and `.put(namespace, key, data)`; then `store.artifact(data)` | the bytes come from the cache service, never from a record the Episode does not hold; the artifact is the Episode's own product (`operations_library.fetch`). `key` is any closed JSON; `.has(namespace, key)` is the question a decision may read |
| `SELECT ... FROM records WHERE record_type='parse_attempt' AND json_extract(data,'$.parse_key')=?` (9 sites, the `materials` copies) | `store.parse_material(material_ref)` | the Store's own parse is idempotent: parsing again returns the same parse attempt, held as produced |
| `SELECT id FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=?` (7 sites, `jobs/service_calls/<axis>/job_provider.py`: every job receipt of the run) | not a Store lookup any more: a job's record is a row of the job ledger the job access service writes through `ctx.store` (stage 1b, `episode_runtime/job_access.py`), held by the Episode that launched it and passed by reference | an Episode lists only the job rows and sources it holds (`reader.table(...)`, `reader.list('source')`); nothing lists every Episode's |
| `store._caller_source(value, provider)` (27 sites in the nine `records/documents/*/materials.py`) | `store.caller_source(value, provider)` | the Store's own rule: the canonical bytes of `value` as an artifact and a `source` record of origin `caller`; the Episode holds both as produced. (After stage 2 only the Store's one `materials.py` calls the private form) |
| `store._assessment_write_extent(row)` (20 sites in 20 files: `findings/<axis>/finding_validity.py` and `scientific_findings.py`, `records/sequence_and_context_sources/<axis>/component_assessment_dependencies.py`, `literature/storage/<axis>/literature_aggregation_storage.py`; `row` is always a stored assessment) | `reader.assessment_write_extent(row['id'])` | the Store's rule run over held records: the same segments, `[]` or `None`. The assessment, its hypothesis and observation, the subjects those name and what each subject's coverage and mapping follow must be held, else `CustodyError`; a reference that is not an assessment raises `ValueError` |
| `store._record_roots(kind, row)` (8 sites: `findings/<axis>/scientific_findings.py` for an assessment, `literature/grading/literature_task_credit.py` for a hypothesis; `row` is always a stored record) | `reader.roots(row['id'])` | the same list: the Store computes the roots of a record with `_record_roots` when it writes it and `roots` returns them. Only the record itself must be held |
| `store._assert_library_write_scope('assessment', row, scope, current=row)` (5 sites, `findings/<axis>/scientific_findings.py`, `validate_replacement_scope`; `row` is a stored assessment) | `reader.assert_library_write_scope(row['id'], scope)` | raises the Store's `ContractError` unless the held record is owned within `scope` (a revisioned record as proposed and as current). The scope's subjects and every record the rule reads (the hypothesis, its subjects, a read selection it reaches) must be held; the members of a held read selection are read with it |
| `store._refs(row)` (2 sites, `records/<axis>/episode_receipts.py`) | `reader.named_references(row['id'])` | the references the held record names, in the Store's order. (The `episode_receipts.py` ledgers themselves are deleted: that is custody) |
| `store._literature_sheet_updating` read with `getattr` and set and cleared around the work (30 sites in 5 files, `literature/storage/<axis>/literature_sheet_updates.py`: `publication` and `admitted`) | `with store.section('literature_sheet_updating') as outer:` in place of the `getattr`, the two assignments and the `try/finally` | `outer` is `True` for the outermost entry of the named section in this Episode's unit and `False` for a call made inside it; the state is the Episode's, lasts for the call, and is released by an error too (`operations_library.update_sheet`) |
| `DELETE FROM provider_job_failures WHERE job_ref=?` (5 sites, `jobs/service_calls/<axis>/provider_jobs.py`) | `store.table(FAILURES).withdraw({'job': job})` (the declared key columns and their values) | the row stays, marked: its next revision with the system column `withdrawn` true, held as produced by the unit. `select` leaves withdrawn rows out (`select(where, withdrawn=True)` returns them too), `get(row_ref)` returns the row with its mark, `put` with the same key makes it live again. Only a row this Episode wrote can be withdrawn. A withdrawal by a unit that did not finish is taken back on resume like any row write |
| `scope_measure`, `iter_scope_coverage`, `read_subject_ref`, `context_mask_measure`, `context_mask_target_full`, `context_mask_dimension_segments` (no library call today; the Store's ownership rule uses the first and the third) | the same names on `reader` | every subject and read selection the scope or mask names must be held; `read_subject_ref` requires the library held |
| `context_mask_target_query(mask, target_ref)` (returns SQL for the caller to run; no library call today) | `reader.context_mask_positions(mask, target_ref, limit=None, offset=0)` | the rows of that query (`target_ref`, `member_ref`, `dimension_ref`, `read_ref`, `length`, `unit`, `start`, `end`), ordered by member, unit, start, end. The SQL is not handed out |
| a work-table query other than equality: `ORDER BY rowid`, `ORDER BY ... DESC`, `IN (...)`, `count(*)`, a `LEFT JOIN` of two tables on their shared key (`literature_sheet_updates.py`), a list column that contains a reference | `reader.table(T).select(where)` and Python on the rows: `reversed(rows)`, `sorted(rows, key=...)`, `[row for row in rows if row['state'] in states]`, `len(rows)`, a dictionary of one table's rows by key | no wider query was needed. `select` returns the held rows in receipt order (for the writer: the order of first write, which is what `ORDER BY rowid` gave) and is one query of the system table however many rows are held. A row another Episode wrote (`WHERE episode_id=<owner>`) is read by `select({'episode_id': owner})` once it is held: the owner returns it in a `record_refs` field. There is no query over rows the Episode does not hold |
| `libraries.member_page(store, library_ref, scope=scope, selection_ref=..., offset=..., limit=...)` (the nine deleted copies of `records/<axis>/library_targets.py`; called by `tools/<axis>/tools.py` for `library.members`, six axes) | `reader.library_members(library_ref, *, selection_ref=None, offset=0, limit=50, scope=None)` | stage 1c. The Store's own page (`gene_annotation_episode/library_targets.py`, the one copy): `{'library_ref', 'selection_ref', 'members', 'total', 'offset', 'limit', 'next_offset', 'next_query'}`, each member the read subject in its model view, in the library's order; `scope=None` is the whole library. Held: the library, **every collection it binds** (`collection_refs`: the reads are rows of those collections), the scope's subjects and read selections, and `selection_ref`; else `CustodyError`. A member's `id` is a name: `get` of a read subject still needs that reference held. A read is read without holding it through this page (its record) and `reader.material_member(member['member_ref'])` (its sequence, through the held collection): `operations_library.read_page`, `selected_fasta` |
| `libraries.select(store, library_ref, scope=scope, member_refs=... \| ordinal_ranges=...)` (same files; `library.select`): a `read_selection` record and its rows in `library_selection_members` | `store.select_library_members(library_ref, *, member_refs=None, ordinal_ranges=None, scope=None)` | stage 1c. The Store's own `select` in one receipted transaction; returns the `read_selection` record, which the Episode holds as produced at the unit (in `with store.transaction():` receipted on commit; rolled back, neither the record nor its rows remain). Held: the library, every collection it binds, the scope's subjects and read selections, every member named (itself or its collection). The Store's refusals are unchanged (`selected_member_outside_assigned_scope`, `choose_original_members_or_ordinal_ranges`, ...) (`operations_library.freeze_reads`) |
| `SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref` (5 sites, `tools/<axis>/tools.py`: the `queries.fasta` of a read mapping) | `reader.selection_members(selection_ref, limit=None, offset=0)` | stage 1c. The references of the reads the held `read_selection` froze, ordered by reference (all, or a page). Only the selection must be held; a reference that is not a read selection is the Store's `wrong_reference_type`. The references are names (as with `read_subject_ref`): `store.get(read_ref)` raises `CustodyError` unless that read subject is held, so a function that needs each read's record and sequence takes them from `library_members(library_ref, selection_ref=...)` and `material_member` (`operations_library.selected_reads`, `selected_fasta`) |
| `SELECT 1 FROM tool_operations WHERE ... json_extract(result,'$.feedback.diagnostic_ref')=?` (`records/sequence_and_context_sources/genomic_source_receipts.py`, `source_reference_restriction`; the operation ledger is deleted) | `reader.is_diagnostic_ref(ref)` | stage 1c. Whether the value a tool unit **of this Episode** returned names the held record `ref` under a key `diagnostic_ref`, at any depth (`feedback.diagnostic_ref` and deeper). Known for every recorded unit (again after a resume) and for the unit being completed from the moment its tool returned, so `credit` of that unit sees it; the tool that is still running has no outcome yet. `ref` must be held (`CustodyError`); another Episode's diagnostic, passed or returned, is not one of this Episode's (`operations_library.may_be_read_as_a_source`) |

### Not Store operations (the library's own, stage 2)

| Old | What it becomes |
|---|---|
| `store._unit`, `_merge_segments`, `_covered_by` (static, read nothing) | pure functions in a library module |
| the nine copies of the Store's material implementation under `records/documents/*/` (with their `material_name_counts` deletes and their temporary files) | one copy, with the Store (`gene_annotation_episode/materials.py`); episodes call `store.register_material`, `parse_material`, `material_*`, `caller_source`, `artifact_file` |
| `DELETE FROM fv_pending` in the `findings/<axis>/finding_validity.py` copies | no change of kind: `fv_*` are tables of a private temporary SQLite database the function opens itself (`sqlite3.connect('')`), not tables of the Store; only its reads of the Store change (`reader.current_assessments`, `reader.assessment_write_extent`) |

### No replacement yet

None. A pattern that is in none of the tables above is reported as a blocker with its call site; it is not
worked around with a service or an import of the Store.

## 3. Carrying one function family over

1. Give every function that took the `Store` the scoped store instead (same parameter name `store`), and every
   function used by `credit`, `action`, `read_from_child` or `internal_summary` the reader.
2. Replace each call by the table above. Calls with the same name need no change.
3. Declare each of the family's own tables as a `TableDeclaration`; choose the key columns the family used to find
   "its" row; list the columns that hold record references in `record_refs`. Delete the `CREATE TABLE`, the
   `sqlite_master` checks, the run, episode and operation-key columns, the `*_operations` and `*_received` tables.
4. A row or record another Episode must read is returned or passed by reference in a `record_refs` field.
5. A temporary file is a file of a scratch directory; a file kept as an artifact is `store.artifact_file`; a
   table creation with its commit is deleted; a delete is a withdrawal; a cache is the `work_cache` service
   (table "System operations built in stage 1").
6. A pattern that is in none of the tables stops the family's carry-over: report it as a blocker with its call
   site; do not work around it with a service or an import of the Store.

## 4. `native_execution` records

The Store no longer has the record kind `native_execution` (it was removed from `gene_annotation_episode/state.py`
on 18 November). Eight library modules still write it and read it back; each call fails with the Store's
`unknown_record_type` (the write) or `wrong_reference_type` (the read) when its family is carried over.

| Site (under `episode_support/jobs/local_execution/`) | Write | Read |
|---|---|---|
| `biochemical_feasibility_evidence/native_timing_information.py` | `record_native_measurement`, line 14 | `read_measurement`, line 20 |
| `sample_context_evidence/native_timing_information.py` | line 18 | line 24 |
| `gene_context_evidence/native_timing_information.py` | line 20 | line 46 |
| `structural_homology_evidence/native_timing_information.py` | line 23 | line 49 |
| `sequence_homology_evidence/native_timing_information.py` | line 25 | line 51 |
| `partner_presence_evidence/native_timing_information.py` | line 25 | line 51 |
| `perturbation_evidence/native_timing_information.py` | line 25 | line 51 |
| `evolutionary_history_evidence/native_timing_information.py` | line 25 | line 51 |

Six of the eight also declare the form format `'x-reference-namespace': 'native_execution'` for a `receipt_ref`
field, and `tools/experimental_activity_evidence/tools.py:535` tests `row.get('record_type') == 'native_execution'`.

What the record was: the host's receipt of one native measurement the Episode's own tool made
(`{'representation': 'native_execution_receipt_v2', 'operation', 'measurement_artifact_ref', 'operands'}`, with
the measurement itself in an artifact).

| Old | Replacement |
|---|---|
| `store.put('native_execution', {...}, origin='tool')` inside `with store.transaction():` after `store.artifact(measurement)` | a declared work table of the module, for example `NATIVE_MEASUREMENTS = TableDeclaration(name='native_measurements', columns=('operation', 'operands', 'measurement_artifact_ref'), key=('measurement_artifact_ref',), record_refs=('measurement_artifact_ref',))`; the tool writes `store.artifact(...)` and `store.table(NATIVE_MEASUREMENTS).put({...})` in one `with store.transaction():`. The row reference (`row_...`) takes the place of the record reference. The system fills run, Episode, unit and operation key, so the receipt says which unit measured |
| `store._require(reference, {'native_execution'})`, then `store.get_artifact(record['measurement_artifact_ref'])` | `reader.table(NATIVE_MEASUREMENTS).get(row_ref)`, then `reader.get_artifact(row['measurement_artifact_ref'])`; both need the row and the artifact held, so a child returns both in `record_refs` fields |
| the form format `'x-reference-namespace': 'native_execution'` | a `record_refs` field of the episode's `RETURN_FORM` that carries the row reference |
| a measurement a **detached** local job publishes from its own process | the native event ledger, not the Store: the job calls `publish_native_event(handle, publication, receipt_bytes=...)`; the tool that waits for it writes the receipt bytes with `store.artifact` and the row above |

A native measurement is provenance of a tool run. It is never a controller input (the system builds every
controller input itself) and it earns credit only through the episode's own `credit.py`.
