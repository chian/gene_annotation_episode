# Launch port recipe: from a shell tool to defined launch actions (19 November 2026)

The worked example is A103: `root/a103/gene_context_evidence/execution_job_submission/local_job_execution` (the
launch child) and its parent `root/a103/gene_context_evidence/execution_job_submission`. Both run with the real
model (`runs/fixlaunch_11`). This recipe says how to apply the same to the other launch episodes:
`local_job_execution`, `hpc_job_execution` and `api_job_execution` of a101, a102, a104, a106, a107, a110 (a105 and
a108 have none), and to the launch episodes of A103 that were not ported (section 8).

Read first: `AGENTS.md`, `TRANSFORM_GUIDE.md`, `LOCAL_WRAPPER.md`, `BRANCH_FIX_BLOCKERS_a103.md`.

## 1. The rules the port carries out

1. **The model is the router.** It answers with one action from a fixed set, as structured JSON, with controlled
   arguments (every field an `enum` built by code, a number in a range, or a record reference). Code carries the
   action out. The model never writes or runs a command: no `exec_command`, no shell, no free command text, in no
   tool, schema, prompt or test of an episode.
2. **One library function per resource kind is the execution and inspection point.** The episode's tool calls that
   function and nothing else to start work on a resource. For now it is a pure pass-through of the command the
   assignment gives; the owner adds controls there later, not in episodes.

   | Kind | Module, function | State | Called by |
   |---|---|---|---|
   | local | `episode_support/jobs/resource_local.py`, `execute_on_local_resource` (`LOCAL_WRAPPER.md`) | written, tested | every `local_job_execution` and `local_resource_work_execution` |
   | hpc | `episode_support/jobs/resource_hpc.py`, one public function (section 6) | to write | every `hpc_job_execution` (and `hpc_resource_work_execution`) |
   | api | `episode_support/jobs/resource_api.py`, one public function (section 7) | to write; needs an API route first | every `api_job_execution` (and `api_resource_work_execution`) |

3. **The prompt is the design.** Print the real model request before and after (through `next_decision`, and the
   recorded `request.json` of a model run) and judge it: it says what the episode is for, which job is to be run,
   what the model chooses, what earns credit, and the actions that exist. The context shows the assignment once
   and the credit as the productivity signal, with no controller internals.
4. **The launching child ends at handoff.** Its credit is the credit the assignment's `requested_job_handoff`
   requirement defines; its yield controller's target is that credit; the handoff row is returned as a record
   reference in a controlled return.
5. **Library files are not stripped.** Only episode files lose the old tool. A library file that mentions
   `exec_command` stays as it is (section 9). A library function is added only where a defined action needs one
   that does not exist.

## 2. Find the files of your axis

Run the search inside your own axis tree only (never over the repository):

```
grep -rl exec_command gene_annotation_episode/episodic_workflow/root/<axis> --include=*.py | sort
```

Every hit in an episode file is one of: the tool and its schema (`task.py`), prompt text (`task.py`, sometimes
`goal.py`), the reading of the tool's outcome (`messages/internal_summary.py`), a capability list in the parent
(`execution_job_submission/task.py`: `PRACTICAL_TOOL_NAMES = ['exec_command']`), or a test.

## 3. Port a `local_job_execution`, file by file

Copy the A103 files into the episode folder and change only what is the episode's own (the binding path, the axis
folder in a library import, its yield profile). The ten-file shape stays; an episode imports nothing from another
episode, so the files are copies.

| File | What it holds after the port | What goes |
|---|---|---|
| `goal.py` | `BINDING_PATH` of the episode; `GOAL`, `UNIT`, `RESULT` of a launch that ends at handoff | "execute until outputs exist" wording |
| `task.py` | `SERVICES = ('job_access',)`; `TOOLS = {'launch_job', 'hold_launch'}`; `INSTRUCTIONS`; `output_schema(assignment)`; `decide`; `action` | the shell tool, its schema, `TerminalExecution`, `_operations`, the lookup tools and their texts, `_task_text`, `time_accounting`, the `arguments_json` answer |
| `credit.py` | `summary['handoff_credit']` once a held `JOB_LEDGER` handoff row of the assigned resource exists (`job_records.job_rows(records)`), else `0.0` | `project_practical_credit` over shell receipts |
| `yield_estimator.py` | `CompletionYieldController` with target `parent_input['handoff_credit']`, cost and parameters from `settings['task_yield_profiles']['launch_local:' + yield class]` | nothing else; the `.get` with its own error becomes the plain lookup |
| `messages/read_from_parent.py` | the `practical_assignment_v1` form, one field per property of the axis's `ASSIGNMENT_SCHEMA`; `validate_assignment`; parent input `{'assignment', 'handoff_credit'}` | `record_refs` and `scientific_task` (see blocker 3) |
| `messages/internal_summary.py` | `assignment`, `handoff_credit`, `launches` (handed off, or failed with the failure code), `holds`, `handoff_refs`, `credit_by_action` (the controller's marginal credits) | receipts, validations, completion proof, `yield_table`, `selected_execution_task` |
| `messages/final_to_parent.py` | required `credit`, `finding` (three counts); selectable `execution_handoff_refs` (`record_refs`) and `execution_completed` (boolean) | every result-side field and native family (a launch acquires nothing), every text and list field |
| `episode.py` | unchanged apart from its docstring | |

The two actions:

- `launch_job` with `resource_id` (an `enum` of the one resource id the assignment names). `action` builds
  `ToolCall('launch_job', {'resource_id', 'command': requested_job['argv'], 'environment':
  requested_job['environment']})` from the assignment in the summary, never from the answer. The tool is
  `async def launch_job(arguments, ctx): return await execute_on_local_resource(ctx, arguments['resource_id'],
  arguments['command'], arguments['environment'], wait=False)`.
- `hold_launch` with `reason` (an `enum`: `constraints_not_met`, `launch_failed`). The tool returns `{'status':
  'held', 'reason'}`. It starts nothing and earns nothing; it is the unit the model takes when it should not
  launch, so that a failed launch is not repeated only because no other action exists.

A local assignment's `constraints` (`memory_bytes`, `scratch_bytes`, `allocation`) name the allocation the job is
to run under and must equal the resource's policy; they are not a range, so `launch_job` has no override field.
The model is shown them beside `ctx.services['job_access'].read('describe', resource_id)` and chooses.

`decide` builds this context and nothing else: `assignment` (the parent input's assignment, once), `resource` (the
`describe` read), `actions_so_far` (`launches`, `holds`), `credit` (`handoff_earns`,
`earned_by_each_action_so_far`). The output schema is strict (every object closed, every property required, `anyOf`
the only composition): check it with `model_exchange/tests/provider_schema_rules.violations`.

Do not add a check of the answer, a `Rejected` path, or a guard: the schema fixes the answer and a wrong input
raises its own error.

## 4. Port the parent `execution_job_submission`

| File | Change |
|---|---|
| `task.py` | one action for the model: `commission_launch` with `resource_id` (an `enum` of the permitted resource ids); `action` returns `ChildCall(summary['permitted'][resource_id]['slot'], {'resource_id': resource_id})`. Remove `PRACTICAL_TOOL_NAMES` and the `tool_names` of a local or HPC resource from the capabilities; remove the two lookup tools, their library texts and contexts, `_selected_execution_task`, `_task_text`, the `controller` and `time_accounting` context, `generation_schema` and `decode_response`. The context is: `assignment` (once), `permitted_resources`, `resources`, `received_bvbrc_values`, `launches_so_far`, `credit` |
| `messages/msg_to_child.py` | `launch_local` passes the request of the resource and nothing else (`assignment=request`); the selection stays `('execution_handoff_refs', 'execution_completed')` |
| `messages/read_from_child.py` | unchanged in what it returns (handoff refs, the flag, the child's credit and its finding of counts) |
| `messages/internal_summary.py` | no lookups, no `yield_table`; `credit_by_action` instead |
| `messages/final_to_parent.py` | remove the `qualification` text field (prose in a return) |
| `goal.py` | `UNIT` no longer names a library lookup |

The instruction libraries were removed from both A103 episodes because neither decision used them: the child has
no command to write, and nothing a lookup returned in the parent reached a commission. Where an axis's decision
really uses a library (for example to choose among resources by their instructions), keep that lookup as a defined
action with an `enum` of operations; otherwise remove it with its text.

## 5. Tests to write and run

Real only: a real Store, `RunJournal`, `job_services(configuration)`, real detached local jobs.

- Child, offline (`tests/test_local_job_execution_binding.py`, helper `tests/launch_world.py`): the class checks,
  the ten-file set, the forms, the decision request through `next_decision` (context equal to the expected
  record, the assignment once, `violations(schema) == []`, the two actions), `action` taking the command from the
  assignment, `run_unit(launch_job)` starting a real job, the handoff row held as `produced`, credit equal to the
  requirement's credit, the controller stopped after that unit, the admitted result, resume with no second job;
  a hold; a launch the resource refuses (a resource whose policy asks for more memory than the machine has).
- Child, real model (`tests/test_branch_local_job_execution_model_run.py`): the model's answer is `launch_job`,
  one unit, `ended_by` `yield_stop`, the return, the job's file exists after `route.wait`, resume asks no model.
- Parent, offline (`tests/test_binding.py`, `tests/test_local_submission_stepped.py`, helper
  `tests/submission_world.py`) and real model (`tests/test_branch_execution_job_submission_model_run.py`): the
  parent's model answers `commission_launch`, the child's `launch_job`; the handoff row is `produced` in the child
  and `returned` in the parent; the parent's credit is its `handoff_unit`.
- The parent's `tests/test_binding.py` lists the files of the folder: add the new test files to its `FILES`.

Commands (a fresh run directory each time, one workflow at a time in the slot):

```
bash tools/one_workflow.sh --slot <slot> runs/<run> -- env HOME=$PWD/runs/<run>/home http_proxy=http://127.0.0.1:9 \
  https_proxy=http://127.0.0.1:9 PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest -p no:cacheprovider \
  --basetemp=runs/<run>/tmp <episode>/tests <parent>/tests -v --tb=short                      # offline
bash tools/one_workflow.sh --slot <slot> runs/<run> -- env HOME=$PWD/runs/<run>/home CODEX_HOME=/home/chia/.codex \
  PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest -p no:cacheprovider --basetemp=runs/<run>/tmp \
  <test file> -m model_run -v --tb=short -s                                                    # real model
```

A model run can fail on an intermittent refusal of the local launch (`BRANCH_FIX_BLOCKERS_a103.md`, item 2); the
journal then shows a failed `launch_job` unit with `service_did_not_initialize`. Run it again.

## 6. `hpc_job_execution`: the same episode shape on its own wrapper

Custom library code per kind: write `episode_support/jobs/resource_hpc.py` with one public function, the
inspection point before execution on an HPC resource (suggested: `async def execute_on_hpc_resource(ctx,
resource_id, command, environment, *, wait, allocation, inputs=None, estimates=None, name='job')`). It composes
the job of the real route `PbsSshRoute` (`episode_support/jobs/pbs_job_route.py`: `{'mode': 'batch' | 'login',
'script', 'arguments', 'env'}`) from the command the assignment gives and calls `JobAccess.launch` (or `run` when
waited for). Like the local wrapper it is a pass-through with one marked line for later controls. The scheduler
directives (`#PBS` account, queue, resources) are composed there, by code, from `allocation`.

The episode differs from the local one only in its controlled fields. An HPC assignment's `constraints` give real
choices (`allowed_queues`, `allowed_accounts`, `queue`, `account`, `resources`, `allocation`; see
`TerminalExecution.validate_assignment`), so `launch_job` gets one `enum` field for each choice the constraints
leave open, for example `queue` with the values of `constraints['allowed_queues']`. A constraint that fixes a
value gives no field. `action` puts the chosen values into `allocation`. No field takes text.

Not available today: `qsub`, `qstat`, `qdel` have never run (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided
yet", item 4), and nothing authenticates to Aurora in a test. The offline and model tests of an HPC launch run the
route through a local shell as its transport in `mode: 'login'`, as `episode_support/jobs/tests/test_job_services.py`
does.

## 7. `api_job_execution`

There is no API route (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided yet", item 3), so an API launch cannot
be ported onto a real launch yet. When the route exists: `episode_support/jobs/resource_api.py`, one public
function, the inspection point before a request is sent; the episode's action is `submit_request` with controlled
fields only (the service's operation from an `enum`, the subject as a record reference, numeric parameters in their
ranges), and the request body is composed by library code from the assignment. Until then the API episodes keep
their `BLOCKED-ON-JOB-SERVICE` errors; do not replace them with a stand-in.

## 8. Where the launch episodes are

Listed with `ls -d root/a1*/*/execution_job_submission/*_job_execution` and the same one and two levels deeper.
Each `execution_job_submission` folder is itself a parent to port (section 4).

| Axis | Head | `execution_job_submission` trees | Children in each |
|---|---|---|---|
| a101 | `sequence_homology_evidence` | `execution_job_submission` | api, hpc, local |
| a102 | `structural_homology_evidence` | `execution_job_submission`; `hpc_work_planning/execution_job_submission`; `hpc_work_planning/hpc_allocation_execution/execution_job_submission` | api, hpc, local |
| a103 | `gene_context_evidence` | the same three trees | api, hpc, local |
| a104 | `evolutionary_history_evidence` | the same three trees | api, hpc, local |
| a106 | `perturbation_evidence` | `execution_job_submission`; `published_evidence_assessment/execution_job_submission` | api only |
| a107 | `partner_presence_evidence` | the same three trees as a102 | api, hpc, local |
| a110 | `biochemical_feasibility_evidence` | the same three trees as a102 | hpc, local |

The local resource-work episodes that call the same local wrapper (with `wait=True`):
`a101/sequence_homology_evidence/resource_work_submission/local_resource_work_execution`,
`a102/structural_homology_evidence/resource_work_submission/local_resource_work_execution`,
`a103/gene_context_evidence/resource_work_submission/local_resource_work_execution`.

A103, state after this fix:

| Episode | State |
|---|---|
| `execution_job_submission/local_job_execution` | ported; offline and real-model tests pass |
| `execution_job_submission` | ported for the local child; API requests and `native_*` resource bindings still raise |
| `execution_job_submission/hpc_job_execution` | not ported (`task.py` offers the shell tool) |
| `execution_job_submission/api_job_execution` | not ported (no API route) |
| `hpc_work_planning/execution_job_submission` and its `local_job_execution` | not ported; the child's files equal the old files of the ported one except `goal.py`, so the port is a copy with the binding path changed (`task.py`, `messages/internal_summary.py`, `tests/test_local_job_execution_binding.py` name the old tool) |
| `hpc_work_planning/execution_job_submission/hpc_job_execution` | not ported (`task.py`) |
| `hpc_work_planning/hpc_allocation_execution/execution_job_submission` and its `local_job_execution` | not ported; this copy differs from the others (one tool, no lookups; `task.py`, `tests/test_episode.py`) |
| `hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution` | not ported (`goal.py`, `task.py`) |

The nested trees are commissioned by `hpc_work_planning` and `hpc_allocation_execution`: their `msg_to_child`
must pass the local child the request alone, as section 4 says for the head's tree.

## 9. Library files that mention `exec_command` (do not delete or strip)

These are controlled code. They stay. The ported episodes stop importing the ones they no longer call (the local
launch child no longer imports `terminal_execution`, `terminal_scientific_evidence`, `practical_execution_credit`
or the instruction libraries; the parent still calls `TerminalExecution.validate_assignment`). Found with a bounded
glob, not a recursive search:

```
cd gene_annotation_episode/episodic_workflow
grep -l exec_command episode_support/*/*.py episode_support/*/*/*.py \
  episode_support/*/*_evidence/*.py episode_support/*/*/*_evidence/*.py episode_support/*/*/*/*_evidence/*.py | sort
```

| Library file | Axis folders that have a copy |
|---|---|
| `episode_support/jobs/local_execution/<axis>/terminal_execution.py` | `biochemical_feasibility_evidence`, `gene_context_evidence`, `partner_presence_evidence`, `sequence_homology_evidence`, `structural_homology_evidence` |
| `episode_support/findings/<axis>/terminal_scientific_evidence.py` | those five and `evolutionary_history_evidence` |
| `episode_support/records/<axis>/practical_execution_records.py` | the same six |
| `episode_support/records/local_execution/<axis>/native_database_terminal_custody.py` | `evolutionary_history_evidence`, `partner_presence_evidence`, `sequence_homology_evidence` |
| `episode_support/acquisition/native_terminal_transport.py` | one file, no axis |

That is 21 files. `practical_execution_records.py` names the old tool in `JOB_TOOLS` and `_job_matches` (the
old proof that a shell receipt was the requested job); the ported launch credit does not use them: it reads the
handoff row.

## 10. Checks before reporting a port done

1. `grep -rl exec_command <episode folder> <parent folder> --include=*.py` lists nothing, tests included.
2. The printed request has no `controller`, `alpha`, `status_code`, `uncertainty_code`, `expected_next_gain`,
   `time_accounting`, no library context, and shows the assignment once.
3. Every field of every action in the output schema has an `enum` (or is a number with a range, or a record
   reference that `action` checks with `records.holds`).
4. The tool that starts work contains one call: the wrapper of its resource kind.
5. The return form has no `text` and no `list` field that a model wrote into.
6. Offline tests and both model runs pass; the model's decisions are in the journal (`journal.model_calls`).

## Correction (2026-11-19, owner): section 4 is wrong about the library lookups

Do NOT remove the parent's two lookup tools (`knowledge_lookup`, `launch_instruction_lookup`) or the parent's
`reason`: the test is what the episode's own `goal.py` UNIT names, not whether a lookup's result reached a commission.
Where the goal names a lookup or a reasoning commit and its job is done nowhere else, keep the tool with its
arguments unchanged. Open arguments to an episode's own tool (free-text reasoning) are not a defect; only what crosses
between episodes must be controlled. Only bookkeeping/provenance actions (earn nothing, change no next step) become
automatic code: the launch-instruction `select` is now a pin written by code at the end of a `read` and passed to the
launch child by `msg_to_child` (see the restored A103, A107, A101, A104 parents). `exec_command` and its lookups in the
local child stay removed. The `goal.py` row above ("UNIT no longer names a library lookup") and the remove-the-two-
lookup-tools sentence in the `task.py` row no longer apply to the parents.
