# Extract port, group 3: what the port leaves open (19 November 2026)

Written by the porter of the seven `execution_result_acquisition` episodes of form 3 of `EXTRACT_PORT_RECIPE.md`
(workspace given, direct `access` calls):

- `root/a103/gene_context_evidence/execution_result_acquisition`
- `root/a103/gene_context_evidence/hpc_work_planning/execution_result_acquisition`
- `root/a103/gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`
- `root/a104/evolutionary_history_evidence/hpc_work_planning/execution_result_acquisition`
- `root/a104/evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`
- `root/a107/partner_presence_evidence/hpc_work_planning/execution_result_acquisition`
- `root/a107/partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition`

No file of `episode_support/` or `episode_runtime/` was edited, and no parent episode. Every episode runs on
`JobAccess.check` and `JobAccess.fetch` with a real local job (offline tests through `next_decision` and `run_unit`;
one real-model run per axis). The six copies inside `hpc_work_planning` were run against the local route only:
nothing remote was contacted.

## 1. Members of `JobAccess` the port would use

No member the port needs is missing. As in `BRANCH_FIX_BLOCKERS_a101.md` section 1, a bounded fetch would be
cheaper: `fetch(ctx, handoff_ref, names=[...])` reads each requested file whole into memory and writes it as one
artifact, so a requested interval of a large file costs the whole file. For the HPC copies this is the first thing
the remote fetch will meet (section 2).

## 2. What the HPC remote fetch will need (the HPC wrapper's job)

The episodes need nothing changed for a remote job: they call `check` and `fetch` on the handoff row they hold and
read windows from the fetched artifacts. What has to exist around them:

1. **A PBS handoff row has no job directory.** The commission's `workspace` is the job's directory, and the
   episode names each requested path by its path inside it (`read_from_parent.result_names`), because a route lists a
   job's results that way. `LocalJobRoute.submit` returns `native['directory']`; `PbsSshRoute.submit` returns
   `native = {'mode', 'name', 'job_id' or 'pid', 'submitted_at'}` with no directory. On a PBS route the directory is
   `<route workspace>/<handle>`: the commissioner has to build it from `job_access.read('describe',
   resource_id)['workspace']` and the handoff row's `job`. Wanted in the library (not edited here):
   `PbsSshRoute.submit` returning `native['directory']`, so that every commissioner writes
   `workspace = handoff['detail']['native']['directory']` whatever the route.
2. **Only files inside the job's directory can be fetched.** `PbsSshRoute.results` lists the regular files below
   `<workspace>/<handle>` and `read` refuses any other name (`file_name_outside_the_job_directory`). The HPC
   parents commission paths below the plan's workspace (`plan['manifest']['workspace']`, for example
   `<project>/hpc/<plan>/units/<unit>/result.json`). Either the job writes its results into its own directory, or
   the route's workspace and handle are made to coincide with the plan's directory, or the route gets a member that
   reads below a second declared root. Until one of these holds, a fetch of a plan path fails with
   `result_not_in_catalog` (the failed outcome the service returns; the episode records it and earns nothing).
3. **Whole-file fetch through the transport.** `PbsSshRoute.read` returns a file as base64 in one JSON reply and
   `fetch` holds it in memory (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not provided yet", item 9). Result files of
   an allocation can be large. Wanted: `fetch(ctx, handoff_ref, names=[name], offset=, limit=)` (the artifact of
   one byte window, the closure row once the requested intervals are fetched), or a chunked read written with
   `ctx.store.artifact_stream`.
4. **The scheduler calls have never run** (`qstat -x -f -F json`, `qsub`, `qdel`, `qselect`; "Not provided yet",
   item 4). The states the episodes show the model and return (`queued`, `running`, `finished`, `failed`,
   `cancelled`, `unknown`) are the route's reading of the `qstat` reply, untested against a real scheduler.
5. **Settings.** A commission with `resource_kind: 'hpc'` names the yield profiles
   `results_yield_profiles['native_unbounded_hpc']` and `task_yield_profiles['results:native_finite_hpc']` of the
   episode's settings; the run's caller supplies them. (The tests here commission `resource_kind: 'local'` with the
   local profiles; the `hpc` keys are exercised by the controller test of each `test_binding.py`.)
6. **The transport** is the route's configured `ssh_argv` (the existing master); nothing in the episodes opens or
   repairs one. No test here authenticates to anything.

## 3. What each parent still has to do (not this port's work)

The assignment forms were kept as the parents write them (`handoff_ref` as one record reference, `selector`,
`resource_kind`, `workspace`, `acquired_record_unit`, `initial_result_refs`, `initial_result_artifact_refs`), so the
existing `msg_to_child` of each parent is still admitted by the child's form. What the parents send is not yet what
the child needs:

- **The handoff record.** All six HPC parents pass the handoff reference of their plan or launch report
  (`plan['handoff_ref']`, `hpc['handoffs'][...]['handoff_ref']`, the model's `handoff_ref`). The child reads it as a
  row of `JOB_LEDGER` (`view.records.table(JOB_LEDGER).get(...)`) and hands it to `JobAccess.check` and `fetch`. It
  must be the handoff row `JobAccess.launch` wrote; an old handoff source record raises there.
- **`workspace`.** The HPC parents pass `plan['manifest']['workspace']`. It has to be the job's directory
  (section 2, items 1 and 2).
- **A103 head** (`gene_context_evidence/task.py`, `CHILD_ASSIGNMENTS['execution_result_acquisition']`): the model
  writes the whole assignment and the text offers `"resource_kind": "local"|"hpc"|"api"`. The child's form now
  admits `local` and `hpc` only; the assignment should be built by code from the handoff row the head holds.
- **A107 planning and A107 allocation** (`messages/msg_to_child.py`, slot `results`): both add `constraints` to the
  assignment when the model gave one. `constraints` was an open record whose only reader was the removed target
  description; it is no longer a field of the child's form, so such a commission fails with `FormError`. The two
  lines that add it are to be deleted in the parents.
- **Selection.** New selectable fields of every copy: `execution_job_record_refs` (the latest check row and the
  closure row: a parent that holds the closure no longer counts the job as outstanding) and
  `execution_result_artifact_refs` (the information artifact of each returned result record and the fetched files:
  what a later commission passes as `initial_result_artifact_refs`). No parent selects them yet. The A107 planning
  parent already selects `execution_result_artifact_refs` and passes it back. The A103 planning parent builds
  `initial_result_artifact_refs` from `summary['result_artifacts']`, which its `read_from_child` does not fill from
  this child's return.
- **`message`.** The parents send `initial_report`, `plan_ref` or `purpose` in the message; the child reads no
  message.

Return fields kept as each parent reads them today: `execution_result_refs` and `execution_completed` are required
in the A103 copies, the A104 planning copy and the A107 allocation copy; `execution_completed` is selectable in the
A104 allocation copy (its parent selects it); every field is selectable in the A107 planning copy (its parent
selects three). `execution_result_refs` now names only the result records this Episode retained (the earlier ones
the parent passed are not returned again).

## 4. Typed selectors and API targets

The seven `read_from_parent.py` raised `NotImplementedError('BLOCKED-ON-JOB-SERVICE: the result host of a typed or
API target ...')` for a selector with a `version` or `resource_kind: 'api'`. The raise is gone: these episodes
acquire plain file results, `resource_kind` is a choice over `local` and `hpc`, and a selector with other keys does
not fit the selector schema, so such a commission fails with its own error (`FormError`, `ContractError`). What a
typed or API result would need is unchanged: a route to API services (`LAUNCH_MONITOR_EXTRACT_MECHANICS.md`, "Not
provided yet", item 3) and the typed result families, which are in no place (`BRANCH_FIX_BLOCKERS_a101.md`,
section 5). The always-empty return fields of those families (`_family_fields()`, `execution_blast_hsps`,
`execution_blast_pairwise_result_refs`, `execution_file_source_refs`, `execution_file_capture_outcomes`,
`bvbrc_appservice_support_refs`, `execution_result_origin`) are removed from the seven return forms.

## 5. The estimate table entry of a finished job (A107 allocation copy)

The carried A107 allocation copy had `_close_job`, which raised: it wanted to write the closure row and to add the
finished action to the estimate table. The closure row is written by `JobAccess.fetch`. The estimate table entry is
not written: `EstimateTable.resolve(key, actual, at=)` needs the key under which the launch recorded its
expectation (`expect(kind, expectation, key=, at=)`), and neither the handoff row's `detail['estimates']` nor the
assignment carries that key. Wanted: the launch keeps the expectation key in the handoff row's estimates (or the
parent passes it), then the collect tool calls `ctx.services['estimate_table'].resolve(...)` and the episode
declares `estimate_table` in `SERVICES`. `LAUNCH_MONITOR_EXTRACT_MECHANICS.md` section 7 describes this step; no
ported extract episode does it yet (A101 does not either).

## 6. A later acquisition of the same job fetches again

The form has no field for the job rows of an earlier acquisition, so a second Episode commissioned for the same
handoff does not hold the first one's closure row: it offers the fetch again, the service fetches the files again
(the same bytes are the same artifacts) and writes a closure row of its own. The earlier result records passed in
`initial_result_refs` are read from custody and their bytes earn nothing
(`test_bytes_an_earlier_acquisition_retained_earn_nothing_in_a_later_one`). Passing the earlier closure row would
save the second fetch; it needs a `record_refs` field for job rows in the assignment form (A101's form has
`record_refs` for this).

## 7. Model runs

One real-model run per axis, a finished local job (A103 head, A104 planning copy, A107 planning copy). The job that
has not ended, the finite selector and the earlier results are run offline only (`test_plain_results.py` in each
folder); the model-run file of each folder has the finished-job test only. As in `BRANCH_FIX_BLOCKERS_a101.md`
section 6, after the fetch earned the whole unit the accumulation controller took 8 to 10 further status requests
that earned nothing before it stopped (settings of the test: cutoff 0.1, `uncertainty_alpha` 0.05).

## 8. Not changed

`yield_estimator.py` of the seven folders keeps its logic, with `settings.get('results_yield_profiles', {})` and
the `_profile` raise for a missing profile (recipe step 6: no change of logic).
