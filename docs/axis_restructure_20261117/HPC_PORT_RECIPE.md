# HPC planning port recipe: `hpc_work_planning` and its two sisters on the `HpcLedger` work table (19 November 2026)

Done for A107 (`root/a107/partner_presence_evidence/hpc_work_planning`, `hpc_resource_prediction`,
`hpc_allocation_execution`). This is the same work for A102, A103, A104 and A110. The A107 files are the worked
example: copy the shape, keep each axis's own wording, science and library (`jobs/hpc/<axis>/`). Do the three
episodes bottom-up and confirm each with a real model run before the next: prediction, then allocation, then the
head over its children.

Not part of this recipe: the launch, monitor and results children (`execution_job_submission` and its route
children, `execution_progress_assessment`, `execution_result_acquisition`), which are ported by
`LAUNCH_PORT_RECIPE.md`.

## 1. The design in ten lines

1. The HPC ledger is the work table `HPC_LEDGER` in custody (`episode_support/jobs/hpc_ledger.py`). It is not a
   service, not a file and has no directory. No episode declares `hpc_ledger` in `SERVICES`.
2. A ledger is named by its commission: `ledger_id(commission)`. Whoever is first opens it with
   `HpcLedger.open(ctx.store, commission)` (the head's `hpc_open`; the prediction's `hpc_open` when it is the
   entry). Every later tool is handed the id in its arguments and reads with
   `HpcLedger.existing(ctx.store, arguments['ledger'])`.
3. An Episode reads only the rows it holds. The head passes a sister `ledger_row_refs` (`ledger.refs()`: every held
   row and the records the rows name in `source_refs`) and, to the allocation sister, the id (`ledger`). A sister
   returns `hpc_ledger_refs` (required field, `record_refs`): the head then holds the sister's rows.
4. The head's `internal_summary` reads the ledger through `view.records` at every decision
   (`HpcLedger.existing(view.records, ledger_id)`), so a sister's work is in the credit of the unit that
   commissioned it. The sisters return the ledger's view with each tool outcome and their summary keeps the latest.
5. There is no `ledger.once`, `cached` or `save_action`: the journal replays a finished unit and an abandoned
   unit's rows are taken back. A value a unit computes is written with `put(kind, value, identity=...)`. The one
   real "once per ledger" value (the shared-history entry) is "read the held row, else compute and put".
6. There is no `ledger.path`. The frozen plan that the launch reads is an artifact of the `hpc_plan` unit which the
   ledger names: `ledger.put('launch_input', {'plan_id', 'artifact_ref'}, identity='launch_input:' + plan_id,
   source_refs=[artifact])`. `msg_to_child` passes it in the launch's `record_refs`. `closed_measurement` takes
   the ledger id for its provenance.
7. The resource is reached only through `ctx.services['job_access']`, by the library functions of
   `episode_support/jobs/hpc/hpc_remote.py` and `hpc_queue.observe(ctx, resource_id)`. A request that fails is a
   returned unit with status `failed`. The shared memory is `ctx.services['estimate_table']`, called directly.
8. Returns are controlled data: `credit`, `finding` (counts, booleans), `hpc_ledger_refs`, and selectable record
   fields. No text field, no list of names, no field that restates the credit.
9. Credit on a shared ledger is the episode's own: the prediction's model improvement since its entry; for the
   allocation sister and the head, the ledger's credit minus the ledger's credit when the episode first read or
   opened it.
10. The prompt states the job first (`INSTRUCTIONS`: what the episode is for, what it is shown, how to work, what
    earns credit) and `decide` shows only what the decision needs.

## 2. Files of the worked example

| What | File |
|---|---|
| The ledger (`refs()` now also returns the records a row names) | `episode_support/jobs/hpc_ledger.py` |
| Remote commands, file read and write, handoff target, job status | `episode_support/jobs/hpc/hpc_remote.py` (shared by all axes) |
| Queue observation through job access | `episode_support/jobs/hpc/hpc_queue.py` `observe` (shared; the old `observe(configuration)` is deleted) |
| Their real tests | `episode_support/jobs/tests/test_job_services.py` (`test_the_refs_of_a_ledger_carry_the_artifact_a_row_names`, `test_a_remote_file_is_written_and_read_and_the_queue_is_asked_through_the_route`), test episode `jobs/tests/job_probe/task.py` |
| Prediction | `root/a107/.../hpc_work_planning/hpc_resource_prediction/` (all files) |
| Allocation | `root/a107/.../hpc_work_planning/hpc_allocation_execution/` (all files but its children) |
| Head | `root/a107/.../hpc_work_planning/` (`task.py`, `credit.py`, `goal.py`, `messages/*`) |
| The test world | `.../hpc_resource_prediction/tests/hpc_world.py` |
| Offline tests through `next_decision` and `run_unit` | `tests/test_hpc_resource_prediction_runs.py`, `tests/test_hpc_allocation_execution_runs.py`, `tests/test_hpc_work_planning_runs.py` |
| Real-model branch tests | `tests/test_branch_*_model_run.py` in the three folders |
| What had no real call | `BRANCH_FIX_BLOCKERS_a107.md` |

## 3. Steps for one axis

### 3.0 The axis's library (`episode_support/jobs/hpc/<axis>/`)

- `hpc_monitoring.py` `MonitorCronController.reserve`: replace `self.ledger.once(reference, 'monitor_schedule',
  calculate)` by `schedule = calculate(); self.ledger.put('monitor_schedule', schedule, identity=reference);
  return schedule`.
- `hpc_history.py` `closed_measurement(..., ledger=)`: the keyword is `ledger` (the id). A102 still has
  `ledger_path`.
- `hpc_commission_sources.py` (A102): still raw Store access; A107's is the custody form (`TableDeclaration`).

### 3.1 `hpc_resource_prediction`

1. `task.py`: `SERVICES = ('job_access', 'estimate_table')`. Import `HpcLedger` from
   `episode_support.jobs.hpc_ledger` and `hpc_remote`; delete the import of the old `HPCLedger`.
2. Delete `_open_ledger`, `_remote`, `_acquire_queue` and every `raise NotImplementedError`.
3. `hpc_open(arguments, ctx)`: `ledger = HpcLedger.open(ctx.store, commission)`; write the `owner` row when the
   Episode holds none (`{'run_id', 'episode_id': arguments['owner_episode_id'], 'scope', commission identity}`);
   keep the old check of scope and commission identity against the owner row; write the reference model, the
   shared-history entry (held row, else compute and put) and this episode's `entry:<episode_id>` row.
4. Every other tool: `HpcLedger.existing(ctx.store, arguments['ledger'])`. `action` adds `'ledger':
   summary['ledger']['ledger_id']` to the tool arguments.
5. `ledger.once(identity, kind, calculate)` becomes `ledger.put(kind, calculate(), identity=identity)`.
6. Discovery: `await hpc_remote.command(ctx, commission['resource_id'], command, name='discovery')`; the return
   code is `ran['returncode']`, the output `ran['files']['stdout.log']`. Queue: `await hpc_queue.observe(ctx,
   commission['resource_id'])`. Both tools become `async def`. A reply whose status is not `completed` is returned
   as a unit with status `failed` and `feedback {'category': 'resource_request', 'code', 'detail'}`.
7. The shared memory: `ctx.services['estimate_table']` when `ctx.settings['shared_execution_memory']` is true
   (`latest`, `observe`, `history`, `as_record`).
8. The ledger view each outcome returns gains `ledger_id` and `ledger_refs` (`ledger.refs()`).
9. `messages/read_from_parent.py`: add `ledger_row_refs` (`record_refs`, optional).
10. `messages/final_to_parent.py`: required `credit`, `finding` (counts and booleans), `hpc_ledger_refs`;
    selectable `hpc_result_refs`. Delete `hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations` and every text
    field.
11. Prompt: write `INSTRUCTIONS` and the tool descriptions for the new design, and reduce `decide`'s context
    (section 5).

### 3.2 `hpc_allocation_execution`

1. `task.py`: delete the block of stubs (`handoff_target`, `observe_target`, `read_window`,
   `write_allocation_control`, `observe_queue_value`, `run_command`, `estimate_latest`, `estimate_observe`,
   `estimate_history`, `estimate_policy`, `estimate_record`) and call the real thing where each was used:
   `hpc_remote.handoff_target(ctx.store, handoff_ref)`, `hpc_remote.job_status(ctx, target)`,
   `hpc_remote.read_file(ctx, resource_id, path, limit, name=)`, `hpc_remote.write_file(ctx, resource_id, path,
   artifact_ref, name=)`, `hpc_queue.observe(ctx, resource_id, name=)`, `hpc_remote.command(...)`, and the
   members of `ctx.services['estimate_table']` (`latest`, `observe`, `history`, `policy`, `record`).
   Give each command of one unit its own `name` (the job handle is derived from the unit's key and the name).
2. A failed request inside a tool that makes several: the A107 file raises its own `ResourceRequestFailed(failure)`
   from `answered(reply)` and each tool that reaches the resource catches it once and returns `failed(...)`.
3. `open_ledger`: `HpcLedger.existing(ctx.store, arguments['ledger'])` and the old scope and identity check. Delete
   `launch_input_path`, the setting `directory`, `coordinator_workspace`, `_immutable` and the async `once`.
4. `hpc_plan`: write the plan artifact and the `launch_input` row (section 1, item 6); return an invalid unit for
   a model-named reference the ledger does not hold or a stale queue observation.
5. `hpc_handoff`: the target is the held `JOB_LEDGER` handoff row; `action` rejects a handoff that the launch of
   that plan did not return. Name the handoff row in the `handoff` row's `source_refs` so that it travels with the
   ledger.
6. `export_closed`: `closed_measurement(..., ledger=ledger.ledger)` and `estimate_table.record(**measurement)`.
7. `decide`: delete the read of `resource_tool_estimates`; with the shared memory show
   `ctx.services['estimate_table'].read('profiles')`.
8. `yield_estimator.py`: `settings['cost']` (not `cutoff`).
9. `credit.py`: the ledger's credit minus the credit of the first outcome's view (`entry_credit` in the summary).
10. `messages/msg_to_child.py` (launch): `record_refs` = the input records and `plan['launch_input_ref']`; the
    message names `launch_input_ref` and no path.
11. `messages/read_from_parent.py`: `ledger` (text id) and `ledger_row_refs` (`record_refs`), both required.
12. `messages/final_to_parent.py`: as 3.1 item 10, with selectable `hpc_result_refs` and
    `hpc_result_artifact_refs`.
13. Prompt: as section 5.

### 3.3 `hpc_work_planning` (the head)

1. `task.py`: the same tool bodies as the allocation sister (each episode keeps its own copy). `hpc_open` creates
   the ledger: `HpcLedger.open(ctx.store, commission_of(arguments, ctx))`, the `owner` row when none is held (this
   Episode's `run_id` and `episode_id`), the tool request, the reference model; it returns `{'ledger': id,
   'credit_at_open': ...}`. Delete `ledger_directory`, the owner-is-me check of the old `open_ledger`, and
   `resolve_tool_request` (see `BRANCH_FIX_BLOCKERS_a107.md` 3.3).
2. The head's tool outcomes carry no ledger view. `messages/internal_summary.py` computes
   `task.ledger_view(HpcLedger.existing(view.records, ledger_id))` once `hpc_open` has returned the id. Delete
   `ledger_stale`, `LEDGER_SISTERS` and the second `hpc_open` after a sister.
3. `messages/msg_to_child.py`: both sisters get `ledger_row_refs: view['ledger_refs']`; the allocation sister also
   `ledger: view['ledger_id']`. `PREDICTION_SELECTION = ()`, `EXECUTION_SELECTION = ('hpc_result_refs',
   'hpc_result_artifact_refs')`.
4. `messages/read_from_child.py`: a sister's report is its credit and its finding's counts (and the result
   references of the allocation sister). The ledger rows are received in custody and are not listed.
5. `credit.py`: the ledger's credit minus `credit_at_open`.
6. `messages/final_to_parent.py`: as the allocation sister's, with the counts of sister commissions.
7. The evidence head above (`root/<axis>/<head>/messages/msg_to_child.py`, table `SELECTABLE['hpc']`, and its
   `read_from_child`) must stop naming the removed return fields; to continue HPC work later it passes the
   returned `hpc_ledger_refs` back in `received_record_refs`.

## 4. Tests

- The world: one configured commission with measured history (cases to train on and later ones held out), a
  `pbs_ssh` resource with `account`, `workspace` and `python_executable`, the real `job_services`. Two transports
  for the resource's `PbsSshRoute`: `absent` for model runs (a transport program that does not exist: every request
  is `transport_unavailable`, nothing is contacted, whatever the model selects), `local_shell` (`['/bin/sh',
  '-c']`) for offline tests that choose every command themselves. Never bind a real transport in a test.
- The allocation sister alone: its ledger is created by the prediction episode's own `hpc_open` as the first unit
  of a run of that episode in the same Store (`hpc_world.ledger_of_the_prediction_sister`), and the entry
  assignment names the id and the rows. A caller writes no ledger row.
- Offline (no model): `next_decision` (the first is the code-issued opening or reading unit; the second is the
  `ModelRequest`, which the test saves), `run_unit` for each tool as far as it goes here, the controller's stop,
  the admitted controlled return, `resume` of the closed run, and the ledger passed on in custody.
- Real model, in order: prediction alone; allocation alone; the head over its children. Each asserts a closed run,
  an admitted return, and a resume that makes no model call and no unit.
- Commands: `bash tools/one_workflow.sh --slot <slot> runs/<fresh> -- env HOME=$PWD/runs/<fresh>/home
  CODEX_HOME=/home/chia/.codex PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest -p no:cacheprovider
  --basetemp=runs/<fresh>/tmp <path> -m model_run -v --tb=short`; offline with `http_proxy=http://127.0.0.1:9
  https_proxy=http://127.0.0.1:9`, without `CODEX_HOME` and `-m model_run`.

## 5. The prompt (do this first for each episode)

Print the request before changing it (`next_decision` after the opening unit; the A107 tests save
`model_request.json`). The A107 prediction request went from 32.5 KB to 17.3 KB.

Remove from the instructions: text about the old runner and the old transport (SSH transports, sisters'
assignments "copy hpc_child_commission exactly", scope inheritance rules, report repair), and library instruction
texts for tools the episode does not offer. Remove from the context: the goal a second time, the yield controller's
state and yield table (`controller`, `action_yields`: alpha, status and uncertainty codes), the progress clock
(`time_accounting`), the whole ledger view inside `last_local_outcome`, the full commission where a few fields
decide, and fields that are always empty for the episode (monitors in the prediction).

Write: one paragraph that says what the episode is for; one that names each context field; one that says how to
work, tool by tool, keeping the owner's sentences that carry a decision (a plan is launched once; completion is not
acceptance; never replace an uncertain submission; unknown inputs stay unknown; the fixed validation set cannot
change); one that says what earns credit and that the episode ends by itself. Tool descriptions say what the tool
records in the ledger. Say what to do when the resource cannot be reached.

| Episode | Purpose sentence in A107 |
|---|---|
| prediction | "predict the time and resources the commissioned work needs on the resource and record that expectation in the HPC ledger of the commission" |
| allocation | "plan the allocation from the HPC ledger of the commission and carry that plan through" |
| head | "bring the commissioned computation to completion on the HPC resource by commissioning two sister episodes that work over the ledger" |

## 6. What each axis still has (read from the files on 19 November 2026)

`stubs` counts `raise NotImplementedError` in `task.py`. "old import" means the file imports the deleted
`jobs.hpc.<axis>.hpc_ledger.HPCLedger`, so the episode cannot be imported.

| Axis, episode | Ledger | Still to do |
|---|---|---|
| A102 head | imports `HpcLedger`; tools read `arguments['ledger']` | 12 stubs; `launch_input_path` and `ledger.path` (2), `ledger_path=`; 1 `ledger.once`; `_immutable` file; yield reads `cutoff`; assignment and sister commissions pass no ledger; return has 5 text or list fields and no `hpc_ledger_refs`; summary; prompt; no run tests |
| A102 prediction | old import (7 uses of `HPCLedger`) | everything of 3.1; 11 stubs; library: `hpc_history.closed_measurement(ledger_path=)`, `hpc_monitoring` `ledger.once`, `hpc_commission_sources` raw Store |
| A102 allocation | imports `HpcLedger`; tools read `arguments['ledger']` | 11 stubs; `launch_input_path`, `ledger.path` (2), `ledger_path=`; 1 `ledger.once`; `_immutable`; yield reads `cutoff`; assignment form has no `ledger` / `ledger_row_refs`; return as the head's; prompt; no run tests |
| A103 head | imports `HpcLedger`; tools read `arguments['ledger']` | 17 stubs (3 `unplaced`); `launch_input_path` (3 uses), 2 `_immutable`; 1 `ledger.once`; yield reads `cutoff`; sister commissions pass no ledger; return; summary; prompt; no run tests |
| A103 prediction | old import (3 uses); form already has a ledger field | 1 stub; 6 `ledger.once`; `hpc_open` on `HpcLedger.open`; remote calls on `hpc_remote` (4 `subprocess` / queue sites); yield reads only `commissions` (check its cost setting); return has 3 text or list fields; prompt; no run tests |
| A103 allocation | both imports (old 3 uses, new 2); tools read `arguments['ledger']`; form has the ledger fields | 2 stubs; finish the removal of the old import; return has 9 text or list fields; yield setting; credit at entry; prompt; no run tests |
| A104 head | imports `HpcLedger`; tools read `arguments['ledger']` | 13 stubs (1 `unplaced`); `launch_input_path` (3 uses), `_immutable`; 1 `ledger.once`; yield reads `cutoff`; sister commissions pass no ledger; return; summary; prompt; library `hpc_monitoring` `ledger.once`; no run tests |
| A104 prediction | old import (7 uses) | everything of 3.1; 14 stubs |
| A104 allocation | `SERVICES` still names `hpc_ledger`; old import; no `arguments['ledger']` | everything of 3.2: 1 stub, 1 `ledger.path`, 11 `ledger.once`; form already has the ledger fields; yield already reads `cost` |
| A110 head | imports `HpcLedger`; tools read `arguments['ledger']` | 16 stubs; 1 `ledger.once`; yield reads `cutoff`; sister commissions pass no ledger; return; summary; prompt; no run tests |
| A110 prediction | old import (4 uses); return already names ledger refs | 1 stub (`unplaced`); `hpc_open` on `HpcLedger.open`; remote calls on `hpc_remote`; return still has 6 text or list fields; yield already reads `cost`; prompt; no run tests |
| A110 allocation | imports `HpcLedger`; tools read `arguments['ledger']`; form has the ledger fields | 14 stubs; 1 `ledger.once`; yield reads `cutoff`; return has 5 text or list fields; credit at entry; prompt; no run tests |

No axis other than A107 has a `test_branch_*_model_run.py` in its three HPC planning folders.
