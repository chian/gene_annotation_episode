# Long jobs: the HPC launch leaf, the API launch leaf and the monitor leaf (one design, 2026-11-20)

Status: DESIGN ONLY. Nothing was built, run or edited in any episode folder. It is written so that the three build
forks (`blast_database_preparation`, `database_blast`, `all_vs_all_blast`) copy one design instead of inventing three.

**How to read the labels.** *Read* = I read it in the repository this session and it says what is stated. *Relayed* =
taken from a document or a fork report, not checked in code. *Unverified* = a claim about something that has never
run here (above all PBS/Aurora, which has never been contacted from this code). *Proposal* = my recommendation; the
owner decides.

Sources read in full: `AGENTS.md`; the owner's decisions D1-D20 and my inferences I1-I8 in
`docs/plan/A101_blast_regions_plan.html`; `docs/axis_restructure_20261117/` `HPC_PORT_RECIPE`, `API_PORT_RECIPE`,
`API_SERVICE_INVENTORY`, `LAUNCH_PORT_RECIPE`, `LAUNCH_MONITOR_EXTRACT_MECHANICS`, `MONITOR_PORT_RECIPE`,
`WAIT_ACTION`, `LOCAL_WRAPPER`; `launch_instruction_library/` `aurora-access/operations/pbs/storage/software`,
`api-blast/operations/results/service`; `examples/aurora_execution_resources.json`; `tools/aurora_ssh.sh`;
`episode_runtime/job_access.py`; in `episode_support/jobs/`: `job_services`, `pbs_job_route`, `api_job_route`,
`pbs_batch_job`, `job_progress`, `job_records`, `job_wait`, `resource_local`, `native_events`, `hpc/hpc_remote`,
`hpc/hpc_queue`, `hpc/hpc_allocation` (head), `similarity_search/.../blast_preparation_run`; `yield_control`
(`CompletionYieldController`); the committed partial leaves `blast_database_preparation/launch_hpc`,
`database_blast/launch_api` and `database_blast/monitor`; and the old (reference-only) `old_execution_job_submission/hpc_job_execution`.

## 0. The key choices in ten lines

1. All three leaves are **code-decided**: `decide` returns the unit; no model is asked (the model has nothing to choose: the commission fixes the job).
2. Every job goes through the system's `JobAccess` only (launch / check / window / fetch / cancel). Rows in custody: handoff, check, window, closure.
3. A launch leaf **ends at the handoff**. It never waits, checks, fetches or interprets.
4. The scheduler allocation (including walltime) is set **by the launching leaf in the job request** as scheduler operands (D19); no application deadline exists anywhere.
5. Allocation fields should be **controlled** (queue from a configured list, node count and walltime seconds as numbers in range; account and filesystems from configuration), not five free-text operands (proposal).
6. **One submission per intent.** After any failure that is not provably "not sent", a launch leaf makes **no second submission**; the parent decides. (The committed partial leaves break this; section 7.)
7. Authentication: reuse of the owner's existing master connection only. A lost transport is an operational stop: **one attempt, then end**, no retry, no fallback.
8. A monitor exists **only for long jobs** (HPC, public API). One visit = wait for the provider's spacing, one `check`; credit only for a newly shown fact; the parent does not commission a visit when the held check is already terminal.
9. The ending problem (several no-gain re-reads) is handled **by the parent's rule plus the monitor's completion controller and cost setting**, never by a stop action.
10. Missing shared library functions are listed in section 6 with one proposed home each; they should be written **once, by one fork, before** the three build forks adapt their copies.

## 1. The frame every long job shares (read)

- **Service.** `ctx.services['job_access']` is a `JobAccess` over one *route* per resource id (`local`, `pbs`, `api`). Episodes declare `SERVICES = ('job_access',)`. A decision may only *read* (`read('describe', resource_id)`, `read('resources')`); tools act.
- **Rows.** The job ledger (`JOB_LEDGER`) is a work table in custody. `launch` writes a `handoff` row (resource id, route kind, the route's native identity of the job, digest of the job, input references, estimates); `check` writes a `check` row (state, whether results are available, the assessment); `window` writes a `window` row; `fetch` / `cancel` write the `closure` row. The reply of the route is an artifact beside each row. The Episode holds what it wrote or was handed; it reads nothing else.
- **Handles and resume.** The job handle derives from the unit's operation key, the resource id and a `name`; so a **unit** that runs again (resume) adopts its job, while a **new unit** (even in the same Episode) has a **new handle** and would submit a new job. This one fact drives sections 2.6 and 3.4.
- **Failures.** A request the resource refused is *returned* (`{'status': 'failed', 'failure': {'code', 'detail'}}`), no row is written, and it is never a state of the job. Any other error ends the run.
- **Episode shape.** Leaves have no children: no `msg_to_child.py`, no `read_from_child.py`, no `tests/` folder. The system requires an `action` member even for an episode that asks no model; code-decided leaves implement it as one line that raises (the owner's open question from the pairwise pilot, decision A9 below).
- **Controlled messaging.** What a parent sends a leaf is numbers, booleans, fixed-vocabulary values and record references. What a leaf returns is `credit`, `finding` (counts, booleans, a failure code from a fixed vocabulary) and selectable record references. No text a model wrote.
- **Credit and stopping** (AGENTS.md; D17). Credit is only for what is gained, read by `credit.py` from rows the Episode holds. The yield estimator alone stops the Episode. `CompletionYieldController(epoch, initial_credit, cost, target, settings)` requires `cost < target` (read in `yield_control`).
- **Kind check** (D9). The action itself is the declaration; the job it built is checked with the single `derived_analysis_kind` function before anything is sent; a mismatch raises.

## 2. The HPC launch leaf (Aurora / PBS)

Template: `blast_database_preparation/launch_hpc` (committed, partly reviewed). Same design for `database_blast/launch_hpc` (custom database) and `all_vs_all_blast/launch_hpc` (chunked).

### 2.1 What it receives (controlled) and what code builds

| Received from the parent | Kind | Notes |
|---|---|---|
| the action's own job fields (preparation: kind, molecule, switches; database search: program, hit-list size; all-vs-all: thresholds, chunk index) | numbers / vocabulary | each action's own form; validated in `read_from_parent` |
| the sequence records the job reads | record references, passed in custody | the staged FASTA is read through custody |
| for a custom database: the prepared-data record | record reference | the database stays on the resource; the record names where (preparation's design) |
| `resource_id` | text checked against `job_access.read('resources')`: must be kind `pbs` | else a wrong commission: the run fails |
| allocation | see 2.2 | |
| `handoff_unit` | positive number | the credit of the established handoff |

Code builds, in `task.py`, by calling library functions only: the plan and the driver as artifacts; the **command** (the cluster's absolute Python, the driver, the plan; the Python path and the executables with their sha256 come from this episode's `ctx.settings['resources'][resource_id]`); the batch job `pbs_batch_job(command, allocation)` = a script `cd "$PBS_O_WORKDIR"; <command>` plus the `qsub` operands; then `JobAccess.launch(ctx, resource_id, job, inputs=..., estimates=...)` once. *Read.*

### 2.2 The scheduler allocation as scheduler operands (D19)

`pbs_batch_job` (read) takes exactly five operands, each a plain string matching `[A-Za-z0-9_.:=+@,-]+`, and builds `-A account -q queue -l select=... -l walltime=... -l filesystems=...`. It is passed through, never defaulted, and a missing or malformed operand is a wrong commission.

| Operand | Where the value comes from (proposal) | Source in the repo |
|---|---|---|
| `account` | the resource's configuration (`BioReason-Aurora-Test`); not chosen by a parent or a model | AGENTS.md; `aurora-pbs.md` (relayed) |
| `filesystems` | configuration (`flare` for work under `/lus/flare/projects/BioReason-Aurora-Test`) | `aurora-pbs.md`, `aurora-storage.md` (relayed) |
| `queue` | a value from the queue list in the resource's settings (an enum); queue rules change, so the owner owns the list | `aurora-pbs.md` says to inspect current limits; no list exists in the repo |
| `select` | built by code from an integer node count in the queue's range; the exact Aurora `select=` syntax is **not in any document I read** | unverified (decision A3) |
| `walltime` | built by code as `HH:MM:SS` from an integer `walltime_seconds` that must not exceed the queue's configured maximum | see A1 |

There is no application deadline: the walltime is required by `qsub`, is the scheduler's limit on the job, and is recorded in the handoff's `estimates`; it never reaches a yield estimator and never stops an Episode. (`aurora-pbs.md`, relayed: "A PBS walltime resource operand is separate from the scientific episode's continuation expectation.") The committed `launch_hpc` takes the five operands as free text (`ALLOCATION_FORM`): that violates "controlled data only"; replace it as above.

### 2.3 Staging, output and the shared filesystem

- **Inputs** held in custody are staged by `launch`: each artifact is base64-encoded into the JSON request that goes through the transport on stdin and is written into the job directory `<workspace>/<handle>` by the remote program. *Read.* Consequence: **the inputs must be small enough to travel in one request**; there is no staging of a large file from the cluster's own filesystem (missing capability, M6, decision A4).
- **Job directory.** Everything lives under the configured workspace (`/lus/flare/projects/BioReason-Aurora-Test/...`, relayed from the Aurora storage entry; nothing in home but the one directory index).
- **Outputs.** The route's `results` lists the regular files the job left in its directory, control files and staged inputs excluded (read). `fetch` reads each requested file fully into memory and writes it as an artifact (read; item 9 of the old "not provided yet" list). So only **small receipts and reports** are fetched into custody; large products (a database, a similarity graph) stay on the resource and are referenced by a record (the preparation design: `placement_prefix`).
- **Databases for a search on the cluster** are referenced by their path on the resource, taken from the prepared-data record, and checked by the job's driver; they are not staged.

### 2.4 Submit, hand off, detach (read: `pbs_job_route`)

`PbsSshRoute.submit` runs one small Python program on the resource through the transport, with the request as JSON on stdin and the reply on stdout. For `mode: 'batch'`: write the staged files, write `job.pbs`, `touch submitting` (the intent), `qsub -N ep<last 13 of handle> -o stdout.log -e stderr.log [-v env] <args> job.pbs`, publish `submission.json`. A rerun of the same handle returns the recorded submission (`adopted`). A rerun that finds an intent but no record asks the scheduler for the name (`qselect -x -N <name>`); if none, the outcome is unknown and the request fails with `submission_outcome_unknown`; nothing is submitted a second time on a guess. The job then runs in PBS after the Episode has ended; the Episode's work is done at the handoff row.

**What "accepted" means:** `qsub` returned a job id, which is the row's `native.job_id`. It may still be queued. **Unverified:** `qsub`, `qstat`, `qdel` and `qselect` have never been executed by this code (relayed, `LAUNCH_MONITOR_EXTRACT_MECHANICS`, "Not provided yet" item 4; the tests use a local shell as the transport in login mode).

### 2.5 Authentication and a lost transport (AGENTS.md; `aurora-access.md`; `tools/aurora_ssh.sh`, read)

- The only transport is `ssh_argv: ['/bin/bash', '<repo>/tools/aurora_ssh.sh']`. The route appends exactly one quoted remote command. The script uses the owner's existing master socket with `ControlMaster=no`, `BatchMode=yes`, `ProxyCommand=/bin/false` and no password or key fallback. If the socket is missing it prints "Original authenticated bastion socket unavailable; no login attempted." and exits 69.
- No leaf, route or script authenticates, renews, repairs or replaces the master. The leaf contains no authentication code.
- A down transport reaches the leaf as the failed outcome `transport_or_remote_program_failed` (nonzero exit; the detail holds the exit code and the stderr tail, so 69 identifies "master gone") or `transport_unavailable` (the program could not be started). *Read.*
- **What the leaf does** (proposal; the committed leaf does not): after a transport-class failure it makes **no further launch attempt in that Episode**. `decide` then returns the read-only `handoff_read` unit, which earns nothing, so the controller ends the Episode. The return carries the failure code in a controlled `finding` field and credit 0. The parent returns it upward; nobody retries until the owner has restored the connection. This is the "operational stop" of the Aurora entry.
- A failed transport never shows that a native job failed and never authorizes replacing an uncertain submission (Aurora entry, relayed).

### 2.6 One submission per intent (the rule every launch leaf follows)

Because a new unit has a new handle (section 1), a leaf that simply decides "launch" again after a failure can submit twice. Rule: the leaf may decide a further launch **only** after a failure that proves nothing was sent; for PBS that is `scheduler_command_failed` raised by `qsub` itself (the scheduler refused; nothing queued) or a request that the route refused before the remote program ran. After `submission_outcome_unknown`, after any transport-class failure, or after an accepted handoff, it makes no new launch. This is one pure function in the shared failure table (M8), not logic copied per leaf.

### 2.7 What is validated offline and what needs the owner's login

| Check | Offline? |
|---|---|
| the commission form, the controlled allocation fields, the kind derivation, the compiled plan and driver bytes | yes (pure) |
| `pbs_batch_job` output: script text and `qsub` argument list for a given allocation | yes (pure; compare to the Aurora entry's rules) |
| the remote program and the route's adopt/intent logic in **login mode** through a local shell as transport | yes (real; existing route behaviour) |
| the leaf's `decide` rules after each failure code (2.5, 2.6) | yes (pure, driven by returned failure values) |
| `qsub`, `qstat -x -f -F json`, `qdel`, `qselect`, the reading of the `qstat` reply, queue limits, `select` syntax, BLAST+ and Python on Aurora, quotas | **only with the owner's live connection**; none of it has ever run |
| any claim about walltime or memory kills | only after a real job ends that way |

No fake scheduler is to be written to stand in for these (the owner: real runs only). Everything in the last two rows is reported as "not run".

### 2.8 Failure codes (what exists and what each means for the leaf)

| Code | Exists in code? | Meaning | Leaf action |
|---|---|---|---|
| `transport_or_remote_program_failed` | yes (`pbs_job_route`) | transport or remote program exited nonzero (69 = master gone) | stop, report; no retry |
| `transport_unavailable` | yes | transport program could not start | stop, report |
| `scheduler_command_unavailable` | yes (remote program) | a scheduler command is missing on the resource | stop, report (configuration) |
| `scheduler_command_failed` | yes | `qsub` returned nonzero (detail: command, return code, stderr). A full queue or a refused request is expected to appear here; **unverified** | may decide one more launch only if the owner's rule allows; default: report |
| `submission_outcome_unknown` | yes | intent without a record, scheduler has no such name | stop, report; never resubmit |
| `file_name_outside_the_job_directory`, `job_not_found`, `result_file_missing`, `results_not_available`, `job_state_unknown`, `result_not_in_catalog`, `result_differs_from_its_catalog_entry` | yes | later operations (check, fetch), not launch | belongs to monitor/results |
| queue full, walltime exceeded, out of memory | **no distinct code** | the first shows as `scheduler_command_failed`; the other two are not launch failures at all: the job ends with state `failed` and PBS fields (`Exit_status`, used vs requested walltime and memory) | a classification function over the `qstat` fields is missing (M4); **unverified** |

## 3. The API launch leaf (public web service; NCBI BLAST first)

Template: `database_blast/launch_api` (committed, reviewed by reading only; one earlier run record exists, `runs/db_blast_launch_api_1`, whose stderr ends in a script error after the result).

### 3.1 What it receives and builds
Received: `resource_id` (a bound `api` route), `service` (enum, `ncbi_blast` today), the query as one subject record plus its sequence artifact (record references), `program` (enum of the five BLAST programs), `database` (enum of a hosted vocabulary), `hitlist_size` (integer ≥ 1), `completion_target` (positive). Built by code: the request `{program, database, hitlist_size}` validated against the route's `describe()['request_schema']`; the program must take the query's molecule (`query_unit_by_program`); the job `request + {'query_file': 'query.fasta'}`; the query is staged from the held artifact; the job's derived kind must equal `database_search`. *Read.* The database vocabulary in the committed form (`swissprot`, `nr`, `refseq_protein`, `pdbaa`, `nt`) is **unverified** against the service (decision A11).

### 3.2 Client identification and rate limits (read: `api_job_route`; relayed: `api-blast.md`)
- Every request carries `tool=<client_name>` and the `User-Agent` of the same name; `email=<contact_email>` only when the configuration gives one (`None` means none is sent). No credential of any kind is ever sent: no login, token, cookie or `Authorization` header.
- **Never the owner's name or email.** Use a neutral client name that names no person (proposal: a fixed generic string such as `annotation-episode-client`) and `contact_email = None`. NCBI asks clients to identify themselves; if the service ever throttles, the owner decides whether to supply a non-personal project address (decision A6).
- Spacing, kept by the route in `<workspace>/rate.json` under a file lock and shared by every process using the workspace: at least `request_spacing_seconds` between two contacts and `poll_spacing_seconds` between two status requests of one job. Documented values for NCBI: 10 s and 60 s (relayed: instruction library and `API_PORT_RECIPE`). A request that would come too early is **not sent**: it fails with `provider_spacing_required` carrying `sent: False`, `retry_after_seconds` and `earliest_at`. Only `wait` sleeps.
- Daily or per-IP limits beyond these: not stated in any document I read. Unknown.

### 3.3 Submission once; what "accepted" means; idempotency
`submit` writes the intent (`submitting`), makes one POST, writes `submit.response` and `submission.json` (read). A recorded answer is returned on a rerun (`adopted`); a recorded refusal is raised again; an intent without an answer is `submission_outcome_unknown` with `sent: 'unknown'`. **Accepted** = the reply contained a request id (RID) and the service's estimate (RTOE); both go into `submission.json` and the handoff row (`native`: service, remote_id, expected_seconds, directory, the request without the query). `WAITING` is an accepted, unfinished search; it does not say whether the search has begun. The handoff is established by the validated RID (relayed).

### 3.4 What the leaf may do after a failure (corrects the committed leaf)
The `sent` field decides, by the same shared function as section 2.6:

| `sent` | Examples | Next |
|---|---|---|
| `False` | `provider_spacing_required` | wait `retry_after_seconds` and decide one new submit unit. **Safe:** the route raised before it wrote any intent |
| `True` | `provider_http_<status>`, `provider_redirect_not_followed`, `provider_submission_response_invalid` | the service answered and no job was recorded; **end**, report the code; the parent decides whether to commission a new launch |
| `'unknown'` | `provider_request_timeout`, `provider_connection_failed` after the POST began | **end; never submit again**. A new unit would be a new handle and so a second search |

### 3.5 Results, expiry
The leaf fetches nothing. Later, `fetch` (results episode) needs a recorded `finished` status (else `results_not_available`), makes one result request (JSON2), and keeps the files in the job directory, from which later reads are served; so remote expiry only matters before the first fetch. The service no longer knowing the RID shows as provider status `UNKNOWN`, which the route maps to job state `unknown` (read). **How long NCBI keeps results is not stated in any repository document I read.** Design: the results episode fetches promptly after the first `finished`; an `unknown` after an earlier `queued` is reported as "lost or expired", never as "no hits". A native no-hit result is scoped to the submitted operand and settings, not biological absence (relayed, `api-blast.md`). The service has no cancel (`cancel_not_offered_by_the_service`).

## 4. The monitor leaf (long jobs only)

Template: `database_blast/monitor` (committed). Copies for `blast_database_preparation/monitor` (HPC builds only) and `all_vs_all_blast/monitor` (HPC only). Pairwise and small local actions have **no** monitor: their job ends in about a second and the results step's status check and the system's wait on the end event cover it.

### 4.1 One visit
`decide` returns one unit, `check_when_allowed`: wait the number of seconds the decision gives, then one `job_access.check(ctx, handoff_ref, assess=status_reading)`, which writes a `check` row. Wait = the provider's spacing for an API job (read from `describe`), `poll_seconds` for a PBS job, or what the route asked after a refused request. Resume replays a finished unit without waiting again; a unit cut while waiting waits again. No deadline.

### 4.2 What it observes (read: `job_progress`)
State from the fixed vocabulary (`queued`, `running`, `finished`, `failed`, `cancelled`, `unknown`), whether results are available, and measurements by route kind: API: the service's status word and, once finished, whether it found hits; PBS: the return code of an ended job only. Logs (`window` unit) exist for PBS (`stdout.log`, `stderr.log`) and not for API; the committed monitor offers no `window` unit (a design choice to keep: a visit is a status check). What is **not** measured for PBS today (queue wait, start time, used versus requested walltime and memory) is the gap M4.

### 4.3 Credit (D17)
`progress_information`: one information unit for each held check row, outside the baseline the parent passed, that shows a fact of its job the earlier rows do not. Timestamps, elapsed time of an unfinished job and log size are not facts. A repeated unchanged check, a refused check (no row) and a re-read earn nothing.

### 4.4 How it ends (the finding of the earlier monitor test, within the rule)
The earlier monitor fork observed that ending takes several no-gain re-reads because no stop action exists (relayed; the old monitor, accumulation controller, cost 0.2: 4 to 7 units, about 90-100 s of model calls; with the completion controller, earlier tests saw runs go on "through four to five units that earned nothing", `WAIT_ACTION`, relayed). Stopping belongs to the yield estimator alone, so the design does three things and adds no stop action:
1. **Parent rule (removes the main cause):** the parent commissions a visit only when the latest check it holds shows a non-terminal state; when it already shows a terminal state or `result_available`, it commissions results, not a monitor. The parent reads this from `outstanding_jobs` (read: `job_records`), which gives each job's latest check.
2. **Controller:** the committed monitor uses `CompletionYieldController` with target = one information unit: the visit completes at the first newly informative check, and otherwise stops when the predicted upper bound of the next gain is at or below `cost`. `cost` must be below the unit. Pick `cost` as a setting per action and **measure it in the first real run**: how many no-gain units precede the stop is a property of the estimator's forecast that I could not derive from reading.
3. **Code-decided unit:** the monitor makes no model calls, so the no-gain units are cheap (a wait and one status request each), not 15 seconds of model time.

### 4.5 Returns and failures
Returns `credit`, `finding` (`observed`, `checks_made`, `state`, `result_available`) and `check_refs` (the rows it wrote; the parent passes them back as the next baseline). A status the resource did not answer is a returned failed outcome and writes no row. After a **transport-class** failure on PBS the monitor makes no further check in that visit (same rule as 2.5); a monitor that keeps asking the master is the loop the Aurora entry forbids. After `provider_spacing_required` it waits and checks again.

## 5. File sets and what is copied (all three leaves)

Each leaf folder holds exactly these ten files (no `tests/`, no `msg_to_child.py`, no `read_from_child.py`):

```
__init__.py  goal.py  task.py  credit.py  yield_estimator.py  episode.py
messages/__init__.py  messages/read_from_parent.py  messages/internal_summary.py  messages/final_to_parent.py
```

| File | HPC launch | API launch | Monitor | Differs per action? |
|---|---|---|---|---|
| `goal.py` | launch of this action's job | submit of this action's request | check of one job | yes: binding path and the action's wording |
| `task.py` | `launch_<action>_job`, `handoff_read`; `decide` by code; stop rule 2.5/2.6 | `submit` (spacing wait + one submit); `decide` by code; rule 3.4 | `check_when_allowed`; `decide` by code; rule 4.5 | the job-building call; the rest identical |
| `credit.py` | handoff unit once | completion target once | `progress_information` | no |
| `yield_estimator.py` | `CompletionYieldController(handoff_unit)` | `CompletionYieldController(completion_target)` | `CompletionYieldController(information_unit)` | epoch name only |
| `episode.py` | one class | one class | one class | binding path |
| `messages/read_from_parent.py` | the action's job form + controlled allocation | the request form | handoff ref, known checks, information unit | job fields yes |
| `messages/internal_summary.py` | launches, handoff refs | submissions, handoff refs, `sent` | units, own check refs, latest check | no |
| `messages/final_to_parent.py` | credit, finding (+ failure code), `execution_handoff_refs`, `execution_completed` | the same | credit, finding, `check_refs` | no |

Per the repository rules the copies are private and shared code is **library functions only**. Copied per action: all ten files (change the binding path, the job form and goal wording, the yield epoch name). Shared and called: the functions in section 6 under "exists" and, once written, the "missing" ones.

## 6. Library: what exists, what is missing (one home each)

Exists (read): `episode_runtime/job_access.py` (`JobAccess`, `JOB_LEDGER`, `STATES`, `RouteRequestError`, `job_handle`); `jobs/pbs_job_route.py`, `jobs/api_job_route.py`, `jobs/local_job_route.py`; `jobs/job_services.py`; `jobs/pbs_batch_job.py` (`pbs_batch_job`); `jobs/job_progress.py` (`status_reading`, `check_view`, `progress_information`, `LOGS`, `READINGS` for `local`, `pbs`, `api`); `jobs/job_records.py` (`outstanding_jobs`, `handoff`, `checks`, `closure`); `jobs/resource_local.py` (`execute_on_local_resource`); `jobs/job_wait.py` (a set-time wait then one check; used by actions that ask a model to wait, not by the code-decided monitor); `jobs/native_events.py` (waits on a local job's end event only); `forms/.../blast_analysis_kind.derived_analysis_kind`; the preparation-specific `blast_preparation_run.launch_preparation` (composes local or PBS inline).

Missing:

| Id | Function | Proposed single home | Why |
|---|---|---|---|
| M1 | `execute_on_hpc_resource(ctx, resource_id, command, environment, *, allocation, inputs=None, estimates=None, name='job')`: checks kind `pbs`, builds the batch job, launches once | new `jobs/resource_hpc.py` (the recipe's "to write"; `resource_hpc.py` does not exist) | one inspection point per resource kind, as `resource_local` is; replaces the inline composition in `launch_preparation` |
| M2 | `submit_to_service(ctx, resource_id, job, *, inputs, name='job')`: validates the job against the route's `request_schema` and the molecule, launches, returns the outcome with `sent` and `retry_after_seconds` | new `jobs/resource_api.py` (does not exist) | the API inspection point |
| M3 | `allocation_from_commission(fields, resource_settings)` -> the five operand strings from an enum queue, integer nodes, integer walltime seconds, configured account and filesystems; refuses a value above the queue's configured limit | inside `jobs/resource_hpc.py` | controlled allocation (2.2) |
| M4 | PBS reading of a `qstat` reply (state, exit status, start/end times, used versus requested walltime and memory) and `failure_class(native)` -> `walltime_exceeded`, `memory_exceeded`, `exit_nonzero`, `scheduler_killed`, `unknown` | extend `jobs/job_progress.py` (`_pbs`, `READINGS`) | monitor and results read the same function; **fields unverified** |
| M5 | `PbsSshRoute.describe()` should expose `poll_spacing_seconds` (it already holds `poll_seconds`) and the queue limits from settings | `jobs/pbs_job_route.py` | without it the committed monitor's wait is 0 for PBS and it asks the master back to back |
| M6 | staging a large input by path from the resource's own filesystem (a "resident input" verified by a login-mode command) | new function in `jobs/resource_hpc.py` plus a record kind | today every input must travel in the launch request |
| M8 | `launch_retry_rule(failure)` and `monitor_retry_rule(failure)`: one table mapping every route/JobAccess failure code (and `sent`) to `retry_after`, `end_and_report`, `stop_run` | new `jobs/job_failures.py` | the single home of rules 2.5, 2.6, 3.4, 4.5, so no leaf copies them |

(M7 intentionally not used.) Also noted: `examples/aurora_execution_resources.json` is **not** a valid `PbsSshRoute` configuration: the route requires exactly `ssh_argv`, `python_executable`, `workspace`, `scheduler` (a dict of `qsub`, `qstat`, `qdel`, `qselect`) and `poll_seconds`; the example's `scheduler` has `kind` and `required_resources` and it has no `poll_seconds` (decision A10).

## 7. Defects found in the committed partial leaves (by reading only; nothing was run)

1. `launch_api`: after a failure with `sent` unknown (or true), `decide` returns another `submit`; the new unit has a new handle, so the route's "answers the same error" protection does not apply and a second search could be submitted. Its docstring says the opposite. Fix: rule 3.4.
2. `launch_hpc` (preparation): allocation as five free-text operands (not controlled); after any failure `decide` launches again, including after `submission_outcome_unknown` and transport failures. Fix: 2.2, 2.5, 2.6.
3. `monitor`: reads `describe().get('poll_spacing_seconds', 0)`; `PbsSshRoute.describe` has none, so PBS checks are not spaced; it also keeps checking after a transport failure. Fix: M5 and rule 4.5.
4. All three: `action` raises because the system requires the member (open question A9).
5. The earlier run record `runs/db_blast_launch_api_1` shows `launch_api` earning credit 1.0 with 0 model calls and a refusal of `blastn` on a protein; its stderr ends in an error in the run script's cleanup (`'Store' object has no attribute 'table'`), which is not an episode defect. *Relayed from my earlier reading of that run.*

## 8. Owner decisions, each with a recommendation

| Id | Decision | Recommendation |
|---|---|---|
| A1 | Where does the PBS walltime value come from? | Default: the selected queue's configured maximum (the scheduler ends the job, never the application); the parent may pass a smaller `walltime_seconds` within the limit; always recorded in the handoff `estimates`. A short walltime shortens queue wait but kills longer jobs: the owner's cost/risk call |
| A2 | Controlled allocation fields instead of five text operands | Yes: queue (enum from configured list), nodes (integer in range), `walltime_seconds` (integer in range); account and filesystems from configuration |
| A3 | Aurora facts the repo does not hold: the `select=` syntax, current queue limits, and where BLAST+ and HMMER executables and a suitable Python live (the software entry names only Python 3.12.12, Biopython and the gentner source) | The owner supplies them, or authorizes the first HPC action to be a read-only login-mode inspection through the existing master |
| A4 | Large inputs | Add resident inputs (M6); until then inputs must be small enough to stage in the launch request |
| A5 | A lost transport | End the Episode, return the failure code, credit 0, no retry until the owner restores the master (2.5) |
| A6 | API client identification | Generic neutral client name, `contact_email = None`; supply a non-personal project address only if NCBI throttles |
| A7 | Monitor ending | Parent rule 4.4(1), completion controller, `cost` per action, measured in the first real run; no stop action |
| A8 | The first real HPC run | The smallest real job: the 12-protein database build, one node, the smallest allowed walltime, in the queue the owner names (the earlier "debug, one node, five minutes" is a historical observation, not a default); the owner authenticates first |
| A9 | The system's required `action` member for code-decided episodes | A legitimate declared form (`ACTION = None`) in `EpisodeBinding`; that is a change to the system package, not to an episode |
| A10 | `examples/aurora_execution_resources.json` | Rewrite it as a valid `PbsSshRoute` configuration (with `scheduler` command names and `poll_seconds`) |
| A11 | Hosted database vocabulary | Verify `swissprot, nr, refseq_protein, pdbaa, nt` against NCBI's current database names before the first real submission |
| A12 | A chunked run (all-vs-all) has several jobs | One monitor visit per job (the committed form takes exactly one handoff row); the parent loops. PBS array jobs are not supported by the route or builder; chunks are separate batch jobs, each a launch with its own `name` |

## 9. What each build fork does when this lands

- **Before any fork:** the owner answers A1-A4 (at least A3); one library fork writes M1, M2, M3, M4, M5, M8 (M6 after A4) once, in the single homes above, and checks them offline. The three build forks must not write these.
- **Preparation fork:** adapt `launch_hpc` (controlled allocation, rules 2.5/2.6 through M8, call `execute_on_hpc_resource`); copy `monitor` for HPC builds only; the local path keeps `execute_on_local_resource`.
- **Database fork:** fix `launch_api` (rule 3.4 through M8, `submit_to_service`); build `launch_hpc` for a custom database (the prepared-data record names the resident database; the allocation as 2.2); copy `monitor` for both route kinds.
- **All-vs-all fork:** build `launch_hpc` for chunks (N separate batch jobs, one launch per chunk with `name='chunk-<i>'`, ending when every chunk has a handoff; credit per handoff within the commission's target); copy `monitor` (HPC only, one visit per chunk job, A12).
- **Everyone:** the ten-file set; code-decided `decide`; no `tests/`; no real run until the owner defines the real entry; HPC leaves validated offline only and reported as "not run".
