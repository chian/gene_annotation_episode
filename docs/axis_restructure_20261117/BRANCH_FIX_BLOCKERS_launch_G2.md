# Local launch port of A107 and A110: blockers and open points (19 November 2026)

Written with the port of `root/a107/partner_presence_evidence/execution_job_submission` and
`root/a110/biochemical_feasibility_evidence/execution_job_submission`, each with its `local_job_execution` child
(`LAUNCH_PORT_RECIPE.md`, `LOCAL_WRAPPER.md`; the pattern is the A103 port). No file of `episode_support/` or
`episode_runtime/` was edited.

## 1. Missing member: `estimate_table.resource_tool_estimates(kind)` (A110 parent)

The A110 `execution_job_submission` named the service `estimate_table` and read
`ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')` in `decide`: the timing information of
earlier runs per resource ("Capabilities, recorded inventory and timing information inform the choice", its goal).
`EstimateTable` (`episode_runtime/estimate_table.py`) has no such member. Its read members are `kind_statistics(kind)`,
`rows(kind, limit)`, `expectation(key)`, `kinds`, `latest(resource, kind, now)`, `history(profile, now, queue_only,
limit)`, `profiles(tools, now, limit)`, `policy`, `as_record`: none gives the estimates of a launch by resource.
Before the port every decision of this episode after its lookup raised
`NotImplementedError('BLOCKED-ON-JOB-SERVICE: estimate_table.resource_tool_estimates(kind) ...')` (`runs/lchg2_4.log`).

State after the port: the read and its `NotImplementedError` are removed, the episode declares `SERVICES = ()`, and
its model is shown no timing information. The goal text in `goal.py` is unchanged and still names it; the prompt
(`INSTRUCTIONS`) names only what is shown (the configured resources and the recorded inventory).

Wanted, for whoever owns the estimate table: one read member that returns, for a kind of action and a list of resource
ids, what earlier launches on each resource took (queue, setup, work, return), as closed JSON. The episode then
declares `SERVICES = ('estimate_table',)` and adds the value to its context under one key.

## 2. No member of `JobAccess` is missing for the local launch

Both children use `execute_on_local_resource(ctx, resource_id, command, environment, wait=False)` and
`ctx.services['job_access'].read('describe', resource_id)`. Both exist.

## 3. The tools of the old files, one by one (owner correction, 19 November 2026)

The first port removed the two library lookups and `reason` from the A107 parent on the ground that their arguments
are open. That ground was wrong: open arguments of an episode's own tool are not a defect; only what passes between
episodes is controlled. The two lookups are restored with their arguments unchanged. `reason` was restored and then
removed again by the owner's decision, on the episode's own purpose (its row below). Lines are of the committed
files (`git show d1b78591e:<file>`).

| Tool (old file, line) | What the episode's `goal.py` says | Its job after the port |
|---|---|---|
| A107 parent `knowledge_lookup` (`execution_job_submission/task.py:180`) | Goal: choose which permitted request to commission; capabilities, recorded inventory and timing information inform the choice. Old unit: "one lookup ... of a run-frozen instruction library" | Was done nowhere. Restored: `ToolCall('knowledge_lookup', {'operation', 'arguments'})`, operations `knowledge.search`, `.entry`, `.read`; what it returned is shown at the next decision |
| A107 parent `launch_instruction_lookup` (`task.py:186`) | the same; "Preserve ... pinned instructions" | Was done nowhere. Restored with the same arguments for `launch.instructions.search`, `.entry`, `.read`. Its fourth operation, `launch.instructions.select`, is bookkeeping (below) |
| A107 parent `reason` (`task.py:192`) | The goal names no interpretation. Old unit: "or one reasoning commit" | Removed (owner, 19 November 2026). `reason` commits typed scientific records (anchored terms, source subjects, contexts, observations, hypotheses, assessments, annotation updates). A launch parent chooses which resource to commission a launch on: it reads no source and weighs no evidence, so it has nothing to commit and nothing reads such a record. With it went the tool, its answer branch, its paragraph of the prompt, the `reasoning_scope` and `passed_record_refs` context, the rejection path of `action` and the tests of the commit. `scope` stays in the assignment form because the API child is commissioned with it |
| A107 parent `execution_capabilities` (`task.py:136`) | "Capabilities, recorded inventory ... inform the choice" | Kept. It was never a model choice: `decide` issues it as the first unit |
| A107 child `exec_command` (`local_job_execution/task.py:123`) | Old goal: "write and run the shell commands that bring about the requested endpoint ... and retain the receipt of each command" | Not restored: the owner's rule is that no model writes a command. Starting the requested job is `launch_job` (code, the assignment's argv). Retaining the receipt is bookkeeping (below). Writing scripts, preparing an environment and staging inputs (`target=coordinator`) are done nowhere (item 5). Bringing about `completed_job_outputs` is not a launch's: it ends at handoff (item 6) |
| A110 child `exec_command` (`local_job_execution/task.py:112`) | Old goal: "Execute the frozen request locally and retain its receipts" | the same as the A107 child |
| A110 parent `execution_capabilities` (`task.py:81`) | as the A107 parent | Kept; issued by code. The A110 parent had no other tool, so nothing was removed from it. Its read of the estimate table was not a tool (item 1) |

Bookkeeping and provenance, done by code at the end of the unit that produced the result, not offered as choices:

- **Pinning a launch-instruction section** (`launch.instructions.select`). In the committed A107 parent the model could
  choose it, and its result reached no commission (`messages/msg_to_child.py` read only the commissioner's pins): it
  earned nothing and changed no next step. Now `launch_instruction_lookup` pins the section at the end of a completed
  `launch.instructions.read` (the section's identity and digest, `outcome['pinned']`), the summary gathers the pins,
  and `msg_to_child` adds them to the instructions the commissioner pinned (checked by the library's
  `retain_inherited_selection`), so they travel to the launch child with the request. This wiring is new. Every
  section the model reads is pinned; the model no longer chooses a subset of what it read.
- **The receipt of a command** (the old children saved `ctx.store.artifact(canonical(receipt))` and an
  `operation_ref` inside `exec_command`). The record of a launch is now written by `job_access` in the launch unit:
  the `JOB_LEDGER` handoff row and the reply artifact, both produced by the unit.
- **Looking again at an uncertain submission instead of launching twice** (old prompt text). The job handle is
  derived from the unit's operation key; a unit that runs again takes up the job it started.

The A107 parent's request, as recorded in the real-model runs of branch 1b (`request.json` of the parent's call;
characters of the instructions, of the context and of the answer schema as compact JSON):

| State | Run | Instructions | Context | Answer schema | Actions |
|---|---|---|---|---|---|
| committed file (`next_decision`, `runs/lchg2_2.log`) | none | 2881 | 3856 | not measured | commission, 7 library operations, `reason` |
| first port: commission only | `runs/lchg2_7` | 2180 | 1321 | 296 | `commission_launch` |
| lookups and `reason` restored | `runs/lchg2_15` | 3634 | 1626 | 3373 | `commission_launch`, 3 + 3 library reads, `reason` |
| lookups kept, `reason` removed | `runs/lchg2_19` | 3312 | 1378 | 3088 | `commission_launch`, 3 + 3 library reads |

The request with `reason` never carried the Store's reasoning schema: the commit travelled as JSON text described only
as an object. So removing `reason` took out one answer branch (285 characters), its paragraph of the prompt and two
context keys, not a schema.

The first port had overwritten an uncommitted change another agent made to this `task.py` at 16:56 on 19 November
(`_TRANSPORT`: `open_records_as_text` set to `True`, so that the reasoning commit travels as text). That change served
`reason` only. With `reason` removed no action has an open record, and `_TRANSPORT` has the committed value (`False`).
The agent who made that change should know its subject is gone.

## 4. Moved: the flux-balance binding check of a configured local resource (A110)

The old A110 local child checked the bindings of its configured resource
(`validate_flux_balance_bindings(configuration['native_flux_balance'])`, settings `resources`). The ported child has no
resource configuration in its settings (its resource is what `job_access` describes). The check is now in the parent's
`_bound`, which reads the configured resources before the lookup. A test runs it through `next_decision`
(`tests/test_local_submission_stepped.py`).

## 5. Inputs of a job are not staged (the same open point as `BRANCH_FIX_BLOCKERS_a103.md`, item 3)

The local child receives the request alone. Its form has no `record_refs` and no `scientific_task` field any more and
`msg_to_child` of each parent passes neither to `launch_local`. Both parents still admit `record_refs` and
`scientific_task` from their head (the A107 parent passes them to its API child). A job runs on what its argv names.

## 6. An assignment with no `requested_job_handoff` requirement (the same as `BRANCH_FIX_BLOCKERS_a103.md`, item 4)

The child's completion target is the credit of the handoff requirements. A request whose only requirements are of
other kinds has a target of zero and the completion controller refuses it. Before the port the target was the sum of
all requirements.

## 7. Changes of settings and of what the model is shown

- The local children read one setting, `task_yield_profiles`. `resources`, `initial_information`,
  `coordinator_workspace`, `launch_instructions_directory` and `tool_knowledge_directory` are no longer read by them.
- The A110 parent reads `settings['initial_information']` as a required setting (it was `settings.get(
  'initial_information', {})`); the inventory of one resource stays optional. The A107 parent reads the two library
  directories (`launch_instructions_directory`, `tool_knowledge_directory`); the A110 parent, which had no lookup
  tool, reads neither.
- A configured resource is shown without `tool_names` (a local or HPC resource offers no tool to a model), without
  `knowledge_entry_ids`, and in A110 without `ssh_argv` and `scheduler` (they served the writing of commands).

## 8. Still raising in the A107 parent (unchanged by this port)

- A launch assignment with an API request: `job_access.validate_assignment` and `capabilities`
  (`NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')`, `task.py`).
- An unknown request version: `NotImplementedError('unplaced:a107_blast_execution.BLAST_GRADED_REQUEST_SCHEMA:...')`
  (`messages/read_from_parent.py`).

## 9. Not ported here

`hpc_job_execution` and `api_job_execution` of both trees, and the nested trees
`hpc_work_planning/execution_job_submission/**` and
`hpc_work_planning/hpc_allocation_execution/execution_job_submission/**` of both axes: their files still name the old
shell tool.

## 10. The intermittent refusal `local_job_boundary_unavailable`

Not seen. Eight real local launches that were meant to succeed ran in these runs (two offline and two with the model
per axis); every one was handed off. The one launch per axis that the refusal test sends to a resource whose policy
asks for more memory than the machine has was refused, as that test intends.

## 11. Failures seen in neighbouring tests, not caused by this port and not changed

- `root/a110/biochemical_feasibility_evidence/tests/test_episode.py` did not collect at 17:11 on 19 November
  (`ImportError: cannot import name 'credit_binding'` from `execution_result_acquisition/credit.py`,
  `runs/lchg2_11.log`). That folder is not part of this port: another agent was rewriting it at that minute (its
  `credit.py`, `goal.py`, `task.py`, `messages/*` and tests carry times from 17:11 to 17:13; no document names the
  agent). Run again after those writes, the file collects and its tests pass (`runs/lchg2_16.log`).
- `root/a107/partner_presence_evidence/tests/test_binding.py::test_the_selectable_names_are_the_names_the_child_declares[hpc]`
  fails on the `hpc_work_planning` return fields (`hpc_credit`, `hpc_model_ref`, `hpc_accepted_obligations`). The other
  21 tests of that folder and of `a110/.../tests/test_decision_schema.py` pass, the `launch` case among them.
  `runs/lchg2_12.log`.
- `docs/EVIDENCE_AXIS_LEDGER.md` was not edited (it is modified in the working tree by other work).
