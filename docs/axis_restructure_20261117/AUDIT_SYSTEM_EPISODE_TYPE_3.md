# Third audit of the system episode type and generic runner (19 November 2026)

Third, independent pass over `episode_runtime/`, `method_loop/`, `yield_control/`, their tests,
`BINDING_CONTRACT.md`, `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` and `carry_over_guide/`, after the fix round that
followed `AUDIT_SYSTEM_EPISODE_TYPE_2.md`. The fix agent's report was treated as a set of claims. No code, test or
other document was changed and nothing was committed. Findings of this audit are numbered T1 to T22.

## Verdict

**Not yet sound to build the 202 episodes on.** The runner mechanics are now good: units, attempts, model calls,
receipts on commit, the decision context, the selection handshake and resume all held under my probes, and a wrong
commission simply fails. Three things stop the carry-over, and each changes what every episode file contains:

1. **Three of the owner's rulings are not met.**
   - Ruling 2: `Done` ends an Episode without the yield estimator, and one guide line tells a failing episode to
     end itself that way (T1).
   - Ruling 1: the contract and a kept test teach `action` to check whether a model-named record is held and to
     feed the miss back to the model (T2).
   - Ruling 5: nothing makes credit and finding "always returned"; each child would recompute its credit with a
     second formula (T3).
2. **Custody has holes on its documented operations, and one undecided rule.**
   - A unit can read the content of a record it does not hold, with public calls only (T4).
   - Parsing material through `ctx.store` writes records the Episode then cannot read (T6).
   - Whether holding a record lets an Episode read the records it names is not decided (T5). The answer sets what
     every `msg_to_child` and `final_to_parent` must list.
3. **The library is untouched.** 1,604 raw SQL sites in 253 files remain, no library module declares a work table
   or takes the scoped store, and no real episode is an `EpisodeBinding` class yet (0 found).

Fixing T1 to T6 and T8 to T10 first is a few days of system work. After that the system is a sound base, and the
remaining work is the library carry-over.

## How this was checked

- **Earlier work.** My first attempt at this audit was cut off by an API overload and left nothing on disk (no
  `runs/aud3*`, no draft). Everything here was done again from the start.
- **Read in full:** every file of `episode_runtime/`; the loop, view, `Leaf`, `ChildEpisodeUnit` and end kinds of
  `method_loop/episode.py`; the controllers of `yield_control/__init__.py`; every test and test episode under
  `episode_runtime/tests/`; `BINDING_CONTRACT.md`; `LAUNCH_MONITOR_EXTRACT_MECHANICS.md`; `store-access.md`; the
  Store's `transaction`, `put` surroundings, `query_records`, `record_coverage`, `validate_scope`
  (`library_targets.py:296`) and `materials.py` registration, parsing and member reads; `native_event_ledger.py`.
- **Tests run** (all through `tools/one_workflow.sh --slot aud3`):
  - `runs/aud3_sys_01`: `episode_runtime/tests`, **71 passed, 1 failed (the intended one), 3 deselected**, 41 s.
  - `runs/aud3_sys_02`: the same plus `tests/test_numerical.py`, `tests/test_native_execution_events.py` and
    `jobs/tests/test_waiting.py`: **135 passed, 1 failed, 3 deselected**.
  - `runs/aud3_model_01`: `-m model_run`, **3 passed**, 145 s (HOME held only the `.codex` link).
  - The fix agent's "187 passed" is **not reproduced**: its report does not say which files it ran.
- **Hashes:** all eight `method_loop/*.py` match `LOCAL_PATCHES.json` (`identities.py` matches upstream).
- **Probes:** 13 throwaway tests with a ten-file probe episode, real runner, journal, Store and `yield_control`,
  no model call. Files: `runs/aud3_probes/` (`aud3ep/`, `test_aud3_probe.py`). Runs: `runs/aud3_probe_01` and
  `runs/aud3_probe_02` (13 passed). Lines starting `PROBE` in each run's `stdout.log` are quoted below as P1 to
  P12 and C1 to C11.
- **Counts:** `grep` over the non-test files of `episode_support/` (2,547 files).
- **Old episodes:** a delegated reader read seven kinds in `root/a102/structural_homology_evidence/**` at
  `97308b94c` with `git show` only. It did not follow imports out of the tree; such answers are marked "not
  determinable". A second delegated reader compared the five old guides with the new `README.md`.
- **Limits.**
  - The whole restructure is one uncommitted working tree, so `git` cannot separate this round's changes from
    earlier ones. I checked what the report named and what file times after 01:53 showed.
  - I did not run the whole test tree.
  - The old-episode reader's line numbers were not re-read by me.

## 1. The owner's rulings, in the code and in the documents

| Ruling | Code | Documents and tests |
|---|---|---|
| 1. A wrong commission fails; nothing checks, repairs or feeds back | **Met for the commission itself.** A bad selection or an unheld record raises where the child is built (`runner.py:311-319`), after the attempt is journaled (`episode_type.py:484`). The run records the failure, the unit stays `began`, and resume raises the same error (`test_probe_runs.py:300-322`, confirmed in `aud3_sys_01`). No link-time name comparison exists | **Violated** by the example in `BINDING_CONTRACT.md:272-275` and the kept test `test_model_run.py:61-95` (T2). `README.md:373` moves a child's check of its assignment into the child (T2). `runner.py:264-275` and `:320-322` check the entry input ahead of recording (T2, owner input) |
| 2. Stopping is the yield estimator's alone | **Violated.** `Done` ends the source (`episode_type.py:444-446`; `method_loop/episode.py:1221-1222`, `ended_by='exhausted'`). No "observed unit" concept exists anywhere | Contract `:290` and `:330` contradict each other; `README.md:152` tells a failed episode to return `Done(closing=<the failure>)`; all three test episodes end by `Done` in ordinary runs (T1) |
| 3. Library never touches the Store directly | System side met: no raw-Store service, `ctx.store` has no `db` or `path` (P9). **Library side not started:** 1,604 `store.db` sites, 0 uses of the custody API | Stated correctly as rule 3. `BINDING_CONTRACT.md:195` ("nothing an episode can reach in the Store" is outside custody) is false (T4, T6, T7) |
| 4. `yield_estimator.py` reads only what `read_from_parent` produced | Met: `build_controller` passes `view.parent_input` (`episode_type.py:361-368`); no episode function receives the raw assignment | Stated correctly (`BINDING_CONTRACT.md:26-27`, `README.md` rule 4) |
| 5. The child declares, the parent selects; credit and finding always returned | Selection met (`RecordForm.select`, `FormError`). **"Always returned" has no support** (T3) | `BINDING_CONTRACT.md:29` says the required fields "(credit, finding)" are always returned; the probe test episode's return form has neither |
| 6. No fakes; three estimators; credit unbounded; no role or axis names; class inherits only the system type | Met. The runner refuses a controller that is not one of the three (`runner.py:127`). Credit is only checked finite (`episode_type.py:184-187`). No role or axis word in `episode_runtime/*.py` or `method_loop/*.py`. Base check at `episode_type.py:234` | One test edits the journal by SQL (`test_probe_runs.py:153`); see section 11 |
| 7. Structure and `method_loop` are not fixed | `AGENTS.md` places the runner and estimators under `episode_support/`; they are top-level packages (`episode_runtime/`, `method_loop/`, `yield_control/`) (T17) | |

## 2. Status of N1 to N14 and the leftovers of audit 2

| | Status | Evidence | What remains |
|---|---|---|---|
| N1 scoped store and library | **Partial** | Inventories, `require`, `artifact_path`, `in_scope`, receipted `register_material` and `create_problem`, and work tables exist and work (their tests; P4, P6) | The library is untouched. New problems T4 to T8, T12 |
| N2 receipts on commit | **Fixed** | P4: inner rollback inside a committing outer transaction leaves no receipt and no record; `receipts == produced`; a write in `read_snapshot()` is receipted | The opposite gap: a cut after the Store commit leaves records with no receipt (T9c) |
| N3 account owner | **Fixed** | `store_scope.py:377-378`; their test gives two runs separate accounts | Two journals using one run id over one Store collide (T11) |
| N4 refused commission | **Resolved as ruled** (nothing built) | Contract `:286-289`, `:327-329` now say the truth | T2 for the wording and the entry pre-check |
| N5 parent cannot know child fields | **Resolved as ruled** (nothing built) | | |
| N6 decision context | **Fixed in form** | `decide(summary, feedback, ctx)`, `action(response, summary, records, ctx)`; `DecisionContext` (`recording.py:274-288`); clock recorded per unit position (`progress.py:81-93`; their test) | Services read in `decide` are not recorded (T10). `Done(closing)` is T1 |
| N7 model in a tool | **Fixed** | `ctx.model` is the same `RecordedModel`; model test passed in `aud3_model_01` | |
| N8 custody strength | **Documented as a rule, not a wall** | Contract `:260-265`. A scope over an unheld subject is refused (P2: `get_input`, `subject_length` refused) | Bypasses through public calls: T4, T7, T13 |
| N9 abandoned attempts | **Partly fixed** | `abandoned_receipts`, `ctx.abandoned`, `reclaim` work; `reclaim` of an unheld record is refused (P9) | Three gaps (T9) |
| N10 units that gain nothing | **Resolved as ruled** (no code) | Their test shows only the estimator ends such runs | The wait is still "not provided" |
| N11 class checks | **Partly** | C9 to C11 refused | C1 to C8 accepted (T14) |
| N12 two names for one operation | **Fixed** | `ctx` has no `records` (their test) | |
| N13 large outcomes | **Not done** | | |
| N14 journal gaps | **Mostly fixed** | Controller step, `end_reason`, closing, declared services, service builds are journaled | By reading, not run: a `link` that raises after `open_run` records no failure (`runner.py:420-421`; failure is recorded only in `EpisodeRun.run`, `:90-92`) |
| S10 import cycle | **Fixed** | `yield_control` imports nothing from the runner; `PROGRESS_TIME_VERSION` at `yield_control/__init__.py:33` | |
| M5, M8, M9 | Not done | | |
| M7 old recorder calls | Not done | 54 sites in 18 non-test library files, unchanged | |
| Dead code (Q9) | **Deleted** | See section 8 | `transitioned`, `requests_transition` remain in `yield_control`; `SourceEnd` remains in `method_loop` (T22) |

## 3. New findings

Severity: **blocks** = violates a ruling, or the answer changes every episode; **fix first** = a defect that would
be copied into many episodes; **minor**.

### T1. `Done` is a stop the yield estimator does not decide (blocks; ruling 2)

- `decide` or `action` returns `Done`; `_unit` returns `None` (`episode_type.py:444-446`); the loop breaks with
  `ended_by='exhausted'` (`method_loop/episode.py:1221-1222`).
- All three test episodes end this way in ordinary runs (`test_system_recording.py:121-123`: both completions are
  `'exhausted'`). `fact_extraction` ends itself when it has found the fact (`fact_extraction/task.py:27-28`).
- `BINDING_CONTRACT.md:290` describes `Done`; `:330` says the run goes "to its controller-decided end".
  `README.md:152`: "An episode that ends because it failed returns `Done(closing=<the failure>)`".
  `LAUNCH_MONITOR_EXTRACT_MECHANICS.md:227-228` lists it as one of the two ways a head closes.
- The fix agent called this an open design point. Under the ruling as written it is a second stopping rule.

Suggested fix (owner decides, question 1). Either remove `Done`, so a task always offers a unit and only the
controller closes the Episode (a closing value then comes from a tool unit's arguments or `final_to_parent`); or
the owner names "the task has no unit left" as the one permitted non-estimator end and the documents forbid using
it as a decision, starting with `README.md:152`. Either way every `task.py` depends on the answer.

### T2. Documents and a kept test teach a check with feedback for a record a commission would need (blocks; ruling 1)

- `BINDING_CONTRACT.md:272-275`: `action` raises `Rejected(feedback)` when the model's answer "names a record
  `records.holds(ref)` denies", and `decide` is called again with that feedback.
- `test_model_run.py:61-95` and `probe/task.py:267-268` do exactly that (`{'not_held': ref}` goes back to the model).
- The first audit asked for `records` in `action` for this purpose. For a tool argument it is an ordinary
  rejected answer. For a record a `ChildCall` will pass it is a check plus a feedback path for a wrong commission.
- `README.md:373` keeps a child-side check of its assigned spans ("the check moves to `internal_summary` or to the
  first tool").
- The entry input is checked before the run is recorded: `_prepare` admits the entry assignment
  (`runner.py:264-275`, then again at `:311`), and `require_in_store` checks each entry record exists
  (`runner.py:320-322`, `store_scope.py:52-62`). The contract presents this as a feature (`:323-329`, `:393`).
- Wording that reads as a guarantee: "refused before anything of the child is recorded" (`runner.py:246-248`),
  "a refused commission leaves no Episode behind" (`:317`).

Suggested fix. Delete the example from the contract and say what `Rejected` is for: an unworthy or malformed
answer (`GOAL.md`). Change the test so the rejection is not a custody question. Delete `README.md:373`'s kept
check. Owner to say whether the entry caller's input falls under ruling 1 (question 2); if it does, delete the
admission in `_prepare` and `require_in_store`. Nothing is added.

### T3. "Credit and finding are always returned" has no support in the system (blocks; ruling 5)

- The class check asks only that `return_form` is a `RecordForm` (`episode_type.py:270-272`).
- `final_to_parent` receives `completion = {ended_by, end_reason, units_consumed, closing}`
  (`episode_type.py:501-502`): not the credit the controller saw, and no `records`.
- `fact_collection` therefore states its credit formula twice (`credit.py:5` and
  `messages/final_to_parent.py:13-14`). The probe episode returns neither credit nor finding
  (`probe/messages/final_to_parent.py:5-14`). A credit that reads records (`probe/credit.py:18-19`) cannot be
  recomputed in `final_to_parent` at all.

Consequence. In 202 episodes the returned credit would be a second formula that can differ from the one the
estimator stopped on.

Suggested fix. Put the Episode's credit, as the controller last saw it, into `completion`; and have the Episode
type require `credit` and `finding` as required fields of every episode's own `return_form`. That is a property of
one episode's own declaration, not a comparison between episodes. Owner to give the form of `finding` (question 3).

### T4. A write may name records the Episode does not hold, and the Store then reads them for it (fix first)

- P1: a tool that cannot read artifact S (`CustodyError`) writes a `source` record naming S
  (`ctx.store.put`), registers material from it, and `ctx.store.material_read(material)` returns the bytes of S.
  `holds(S)` stays `False` throughout.
- P10: an Episode holding only the problem subject commits a term anchored in a source it does not hold. The
  commit completes, the Episode holds the term, and the term carries the quoted text of the unheld artifact
  (`'quote': 'protein binds zinc'`). Start and end are the caller's choice, so any span can be read.
- Cause: `ScopedStore.put` (`store_scope.py:357-362`) and `commit_reasoning` (`:371-381`) do not look at the
  references a write names. Work-table rows do (`work_tables.py:214-216`).
- This is not the documented limit "writes the same bytes": no knowledge of the content is needed.

Suggested fix. A write requires every reference it names (the Store's `_refs`) to be readable by the unit, the
rule rows already follow.

### T5. Custody has no rule for the records a held record names (blocks: decide before the carry-over)

- A named read needs its own receipt: an Episode holding a source cannot `get_artifact(source['artifact_ref'])`
  unless the artifact was also named (P1 `read_before`; their fixture passes both, `test_scoped_store.py:80`).
- The Store's own operations follow references without custody: `material_read`, `parse_material`, anchors (T4).
- The library follows references constantly: 1,388 `store.get` and 568 `store.get_artifact` sites.
- A work-table sheet is one row per cell, so returning a sheet means one reference per cell in a `record_refs`
  field.

Consequence. Every `assignment_form` and `return_form` must list the transitive closure of what the receiver's
library code will read (assessment, hypothesis, observations, source, artifact, sheet rows), or the read fails.

Suggested fix (question 4). Either a pass or return carries the records the named records name, computed by the
system with `_refs` as `__produce_named` already does for material (`store_scope.py:345-355`), with a receipt for
each; or the contract states "name every record" and T4 closes the other side. Neither is a commission check; it
is the definition of what a pass contains.

### T6. `parse_material` and `material_reference` write records without receipts (fix first)

- P3: after `ctx.store.parse_material(material)` the Store has one parse attempt, one collection and two members.
  The Episode holds none of them: `holds` is `False`, `material_errors`, `material_members` and `get` raise
  `CustodyError`, `list('parse_attempt')` is empty. The unit's `produced` names only material, source, artifact.
- Cause: both are listed and implemented as reads (`store_scope.py:180-182`, `204-206`; contract `:204`) but they
  write (`materials.py:240-381`, `608-614`).
- Members are a second question: `material_member(member_ref)` needs each member held, and a collection can have
  very many.

Suggested fix. Treat both as writes (guard, transaction, receipts for what they create). Say in the contract that
holding a collection lets the Episode read its members.

### T7. `record_coverage(row)` and scope arithmetic read what the Episode does not hold (minor)

- P2: `record_coverage({'id': <held>, 'record_type': 'hypothesis', 'subject_refs': [<unheld input>]})` returns
  the unheld input's extent. `store_scope.py:164-166` checks only `row['id']`.
- `validate_scope` reads the whole problem and, with segments or read selections, inputs and selection records
  (`library_targets.py:296-326`). P2: it accepts a scope over an unheld subject. The contract says the ten
  scope functions "read no record" (`:206`).
- `query_records(references=[ref])` tells whether an unheld record exists (P2: total 0, against
  `unknown_reference` for a missing one).

Suggested fix. `record_coverage` reads the row by its id. Correct the contract's sentence.

### T8. The read-only reader has six operations (fix first)

- `RecordReader` offers `holds`, `refs`, `receipt`, `get`, `get_artifact`, `table` (`store_scope.py:65-97`).
  `credit`, `action`, `read_from_child` and `internal_summary` get nothing else: no `require`, `list`, `count`,
  `current_assessments`, `current_assessment_subset`, `in_scope`, `roots`, `query_records`, no scope arithmetic.
- `AGENTS.md` requires that an A105 or A108 interpretation gets no credit before its sheet exists. A credit can
  check the sheet row through `records.table`, but it cannot ask whether an assessment is current.
- `literature/grading/literature_task_credit.py` makes 17 calls on a store.

Suggested fix. Give `RecordReader` every read-only operation of `ScopedStore` (move the read methods to it).

### T9. Three gaps in what a rerun is told about its abandoned attempt (fix first)

- **(a) An abandoned record stays readable by the pure functions until the next unit begins.** P5: the rerun
  names the abandoned record in its outcome without reclaiming it; `internal_summary` reads it; the unit
  completes; the next unit then fails with `CustodyError`, and every resume fails the same way. Cause:
  `_abandoned` is not cleared when the attempt ends (`recording.py:131-135`, `193-209`).
  Fix: clear it in `end_attempt`, so only the rerun tool can read it and the failure is immediate.
- **(b) A row first written by an earlier unit and rewritten by the abandoned attempt keeps the abandoned
  value.** P6: the rerun finds value 2, revision 2; `ctx.abandoned` is empty. `abandon_produced` moves only
  receipts whose unit is the rerun's (`journal.py:312-322`). The row's `operation_key` column equals
  `ctx.operation_key`, so a tool can tell, but nothing says so. Fix: state it in the contract.
- **(c) A cut between the Store's commit and the journal's receipt.** P7: the Store has the committed source,
  the journal has no receipt, and the rerun's `ctx.abandoned` is empty. The receipt is written after the commit,
  in another file (`store_scope.py:421-426`, then `recording.py:168-172`). For a revisioned kind the contract's
  recipe (`:412-414`: find the abandoned revision in `ctx.abandoned`) then has nothing to find.
  Fix: write receipts in the Store's own transaction (a system table beside `episode_work_rows`).

### T10. What `decide` and `action` read from a service is not recorded (fix first)

- P12: `decide` returns `Done` with a value read from a service; the run closes; the service's value changes; a
  resume of the **closed** run raises `JournalError: recorded_episode_completion_differs`. Their tests show the
  same for an open run (`recorded_model_call_differs`, `abandoned_unit_differs`).
- The contract states the burden (`:162-164`) and the launch design accepts it ("the service gives each run the
  table as it stood", `:111-113`). Job status or a live estimate read in `decide` makes a run unresumable.
- Nothing stops `decide` from acting through a service; "only read" is a convention.

Suggested fix (question 5). Record a decision's reads as the clock is recorded: once per unit position, replayed
on resume. Or keep services out of `decide` and `action` and fetch through tool units.

### T11. One run id in two journals over one Store collides (minor)

P11: the second run gets the same row reference and the same operation key, and its write becomes revision 2 of
the first run's row. `commit_reasoning` is idempotent on that key, so it would return the first run's commit. Run
ids are unique per journal only. Fix: have the run claim its id in the Store.

### T12. Inventories: a silent page limit and cost (minor)

- `ctx.store.list(kind, scope=None, limit=100)` (`store_scope.py:243`). `store-access.md:92` maps a raw
  `SELECT` to "`store.list(kind, scope)` filtered in Python": that reads only the first 100 held records.
  `limit=None` works on the scoped store and is not mentioned.
- Each inventory call reads every held record (`store_scope.py:222-229`); each `select` runs one query per held
  reference (`work_tables.py:192-198`).

### T13. `artifact_path` hands out a path inside the Store's directory (minor)

P8: from `ctx.store.artifact_path(held)` a tool reaches `state.sqlite3` and reads an unheld artifact's bytes. The
contract says no episode receives the directory (`:187-188`). About 45 library sites need the file of an artifact,
so the operation is needed; the contract should say what it exposes.

### T14. Class-definition checks: what still gets through (minor)

| Probe | Accepted |
|---|---|
| C1 | A second class of the same name in one `episode.py`, the first kept under an alias (`_EPISODE_OF_MODULE` compares names, `episode_type.py:288-290`) |
| C2 | A class given `EpisodeBinding` as base after its definition: no check runs, and `BindingRegistry` accepts its instance |
| C3 | `assignment_form` taken from another episode |
| C4 | A `lambda` member |
| C5 | Module-level mutable state used by a member (state shared by all Episodes of the binding) |
| C6, C7 | A member or tool that calls another episode's function through an import inside it |
| C8 | A class attribute replaced after definition (`Aud3.credit = len`), then registered |

Refused: a decorated member (C9), a `staticmethod` (C10), a keyword-only parameter (C11).

Suggested fix. Mark each class the check passed and have `BindingRegistry` accept only marked classes whose
members still equal the checked ones (closes C1, C2, C8). C3 and C6 belong to the import test (T15).

### T15. The import test the contract relies on has nothing to test (minor)

`BINDING_CONTRACT.md:103` leaves "what `episode.py` may import" to `root/tests/test_private_bindings.py`. That
test's docstring still states the old rule ("inherits only from classes defined in its own folder", a home
factory, `CARRY_OVER_GUIDE.md`), and no `EpisodeBinding` class exists under `root/` (0 found).

### T16. `BINDING_CONTRACT.md` against the code

| Line | Says | Code |
|---|---|---|
| 29 | required fields (credit, finding) are always returned | not required, not supplied (T3) |
| 38 | the native event ledger is "reached as a service" | 21 library modules import it directly; no service wraps it |
| 100-102 | the class's copies "cannot be assigned to" | items cannot; the attribute can (C8) |
| 91 | a second episode class in the same `episode.py` is refused | not when it has the same name (C1) |
| 162 | `decide` and `action` only read | not enforced (T10) |
| 187-188 | no library function receives the Store's directory | `artifact_path` (T13) |
| 190-191 | the boundary test fails when a library module imports `Store` | true, and it passes for the 251 other files that run SQL on `store.db` (section 9) |
| 195 | nothing an episode can reach in the Store is outside custody | T4, T6, T7 |
| 204 | `parse_material`, `material_reference` are reads | they write (T6) |
| 206 | the first ten scope functions read no record | `validate_scope` and `scope_covers` read (T7) |
| 224-226 | `_literature_sheet_updating` is a private Store helper | it is not in `state.py`; the literature library sets it as a flag on the object it is handed (0 call sites, 5 files) |
| 272-275 | the `records.holds` rejection example | T2 |
| 290, 330 | `Done` ends the source; the run goes to its controller-decided end | T1 |
| 323-329, 393 | entry input checked before the run is recorded | T2 |
| 407 | resuming a closed run returns its recorded result | it decides the last position again (P12) |
| 412-414 | the tool finds the abandoned revision in `ctx.abandoned` | not after T9c, not for rows (T9b) |

### T17. `AGENTS.md` and the code disagree on where the system lives (minor; owner input)

`AGENTS.md` ("Repository layout") reads as if `episode_runtime/` and `yield_control/` were inside
`episode_support/`. They are top-level packages beside `method_loop/`.

### T18. The Store no longer accepts `native_execution` records; 8 library sites still write them (minor)

`git diff HEAD -- gene_annotation_episode/state.py` removes the kind. The file is dated 18 November, before this
round. Those writers will fail when carried over.

### T19 to T22 (minor)

- **T19.** The reported test total (187) cannot be reproduced; the report should name its command.
- **T20.** `store-access.md` counts are right for the spelling `store.db` (1,604 sites, 253 files, recounted).
  Not counted: 125 `self.db` sites in 7 files that keep their own SQLite files (`run_statistics.py` in three
  copies, `homology_jobs.py` in two, `episode_receipts.py` in two). The page says about 28 raw
  `INSERT INTO artifacts` sites; I count 14, in 14 files.
- **T21.** `jobs/waiting.py` documents `wait_target_feedback` as model feedback for a wait target the ledger does
  not know. That is feedback for a wrong wait choice, not for a commission; noted so the owner sees it.
- **T22.** Dead pieces left: `transitioned(epoch)` and `requests_transition` in `yield_control/__init__.py`
  (`:787`, `:865`, `:896`, `:930`); `SourceEnd` and `END_SOURCE_FAILED` in `method_loop/episode.py:78-80,
  1223-1225`, which the Episode type never produces.

## 4. Custody: what I tried to break

| Attempt | Result |
|---|---|
| Read an unheld record by its reference | Refused (`get`, `get_artifact`, `get_input`, `subject_length`, `table.get`) |
| Read an unheld record's content through a write that names it | **Succeeded** (P1, P10; T4) |
| Read an unheld input's extent | **Succeeded** through `record_coverage` (P2; T7) |
| Read the Store's files | **Succeeded** from `artifact_path` (P8; T13) |
| Forge a receipt with public calls | Not found. `reclaim` of an unheld record is refused (P9). Same-bytes writes are the documented limit |
| Rollback leaving receipts | Not reproduced: fixed (P4) |
| Nested transactions | Correct in both directions (P4 and their test) |
| Commit leaving no receipt | **Reproduced** with a cut at the receipt (P7; T9c) |
| Leak across runs sharing a Store | None with different run ids (P11, their tests). **Collision** with the same run id in two journals (T11) |
| Abandoned attempts | T9a, T9b |
| Rows of another Episode | Not readable, not writable (their test; P11 `before: []`) |

## 5. Does `ctx.store` with work tables cover the library's raw-Store patterns?

**For methods of the Store: yes, with T4 to T8 and T12. For the library as it stands: nothing has moved.**

- The mapping in `store-access.md` is accurate for the same-name calls and the renamed ones, except:
  `parse_material` and `material_reference` (T6); `list` (T12); every `store.get` that follows a reference now
  needs that reference held (T5), which the table's one-line "changed behaviour" understates.
- Work tables fit sheets, cells, ledgers and projections whose rows one Episode writes. They do not delete rows
  (the library has `DELETE FROM` in `finding_validity.py` and five `service_calls` copies) and query by equality
  only.

The "no replacement yet" list, for the three kinds asked about:

| Missing | Who uses it | Blocker for literature, passage extraction, structure? | Minimal custody-obeying replacement |
|---|---|---|---|
| Scratch directory under `store.path` (about 50 sites) | `tools/<axis>/tools.py`, `protein_structure_tools.py`, sequence operations, the nine `materials.py` copies | **No.** Literature storage and passage code do not use it. Structure tools do | It is not a Store operation: nothing in a scratch directory is a record. A declared service that hands out a directory under the run directory; what is kept is written with `ctx.store.artifact` |
| Artifact written from a file (14 raw `INSERT` sites) | `readers/<axis>/source_bytes.py` (used by `literature/inputs` of three axes) and the nine `materials.py` copies | **Not a hard blocker** for literature and passage: papers fit in memory, so `ctx.store.artifact(bytes)` works today. A blocker for large structure and sequence files | One scoped-store write that calls the Store's own `materials.artifact_file` (`materials.py:99`) under the guard and receipts the reference |
| `_caller_source` (27 sites) | material intake | No | A library function over `artifact` and `put` |
| `_assessment_write_extent` (20 sites) | literature storage of five axes, findings | **Yes for literature** | One scoped-store read that requires the hypothesis it reads to be held |
| `_record_roots` (8), `_assert_library_write_scope` (5) | findings, `literature_task_credit.py` | **Yes for literature credit and findings** | One scoped-store operation each; `_record_roots` also on the read-only reader (T8) |
| `_refs` (2) | `episode_receipts.py` | No: old-runner machinery, deleted | |
| `_literature_sheet_updating` | literature sheet updates | No: it is a library flag, not a Store helper | A flag in the library's own call, or `store.in_transaction()` |
| Worker-thread connection (1 site) | `protein_structure_tools.py:481-487` | **Yes for structure** | No Store in the worker: the tool reads inputs through `ctx.store` (file paths from `artifact_path`), the thread computes on files, the tool writes the results. This is a rewrite of `prepare_protein_structure_worker`, not a system gap |

Blocking literature and passage extraction more than any item above: the 888 raw SQL sites of `literature/`
(sheets, cells, pointers, ledgers) must become work tables, and T5 and T8 must be settled first.

## 6. The decision context, `Done(closing)` and `ctx.model`

- `ctx.settings` is a deep copy per call (`runner.py:219-226`); `ctx.clock` is captured once per unit position
  and replayed (their test; 5 points for 4 units and the closing decision). `ctx.run_id`, `episode_id`,
  `binding_path`, `key` are as documented.
- `Done(closing)` reaches `final_to_parent` and the journal (their test). It is recomputed, not restored, on
  resume: the closing decision runs again (P12). See T1 and T10.
- `ctx.model`: recorded and replayed under the unit, numbered after the decision's calls
  (`recording.py:64-88`); confirmed by the model run.
- A tool has no clock in its context; it reads the real clock and returns the time. That is consistent.

## 7. A wrong commission chosen by the model is replayed on resume

**This is what ruling 1 implies, not a defect.** The unit stays `began`, the recorded model answer is returned
again, the same commission is built and the same error is raised. The run has failed.

What follows from the code, so the documents can say it plainly:

- If the correction is in the **child** (it declares the field), the commission is unchanged and the run resumes.
- If the correction changes what the **parent sends**, resume raises `abandoned_unit_differs`
  (`journal.py:169-170`), because the attempt's digest covers the message.
- If the correction is in the **prompt**, resume raises `recorded_model_call_differs`.
- In the last two cases the run cannot continue and a new run is started.

One wording point: `record_run_failure` says the run "stays active and can resume" (`journal.py:106-108`). For a
wrong commission "can resume" is misleading; the state stays `active` only because nothing closes it.

## 8. Deleted machinery and the native event ledger

- `durable.py`, `durable_worker.py`, `suspension.py`, `archive.py` and `tests/test_durable_episode.py` are gone.
  No Python file under `gene_annotation_episode/`, `tests/`, `tools/`, `examples/`, `episode_runtime/`,
  `method_loop/` or `yield_control/` names any of them or their classes (searched for 12 names). **They were
  unused by what remains.**
- `NativeEventLedger` keeps the native half: registration, publication, target validation, `wait_events`.
  21 library files and 2 test files import it, as reported.
- **Failure shape.** `NativeEventLedgerError.failure` is `{code, affected_refs}`. The nine `native_events.py`
  copies read only `failure['code']`, so dropping `diagnostic_ref` and `partial_record_refs` breaks none of them.
  `records/hpc/resource_records.py:55-57` still has a failure schema with both fields; I found no code that
  passes a ledger failure to it. **Low risk.**
- **Unknown wait event.** `EventTargetError('unsupported_wait_event')` is raised in the ledger and turned into a
  failed outcome by `jobs/waiting.py:38-43`; `test_waiting.py` covers it and passes. **Low risk.**
- `hpc_monitoring.py` (three copies) sleeps in the process (`await asyncio.sleep(remaining)`, `:128`). That is a
  wait inside library code; it stays until the job library is carried over.
- Other behaviour changes outside the system packages that I could see: `state.py` (scope arguments now
  required, `native_execution` removed; T18), dated before this round.

## 9. The intentionally red test

`test_no_library_function_module_imports_the_store_class` fails on exactly two modules, as reported.

- `readers/protein_structure/protein_structure_operands.py:44` imports `Store` only under `TYPE_CHECKING`, for
  an annotation, beside an import of a deleted module. It is a one-line removal, not a custody problem.
- `tools/protein_structure/protein_structure_tools.py:482-484` opens `Store(store_path)` in a worker thread.
  That one is real (section 5).
- The test is a real test on real source. Its gauge is narrow: it passes for every one of the 251 other files
  that run SQL on `store.db`. No test measures how much of the library is under custody. A red test kept as a
  marker is the owner's call; if it stays, it should count the raw sites so its number falls as families move.

## 10. Genericity and duplicates

- No role, axis id or episode rule in `episode_runtime/*.py` or `method_loop/*.py` (searched for axis ids and
  role words; the only hits are "annotation" in docstrings and the Store's method names in `store_scope.py`).
- `store_scope.py` repeats about 60 Store method names; each Store change has two places. Acceptable.
- Duplicates left: a child's report in both `view.updates` and `outcomes[*].report`; the entry assignment is
  admitted twice (`runner.py:272`, `:311`); credit stated twice per episode until T3 is fixed.

## 11. Tests

Real: the runner, journal, Store, loop, controllers and the test episodes are real; interruptions are real
exceptions; the model tests call the model.

Weak or questionable:
- `test_probe_runs.py:153` rewrites a journal row by SQL to make "another service declaration". A real second
  declaration (a variant episode) would test the same thing.
- `test_model_run.py:61-95` is T2.
- `tests/test_native_execution_events.py` patches the ledger's internals to place events between a read and a
  wait (`:159-160`, `:369`, `:405`, `:430`). They are instrumented real objects, not scripted stand-ins; the owner
  may still want to look.

Not covered by any kept test (shown by a probe, or absent): T4, T6, T7, T9a to T9c, T10 on a closed run, T11;
an inner rollback inside a committing transaction (P4 passes); a child returning a record it does not hold; a
tool raising after a committed transaction; any real episode, service or job.

## 12. The deleted old guides against `README.md`

The five old guides exist only as scratchpad copies. Compared by a delegated reader; I spot-checked
`README.md:30-36`, `:152`, `:373`.

Not lost, because the old guides never had them: the grading-sheet-before-credit rule, the typed
`investigation_finding`, at-most-once submission, the method for proving a move verbatim.

Lost and needed for the carry-over (old file and line):

1. Library modules the new guide does not place: `genomic_source_invocation.py` (still calls the removed
   recorder), `records/*/held_inputs.py`, `received_sequence_reader.py`, the `*received*_contract(s).py` forms,
   `literature_received_fact_render.py`, the paths of the operation-receipt modules (`system_recording.md:176-184`).
2. Where each credit projector lives (`progress-and-continuation.md:46-47, 88`).
3. `project_finding_progress` and the credit-view fields (`progress-and-continuation.md:45, 52`).
4. Which old estimator maps to which controller, and the trap that credit above a completion target now raises
   `completion_credit_exceeds_target` where the old code took the remainder (`:81, :87`).
5. The episode's own `validate_report` check of facts before returning (`parent-and-children.md:57, 308`).
6. The per-axis form helpers and `report_form_values.py` (`parent-and-children.md:31`).
7. Where instruction text lives (`deciding.md:91-92, 115-118`).
8. Which axes use which transport (`deciding.md:33, 133`).
9. The `reasoning_schema()` envelope and the refusal of an empty reasoning commit (`deciding.md:131-132`);
   `reasoning_schema` is also absent from the scoped store.

Useful but smaller: "parent credit is its own measurement, never a sum of child credits"; scope by namespace;
the details of feedback for rejected model answers; the field names the root's heads receive; timing traps in
`jobs/`.

The two `.tsv` files are explained by `README.md:395-416` and name no old API as a target.

## 13. Can each old kind now be written as a class in the ten-file structure?

Facts are from the a102 tree at `97308b94c`. All seven kinds carried a near-identical copy of one decision loop,
so four things are common to all: several model exchanges per decision with work run inside the decision
(`decision_delivery.py:275-329`); a context built from tables and services outside the Episode
(`:42-87`, `:268`); a return form written by the parent's model (`task.py:169`); pending children, a `wait`
action and redelivery (`child_commissioning.py:14`). The first becomes tool units; the second is the decision
context plus T10; the last two are dropped by the rulings. None of the trees calls the private Store helpers,
`store.path` or `Store(path)` itself; those are in the imported library, which was not read.

| Kind | Writable now? | What it still needs |
|---|---|---|
| **Head** (`structural_homology_evidence`) | **In shape, yes.** Several child slots and self-commissioning work | Credit was a service call (`credit.py:25`); it must be rebuilt on held records and needs T8. The literature-structure repository took the raw Store (`received_structural_context.py:15-16`). T1 decides how a head ends its turn. T3 for the returned credit. T5 for what each return must carry |
| **Literature** (`published_evidence_assessment`) | **No** | Its summary read library tables by raw SQL (`internal_summary.py:46-54`); its storage, credit (`LiteratureTaskCredit`) and yield controller are library code outside the tree (not determinable). Needs the literature tables as work tables, `_assessment_write_extent` and `_record_roots` under custody, T5, T6 for material, T8 for credit. `AGENTS.md`'s sheet-before-credit rule is expressible once T8 is done |
| **Job submission** (`execution_job_submission`) | **Not yet** | Job access as a declared service, idempotent on `ctx.operation_key` (not built). Credit came from a provider (`credit.py:19-27`); it must come from the held handoff. Its bounded maximum was computed from held records (`yield_estimator.py:50-71`); a controller is built from settings and the parent input only, so that maximum must be put into the parent input by the commissioner or it is lost |
| **Leaf, HPC job** (`hpc_job_execution`) | **Not yet** | The same job service. It read its parent's request by SQL (`operations.py:21`), which ruling 4 now forbids: it arrives in the assignment. Its intent files (`terminal_operations.py:26-42`) become `ctx.operation_key` plus a work-table row; T9c matters here. Its estimator checked a completion proof per action; with the three controllers that is lost |
| **HPC planning** (`hpc_work_planning`) | **Not as it was** | Its state was its own SQLite ledger, shared with its children by path (`portfolio_state.py:17-18`, `to_child_execution_job_submission.py:14`): every fact becomes a row passed in custody. Its estimator took a per-action packet with a clock and wrote to the ledger (`yield_estimator.py:22-92`): not one of the three. A tool slept until a schedule (`waiting.py:43`): no wait exists. SSH and queue access as a service |
| **Monitor** (`execution_progress_assessment`) | **Closest: yes, with the service** | One observing tool over the job service. Credit was a service call (`credit.py:13`); it must read what the check tool wrote. Its estimator is plain accumulation from settings |
| **Result acquisition** (`execution_result_acquisition`) | **Not yet** | Transport as a service. It checked its commission against the parent's records by raw SQL (`saved_result_commission.py:15-40`): dropped by ruling 1. Its intent and window files become work-table rows. Large results need the artifact-from-file write (section 5). Its finite maximum came from held records: same loss as job submission |
| **Leaf, passage extraction** | **No** | The same library as literature. It also listed a `child` action while having no children |

What every kind needs before it is written: T1 (how it ends), T3 (what it returns), T5 (what a pass contains).

## 14. Questions only the owner can decide

1. **`Done`** (T1). Is "the task has no unit left" a permitted end, or does only the controller close an Episode?
   And how does a head with only an outstanding job end its turn?
2. **The entry caller** (T2). Does ruling 1 cover the run's caller, so that the entry input is not checked ahead of
   recording either?
3. **Credit and finding** (T3). Should the system hand the Episode's credit to `final_to_parent` and require
   both fields in every return form? What is the form of `finding`?
4. **What a pass contains** (T5). Does passing or returning a record carry the records it names, or must every
   one be named?
5. **Reads in a decision** (T10). Should the system record what `decide` and `action` read from a service, or
   should services be closed to them?
6. **`Rejected` and custody** (T2). May an episode's `action` reject a model answer because a record is not held,
   when that record is for a tool and not for a commission?
7. **The red test** (section 9). Keep it as a marker, and if so should it count raw-Store sites?
8. **Where the system packages live** (T17). Top level as now, or under `episode_support/` as `AGENTS.md` reads?
9. Still open from audit 2: large outcomes (N13); the 54 old recorder call sites (M7).
