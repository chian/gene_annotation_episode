# Launch, monitor, extract: mechanics (19 November 2026)

This issue replaces the 18 November issue; it was revised the same day for the decisions on how an Episode ends
(T1), credit and finding in every return (T3) and recorded service reads (T10). It is written against
`BINDING_CONTRACT.md`, which is the source of truth for every system name used here.

The system parts named here (`ctx.store`, `ctx.services`, `ctx.clock`, custody, the attempts journal, the
selection of return fields) exist in `episode_runtime/` and are tested on its test episodes. The job services
exist too and run on real local jobs; the section "Provided now" gives their real names and calls, which differ
from the example names used in sections 5 to 9. The job episodes are still the design. The last section lists
what is not provided yet.

The owner's rules bind every line (`AGENTS.md`, "How the system fails and stops"): a wrong commission fails with
its error; stopping belongs to the episode's yield estimator alone; no library function touches the Store
directly; `yield_estimator.py` reads what `read_from_parent.py` produced; a child declares every field it can
return and the parent selects. From `GOAL.md`: no elapsed-time, token, turn or count budget; axis credit is never
bounded or rescaled; only the three yield estimators.

## 1. The design in short

1. **Launch.** A launch is one child commission. The launching child submits the job, returns the job's handoff
   record in custody in its typed result, and closes. No Episode stays open for the job. The parent does other work.
2. **Monitor.** The parent learns about the job only by commissioning its monitor child. One check is one monitor
   Episode: one status request, a new time-remaining estimate, a score of the previous estimate, a return.
3. **Extract.** When a check says results are available, the parent commissions its result-acquisition child. The
   results come back as records in custody and the parent's credit is measured again.
4. **Custody, not inventory.** A job's records travel in custody. There is no "all outstanding jobs" read of the
   Store. An Episode knows its outstanding jobs from its own view and the records it holds.
5. **End of turn.** No task ends its own Episode: only the yield controller does. A head with only an outstanding
   job has only waits and checks left to offer. When the forecast yield of those units does not exceed their cost,
   its controller ends it (what a wait or a check earns is the head's own `credit.py` and settings). Its result
   names the job and returns the job's records. The root commissions that head again later and passes the records
   back.
6. **Services.** Job access and the estimate table (memory of earlier runs' estimates) are services of the run.
7. **The model picks; code refuses.** A separate numerical calculation in the library, called from `action`,
   refuses an unworthy pick. It is not a yield estimator. Only the episode's yield controller stops an Episode.
8. **Estimate credit** is kept apart from axis credit. **Learning across runs** is kept as settings and
   thresholds that are logged, readable and overridable.

## 2. Terms

- **Job**: a computation that keeps running after the Episode that started it has returned: a PBS job, a task on
  a remote service, or a detached local job.
- **Launching child**: the child Episode that submits a job and returns: `execution_job_submission` with a route
  child (`hpc_job_execution`, `api_job_execution`, `local_job_execution`). A **check** is one commission of the
  monitor child (`execution_progress_assessment`), a **fetch** one of `execution_result_acquisition`, for one job.
- **Handoff record**: what the submitting tool writes through `ctx.store`: the job handle, the job kind, how to
  find the job, the submission time (UTC) and the estimates made at launch.
- **Outstanding job**: a job whose handoff record an Episode holds and whose closure record it does not hold.
- **Kind of action**: a key such as "A102 planned HPC job". **Estimate credit**: the scores of estimates against
  what happened.

The service names `job_access` and `estimate_table`, the service methods, the slot names, the field names and
the table name used below are examples. The system fixes no service name, slot name or field name.

## 3. Who does what

| Who | Does | Never does |
|---|---|---|
| Launching child | Submits once through the job-access service. Writes the handoff record through `ctx.store`. Returns it in a `record_refs` field of its result. Closes. | Waits for the job. |
| Parent (an axis head) | Lets the model pick; refuses unworthy picks in `action`. Commissions launch, monitor and fetch with `ChildCall`. Carries the job's records. Measures its credit from the results it holds. | Reads a job record it was not handed. |
| Monitor child | One fresh status request per check. New time-remaining estimate. Score of the previous estimate. Writes a check record and returns it in custody. | Fetches results. Stays open until the job ends. |
| Result-acquisition child | Fetches and verifies the results. Writes them and a closure record through `ctx.store`. Returns them in custody. Adds the finished action to the estimate table. | Decides whether the job is done; that comes from a check. |
| Root | Commissions heads. Holds the records of jobs a head left outstanding and passes them back when it commissions that head again. Compares actions across axes. | Contacts a scheduler. Keeps a list of jobs outside its own view. |
| The run's caller | Supplies the `services` factories and the `continuation` settings to `link`. Links, resumes, and starts later runs. | |

## 4. Which file holds what

| File | In a head | In a job child (launch, monitor, fetch) |
|---|---|---|
| `goal.py` | `binding_path`, `goal`, `unit`, `result` | the same four |
| `task.py` | `child_slots` with the launch, monitor and fetch slots; `services` (the estimate table, to read); `decide` builds the model request from the summary, `ctx.clock` and `ctx.settings`; `action` runs the action-value calculation and returns a `ChildCall` or raises `Rejected` | `tools` (submit, check, collect; each `def tool(arguments, ctx)`); `services` (job access; the estimate table where a tool writes to it) |
| `credit.py` | the head's credit from its summary and held records; results count once it holds them | launch: for example one per usable handoff; monitor: information learned; fetch: results acquired |
| `yield_estimator.py` | one of the three controllers, built from `settings` and `parent_input` | the same |
| `messages/read_from_parent.py` | `assignment_form` with a `record_refs` field for outstanding-job records; `read_from_parent` puts them into the parent input | `assignment_form` with a `record_refs` field for the job's records |
| `messages/msg_to_child.py` | builds each `ChildMessage`: names the job's records in the assignment, selects return fields | only if the child has children of its own |
| `messages/read_from_child.py` | the report it keeps of a handoff, a check finding or a fetch | the same condition |
| `messages/internal_summary.py` | the outstanding jobs, from `view.parent_input`, `view.outcomes` and `view.records` | what its tools returned so far |
| `messages/final_to_parent.py` | `return_form` declaring credit, finding, the outstanding jobs, their `record_refs` and the estimate credit | `return_form` declaring credit, finding and the `record_refs` of what it wrote |
| `episode.py` | the one class | the one class |

## 5. Services: job access and the estimate table

A service is the run's access to something outside the Store.

- **Declared.** An episode names the services its functions need in `task.py`: `SERVICES = ('job_access',)`.
- **Supplied.** The run's caller gives `link` the `services` collaborator: a mapping from each name to a
  zero-argument factory. A declared name with no factory refuses the link (`LinkError('service_required:...')`).
- **Built once per run**, on first use, and shared by every episode that declares the name. A tool reaches it as
  `ctx.services['job_access']`; a name the episode did not declare raises `KeyError`.
- **Journaled.** The journal records the names each binding declares (table `services`, compared on resume) and
  each build (table `service_builds`: the name, the Episode that first used it, its unit).
- **Tools act through a service; decisions read from it, and their reads are recorded.** A tool is handed the
  service itself. `decide` and `action` are handed a read handle and never the service:
  `ctx.services['estimate_table'].read(member, *arguments)` returns the service's public attribute `member`
  (called with `arguments` when it is callable) as closed JSON. The system records the value under the unit
  position being decided (journal table `service_reads`), as it records the decision's clock, and gives the same
  read the recorded value from then on: after a rejected answer, when the unit runs again, and on resume. So a
  decision that is made again is made on the values it first read, whatever the service says by then, and a
  rebuilt model request equals its record. (Provisional: owner decision T10 in `BINDING_CONTRACT.md`.)
- **State.** A resumed run builds its services again and their in-memory state starts empty. Durable state, and
  doing each operation once per `ctx.operation_key`, are the service's own job.
- `credit`, `internal_summary`, `read_from_child`, `final_to_parent` and `yield_controller` receive no services.
  A monitor's credit therefore reads what its check tool returned and wrote, not the scheduler.

**Job access** is the scheduler, SSH, the transport, local execution and the native event ledger. It submits,
asks status, fetches and cancels. It is the service `JobAccess` with one route per resource ("Provided now").
The older library functions in the table below exist in `episode_support/` in their old form, several as per-axis
copies; the routes do not call them.

| Job kind | Status request | Fetch | Cancel |
|---|---|---|---|
| HPC (PBS) | `TerminalExecution.observe_execution` (a `qstat -x -f -F json <job>` on the resource) and `read_output` | `read_output` of the result files | no `qdel` call exists in the library |
| Detached local job | `native_lifecycle.status(handle)` | `native_lifecycle.collect(handle)` | `native_lifecycle.cancel(handle)` |
| API service (NCBI BLAST, BV-BRC and others) | `prepare_observation`, then `invoke` and `decode` of the service interface | the service's `result_catalog` and `publish` | the service interface has no cancel operation |

**The native event ledger** (`episode_support/jobs/native_event_ledger.py`, `NativeEventLedger`) is the ledger of
detached local jobs: registered job identities, each job's one service-exit publication and an event cursor, in
its own SQLite file. `register_native_target` and `publish_native_event` accept an identical repeat and refuse a
different one (`identity_conflict`). `wait_events(condition)` is `async` and returns the next events or its
reconsideration time. The ledger is outside the Store and outside custody; episodes reach it only as the service
`NativeEvents`, whose `wait(ctx, condition)` writes the receipt of each event it woke on through `ctx.store`.

**The estimate table** is the memory of earlier runs: for each kind of action, what was predicted and what
happened (gain, duration, cost, scores). Tools add rows through it, once per `ctx.operation_key`. `decide` and
`action` read it through its read handle. Each read is recorded with the decision that made it, so a resumed
run decides again on the values it first read; the service keeps no per-run view of the table for that.

Two limits of services, from the contract: two episodes that declare one service share that object, and what
passes through a service is in no receipt. So job records never travel through a service. They travel in custody.

## 6. Job records travel in custody

Everything that is a Store record, an artifact or a work-table row is read and written through `ctx.store`. A
write is receipted as produced by the unit (inside `ctx.store.transaction()`, when the transaction commits). A
library function in `episode_support/` is handed `ctx.store`, and the service it needs, by the tool that calls it.

A job has three kinds of record: the handoff, each check, and the closure. Each is written by a tool of the
Episode that did the work. A record can be a Store record (`ctx.store.put`), an artifact (`ctx.store.artifact`)
or a row of a declared work table. The example keeps them as rows of one work table declared in the job library,
with bulky replies as artifacts:

```python
JOB_LEDGER = TableDeclaration(name='job_ledger', columns=('job', 'event', 'at', 'detail', 'source_ref'),
                              key=('job', 'event', 'at'), record_refs=('source_ref',))
```

| Move | How it is named | Receipt |
|---|---|---|
| A tool writes it | `ctx.store.table(JOB_LEDGER).put({...})`, `ctx.store.artifact(...)` | `produced` |
| Child to parent | a `record_refs` field of the child's admitted result | `returned` |
| Parent to child | a `record_refs` field of the assignment `msg_to_child` builds | `commissioned` |
| Caller to entry Episode | a `record_refs` field of the entry assignment; the record must exist in the Store | `entry` |

An Episode reads only what it holds. `records.table(JOB_LEDGER).select({'job': handle})` returns the held rows
only, and so does every inventory of `ctx.store` (`list`, `count`). So there is no way to ask the Store for jobs
an Episode was not handed. An Episode knows its outstanding jobs from three places, all in its view:
`view.parent_input` (the job records its parent passed in this commission), `view.outcomes` (the results of its
own launch, check and fetch units) and `view.records` (the content of those records).

## 7. One job from launch to extraction

The A102 head (`structural_homology_evidence`) and one PBS job. Clock times are the owner's example. Head
`task.py`: `CHILD_SLOTS = {'launch': '.../execution_job_submission', 'monitor':
'.../execution_progress_assessment', 'fetch': '.../execution_result_acquisition', ...}`.

**10:00, launch.** The head's `decide(summary, feedback, ctx)` returns a `ModelRequest`. The model picks "launch
planned HPC work" and gives its prediction (section 13). `action(response, summary, records, ctx)` runs the
action-value calculation and returns `ChildCall('launch', {'work': ..., 'prediction': {...}})`. Then
`msg_to_child('launch', arguments, summary)` returns:

```python
ChildMessage(objective='Submit the planned structure search and return at handoff',
             message={'endpoint': 'usable_handoff', 'prediction': arguments['prediction']},
             assignment={'input_refs': [...]},          # record_refs: the inputs the job needs, held by the head
             selection=())
```

The child runs as one unit under the key `launch_<position>`. Its submit tool:

```python
def submit(arguments, ctx):
    job = ctx.services['job_access'].submit(arguments['job'], key=ctx.operation_key)
    reply = ctx.store.artifact(job['scheduler_reply'], 'application/json')
    row = ctx.store.table(JOB_LEDGER).put({'job': job['handle'], 'event': 'handoff', 'at': job['submitted_at'],
                                           'detail': {...}, 'source_ref': reply})
    return {'job': job['handle'], 'submitted_at': job['submitted_at'], 'handoff_ref': row['id']}
```

`detail` holds the job kind, the scheduler's job id and the launch estimates: the prediction, the expected gain,
the duration estimate ("done about 16:00") and the expected cost. The child's result is
`{'credit': ..., 'finding': {...}, 'handoff_refs': [row_ref]}` (`handoff_refs` is a `record_refs` field), and the
child closes. The head now holds the handoff row (`returned`). Its unit outcome keeps the `ChildCall` arguments
and the message. When the submit tool sits in a route child, the record comes up one more return in custody.

**10:01, other work.** The head decides again, for example for literature assessment. Its summary now lists job J
as outstanding, with `check_at` (section 11).

**12:00, a check.** `ctx.clock.now` has passed J's `check_at`. The model picks "check job J". `action` returns
`ChildCall('monitor', {'job': handle})`, and `msg_to_child` returns:

```python
ChildMessage(objective='Report the state of job J and a new time-remaining estimate',
             message={'job': handle},
             assignment={'job_refs': [handoff_ref]},    # record_refs: the head holds it, so it may pass it
             selection=('progress_detail',))            # a selectable field of the monitor's return form
```

The monitor's check tool reads the handoff with `ctx.store.get(handoff_ref)`, makes one status request with
`ctx.services['job_access'].status(handle)`, reads the real clock, computes the new time-remaining estimate
("done about 15:30"), scores the 10:00 estimate, and writes one check row (`event: 'check'`) with the reply as an
artifact. A failed request (transport down, scheduler error) is a returned outcome with status `failed`; it is
not a job state. The monitor returns `credit`, a `finding` (state `running`, completed fraction 0.4, results not
available, the time-remaining estimate, `check_at` as a UTC time, the score), `check_refs: [check_ref]` and the
selected `progress_detail`. The monitor declares `progress_detail` in its own `return_form` as selectable
(`required=False`); its required fields are always returned. The head holds the check row and decides again:
other work, or a wait or another check, until its controller ends its turn (section 8).

**15:30, the job is done.** The next check passes `job_refs: [handoff_ref, check_ref]`, finds the job finished
with results available, and scores the 12:00 estimate against the actual finish time.

**15:31, extraction.** The model picks "fetch job J". `action` returns `ChildCall('fetch', {'job': handle})`; the
assignment names the handoff and the latest check in `job_refs`. The collect tool fetches each result through
`ctx.services['job_access']`, verifies it, writes it with `ctx.store.artifact(data, media_type)` (and a Store
record where one is wanted), writes the closure row (`event: 'closure'`, outcome `results_acquired`, actual
duration and cost), and adds the finished action to `ctx.services['estimate_table']` under `ctx.operation_key`.
It returns `{'credit': ..., 'finding': {...}, 'result_refs': [...], 'closure_refs': [closure_ref]}`.

**Credit.** The head now holds the results. Its `credit(summary, records)` reads them through `records`, so the
head's credit for this unit includes the job's results. The gain predicted at 10:00 is scored against the gain
obtained: the head's credit after this unit minus its credit before it (the journal's controller step of the unit
records the credit and the marginal credit). The score is estimate credit (section 11).

**Abandoning.** The job's expected gain is computed again from each check. When waiting is no longer worth it,
the action offered is "cancel job J": one tool unit, in an episode that declares the job-access service, that
cancels the job, confirms with one status request and writes the closure row with outcome `cancelled`. A
cancelled job gets no gain score.

## 8. How a head's turn ends, and the root's return to it

A head's Episode closes as every Episode closes, in the one way there is: its yield controller stops it
(`ended_by='yield_stop'`). The task cannot close it: `decide` and `action` produce only a `ToolCall` or a
`ChildCall`, and the system has no action that ends an Episode. No rule about jobs is added.

A head with only an outstanding job still has units to offer: a check of the job (one monitor commission) or a
wait (a tool unit). What each of them earns is the head's own `credit.py` and settings. While the job runs and
nothing new can be learned they earn little or nothing, so the controller's forecast of the next unit's credit
falls to the units' cost or below, and the controller stops the head. Two consequences for the head's files:

- its `action` always accepts at least one unit (a wait or a check). The refusal of unworthy picks (section 13)
  must leave one, because a decision that rejects every answer never produces a unit and nothing else stops it;
- its `continuation` settings give its units a cost above zero. At cost zero an accumulating controller never
  stops (the forecast of the next unit's credit stays above zero).

The system then calls `final_to_parent(summary, completion, selection)` with `completion = {'ended_by',
'units_consumed', 'credit'}`; `credit` is the head's credit as its controller last saw it.

**What the head returns.** `credit` (the system's `completion['credit']`) and `finding` are required fields of
every return form. Beside them, declared in the head's `return_form`:

```python
{'credit': ..., 'finding': {...},
 'outstanding_jobs': [{'job': handle, 'kind': 'A102 planned HPC job', 'check_at': '2026-11-19T15:30:00+00:00',
                       'expected_gain': {...}, 'time_remaining': {...}}],
 'outstanding_job_refs': [handoff_ref, check_ref],      # record_refs: returned in custody
 'estimation_credit': ...}
```

The root now holds the two records (`returned`). Its `read_from_child` puts the outstanding job into its report,
so the root's summary lists it under that axis. In this design the fields that carry a job are required fields
of the head's return form, so they are always returned.

**What the root passes back.** Later the model picks "return to `structural_homology_evidence` for job J". The
root's `action` returns `ChildCall('structural_homology_evidence', {'jobs': [handle]})` and `msg_to_child`
returns:

```python
ChildMessage(objective='Continue structural homology evidence; job J is outstanding',
             message={'jobs': [{'job': handle, 'check_at': '2026-11-19T15:30:00+00:00'}]},
             assignment={'subject_refs': [...], 'outstanding_job_refs': [handoff_ref, check_ref]},
             selection=())
```

**How the new head sees it.** The pass is admitted because the root holds both records. The commission builds a
new Episode under a new key (`structural_homology_evidence_<position>`). It holds the two records (`commissioned`).

1. `read_from_parent(assignment, message)` puts `outstanding_job_refs` and the message's job list into the
   parent input. This is the only place the assignment is read.
2. `yield_controller(initial_credit, settings, parent_input)` and `view.parent_input` see that parent input.
3. `internal_summary(view)` reads the rows through `view.records` and lists job J as outstanding, with its
   latest check and `check_at`.
4. `decide` compares `check_at` with `ctx.clock.now` and offers "check job J". The check and the fetch then run
   exactly as in section 7.

**The root itself.** If the root's Episode closes with a job outstanding, its result names the job in the same
two fields, and the run closes. A later run can be linked with those records in a `record_refs` field of its
entry assignment: they exist in the Store, so the entry Episode holds them (`entry`).

## 9. Submitting at most once; restart and failure

- Before a tool runs, the system journals that the unit began (table `attempts`: label, operation key, digest of
  the arguments). The unit's completion marks it finished.
- On resume a unit that began and did not finish runs again, with the same `ctx.operation_key` and `ctx.resumed`
  true.
- `ctx.abandoned` names what the abandoned attempt produced: `({'ref', 'producer_unit'}, ...)`. The rerun may
  read each (`ctx.store.get`, `get_artifact`) and take one over as its own product with `ctx.store.reclaim(ref)`.
- The system guarantees the key and the journal, not the outside world. The submission must be idempotent on
  the key: `job_access.submit(..., key=ctx.operation_key)` returns the job it already submitted under that key,
  with its original submission time, instead of submitting again. That memory is durable state of the service.
- **Restart.** `resume` re-links the recorded run. Completed units are not run again; each Episode's view,
  receipts and recorded model answers are restored. A job that kept running while the process was stopped is
  found by the next check. Services are built again and start empty (section 5).
- **A failed job** is a state a check reports. It is closed with outcome `failed` and gain zero. **A failed
  status, fetch or cancel request** is a returned outcome of its tool unit.
- **An exception in a tool** ends the run and is recorded as its failure. The run stays `active` and can resume.
- **A wrong commission** (a selection the child does not declare, an assignment its form does not admit, a record
  the parent does not hold) fails with its error (`FormError`, `CustodyError`). The run fails with that message.

## 10. Time

- **`decide` and `action`** read `ctx.clock`, a `DecisionClock`: `now` (UTC), `began_at` (UTC, when the Episode
  began), `elapsed_seconds`, `progress_time` (the progress receipt of the last completed unit). It is captured
  once per unit position and recorded. Every `decide` call for that unit, and every replay of it, sees the same
  time, so "is `check_at` due" is answered the same way on resume.
- **A tool** has no clock in its context. It reads the real clock itself and returns the times in its outcome.
  The outcome is journaled with the unit and restored in `view.outcomes`.
- Launch time, check time, `check_at` and `wait_until` are UTC values recorded that way: in a tool's outcome, in
  the job's records, or in a tool's arguments.
- After a restart on another boot, `elapsed_seconds` and the progress receipts are `unavailable`, never
  estimated. `now` is still a valid UTC time.

## 11. Estimates, their scoring, and estimate credit

| Estimate | Made by | When | Scored |
|---|---|---|---|
| Gain: the credit the head expects from the job, in its own credit units (value, lower, upper) | the action-value calculation, from the model's prediction | before launch | at the fetch, against the gain obtained |
| Duration: a distribution of seconds from handoff to the job's end | the library's time model, in the launching child | at launch | as the first time-remaining estimate |
| Time remaining: a distribution of seconds from the check to the job's end | the monitor's check tool | at each check | at the next check |

- **Scoring a time estimate.** If the job has ended, the score is against the actual remaining time. If not, the
  estimate is scored as censored ("more than the time since the estimate"). The score is the log score of the
  estimate minus the log score of a reference estimate; it is signed and unbounded. Each estimate is scored once.
  The functions exist in the library's `hpc_prediction.py` (`predict`, `update`, `log_score` with `censored`,
  `probability_within`), as per-axis copies in their old form.
- **`check_at`** is not a fixed interval. It is the earliest time at which P(job done by then) times the job's
  current expected gain, minus the cost of one check and one fetch, passes the action-value rule. A better
  estimate places the check just after the job ends.
- **Estimate credit.** Each score is stored with its estimate in the job's check or closure record and in the
  estimate table. An Episode returns the sum of its scores in its own declared field (`estimation_credit`). It
  never enters `credit`, the axis credits or the root's hypervolume, and it is not in the controller input.

## 12. Stopping and credit

- Each unit's controller input is exactly `{'credit': credit(summary, records), 'estimation_context':
  {'progress_time': ...}}`. The episode's yield controller reads it and alone decides whether the Episode stops.
  The controller is one of `AccumulationYieldController`, `BoundedQualityYieldController`,
  `CompletionYieldController`, returned by `yield_estimator.py`; the runner refuses anything else.
- Whether a check, a lookup or a wait earns credit is that episode's own `credit.py` and settings. For example
  the A102 monitor's own files count credit for information (newly informative progress snapshots times an
  information unit) and name the accumulation controller.
- There is no job rule in stopping: nothing keeps an Episode open because a job is outstanding, and nothing
  closes it for that reason.

## 13. The action-value calculation

`GOAL.md`: the model picks actions and code refuses unworthy ones. Worth comes from a numerical calculation that
compares this action's expected yield with other actions', using data from this run and past runs. Before a
costly action its expected outcomes are recorded. The action is valued by how well it tells the possibilities
apart, and a cheaper action of similar gain is preferred.

**What it is and is not.** It is a separate numerical calculation: pure functions in the library, called from
`action`. It is not a fourth yield estimator. There are only the three yield estimators, and they alone decide
stopping. The calculation never closes an Episode and gives the controller nothing.

**Its inputs**, all of which `action(response, summary, records, ctx)` already has: the `response` (the model's
pick and, for a costly action, its prediction); the `summary` (this run: the Episode's outcomes so far, its
outstanding jobs, what its parent's message said); `ctx.settings` (thresholds, costs and typical values per kind
of action); `ctx.services['estimate_table'].read(...)` (past runs; the read is recorded with the decision);
`ctx.clock` (the time of this decision).

**Its result.** For a worthy pick, `action` returns the `ToolCall` or `ChildCall`. For an unworthy pick, `action`
raises `Rejected(feedback)`: no unit is created, the controller is given nothing, and `decide` is called again
with that feedback (for example the cheaper action that was preferred). `decide` may run the same functions to
show the model each action's expected gain and cost in the request's context.

**The prediction** is part of the model's answer for a costly action (a job launch or a child commission):
`candidates` (the candidate annotations compared, as record references); `current_support` (one number per
candidate, summing to one); `outcomes` (each with a `label`, a `probability` and `support_after`, one number per
candidate). It is recorded before the action runs: the model's answer is journaled as a model call, and the
`ChildCall` arguments and message that carry it are kept in the unit's outcome.

**The numbers.** Discrimination d is the expected fall in uncertainty about which candidate is right, as a
fraction of the present uncertainty. With H the entropy of a support vector: d = (H(`current_support`) minus the
sum over outcomes of `probability` times H(`support_after`)) divided by H(`current_support`). d is high when
different outcomes favour different candidates and zero when no outcome changes the support. An outcome is
definitive when its `support_after` gives one candidate at least the setting `definitive_support`. Expected gain
is the kind's typical gain band times d times the kind's correction (how far earlier predictions were off).

**The refusal.** A pick X is unworthy in two cases. (1) X is not worth its own cost: the upper bound of its
expected gain minus its cost is at or below the kind's threshold. (2) Something cheaper gains about as much: an
available action Y costs less and its expected gain is at least (1 minus the threshold) times the upper bound of
X's. Because the rule uses X's upper bound, a kind with little history and a wide band still gets tried.

**Across axes.** The root sees every axis's reports in its own view, so the comparison across axes is made in
the root's `action`. A head compares the actions it can take itself. What is available elsewhere reaches a head
only through the root's message in the commission.

## 14. Settings and learning across runs

- Settings and yield thresholds are the `continuation` collaborator: a mapping with one entry per binding path.
  A binding path without an entry refuses the link. The mapping is journaled at link (table `settings`) and
  compared on resume; other settings raise `JournalError`.
- An episode's own entry reaches `yield_controller(initial_credit, settings, parent_input)` as `settings`, and
  `decide`, `action` and tools as `ctx.settings` (a copy).
- Learning across runs is numbers, not text for the model. After a run, the typical gain, duration, cost,
  correction and threshold of each kind of action are recomputed from the estimate table. The next run's caller
  loads them into `continuation`.
- Every change is logged: the setting, the value before and after, the rows behind it, the run that caused it.
  A value the owner fixed in an overrides file is not recomputed; the log says what would have been set. So the
  settings are logged, readable and overridable, and each run's journal says which were in force.

## Provided now: the job services (19 November 2026)

Built and run by `episode_support/jobs/tests/test_job_services.py` (15 tests through the real runner; local jobs
are real detached systemd services). The run's caller gets every factory from
`episode_support/jobs/job_services.py`: `job_services(configuration)` returns `{name: factory}` for the
`services` collaborator. The names in sections 5 to 9 were examples; these are the real ones.

| Service name | Class, module | What a tool calls (`service = ctx.services[name]`) | What a decision reads (`.read(member, ...)`) |
|---|---|---|---|
| `job_access` | `JobAccess`, `episode_runtime/job_access.py` | `launch(ctx, resource_id, job, inputs=None, estimates=None, name='job')`, `check(ctx, handoff_ref, assess=None)`, `window(ctx, handoff_ref, name, offset=, limit=)` (one byte window of a file of the job, a log while it runs; no check and no closure), `fetch(ctx, handoff_ref, names=None)`, `cancel(ctx, handoff_ref)`, `await run(ctx, resource_id, job, inputs=None, name='command')` (launch, wait, fetch in one unit) | `resources`, `describe(resource_id)` |
| `estimate_table` | `EstimateTable`, `episode_runtime/estimate_table.py` | `expect(kind, expectation, key=, at=)` before a costly action, `resolve(key, actual, at=)` after it; `observe(resource, kind, data, observed_at=, provenance=)`, `record(attempt_id=, profile=, observation=)` | `kind_statistics(kind)`, `rows(kind, limit)`, `expectation(key)`, `kinds`, `latest(resource, kind, now)`, `history(profile, now, queue_only, limit)`, `profiles(tools, now, limit)`, `policy`, `as_record` |
| `native_events` | `NativeEvents`, `episode_support/jobs/native_events.py` | `await wait(ctx, condition)` (the receipts of the events come into custody), `receipt(ctx, handle, record_ref)`; the ledger's own `register_native_target`, `validate_event_targets`, `wait_events` (so `waiting.selected_wait(service, condition)` works) | `targets(handles)` |
| `resource_adapter`, `resources` (one object) | `ResourceAdapters`, `episode_runtime/resource_adapters.py`; each bound resource is a `JobResourceAdapter` (`episode_support/jobs/job_resource_adapter.py`) | `prepare_assignment(ctx, assignment)`, `await execute(ctx, assignment, tool, arguments)`, `await check_handoff(ctx, handoff)` | `declared_capabilities`, `adapter_capabilities`, `bound_resource_ids`, `is_bound(resource_id)`, `catalog(assignment)`, `decision_context(assignment)`, `facts(assignment)` |
| `instruction_libraries` | `InstructionLibraries`, `episode_support/jobs/instruction_libraries.py` | `execute(name, arguments)` (one lookup of either frozen library) | `launch_instruction_library`, `tool_knowledge`, `context`, `catalog`, `for_resource(configuration)`, `materialize(selection)`, `entries_for_tool(name)` |

Not services, because they read nothing outside the Store:

- **The job record kind** is the declared work table `JOB_LEDGER` (`episode_runtime/job_access.py`: columns
  `job`, `event`, `at`, `detail`, `source_ref`, `result_refs`; key `job`, `event`, `at`; events `handoff`, `check`, `window`,
  `closure`). `job_access` writes the rows through `ctx.store` with the route's reply as an artifact, so the tool
  does not write them itself (section 7's example tool is replaced by one call). The readers for summaries and
  credit are `episode_support/jobs/job_records.py`: `outstanding_jobs(reader)`, `handoff`, `checks`, `closure`,
  `job_rows`.
- **The HPC ledger** is the declared work table `HPC_LEDGER` (`episode_support/jobs/hpc_ledger.py`):
  `HpcLedger.open(ctx.store, commission)`, `HpcLedger.existing(reader, ledger_id)`, `put`, `read`, `records`,
  `freeze`, `score(measured_ref, log_score=, measured_value=, forecast_metric=)`, `accept`, `model_credit`,
  `credit_view`, `refs` (the rows, and the records they name in `source_refs`, to pass or return in custody). An episode that named a `hpc_ledger` service drops
  it from `SERVICES`. The old `once`, `cached` and `save_action` are not carried: the journal replays finished
  units.
- **The action-value calculation** (section 13) is `episode_support/jobs/action_value.py`: `discrimination`,
  `definitive_outcomes`, `expected_gain`, `refusal`.

**No relaunch on resume, without a table of finished operations.** A job's handle is derived from the unit's
`ctx.operation_key`. A unit that runs again takes over the row its abandoned attempt wrote (`ctx.abandoned`,
`ctx.store.reclaim`) and the route is not asked (`replayed`). When the attempt was cut before its row committed,
the route is asked again with the same handle and returns the job it already has (`adopted`). Section 9's
`submit(..., key=ctx.operation_key)` is this.

**Routes** (one per resource id; the protocol is stated in `episode_runtime/job_access.py`):

- `LocalJobRoute` (`episode_support/jobs/local_job_route.py`): a job `{'command', 'env'}` runs as a detached
  systemd user service through `gene_annotation_episode.native_lifecycle`. The job runs
  `episode_support/jobs/detached_job.py`, which writes the command's receipt and publishes it to the native event
  ledger from the job's own process.
- `PbsSshRoute` (`episode_support/jobs/pbs_job_route.py`): a job `{'mode', 'script', 'arguments', 'env'}` through
  the configured transport (`ssh_argv`); `mode: 'batch'` uses `qsub`, `qstat -x -f -F json`, `qdel` and, for an
  unrecorded submission, `qselect -x -N`; `mode: 'login'` runs the script as a detached process on the node the
  transport reaches.

**How the wanted calls of the carried episodes map.** The carried episodes name about eighty different members of
`job_access` in their `BLOCKED-ON-JOB-SERVICE` notes. They reduce to these:

| Wanted call | Real call |
|---|---|
| `exec_command`, `run_command`, `run_discovery`, `run_remote`, `execute_command`, `begin_command` with `finish_command`, `stage_input` | `await job_access.run(ctx, resource_id, job, inputs={name: ref})`: the command is launched once under the unit's key, waited for, and its files come back as artifacts |
| `submit`, `launch_operation`, `api_operation` (a submission) | `job_access.launch(ctx, resource_id, job, inputs=, estimates=)` |
| `status`, `observe_target`, `observe_progress`, `observe_queue` (as a `run` of the queue command), `read_progress` | `job_access.check(ctx, handoff_ref, assess=<the episode's own reading of the reply>)`; an earlier check is read from the held check rows |
| `read_file`, `read_target`, `result_host`, `api_result_catalog`, `api_result_operation` | `job_access.fetch(ctx, handoff_ref, names=[...])` |
| a log window of a job that still runs (`progress_log`, `read_output` of a live job) | `job_access.window(ctx, handoff_ref, name, offset=, limit=)`: the bytes come into custody as an artifact named by a `window` row; the job is not closed |
| `handoff_refs`, `native_event_targets`, `describe_progress_target`, `describe_result_target` | the held handoff row (`job_records.handoff`, `outstanding_jobs`); its `detail['native']` names the event target |
| `capabilities`, `api_capabilities`, `launch_catalog`, `api_catalog` | `job_access.read('resources')`, `.read('describe', resource_id)`; `resource_adapter.read('catalog', assignment)` |
| `estimate_table.observe`, `latest`, `record`, `history`, `policy`, `as_record` | the same members (`record` takes `attempt_id`, not `key`) |
| `validate_assignment`, `validate_action`, `validate_report`, `credit_view`, `resolve`, `direct_dependencies`, `execution_expectations`, `received_bvbrc_context`, `api_decision_context` | not a service: each reads only the Episode's own assignment and held records, so it is the episode's own code or a library function it calls |

## Not provided yet (for a later build)

1. **The root waiting in the process until a check time.** The system has no wait. A wait is a tool unit: an
   `async` tool that awaits `native_events.wait(ctx, condition)`, whose credit is whatever that episode's
   `credit.py` gives it. Otherwise the run ends: an interrupted run is resumed by its caller, and after a closed
   run the caller links a later run (section 8). Nothing starts either at `check_at`.
2. **The recomputation of settings after a run**, its change log and the overrides file (section 14).
   `EstimateTable.kind_statistics` gives the numbers; nothing writes them into `continuation`.
3. **A route to API services** (NCBI BLAST, BV-BRC and others). The route protocol admits one; none is written,
   and a cancel operation for API services does not exist. The library's API code
   (`episode_support/jobs/service_calls/`) is still in its old form.
4. **The PBS scheduler calls have not run.** `PbsSshRoute` is tested through a local shell as its transport: the
   remote program, a login-mode job, staging, status, results, reading, cancelling, adoption of a recorded
   submission and the refusal of an unknown one all run. No PBS scheduler is installed where the tests run and
   nothing authenticates to Aurora, so `qsub`, `qstat`, `qdel` and `qselect` (the batch mode, and the reading of
   the `qstat` reply) are written and have never been executed.
5. **The scheduler-specific observations of the old `TerminalExecution`** (`observe_execution` with its PBS field
   measurements, `write_allocation_control`, the `qsub` shim that records the submitted script) are not carried
   into a route. They stay in the library's per-axis copies until the jobs family is carried over.
6. **The time model and the scores of estimates** (`hpc_prediction.py`: `predict`, `update`, `log_score`) remain
   per-axis library copies. An episode passes its own functions (`check(..., assess=...)`, `HpcLedger.score`).
7. **Per-call model timing.** The journal keeps each model call's request and response, not when it was asked
   or how long it took. The decision clock is one time per unit position.
8. **A count of rejections visible to `decide`.** `decide` receives only the latest feedback. It cannot see how
   many answers were rejected for this unit, or the earlier feedback.
9. **Writing an artifact from a file without loading it, and a scratch directory under the Store.**
   `job_access.fetch` reads each result file into memory and writes it with `ctx.store.artifact(data, media_type)`.
10. **Real episodes on the services.** The carried launch, monitor, result-acquisition, resource and HPC planning
    episodes still raise at their `BLOCKED-ON-JOB-SERVICE` notes; each is rewritten onto the calls above in the
    episode stage. The only episode that runs on the services today is the test episode
    `episode_support/jobs/tests/job_probe/`. Since then the A104 monitor
    (`root/a104/evolutionary_history_evidence/execution_progress_assessment`) runs on them: `MONITOR_PORT_RECIPE.md`
    is its port and the steps for every other monitor; its reading of check rows is `episode_support/jobs/job_progress.py`.
