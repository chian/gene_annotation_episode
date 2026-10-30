# Configured A105 run 278: read-only recovery audit

## Scope and result

The original configured caller was interrupted while its annotation parent was waiting for a literature child. This audit did not resume inference, change the saved database, inspect provider request or response bodies, reinterpret the paper, or edit caller 001/002 or its frozen source. The new `check_read_only.py` is an additive preflight; its successful result means the current saved state is *internally consistent as a candidate for replay*, not that a live resume has been demonstrated.

The preflight ran at 2026-10-29 01:27 UTC with `.venv/bin/python -B verification/a105_configured_run_recovery_305/check_read_only.py`. It verified all 1,037 files in `SOURCE_PIN_001.json` and all 10 original entrypoint/contract files in `ENTRYPOINT_PIN_002.json`, compared prepared settings with both the run file and saved `runtime_runs.settings`, and compared the saved root objective, assignment, initial report, contract declaration, purpose and expanded schema with the original prepared caller. The process identity in `STATUS_002.json` (PID 3726505, boot ID and start ticks) is no longer live. The read-only SQLite connection reported `total_changes = 0`.

| Saved item | Observed state |
| --- | --- |
| Run | `run_266d996f86fb4fc491a5fac50d62cd33`, state `running` |
| Root | `episode_6e71ad5eab1c45a6ff1bf9039d41dd5273447efe7d7181a71b16d3bed4807ba9`, active |
| Episodes | 11 total: 9 yielded literature children, active root, active literature `child_10` |
| Action/observation/model-call rows | 615 / 548 / 618 |
| Admitted child returns | 9, all saved in `runtime_report_attempts` |
| Unfinished root action | decision 10, `episode_child`, no result or credit |
| Unanswered child decision | `child_10`, logical call 18, purpose `decision` |
| Physical exchange | index 0, no response or lookup result |

The 615 versus 548 count does not by itself indicate duplicate or missing observations. Failed/rejected selections can have an action row without a controller observation. The saved primary keys and `on_unit` equality check are the relevant replay guards.

## Reconstruction path inspected

- `caller_002.py` was read in full. `execute()` reloads `prepared_caller.json`, verifies the pin and original entrypoint contracts, opens the existing `Store`, builds tools and a new provider directory, assembles the same workflow and root, and runs `root.run_async(workflow.context)`. It does not offer a separate resume mode.
- The pinned `runtime.py` decision reconstruction path (`DecisionSource.call`, `exchange_decision`, `next`, `execute`; `Workflow.selected`, `build`, `controller_value`) and pinned `method_loop/episode.py` replay/observation path were inspected. Existing model responses and completed action results are retrieved from the journal. The unfinished `decision_exchange_v1` call creates a new physical retry exchange linked to the unanswered exchange before another model call. Existing `runtime_observations` must match reconstructed observations; they are not inserted again.
- For blocking children, the parent re-enters its selected child. Each already admitted return is read from the saved report attempt and its old action outcome/credit. The unfinished root decision 10 has neither result nor credit, so it can receive the eventual `child_10` return once. `save_attempt` rejects a different replayed contract or form.
- The pinned `providers.py` creates a new native provider session for a retry. An old remote inference might have completed after its process lost the result, but no response is committed in the runtime journal. Retrying can therefore cause a second *physical* inference for the same logical decision. This is distinct from a second selected action or observation. Provider bodies were not inspected.
- The pinned timing path closes an old running interval as `end_unobserved` when it starts a new interval, so process downtime is not asserted to be execution time. The run-frozen knowledge and launch-instruction snapshots are reused if their saved indexes exist; the pin manifest verifies their implementation bytes, while the original saved settings identify the configured libraries.
- The caller uses no independent `execution_binding`; this is the blocking-child reconstruction branch. The current repository `runtime.py` differs from the pinned runtime, so any future replay must import the frozen pin exactly as the original caller does.

## Live recovery procedure for a later authorized run

1. Re-run `check_read_only.py` immediately before a single replay owner starts. Abort if the original process identity is live, any pin or contract comparison fails, the pending call/action changed, or the database is no longer in the observed state.
2. Retain the original run ID, prepared settings, root request, source identities, pin and saved journal. Use the original `caller_002.py execute` path with the repository `.venv` so its own pin verification and assembly run. Do not create a new run, rewrite old calls, clear the pending exchange, or synthesize a child return.
3. Expect the first new model operation to be a retry for `child_10` logical decision 18; the runtime should append a new physical exchange with `retry_of_exchange_index = 0`. It should then complete that child and root decision 10 if the child returns. Do not treat a native provider session ID as the scientific run identity.
4. After the run yields or fails, inspect public status/summary and read-only journal counts. Verify the original nine report attempts, existing action keys and existing observation keys still have their original values; check any new rows correspond to actual work after the pending point. Verify that exactly one root action result/credit and observation were added for the completed `child_10` return, if it returned. Do not infer scientific completion from termination.

This audit did **not** implement or launch a live resume wrapper. The original caller itself is the concrete replay entrypoint. A live wrapper would mutate the existing 3.9 GB SQLite state and the original status/return files; a clone rehearsal was not performed, and the old provider operation has no journaled response. The read-only preflight is the safe additive entrypoint currently established. A future live run should record its own before/after receipt without changing the original caller or fixed contracts.
