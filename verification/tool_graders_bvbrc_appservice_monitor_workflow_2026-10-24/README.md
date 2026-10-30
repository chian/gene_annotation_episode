# Shared Workflow AppService native monitor verification

Owned test: `tests/test_bvbrc_appservice_monitor_workflow.py`.

This workload changes only that test and this verification directory. It uses
the existing `Workflow`, `ExecutionServiceFactory`, `Store`, journal,
`launch` / `launch_api` / `monitor` bindings, AppService custody, typed report
admission, practical endpoint estimation, and progress readers. No new episode
type, prompt, runtime tool, production controller or scientific score is added.

The native responses and model decisions are explicitly controlled fixtures.
Socket connections and urllib transport are forbidden. Root and monitor
continuation are explicitly scripted fixture controllers; launch and API
closure use the actual practical completion proof and exact-zero estimator.

The one scenario selects root -> launch -> launch_api prepare/submit, returns
the original native TaskHandoff, commissions the existing monitor, and selects
`progress.observe` twice: `query_tasks`, then `stdout`. Each native choice and
its exact requested field subset must be present in the original saved action.
The monitor form requests existing typed facts for progress references, target,
latest state, observation time, and result availability. Native timing and log
windows remain attached to the exact admitted progress references.

An injected interruption occurs after the complete original stdout response is
retained and before its progress projection. The test closes and reopens Store,
rebuilds Workflow, forbids all further native and decision-provider calls, and
resumes the same selections. It then replays the closed workflow and compares
the full archived tree, numerical observations and frozen return forms.

Expected concrete fixture facts:

- Native task ID `123`, originally submitted as `Homology`.
- Exactly one `AppService.start_app2`, one `AppService.query_tasks`, and one
  `task_info/123/stdout` request, across interruption and recovery.
- Status `running`, lifecycle `executing`; native `elapsed_time = 01:02:03`
  remains `SQL_TIMEDIFF` with unknown timestamp timezone. The zero-date start
  string and null completion remain unchanged. No duration seconds are inferred.
- HTTP request turnaround remains a distinct transport measure: 0.25 seconds
  for the controlled status response and 0.125 seconds for stdout.
- Complete stdout contains 42 bytes, including NUL and invalid UTF-8. Only the
  caller-selected last 12 bytes cross as a window; original retained-response
  offsets are `[30, 42)`, and the retained window has local offsets `[0, 12)`.
- Stdout leaves current state unknown; the latest typed state is null, while
  the earlier running observation remains available through its progress ref.
- Seven total completed-action observations: root 2, launch 1, launch_api 2,
  monitor 2. The two monitor actions each receive the configured 0.5 information
  unit; scientific record and annotation counts remain zero.

First run, retained without replacement:

```text
.venv/bin/python -m pytest -q tests/test_bvbrc_appservice_monitor_workflow.py \
  --basetemp=verification/tool_graders_bvbrc_appservice_monitor_workflow_2026-10-24/first-run \
  --junitxml=verification/tool_graders_bvbrc_appservice_monitor_workflow_2026-10-24/first-run.xml
1 failed in 66.41s
```

The first failure was a production return-boundary defect, not a failed native
observation. `runtime_report_attempts` recorded `unknown_reference` at
`report.target` for the existing `monitoring_target_handle` source and its
`execution_handle` namespace. `Workflow.resolver` called
`ExecutionEpisodes.resolve_received_reference` before the monitor resolver;
the AppService receipt resolver returned false and vetoed that valid monitor
handle. All four episode loops closed and the requested native capture and
interrupted recovery completed before the failing admission assertion.
The production owner was given the exact failure and owns its repair.
`first-run.log`, `first-run.xml`, `first-run-evidence.json`, and the actual
Store, receipts and archives under `first-run/` preserve this evidence.

This verification does not establish live BV-BRC authentication/access,
configured-model decision quality, native scientific Homology output or grading,
HPC execution, detached-worker scheduling/recovery, or the wider tool inventory.
The existing module/consumer tests own the larger failure and missing-data
matrix; this workload concentrates on the shared-loop communication path.

## Additive successful verification after the resolver repair

The production owner added narrow AppService monitor target resolution using
the existing original-assignment and handoff-custody proofs. This verification
workload did not edit those production files. The original requested target
field remains in the test.

```text
.venv/bin/python -m pytest -q tests/test_bvbrc_appservice_monitor_workflow.py \
  --basetemp=verification/tool_graders_bvbrc_appservice_monitor_workflow_2026-10-24/second-run \
  --junitxml=verification/tool_graders_bvbrc_appservice_monitor_workflow_2026-10-24/second-run.xml
1 passed in 98.04s
```

All three child-to-parent forms were admitted with zero failures. The monitor's
typed return contains exactly `progress`, `target`, `latest_state`,
`latest_observed_at`, and `result_available`. The scientific parent's actual
received-progress ledger contains the two exact references from that form.
Native SQL timing and the retained window are read from those original
progress records; no new unrestricted report field was introduced.

Both recovery phases passed with every further native and decision-provider
call forbidden. The five pre-interruption observations remained unchanged;
recovery added the stdout observation and parent monitor-return observation,
for seven total. Closed replay preserved all seven observations, every frozen
return form, and the complete archived episode tree. Launch and API endpoint
closure retained their final gain of 2 and exact-zero future expectation; API
preparation retained its prior gain of 0. Monitor gains remained 0.5 and 0.5,
separate from scientific credit.

`second-run.log`, `second-run.xml`, and the actual Store, receipts and archives
under `second-run/` retain the successful execution evidence.
`verified-path.json` captures the numerical observations, exact admitted form,
received references, native timing, full 42-byte stdout in hexadecimal,
12-byte window and offsets, and SHA-256 identities of the tested source paths.
The earlier failing records remain unchanged in `first-run/` and its companion
files. The live-resource, model, scientific-output and detached-worker limits
stated above still apply.
