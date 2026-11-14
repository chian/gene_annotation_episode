# triage_b: HPC planning homes (`hpc_work_planning`, `hpc_allocation_execution`, `hpc_resource_prediction`)

Scope: 122 failures in 11 failure groups (rows of `runs/claude_tests_leaf_up_20261114_02/failure_groups.tsv`).
Paths below are relative to `gene_annotation_episode/episodic_workflow/root/` unless they start with `runs/` or `tools/`.

## Headline

- All 122 failures are test-side. No product defect was found in this cluster, and no proposed fix touches product code.
- None was caused by the automated import re-pointing. Commits 3dd58552a, 22c1bab66, f29225f0a and 632283f17 did not touch any helper or test file involved here (`git show --stat` per commit). The files date from the snapshot commit dfe3e6091, so these tests were already failing there. Pre-snapshot history contains none of these helpers or symbols, so it gives no "original" to compare against.
- Every per-home test file in the five shared modules is a 6-7 line shell that sets only `axis`, `binding_path`/`parent_path` and `role`, and inherits everything from one shared helper in `tests/`. The copies differ only in those attributes. A group therefore has the same cause in every home of an axis; which axes fail is decided by per-axis product differences (intended customisation).
- Four distinct causes:
  - C1: a102/a103/a104 route task instructions through the axis service, which dispatches to the private composer; the shared helpers stub that service. 58 failures.
  - C2: a104 has its own presentation and provider-dispatch interface, and an extended child-receiver table; the shared helpers assume the other axes' form. 18 failures.
  - C3: a103's `Workflow.build` calls `self.legacy_parent_for_path`; the hand-built workflow doubles lack it. 16 failures.
  - C4: a103's registry gives the annotation root a real parent (`legacy_annotation`); an a103-private helper still expects the label `None` in an error message. 30 failures.

## How this was checked

- Read: tracebacks in `junit/*.xml`, the shared helpers, the per-axis product code, and `ownership.md` notes (treated as claims and checked against code).
- Ran: 10 runs, one test file each, through the launcher with slot `triage_b` (`runs/claude_triage_triage_b_01` to `_10`).
  - Run 01 printed the actual captured results for C4, because the helper raises a bare `AssertionError`.
  - Runs 02-10 applied the proposed test-helper edits in memory and ran the unmodified test file. The helper source was read, edited as a string, compiled and placed in `sys.modules` by a script kept outside the repository (session scratchpad). No repository file was changed.
  - This is a step beyond the brief's plain "run a test": it was the only way to confirm a fix without editing files.
- The exact edits used in runs 02-10 are the ones listed under "Minimal fix" below.

## Table

| # | Group (module :: test, message) | Count / homes | Class | Cause (evidence) | Minimal fix | Changes scientific behaviour? |
|---|---|---|---|---|---|---|
| 1 | `test_planning_allocation_task` :: `test_private_decision_dispatch_saved_replay_and_selected_presentation`, "Private task selected axis instruction composer" | 32 / a102, a103 x 4 homes | stale_test | C1 | F1a | No (test only) |
| 2 | `test_prediction_prompt` :: `test_private_composer_omits_unavailable_child_repair`, "Axis composer selected" | 6 / a102, a103, a104 x 2 homes | stale_test | C1 | F1b | No |
| 3 | `test_prediction_prompt` :: `test_actual_decision_dispatch_and_saved_replay_keep_private_presentation`, bare `AssertionError` | 20 / a102, a103 (4 params each), a104 (2 undeclared params) x 2 homes | stale_test | C1 | F1b | No |
| 4 | same test, "Declared renderer was omitted" | 4 / a104 x 2 homes | stale_test | C2a | F2a | No |
| 5 | `test_prediction_prompt` :: `test_frozen_candidate_identity_and_utf8_bytes_are_preserved`, `present_task_context() missing 3 required positional arguments` | 2 / a104 x 2 homes | stale_test | C2b | F2b | No |
| 6 | :: `test_ordinary_provider_rendering_preserves_actual_operands`, same TypeError | 2 / a104 x 2 | stale_test | C2b | F2b | No |
| 7 | :: `test_provider_frames_retain_model_updates_and_received_lookup`, same TypeError | 4 / a104 x 2 | stale_test | C2b | F2b | No |
| 8 | :: `test_requested_report_facts_and_unknown_lookup_remain_distinct`, `unexpected keyword argument 'lookup_results'` | 2 / a104 x 2 | stale_test | C2b | F2b | No |
| 9 | `test_allocation_exchange` :: `test_runtime_uses_this_parents_named_allocation_receiver` and `test_prediction_exchange` :: `test_runtime_uses_this_parents_named_prediction_receiver`, bare `AssertionError` | 2 + 2 / a104 x 2 homes | stale_test | C2c | F2c | No |
| 10 | `legacy_parent_for_path` missing on `SimpleNamespace`: `test_planning_allocation_task` :: `test_original_runtime_build_selects_this_binding_task` (4), `test_prediction_task` :: `test_runtime_build_selects_declared_private_task` (2), `test_private_resource_tasks` :: `test_actual_workflow_build_selects_exact_task` (10) | 16 / a103 only | test_wiring | C3 | F3 | No |
| 11 | `test_private_resource_tasks` :: `test_source_owned_runtime_planning_repair`, bare `AssertionError` | 30 / a103 (`a103/tests`), 10 resource homes x 3 scenarios | stale_test | C4 | F4 | No |

## C1: instruction dispatch through the axis service (groups 1, 2, 3)

Product code:
- In a102, a103 and a104, every HPC planning, allocation and prediction task has `def instructions(self, context): return self.workflow.services.instructions(self, context)`. Example: `a102/hpc_work_planning/task_decision.py:72-73`. This holds for all 6 HPC homes of each of the three axes.
- The task class declares its private composer as `instruction_composer = staticmethod(instructions)`: `a102/hpc_work_planning/task_decision.py:7`, same in a103; `a104/hpc_work_planning/task.py:21`.
- The real service dispatches on that attribute: `a102/episode_services.py:73-78`, `a103/episode_services.py:67-70`, `a104/episode_services.py:68-73`.
- Real workflows install the real service: `a102/runtime.py:1934`, `a103/runtime.py:1495`, `a104/runtime.py:767`. The private composer is therefore what a real run uses.
- a107 and a110 call the private composer directly instead: `a107/hpc_work_planning/task_decision.py:71-72`. That is the form the helpers assume.
- `a102/hpc_work_planning/ownership.md:54-56` (same text in a103) describes this as a deliberate correction dated 2026-11-12. The code agrees with the note.

Test helpers:
- `tests/hpc_planning_allocation_task_behavior.py:198-203` uses the real `WorkflowServices` only for a104. For every other axis it installs a stub whose `instructions` calls `pytest.fail`. a102 and a103 hit the stub (group 1).
- `tests/hpc_prediction_prompt_behavior.py:30` sets `services.instructions` to the axis-wide `runtime_prompt.instructions`. The task then gets axis-wide text, which contains `pending_child_delivery`, and the assertion at line 174 fails (group 3).
- `tests/hpc_prediction_prompt_behavior.py:114` replaces `services.instructions` with a `pytest.fail` stub (group 2).

Minimal fix:
- F1a: `tests/hpc_planning_allocation_task_behavior.py:198`: change `if self.axis == 'a104':` to `if self.axis in ('a102', 'a103', 'a104'):`.
- F1b: `tests/hpc_prediction_prompt_behavior.py`:
  - after line 30, for axes a102/a103/a104 set `task.workflow.services = self.module('episode_services').WorkflowServices(task.workflow)`;
  - at line 114, for those axes make the axis-wide composer the thing that must not be called (patch `self.module('runtime_prompt').instructions` to `pytest.fail`, with `monkeypatch` so it is undone); keep the current stub for a107/a110.

Verified by running:
- F1a: run 02 (`a103/hpc_work_planning`, 15 passed) and run 09 (`a102/scientific_process/hpc_work_planning/hpc_allocation_execution`, 15 passed).
- F1b: run 03 (`a102/hpc_work_planning/hpc_resource_prediction`, 18 passed) and run 10 (`a103/scientific_process/...`, 18 passed); a104 in run 04.
- The remaining homes were not run. They share the helper and the identical product pattern (checked by grep over all 6 homes x 3 axes).

Side observation (read, not run): `test_private_instructions_preserve_goal_selected_libraries_and_wait_guidance` (helper lines 161-163) passes on a102/a103/a104 but compares the axis composer with itself there, so it does not check the private composer on those axes.

## C2: a104-specific interfaces (groups 4-9)

C2a, provider dispatch (group 4):
- a104 tasks do not look for `complete_with_presentation` on an arbitrary provider. `a104/hpc_work_planning/hpc_resource_prediction/decision_provider.py:9-58` presents only when the provider is the real `ModelConnection`, checked by identity; otherwise it calls `provider.complete`.
- The helper's `SimpleNamespace` provider (`tests/hpc_prediction_prompt_behavior.py:153-155`) therefore reaches its `complete` stub, which fails.
- The planning helper already has the a104 form: `tests/hpc_planning_allocation_task_behavior.py:212-216` uses `a104/tests/provider_dispatch_fixtures.py:27-35` (`controlled_serial_model`). The prediction-prompt helper was not given the same branch.

C2b, renderer signature (groups 5-8):
- In a104 the binding's `decision_prompt_renderer` is `present_task_context(provider, episode_id, role, instructions, context)`, tagged `presentation_protocol = 'episode_context_presentation_v1'`: `a104/hpc_work_planning/hpc_resource_prediction/episode.py:26`, `presentation.py:5` and `:42`.
- `a104/providers.py:686-690` calls it with that 5-argument form. It selects `library.hpc_prompt.render_hpc_prompt` for HPC contexts: `presentation_selection.py:16-18`.
- Other axes declare `render_hpc_prompt(state, instructions, *, lookup_results=())` directly. The helper calls the declared renderer in that 2-argument form at `tests/hpc_prediction_prompt_behavior.py:63, 77, 89, 104, 109`.
- Line 117 also asserts the renderer's module is `<axis>.library.hpc_prompt`. In a104 it is `<home>.presentation`. This is currently hidden behind group 2 and would fail next.

C2c, child receivers (group 9):
- `a104/hpc_work_planning/episode.py:92-103` (same in `a104/scientific_process/hpc_work_planning/episode.py:97-99`) also names receivers for `launch` and `results`.
- Other axes return `None` for `launch`: `a102/hpc_work_planning/episode.py:69-72`.
- The helpers assert `child_report_receiver('launch') is None`: `tests/hpc_allocation_parent_exchange.py:190`, `tests/hpc_prediction_parent_exchange.py:199`.

Minimal fix (all in the shared helpers, a104 branches only):
- F2a: `tests/hpc_prediction_prompt_behavior.py:153`: add the a104 branch that builds the provider with `controlled_serial_model(controlled_config(), tmp_path/'controlled-provider', tmp_path, complete)` and sets `has_session`, as the planning helper does.
- F2b: same file:
  - `renderer()` (lines 33-36) returns `self.module('library.hpc_prompt').render_hpc_prompt` for a104, as the expected text;
  - line 101 passes `binding.decision_prompt_renderer` as `prompt_renderer` (same object as today on the other axes);
  - line 117 expects `binding.__module__.removesuffix('.episode') + '.presentation'` for a104.
- F2c: at the two assertion lines, for a104 assert the receiver's module is `<parent home>.from_child_execution_job_submission`; keep `is None` for the other axes.

Verified by running:
- F1b + F2a + F2b: run 04 (`a104/hpc_work_planning/hpc_resource_prediction`, 18 passed; 10 failed before).
- F2c: runs 05 and 06 (`a104/scientific_process/hpc_work_planning`, 14 and 12 passed).
- Not run: the other a104 copy of each file. Same helper and same product code, by reading.

Retraction of a false lead: I first read `a104/.../presentation.py` with long lines cut off and thought `text_instructions` was not imported. The full import line does import it, and run 04 exercises that path and passes. There is no defect there.

## C3: workflow double lacks `legacy_parent_for_path` (group 10)

- `a103/runtime.py:3952-3954`: `Workflow.build` begins with `self.legacy_parent_for_path(...)` when no request assembler is given. The method is `a103/runtime.py:2122-2131`. No other axis's `runtime.py` has it.
- The tests call `runtime.Workflow.build(<SimpleNamespace>, ...)` with a hand-built double that has no such attribute:
  - `tests/hpc_planning_allocation_task_behavior.py:59-68`
  - `tests/hpc_prediction_task_behavior.py:23-33`
  - `a103/tests/resource_task_checks.py:308-317`
- For the roles under test the method returns `None` (role is in `episode_bindings.roles`), so nothing else changes.

Minimal fix (F3): give the double the real method, bound to itself, before the `build` call.
- Shared helpers, for a103 only: `workflow.legacy_parent_for_path = lambda path: runtime.Workflow.legacy_parent_for_path(workflow, path)`.
- `a103/tests/resource_task_checks.py`, after line 313: `host.legacy_parent_for_path = lambda path: runtime.Workflow.legacy_parent_for_path(host, path)`.
- This uses the real method, not a stub returning `None`.

Verified by running: run 02 (planning, 15 passed), run 07 (`a103/scientific_process/.../hpc_resource_prediction/tests/test_prediction_task.py`, 10 passed), run 08 (all 10 `test_actual_workflow_build_selects_exact_task` params passed). No further missing attribute appeared.

## C4: error label for the annotation root (group 11)

- Failing scenarios: `invalid_private_parent`, `root_missing_launch`, `root_source_missing_launch`, for each of the 10 resource homes. The `scientific_*` counterparts pass.
- Run 01 printed the actual results:
  - `LookupError('episode_child_not_bound:legacy_annotation:launch')`
  - `LookupError('episode_child_not_bound:legacy_annotation:launch_local')`
- The helper expects the same error with `None` in place of `legacy_annotation`: `a103/tests/resource_planning_checks.py:159-160` and `:181`.
- Why the label differs: `a103/episode_bindings.py:450-453` resolves the `annotation` root to the real `LegacyAnnotationEpisode` (`a103/homology_service_setup.py:3-6`), whose `binding_path` is `'legacy_annotation'` (`a103/episode.py:17-18`). The message is built from the parent's binding path at `a103/episode_bindings.py:433`.
- The exception type, the error code and the "no side effects" assertions are unchanged; only the label in the message differs.

Minimal fix (F4): `a103/tests/resource_planning_checks.py:159`: `else 'None'` becomes `else 'legacy_annotation'`; `:181`: `...:None:launch_local` becomes `...:legacy_annotation:launch_local`.

Verified by running: run 08, the 10 `invalid_private_parent` and 40 `*missing_launch` params passed.

Not established: whether the label change was intended as such or is a by-product of introducing the legacy parent objects. Either way the lookup still fails explicitly with the same error type and code.

## Runs

| Run dir (`runs/claude_triage_triage_b_NN`) | Test file | In-memory helper edits | Result |
|---|---|---|---|
| 01 | `a103/tests/test_private_resource_tasks.py` (3 scenarios of the planning-repair test) | none; printed captured results | 30 failed; actual messages recorded |
| 02 | `a103/hpc_work_planning/tests/test_planning_allocation_task.py` | F1a + F3 | 15 passed |
| 03 | `a102/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | F1b | 18 passed |
| 04 | `a104/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | F1b + F2a + F2b | 18 passed |
| 05 | `a104/scientific_process/hpc_work_planning/tests/test_allocation_exchange.py` | F2c | 14 passed |
| 06 | `a104/scientific_process/hpc_work_planning/tests/test_prediction_exchange.py` | F2c | 12 passed |
| 07 | `a103/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | F3 | 10 passed |
| 08 | `a103/tests/test_private_resource_tasks.py` (build test + 5 planning scenarios) | F3 + F4 | 60 passed |
| 09 | `a102/scientific_process/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | F1a + F3 | 15 passed |
| 10 | `a103/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | F1b | 18 passed |

## Fix footprint

Seven test-helper files (five shared, two a103-private), no product files:
- `tests/hpc_planning_allocation_task_behavior.py`
- `tests/hpc_prediction_prompt_behavior.py`
- `tests/hpc_prediction_task_behavior.py`
- `tests/hpc_allocation_parent_exchange.py`
- `tests/hpc_prediction_parent_exchange.py`
- `a103/tests/resource_task_checks.py`
- `a103/tests/resource_planning_checks.py`

The shared-helper edits are explicit per-axis branches, in the style the helpers already use (`if self.axis == 'a104'`, `if self.axis == 'a110'`). They add no fallback or default. None of the fixes changes what evidence is accepted, graded, credited or reported.

## Follow-up: fixes applied on disk and rerun (2026-11-14)

The coordinator authorised editing the seven test-helper files. The edits were applied; the rerun results are appended below once complete.

### Time expectation, written before launching

- 46 small test files (the 20 failing HPC-home files, 17 previously-passing regression files, 5 `test_private_launch` files that reach the edited build test through an adapter, 4 extra regression copies in other home types): 1-8 s of pytest each in the earlier run plus about 3 s of launcher overhead, so about 5-7 minutes in total, run one after another.
- `a103/tests/test_private_resource_tasks.py` (1490 tests): 746 s of test time in the earlier run, so about 13-14 minutes.
- Expected total: about 20 minutes of wall time, all in slot `triage_b`, one file at a time.

### Result

- All 122 failures of this cluster now pass, in every home that had one: 21 test files, 0 failures left.
- No regression: the 21 previously-passing files rerun as checks (a102, a103, a104, a107, a110) have the same counts as before.
- Side effect outside this cluster: the 4 a103 `test_private_launch` files each lose one failure (`test_actual_runtime_build_selects_private_launch_task`, the same `legacy_parent_for_path` cause), because they call the edited build test through an adapter.
- Nothing in this cluster still fails.
- The 5 `test_private_launch` files were run twice:
  - At 09:43 (runs 52-56) each still had 5 failures, the same tests and messages as before, from another cluster's helper `tests/hpc_launch_task_checks.py` (not one of the seven files).
  - At 09:48 another agent edited that helper. Rerun at 10:02 against the working tree as it then stood (runs 58-62), all five files pass 27 / 0. That shows my edit and theirs work together; the remaining 5 fixes per file are theirs, not mine.
- Other agents were editing other test files (and `a103/homology_results.py`) in the same working tree while these reruns ran. None of the seven files here was touched by anyone else: their diff contains only the edits described in this report.

### Two places where the on-disk edit differs from what was run in memory

- `tests/hpc_planning_allocation_task_behavior.py`, build test: the a103 branch is selected by the runtime module name (`runtime.__name__ == '...root.a103.runtime'`), not by `self.axis`. Other test files call this test with an adapter object that has no `axis` (`tests/hpc_launch_task_checks.py:160-161` and four a104 test files); `self.axis` there would have raised `AttributeError` and broken tests that pass today. Still an explicit a103-only branch.
- `tests/hpc_prediction_prompt_behavior.py`, `test_private_composer_omits_unavailable_child_repair`: the axis-wide `runtime_prompt.instructions` is replaced with `monkeypatch.setattr`, so it is restored after the test. The in-memory version assigned it without restoring, which would have leaked into later tests in the same process.

Both were rerun on disk in every affected home (table below).

### Not covered

- The four a104 files that call the edited build test through an adapter (`a104/tests/test_a104_non_hpc_launch.py`, `test_a104_native_execution_private.py`, `test_a104_results_preservation.py`, `test_a104_non_hpc_results_preservation.py`) were not rerun: `a104/tests` has no baseline in run `_02` and is being run by another window. By reading, the new branch is not taken for a104, so their code path is unchanged.

### `git diff --stat` for the seven files

```
 .../root/a103/tests/resource_planning_checks.py    |  6 ++++--
 .../root/a103/tests/resource_task_checks.py        |  1 +
 .../root/tests/hpc_allocation_parent_exchange.py   |  6 +++++-
 .../tests/hpc_planning_allocation_task_behavior.py |  6 +++++-
 .../root/tests/hpc_prediction_parent_exchange.py   |  6 +++++-
 .../root/tests/hpc_prediction_prompt_behavior.py   | 25 +++++++++++++++++-----
 .../root/tests/hpc_prediction_task_behavior.py     |  3 +++
 7 files changed, 43 insertions(+), 10 deletions(-)
```

This work changed no other tracked file and committed nothing. `git status` now lists many other modified files; those are other agents' edits.

### Time: expected versus actual

| Part | Expected | Actual |
|---|---|---|
| 46 small files | 5-7 min | 3 min (181 s) |
| `a103/tests/test_private_resource_tasks.py` | 13-14 min | 17 min wall (pytest 933 s against 746 s in the earlier run; other windows were running tests at the same time) |
| Total | about 20 min | about 21 min |

### Before and after, per test file

"Before" is run `runs/claude_tests_leaf_up_20261114_02`; "after" is `runs/claude_triage_triage_b_NN/junit.xml`. Counts are passed / failed. Paths are relative to `gene_annotation_episode/episodic_workflow/root/`.

| Run NN | Why rerun | Test file | Before | After |
|---|---|---|---|---|
| 11 | failed before | `a102/hpc_work_planning/tests/test_planning_allocation_task.py` | 11 / 4 | 15 / 0 |
| 12 | failed before | `a102/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | 11 / 4 | 15 / 0 |
| 13 | failed before | `a102/scientific_process/hpc_work_planning/tests/test_planning_allocation_task.py` | 11 / 4 | 15 / 0 |
| 14 | failed before | `a102/scientific_process/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | 11 / 4 | 15 / 0 |
| 15 | failed before | `a103/hpc_work_planning/tests/test_planning_allocation_task.py` | 10 / 5 | 15 / 0 |
| 16 | failed before | `a103/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | 10 / 5 | 15 / 0 |
| 17 | failed before | `a103/scientific_process/hpc_work_planning/tests/test_planning_allocation_task.py` | 10 / 5 | 15 / 0 |
| 18 | failed before | `a103/scientific_process/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | 10 / 5 | 15 / 0 |
| 19 | failed before | `a102/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 13 / 5 | 18 / 0 |
| 20 | failed before | `a102/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 13 / 5 | 18 / 0 |
| 21 | failed before | `a103/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 13 / 5 | 18 / 0 |
| 22 | failed before | `a103/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 13 / 5 | 18 / 0 |
| 23 | failed before | `a104/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 8 / 10 | 18 / 0 |
| 24 | failed before | `a104/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 8 / 10 | 18 / 0 |
| 25 | failed before | `a103/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 9 / 1 | 10 / 0 |
| 26 | failed before | `a103/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 9 / 1 | 10 / 0 |
| 27 | failed before | `a104/hpc_work_planning/tests/test_allocation_exchange.py` | 13 / 1 | 14 / 0 |
| 28 | failed before | `a104/hpc_work_planning/tests/test_prediction_exchange.py` | 11 / 1 | 12 / 0 |
| 29 | failed before | `a104/scientific_process/hpc_work_planning/tests/test_allocation_exchange.py` | 13 / 1 | 14 / 0 |
| 30 | failed before | `a104/scientific_process/hpc_work_planning/tests/test_prediction_exchange.py` | 11 / 1 | 12 / 0 |
| 31 | regression check | `a104/hpc_work_planning/tests/test_planning_allocation_task.py` | 15 / 0 | 15 / 0 |
| 32 | regression check | `a107/hpc_work_planning/tests/test_planning_allocation_task.py` | 15 / 0 | 15 / 0 |
| 33 | regression check | `a110/hpc_work_planning/tests/test_planning_allocation_task.py` | 15 / 0 | 15 / 0 |
| 34 | regression check | `a107/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 18 / 0 | 18 / 0 |
| 35 | regression check | `a110/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 18 / 0 | 18 / 0 |
| 36 | regression check | `a102/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 10 / 0 | 10 / 0 |
| 37 | regression check | `a104/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 10 / 0 | 10 / 0 |
| 38 | regression check | `a107/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 10 / 0 | 10 / 0 |
| 39 | regression check | `a110/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_task.py` | 10 / 0 | 10 / 0 |
| 40 | regression check | `a102/hpc_work_planning/tests/test_allocation_exchange.py` | 14 / 0 | 14 / 0 |
| 41 | regression check | `a102/hpc_work_planning/tests/test_prediction_exchange.py` | 12 / 0 | 12 / 0 |
| 42 | regression check | `a103/hpc_work_planning/tests/test_allocation_exchange.py` | 14 / 0 | 14 / 0 |
| 43 | regression check | `a103/hpc_work_planning/tests/test_prediction_exchange.py` | 12 / 0 | 12 / 0 |
| 44 | regression check | `a107/hpc_work_planning/tests/test_allocation_exchange.py` | 14 / 0 | 14 / 0 |
| 45 | regression check | `a107/hpc_work_planning/tests/test_prediction_exchange.py` | 12 / 0 | 12 / 0 |
| 46 | regression check | `a110/hpc_work_planning/tests/test_allocation_exchange.py` | 14 / 0 | 14 / 0 |
| 47 | regression check | `a110/hpc_work_planning/tests/test_prediction_exchange.py` | 12 / 0 | 12 / 0 |
| 48 | regression check | `a104/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | 15 / 0 | 15 / 0 |
| 49 | regression check | `a107/hpc_work_planning/hpc_allocation_execution/tests/test_planning_allocation_task.py` | 15 / 0 | 15 / 0 |
| 50 | regression check | `a110/scientific_process/hpc_work_planning/tests/test_planning_allocation_task.py` | 15 / 0 | 15 / 0 |
| 51 | regression check | `a107/scientific_process/hpc_work_planning/hpc_resource_prediction/tests/test_prediction_prompt.py` | 18 / 0 | 18 / 0 |
| 52 | adapter caller | `a103/hpc_work_planning/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 22 / 5 |
| 53 | adapter caller | `a103/hpc_work_planning/hpc_allocation_execution/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 22 / 5 |
| 54 | adapter caller | `a103/scientific_process/hpc_work_planning/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 22 / 5 |
| 55 | adapter caller | `a103/scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 22 / 5 |
| 56 | adapter caller | `a102/hpc_work_planning/execution_job_submission/tests/test_private_launch.py` | 22 / 5 | 22 / 5 |
| 57 | failed before | `a103/tests/test_private_resource_tasks.py` | 1450 / 40 | 1490 / 0 |
| | total | 47 files | 2062 / 151 | 2188 / 25 |
| 58 | adapter caller, second run at 10:02 | `a103/hpc_work_planning/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 27 / 0 |
| 59 | adapter caller, second run at 10:02 | `a103/hpc_work_planning/hpc_allocation_execution/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 27 / 0 |
| 60 | adapter caller, second run at 10:02 | `a103/scientific_process/hpc_work_planning/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 27 / 0 |
| 61 | adapter caller, second run at 10:02 | `a103/scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/tests/test_private_launch.py` | 21 / 6 | 27 / 0 |
| 62 | adapter caller, second run at 10:02 | `a102/hpc_work_planning/execution_job_submission/tests/test_private_launch.py` | 22 / 5 | 27 / 0 |

The total row counts runs 11-57 only. In it, the 151 failures before are this cluster's 122 plus 29 in the launch files; the 25 after are all in the launch files as of 09:43 and are gone in runs 58-62.
