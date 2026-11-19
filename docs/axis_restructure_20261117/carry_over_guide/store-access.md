# Store access in the library: from raw Store calls to custody (19 November 2026)

The owner's rule: library functions never write to the Store or its tables directly. Anything they read or write
goes through custody: the scoped store the system hands the episode (`ctx.store` in a tool; the read-only
`records` in `credit`, `action`, `read_from_child`, `internal_summary`, which has every read of `ctx.store` and
no write), or an operation of it that has custody built in. A library function receives that object as its `store` (or `reader`) argument and calls only what it
offers. It never receives the `Store`, its connection (`store.db`) or its directory (`store.path`).

This page is the mapping for the carry-over, per function family. It does not rewrite the library. The API it
maps to is in `BINDING_CONTRACT.md` ("The Store under custody"); the code is `episode_runtime/store_scope.py` and
`episode_runtime/work_tables.py`; the worked example is `episode_runtime/tests/sheet_library.py` with the `probe`
test episode. `episode_runtime/tests/test_library_boundary.py` fails while a library function module imports the
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
| `store.list`, `count`, `subjects`, `references`, `targets`, `current_assessments`, `current_annotations`, `iter_current_annotations`, `iter_current_accounts`, `current_assessment_subset` | the same | inventories of **held** records only. `list(kind, scope=None, limit=None, offset=0)` returns every held record unless a `limit` is given (the Store's own `list` stops at 100) |
| `store.record_coverage(row)`, `store.scope_coverage(scope)`, `store.scope_dimension_segments(scope, ref)` | the same | the record `row['id']` (read again from the Store; the rest of `row` is not used), or the scope's subjects, must be held. For an assessment its hypothesis, and for a hypothesis or an observation every subject it names, must be held too |
| "is this assessment still current" by a query on `current_revisions` | `reader.is_current(ref)` | the record must be held |
| `store.register_material(...)` | the same | a `source_ref` must be held; the Episode holds the material and the records it names |
| `store.problem()["subject_refs"]` | the same (or `store.targets()`) | only the subjects the Episode holds |

### Renamed or reshaped

| Old | Now |
|---|---|
| `store._require(ref, kinds, field_path=...)` | `store.require(ref, kinds, field_path=...)` |
| `store._in_scope(ref, store.validate_scope(scope))` | `store.in_scope(ref, scope)` |
| `store.path / "artifacts" / sha[:2] / sha` (to read an artifact's file) | `reader.open_artifact(ref)`: a read-only binary file object of the held artifact. There is no path. A function that must give a file name to an external program copies the bytes into a scratch directory (not built yet, below) |
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

### No replacement yet (to be built next)

| Old | Why it has none | What would replace it |
|---|---|---|
| temporary files and directories under `store.path` (about 50 sites) | the directory is not offered | a scratch directory operation of the scoped store |
| streaming a download into the artifact directory with a raw `INSERT INTO artifacts` (14 sites in 14 files: `readers/<axis>/source_bytes.py` and the nine `records/documents/*/materials.py` copies) | it writes an artifact outside custody | a receipted "artifact from a file" write: one scoped-store write over the Store's own `materials.artifact_file`. Until then `store.artifact(bytes)` works for content that fits in memory (papers do) |
| `store.path / "cache" / ...` (4 sites) | not a record | a service |
| `store.db.commit()` (14 sites) | a library function may not commit the unit's transaction | restructure around `with store.transaction():` |
| a lookup in `records` that must find a record the Episode does not hold (for example "was this source already fetched or parsed by anyone") | custody hides it | writing the same content again returns the same reference and is held as produced; a cross-Episode cache of work is otherwise a service |
| `store._caller_source`, `_assessment_write_extent`, `_record_roots`, `_assert_library_write_scope`, `_refs` | private Store helpers without a custody-limited form | one operation each, when its family is carried over (`_assessment_write_extent`, `_record_roots` and `_assert_library_write_scope` block literature storage, credit and findings) |
| `store._literature_sheet_updating = True` (5 files) | not a Store helper: a flag the literature library sets on the Store object it was handed; the scoped store takes no attribute | the library keeps the state in its own call, or asks `store.in_transaction()` |
| deleting a row of a library table (`DELETE FROM` in the `findings/<axis>/finding_validity.py` copies and in `service_calls` copies) | a work-table row is rewritten, never deleted | a column that marks the row withdrawn, written as the next revision |
| `store._unit`, `_merge_segments`, `_covered_by` (static, read nothing) | not Store operations | pure functions in a library module |
| `scope_measure`, `context_mask_measure`, `context_mask_target_full`, `context_mask_target_query`, `context_mask_dimension_segments`, `read_subject_ref`, `iter_scope_coverage` | no custody-limited form yet (no library use counted) | as needed |
| `Store(store_path)` opened in a worker thread (`protein_structure_tools.py`) | a second connection is outside custody | no Store in the worker: the tool reads the inputs through `ctx.store` (`open_artifact`), the thread computes on files of its own, the tool writes the results. This is a rewrite of `prepare_protein_structure_worker`, not a missing system operation |
| the nine copies of the Store's material implementation under `records/documents/*/` | they are the Store's implementation, written against the raw Store | one copy, with the Store (`gene_annotation_episode/materials.py`); episodes call `store.register_material`, `parse_material`, `material_*` |
| a work-table query other than equality on columns, or over rows the Episode does not hold | `select` filters held rows by equality | filter the selected rows in Python; anything wider is a new operation |

## 3. Carrying one function family over

1. Give every function that took the `Store` the scoped store instead (same parameter name `store`), and every
   function used by `credit`, `action`, `read_from_child` or `internal_summary` the reader.
2. Replace each call by the table above. Calls with the same name need no change.
3. Declare each of the family's own tables as a `TableDeclaration`; choose the key columns the family used to find
   "its" row; list the columns that hold record references in `record_refs`. Delete the `CREATE TABLE`, the
   `sqlite_master` checks, the run, episode and operation-key columns, the `*_operations` and `*_received` tables.
4. A row or record another Episode must read is returned or passed by reference in a `record_refs` field.
5. Anything in the "no replacement yet" table stops the family's carry-over until that operation exists; do not
   work around it with a service or an import of the Store.

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
