# Second audit of the system episode type and generic runner (19 November 2026)

Second, independent pass over `episode_runtime/`, `method_loop/`, their tests, `BINDING_CONTRACT.md` and the
carry-over guides, after another agent fixed the findings of `AUDIT_SYSTEM_EPISODE_TYPE.md`. The fix agent's
report was treated as a set of claims. No code, test or other document was changed; nothing was committed.

## Verdict

**Not yet sound to build 202 episodes on. Much closer than at the first audit.**

What now holds up under my own probes: the tool context and services channel, `parent_input` in the yield
estimator, record reading in credit and child receipt, slot and arguments in child outcomes, exact restore of
the view on resume, the began/finished journal with a stable operation key, closed-run resume, the selection
handshake in the plain case, and an episode that commissions its own kind three levels deep with an
interruption at the bottom.

What still stands between this and the carry-over:

1. **The custody-scoped Store covers Store methods, but the support library does not use the Store through
   methods.** 253 non-test library files run SQL on `store.db` (1,604 call sites; 122 of the files are
   literature storage). `ctx.store` has no `db`. Literature episodes cannot be written until the owner decides
   how that library reaches its tables (N1).
2. **Three decisions that change a signature or what every `task.py` contains are still open**: what `decide` and
   `action` may see besides the summary (run configuration, thresholds, a clock: N6); what happens to units that
   gain nothing, including the root's wait (N10, measured below); and the launch/monitor/extract document, which
   still describes the removed design (B6).
3. **Four defects in the fixes** should be repaired first: receipts survive a rolled-back transaction (N2), the
   account owner the system gives the Store is not unique (N3), a refused commission or link leaves records and
   can make a run permanently unresumable (N4), and a rerun cannot see what its abandoned attempt wrote (N9).

No real episode is in the new form yet: `grep 'class .*(EpisodeBinding)'` under `gene_annotation_episode/` finds
0. Everything below was shown on the three test episodes.

## How this was checked

- Read in full: every file of `episode_runtime/` (including `store_scope.py`, `services.py`), `method_loop/episode.py`,
  `forms.py`, `jsonvalue.py`, `communication.py`, `runtime.py`, `suspension.py`, `LOCAL_PATCHES.json`,
  `SOURCE.json`; the outline of `durable.py` and the head of `durable_worker.py`; every test file and test episode
  under `episode_runtime/tests/`; `BINDING_CONTRACT.md`, `carry_over_guide/system_recording.md`, the headers of the
  other four guides, the summary and searched lines of `LAUNCH_MONITOR_EXTRACT_MECHANICS.md`; the `put`,
  `query_records`, `reasoning_view`, `reference_subset` and `commit_reasoning` bodies of `gene_annotation_episode/state.py`.
- Ran the system's tests: `runs/aud2_sys_01`, **98 passed, 1 deselected** (`model_run`), 34 s. The fix agent's
  count is confirmed. I did not run `model_run`; its claim (passed, 51 s) is unverified.
- Hashed every `method_loop/*.py`: all 12 match `LOCAL_PATCHES.json`.
- Ran 12 throwaway probes with the real runner, journal, Store and `yield_control`; the model was never called.
  Files: `runs/aud2_probes/test_aud2_probe.py` (run `runs/aud2_probe_01`, 9 passed) and
  `runs/aud2_probes/test_aud2_probe_b.py` (run `runs/aud2_probe_02`, 3 passed). Lines beginning `PROBE` in each
  run's `stdout.log` are the evidence quoted below by probe id (A1..F3).
- Counted Store uses in `episode_support/` with `grep` (non-test files only: 2,546 files).
- Old episodes: a delegated reader read seven episode folders of the a102 tree at `97308b94c`
  (`git show` only, inside `root/a102/structural_homology_evidence/**`, never the shared root). Paths in
  section 7 are relative to that folder. **Limit:** credit and estimator internals of the head, literature and
  monitor episodes are in modules outside the tree and were not read; such answers are marked "not determinable".
  The reader read some files by grep or diff only (`closed_credit.py`, `decision_contracts.py`, most HPC
  `allocation_*`/`portfolio_*` bodies) and did not read `*_presentation.py`, `scientific_contracts.py` or tests.

## 1. The seven blockers

| | Status | Evidence | What remains |
|---|---|---|---|
| B1 tool channel | **Fixed in form; one large gap** | `tool(arguments, ctx)`, `UnitContext` (`recording.py:245-254`); `services` member and link check (`episode_type.py:256-259`, `runner.py:88-91`); a tool sees only declared services, each built once (their test; `services.py:19-39`); `ToolRecords` has no admission call and forwards no options (A5: `put(..., account_owner=)` raises `TypeError`) | The scoped Store does not cover what the library does (N1). Custody is by convention only (N8). Model calls inside a tool are unrecorded (N7) |
| B2 `yield_controller` | **Fixed** | `yield_controller(initial_credit, settings, parent_input)` (`episode_type.py:329-336`). D1: a `CompletionYieldController` and a `BoundedQualityYieldController` whose target comes from `parent_input` stop a 5-step plan after 2 units (`yield_stop`, credits `[1.0, 2.0]`), and the closed run resumes to the same end | No test episode uses `parent_input` or a non-accumulation controller in a run. Old estimators that needed a per-unit proof or packet have no channel (section 7) |
| B3 record content in credit and receipt | **Fixed for Store records and artifacts** | `credit(summary, records)`, `action(..., records)`, `read_from_child(..., records)`, `view.records` (`episode_type.py:326-327, 401, 455, 331-334`). D2: credit read the artifact its own unit produced and the one its child returned (credits `[18.0, 144.0]`) | `RecordReader` offers `read` and `read_artifact` only: no "is this the current revision", no scope question, nothing in library tables. The literature sheet is a row in a library table, not a Store record (N1), so "no credit before the sheet exists" still rests on a tool outcome |
| B4 slot and arguments | **Fixed** | Outcome is `{kind, slot, arguments, message, completion, result, report}` (`episode_type.py:440-457`); their test and F1 | The outcome now holds the whole assignment, result and report (N13) |
| B5 view on resume | **Fixed** | `EpisodeUpdate.from_record` (`method_loop/episode.py:486-499`), `_restore_units` (`:1204-1217`), `units.episode_update` (`journal.py:40-42`). Their test compares an uninterrupted and a resumed run; F1 resumes three levels deep and a second resume of the closed run returns the same result | `updates` and `outcomes[*].report` are kept as two sources of the same report |
| B6 launch/monitor/extract | **Partly** | The contract has a table of what the design needs (`BINDING_CONTRACT.md:263-278`): six rows provided, four "Not provided" | The mechanics document itself was not re-issued. It still says "Nothing in this document is built", "`episode_runtime` does not change" (summary 5), collaborators given to every binding (`:406-407, 468`), `bound.recorder` (`:470`), "reads its outstanding jobs from the Store" (`:65, 86, 484`), "waits in the process" (`:752`). The root's wait is undecided and measurably harmful as a unit (N10) |
| B7 interrupted side effects | **Fixed as far as a journal can; one new problem** | `attempts` table (`journal.py:43-45, 147-160`); begun before a tool runs (`episode_type.py:423`) and before a child is commissioned (`:445`). B1: rerun has `resumed=True` and the same key. B2: an interruption inside a child gives the child's tool `resumed=True` with the same key, parent attempt `began` → `finished`. B3: an interruption between the child's close and the parent's unit does not run the child's tool again (1 execution). B4: a really changed unit raises `abandoned_unit_differs` | The rerun cannot see what the abandoned attempt wrote, and the journal row is deleted (N9) |

## 2. The other first-audit findings

| | Status |
|---|---|
| S1 class checks | Fixed for the six holes listed. Nine further ways round remain (N11) |
| S2 forgeable custody | Admission calls and `**options` are off the tool's objects. "Record `produced` only when the Store created the record" was not done; the contract now documents the weaker meaning (A2, N8) |
| S3 journal | Settings journaled and compared (their test). Parent-input digest journaled at controller build (`runner.py:118`). Run failure recorded, but only from `run()` (C3: failure `None`). Custody passes before `open_episode` (`runner.py:279-286`). Still absent: the controller's step and estimate per unit, `end_reason`, times on rows other than progress receipts |
| S4 rejections | Not done (admitted). See N6 and section 7 |
| S5 declaration | Stated as a description; built at every controller build and discarded (`runner.py:117`). Stopping text follows the controller kind |
| S6 `read_from_child` twice | Fixed (one `project` callback, `episode_type.py:453-458`) |
| S7 patch manifest | Fixed: all 12 hashes match; listed test files exist |
| S8 episode type in the vendored library | Fixed: moved to `episode_runtime/episode_type.py`; `SOURCE.json` scope amended. `durable.py` with its own SQLite ledger is still in `method_loop` (section 4) |
| S9 fallback and optional hooks | Fixed (`method_loop/episode.py:1219-1230`; no `getattr(source, ..., None)` left) |
| S10 import cycle | Not done (`yield_control/__init__.py:30`; function-level imports at `runner.py:97`, `episode_type.py:359`) |
| S11 tests | Much improved (section 6) |
| M1 duplicates | One `jsonvalue.py`. New duplicate: N12 |
| M2, M3, M4 | Fixed (`compose`, `start_run`, `report_form` gone; table renamed `progress_points`) |
| M5 memory, M8 quadratic summary, M9 stale controller state | Not done |
| M7 old recorder calls | Not done: 54 call sites in 18 non-test files of `episode_support/` |

## 3. New findings

Severity: **blocks** = a whole episode kind cannot be written, or the answer changes a signature in every
episode; **fix first** = a defect or gap that would be copied into many episodes; **minor**.

### N1. The scoped Store does not cover how the support library uses the Store (blocks)

Evidence.
- Non-test files of `episode_support/` call, on a `store` object: `.db` **1,604** times in **253** files
  (122 under `literature/storage`, 19 `jobs/service_calls`, 18 `records/documents`, 5 `literature/grading`,
  5 `jobs/hpc`), `._require` 376, `.path` 130, `._unit` 45, `._caller_source` 27, `._literature_sheet_updating` 20,
  `._assessment_write_extent` 20, `._in_scope` 14, `.record_coverage` 12, `.problem` 22, `.register_material` 24,
  `.register_native_target` 9, `.publish_native_event` 9, `.current_assessments` 7.
- A5: on `ctx.store`, `hasattr` is `False` for `db`, `path`, `_require`, `_unit`, `_in_scope`, `list`, `count`,
  `problem`, `targets`, `references`, `subjects`, `current_assessments`, `current_assessment_subset`,
  `register_material`, `register_native_target`, `publish_native_event`, `record_coverage`, `scope_coverage`.
- The contract's list of what is not offered (`BINDING_CONTRACT.md:122-127`) and the fix agent's list name the
  public enumerations and "the underscore-prefixed methods". Neither names `db` or `path`, the two largest.
- Literature storage keeps its own tables in the Store's SQLite file (`CREATE TABLE IF NOT EXISTS` in
  `literature/storage/*.py`), keyed by `(run_id, episode_id, operation_key)` with its own "already done" lookup
  (`literature_subscore_storage.py:334-348`). That is a second replay device, in the library. Literature credit
  reads the same tables (`literature/grading/literature_task_credit.py` uses `store.db`).

Consequence. A carried-over literature tool that calls the library with `ctx.store` fails with `AttributeError`.
The path of least resistance is to register the raw Store as a service, which the system allows (`services` is any
factory) and which switches custody off for every tool that does it.

Suggested fix (owner decision, question 1). One of: (a) the library's tables become Store records or artifacts,
so sheets are held, passed and read like anything else and credit can check a sheet through `records`; (b) the
facade grows one narrow, named door for library tables (the system owns the key columns and fills run, episode
and operation key itself); (c) accept a raw-Store service for named libraries and say in the contract that
custody does not cover them. Whichever is chosen, add `db` and `path` to the contract's list.

### N2. Receipts survive a rolled-back transaction (fix first)

Evidence. A3: a tool opens `ctx.store.transaction()`, writes an artifact and a `source` record, and the block
raises. The Store rolls both back. Afterwards `ctx.records.holds(ref)` is `True` for both,
`read` raises `ContractError: unknown_reference` / `unknown_artifact`, the journal has two `produced` receipts
for records that do not exist, and the unit's `produced` list names both. Cause: the receipt is written to the
journal at once (`recording.py:127-133`), outside the Store's transaction (`store_scope.py:174-177`).
`episode_support/` uses `store.transaction(` 421 times.

Suggested fix. The facade's `transaction()` collects the references produced inside it and receipts them only
when the block commits.

### N3. The account owner the system gives the Store is not unique (fix first)

Evidence (by reading; not run). `ScopedStore.commit_reasoning` passes `account_owner=self.__custody.path[-1]`
(`store_scope.py:169`), the pair (grain name, key) of the Episode's last path segment. A child's key is
`<slot>_<position>` (`episode_type.py:444`), so the same binding commissioned at the same position by two
different parent Episodes, or in two runs that share a Store, has the same owner. The Store derives the
interpretation-account key from that owner (`state.py:1593`), so the second Episode revises the first one's
account or gets `RevisionConflict`. The old episodes passed `(run_id, episode_id)`
(`task.py:222` of the a102 head at `97308b94c`).

Suggested fix. Pass `(run_id, episode_id)`.

### N4. A refused commission or link leaves records, and can make a run unresumable (fix first)

Evidence.
- C1: a commission whose selection names a field the child does not offer raises `FormError`. The parent's
  attempt row is already journaled `began` (`episode_type.py:445` runs before the builder at `:449`), and the run
  stays `active`. `resume` raises the same `FormError`. When the selection, or a record reference, came from a
  model response, that response is replayed, so the run can never get past the unit without a code change.
- C2: an entry with a bad selection raises `FormError` and the run id is used up (`run_state` = `active`).
- C3: an entry assignment naming a record that does not exist raises `ContractError`; the run id is used up, no
  failure is recorded, and linking again with the same id raises `run_already_recorded`.
- The contract says "the commission is refused before anything is recorded" (`BINDING_CONTRACT.md:168`) and "a
  refused link does not use up the run id" (`:181`). Both are false for these cases: `open_run` (`runner.py:375`)
  precedes the entry build (`:314`), where selection, custody and `read_from_parent` are checked.

Suggested fix. Build and admit the commission (assignment form, selection, custody) before `attempts.begin`, and
for a model-derived commission hand the refusal to `decide` as feedback, like `Rejected`. Check the entry's
selection, record existence and `read_from_parent` in `_prepare`.

### N5. A parent cannot know which fields its child offers (fix first)

Evidence. The selection is built in `msg_to_child` from the model's arguments. The selectable names live in the
child's `final_to_parent.py`, which the parent may not import. Nothing gives them to `action`, `msg_to_child` or
the summary, and nothing checks at link time that the names a parent can select exist. So every parent copies
its children's field names by hand, and a mismatch appears only at run time, as N4.

Suggested fix. Either the parent declares per slot the names it may select and `link` checks them against the
child's form, or the system passes each slot's selectable names to `action`.

### N6. `decide` and `action` see nothing of the run but the summary (blocks: decide before the carry-over)

Evidence.
- Services reach tools only. `settings` reach `yield_controller` only. No function sees a clock.
- In all seven old kinds the decision context held things that are none of own outcomes, assignment or held
  records: the configured tools and resources, `time_accounting`, `execution_expectations`,
  `resource_tool_estimates`, the controller's yield table, shared information (`task.py:90`,
  `decision_delivery.py:42-87, 268` of the head; the same files in the other six).
- `GOAL.md`: "code refuses unworthy ones ... using data from this and past runs". The refusal belongs in
  `action(response, summary, records)`, which can read neither thresholds nor past-run data.
- The old planner refused by the clock (`hpc_work_planning/queue_observations.py:26-27`). A pure `action` cannot.
- `Done()` carries nothing, and the summary cannot see model responses. Every old response carried a
  `report_update` kept for the final report (`task.py:194-196`). A model-written closing value now needs a tool
  unit whose arguments are the value.

Workarounds exist (a parent forwards configuration in its message; a tool unit fetches a table and the summary
carries it; a "report" tool), and each adds units that gain nothing (N10) or a forwarding rule every level must
follow. If the owner instead wants `action` to receive settings or a read-only configuration, that is a
signature change in 202 `task.py` files, so it should be settled now (question 2).

### N7. A model call made inside a tool is not recorded (fix first)

Evidence. `UnitContext` has no model (`recording.py:245-254`); `RecordedModel` serves `decide` only
(`episode_type.py:398`). A tool that needs the model must get a provider as a service, and that call is in no
journal table. The old head ran lookups that executed work inside a decision (`decision_delivery.py:329`).

Suggested fix. Give tools `ctx.model`, the same `RecordedModel`, keyed by unit and call index.

### N8. Custody holds only if tools keep to the documented names (minor; owner may want it hard)

Evidence.
- A1: `ctx.store._ScopedStore__store` is the raw Store; `ctx.records._RecordReader__custody.admit_entry([ref])`
  writes a forged `entry` receipt, after which the unheld record reads normally; the journal object is reachable
  the same way. The contract's sentence "tools get `ToolRecords` and `ctx.store`, which have none" is true of
  the public names only.
- A2: a tool that writes the same bytes as a record it does not hold then holds it, with a `produced` receipt
  naming itself as producer (`recording.py:115-125`; `Store.put` returns an existing row, `state.py:1633, 1655`).
  It can then return it to its parent as its own product.
- A4: with an input it does not hold, `get_input`, `get` and `subject_length` are refused, but
  `ctx.store.reasoning_view(scope)` returns the input's record view (length, molecule, `sequence_ref`,
  `source_record`) because subjects are read from the scope (`state.py:1790`); `scope_dimension_segments` returns
  its extent; `validate_scope` accepts it.
- Services are shared objects (`services.py:13-23`): two episodes that declare one service can pass anything
  through it, outside custody and outside the journal.

Suggested fix. Receipt `produced` only when the Store created the row. Require every `subject_refs` of a scope
argument to be held. If the owner wants custody enforced rather than agreed, hold the Store and custody in
closures instead of attributes.

### N9. A rerun cannot see what its abandoned attempt wrote (fix first)

Evidence. B1: on the rerun, the marker the first attempt wrote is not held (`marker held before the rerun wrote
it: False`) although the Store still has it. `begin_attempt` deletes the abandoned receipts
(`recording.py:139-145`, `journal.py:264-271`).
- The Store therefore cannot serve as a tool's intent log. The old job leaf did exactly that with
  `state.begin(operation_key)` / `state.finish(...)` and returned the saved receipt when the intent was complete
  (`execution_job_submission/hpc_job_execution/terminal_operations.py:25-42`).
- For a revisioned kind the abandoned write is the current revision, and the rerun may not read it. The contract
  says the tool "handles" the `RevisionConflict` "with `ctx.resumed`" (`BINDING_CONTRACT.md:252-253`) but gives
  it no way to.
- The `DELETE` removes trace: after the rerun the journal no longer shows that the abandoned attempt wrote
  anything.

Suggested fix. Keep the abandoned receipts, marked abandoned, and give the rerun their references
(`ctx.abandoned`, readable). `commit_reasoning` is already idempotent on its operation key
(`state.py:1842`); say so in the contract and tell tools to pass `ctx.operation_key`.

### N10. Units that gain nothing end the Episode (blocks: decide before the carry-over)

Evidence. F3, an accumulation controller, 30-step plan:

| Units that gain credit first | Cost 0 | Cost 0.01 | Cost 0.5 |
|---|---|---|---|
| 0 | runs all 30 | `yield_stop` after 15 | `yield_stop` after 2 |
| 3 | runs all 30 | `yield_stop` after 10 | `yield_stop` after 6 |

Under the present API these are all units with no gain: the root's wait until a check time (the contract's own
"Not provided" row), every information lookup that used to be an exchange inside one decision, a model-written
report (N6), writing a child's returned cells into the parent's sheet (`read_from_child` is read-only), a
monitor check that finds "still running". `GOAL.md` says information is gathered through tool calls, so lookups
as units are intended; their effect on the yield history is not addressed anywhere.

Suggested fix (question 3). Decide whether the system gets a unit that the controller does not observe (a wait,
a lookup), or whether each episode's credit must be written so that such units gain something.

### N11. Class-definition checks: what still gets through (minor)

| Probe | Accepted |
|---|---|
| E1 | A second class in the same `episode.py` with the same members and another `binding_path` |
| E2 | A metaclass |
| E3b | Another episode's function with `__module__` set to this episode's file (the repo's own test builds its variants this way) |
| E5 | `async def decide`, a generator `internal_summary` (they fail at the first run instead) |
| E8 | A tool taken from another episode's `task.py` (admitted limit) |
| E9 | A `binding_path` unrelated to the package |
| E10 | A closure built by a factory, with state captured |
| E13 | Instance attributes replacing members after construction (`binding.tools = {...}`); the registry accepts the instance |
| E14 | Adding to the `tools` mapping after the class check |

Refused, as claimed: any dunder including `__slots__` and annotations (E6, E7), a borrowed function (E3a), class
keywords (E11), a module not named `<pkg>.episode` (E12).

The class check cannot see imports. `root/tests/test_private_bindings.py` is the right place for E1, E9 and
"imports nothing from another episode"; it reads the axis trees with `ast`. Cheap additions to the class check:
refuse coroutine and generator functions, require `type(cls) is type`, freeze `tools` and `child_slots`
(`MappingProxyType`), and have `BindingRegistry` refuse an instance with attributes of its own.

### N12. `ctx.records` and `ctx.store` offer the same four operations under two names (minor)

`read`/`get`, `read_artifact`/`get_artifact`, `put`/`put`, `write_artifact`/`artifact`
(`recording.py:198-217`, `store_scope.py:37-41, 160-164`). Two ways to do one thing in every tool. Keep one.

### N13. Outcomes are large and recopied (minor, not measured)

Each child outcome carries the whole `message` (assignment with every record reference), the child's `result` and
the `report`; the update repeats the report. `internal_summary` is recomputed over all outcomes at least twice
per unit and JSON-copied each time (`episode_type.py:323-324, 384, 391`). Each parent also keeps every closed
child's full record (`archive_record` is never set). A head that commissions literature many times will feel it.

### N14. Smaller gaps in the journal (minor)

No controller step or estimate per unit and no `end_reason`, so "why did it stop" needs the settings and a
replay. A refused link or resume records no failure (C3). Services, unlike settings, are not recorded, and a
service's state is rebuilt empty on resume; a cross-run table written from a tool is written twice by a rerun
unless the service is idempotent on `ctx.operation_key`.

## 4. Leftovers and duplicates

| Item | Needed by launch/monitor/extract? | Recommendation |
|---|---|---|
| `durable.py`, native-target half (`register_native_target`, `publish_native_event`, `validate_event_targets`, `wait_events`) | Yes: 21 library files import it (9 `records/local_execution`, 9 `jobs/local_execution`, 2 `jobs/similarity_search`, `jobs/waiting.py`). The design keeps a detached local job | It is job-support code with its own SQLite ledger; it belongs in `episode_support/jobs`, behind a service, not in the generic loop |
| `durable.py`, commission/return/receiver-claim half, and `durable_worker.py` | No. They run an Episode in a detached process. "No Episode stays open for the job" (mechanics, summary 1). Only `tests/test_durable_episode.py` uses them | Dead; delete with that test |
| `suspension.py` | No. Nothing binds a `SuspensionState` any more, so `external_wait(a, c)` is `await a`. Four library files call it (`jobs/waiting.py`, three `hpc_monitoring.py`); the mechanics document removes the caller's wait (`:277`) | Dead; delete and replace the calls with `await` |
| `archive.py` | Not by jobs. `ArchivedRecord` is a type in `episode.py`; `JsonArchive` is used only by `durable_worker.py`; the runner never sets `archive_record` | Dead until N13 is addressed |
| `yield_control` controllers: `transitioned(epoch)`, `requests_transition` in the step record (`:784, 862, 893, 927`) | No | Leftover of the removed goal revision |
| `bound.recorder` / `.recorded(` / `.recall(` in the library | No | 54 call sites, 18 non-test files (`jobs` 13, `acquisition` 3, `readers` 2), unchanged since the first audit |
| Two sources of a child's report (`view.updates`, `outcomes[*].report`); N12 | | Duplicates introduced or kept by the fixes |

Genericity: no role, axis id or episode rule appears in `method_loop/*.py` or `episode_runtime/*.py` (searched
for the axis ids and the role words). `store_scope.py` names about 45 methods of the application's Store and
knows the shape of a reasoning commit; that is application knowledge in the runner package, acceptable there,
but each Store change now has two places.

## 5. Documents against the code

| Document | Says | Code |
|---|---|---|
| `BINDING_CONTRACT.md:168` | a refused commission is refused "before anything is recorded" | the attempt is journaled (C1) |
| `BINDING_CONTRACT.md:181` | a refused link does not use up the run id | it does for a bad selection, an unknown record, a failing `read_from_parent` (C2, C3) |
| `BINDING_CONTRACT.md:122-127` | the list of what `ctx.store` does not offer | omits `db` and `path` (N1) |
| `BINDING_CONTRACT.md:252-253` | the tool handles a `RevisionConflict` with `ctx.resumed` | it cannot read the abandoned revision (N9) |
| `system_recording.md` F2 | `store.query_records(kind, scope, record_selection=...)` | `TypeError` on `ctx.store` (A5); the facade supplies the selection itself |
| `system_recording.md` F8 | `final_to_parent(summary, completion)` | three parameters |
| `store-tools-records.md` banner | episodes are `method_loop.EpisodeBinding` classes | `episode_runtime.EpisodeBinding` |
| `deciding.md`, `parent-and-children.md`, `progress-and-continuation.md`, body of `store-tools-records.md` | the hook API: `bound.recorder`, `Commission(request, assignment, report_form=None)` in `episode_runtime.forms`, `ChildBuilder.admit(result, report_form)`, home factories, `build_result` | none of it exists. Only one of the four has a "superseded" note. These guides are what a carry-over agent would follow |
| `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` | see B6 | |
| `README.md` global plan | P0-P5, "the hooks through which a binding supplies its episode" | the class contract |
| `episode_type.py:49, 305`, `method_loop/runtime.py:26-27` | `final_to_parent(..., completion)`; entry input `{'assignment', 'message'}`; "optional `observe_unit` port", "two structural booleans" | stale docstrings |

`LOCAL_PATCHES.json`: every hash matches and every listed test file exists.

## 6. Tests

Real: no stand-in for the runner, journal, Store, loop or controllers; the three test episodes are in the
ten-file layout; interruptions are real exceptions in real tools.

Weak or questionable:
- `test_a_model_named_record_that_is_not_held_is_rejected...` writes the "model's answers" into the journal with
  `journal.record_model_call` and lets replay return them. It exercises the real `Rejected` loop, but the
  responses are authored by the test. Under the owner's rule against scripted fakes this needs a decision; the
  same behaviour could be shown in the `model_run` test.
- `test_a_changed_unit_after_an_abandoned_attempt_is_refused` edits the journal with SQL. B4 shows a really
  changed unit is refused; the test should do that.
- `test_the_episode_files_hold_no_recording_or_custody_code` is still a word list.
- `test_class_definition.py` builds every variant by setting `__module__`, which is itself hole E3b.

Not covered by any kept test (each shown by a probe or absent): an episode that commissions its own kind (F1
works); a bounded or completion controller in a run, and any use of `parent_input` (D1 works); credit reading a
record (D2 works); a rolled-back transaction (A3, defect); `put` of a record rather than an artifact;
`commit_reasoning`, `query_records`, `reasoning_view`, `reference_subset` through the facade; units with no gain
(F3); N4's refusals after recording; nested forms with selection; any real episode, any real service, a real
job.

## 7. Can each old kind be written as a class with this API?

Facts are from the a102 tree at `97308b94c`. All seven kinds shared one decision machine (near-copies of
`task.py`, `decision_delivery.py`, `task_state.py`, `report_delivery.py`), so four needs are common to all:

- **Several exchanges per decision.** The model could answer `request_context` any number of times before
  `select_action`, and one lookup executed work inside the decision (`decision_delivery.py:275-339, 329`). Now:
  each lookup is a tool unit (N10), or a `Rejected` whose feedback replaces the previous one.
- **Context from outside the episode** (N6): time accounting, configured tools and resources, expectations.
- **A return form written by the parent**, with initial values, an attempts table and redelivery
  (`to_child_*.py`, `from_child_*.py`, `task.py:201-203`). Replaced by the selection handshake; initial values
  can ride in the message; redelivery is gone. Expressible, with N4 and N5.
- **Pending children and a `wait` action** (`child_commissioning.py:14`, `task.py:230`, `task_waiting.py:6-9`).
  Dropped by the launch design; the wait is N10.

Everything the old files read from `runtime_*` tables through `store.db` (10 to 19 call sites per episode) was
old-runner machinery and is replaced by the view; it is not counted as a lack.

| Kind | Writable now? | What the API still lacks for it |
|---|---|---|
| **Head** (`structural_homology_evidence`): eight child roles, itself among them | **Yes in shape; with losses the owner must accept.** Self-commissioning works (F1). `reason` becomes a tool calling `ctx.store.commit_reasoning(payload, scope, ctx.operation_key)` | N3 before any reasoning commit. N6 (tool catalogue, resources and expectations in the prompt). The summary read received literature through a repository over the raw Store (`received_structural_context.py:15-16`): N1. Credit is `services.scientific_credit` with an outside projector: not determinable; if it queries the Store by scope, `RecordReader` cannot |
| **Literature** (`published_evidence_assessment`) | **No, until N1 is decided** | Its tools, its credit (`LiteratureTaskCredit`) and its check of a child's form against saved answers and sheet rows (`received_evidence.py:43-73`) all go through repositories over `store.db`. Returned cells were written on receipt (`received_evidence.py:26-35`); `read_from_child` is read-only, so that becomes a tool unit (N10) or the child's job. The yield settings it copied into the assignment (`from_parent.py:59-65`) fit `parent_input` exactly. Interpretation, grader choice and sheet in one action fit one tool unit, provided grading needs no model call (not determinable; else N7) |
| **Job submission** (`execution_job_submission`): three route children | **Yes** | Credit counted usable handoffs through `targets.usable_handoff` on a job-provider object (`credit.py:16-28`); `credit` has no services, so "usable" must be a pure function of the held handoff record or a typed field of the route child's result. The bounded maximum ("requests not yet held", `yield_estimator.py:47-54`) becomes maximum from `parent_input` with the held ones counted in the initial credit. Its behaviour changed under an HPC ancestor (`action_policy.py:7-12`) and it imported the planner's `authenticate_launch` (`from_parent.py:25-27`): both must arrive in the assignment |
| **HPC planning** (`hpc_work_planning`) | **Not as it was. In the form the launch design intends: yes, with the most work** | Its state was a file ledger (33 `records`, 17 `put`, 16 `save_action` calls) that also held its credit (`credit.py:14-16`) and that its launch child read by path (`to_child_execution_job_submission.py:32-67`): every ledger fact must become a tool outcome or a Store record passed in custody. Its estimator took a packet per action with a schedule and a clock time (`yield_estimator.py:25-92`); a controller input is fixed to credit and progress time, so a per-action prediction has no way into the controller, and "only the three" drops the estimator. Clock refusals (N6). `hpc.monitor.wait` (`waiting.py:25-50`) is the wait of N10. Cross-run memory (`configuration.py:30-32`, `measured_history.py:76`) is a service outside the journal (N14) |
| **Monitor** (`execution_progress_assessment`): may commission itself | **Yes; the closest fit** | Job access as a service for its one observing tool. Credit read a provider's progress store through `services` (`credit.py:11-21`): it must come from the tool's outcome. Snapshots lived in the provider's store; to reach a parent they must be Store records. A check that finds "still running" is a unit with no gain (N10) |
| **Result acquisition** (`execution_result_acquisition`): no children | **Yes** | Transport as a service. Its per-operation intent, observation, window and receipt files (`retained_result_acquisition.py:36-68`) move into that service keyed by `ctx.operation_key`, because the Store cannot hold them across a rerun (N9). Credit over result bytes works through `records.read_artifact` (D2). The estimator read a completion proof from the estimation context (`yield_estimator.py:47`): no channel; a bounded controller with maximum from `parent_input` replaces it |
| **Leaf, HPC job** (`hpc_job_execution`) | **Yes** | SSH and scheduler as a service. At-most-once: the system's began/finished journal replaces half of `state.begin`/`state.finish`; the other half, "return the saved receipt of the completed intent", needs N9 or a registry in the service. Working directory and environment carried between units (`terminal_operations.py:36-40`) ride in outcomes. It read its parent's request by SQL (`operations.py:21`): assignment |
| **Leaf, passage extraction** | **No, until N1** (same library as literature) | It checked assigned spans against the source artifact's size in `from_parent.py:10-52`; `read_from_parent` receives no `records`, so that check moves to the summary or the first tool |

Where the owner's decision rule would live: the model's pick in `decide`; the refusal in `action`, which lacks
its inputs (N6); the prediction in the costly action's arguments, which are now kept (B4). The comparison of
this action's expected yield with other actions' has no file and no data path: `yield_estimator.py` returns a
controller and nothing else reads settings.

## 8. Questions only the owner can decide

1. **How the support library reaches its tables** (N1): Store records, a narrow door in the facade, or a
   raw-Store service outside custody? Literature and passage episodes wait on this.
2. **What `decide` and `action` may see** (N6): only the summary, with configuration forwarded parent to child
   and thresholds fetched by tool units; or settings, a read-only run configuration and a time as arguments?
   The second changes two signatures in every `task.py`.
3. **Units that gain nothing** (N10): does the system get a kind of unit the controller does not observe (the
   root's wait, a lookup, a report), or must every credit be written so these gain something? F3 shows the
   present behaviour: 2 to 15 such units end an Episode at a non-zero cost.
4. **The launch/monitor/extract document** (B6): re-issue it against the contract, or is the contract's table the
   design now? The mechanics document's section 8 ("a fourth estimator type that judges one specific action",
   agreed to try) also conflicts with `GOAL.md` "only the three yield estimators".
5. **Is custody a rule or a wall** (N8)? Today a tool that breaks the naming convention reaches everything, and a
   scope argument reads inputs the Episode does not hold.
6. **Does a rerun get its abandoned attempt's records** (N9), or do all intent logs live in services?
7. **May a tool call the model** (N7), recorded by the system?
8. **The seeded-journal model test** (section 6): acceptable, or a scripted fake to be replaced by a model run?
9. **Dead code** (section 4): delete `durable_worker.py`, the commission half of `durable.py`, `suspension.py`
   and `archive.py` now, and move the native-target half of `durable.py` into `episode_support/jobs`?
10. Still open from the first audit: the import cycle (S10); elapsed time shown to the model; whether the four
    older carry-over guides are rewritten or withdrawn before agents follow them (section 5).
