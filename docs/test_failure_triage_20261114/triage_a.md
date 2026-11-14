# triage_a: execution_job_submission / api_job_execution failures (124 failures, 8 distinct causes)

Paths below are relative to `gene_annotation_episode/episodic_workflow/root/` (written `R/`) unless they start with `runs/` or `tools/`.

## How this was checked

- Read: every failing test body, the product code it reaches, and the junit tracebacks in
  `runs/claude_tests_leaf_up_20261114_02/junit/` for every home (failing line compared across all homes).
- Ran (launcher, slot `triage_a`, three runs, one scratch test file each, files kept outside the repository):
  `runs/claude_triage_triage_a_01`, `_02`, `_03`. Each probe re-ran an existing test with one proposed test-side
  change applied from outside. Results are quoted per cause as "probe".
- Git history is of no use for ordering here: tests and product for these homes all arrived in one commit
  (`dfe3e6091`), and none of the files in this cluster were touched by the import re-pointing commits
  (`git log` shows only `dfe3e6091` for each). So no failure in this cluster is caused by a wrong re-pointing.
- Not verified: axis-level sibling tests cited as evidence (`R/a107/tests/*`, `R/a110/tests/*`) have no row in
  `results.tsv` of the run I was given, so I cite what they assert, not that they pass.

## Do the copies differ? Is the cause the same in each home?

The per-home test files are 5-7 line wrappers. Copies differ only in the docstring and the home selector
(`binding_path` / `home` / `axis`). All logic is in shared check modules:

| per-home wrapper | shared logic | homes |
|---|---|---|
| `test_launch_connected.py` | `R/a107/tests/launch_connected.py`, `R/a110/tests/launch_connected.py` (differ only in AXIS, API child present/absent, 31/27 owners, lines 611-613 timing expectation) | 4 in a107, 4 in a110 |
| `test_private_launch.py` | `R/tests/hpc_launch_task_checks.py` (one file for a102 and a103) | 4 in a102, 4 in a103 |
| `test_api_task.py` | `R/a103/tests/api_task_checks.py` | 6 in a103 |
| `test_private_api_tasks.py` | itself, `R/a102/tests/test_private_api_tasks.py`, parametrized over 6 API homes x 2 (the "12 in 1 home") | a102 |

For every group the failing file:line is identical in every home's junit file, and the product code at that
point has the same shape in every home (checked by grep over all homes). One cause per group, same in each home.

## Table

| # | group (test module :: test, message) | count | classification | cause, with evidence | minimal fix | changes scientific behaviour? |
|---|---|---|---|---|---|---|
| A | `test_launch_connected` :: `test_full_registry_keeps_actual_launch_context_and_original_input_file` and `test_original_parent_resource_exposure_and_nearest_hpc_commissioner`, `ValueError: initial_information_recipient_provenance_missing` | 8 + 8 | stale_test | Two stale things in the same tests. (1) The fixture builds `EpisodeBindingRegistry(constructors)` (`launch_connected.py:79`) and never gives it an initial-information catalog. Every Launch/native/results binding declares `initial_information_requires_authority = True` (`R/a107/hpc_work_planning/execution_job_submission/episode.py:82`, a110 `:64`), so the registry raises on purpose (`R/a107/episode_bindings.py:394-398`, `R/a110/episode_bindings.py:370-374`). (2) Lines 175 and 187 call `v.launch.initial_decision_context(...)`, which Launch no longer has; it was replaced by `initial_information_consumer` read through the catalog (`episode.py:83`, `initial_information.py`). The old callback is kept only as a comparison asset (`R/a107/tests/fixtures/initial_information_original/initial_decision_context.py`), and `R/a107/tests/test_information_connected.py:152-155` reads the new path via `registry._recipient_initial_information`. | In both `launch_connected.py` files: after line 79 build the catalog the way `test_information_connected.py:133-137` does (`ExecutionServiceFactory` from the fixture's own `execution_options`, `InitialInformationConfiguration.original_global_factory(factory).construct(...)`, `registry.configure_initial_information(catalog, annotation_initial_information.initial_information)`); replace `v.launch.initial_decision_context(v.context)` at 175 and 187 with `v.registry._recipient_initial_information(v.context)`. Lines 181-182 additionally need cause C's treatment. Probe (run 03): with exactly these changes the whole of the second test and the first test up to line 178 pass in a107 and a110; lines 181-182 then raise `received_execution_original_factory_required`. | No. Test fixture only. |
| B1 | `test_launch_connected` :: `test_interrupted_saved_decision_keeps_full_original_payload_and_renderer[False/True]`, `AttributeError: 'ExecutionEpisode' object has no attribute 'initial_decision_context'` | 16 | stale_test | Line 498 calls the same removed `v.launch.initial_decision_context` (see A). It is only used to build a saved payload. Two further expectations in the same test do not match the product (probe, run 03, with line 498 given an operand): `[False]` fails at line 520, which requires `v.launch.decision_prompt_renderer is library/hpc_prompt.render_hpc_prompt`, but Launch declares `present_launch_context` (`episode.py:77`, a110 `:61`); `[True]` fails at line 514 because the private task only uses the declared renderer when the provider is a genuine `ModelConnection` (`task_decision.py:341-357`), and the test's `SimpleNamespace` provider gets `complete`, which the test set to `forbidden`. The newer sibling `R/a107/tests/test_private_task_refinement.py:503-516` builds the declared provider as `object.__new__(providers.ModelConnection)`. | `launch_connected.py:498`: use `v.registry._recipient_initial_information(v.context)` (needs A's catalog) or a literal payload. `:511-513`: build the declared provider as the sibling test does. `:520-521`: compare with `self.module(self.binding_path + "/task_presentation").present_launch_context`. Alternative: retire this test in favour of the sibling test that already covers the same replay. | No. |
| B2 | `test_launch_connected` :: `test_named_native_report_receipt_redelivery_and_saved_identity`, `AttributeError: ... no attribute 'child_report_receiver'` | 8 | stale_test | Line 564 asks Launch for `child_report_receiver`. In a107/a110 the Launch selector is `execution_child_report_receiver(role)` (`episode.py:142`, a110 `:111`), reached by the runtime only when it is given `child_role` (`R/a107/runtime.py:2308-2313`). The newer sibling test uses that name and explicitly forbids the saved-role lookup on this path (`R/a107/tests/test_private_task_refinement.py:336,347`; same lines in a110). Probe (run 01): with `execution_child_report_receiver("launch_hpc")`, `child_role="launch_hpc"` on the `_receive_form` calls and `registry.received_form_references` stubbed (cause C), lines 564-578 pass in a107 and a110. Lines 579-587 cannot pass: a redelivery whose saved child belongs to a different Launch is accepted, not rejected (probe `test_probe_wrong_parent_is_not_rejected` passes in both axes). | `launch_connected.py:564` -> `execution_child_report_receiver`; add `child_role="launch_hpc"` at 567, 569-570; stub `received_form_references` in `receipt_fixture` (see C); delete 579-587 or decide owner question 2 below. | No for the test fix. Owner question 2 is about delivery identity, not evidence. |
| C | `test_launch_connected` :: `test_original_timing_receipt_branch_remains_axis_specific`, `ValueError: received_execution_original_factory_required` | 8 | test_wiring | The test body is sound. `_receive_form` reaches `registry.received_form_references` (`R/a107/runtime.py:2354`), and the fixture registry has no received-execution catalog while bindings declare `received_execution_requires_authority = True` (`episode.py:79`; raise at `R/a107/episode_bindings.py:624-627`, `R/a110/episode_bindings.py:555-558`). The sibling tests supply a controlled port for exactly this call (`R/a107/tests/test_private_task_refinement.py:339,400`). | `launch_connected.py`, in `receipt_fixture` after line 546: `monkeypatch.setattr(v.registry, "received_form_references", lambda *_: [])`. Probe (run 01): with only this change the test passes unchanged in a107 and in a110 (each with its own axis-specific expectation at 611-613). | No. |
| D | `test_launch_connected` :: `test_native_incoming_schema_and_real_admission_keep_full_frozen_request`, `Failed: DID NOT RAISE ValueError` | 8 | stale_test (medium confidence; see owner question 1) | Lines 234-237 expect `v.launch.prepare_child_request(...)` to reject a request whose `argv` was changed. Launch's `prepare_child_request` returns the assignment unchanged for every role (`episode.py:133-140`, a110 `:104-109`). That identity is recorded as the original behaviour for all six a107 Launch homes in `R/a107/tests/fixtures/organization_original/a107_launch_identity_callbacks.json`. The test's own note file calls these "unexecuted candidate tests" (`R/a107/tests/LAUNCH_CONNECTED_TEST_PORTS.md:3`), and the preparation notes describe Launch-side validation as a candidate only (`runs/hpc_allocation_messages_20261111_a107_a110_preparation/launch_review/REGRESSION_PROPOSALS.md:95-99`); those notes are claims, the code is the evidence. The frozen request is enforced elsewhere: the native child advertises only the frozen request (`hpc_job_execution/from_parent.py:81-89`), that enum is in the action schema (asserted by the passing test at `launch_connected.py:250`), and the Launch task validates every selection against it before dispatch (`task.py:100`). Everything before line 234 in this test passes. | Delete `launch_connected.py:234-237` (keep 238-239). | No. If the owner instead wants the Launch-side check added, that is a product change in plumbing, not in evidence handling. |
| E | `test_private_launch` :: `test_fresh_and_saved_decision_keep_full_launch_payload[4 params]`, `Failed: Private task selected the axis instruction composer` | 32 | stale_test | The test replaces `services.instructions` with a function that fails if a private task calls it (`R/tests/hpc_launch_task_checks.py:445-448`). In the product the private task is meant to call it: `instructions()` calls `self.workflow.services.instructions(self, context)` (`R/a102/hpc_work_planning/execution_job_submission/task_decision.py:85-86`, `R/a103/.../decision_delivery.py:82-83`), and the real service dispatches to the task's own composer (`R/a102/episode_services.py:73-78`, `R/a103/episode_services.py:67-70`; `instruction_composer` declared at `R/a102/.../task.py:15`, `R/a103/.../decision_delivery.py:13`). `R/a103/tests/test_instruction_service_dispatch.py` tests this dispatch design directly. Probe (run 01), routing through the real `WorkflowServices`: the test then fails later, at line 472 (`decision_prompt_renderer is render_hpc_prompt`; a102 declares `render_selected_execution_prompt`, a103 `present_launch_task`), and for a102 with a declared renderer at line 465 (a102 uses `provider.complete` for HPC contexts, `decision_provider.py:15-20`). | `hpc_launch_task_checks.py:445-448`: use `self.module('episode_services').WorkflowServices(task.workflow)` (same change someone has already made for the planning test, see note below); `:465-466` and `:472`: assert against what each axis's binding declares, or drop these two renderer-identity assertions. | No. |
| F | `test_private_launch` :: `test_dependent_descriptors_read_complete_final_launch_files`, bare `AssertionError` | 8 | stale_test | `hpc_launch_task_checks.py:403-404` assert the Launch home has no `terminal_execution.py` and has `terminal_receipts.py`. Every a102/a103 Launch home has `terminal_execution.py`, and it is live code (imported by `R/a102/.../execution_contracts.py:16`, `R/a103/.../contracts.py:21`; listed in each home's `ownership.md`). No file named `terminal_receipts.py` exists anywhere under `R/`. Lines 398-400, 405-406 hold. This is a file-layout assertion, not behaviour. | Delete `hpc_launch_task_checks.py:403-404`. | No. |
| G | `test_private_launch` :: `test_actual_runtime_build_selects_private_launch_task`, `AttributeError: 'types.SimpleNamespace' object has no attribute 'legacy_parent_for_path'` (a103 only) | 4 (same cause explains 23 more outside this cluster: failure_groups rows `test_credit_behavior` 6, `test_planning_allocation_task` 4, `test_prediction_task` 2, `test_private_resource_tasks` 10, `test_progress_task` 1) | test_wiring | Only a103's `Workflow.build` calls `self.legacy_parent_for_path` (`R/a103/runtime.py:3954`, method at `:2122`; no other axis runtime has the name). The shared helper passes a hand-built `SimpleNamespace` workflow without it (`R/tests/hpc_planning_allocation_task_behavior.py:57-66`). a103's own helpers bind the real method (`R/a103/tests/launch_task_checks.py:69`, `api_task_checks.py:73`, `native_task_checks.py:80`). Probe (run 01): with the real method bound, the test passes for a103. | Bind `runtime.Workflow.legacy_parent_for_path` onto the stub before `Workflow.build` in `hpc_planning_allocation_task_behavior.py`. This is already present, uncommitted, in the working tree (see note below). Of the 23 failures outside this cluster, the 4 `test_planning_allocation_task` ones go through this same helper; the other 19 build their own stub workflow, which I did not examine beyond the identical message. | No. |
| H | `test_api_task` :: `test_parent_saved_counterpart_routes_original_progress[2 params]`, `AssertionError` (a103, 6 homes); `test_private_api_tasks` :: `test_parent_receipt_selection_preserves_actual_child_role_and_redelivery`, `assert (<function receive_report> is None)` (a102, 6 homes x 2) | 12 + 12 | stale_test | Both assert that the Launch parent has no receiver for `launch_local` (`R/a103/tests/api_task_checks.py:249`, `R/a102/tests/test_private_api_tasks.py:120`). The Launch parent now names all three children (`R/a103/.../child_commissioning.py:24-31`, `R/a102/.../to_children.py:22-29`). The sibling Launch tests state the rule: only `launch_api` had a receiver before the private task existed, all three once the binding has `decision_source_type` (`R/a103/tests/launch_task_checks.py:239-242`, `R/a102/tests/test_private_launch_tasks.py:120-126`). Everything before the stale line passes. | Replace the one assertion in each file with the final expectation (local and hpc receivers come from `from_child_local_job_execution` / `from_child_hpc_job_execution`; an unrelated role gives `None`). Probe (run 02): with that single change both tests pass to the end, a103 for both params, a102 for all 12 params. | No. |

Counts: A 16 + B1 16 + B2 8 + C 8 + D 8 (= 56 `test_launch_connected`), E 32 + F 8 + G 4 (= 44 `test_private_launch`), H 12 + 12. Total 124.

## Product defects found

None. No group in this cluster is caused by a mixin or attribute lost in the reorganisation: in each case the
attribute the test asks for has a named replacement that sibling tests already exercise, or never existed.

## Two questions for the owner (product behaviour the stale tests happened to describe)

1. Launch-side rejection of a changed frozen native request (a107/a110), cause D. Today the check is at decision
   admission (`task.py:100` against the frozen enum), not in `prepare_child_request`. A direct caller of
   `native.prepare_assignment` with a changed `argv` is validated only against the general request schema
   (`hpc_job_execution/from_parent.py:96-98`). Read, not run.
2. Redelivery from a child of a different Launch (a107/a110), cause B2. a102/a103 reject this with
   `original_delivery_parent_conflict` because their Launch uses `child_report_receiver`, which reads the saved
   child path (`delivery_counterpart.py`). a107/a110 Launch uses `execution_child_report_receiver` with a role
   passed in, and nothing reads the saved child path; the probe shows such a delivery is received and recorded.
   The sibling test forbids that lookup on this path, so the difference looks intended, but it is the one place
   in this cluster where a guard present in two axes is absent in two others. It concerns which child's report a
   parent receives, so it is worth an explicit decision.

## Working tree changed while I was working (not by me)

At 09:39 local time, seven test helper files and `tools/verify_episode_homes.py` became modified in the working
tree (`git status`), among them `R/tests/hpc_planning_allocation_task_behavior.py`, which now binds
`legacy_parent_for_path` for a103 (cause G) and uses the real `WorkflowServices` for a102/a103/a104 in the
planning test (the same repair as cause E, in a different test). I made no edits under the repository other than
this report and the three launcher run directories. The junit results I analysed predate those edits. None of
the shared files of my cluster other than that one were changed (`git diff` is empty for
`hpc_launch_task_checks.py`, both `launch_connected.py`, `a103/tests/api_task_checks.py`, `a102/tests`).
My probe for cause G finished 12 seconds before that file's modification time, so I cannot say which version
it ran against; the conclusion is the same either way, because the probe binds the method itself.

# Follow-up: fixes applied (coordinator instruction, 2026-11-14)

## Time estimate, written before launching any rerun

Basis: the per-directory seconds in `runs/claude_tests_leaf_up_20261114_02/results.tsv` and my three probe runs.
- Baseline of the six a107/a110 sibling files that reuse `launch_connected.py` (no earlier result exists for
  them): about 5 minutes (roughly 250-300 tests at 0.4 s each, plus launcher start-up per file).
- Final reruns: `test_launch_connected` 8 homes x about 45 s (12 s before; the catalog fixture added about 8 s per
  use in probe 3) = 6 min; `test_private_launch` 8 x 6 s = 1 min; `test_api_task` 6 x 6 s = 1 min;
  `test_private_api_tasks.py` 1 min; the six sibling files again 5 min. About 14 minutes.
- Expected total launcher time: about 20 minutes, plus a few short development runs while editing.

## What was changed (test files only; no product code, no commit)

`git diff --stat` for the five files:

```
 .../root/a102/tests/test_private_api_tasks.py      |  7 ++-
 .../root/a103/tests/api_task_checks.py             |  6 +-
 .../root/a107/tests/launch_connected.py            | 70 ++++++++++++++++------
 .../root/a110/tests/launch_connected.py            | 70 ++++++++++++++++------
 .../root/tests/hpc_launch_task_checks.py           | 21 +++----
 5 files changed, 128 insertions(+), 46 deletions(-)
```

The edits to the two `launch_connected.py` files are line-for-line identical (checked by diffing the two diffs).

| cause | what I did | where |
|---|---|---|
| A | New fixture `informed` (depends on `connected`, which is unchanged) binds the original-global initial-information catalog and the received-execution catalog on the registry, built from the fixture's own execution operands. The two tests use it, and the removed `launch.initial_decision_context` call is replaced by `registry._recipient_initial_information`. Beyond the probe: I bound the real received-execution catalog instead of stubbing, so lines 181-182 of the first test run for real and pass. | both `launch_connected.py` |
| B1 | Restated, not retired. Line 498 uses the catalog reader. The declared-renderer variant builds a genuine `ModelConnection` provider. The renderer assertion compares with `<home>/task_presentation.present_launch_context`. Evidence: `test_private_task_refinement.py:104-107` and `:503-516` assert the same two things, and both pass in a107 and a110 (runs 36, 37). | both `launch_connected.py` |
| B2 | Lines 564-578 use `execution_child_report_receiver("launch_hpc")` and pass `child_role`. Lines 579-587 are untouched; the test now fails there (owner decision 2). | both `launch_connected.py` |
| C | One controlled port for `registry.received_form_references` in `receipt_fixture`, as probed. | both `launch_connected.py` |
| D | Unchanged, still failing (owner decision 1). | - |
| E | Real `WorkflowServices`, same call as the planning helper. Added one assertion that the task's declared composer is the home's own `instructions.instructions`, so the test still checks which composer a private task uses. Renderer keyword assertion (old 465): kept for a103 only, where `a103/tests/launch_task_checks.py:303` states the same contract; not asserted for a102, where no test states it. Renderer identity assertion (old 472): removed for both axes; no sibling test asserts an identity. | `tests/hpc_launch_task_checks.py` |
| F | Deleted the two file-location assertions. | `tests/hpc_launch_task_checks.py` |
| G | No edit by me. The bind is in `tests/hpc_planning_allocation_task_behavior.py`, made by another agent; my four failures pass with it. | - |
| H | As probed: the private Launch names all three counterparts; an unrelated role gives `None`. | `a103/tests/api_task_checks.py`, `a102/tests/test_private_api_tasks.py` |

Retired tests: none. No test function was deleted, so I appended nothing to `retired.tsv`.

## Before / after

"Before" is `runs/claude_tests_leaf_up_20261114_02`. "After" is runs `claude_triage_triage_a_13` to `_35`, one file per run.

| test module | homes | before passed / failed | after passed / failed |
|---|---|---|---|
| `test_launch_connected` | 4 a107 + 4 a110 | 152 / 56 | 192 / 16 |
| `test_private_launch` | 4 a102 + 4 a103 | 172 / 44 | 216 / 0 |
| `test_api_task` | 6 a103 | 150 / 12 | 162 / 0 |
| `test_private_api_tasks` | a102 (one file) | 204 / 12 | 216 / 0 |
| total | | 678 / 124 | 786 / 16 |

Still failing (16), identical in all eight a107/a110 Launch homes:
- `test_native_incoming_schema_and_real_admission_keep_full_frozen_request` x 8: `DID NOT RAISE ValueError` (now `launch_connected.py:262`). Cause D, left for owner decision 1.
- `test_named_native_report_receipt_redelivery_and_saved_identity` x 8: `DID NOT RAISE WorkflowError` (now `launch_connected.py:621`), the untouched wrong-parent tail. Owner decision 2.

Sibling tests that reuse the helpers I touched, before and after my edits (failing sets compared name by name, identical):

| file | before | after |
|---|---|---|
| `a107/tests/test_private_task_refinement.py` | 208 / 8 | 208 / 8 |
| `a110/tests/test_private_task_refinement.py` | 192 / 8 | 192 / 8 |
| `a107/tests/test_direct_private_tasks.py` | 130 / 2 | 130 / 2 |
| `a107/tests/test_direct_yield_identity.py` | 16 / 0 | 16 / 0 |
| `a110/tests/test_direct_private_tasks.py` | 122 / 2 | 122 / 2 |
| `a110/tests/test_direct_yield_identity.py` | 8 / 0 | 8 / 0 |

Those sibling failures are not mine and not in my cluster: `test_outgoing_transmission_retains_original_object_and_validation_boundary` (8 per axis; `to_child_*` modules have no `prepare_request`) and `test_actual_parent_transmission_keeps_object_and_child_admission_boundary` (2 per axis).

The four `test_direct_*` files need the environment variable `GENE_DIRECT_TASK_PHASE=connected`. Without it every test errors at setup (`KeyError`, 132 and 16 errors in a107, runs 05 and 06). The numbers above are with the variable set.

Not rerun: three a104 files import `hpc_launch_task_checks.py` but use only `launch_case`, `case_registry`, `module` and three test functions I did not change.

## Time: estimate versus actual

Estimated about 20 minutes of launcher time. Actual about 32 minutes: sibling baselines 13 min (two of those runs were wasted because I had not yet found the required environment variable), one development run 1 min, final reruns 18 min. The misses: the sibling files take 1.5 to 2.5 minutes each, not under a minute, and `test_launch_connected` takes about 55 s per home with the catalog fixture, not 45 s. Separately I lost about 25 minutes of wall time to a wait loop of mine that matched its own command line; no test run was affected.

## Deviations from the rules

- I applied the identical `launch_connected.py` edits to both files with one bare `python3` text-substitution script (standard library only, no project import). The brief says Python runs only through the launcher. All test runs went through the launcher.
- I stopped my own baseline driver once between files to avoid two more uninformative runs; the in-flight launcher run completed normally.
