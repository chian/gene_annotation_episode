# Wait-target repair for coordinator review

Implemented only the reviewed021 workload. The full literature goal remains active/incomplete. No actual017 restart, model call, scientific paper read, real-state edit or old pin/history change was performed.

## Final changed files and consumer path

- `method_loop/durable.py:165`: `EventTargetError` remains a ValueError subtype, with four constrained codes and exact affected references. `:706` resolves existing commission/native identity without calling status; a missing ordinary target becomes `unknown_wait_target`, and unsupported native event becomes `unsupported_wait_event`. Generic `_row` remains unchanged for all its other consumers. `:724` exposes pure `validate_event_targets`; it copies already shape-validated conditions and reads registrations only. Actual backend wait dispatch uses the same target resolution, so an invalid later member cannot be hidden by an earlier valid target or an elapsed selected timer.
- `gene_annotation_episode/runtime.py:148`: deterministic feedback supplies status/category/code/affected_refs/detail. `DecisionSource.apply_response:1291` records a rejected new wait selection with `category=wait_target`; no action leaf, selected wait, credit or observation is created. `Workflow.validate_wait_selection:2025` preserves native custody validation, then validates ordinary/native backend identity. Missing native binding retains its existing meaning and exact offending reference.
- `runtime.py:3165`: exact previously recorded selections bypass selection-time validation. This preserves completed replay and permits an unfinished restored action, selected outside apply_response, to reach its ordinary dispatch path. `DecisionSource.execute:1369` catches ONLY EventTargetError from selected wait dispatch and records a failed result with specific feedback. It does not catch unrelated KeyError, storage error or arbitrary ValueError. Existing failed-result handling saves source feedback/checkpoint, skips credit/receipt/completion staging, raises ActionFailure, and lets FeedbackEpisode reuse the unchanged controller decision. The episode then owns the next selection.
- `gene_annotation_episode/native_event_information.py:391`: existing not-visible/unsupported-event failures now use the ValueError subtype with affected_refs. Their existing detail strings remain unchanged. `_authenticate`, scope, original request/reservation/registry checks, assigned/received visibility and typed-report/cursor validation are unchanged. No immediate-parent-only restriction was added; a legitimately received target from another owner remains valid.
- NEW `tests/test_wait_target_failures.py`:17 final focused tests cover the complete change path. No historical test was edited. `waiting.py`, completion ledger, journal, decision renderers, generic Episode/controller runtime and estimator formulas are unchanged.

The original decision condition, timer, wait identity, estimate snapshot and attempted timing survive failed incomplete-wait restoration unchanged. The outer ordinary action may record the actual new repair-dispatch interval; its original interval remains intact. Failed action credit stays null and no completion slot or yield sample is supplied. Completed saved waits retain their outcome, condition, wake, timing and estimate, bypass validation/provider resampling, and add no observation. Native publication/receipt custody remains distinct from scientific success. No target, timer, retry, cancellation, scheduler or continuation decision is synthesized.

The six reviewed check groups are represented as follows:

1. Unknown/source handles and mixed valid/invalid sets, including expired selected timers: exact failure code/ref, validation has no status poll or backend event change; missing native binding also returns specific feedback.
2. Ordinary and durable new rejected selection→episode-chosen valid wait; persisted unfinished selected wait→recorded failed outcome→episode repair; original snapshot/timing and null failed credit; zero failed observations/slots; final closed replay has no new provider call/sample.
3. Existing bound native visibility/unsupported-kind rejection with exact refs; actual native-binding ordinary-loop rejection/repair; received targets from a different owner remain allowed.
4. Valid selected execution/native controls retain identity/cursor/receipt bytes; completed WaitStore event/replay controls; direct completed Workflow wait replay forbids all validation, re-estimation and backend dispatch while comparing original persisted fields.
5. Durable selected-set notifications and reconsideration/cancellation control; persisted raised wait retains prior measurement and request exactly. This patch introduces no lifecycle/descendant cancellation code. A postpatch live subprocess-descendant survival experiment was not run; preserved control here uses an existing pending commission and native exit receipts, with no native command dispatch.
6. Specific failure code/ref reaches both literature child and reference-parent STEERING with their complete recurring TASK intact. No prompt template or report composer changed.

## Results and precise limits

Final focused suite: **17 passed in59.86s** (`FIX_FINAL_FOCUSED_TESTS_004.xml`). This includes both ordinary/durable selection rejection, real Store/backend state, actual method_loop failure repair, durable reconstruction, and complete-outcome bypass. Providers/controllers and scientific input are explicitly synthetic.

Targeted existing wait controls plus complete NativeEventInformation suite: **42 passed/2 failed in85.58s** (`VALID_CONTROL_TESTS_002.xml`). The seven original passing control cases still pass. The added35 existing native-information cases pass. Two historical tests remain unedited:

- `test_unrequested_native_metadata_is_not_received_and_foreign_wait_is_rejected`: originally exhausted its script after the old test's later root tool choice. It now stops earlier at its historical assertion that category equals `action_contract`; required specific feedback now uses `wait_target`. Its detail string remains `native_event_information_target_not_visible`. This is an intentionally changed diagnostic expectation. The NEW bound-native test explicitly verifies the new feedback and lets its fixture episode choose an actually permitted reconsideration repair; it passes. The historical fixture's later root tool-selection issue is not repaired or hidden.
- `test_completed_wait_replay_uses_frozen_context_after_control_cleanup`: retains the original `refreshed completed/saved root context` assertion during a later root decision. This broader context-refresh issue remains outside the target-identity fix. The NEW completed-outcome bypass check verifies the specific changed wait path directly; it does not claim that the broader resumed context path is repaired.

Original baseline7pass/2fail, source hashes and full failures remain unchanged in `VALID_CONTROL_TESTS_001.xml` and `BASELINE_SOURCE_AND_FAILURES_001.json`. Initial NEW-test development result9pass/3fail is retained in `FIX_FOCUSED_TESTS_001.xml`; those three fixtures incorrectly chose root ordinary tools, which the existing root boundary rejects. Only the new test fixtures were corrected. Intermediate13pass and separate1pass native-boundary results are retained in002/003. They overlap the final suite and are not additive counts.

No configured-model scientific work, actual paper acquisition, actual017 replay/restart, live native program or external/HPC job was run. The coordinator reported concurrent022 changes to tool/literature operation files; joined root checks are still required before any newly pinned configured run. No scientific, axis or full-goal completion is claimed.

## Commands actually executed

All from `/home/chia/repos/gene_annotation_episode`; these are historical commands, not instructions to overwrite their existing receipt/state directories.

Final focused command:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q --tb=short -o cache_dir=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_cache --basetemp=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_final_fix_state_004 --junitxml=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/FIX_FINAL_FOCUSED_TESTS_004.xml tests/test_wait_target_failures.py
```

Targeted existing control/custody command:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q --tb=short -o cache_dir=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_cache --basetemp=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_controls_state_002 --junitxml=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/VALID_CONTROL_TESTS_002.xml tests/test_episode_waiting.py::test_selected_event_set_closes_once_and_replays_original_outcome tests/test_durable_episode.py::test_event_wait_matches_selected_set_and_catches_arrival_before_subscription tests/test_durable_episode.py::test_reconsideration_and_wait_cancellation_do_not_change_execution tests/test_native_event_runtime.py::test_selected_native_wait_uses_original_form_and_one_zero_gain_observation tests/test_native_event_runtime.py::test_unrequested_native_metadata_is_not_received_and_foreign_wait_is_rejected tests/test_native_event_runtime.py::test_completed_wait_replay_uses_frozen_context_after_control_cleanup tests/test_native_event_information.py
```

Earlier focused development commands:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -o cache_dir=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_cache --basetemp=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_state --junitxml=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/FIX_FOCUSED_TESTS_001.xml tests/test_wait_target_failures.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -o cache_dir=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_cache --basetemp=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_state_002 --junitxml=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/FIX_FOCUSED_TESTS_002.xml tests/test_wait_target_failures.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q --tb=short -o cache_dir=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_fix_cache --basetemp=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/pytest_native_fix_state_003 --junitxml=verification/literature_reference_evidence_2026-10-25_001/wait_target_failure_021/FIX_NATIVE_BOUNDARY_TEST_003.xml tests/test_wait_target_failures.py::test_bound_native_rejection_returns_to_episode_without_completing_failed_wait
```

`FIX_FINAL_RECEIPT_004.json` holds full final production/test SHA256 values, before/after comparisons, preserved control-file checks, exact XML failure details and XML digests. All six other original inspected runtime sources and all five historical control/fixture files match their baseline hashes; the original baseline XML digest also matches.
