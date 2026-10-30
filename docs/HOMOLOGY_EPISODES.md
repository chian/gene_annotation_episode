# Job roles in the shared episode runtime

`run_workflow(..., job_episodes=HomologyEpisodes(...))` exposes three additional
child types beneath scientific annotation/improvement episodes. They use the
same `DecisionSource`, `FeedbackEpisode`, journal, archive, typed report guard
and numerical continuation boundary as scientific children. There is no private
job decision loop or prescribed sequence of children.

| Participant | Selected work | Information returned |
| --- | --- | --- |
| Scientific parent | Scientific reasoning/tools; select the query and CPU allocation when commissioning a launch; commission monitoring or results work, optionally after a selected delay | Receives its requested child form; integrates scientific results |
| Launch child | Inspect environment, apply/check the assigned CPU allocation, stage/repair inputs, submit once, repair the existing startup, exercise the handoff | Requested recorded job/allocation/handoff facts and constrained interpretations |
| Monitoring child | Select actual status/progress samples; read its own saved history | Requested immutable sample fields and constrained interpretations |
| Results child | Extract/page native evidence, explicitly retry extraction when selected, inspect extraction errors | Requested canonical evidence references and constrained interpretations |
| Runtime | Execute the selection, record outcomes, project caller-bound credit, deliver the form, apply the controller | Does not choose investigations, manufacture scientific results or substitute actions |

The parent does not receive `homology.submit`, and job children do not receive
the scientific tool catalog or a scientific commitment action. The launch query
must be an explicit protein of the assigned input target; acquired references
cannot become new annotation targets through this interface. The registry order
created when commissioning retains the selected query and CPU as an immutable
assignment. `jobs.order(..., cpu=...)` requires that explicit allocation, bounded
by the caller's `max_cpu`. `homology.configure` takes an empty argument object
and applies/checks the assignment; it does not offer a replacement allocation.
Low-level `jobs.configure(job_ref, cpu)` likewise requires the stored CPU.
Ordering does not execute the job.
Only the launch child's selected submission executes it.

A launch commission may instead name `existing_job_ref` to investigate/repair
an existing in-scope job. That commission has no replacement query/CPU operands.
It preserves the frozen query, CPU allocation and native reservation;
it does not implicitly replace the job, repeat execution or expose a previous
child's private decisions. A closed child can retain unavailable-handoff facts
while a later repair child reports a usable handoff for that same job.

A monitoring commission explicitly names `prior_sample_refs`, using an empty
array when it supplies none. Each reference must be a stored sample of that
same assigned job. The immutable sample values become the child's incoming
baseline; reading them creates no sample or progress. Its credit projector can
therefore distinguish new observations from what the parent already knew. This
information passes through the parent's commission, not global shared history.

The parent may also supply `prior_checked_statuses`, an optional array of closed
status objects received from launch. Each contains the actual status plus
`checked_at_unix_seconds` and must exactly match a successful selected
`homology.check_handoff` result for the assigned job and registry in the action
journal. Changed values or an unrecorded check cannot establish this baseline.
These immutable facts seed known states, outcomes, output states, completed
durations and elapsed bounds alongside prior samples. They do not become sample
records, earn inherited monitoring credit or enter global statistics. Omitting
this optional input preserves the original assignment shape on recovery.

## Forms and functional handoff

The parent still supplies its schema, purpose and initial interpretation fields.
`job_episode_options` documents each role and the available factual schemas;
the runtime does not choose the parent's form. Recorded facts bind through
`x-source`, with the same closed-form guard as other child reports.

Available operational facts are `job_ref`, `job_cpu`, `job_handoff`, `job_handoff_state`,
`job_handoff_failure` and `job_sample`. The handoff is populated only after a
fresh registry connection exercises the actual receiving interface. A child
yielding without a usable handoff returns null and a constrained basic failure
code when those fields are requested. This does not override its controller,
force another turn or claim successful launch completion. A sample is the last
sample actually selected by that child, not an implicit poll at report time.
`job_cpu` reports assigned CPU threads, not measured CPU consumption.

Launch additionally offers optional `job_checked_status`. The parent can request
it under its own form field name with `x-source: job_checked_status`. Its value
is the last successful **selected** handoff check's recorded status and timestamp,
or null if none succeeded. Closure's functional check neither supplies nor
replaces this value. It gives the parent already-obtained status, elapsed time
and output availability without a new poll, sample, composer or observation.
It is a historical check-time fact, not a claim about status at report delivery.

The duration forecaster's measured-sample input remains selected or explicitly
inherited samples. Supplying a checked status as monitoring knowledge does not
fabricate a sample identity or sample-based elapsed forecast. The child sees
the full known status in its assignment and can choose whether a new sample
would add useful information.

The status/baseline correction passed 41 affected checks in 110.63 seconds,
including real native execution with scripted choices and fixture controllers.
The integration traverses the returned launch form, parent-selected baseline,
immutable monitoring assignment, unchanged sample with zero gain, newly completed
timing with one contribution, and replay with no extra samples/observations.
Separate checks reject unrecorded or altered status/timestamp/job/registry values,
exclude rediscovery of completed timing and elapsed overruns, and preserve the
assignment shape when the optional input is absent. Independent source review
found no further concrete defect after the absent-key recovery correction.
This does not demonstrate configured-model selection of these new fields or
production stopping behavior; the separate numerical lifecycle check below
addresses the production controller with scripted selections.
The four baseline-specific checks subsequently passed in 13.71 seconds after
strengthening completed-duration and overrun fixtures to validate the actual
checked-status schema. The overrun uses a separately recorded matching systemd
measurement class, preserving the older class and its frozen history.

Results children can additionally expose `job_result_progress` and
`job_result_progress_failure` when the parent requests those typed facts. The
progress object identifies the last snapshot actually selected by the child,
its query and physical job/registry, parsed and acquired row counts, exact
one-based half-open ordinal intervals, and separate parser/native completeness
fields. It contains no unrestricted failure payload. An optional coverage read
failure returns null progress and a constrained basic code while preserving
valid acquired references and other requested facts.

The selected `homology.coverage(snapshot_ref=...)` tool reads that same durable
inventory and row witnesses without polling, parsing or publishing records.
An acquired parsed prefix is not necessarily a complete native result. Extract,
coverage and error reads all enforce the captured physical job/registry identity;
an earlier job's snapshot cannot substitute for the assigned job even when its
query and execution inputs match. See [HOMOLOGY_RESULTS.md](HOMOLOGY_RESULTS.md).

Operational references must belong to the assigned job and fixed target scope.
Native fields accompanying a sample identity must match that actual stored
sample. A real identifier cannot be relabeled with fabricated elapsed time or
job status. Interpretive choices retain the parent's declared meanings.

Requested execution forecasts retain their `execution_class_ref` and original
`expectation_ref`. Prospective forecasts additionally have a configuration
`proposal_ref` and null `job_ref`; reference resolution checks the actual
in-scope configurations without fabricating an order. Assigned forecasts retain
the job/scope checks. Later history does not replace a saved forecast's values.

Closure facts are frozen once. Parent credit projection and report redelivery
reuse them; neither repeats the functional check nor updates a historical sample
to a later clock value. The existing `redeliver_report` path supports operational
facts and the same job identity restrictions. Representation repair performs no
new native/scientific work and creates no yield observation.

The common optional runtime fact `episode_yield` exposes the child's actual
closing numerical band, continuation cost/decision and completed-action count.
The parent chooses whether to request it, using the closed schema in
`available_report_facts`; it is not automatically added to a job form. It contains
no private history, diagnostics or global findings. See
[EPISODE_YIELD_REPORTS.md](EPISODE_YIELD_REPORTS.md) for its exact fields and example.

## Credit, statistics and completed actions

The caller must supply separate named launch/extraction and monitoring credit
bindings and projectors. Each
receives the role, immutable assignment, episode/run identity and authoritative
Store. Each successful/partial own outcome is saved before projection. Recovery
of a saved outcome awaiting its projection does not repeat the native operation.
Historical saved scores replay unchanged. The caller also supplies the task
projector and controller factory; this binding refuses silent adoption of the
default scientific scorer/controller.

No production launch/monitoring/results score, time exchange rate or estimator
formula is silently selected by this binding. Test scores and fixed-length fixture
controllers are test policies only. An unchanged poll is not automatically
credited; the chosen projector must reflect the requested useful information.

The optional execution-expectation binding supports these role names and explicit
parent `planning_roles`. Before a new bound parent decision, the runtime derives
prospective classes from actual eligible in-scope protein records and caller
resources. It presents the separate duration/resource forecasts before work is
selected. No eligible protein means an empty proposed-class/forecast list;
this read does not translate a sequence or prevent other work. Later decisions
refresh the inventory after actual acquisitions. Scientific evidence, task credit and child yield histories do
not enter global execution statistics. An optional caller-bound completion
recorder now ingests newly completed search attempts independently of episode
lifetimes; startup/tool recovery retries receipt export without repeating work.
See [NATIVE_EXECUTION_STATISTICS.md](NATIVE_EXECUTION_STATISTICS.md).

Credit follows the information gained: timing information earns monitoring
credit and updates execution expectations; scientific information earns scientific
credit. A job is not classified in advance as exclusively timing or scientific.
The execution forecaster itself computes duration expectations and assigns no
credit. The implemented monitoring projector recognizes newly measured completed
durations; its numerical scale remains caller configuration, not a selected
production policy.

One completed child invocation is one parent action, regardless of its internal
turns. Functional form checks, report repair, statistical refresh and timer firing
do not add controller observations. Selected tool failures retain actionable
feedback and the existing runtime's failure accounting.

## Parent-selected timed commissions

A `job_child` selection may include nonnegative `delay_seconds`. There is no
default delay or polling cadence. The parent can base that choice on previous
monitoring forms and its estimator. The runtime durably records the exact
selection, child identity, scheduling time and due time before waiting. Firing
starts that selected child; it does not make another model decision. The entire
delayed invocation is one parent action, including the timer wait in its measured
wall time. No separate timer event is scored.

When requested, the recorded closing monitoring yield gives the parent the
post-action forecast rather than the earlier estimate visible to the child's
last model call. Returning it creates no new credit or observation and does not
choose a delay. The estimate remains in the child's configured controller units;
it does not become a job completion-time forecast or the parent's task score.

Interruption/resume preserves the original due time and reuses the same child.
This first sequential binding awaits its selected delayed child. It does not
provide concurrent commissions or an external daemon that restarts a stopped
workflow; those are distinct capabilities, not implied by a durable timer row.

## Verification scope

`tests/test_homology_episode_runtime.py` uses the actual shared tree, an actual
one-reference phmmer search, canonical Store and bounded parser with scripted
decisions and explicit fixture credit/controllers. Its coordinated native wrapper
is labeled synthetic: the test holds execution until a monitoring child has
closed, then releases actual phmmer. It is not relabeled biological evidence.

The checks cover parent/role tool ownership, unchanged-poll scores, delayed
monitor recommissioning, actual evidence returned and used by a parent tool,
interruption after submission, interrupted timer recovery, sample-fact fidelity,
and contract repair from saved facts without another launch. They do not prove
configured-model scientific reasoning, a production yield formula or completed
gene annotation.

The current parent-allocation/prospective-binding verification passed **40 tests**
in 96.59 seconds across `test_case_execution.py`, `test_homology_jobs.py`,
`test_assigned_expectations.py`, `test_homology_episode_runtime.py`,
`test_resource_estimation_contract.py` and `test_episode_timing_learning.py`.
It includes a parent-selected CPU=2 reaching the immutable assignment, real native
command, statistical class and requested form; rejected child substitution;
prospective references through the real form boundary; and actual timing followed
by monitoring credit, updated parent expectations and a subsequent fixture decision.
The case harness also exercises an initially absent protein followed by an
explicit translation action and refreshed forecasts on the next decision.
These are scripted engineering fixtures with tiny native workloads, not a
configured-model investigation or approval of scientific/monitoring score choices.

The current registry/backend is `single_query_phmmer_jobs_v2`; the serialized
episode binding is `shared_homology_episode_binding_v3`. Existing v1 registries
are not silently migrated or reinterpreted.

The subsequent native-results verification passed 11 direct adapter checks in
182.32 seconds and two shared-runtime/form checks in 28.15 seconds. The latter
exercise overlapping acquisition pages, an explicit read without polling,
exact closure facts and a coverage-storage failure that preserves delivered
evidence. These fixtures select no production acquisition score or controller.

## Receiving failures and retained facts

A later focused review established an operational failure path at commissioning
and closure. It did not establish a hidden stopping rule. The implemented repair
has the following scope:

| Audit field | Evidence and effect |
| --- | --- |
| Owner | `HomologyEpisodes` owns receiving-interface facts; `DecisionSource.next` returns operational commission feedback to the selecting parent. |
| Trigger | A receiver registry read/write fails, a service-control subprocess fails, or the registered order becomes unavailable after an immutable assignment was recorded. |
| Code path | `assign` through `DecisionSource.next`; `_execute` and optional statistics export through `execute`; `facts`, `latest_sample`, `resolve` and `validate_report` through closure/form admission. |
| State effect | Existing selected outcomes, assignments, sample bodies and scientific records remain unchanged. Closure freezes unavailable-handoff facts. A failed optional statistics export records unavailability instead of replacing the selected outcome. |
| Communication effect | The parent receives operational assignment feedback or the existing `receiving_interface_unavailable` closure value. Exact assigned job/CPU, original journaled samples, recorded forecasts and existing scientific references remain returnable when the job registry later fails. |
| Credit effect | No added contribution, erased result, synthetic sample or score change is implied by the failure handling. |
| Controller effect | Failed assignment/setup supplies feedback without a completed action or observation. Closure validation does not override continuation. |
| Run evidence | No configured-model occurrence of these storage/control failures is established. Focused fixtures inject receipt-write failure, registry loss and control errors. |
| Correction | Normalize receiving failures at the existing boundaries; resolve exact assigned identities through retained assignment/query evidence; use original journaled/inherited sample bodies. Unknown identifiers and altered recorded values remain invalid. |
| Verification | Seven focused checks passed in 43.67 seconds. After adding missing-order and closure-timeout coverage, the affected communication/native-role/forecast/recovery group passed 39 checks in 132.72 seconds. These groups overlap. Independent source rereview found no further concrete defect in this focused path. These are scripted engineering checks with tiny native jobs. |

Registry loss is not permission to accept an arbitrary job/sample reference.
The fallback uses the immutable assignment and its actual in-scope query, or an
exact sample returned by a completed selected action or inherited through the
commission. The scientific Store must remain available. It is not a substitute
job registry for new execution. If a sample has not been retained there, the
usual registry lookup must establish it. Altered fields remain rejected.

Closure retains all declared factual sources, including those not requested in
the original form, for later parent-defined report repair/redelivery. Its fresh
functional check does not replace the child's last selected sample. Removing
that check merely because its fields are initially unused would change the
existing redelivery capability.

The unchanged production controller has a minimum eight-observation fit window
in the current case. A five-action launch ending in a successful handoff still
continues at that point. Available tools remain available; no infrastructure
function chooses a repeat or appends zero observations. Finite operational
credit and this controller can leave further selected checks/reads at zero
gain. This is an explicit provisional binding limitation, not authorization to
add a handoff-completion stop, action quota or automatic repeat.

## Numerical lifecycle integration

`tests/test_operational_numerical_lifecycle.py` passed in 40.55 seconds. It uses
`create_policy`'s actual scientific, launch/results and monitoring projectors
and its actual numerical controller with cost 0.001, window 8, subsample 4 and
alpha 0.05. There is no fixture stopping counter or alternative yield estimator.
Every observation follows an explicitly selected completed operation. All five
episodes ended through `yield_stop`; each final available upper bound was below
the recorded cost, with no earlier controller stop.

In this executed fixture, launch took 46 actions, the two monitors took 15 each,
results acquisition took nine and the parent took 58. Each operational child
had one nonzero gain; the parent's scientific score stayed zero throughout.
The native result reached its typed parent form and an actual selected parent
inspection. One timed commission supplied one parent action; one physical
attempt entered the separate statistics history. Closed episodes invoked
provider release. These observed counts are not imposed caps or generic
predictions for other histories. They expose the cost of the current
provisional finite-credit/controller combination after useful work is exhausted.

Decisions and order are scripted stand-ins, not configured models. The existing
explicitly synthetic barrier holds a tiny real phmmer job until the first
monitor numerically closes. The fixture then releases and waits for native
completion before selecting a second monitor after a constant 0.01-second
delay informed by the returned stop flag. Thus it proves numerical closure,
form delivery, accounting and timer plumbing. It does not establish a useful
timing policy, representative native duration, scientific annotation or
configured-model planning. The duration includes the artificial barrier.
Independent source review found no concrete fidelity defect within that scope.
