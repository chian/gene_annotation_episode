# Resource port recipe: `resource_work_submission`, its resource children and `resource_result_acquisition` (19 November 2026)

The worked example is A102, under `root/a102/structural_homology_evidence/`:

- `resource_work_submission/local_resource_work_execution` (the launching child on a local resource),
- `resource_work_submission` (the parent that chooses the resource and commissions the launch),
- `resource_result_acquisition` (the fetch of a handed-off job's result files).

All three run with the real model (`runs/fixres_19`, `fixres_20`, `fixres_21`) and offline through `next_decision`
and `run_unit` (`runs/fixres_18`). This file says how to apply the same to the copies in A101 and A103 and to the
`hpc` and `api` resource children (section 9 lists what each axis has). Nothing outside A102 was edited. One
library file was added (`episode_support/jobs/job_wait.py`, the wait runner); none was changed.

Read first: `AGENTS.md`, `TRANSFORM_GUIDE.md`, `BINDING_CONTRACT.md`, `LAUNCH_MONITOR_EXTRACT_MECHANICS.md`
("Provided now"), `LOCAL_WRAPPER.md`, `WAIT_ACTION.md`, `LAUNCH_PORT_RECIPE.md` (the same port for
`execution_job_submission`), and the A102 files named below with their tests.

## 1. The rules the port carries out

1. **The model chooses an action; code executes it, and no action executes text the model wrote.** The model
   answers with one action of a fixed set, as structured JSON. Whatever starts or touches a job takes its
   arguments from fixed sets code built (a declared resource id, a held handoff row, a number in a range of the
   settings): no episode file offers a command, a script, a path or an environment, so no `exec_command`, and no
   `resource_tool` / `resource_operation` / `adapter_tool` that passes model-written arguments to an adapter tool
   (`job.launch {job: object}` is the same hole).
   **Open arguments to an episode's own tool are not a defect** where the tool is for them: the library lookups
   of the submission take the model's query, as they did. Only what crosses between episodes (`msg_to_child`,
   `final_to_parent`, what `read_from_child` shows) must be controlled. A tool is kept when the episode's own
   purpose has a use for it, not because the old code had it: these episodes have no `reason` (section 4).
2. **One library function per resource kind starts work.** The local one is
   `episode_support/jobs/resource_local.py`, `execute_on_local_resource` (`LOCAL_WRAPPER.md`); it is owned by the
   A103 launch fixer and is reused, not copied. An episode never calls `job_access.launch` or `job_access.run`
   itself and never passes a job to `resource_adapter.execute(..., 'job.launch', ...)`.
3. **Controlled messaging.** Assignments and returns hold numbers, booleans, fixed vocabularies and record
   references. The work travels as a record reference (section 2). Returns have no `qualification`, no
   `interpretation`, no `execution_handoff` record written by anyone: the job ledger rows are the handoff.
4. **Credit comes from held records.** `internal_summary` reads the held `JOB_LEDGER` rows with
   `episode_support/jobs/job_records.py` (`job_rows`); `credit.py` counts what the summary found. No service is
   asked for a credit (`credit_view` is not a member of anything).
5. **The prompt is the design.** Print the request `decide` builds (`next_decision`) before and after and judge
   it: what the episode is for, where the assigned work or handoff is, which actions exist, what earns credit; the
   assignment once; no old-runner text; no controller internals.
6. **Library files are not stripped.** Section 10 lists the library files that mention `exec_command`; they stay.

## 2. The work is a record, and where a generic `{argv, environment}` goes

The old launch assignment carried the job as open records the head's model wrote (`job_request`,
`adapter_assignment.requested_job = {'argv', 'environment'}`), copied unchanged by each `msg_to_child`
(`AUDIT_MODEL_EXECUTION.md`, V6). In the port:

- **The work is one record the commissioner holds**: a JSON artifact
  `{"command": [argv...], "environment": {name: value}, "inputs": {file name: artifact reference}}`. It is passed
  in the assignment field `work_refs` (`record_refs`, one reference) and the artifacts it stages in `input_refs`.
  `resource_work_submission` never reads it; it passes both references on to the resource child.
- **Only the launch tool reads it**, through custody, and hands it verbatim to the wrapper of its kind:

  ```python
  async def launch_work(arguments, ctx):
      work = json.loads(ctx.store.get_artifact(arguments['work_ref']))
      return await execute_on_local_resource(ctx, arguments['resource_id'], work['command'], work['environment'],
                                             wait=False, inputs=work['inputs'], name='work')
  ```

  `arguments` come from `action`, which takes them from the summary (the assignment), never from the model's
  answer. The model's answer for a launch is `{"action": "launch_work"}` and nothing else.
- **A generic `{argv, environment}` branch is therefore handled in exactly one place**: the wrapper
  (`execute_on_local_resource`, line `# INSPECTION POINT`). Today it passes the command through. Controls of the
  command, and the compilation of a controlled job form (a `native_*` form, or a tool name with operand
  references) into an argv, are added there by the owner; an episode adds no check of the command and does not
  wrap the wrapper. The practical-assignment validator (`practical_execution_records.validate_assignment` and its
  `GENERIC_REQUESTED_JOB_SCHEMA`) is no longer called by the ported A102 resource episodes; it is not edited.
- **Who writes the work record.** In the tests the run's caller writes it (`store.artifact(...)`) and passes it as
  an entry record. In the tree, the scientific head must write it with code, from a controlled choice of its
  model; the A102 head has no such action yet (section 11, open item 2).

## 3. What the real services give, and what the old code asked for

| Old call in the carried episodes | Real member |
|---|---|
| `job_access.begin_command` / `run_command` / `finish_command` behind `exec_command` | `await execute_on_local_resource(ctx, resource_id, command, environment, wait=False, inputs=, name=)` (returns what `JobAccess.launch` returns: `status`, `job`, `handoff_ref`, ...) |
| `job_access.check_handoff(handoff, key=...)`, `adapter.check_handoff(handoff, held, key=...)`, `resources.check_handoff(handoff, ctx.operation_key)` | `ctx.services['job_access'].check(ctx, handoff_ref)`, or through the adapters `await ctx.services['resource_adapter'].check_handoff(ctx, {'resource_selection': {'resource_id': ...}, 'handoff_ref': ...})` |
| `adapter.can_check_handoff(resource_id)` | not a member: a handoff's resource is bound or it is not (`is_bound(resource_id)`); an unbound one raises `LookupError('resource_not_bound:...')` in the service |
| `resources.execute(assignment, name, arguments, ctx.operation_key)` | `await ctx.services['resources'].execute(ctx, selecting, 'job.fetch', {'handoff_ref': ..., 'names': [...]})` with a fixed tool name and code-built arguments |
| `resources.read('catalog', assignment)` and the other reads with the results assignment (`KeyError: 'resource_selection'`) | the selecting record is `{'resource_selection': {'resource_id': <the resource of the held handoff row>}, 'handoff_ref': <the row>}`, built from the held row; the old described `handoff` is not passed at all |
| `adapter.credit_view(assignment, held)`, `resources.credit_view(assignment)`, `ctx.store.refs()` for it | none: `credit.py` over the summary of the held job ledger rows |
| `adapter.facts(assignment)` for the handoffs of every adapter | `job_records.job_rows(view.records)` in `internal_summary`; `adapter.facts({'resource_selection': {...}})` only for the reading of one resource |
| `validate_report`, the `report` tool, `validate_form_not_built:A102` | dropped: the return is controlled fields built by `final_to_parent` |

Decisions read through the read handle (recorded): `job_access.read('resources')`;
`resource_adapter.read('declared_capabilities')`, `.read('adapter_capabilities')`, `.read('bound_resource_ids')`.

## 4. The three episodes as ported (A102)

| | `local_resource_work_execution` | `resource_work_submission` | `resource_result_acquisition` |
|---|---|---|---|
| `SERVICES` | `('job_access',)` | `('resource_adapter', 'instruction_libraries')` | `('resources', 'job_access')` |
| Job actions (arguments from fixed sets) | `inspect_resource`; `launch_work` (until a handoff row is held); `check_handoff {handoff_ref}` (once one is held) | `inspect_resource {resource_id}`; `launch_work {resource_id}` (a `ChildCall` of `launch_<kind>`, until a handoff row is held); `check_handoff {handoff_ref}` | `check_job`; `fetch_results` |
| `wait {seconds}` (`WAIT_ACTION.md`) | once a handoff row is held | not offered | always (the handoff row is assigned) |
| Lookups with the model's own arguments, as they were | none | `knowledge_lookup {operation, arguments}`, `launch_instruction_lookup {operation, arguments}` | none |
| `reason` | none | none | none |
| Assignment | `version`, `resource_id`, `work_refs`, `input_refs`, `handoff_unit`, `check_unit` | `version`, `work_refs`, `input_refs`, `allowed_kinds` (subset of `api`, `local`, `hpc`), optional `resource_id`, optional `job_refs` (the rows of an earlier launch, passed back), `completion_target` | `version`, `job_refs` (the handoff row and held check rows), `requested_names` |
| Credit | `handoff_unit` for a held handoff row + `check_unit` for a held receiving check (a `check_handoff` row) whose state is not `unknown` | the same two units, each half of `completion_target` (`read_from_parent`), over the rows it holds | 1 for each requested file whose artifact it holds |
| Controller | completion, target `handoff_unit + check_unit` | completion, target `completion_target` | completion, target `len(requested_names)` |
| Settings | `cost`, `parameters`, `wait_seconds` | `cost`, `parameters` | `cost`, `parameters`, `wait_seconds` |
| Return (required) | `credit`, `finding {job_state, result_available}`, `handoff_refs`, `check_refs` | `credit`, `finding {job_state, route_kind}`, `handoff_refs` | `credit`, `finding {job_state, fetch_outcome}`, `result_refs`, `closure_refs` |
| Return (selectable) | none | `check_refs` | `check_refs` |

Every `finding` value is a `ChoiceField` vocabulary or a boolean. `job_state` is `not_launched` / `not_checked` or
one of `episode_runtime.job_access.STATES`. A lookup and a wait earn nothing.

**No `reason` (owner, 19 November 2026).** `reason` commits typed scientific records (anchored terms, source
subjects, contexts, observations, hypotheses, assessments, annotation updates). These episodes perform an execution
act (launch, check, fetch); none reads a source or weighs evidence for an annotation, so there is nothing for them
to commit and nothing reads such a record. With it go the `scope` and `scope_refs` assignment fields it needed and
the Store's reasoning commit schema in the request. The same holds for the A102 launch parent
`execution_job_submission`, whose `reason` was removed with this port.

A request the resource refuses is the returned outcome `{'status': 'failed', 'failure': {'code', 'detail'}}` of
its unit (as `JobAccess` returns it). With `cost` 0.5 the completion controller stops an episode after two short
units in a row that earn nothing (seen in all three episodes); it stops at once when the target is reached. Its
forecast falls with the measured progress time, so a wait weighs more than a short unit (`WAIT_ACTION.md`, "Credit
and stopping").

**The request** (recorded `request.json` of the first decision, `runs/fixres_19` to `fixres_21`): 3,472 bytes for
the local child, 3,558 for the acquisition and 13,253 for the submission, whose two lookups bring the libraries'
operations and input schemas into `context.library_operations`. With `reason` each was 167 to 176 KB, of which the
Store's reasoning commit schema was 85,735 characters before indentation. A lookup's `arguments` travel as JSON
text.

## 5. Port a `local_resource_work_execution`, file by file

Copy the A102 files into the axis's folder and make them the axis's own (binding path, texts). The files:

| File | What it holds after the port |
|---|---|
| `goal.py` | the episode's purpose sentence, without the old tail ("Ordinary operations are tools; iteration belongs to this shared Episode ... Return the original parent-defined typed form. Only the configured local controller governs continuation"); `UNIT` names the kinds of unit the episode has |
| `messages/read_from_parent.py` | the form of section 4; `read_from_parent` returns `resource_id`, `work_ref`, `input_refs`, `credit_units`, `completion_target`. The practical assignment (`workspace`, `initial_context`, `progress_requirements` with `context_cwd` / `path_exists` / `command_exit` predicates) described a shell session and is not a field |
| `messages/internal_summary.py` | `job_rows(view.records)`: each held handoff row with the state of its latest held check row and its receiving checks (the rows `check_handoff` units wrote); `handoff_held`, `usable_check_held`; the description a reading returned; `actions` (`action`, `status`, `failure` code) |
| `credit.py` | the two units over `handoff_held` and `usable_check_held` |
| `yield_estimator.py` | `CompletionYieldController(name, initial_credit, settings['cost'], parent_input['completion_target'], settings['parameters'])` |
| `task.py` | `INSTRUCTIONS` (purpose, assigned work, actions, credit); `answer_schema(summary, wait_seconds)` (a closed object `{'selection': {'anyOf': [...]}}`, one branch per offered action); `decide`; `selected_action` (pure: validates the answer against the same schema, a wait's range included; `Rejected` otherwise) and `action` (hands it `ctx.settings['wait_seconds']`); the tools `inspect_resource`, `launch_work`, `check_handoff` and `wait` (`WAIT_ACTION.md`) |
| `messages/final_to_parent.py` | the forms of section 4; the rows from the summary |
| `tests/` | a world module (Store with the work record and its input; `job_services(configuration)` with one local resource), a stepped test, the model-run test, the binding test |

Delete from the episode: the tool definition and schema of the command tool, `EXEC_INSTRUCTION`,
`TerminalExecution` and `terminal_artifact_paths` use, `publish_receipt`, the `capabilities()` check of
`settings['resource_capabilities']`, `reason` with the reasoning schema and `REASONING_COMMIT_REQUIREMENT`, the
settings `resources`, `initial_information`, `coordinator_workspace`, `launch_instructions_directory`,
`tool_knowledge_directory`, `task_yield_profiles`, and every `BLOCKED-ON-*` note.

A101's and A103's local children have no command tool of their own; they have `resource_tool` /
`resource_operation` with model-written arguments for an adapter tool, `prepare_resource_assignment`, `reason`,
`wait`, `report` and the two lookups (section 9). The adapter tool is replaced by the job actions of section 4;
the old event-condition `wait` becomes the `wait` of `WAIT_ACTION.md`; `reason` and `report` are not actions
(section 11); whether a launching child keeps its lookups is the owner's call per episode (A102's local child had
none).

## 6. Port a `resource_result_acquisition`, file by file

| File | What it holds after the port |
|---|---|
| `messages/read_from_parent.py` | `version`, `job_refs`, `requested_names`; the message is not read |
| `messages/internal_summary.py` | the handoff row among the held rows; its check and closure rows by time; `job_state`, `result_available`; `acquired` (each requested name a held closure row lists, with its artifact reference); `closure_refs`; the check rows of its own `check_job` units; `actions` |
| `credit.py` | `sum(1 for item in summary['acquired'] if records.holds(item['ref']))` |
| `yield_estimator.py` | completion controller, target `len(requested_names)` |
| `task.py` | `answer_schema(wait_seconds)`: `check_job`, `fetch_results`, `wait {seconds}`; the job tools call `resources.check_handoff(ctx, handoff)` and `resources.execute(ctx, handoff, 'job.fetch', {'handoff_ref', 'names'})` with `handoff = {'resource_selection': {'resource_id': summary['job']['resource_id']}, 'handoff_ref': ...}`; `wait` calls the wait runner; `decide` reads `adapter_capabilities` for the resource's availability |
| `messages/final_to_parent.py` | the forms of section 4; `fetch_outcome` from the last fetch unit (`not_requested`, `results_acquired`, `results_not_available`, `result_not_in_catalog`, `request_failed`) |

A fetch of a job that has not ended is a failed unit (`results_not_available`); the model may `wait` and fetch
again (real model, `runs/fixres_20`: check, failed fetch, two waits of 5 seconds, fetch). `SERVICES` loses
`native_events`.

## 7. Port a `resource_work_submission`, file by file

| File | What it holds after the port |
|---|---|
| `messages/read_from_parent.py` | the form of section 4; `launch_units` (the even split of `completion_target`) |
| `task.py` | `capabilities_of(declared, adapter_capabilities)`, `launchable(summary, capabilities, bound)` (the old `allowed_children` and `_permitted`: bound, has tools, not `unavailable`, a permitted kind, the fixed resource when one is fixed); `answer_schema`; `decide`; `selected_action` (pure: validates and returns the `ToolCall` or `ChildCall`) and `action` (reads the capabilities, calls it); tools `inspect_resource` (the old `inspect_resource` with its failure codes `resource_not_bound`, `resource_unavailable`, `resource_authentication_required`, `resource_availability_unknown`), `check_handoff` (`await resource_adapter.check_handoff(ctx, {...})`), `knowledge_lookup` and `launch_instruction_lookup` (`ctx.services['instruction_libraries'].execute(operation, arguments)`; the operations' names come from the libraries' `catalog()`) |
| `messages/msg_to_child.py` | one commission for every slot: fixed objective, empty message, `{'version', 'resource_id', 'work_refs', 'input_refs', 'handoff_unit', 'check_unit'}`, empty selection |
| `messages/read_from_child.py` | `{'slot', 'child_credit', 'job_state'}`; the returned rows are held from the return on and read by `internal_summary` |
| `messages/internal_summary.py` | the jobs from the held rows (with `route_kind` from the handoff row), `handoff_held`, `usable_handoff_held`, `commissions`, `inspections`, `lookups` (each lookup with its arguments and result), `actions` |
| `credit.py` | the two launch units over `handoff_held` and `usable_handoff_held` |
| `messages/final_to_parent.py` | the forms of section 4 |

`SERVICES` loses `native_events` and gains `instruction_libraries` (the run's caller names the two frozen library
directories in `job_services(configuration)`; the episode's settings lose them). A selection a
`launch.instructions.select` lookup returns has no consumer now: the resource child writes no launch and its
assignment has no `launch_instructions` field.

## 8. `hpc_resource_work_execution` and `api_resource_work_execution`: custom library code per kind

The episode shape is the local one (section 5): the same assignment form, the same actions, the same
credit, controller and return. Only the launch tool differs: it calls the wrapper of its kind, which is custom
library code and the single inspection point for that kind.

- **hpc**: `episode_support/jobs/resource_hpc.py`, one public function (named in `LAUNCH_PORT_RECIPE.md`, section
  6: `execute_on_hpc_resource(ctx, resource_id, command, environment, *, wait, allocation, inputs=None,
  estimates=None, name='job')`). It composes the job of `PbsSshRoute` (`{'mode', 'script', 'arguments', 'env'}`)
  from the work record and the allocation by code, and calls `JobAccess.launch`. It is not written yet. The HPC
  child's assignment adds the controlled allocation fields the commissioner fixed (numbers; a queue and an
  account from fixed vocabularies), and `launch_work` gets one `enum` field for each choice the assignment leaves
  open. The receiving check is `job_access.check(ctx, handoff_ref)` unchanged.
- **api**: `episode_support/jobs/resource_api.py`, one public function over `ApiJobRoute`
  (`episode_support/jobs/api_job_route.py`, `API_PORT_RECIPE.md`). The work record of an API launch is the
  service's request (operation from the route's fixed set, subject references, numeric parameters), composed by
  library code; the model still answers `{"action": "launch_work"}`.

Until a wrapper exists, the episode of that kind is not ported: do not call `job_access.launch` directly and do
not put a stand-in in its place. In A102 the `api` and `hpc` resource children still have their old forms, so a
commission of either by the ported parent is refused by the child's own assignment form (a wrong commission
fails); the parent offers a resource only when it is bound, so the A102 tests, with one bound local resource,
never reach them.

## 9. What each axis has (`ls` of the folders, 19 November 2026)

Each of a101 (`sequence_homology_evidence`), a102 (`structural_homology_evidence`) and a103
(`gene_context_evidence`) has the same five folders; a104 to a110 have none:

```
<head>/resource_result_acquisition
<head>/resource_work_submission
<head>/resource_work_submission/api_resource_work_execution
<head>/resource_work_submission/hpc_resource_work_execution
<head>/resource_work_submission/local_resource_work_execution
```

Each holds `goal.py`, `task.py`, `credit.py`, `yield_estimator.py`, `episode.py`, `messages/` (`read_from_parent.py`,
`internal_summary.py`, `final_to_parent.py`; the parent also `msg_to_child.py`, `read_from_child.py`) and `tests/`.

| Episode | State today | `SERVICES` | Tools today (the adapter tools with model-written arguments are replaced; the event `wait` becomes `wait {seconds}`; `reason` and `report` go; the submission keeps its lookups) |
|---|---|---|---|
| a102 `resource_result_acquisition` | ported | `resources`, `job_access` | |
| a102 `resource_work_submission` | ported | `resource_adapter`, `instruction_libraries` | |
| a102 `.../local_resource_work_execution` | ported | `job_access` | |
| a102 `.../api_resource_work_execution` | not ported (old form; needs the api wrapper) | `resource_adapter`, `native_events` | `prepare_resource_assignment`, `resource_capabilities`, `resource_operation`, `reason`, `wait`, lookups |
| a102 `.../hpc_resource_work_execution` | not ported (old form, raises `NotImplementedError`; needs the hpc wrapper) | `resource_adapter` | `resource_capabilities`, `resource_inspect`, `resource_check_handoff`, `adapter_tool` |
| a101 `resource_result_acquisition` (279 lines of `task.py`) | old form; calls `credit_view` (4 sites) | `resources`, `native_events`, `instruction_libraries` | `resource_tool`, `reason`, `wait`, `report` |
| a101 `resource_work_submission` (417) | old form; `can_check_handoff` (2), `NotImplementedError` (2) | `resource_adapters` | `resource_capabilities`, `resource_inspect`, `resource_check_handoff`, `reason`, `knowledge_lookup`, `launch_instruction_lookup` |
| a101 `.../api_resource_work_execution` (325) | old form; `credit_view` (3) | `resource_adapter`, `native_events` | `prepare_resource_assignment`, `resource_capabilities`, `resource_operation`, `reason`, `wait`, lookups |
| a101 `.../hpc_resource_work_execution` (259) | old form; `NotImplementedError` (4) | `resource_adapter` | `resource_capabilities`, `adapter_tool`, `reason` |
| a101 `.../local_resource_work_execution` (290) | old form; `credit_view` (4) | `resources`, `native_events`, `instruction_libraries` | `resource_tool`, `reason`, `wait`, `report` |
| a103 `resource_result_acquisition` (303) | old form; `credit_view` (4) | `resources`, `native_events`, `instruction_libraries` | `resource_tool`, `reason`, `wait`, `report` |
| a103 `resource_work_submission` (378) | old form; `credit_view` (3), `can_check_handoff` (2) | `resource_adapter`, `native_events` | `resource_capabilities`, `resource_inspect`, `resource_check_handoff`, `reason`, `wait`, lookups |
| a103 `.../api_resource_work_execution` (347) | old form; `credit_view` (3) | `resource_adapter`, `native_events` | `prepare_resource_assignment`, `resource_capabilities`, `resource_operation`, `reason`, `wait`, lookups |
| a103 `.../hpc_resource_work_execution` (322) | old form; `credit_view` (3) | `resource_adapter`, `native_events` | the same seven |
| a103 `.../local_resource_work_execution` (325) | old form; `credit_view` (3) | `resource_adapter`, `native_events` | the same seven |

No a101 or a103 resource episode mentions `exec_command`; their open door is the adapter tool with model-written
arguments. Order of work per axis: the local child, a real model run; the acquisition; the parent over the local
child; then the head (next paragraph). The `hpc` and `api` children wait for their wrappers.

**The head.** The head commissions the parent and the acquisition, so its tables change with their forms (A102:
`task.py` `CHILD_ASSIGNMENTS['resource_launch']` = `work_refs`, `input_refs`, `allowed_kinds`, optional
`resource_id`, `job_refs`; `CHILD_ASSIGNMENTS['resource_results']` = `job_refs`, `requested_names`;
`RETURN_FIELDS` of both = `('check_refs',)`; `messages/msg_to_child.py` `resource_launch` and `resource_results`;
the sample commissions of `tests/test_episode_binding.py`). A selection enum must not be empty (the endpoint
refuses an empty `enum`), which is why each of the two children keeps one selectable field.

## 10. Library files that mention `exec_command` (not deleted, not stripped)

These are library code and documents; the ported episodes no longer call the shell-era functions among them. They
are listed for the owner's later decision, nothing here proposes deleting them.

- `episode_support/acquisition/native_terminal_transport.py`
- `episode_support/findings/{biochemical_feasibility,evolutionary_history,gene_context,partner_presence,sequence_homology,structural_homology}_evidence/terminal_scientific_evidence.py`
- `episode_support/jobs/local_execution/{biochemical_feasibility,gene_context,partner_presence,sequence_homology,structural_homology}_evidence/terminal_execution.py`
- `episode_support/records/{biochemical_feasibility,evolutionary_history,gene_context,partner_presence,sequence_homology,structural_homology}_evidence/practical_execution_records.py`
- `episode_support/records/local_execution/{evolutionary_history,partner_presence,sequence_homology}_evidence/native_database_terminal_custody.py`
- `episode_support/instructions/launch/local-operations.md` and its copies under `evolutionary_history_evidence/`, `gene_context_evidence/`, `partner_presence_evidence/`, `sequence_homology_evidence/`

## 11. What happened to each old tool of the A102 episodes, and open items

Line numbers are of the files at `HEAD` (`d1b78591e`) under `root/a102/structural_homology_evidence/`.

| Old tool (file:line) | What it did | Now |
|---|---|---|
| `exec_command` (`resource_work_submission/local_resource_work_execution/task.py:215`) | ran the shell command the model wrote | gone; `launch_work` starts the assigned work record through `execute_on_local_resource` |
| `resource_capabilities` (local `task.py:255`) | listed the declared capabilities of the settings | the selected resource is in `context.resource`; `inspect_resource` reads the job services' description |
| `resource_inspect` (local `task.py:260`) | the declared capability of a resource the model named | `inspect_resource` (the assigned resource) |
| `resource_check_handoff` (local `task.py:274`) | receiving check of a handoff record the model wrote | `check_handoff {handoff_ref}` on a held row |
| `reason` (local `task.py:293`; acquisition `task.py:260`; parent `task.py:235`) | the model's typed reasoning commit through `commit_reasoning`, with the Store's reasoning commit schema in the request | removed from all three (owner: an execution act reads no source and weighs no evidence, so there is nothing to commit and nothing reads such a record; section 4) |
| `resource_tool` (`resource_result_acquisition/task.py:226`) | one tool of the assigned adapter with arguments the model wrote. The offered catalog was `resource.capabilities` (230) plus the adapter's own tools (254; with the real adapters `job.launch`, `job.check`, `job.fetch`, `job.cancel`); its `resource.inspect` (233) and `resource.check_handoff` (244) branches were reachable only if an adapter listed those names | `check_job` and `fetch_results` (the file names come from the assignment); the resource's availability is in `context.job`; `job.launch` and `job.cancel` are not actions of an acquisition |
| `wait` (acquisition `task.py:272`; parent `task.py:240`) | `selected_wait(native_events, condition)`: waited on a model-written `event_condition_v1` (registered native event targets, each `{handle, event, after_cursor}`, and an optional `reconsider_at` time) and returned the wake; earned nothing | replaced by the owner's `wait {seconds}` (`WAIT_ACTION.md`) in the acquisition and in the local child; not offered by the parent. `NativeEvents.wait(ctx, condition)` can serve a later event runner: a local job's event target is in its handoff row |
| `report` (acquisition `task.py:278`) | meant to record an open `interpretation` object the model wrote, shown back to it as `current_report_update` and returned in the selectable `interpretation` field; it raised `NotImplementedError('validate_form_not_built:A102')` on its first line, so it never recorded anything | not an action (owner: provenance, not a decision). The audit trail of an acquisition is written by code already: the closure row of `fetch_results` (`JOB_LEDGER`, event `closure`: outcome, state, each result's name, artifact reference, bytes and sha256, the handoff row, and the route's reply as its source artifact) and the check rows. The A102 head did nothing with a returned `interpretation` but list the field's name (`messages/read_from_child.py`: `'returned': sorted(set(result) - {'credit', 'finding'})`) |
| `resource_capabilities` (`resource_work_submission/task.py:182`) | every declared capability | `context.resources` in every request (recorded service reads) |
| `resource_inspect` (parent `task.py:189`) | one declared resource, with its failure codes | `inspect_resource {resource_id}`, same codes |
| `resource_check_handoff` (parent `task.py:206`) | receiving check of a handoff record the model wrote | `check_handoff {handoff_ref}` on a held row |
| `knowledge_lookup` (parent `task.py:245`), `launch_instruction_lookup` (parent `task.py:250`) | one operation of a frozen library with the model's arguments | **kept**, arguments unchanged, through the `instruction_libraries` service |

Left the forms: `execution_handoff`, `execution_handoffs`, `adapter_facts`, `interpretation`, `qualification`
(records and text written as open values; the job ledger rows are the handoff), and the practical requirements of
the local child (`progress_requirements`, `completion_keys`, `initial_context`, receipts: predicates over a shell
session; the handoff is now two held rows).

Open items:

1. The A102 `api` and `hpc` resource children are not ported (section 8); the hpc and api wrappers do not exist.
2. The A102 head offers its model `work_refs` as held references but has no action that writes a work record from
   a controlled choice, so the head cannot yet commission `resource_launch` end to end.
3. `resource_result_acquisition` gives one credit per requested file; the head has no unit setting for it.
4. The finding's `route_kind` is the route kind of the handoff row (`local`, `pbs`, `api`), not the declared
   capability kind (`local`, `hpc`, `api`).
5. A wait is long beside short units and the completion controller's forecast falls with measured time: where a
   model is expected to wait, the episode's `cost` setting must allow it (`WAIT_ACTION.md`).

## 12. Tests to write and run

Per episode: a world module in `tests/` (real Store, real `job_services`, real local jobs), a stepped test
(`next_decision` for the request; the episode's own `action` for a router answer; `run_unit` for the unit; the
controller's stop; the admitted result; `resume`), and one `@pytest.mark.model_run` test (`link(...).run()`, the
result admitted, the launched job's result fetched by a later run through the returned handoff row, `resume` with
no new model call). The stepped test of the request asserts `violations(request.output_schema) == []`
(`episode_support/model_exchange/tests/provider_schema_rules.py`), the four headings of the instructions, that
the work reference appears once, and that no old-runner word is in the request. A parent's child unit asks the
child's model, so the parent's stepped test covers its tools and the commission it builds (admitted by the child's
own forms) and the model-run test covers the child unit.

```
# offline
bash tools/one_workflow.sh --slot <slot> runs/<fresh> -- env HOME=$PWD/runs/<fresh>/home \
  http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 PYTHONDONTWRITEBYTECODE=1 eatmydata \
  .venv/bin/python -m pytest -p no:cacheprovider --basetemp=runs/<fresh>/tmp <episode folder>
# real model
bash tools/one_workflow.sh --slot <slot> runs/<fresh> -- env HOME=$PWD/runs/<fresh>/home \
  CODEX_HOME=/home/chia/.codex PYTHONDONTWRITEBYTECODE=1 eatmydata .venv/bin/python -m pytest \
  -p no:cacheprovider --basetemp=runs/<fresh>/tmp <model-run test file> -m model_run -v --tb=short -s
```
