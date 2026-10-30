# Time-aware estimates within episodic execution

The accepted independent-execution target is now docs/EPISODE_STRUCTURE.md.
Explicit yield-informed waiting and pending-work-aware continuation are required
there. The older descriptions below document the existing duration/forecast
bindings and their historical repairs; they do not establish implementation of
independent processes, recursive monitoring or wait-yield estimation. Waiting
estimates must inform the episode's choice without becoming an autonomous
scheduler, a new global scientific-learning channel or a hidden stopping rule.

This records the user's 2026-10-20 clarification, source reviews and the current
episode refactor. Verification status below distinguishes inspected code from
executed paths. The separate execution-tool checkout is not the episode runtime.

## Responsibility and meaning

**Latest resource-choice clarification (2026-10-21):** the scientific parent
assigns the job and constraints. Launch chooses an execution approach where the
choice is open, then commissions a resource-specific iterative child for
API/external-service, local-compute or HPC work. Timing expectations must inform
the episode making that choice. Explicit caller/parent resource constraints
remain binding. Older parent-selected-resource descriptions below explain the
existing flat local implementation and earlier repairs; they do not supersede
this new direction or establish that the nested launch is implemented. See
`EPISODE_STRUCTURE.md` for the current boundary between discussion and code.

The word policy here means estimation support. The estimator supplies expected
duration and the statistical support behind it. It does not choose an action,
resource, delay, probe, retry or cancellation. Each episode receives information
with which to make its own authorized decisions. Its configured local yield
estimator/controller continues to own numerical continuation.

The responsible parent selects the requested job and execution resources from
the caller's actual available capabilities. It can use prior measured durations
to decide what is worth doing, including an inexpensive experiment to learn
execution or waiting times. There is no mandatory timing experiment, estimate
call or experiment-to-production sequence.

A launch child carries out the parent's selected work. Its preparation and
failure repair can require genuine iteration: retrieve resource instructions,
inspect the environment, attempt preparation/submission, inspect outcomes and
revise the relevant approach. Individual operations remain tool calls. Iteration
belongs to the episode rather than being hidden inside another agent loop.
Following a selected resource assignment does not remove the need for these
agentic implementation and repair decisions.

Resource knowledge retrieval and execution tools are available within episode
execution. They are not another workflow layer. Useful findings pass through
the parent's declared typed form; the durable shared history continues to carry
only typed run statistics. Scientific credit, monitoring information credit,
execution-duration forecasts and local yield histories keep separate meanings.

Timing information updates time expectations and earns monitoring credit for
having gained timing information. Scientific information earns scientific credit.
These are separate projections of the information actually obtained. A job's
label does not establish its information value.

Time/resource estimation and its use in episode iteration are the first build
priority. Correct tool execution alone does not establish this behavior.

## Observable progress during a wait

The user clarified that monitoring benefits from job progress information,
including relevant log observations, so an episode can assess whether work is
loading a large model, processing batches slowly, advancing normally or possibly
stalled. These are examples of considerations, not required phases for every
job. Record the progress actually exposed by the selected job or service.
Relevant observations can include phase markers, completed work, timestamps,
throughput and resource measurements, with their job identity and provenance.
The episode interprets those observations; infrastructure does not infer a
stall merely from elapsed time or impose a new timeout, retry or stopping rule.
Child information still reaches its parent through the requested typed form.
An informational observation alone does not authorize a new credit formula.

Current inspection establishes limited visibility: `HomologyJobs.status`
returns native execution state, elapsed service-wall time, output availability
and byte counts. Its schema explicitly makes no search-completion-fraction
claim. These fields do not establish internal loading stages or batch
throughput. The model connection separately waits for a Codex app-server
response; the current monitoring-child interface does not monitor that call or
expose its service phase. Operator polling of that execution handle is not an
autonomous monitoring episode or an episode-selected polling cadence. No private
model conversation, reasoning content or provider event log was read to make
these observations. Richer progress visibility is not claimed as implemented.

The later HomologyProgressProvider binding now retains selected native stdout
and stderr windows, exact original offsets and observed file sizes, immutable
artifact bytes, observation times and source provenance. C8 and recursive typed
monitor forms consume those saved observations; selected-operation replay does
not poll again. A three-worker engineering consumer verified actual tiny phmmer
output while its owning episode remained live. Log text supplies observable
facts for episode interpretation; this adds no internal stage/throughput model,
stall rule, numerical wait-gain formula or model-service monitoring. See
NEXT_PARALLEL_BATCH.md for the exact ports and verification scope.

## Gaps established before this refactor

1. **Information arrives too late for initial planning.**
   `runtime.DecisionSource.call` produces resource forecasts only for job-source
   episodes. `case_execution.run_prepared_case` installs execution expectations
   for launch/monitor/results roles only. A parent can request child-returned
   forecasts, but has no corresponding prospective estimate tool before its
   first commission. This is an information-routing gap, not a need for a
   scheduler or action-selection formula.
2. **Allocation ownership is wrong.**
   `HomologyEpisodes.commission_schemas` accepts a new launch query without CPU;
   `assign` orders it without CPU. Its launch catalog supplies
   `homology.configure(cpu)`, explicitly described as selecting CPU. The current
   tests assert this child-owned CPU transition. Those tests establish current
   behavior, not authorization. Parent-selected allocation must reach durable
   assignment, launch execution and returned facts consistently.
3. **Compact duration reports omit support needed for useful decisions.**
   `RunHistory.capture` retains outcome groups, complete/lower-bound/unmeasured
   counts and maximum observed lower bounds. `ResourceToolEstimator` currently
   reports the successful complete-duration count and mean/min/max only. The
   parent cannot distinguish one success alone from that same success alongside
   many failed or unmeasured attempts using this compact form.
4. **Queue and workload-transfer estimates are not established.**
   The present native receipt measures local service wall time. It separately
   establishes neither queue wait nor native-program-only runtime. The exact
   execution class includes workload size, CPU, implementation, options, corpus
   digest and duration measure. A smaller workload therefore does not currently
   supply a numerical duration estimate for a larger workload.

No review established an actual run making a bad scientific decision because
of these gaps. No implementation or test was changed during these reviews.

## Smallest coherent correction

Supply prospective estimates in the scientific episode's next-decision context.
They describe its actual eligible queries and permitted CPU allocations using
caller-bound execution resources. Resolve corpus, executable, resource identity
and limits from those bindings. The episode can then choose work using its own
yield estimate and these time/resource expectations. No separate forecast query
is required to receive expectations for already available configurations.

The estimate lookup must work without creating a job order, staging inputs or
submitting anything. A proposed execution configuration has its own durable
identity; it must not fabricate a physical job reference. Preserve its original
statistical snapshot in the selected operation record for replay.

Suggested closed result fields and meanings:

| Field | Meaning |
| --- | --- |
| Proposal/configuration reference | Exact proposed work and resource operands; not a submitted job |
| Availability status | Available, no matching history, unavailable history or invalid statistics |
| Duration measure and method | What interval was measured and how the estimate was derived |
| Successful complete sample count | Number supporting the conditional-on-success duration estimate |
| Expected total seconds, nullable | Empirical mean for the compatible class and recorded condition |
| Observed minimum/maximum, nullable | Historical observed range; not a calibrated prediction interval |
| Typed outcome/censoring support | Attempt counts by outcome, complete/lower-bound/unmeasured counts and measured lower bounds |
| Original expectation reference | Provenance for this estimate, retained with the operation |

No suggested action, chosen resource, compulsory delay or stopping output belongs
in this result. Missing history informs the episode; it does not prevent launch.
Reading a forecast cannot earn scientific progress or create a fictitious job
completion. The selected read retains the existing own-action accounting rules;
it adds no extra observation merely because statistics were refreshed.

The parent's launch commission must carry its selected CPU/configuration into
the durable job order and immutable child assignment. The launch child's
configuration operation applies that assignment; preparation or failure repair
does not silently replace it. An unfulfillable request returns structured facts
to inform the responsible episode. Preserve iterative staging/startup/handoff
repair, original job identity, numerical continuation and valid partial work.
Make actual assignment facts available through the existing requested form.

## What a timing experiment can teach

A simple actual job can teach measured setup/availability and its own duration.
Its native receipt enters the same restricted global statistics interface, once
per physical attempt. Repeated polling and report delivery are not new runs.
Timing information from an experiment earns monitoring credit and updates time
expectations. Scientific information is assessed by the scientific projection.

Exact-class empirical summaries are implementation-ready. Transferring a small
experiment to a larger workload requires an explicit model and typed workload
relationship. A possible future model distinguishes startup overhead and
work-dependent throughput, but one measurement cannot identify both. Corpus
composition, cache/I/O behavior and CPU scaling can affect transfer. This is
not an approved formula. No numerical extrapolation is silently supplied by the
initial correction; the episode can still reason from what was actually measured.

Future queue-enabled tools must distinguish measured queue wait, execution and
submission-to-completion turnaround. Present local service-wall records cannot
be relabeled as queue observations. An elapsed unfinished run is a lower bound;
an overrun does not imply zero remaining time. Later observations update future
expectations without rewriting completed actions or closed-child credit.

## Verification for implementation

- A parent can obtain a typed prospective estimate while the job registry has
  no corresponding order or submission.
- The parent's actual selected configuration is the one launched, sampled,
  reported and recovered after interruption; no child substitution occurs.
- A selected timing experiment yields one physical measurement. A later
  compatible estimate can use it; a different-size request remains explicitly
  unsupported for numerical transfer until such a model is bound.
- Failure, censoring, missing history and duration-measure mismatch stay visible
  as typed information without adding a launch or scientific approval gate.
- Original estimates, raw credit changes, observation counts, typed report
  boundaries and closed-history release survive replay unchanged.

These corrections precede a configured-model single-gene investigation.
Parallel launches and queued-resource deployment remain subsequent work.

## Current refactor and verification limits

`ResourceToolEstimator.estimate_context` projects expected duration and statistical
support for prospective execution classes without requiring a physical job.
Assigned and prospective estimates share the same projection. Typed fields retain
the original expectation and class references, outcome counts, incomplete-duration
counts and unknown measurements. This is a duration/resource component, not a
new scientific credit formula or an action selector.

The subsequent ordinary-scientific-child form correction exposes prospective
forecasts as requested `x-source: resource_tool_estimates` facts. Initial values,
updates, final admission and redelivery compare supplied forecast values with
their original journal records. Reference namespaces identify forecasts and
native samples/jobs/registries; parent-selected field names are not reserved.
Static caller-bound forecasts also work without a homology job binding. Closure
uses the latest completed own action's original forecast, not a fresh global
estimate.

After this correction, 38 forecast/native/contract checks passed in 141.84
seconds, then six separation checks passed in 9.77 seconds. A broader 89-check
group passed before the namespace correction; the groups overlap and must not
be added as unique coverage. Independent source review found no remaining defect
in these requested paths. None of these checks launched a configured-model
scientific investigation.

`DecisionSource.call` supplies those estimates before a new non-job decision when
the caller binds execution expectations. Planning configurations are refreshed
from actual eligible query records; saved decisions retain their original inputs.
The fixed-case harness binds planning roles for annotation and improvement
episodes. A new launch commission requires the parent's selected CPU; the durable
order, child assignment, native command and requested `job_cpu` fact retain that
value. The launch configuration tool applies that assignment rather than
selecting a different allocation.

The monitoring draft identifies `new_completed_timing` in recorded samples,
including when the terminal state was already known but its measured duration
was not. It uses the existing caller-selected monitoring information scale.
The native receipt exporter separately updates durable time statistics.

An existing native runtime regression produced 33 passes and one failure after
the forecast schema changed. Its saved report-delivery failure was
`unknown_reference` at
`report.execution_forecasts[0].execution_class_ref`. The forecast existed, but
the receiving form could not resolve its new reference. The resolver has been
changed. Subsequent verification passed 40 tests across
`test_case_execution`, `test_homology_jobs`, `test_assigned_expectations`,
`test_homology_episode_runtime`, `test_resource_estimation_contract` and
`test_episode_timing_learning` (96.59 seconds). These include prospective forecast
references delivered through the actual resolver/form boundary and a tiny native
CPU-2 job whose command, assignment and returned form agree. They also establish
that eligible planning classes refresh after an actual protein translation.

The timing-learning integration executes a tiny native job through scripted
episode decisions. Its completed duration contributes monitoring information,
enters the durable statistics once, and changes the parent's next-decision
forecast while scientific credit stays unchanged. A repeated timing observation
adds no monitoring contribution. These engineering fixtures do not establish a
configured-model scientific investigation or select production credit units.

The independent audit confirms that the unchanged scalar insight-yield estimator
is not itself a defect. The time/resource estimator is a separate source of
expectations for episode decisions. No gain-per-second conversion or change to
the numerical continuation rule is implied by this separation.

## Timing first learned during launch or repair

The explicit `monitoring.include_handoff_checks: true` binding projects selected
successful handoff checks as execution information alongside selected samples.
A check keeps its original checked timestamp and has no sample identity.
Monitoring-information facts and their score are available through the existing
parent-defined form for job roles, separately from each role's operational or
scientific controller score. Closure communication checks earn nothing.

Check-aware commissions, including launch repair of an existing job, can carry
parent-known exact checked statuses and sample references. Shared assignment
validation binds them to the actual job and durable values. Rechecking a known
duration earns zero. No controller formula, timer cadence, combined score or
physical-attempt statistics rule changes. Existing sample-only saved bindings
remain unchanged. See LAUNCH_TIMING_INFORMATION_AUDIT.md for verified defects,
corrections and verification limits.

When a caller exposes more than one homology search mode, local
`job_execution_options` maps actual query/CPU/mode operands to each prospective
execution-class reference. The mode enters the statistical parameter digest.
Shared history contains no scientific query identity or assertion; the local
mapping is configuration information for the owning episode's decision.
One mode's measured duration does not create an estimate for the other mode.

## Ordinary native timing: alignment and XLSX

Ordinary alignments and XLSX selections now use the same typed completion/statistics publisher as
detached work. Durable native_execution receipts carry actual operand roles and
the exact measured timing. NativeTimingInformation uses the existing caller-bound
monitoring unit, received receipts and the frozen inherited/original baseline;
scientific credit remains independently projected. Requested parent forms carry
constrained measured fields with reference/fact validation, without a model
report composer. Unrequested receipt data does not cross merely because the
child measured it. Failed scientific publication preserves timing information
and does not complete the failed action.

The optional execution.estimate tool captures expectations for a proposed
sequence.align, source.xlsx.sheets or source.xlsx.rows configuration before running it. It shares operand preparation
and workload/configuration identity with actual dispatch. Already received native
classes and the latest explicit proposal can refresh typed expectations before
later decisions. The existing ResourceToolEstimator supplies forecasts; no tool
chooses an investigation, allocation, timer or cancellation. Original predictions
stay with the decisions/actions that used them. Native statistical inputs and
before/after-action forecast records also reach the existing completed-action
estimation context, separately from raw scientific gains.

A 47-check group passed, including actual small alignments under scripted episode
decisions, typed child/parent delivery, inherited/repeated zero gain, failed science,
committed-action interruption/recovery, cross-run prospective learning, preserved
original forecasts and unavailable-history reports that do not block work. These
are engineering checks; the configured-model investigation retains its pinned
earlier implementation. A subsequent 97-check group passed in 172.75 seconds
with the XLSX path integrated; a later overlapping 24-check group passed in
82.10 seconds, including pending-export recovery. Workbook compatibility uses
actual input byte size and technical selection features, never the biological
filter literal or workbook/source identity. It is a historical empirical grouping,
not an assertion that equally sized workbooks have identical execution cost.
The typed local receipt names the input source; the shared history does not.
Wrong-sheet failures retain their measured duration with no completed failed
action; partial selections preserve valid rows and separate timing information.

Before a new ordinary forecast, compact pending measurement receipts can retry
export through the existing history writer. The original physical identity,
start condition, destination and measurement survive unavailable history; no
native work reruns. The original completed action and its forecasts remain
unchanged. Recovery/scan failures stay structured information. Other ordinary
native adapters still need their complete paths traced; universal coverage is
not established. See ORDINARY_TOOL_TIMING_AUDIT.md for the observed cases,
responsibilities, corrections and verification limits.

## Availability is not a fixed stopping window

The configured window of eight is the minimum number of completed actions before
fitting. It does not make an all-zero-gain history yield after eight actions.
Investigation_007's root started at 15, remained at 15 through 11 completed own
actions, and its saved marginal history contains eleven zeros. The actual fitted
upper estimate is 0.052372762675616774, above its configured cost 0.001. This is
continued application of the recorded rule, not inherited progress counted as a
new gain. A direct pure-estimator diagnostic gives upper 0.07619158557694622 for
eight zeros and 0.005802316250821756 for forty zeros. Model-dependent fitted bands
need not behave like a zero-count shortcut or a fixed polling allowance.

No zero-history override, early-stop condition or changed fit is installed.
Caller-owned continuation costs can be discussed using actual histories; a
historical prefix crossing another threshold is not a guarantee for a future
child, particularly when its inherited observations differ. The pending proposed
execution-role thresholds were unapplied at that checkpoint. Accurate forwarding of parent-known
statuses is still required to prevent duplicate credit, independently of whether
that changes a particular estimator's stopping time.

Investigation_008 later produced a 46-action launch and 46-action monitor whose
recorded estimates first cross cost 0.01 at action 31 and cost 0.1 at action 18.
A subsequent monitor in that same run first observed an already completed job
and yielded after 15 actions at cost 0.001. These different actual histories
reinforce that a threshold does not prescribe a turn count.

After retaining investigation_008 at an explicit maintenance interruption,
investigation_009 binds caller-selected verification costs of 0.1 for job_launch
and job_monitor, leaving other roles at 0.001. This operator-selected trial
follows an optional preference question; no user approval is claimed. It changes
the existing numeric comparison's cost operand prospectively. Raw credits,
information units, estimator formula, original observations and prior policies
remain unchanged. No forced zero-history stop, timer cadence, native work delay
or episode action cap is added. Actual configured-model monitoring/timer outcomes
must still be inspected; the configuration alone proves none of them.


## Presentation addendum: task and steering, 2026-10-23

Keep the detailed recurring TASK instructions distinct from the terse STEERING
update. Decision-relevant yield expectations, uncertainty, pending progress and
compatible duration information belong in controlled factual steering tables.
Their configuration, implementation and tracking records do not belong in the
model prompt. Making those updates concise must not abbreviate the episode's
actual task or problem-solving instructions. See
[TASK_AND_STEERING.md](TASK_AND_STEERING.md). Estimation and continuation
mathematics are unchanged by this presentation requirement.
