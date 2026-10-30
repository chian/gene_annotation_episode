# Durable execution for the fixed gene investigation

The selected biological question remains the function of the one fixed ybhP
gene. A native homology search supplies evidence about that question. Executing
the search, obtaining matches, or handing off a job is not an annotation result.
The empirical full-corpus probe and its 20 registered HSP observations remain
in `cases/gene_001`; development did not rerun that unchanged search or download.

## One execution implementation

`local_jobs.py` retains the caller-owned resource policy and the existing blocking
and cancellation-safe async tool interfaces. It delegates execution to
`native_lifecycle.py`. Detached execution uses that same implementation, rather
than another subprocess runner or a private episode loop.

The lifecycle has these ordinary operations:

* `prepare_job`: persist a complete, frozen reservation without contacting systemd.
* `start_prepared`: dispatch that reserved unit once, then verify its cgroup and
  release its command; an already-dispatched reservation is never resubmitted.
* `start_job`: the existing blocking-adapter convenience path through those same
  preparation and dispatch implementations.
* `resume_start`: finish an undispatched reservation or its existing startup
  handshake; never replace its command or unit.
* `status`: read the service, native receipt, elapsed time and file availability.
* `collect`: return the original native outcome or a typed operational failure.
* `cancel`: stop/reap the existing control group on explicit caller request.
* `release`: remove transient control files only after the unit is quiescent.

The protected worker monitors allocated scratch while the native command runs.
Both share the verified cgroup. The monitor therefore survives the launching
episode and workflow process. No supervisor daemon or live launcher connection
is required. Memory is hard-capped; swap is disabled; the aggregate scratch
limit is monitored with possible overshoot, alongside hard per-file FSIZE.
Explicit `RuntimeMaxSec=infinity` and a verification of that value enforce the
user's unset work-time policy. The startup/control handshake has its existing
infrastructure deadlines; it is not a native-work or episode timeout.

Native exit/signal identity is recorded separately from the wrapper's systemd
exit. An OOM/timeout claim uses actual service evidence. A wrapper death does
not invent a native exit code. The mapping adapter's resource-failure consumer
now preserves that distinction, including a null native exit when unobserved.

## Standard durable native format

A job owns one JSON handle plus request, readiness, release, native-result and
systemd-completion files. Writes of JSON receipts use atomic replacement and
fsync. The handle binds the exact command, working directory, output locations,
effective policy, actual verified limits, unique unit and monotonic start/boot
identity. The completion hook records actual end/boot identity. Collection later
does not turn time spent waiting to inspect a finished job into execution time.
A missing terminal receipt stays unknown, with no invented zero duration.

The request file is fsynced before the prepared handle is published. Its byte
digest binds the worker's actual request to the reservation. Dispatch validates
it, and the worker checks it before parsing/executing the request; the readiness
receipt retains that same identity. These are execution/communication checks,
not scientific relevance or quality judgments. A prepared reservation has null
start/boot timestamps and no elapsed execution time. Dispatch establishes them.
The native handle protocol is now `durable_systemd_native_job_v2`; older
unreleased native handles are not migrated. New runs use the new protocol.

The new duration measure is `systemd_service_wall_seconds`. Older probe samples
use `protected_service_wall_seconds`, which included their collection latency.
These are distinct recorded execution classes; historical samples are not
relabeled. Children/estimators may consider their declared meanings explicitly.

Blocking tools retain stdout/stderr and complete returned metadata while freeing
transient control files. Detached callers retain the handle and receipts on disk.
Closed episodes do not own or retain the live native execution object.

## Homology service and typed handoff

`homology_jobs.HomologyJobs` adds a persistent registry for one-query phmmer work.
The caller supplies the executable/database assets, their digests, limits and
available CPU allocation. The selected query is a frozen operand, identified
separately from the job/registry and from an episode audit identity.

`order` records the requested operand without staging or submitting it. Launch
tools can inspect the environment, configure CPU, stage private input snapshots,
submit, repair an interrupted native startup and check the handoff. These are
available operations, not a prescribed sequence of episode turns. Staging reuses
unchanged prepared inputs and can repair missing unsubmitted input bytes without
recopying the valid reference database. Submitted input/configuration is fixed.
There is no database reacquisition when the caller already has the corpus.

The handoff contains only registered job/registry references and declared backend,
status, progress and results interface codes. `check_handoff` opens a **new**
registry connection and exercises exactly the receiving `receive` interface.
The existing closed-form guard checks declared types and actual references.
The receiver also verifies that the native handle's command, directory, policy
and output paths describe the registered job. A syntactically valid ID cannot
relabel another job's native execution. Incorrect fields return contract feedback
without replacing the job or discarding its output.

The first successful functional-check receipt retains its actual sample and time;
later checks still exercise the receiver, without inventing duplicate receipt
contributions. Monitoring samples have their actual observation time and a stable
operation identity. Replaying one selected sample returns the recorded sample;
it does not reread a changing clock as new progress. This service assigns no credit
for a new sample identifier or for elapsed time.

The status interface reports actual execution state, outcome, elapsed time,
native return code, basic failure/resource codes and per-output existence/bytes.
For a finished failed process, available files can be valid partial evidence.
`writer_closed` means no further writes from that job; it does not claim the
file is complete scientific output or that an annotation is correct. No hit
count, byte count or running CPU measurement becomes percentage searched.

`result_file` resolves only a declared output role against the admitted handoff.
It is an internal helper for ordinary results-acquisition tools, not a separate
results-reader episode or automatic scientific interpreter. The bounded reusable
parser and canonical result-publication API are now implemented; see
[HOMOLOGY_RESULTS.md](HOMOLOGY_RESULTS.md). The optional shared-runtime binding
exposes them within a scoped results-acquisition child.

## Failure and recovery limits

A complete native reservation now precedes the registry's submission marker.
Process loss on either side of that commit can resume dispatch of the same
never-submitted unit. Kernel file locking serializes launch/preparation changes
and releases automatically when its process exits. Query/CPU identity stays
fixed once reserved. Before dispatch, staging can restore missing exact operand
bytes while retaining an unchanged valid reference snapshot. It cannot change
the problem or repair input bytes while the native command may be using them.

Prepared jobs report `prepared` with no elapsed duration and cannot claim a
usable submitted-job handoff. The responsible episode receives its job identity
and constrained unavailable-handoff facts; its yield estimator still owns
continuation. A parent may commission a new iterative launch/repair investigation
using `existing_job_ref`. That keeps the same job, inputs and reservation rather
than creating a replacement or reopening a closed child's private history.

Missing reservation data for a recorded request remains `submission_unconfirmed`.
A `submitting` attempt whose original backend unit cannot be observed also stays
explicitly unknown. Neither absence authorizes another backend launch. This
ambiguity is distinct from the repaired, provably undispatched reservation path.
Recovery after backend acceptance and before release still resumes that same
actual service. No universal exactly-once recovery from lost backend evidence is
claimed.

The registry does not validate query ownership against a scientific Store on its
own: the commissioning runtime must resolve that supplied semantic operand and
the one-gene scope. It also does not enforce which episode receives each tool.
The optional shared-runtime binding now supplies that ownership, scoped operands,
closure handoff facts, monitoring/results roles and parent-selected delayed
commissions. See [HOMOLOGY_EPISODES.md](HOMOLOGY_EPISODES.md). Its engineering
checks do not establish a configured-model scientific investigation.

## Verification scope

The focused resource/adapter group passed 44 checks; the explicit cgroup OOM
probe remained skipped. It includes actual detached launch-owner exit, recovery
of the same unit after startup-owner loss, stable completed durations, no work
time cap, cancellation/group cleanup, hard file and monitored scratch limits,
sequence workers and adapter preservation of partial valid native rows.

A tiny actual phmmer test used the fixed gene's sequence against a one-reference
test corpus. It verified staging repair/reuse, duplicate-submission prevention,
functional handoff across closed/reopened registry connections, actual typed
monitor samples, actual native results and rejection of mismatched interfaces,
registries and native handles. This is an operational test, not a new full-corpus
scientific comparison, numerical credit validation or configured-model workflow.

Subsequent checks include actual process loss immediately after reservation and
immediately before dispatch, recovery of the same unit across reopened registries,
changed-request refusal both before dispatch and inside the worker, deferred
timing/condition capture, and parent-selected iterative repair of an existing job.
The affected group passed 43 checks with OOM skipped; after the final version/
compatibility grouping change, 13 focused recording/job-role checks passed.
These counts overlap and remain engineering evidence using fixture policies.

An optional caller-bound completion recorder now exports new search receipts to
global execution history; see [NATIVE_EXECUTION_STATISTICS.md](NATIVE_EXECUTION_STATISTICS.md).
Approved monitoring/scientific credit, time-based yield and the model-driven
scientific demonstration remain incomplete. No existing arbitrary minimap2
scores or default hypervolume binding were adopted for this example.

## Parent-selected search sensitivity

Callers can explicitly expose `search_modes = ["native_defaults",
"maximum_sensitivity"]` in the case execution configuration. With that
capability, a new launch commission must include its parent's selected
`search_mode`. Launch, repair and acquisition assignments preserve that value;
the launch child cannot change it through configuration. A requested
`job_search_mode` fact returns the same value through the parent's typed form.
Older saved registries continue their original native-default command.

`maximum_sensitivity` supplies phmmer's native `--max`: all acceleration
filters are disabled and every reference is subjected to full scoring. The
installed HMMER 3.4 manual describes a slight sensitivity improvement at a large
speed cost. Reporting/inclusion thresholds and downstream scientific
interpretation are not changed by this wrapper. Extra runtime, additional
matches or a native significance flag do not themselves earn scientific credit.

This is relevant to the fixed gene because the retained fast search supplied
mostly self-identities and weak distant leads, leaving the functional question
unresolved. Examining filter sensitivity is an available investigation, not a
required experiment or a promise of a characterized homolog. It must not be
chosen just to lengthen a monitoring demonstration.

Prospective context supplies local `job_execution_options`: actual query, CPU,
mode and corresponding execution-class reference. These map selectable operands
to their forecasts before any job order exists. Query identities stay in local
episode configuration, not in global run statistics. The mode enters the
statistical parameter digest; default and maximum-sensitivity durations are
distinct classes, with no invented extrapolation. Unknown duration stays unknown.

Submission and receiving-interface validation use one canonical command
constructor, including the immutable mode. Native output custody retains that
actual command; acquisition continues through the existing parser/publication
path. No extra controller, scoring rule, timeout, delay or private loop is added.

The new tiny native-job regression verifies parent selection through actual
launch, same-job repair, acquisition, parent use and replay. Its default-mode
forecast stays unknown after the maximum-sensitivity duration is recorded.
This does not establish full-corpus usefulness or configured-model selection.
See `tests/test_homology_search_modes.py`; current counts are in BUILD_STATUS.md.
