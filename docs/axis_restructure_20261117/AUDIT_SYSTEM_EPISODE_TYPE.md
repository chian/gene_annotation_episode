# Audit of the system episode type and generic runner (19 November 2026)

Independent audit of `method_loop/` (the vendored loop with local patch `episode_type_outcomes_and_forms_v6`),
`episode_runtime/`, their tests, `BINDING_CONTRACT.md` and `carry_over_guide/system_recording.md` with its
names table, against `GOAL.md` and `AGENTS.md`. No code, test or other document was changed.

## Verdict

**Not yet sound to build 202 episodes on.** The mechanics that exist work: units, outcomes, model calls and
receipts are recorded by the system and replayed; a changed model request fails loudly; a commission of an
unheld record is refused; the four class-definition checks asked about reject the plain cases; the two test
episodes contain no recording or replay code. That part can be kept.

Seven things block the carry-over, because each changes what an episode file must contain or a signature every
episode is written against:

1. A tool cannot reach anything but four custody methods. No services, no configuration, no Store queries (B1).
2. `yield_controller` cannot see the assignment, and 6 of the 8 old episodes that were
   read chose their controller's kind or capacity from it (B2).
3. `credit`, `read_from_child` and `internal_summary` cannot read record content, which old credit was computed from (B3).
4. A child unit's outcome carries neither its slot nor its arguments (B4).
5. `view.updates` and `view.child_reports`, documented as available, are not restored on resume (B5).
6. The chosen launch/monitor/extract design depends on four things the 19 November contract removed (B6).
7. An interrupted tool re-executes its side effects on resume; there is no at-most-once device for a job
   submission (B7).

Eleven further findings should be fixed before the carry-over starts and nine are minor.

## How this was checked

- Read in full: `method_loop/episode_type.py`, `forms.py`, `binding.py`, `__init__.py`, `communication.py`,
  `LOCAL_PATCHES.json`, `SOURCE.json`; the loop, view, `Leaf`, `ChildEpisodeUnit` and resume parts of
  `method_loop/episode.py` (lines 1031-1962); all of `episode_runtime/*.py`; all of `episode_runtime/tests/**`;
  `BINDING_CONTRACT.md`, `system_recording.md`, `GOAL.md`, `AGENTS.md`; the summary, sections 6, 7 and 10 of
  `LAUNCH_MONITOR_EXTRACT_MECHANICS.md`.
- Compared every vendored file's hash with `SOURCE.json` and `LOCAL_PATCHES.json`, and diffed `episode.py` and
  `runtime.py` against upstream `7576c096`.
- Ran the system's tests: `runs/aud_sysep_01`, 12 passed, 1 deselected (`model_run`).
- Ran 7 throwaway probes, `runs/aud_sysep_inputs/test_probe.py`, run `runs/aud_sysep_02` (7 passed; the output
  lines marked `PROBE` are the evidence quoted below). The probes use the real runner, journal, Store,
  `yield_control` and the two test episodes; the model was never called.
- Eight old episodes at `97308b94c` were read by a delegated reader, inside the trees
  `root/a105/experimental_activity_evidence/**` and `root/a104/evolutionary_history_evidence/**` only. Its
  line references are cited in section 5. **Limit:** all eight delegate core mechanics to modules outside
  those trees, which were not read; where a claim depends on them it is marked "not verified".
- Not done: the `model_run` test was not run (it needs the owner's sign-in), and the whole-tree collection was
  not run, so the builder's "63 collection errors" is unverified.

## Findings that block the carry-over

### B1. A tool has no channel for services, configuration or the Store beyond four methods

Evidence.
- A tool is called as `tools[name](arguments, bound.records)` (`method_loop/episode_type.py:341`). Every
  supplied function is called unbound (`_member`, `:213-215`), so instance state cannot reach it.
- `Custody` offers `read`, `read_artifact`, `put`, `write_artifact` (`episode_runtime/recording.py:107-128`).
- `episode_support/` calls the raw Store about 5,000 times with methods custody does not offer:
  `store.transaction(` 416, `store.validate_scope(` 286, `store.reference_subset(` 164, `store.subject_molecule(`
  85, `store.get_input(` 72, `store.list(` 54, `store.map_segments(` 47, `store.query_records(` 11.
- `BINDING_CONTRACT.md` says scope questions "stay Store functions". A tool has no Store to call them on.
- `system_recording.md` F2 tells a tool to call `store.query_records(...)` and F6 to return
  `unit_outcomes.failure_outcome(store, error, ...)`; neither `store` exists in a tool.
- All 8 old episodes got their services by constructor injection: tool registry and `execute_tool`
  (`E1/scientific_operations.py:84`, `E1/configuration.py:8-11`), SSH transport
  (`HJE/native_configuration.py:22-24`), HTTP clients (`MON/hmmer_observer.py:28`), cross-run execution memory
  (`E1/execution_planning.py:18-31`), a model provider inside a tool (`E1/library_services.py:26-29`).

Why it blocks. Every tool's signature depends on the answer. The only routes open today are module-level
globals or `records._store`, which are a hidden second way of doing the job.

Suggested fix. Decide one channel and write it into the contract before any tool is carried over. Two
candidates: (a) the run's collaborators mapping gains named services and a tool receives
`(arguments, records, services)`; (b) custody grows the read-only Store questions and a transaction, and all
other services arrive as library imports configured once at link time. Either way, delete the instructions in
`system_recording.md` that pass `store` to a tool.

### B2. `yield_controller(initial_credit, settings)` cannot see the assignment

Evidence.
- `build_controller` passes only the initial credit and `collaborators['continuation'][binding_path]`
  (`episode_type.py:269-275`, `episode_runtime/runner.py:103-104`).
- Old episodes chose the controller kind and its maximum or target from the commissioned task:
  `maximum_credit = task['credit_unit'] * len(task['experiments'])` (`LIT/yield_estimator.py:73`, six task keys
  at `:14`); remaining eligible requests (`SUB/yield_estimator.py:47-55`); bytes already held
  (`RES/yield_estimator.py:42`). That is 6 of the 8.
- Settings are keyed by binding path only, so one episode commissioned for two task kinds gets one setting.

Why it blocks. `yield_estimator.py` is one of the ten files; its one signature cannot express what most old
estimators did.

Suggested fix. Give the function the admitted `parent_input`: `yield_controller(initial_credit, settings,
parent_input)`. Whether the old custom estimators (`_RemainingCommissionedCredit`, `PracticalYieldEstimator`,
`HPCContinuationEstimator`) are dropped in favour of the three is the owner's rule already ("only the three");
the capacity argument is still needed for `BoundedQuality` and `Completion`.

### B3. Credit and child receipt cannot read record content

Evidence.
- `credit(summary)`, `read_from_child(slot, result, summary)` and `internal_summary(view)` receive no `records`.
- Old credit was a projection over Store state, most importantly right after a child returned: the graded
  sheet exists and the assessment is current (`LIT/credit.py:176-191`, with `requires_episode_receipts = True`
  at `:146-147`); the handoff is usable (`SUB/credit.py:25-30`); a scope projector (`E1/credit.py:35-36`).
- Old receipt had side effects: returned cells were written into the parent's repositories
  (`LIT/from_child_evidence_search_strategy_improvement.py:8-14`).
- AGENTS.md requires that an A105/A108 interpretation "must not receive credit before that sheet exists".
  With the present API the only way to know the sheet exists is a field of a tool outcome or a child return.

Consequence if left. Either every credit-relevant fact becomes a typed field of a tool outcome or child
return (a rule every `return_form` must then follow), or the parent spends an extra verification tool unit per
child, and that unit enters the yield history with zero gain.

On the question "internal_summary cannot see held records: is it a real problem?" The set of held references
is derivable (parent input, `outcomes[*].produced`, `record_refs` fields of child results), but only by
re-deriving custody by hand in every episode, which is what the system was meant to remove. Record content is
not derivable at all. A second consequence: `action` cannot check that a model-chosen reference is held, so it
cannot raise `Rejected`; the commission then dies with `CustodyError` and ends the run
(`runs/aud_sysep_02`: "E refused commission RAISED CustodyError ... run state active").

Suggested fix. Owner decision between: (a) `EpisodeView` gains the held references with their receipts and
`read_from_child` gains read-only `records`; (b) the rule "typed returns carry every credit fact" is written
into the contract and enforced by review. I recommend (a) for the held set, because it costs one view field,
and (b) for content.

### B4. A child unit's outcome has no slot and no arguments

Evidence. `child_outcome` returns `{'kind', 'completion', 'result', 'report'}` (`method_loop/episode.py:607-610`),
and `completion` holds only `ended_by`, `end_reason`, `units_consumed` (`:452-457`). The slot survives only in
the journal's unit label. A tool outcome does carry `tool` and `arguments` (`episode_type.py:347`).

Why it blocks. Every head has three to six slots. A summary folding `view.outcomes` cannot tell which slot an
outcome answers, nor which job handle a monitor commission checked. `GOAL.md` requires that "before a costly
action its expected outcomes are recorded"; for a launch, the costly action is a `ChildCall`, and its
arguments, where the prediction would ride, are dropped.

Suggested fix. Record `{'kind': 'child', 'slot', 'arguments', 'completion', 'result', 'report'}`. Two lines in
`_SystemSource._child` and `child_outcome`.

### B5. `view.updates` and `view.child_reports` are not restored on resume

Evidence.
- `_restore_units` rebuilds each unit as `Contribution(prior.controller_input, outcome=prior.outcome)` with no
  `episode_update` (`method_loop/episode.py:1549`); `_view` reads `ctx._child_updates` (`:1393`), which only a
  live child completion fills.
- `BINDING_CONTRACT.md` lists `updates` and `child_reports` as part of what `internal_summary` may read.
- Probe C, an episode whose summary counts them:
  - uninterrupted: result `{'n': 2, 'n_reports': 1, 'n_updates': 1}`, unit credits `[1.0, 12.0]`;
  - interrupted in unit 1 and resumed: result `{'n': 2, 'n_reports': 0, 'n_updates': 0}`, credits `[1.0, 2.0]`;
  - resuming the closed uninterrupted run: `JournalError recorded_episode_result_differs`.
- The same probe shows the lag asked about: during the child's own unit the credit was computed with
  `n_updates = 0` (credit 1.0), because `with_unit` adds the outcome but not the update (`:1051-1053`).

On the question "credit for a child unit lags: is it a real problem?" Not if the episode reads `outcomes`,
which already holds the child's result and report. It is a real defect for any episode that reads
`updates`/`child_reports`, and resume then makes it worse than a lag.

Suggested fix. One source of child information, not two. Remove `updates` and `child_reports` from the view
the system type gives `internal_summary` (and from the contract), since `outcomes` carries the same report.
The test episodes already use only `outcomes`.

### B6. The launch/monitor/extract design relies on things the contract removed

`LAUNCH_MONITOR_EXTRACT_MECHANICS.md` (18 November, "design chosen by the owner") predates the 19 November
contract and says the runner and `method_loop` "do not change". Four of its mechanisms no longer exist:

| The design says | Line | State under the 19 November contract |
|---|---|---|
| "The table and the job access are collaborators"; the table is "given to every binding as a collaborator" | 406-407, 468 | only `store`, `model_provider`, `continuation`; no episode function receives a collaborator |
| Launch, check, `check_at`, `wait_until` times are "UTC values the source records with `bound.recorder`" | 469-470 | `bound.recorder` is removed; `decide` is a pure function and cannot read a clock |
| "The new head Episode reads its outstanding jobs from the Store" | 65, 156, 484 | custody refuses any record not passed, returned or produced; there is no Store query |
| The root "waits in the process until then, and decides again" | 446, 752 | no wait that is not a unit; a blocking wait tool is a unit with zero gain in the root's yield history |

Why it blocks. 100 of the 202 episodes are submission, monitor, result-acquisition and route episodes
(`execution_job_submission` 18, `execution_progress_assessment` 17, `execution_result_acquisition` 18,
`hpc_job_execution` 16, `local_job_execution` 16, `api_job_execution` 15); 33 more are HPC planning and
resource-work episodes.

Suggested fix. Re-issue the mechanics document against the contract, deciding for each row: outstanding-job
records travel root → head → monitor in `record_refs` fields; times are captured inside tool outcomes; the
table is a Store record passed in custody or a named service under B1; and the wait is either a tool unit
whose zero gain the root's estimator is told to ignore, or a unit-less wait added to the system type.

### B7. An interrupted tool repeats its side effects, and leaves an orphan produced record

Evidence.
- Probe F, a tool that writes a record and is then interrupted. After resume the unit's outcome reports
  `produced: [artifact_bc7c6d5e9, artifact_3dafcfaa6]` although the tool returned only the second. The first
  attempt's `produced` receipt was journaled at the same unit (`recording.py:130-133`) and the outcome lists
  every produced receipt of that unit (`episode_type.py:344-346`).
- `BINDING_CONTRACT.md` claims "a repeated tool write gives the same reference and the same receipt". That
  holds only when the retry writes identical bytes. For revisioned Store kinds a retry with the original
  `expected_revision` raises `RevisionConflict` (`gene_annotation_episode/state.py:1611-1620`).
- Nothing lets the system know a unit was started. A job submission tool that is interrupted after the
  scheduler accepted the job submits again on resume. The old `hpc_job_execution` kept intent and finish
  receipts for exactly this (`HJE/native_receipt_state.py:9-16`, `native_tool_actions.py:29, 39-45`).

Why it blocks. Replay is meant to be the system's; with no device, each launch tool must write its own
"did I already do this" check, which is replay code inside an episode.

Suggested fix. The system journals "unit N began, with this action" before executing it. On resume a begun,
unfinished unit is handed to the tool with that fact (or the tool's first-attempt produced records), and
receipts of an abandoned attempt are either removed or marked. Correct the contract sentence.

## Findings to fix before the carry-over starts

### S1. The class-definition checks have six holes

The four cases asked about are rejected (probe A): a second base or an episode base
(`episode_must_inherit_only_from_EpisodeBinding`), each of the 15 members missing, an extra or `_private`
member, each of the 9 system members overridden, and all four child-member/slot mismatches. The holes:

| Hole | Probe result | Cause |
|---|---|---|
| An episode that defines `__init_subclass__` can be inherited from; the derived class adds a helper, overrides `credit`, and `BindingRegistry` accepts it | a4 ACCEPTED ×3 | dunder names are skipped (`episode_type.py:174`) |
| `__init__`, `__getattr__`, `__helper__` accepted | c3, c4, c4b ACCEPTED | same |
| A function taken from another episode's module is accepted, all of them at once | e1, e1b ACCEPTED | only `inspect.isfunction` is checked (`:204-206`); the error text says "function_of_its_file" but no file is checked |
| `decide` with no parameters accepted | e2 ACCEPTED | no signature check |
| A tool that is a class or a `functools.partial` accepted; the contract says "tools that are not functions" are rejected | e3, e3b ACCEPTED | `callable(function)` (`:201`) |
| Bad slot names, non-text child paths, an invalid `binding_path`, a tool name with a space accepted at class definition | e4, e7, e8 ACCEPTED | checked only later in `episode_runtime/bindings.py:45-53` |

Assignment after definition (`X.build_episode = ...`, `X.credit = ...`) is also accepted (c6); that is Python
and needs a metaclass to stop.

Suggested fix. Reject every dunder except those Python adds itself; require `function.__module__` to be the
episode package's own file for that member (`<package>.credit`, `<package>.messages.internal_summary`, ...),
which enforces "imports nothing from another episode" for the members; check each signature's parameter
names; require tools to be plain functions; move the path and slot-name checks from the registry into the
class check and delete them from the registry.

### S2. The `records` object a tool receives can forge custody

Evidence. `Custody` exposes the runner's own passes as public methods (`recording.py:142-162`). Probe B: a
tool calls `records.admit_entry([ref])` on a record it was only told about as text, then reads it; the journal
shows a second `entry` receipt. `put` also forwards arbitrary `**options` to `Store.put` (`:118-122`), so a
tool supplies `account_owner`, which the Store calls the "runtime owner" (`state.py:1544-1547`).

Also: a `produced` receipt is written whenever a tool writes content that already exists (content-addressed
artifacts, idempotent `put`), so `producer` means "an episode that wrote these bytes", not the first producer.

Suggested fix. Hand tools a narrow facade (`refs`, `holds`, `receipt`, `read`, `read_artifact`, `put`,
`write_artifact`) and keep `admit_entry`, `pass_to`, `return_to` on a runner-only object. Have the system
supply owner options. Record `produced` only when the Store created the record.

### S3. Continuation settings and controller decisions are not in the journal

Evidence.
- `collaborators['continuation']` is supplied afresh at `resume` and is recorded nowhere. Probe G: an
  interrupted run resumed with cost `1e9` instead of `0` ends `yield_stop` after 1 unit with no error. A closed
  run fails only incidentally (`recorded_episode_completion_differs`).
- `units` holds label, controller input and outcome (`journal.py:55-56`). The controller's step (estimate,
  cost, stop) is not recorded, nor `end_reason`, so "why did it stop" cannot be read from the journal without
  the settings, which are also absent.
- No row has a time. `system_recording.md` F7 concedes "per-call start/end timing has no equivalent".
- A run that dies leaves `runs.state = 'active'` and no failure record. A refused commission leaves the child's
  `episodes` row `active` with no units (probe E), because `open_episode` runs before the custody pass
  (`runner.py:260-271`). A `link` that fails after `open_run` (`runner.py:357-359`) burns the run id.

`GOAL.md` wants cross-run learning "kept as logged, readable, overridable settings and yield thresholds".

Suggested fix. Record each episode's settings with its commission and compare on resume; record the
controller step with each unit; add a captured-at time to units, model calls and receipts; record the
exception that ended a run; pass custody before `open_episode`.

### S4. Rejected model responses are outside every control and invisible to the episode

Evidence. `_SystemSource.next` loops `decide → model → action` until an action is accepted
(`episode_type.py:313-325`). A rejection creates no unit and no observation, as AGENTS.md requires. But
`decide` receives only the latest feedback, the summary is not recomputed, and nothing counts, so the episode
cannot know it is on its fifth rejection and the yield controller never sees the spend. Rejections are also
not journaled as such; they must be reconstructed from `model_calls`.

The old head used several exchanges per decision: the model could answer `request_context` any number of times
before `select_action` (`E1/task_decision.py:138-139, 264-328`). Under the new API that can only be imitated
with `Rejected`, and only the last feedback survives.

This is not a request for a cutoff, which AGENTS.md forbids. Suggested fix: `decide(summary, exchange)` where
`exchange` is the ordered list of this unit's responses and feedbacks, already replayable from `model_calls`;
journal each rejection's feedback.

### S5. `declaration()` is generated but nothing consumes it

Evidence. The only caller of `.declaration()` in the tree is `episode_runtime/tests/test_system_recording.py`.
The runner reads the binding's attributes directly and never calls `accepts`, so the declaration is not
validated at link time and can raise only when somebody asks for it.

On the question "yield_estimator.py fills two declaration roles: is it a real problem?" Functionally no:
`rarefaction` and `continuation` both point at the one `yield_controller` (`episode_type.py:242-243`) and
nothing reads either. On "progress, stopping, schema, composer, build_child are system-supplied": harmless for
`schema`, `composer` and `build_child`. The fixed `stopping` text (`:234`, "stops when its forecast of further
credit is at or below its cost") is wrong for `CompletionYieldController`. Old episodes put more than a number
into the controller input (`practical_completion` at `HJE/completion.py:31-39`; a continuation packet at
`PLAN/yield_estimator.py:25-92`); `Done()` replaces the first and the launch design removes the second, so the
fixed schema loses nothing essential.

Suggested fix. Either build and validate the declaration for every binding in `BindingRegistry` and record it
with the run, or state in the contract that it is a description only. Take the stopping text from the
controller.

### S6. `read_from_child` runs twice, and the report duplicates the result

Evidence.
- Probe C: "read_from_child calls for one child unit: 2". `receive` calls `report` again
  (`episode_type.py:367-372`), and the credit is computed from that second, unadmitted value.
- The outcome holds both the child's raw `result` and the `report`. `ReportContract` exists upstream to keep
  the child's raw result away from the parent's model (`communication.py:79-96`); putting `result` in the
  outcome bypasses it. In the test episode `read_from_child` returns `{'fact': result['fact']}`, a copy.
- Each child edge is therefore described three times: the child's `return_form`, the parent's
  `ReportContract`, and `read_from_child`.

Suggested fix. Call `read_from_child` once and build the credit from the admitted report. Ask the owner
whether the outcome should carry the result, the report, or both (question 5 below).

### S7. `LOCAL_PATCHES.json` does not describe the vendored files

| File | State |
|---|---|
| `runtime.py` | differs from upstream (`unit_ref`, optional `observe_unit` port, `:107-132`); **not listed** |
| `suspension.py` | local file, **not listed** |
| `independent.py` | listed hash `0b2cd709…`, actual `bfa27e74…` |
| `durable.py` | listed `5f99292d…`, actual `a3e5cba9…` |
| `durable_worker.py` | listed `fb3cfc5d…`, actual `2a9d94b3…` |
| `episode.py`, `__init__.py`, `binding.py`, `forms.py`, `episode_type.py`, `archive.py` | hashes match |
| `verification` | 6 of the 7 named test files do not exist (`tests/test_runtime.py`, `test_independent_episode.py`, `test_deferred_episode.py`, `test_episode_admission.py`, `test_episode_completion.py`, `test_ready_child_delivery.py`); no entry for v6 |

The four stale or missing entries predate this build, but the builder rewrote the manifest for v6 and left
them. `episode.py` is 2,381 lines against upstream's 1,855; most of the difference serves the unused pending,
independent and redelivery machinery (section 4).

Genericity of the v6 patch: the `episode.py` and `binding.py` changes are generic. `forms.py` is generic
apart from comments naming "Store record references", a non-existent `custody.py` (`:27-29`) and "an axis's
own evidence task" (`:10`). `episode_type.py` is not generic in the `SOURCE.json` sense (S8).

Suggested fix. Regenerate every hash, list `runtime.py` and `suspension.py`, replace the verification list
with tests that exist.

### S8. The episode type sits in the vendored library but encodes this application

Evidence.
- `SOURCE.json`: "generic method_loop only; no biological application or numerical policy". The manifest's
  purpose says custody "remains in consumers (episode_runtime)".
- `episode_type.py` names this project's ten files (`:134-144`), expects `bound.model`, `bound.records`,
  `bound.progress`, and reads the custody receipt format directly: `receipt(ref)['how'] == 'produced'` and
  `['unit'] == position` (`:344-346`).
- The working copy of AGENTS.md says the base type is "in `episode_runtime`".
- `method_loop/durable.py` depends on `sqlite3` and keeps its own store (`commissions`, `returns`,
  `receiver_claims`, `native_targets`, ...; `:368-393`): a second journal inside the "generic" library.
- Nothing in `method_loop` names a role or axis id, and nothing in `episode_runtime` does either, apart from
  one docstring ("a head's `credit` and `finding`", `runner.py:210`).

Suggested fix. Owner question 1. Whichever home is chosen, replace the receipt-format read with one custody
call (`records.produced_at(position)`).

### S9. A fallback and four optional hooks sit in the live loop

Evidence.
- When a resumed Episode's controller already says stop, the loop takes `state.decision`, finds no
  `requests_transition` on `yield_control`'s `ContinuationDecision`, and substitutes
  `SimpleNamespace(stop=True, requests_transition=False)` (`method_loop/episode.py:1654-1659`). Probe G went
  through this path. It is a fallback on every such resume.
- The loop looks up `bind_execution_context`, `suspension_changed`, `record_execution_failure` and
  `next_epoch` on the source with `getattr(..., None)` (`:1290, 1293, 1297, 1568, 1588, 1690`). The system
  source defines none.
- `recording.py:65-66` and `:103-104` check for a `None` provider and store, which `_check_collaborators`
  already makes impossible. `runner.py:293-298` checks the result of the system's own `build_episode`.

Suggested fix. Make the resume-stop path state what it needs explicitly; the rest goes with the unused
machinery it serves.

### S10. `yield_control` and `episode_runtime` import each other

`yield_control/__init__.py:30` imports `PROGRESS_TIME_VERSION` from `episode_runtime`; `runner.py:86-92`
imports the controllers inside a function, with a comment explaining the cycle. Suggested fix: the estimator
library should not depend on the runner; keep the receipt version with the receipt's consumer or in a module
both import.

### S11. The tests do not cover what the report claims

What is real: no fake or scripted stand-in anywhere; real `RunJournal`, `Store`, loop, `yield_control`; the
two episodes are real episodes in the ten-file layout.

What the 12 executed tests do not reach:
- **Any model call.** `RecordedModel.complete` and the `Rejected` loop run only in the deselected `model_run`
  test, which the builder did not run. Probe D exercised both from a seeded journal: one rejected and one
  accepted response replay into 1 unit, 2 model calls, 0 provider calls; a changed request raises
  `JournalError recorded_model_call_differs:...:0:0`. So the claim is true but was untested.
- **A controller stop.** Every run ends `exhausted` at cost 0.
- An inner entry and `ancestors` (probe E: both work), `start_run`, `BindingRegistry.compose`, every
  `LinkError`, `returned_record_not_held`, a changed commission on resume, self-nesting slots,
  `records.read`/`put` (only artifacts are used).
- An interruption after a side effect (B7) or after a completed child (B5).

Two weak tests. `test_the_episode_files_hold_no_recording_or_custody_code` is a word list; the parent's own
tool calls `records.receipt(...)` (`fact_collection/task.py:20`) and passes because the list has `receipts(`.
`test_the_episode_type_admits_only_the_episode_files_members` covers six cases and none of the S1 holes.

`episode_runtime/tests` is not in `pyproject.toml` `testpaths`, so a default run does not collect it. The
builder's "100 tests pass" is 12 tests of this system plus others.

Suggested fix. Add the probes' cases as tests, add the path to `testpaths`, run `model_run` once.

## Minor findings

- **M1. Duplicates.** Canonical JSON five times (`episode_type._closed:69`, `recording._closed_json:35`,
  `forms._json:37`, `journal.canonical:19`, `durable.canonical:47`). JSON equality twice (`forms._same:173`,
  `journal._equal:23`). Grain name twice (`bindings.grain_name_for:25`, `EpisodeBinding.grain_name`).
  `SYSTEM_COLLABORATORS` and `STANDARD_COLLABORATORS` name the same three. Text checks of `goal`, `unit`,
  `result` in both the class check and the registry.
- **M2. Unused runner surface.** `BindingRegistry.compose` and the "home factory(services)" text
  (`bindings.py:58-77`): no caller, and `EpisodeBinding` takes no services. `start_run`, `grain_name_for`,
  `interface_failures` as an export, `Custody.holds`: no caller in the system.
- **M3. The commissioned report form is half built.** `Commission.report_form`, `_report_form`
  (`runner.py:206-218`), `ChildBuilder.admit(report_form)` and `BoundEpisode.report_form` exist, but
  `ChildMessage` has no such field and `_child` never passes one (`episode_type.py:364`). See question 6.
- **M4. The `decisions` table holds no decisions**, only progress-clock points.
- **M5. Memory.** Each parent keeps every closed child's full `EpisodeRecord` in its unit records
  (`episode.py:1519-1520`); `archive_record`, which released them, is never set. A root that commissions nine
  heads repeatedly holds every descendant's trace until it closes. Not measured.
- **M6. Contract text that does not match the code.** "tools that are not functions" (S1); "a repeated tool
  write gives the same reference" (B7); `updates` and `child_reports` in the view (B5); `compose` and the home
  factory (M2); `system_recording.md` F8 "elapsed time shown to a model comes from progress receipts in the
  controller inputs", which no episode function can read; `README.md` still gives the hook-based plan P0-P5.
- **M7. The support library still holds the old port.** 23 files under `episode_support/` call
  `bound.recorder`, `.recorded(` or `.recall(` (54 call sites; `jobs/**/monitor_runtime.py`,
  `jobs/local_execution/**/local_job_runtime.py`, described in their own docstrings as mix-ins), and two test
  files import `episode_runtime.journal.EpisodeRecorder`. `system_recording.md` lists them as to be removed.
  Outside the audited packages; noted because they are the old recording path still in the tree.
- **M8. `internal_summary` is recomputed from all outcomes** at least twice per unit and JSON-copied each
  time. Quadratic in units; not measured.
- **M9. The summary can see `view.controller_state` one unit stale** inside `with_unit`, and `None` when the
  controller is built.

## 4. Unused machinery: confirmed, and whether launch/monitor/extract could need it

"Unused" means no reference outside `method_loop` itself, by search of the tree excluding `runs/`, `docs/`,
`_superseded/` and the old-port trees. No deletion is recommended here; this is classification.

| Item | Unused? | Class | Reason |
|---|---|---|---|
| `DeferredUnit`, `PendingAction` | yes | certainly dead as written | Needs a registered pending child invocation (`episode.py:1189-1192`), which the design excludes. The root's wait (B6) is a real need, but this cannot express a timed wait |
| `ClosedChildUnit` | yes (its helper `_receive_closed_child_async` is live) | certainly dead | The design re-commissions; resume rebuilds and replays a closed child |
| `IndependentChild`, `independent.py`, `suspension.py`, `allow_suspension`, `start_async`, the owned-child branches of `_run_loop_async` | yes | certainly dead under the chosen design | "Only one Episode decides at a time. There are no concurrent Episode tasks" (mechanics, summary 5). Live again only if the owner reverses that |
| `durable.py` | **no; the builder's claim is wrong** | belongs elsewhere | `episode_support` imports `canonical` or `content_digest` from it in 43 files and `DurableExecutionStore` in 11 (the nine `records/local_execution/*/native_events.py`, `jobs/waiting.py` and its test); `tests/test_durable_episode.py` and `tests/test_native_execution_events.py` test it. The native-target ledger serves detached local jobs, which the design keeps as a job kind: possibly needed, as job-support library, not as part of the loop |
| `durable_worker.py` and the commission/return/receiver-claim half of `durable.py` | used only by `tests/test_durable_episode.py` | certainly dead under the chosen design | They run an Episode in a detached process; no Episode outlives its parent |
| `reconstruction.py` | yes, imported by nothing | certainly dead | A second replay mechanism; the runner's journal and `resume_units` are the one in use |
| `archive.py` | `ArchivedRecord` is a type in `episode.py`; `JsonArchive` only in `durable_worker` | possibly needed, not for jobs | Bounded memory for long runs (M5) |
| `ReportRedelivery`, `ReportDeliveryError`, `receive_failure`, `delivery_contract` | yes | certainly dead unless question 6 is answered yes | Old parents used redelivery only to repair model-authored forms (`E1/from_child_published_evidence_assessment.py:42-62`) |
| `GoalProposal`, `GoalPreview`, `GoalState`, `EpochMutation`, `next_epoch`, `Context.transition` | yes | certainly dead | `yield_control` steps never set `requests_transition`; none of the 8 old episodes revised a goal in place |
| `leaves()`, `_LeafSource`, sync `Episode.run`, `run_unit_async` | yes | certainly dead | Upstream conveniences; the runner uses `run_async` only |
| `resume_owned_accounting_async` | only `independent.py` | certainly dead with it | |
| `EpisodeView.model_inputs`, `ParentReport.validate_model_inputs`, `Context.model_inputs` | yes | certainly dead as built | The audit boundary they enforce is bypassed by S6 |
| `Commission.report_form` | see M3 | possibly needed | Question 6 |
| `STANDARD_COLLABORATORS` beyond the three | now exactly the three | duplicate (M1) | B1 may add named services |

## 5. Fit of the ten files to the old episodes

Members and signatures, with the verdict for each file:

| File | Members | Sensible for the old episodes? |
|---|---|---|
| `goal.py` | `binding_path`, `goal`, `unit`, `result` | Yes |
| `task.py` | `child_slots`, `tools`, `decide(summary, feedback)`, `action(response, summary)` | Partly. Tools lack services (B1). `decide` cannot see earlier exchanges (S4), a clock or the cross-axis table (B6). A model answer that is itself the work (`reason`, `E1/task.py:161-168`; the graded interpretation, `LIT/grading/experimental_interpretation.py:17-60`) fits as a `ToolCall` whose arguments are the answer, which keeps the AGENTS.md coupling of interpretation and sheet in one unit, provided grading needs no model call (not verified) |
| `credit.py` | `credit(summary)` | Only if every credit fact is in the summary (B3) |
| `yield_estimator.py` | `yield_controller(initial_credit, settings)` | No for 6 of 8 (B2) |
| `messages/read_from_parent.py` | `assignment_form`, `read_from_parent(assignment, message)` | Yes. Old validation that read record content (span sizes, `PSG/from_parent.py:121-138`) must move to a tool |
| `messages/msg_to_child.py` | `msg_to_child(slot, arguments, summary) -> ChildMessage` | Yes, except a parent-authored return form with initial values (question 6) |
| `messages/read_from_child.py` | `read_from_child(slot, result, summary)` | Partly: no records, no side effects (B3); called twice (S6) |
| `messages/internal_summary.py` | `internal_summary(view)` | Partly: no held records (B3), no slot or arguments for child outcomes (B4), no time |
| `messages/final_to_parent.py` | `return_form`, `final_to_parent(summary, completion)` | Yes, with the same limit on record content |
| `episode.py` | the class | Yes |

Per episode (a105 head and literature, a104 job episodes):

| Old episode | Could it be written today? | What it needs that is missing |
|---|---|---|
| `experimental_activity_evidence` (head) | No | Store-projected credit; service-backed tools; a model call inside a tool; the `shared.*` board; parent-authored child forms; elapsed time in the decision |
| `published_evidence_assessment` (literature) | With awkwardness; one part no | Controller kind and capacity from the task; Store-read credit after a child returns; network tools; `receive_cells` on return |
| `passage_evidence_extraction` (leaf) | With awkwardness | The same two as literature; `state.query` |
| `execution_job_submission` | With awkwardness | Controller maximum from the assignment; route child returns must carry "usable handoff" as typed fields; slot in the child outcome |
| `hpc_job_execution` (leaf) | With awkwardness | SSH and resource configuration for its one tool; at-most-once submission (B7) |
| `hpc_work_planning` | The old form no; the form the new design intends, with awkwardness | Service-backed tools; binding the handoff on receipt; descendants reading the planner's ledger by owner |
| `execution_progress_assessment` (monitor) | With awkwardness; the closest fit | Job access for the observe tool; the previous estimate passed in custody |
| `execution_result_acquisition` | With awkwardness | Transport for tools; a bounded controller whose maximum depends on the assignment |

Where the owner's decision logic would live: the model's pick in `decide`; the code's refusal in `action`
(`Rejected`); the prediction in the costly action's arguments, which needs B4 for child commissions. The
worth-it arithmetic has no file: `yield_estimator.py` holds only the controller factory, and `decide` cannot
read settings, the table or the clock. None of the 8 old episodes had a value-based refusal; `hpc_work_planning`
alone froze a prediction before acting (`PLAN/portfolio_planning.py:27-35`).

## 6. System-only recording: summary of what was asked

| Question | Answer |
|---|---|
| Does an episode still have to do anything for recording, custody, tracing or replay? | Not in the two test episodes. In real ones yes, in three places: re-deriving the held set (B3), guarding a repeated side effect (B7), echoing slot and arguments (B4) |
| Are the two test episodes free of such code? | Yes, except that one tool reads `records.receipt` to report a producer, which the contract allows |
| Can an episode read a record it does not hold? | Through the documented reads, no (`CustodyError record_not_held`). Through `records.admit_entry`, yes (S2) |
| Can a parent pass a record it does not hold? | No: `record_not_held_by_commissioner`, nothing passed. It ends the run and leaves the child's journal row (S3) |
| Does resume replay model calls, receipts, units and outcomes exactly? | Model calls, receipts and outcomes yes. Not `view.updates` (B5), not an interrupted tool (B7), not if the settings changed (S3) |
| Does a changed request fail loudly? | Yes (probe D) |

## Open questions only the owner can decide

1. **Where the episode type lives.** AGENTS.md says `episode_runtime`; it is in vendored `method_loop`, whose
   `SOURCE.json` scope excludes application content. Keep it there and amend the scope, or move it?
2. **How a tool reaches services and the Store** (B1): named services passed to tools, or custody extended and
   everything else imported? This also decides how a model call inside a tool (tool retrieval, perhaps
   grading) is recorded.
3. **What `yield_estimator.py` may read** (B2): the assignment? And are the old custom estimators simply
   dropped for the three?
4. **Who may read record content** (B3): only tools, with every credit fact carried in typed returns, or also
   `read_from_child` and the view?
5. **One channel or two from child to parent** (S6): the typed result, the `ReportContract` report, or both?
6. **Parent-authored return forms.** Old parents wrote each child's typed form and initial values
   (`E1/to_child_published_evidence_assessment.py:11-20`), and AGENTS.md speaks of the parent requesting cells.
   Restore that (then `ChildMessage` gains `report_form`, and redelivery may be wanted again), or are return
   forms now fixed per episode?
7. **Launch/monitor/extract against custody** (B6): do outstanding-job records travel through the root in
   `record_refs` fields; where does the cross-axis table live; is the root's wait a unit?
8. **At-most-once side effects** (B7): a system "unit began" record, or accepted re-execution with idempotent
   tools?
9. **Cross-episode channels other than custody.** The head's `shared.*` information board and the planner's
   ledger read by descendants have no equivalent. Dropped, or rebuilt as passed records?
10. **Rejections** (S4): should the episode see the whole exchange of the current decision?
11. **The unused vendored machinery** (section 4): the rows marked certainly dead make up most of the 526 lines
    by which `episode.py` exceeds upstream. AGENTS.md says to delete what is not wanted; these are the
    candidates, and `durable.py`'s native-target ledger needs a new home first.
12. **Elapsed time shown to the model.** The old head put `time_accounting` in its decision context
    (`E1/decision_inputs.py:23`). No episode function can see a clock or a progress receipt now. Wanted?
