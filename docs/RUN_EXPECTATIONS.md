# Shared execution expectations and local episode learning

Global history records execution expectations across compatible execution classes.
Each child retains its own yield history and expectation snapshots. Shared
history contains typed run statistics; scientific credit remains separate.

## Ownership

| Mechanism | Owns | Does not own |
| --- | --- | --- |
| Native execution recorder | Measured phase timing, outcome, provenance, execution configuration | Scientific interpretation, child yield, continuation |
| Shared history | Durable execution observations and descriptive expectations for compatible execution classes | Child credit histories, scientific findings or recommendations |
| Caller | Shared history path, resource identities, explicit resource-condition updates | Fabricated execution measurements |
| Child yield estimator | Its next-work estimate, informed by its own history and a particular expectation snapshot | Rewriting shared measurements or other children's estimates |
| Task-credit projection | Goal-relevant recorded contributions and their communication | Treating timing, polling or a global timing revision as scientific progress |
| Controller | The configured continuation rule | An extra timeout, stop rule or gate derived by the statistics store |

`gene_annotation_episode/run_statistics.py` has no access to the scientific
Store, runtime journal, models, controller or episode tree. Infrastructure gets
`RunHistory`. Episode-facing tools can be supplied an `ExpectationReader`, which
opens SQLite read-only and can retrieve a particular immutable snapshot.
The reader is bound to the snapshot references supplied by the caller for that
child's context; it cannot substitute a different execution class or silently
switch to a newer version.
`execution_expectations.ExecutionExpectations` binds explicit execution classes
to selected episode types in the shared scientific runtime. Its v3 homology
binding additionally records caller-selected `planning_roles`. The fixed-case
harness selects `annotation` and `improvement`. Before each new decision for
those types, `HomologyEpisodes.prospective_execution_classes(store, scope)` derives
classes from actual eligible protein records and the bound resources, including
the available CPU allocations. It neither creates a job nor translates a gene.
An empty eligible inventory supplies empty classes/forecasts; later actual work
can make a protein available for a subsequent decision.

A fresh decision receives its captured statistical context and independent
resource/tool forecasts before choosing work; the exact supplied context is
persisted before model dispatch. The runtime also supplies it to that episode's estimator after
its completed action, paired with the measured action and decision-call times.
This is a runtime input binding, not a separately selected child or report tool.
It is optional caller configuration, frozen in the run settings. The operational
launch/monitor/results roles have an optional shared-runtime binding described
in [HOMOLOGY_EPISODES.md](HOMOLOGY_EPISODES.md). Their production score/time formulas
remain incomplete. Do not infer a configured-model end-to-end demonstration.

## Restricted information

An execution class has a declared phase/backend, caller-configured resource
identity, implementation/parameter digests, resource limits, thread count,
query/reference sizes, reference availability and the duration measurement's
meaning. It contains no gene identity, annotations, hypotheses, result text or
episode instructions. Null implementation/context fields mean unrecorded;
they do not establish compatibility with a known implementation/context.
Resource identities must distinguish hardware or execution environments where
the caller knows they differ; this prototype does not discover hardware changes.

Each measurement has an attempt digest, source-receipt digest, UTC observation
time, enumerated execution outcome and duration kind, finite elapsed seconds
(or an explicit unknown), and an optional resource-condition reference captured
at execution start. Measurements have no arbitrary dictionary or text field.
The attempt identity represents the physical execution, not a query checksum:
replaying the same receipt contributes once, while another actual execution may
contribute another sample. A conflicting replay reports an identity conflict
and preserves the original observation.

Live poll samples remain in the job's own durable records. They are not new
completed execution samples. This API records one immutable timing receipt per
physical phase attempt; it does not yet implement later corrections/refinements
of an already recorded incomplete receipt. A future recovery integration must
handle that explicitly, preserving attempt identity and old snapshots. A failure
to publish statistics must not erase job results or be reported as scientific
failure. The native completion binding now preserves this separation and
recovers retained exports; see [NATIVE_EXECUTION_STATISTICS.md](NATIVE_EXECUTION_STATISTICS.md).

Snapshots contain the exact execution class, an observation watermark, the
current caller-reported resource condition and statistics grouped by observed
condition and execution outcome. Complete durations have sample count, mean,
minimum and maximum. Lower bounds and unknown times have separate counts; a
lower bound is not a completed duration or a zero-time success. Failed execution
durations do not enter the successful-duration mean.

The initial expectation method is explicitly named
`empirical_complete_duration_mean_by_condition_and_outcome_v1`. These are
descriptive statistics, not a calibrated completion-time distribution, remaining
time, information-gain score or controller cost. One sample supplies one observed
duration. It does not establish confidence, variance or forecast accuracy. This
initial implementation groups exact configurations/sizes; it does not silently
extrapolate to a different-sized gene, database, binary or parameter choice.
No arbitrary credit weights, time exchange rate or smoothing of child yields
have been added.

Only the statistical interface is shared outside the episode tree. It cannot
transport reasoning or scientific results around the report boundary. Children
still fill parent-defined typed forms. Requested resource/tool forecast fields
preserve `execution_class_ref`, `expectation_ref`, and, for prospective work,
`proposal_ref` with null `job_ref`. These references resolve from original
recorded forecasts. Prospective resolution checks actual in-scope configurations
without requiring a submitted job; later history does not substitute a new
snapshot. Reports remain parent-defined rather than receiving an unsolicited
statistics dump.

The forecast uses the successful complete-duration mean for the exact class and
current recorded condition. Its typed `outcome_support` distinguishes succeeded,
failed, cancelled, resource-limit and unknown outcomes, with attempt,
complete-duration, lower-bound and unmeasured counts and maximum observed lower
bounds. Null support means unavailable/invalid statistics; zero counts describe
known empty history. Observed minimum/maximum are historical ranges, not calibrated
prediction intervals. CPU describes allocation, memory/scratch fields describe
configured limits, and neither measures consumption. Local service wall time
does not separately measure queue wait or native-program runtime. No remaining-time
subtraction or transfer across query sizes, CPU allocations or duration measures
is supplied.

## Updates and temporal meaning

`capture()` freezes a snapshot in the shared SQLite history. Subsequent runs can
produce a new snapshot; earlier snapshots remain unchanged. An unrelated
execution class does not invalidate a snapshot. Measurements and condition state
are read in one transaction. Append checks are serialized across writers.
No new data changes a child's past credit or creates a controller observation.
The runtime retains the snapshot used with the decision that used it. Completed
and pending saved decisions reuse their original context on replay. A genuinely
new decision may see a newer snapshot. A missing/unreadable history produces an
explicit unavailable statistical context, not a zero duration or automatic stop.
A consumer does not initialize a missing database or add statistical tables to
an unrelated SQLite database.

## Local estimator input and accounting

`run_workflow(..., execution_expectations=binding)` records the caller's shared
path and per-episode-type execution classes. Resume restores this binding;
an explicit replacement is a configuration conflict. The caller must select
types exposed by this workflow. Episodes cannot override these classes/path in
their action content.

The assigned-homology selector derives its class from the immutable
job assignment and selected CPU/query size in the caller-bound registry.
The parent supplies CPU when ordering; the launch child checks/applies it and
cannot replace it. Prospective and assigned classes use the same
`HomologyStatistics.execution_class_for_query` constructor on actual query bytes.
After reservation, the recorded native class is reused. This selector is data-only
caller configuration; it does not poll execution, change credit or let episode
content replace global resource identities. Decisions still pin the selected
snapshot before dispatch. See [CASE_EXECUTION.md](CASE_EXECUTION.md).

`runtime_estimation_contexts` stores one immutable local context per completed
own action. It contains the captured statistical input, original resource/tool
forecasts at selection and, where recorded, after the action, plus that action's
measured decision/work times. It does not contain an ancestor/descendant history
or a private child result. Failed actions do not create contexts or controller
observations. A completed child invocation is one parent action regardless of
the number of child actions. Its inclusive timer closes before the context is
recorded, so the parent receives a completed duration rather than a running
clock sample whose replay value would drift. These inclusive durations must not
be summed across episode levels as compute consumption.

`YieldController(..., estimate_with_context=callback)` gives a caller-selected
local estimator this interface:

```python
callback(raw_credit_changes, parameters, completed_action_contexts) -> YieldEstimate
```

The two histories are rank-aligned tuples of the same completed own actions.
Each context retains its original expectation version and measured time; neither
tuple contains previous predictions or other children's yield estimates. The
callback must return an estimate for that same action history. Custom estimates
retain their declared provenance, or an explicit caller-injected function binding;
they are not automatically attributed to the nano-graphrag template. The base controller
still applies its defined upper-bound/cost rule. The default template-derived
scalar insight estimator remains numerically unchanged. The separate
duration/resource estimator supplies another decision input; no gain-per-second
conversion, time penalty or new stopping condition is inferred from that
separation. Timing information earns monitoring credit and updates execution
expectations; scientific information earns scientific credit. The forecaster
does not assign either score or classify a job by its intended purpose.

Tests with synthetic providers and explicit fixture estimators exercise the
complete method-loop input path, within-child snapshot updates, form isolation,
raw score preservation, inclusive parent-child timing, failures, global-history
unavailability and interruption/replay. Their numeric bands/stopping counts are
test policies, not proposed production monitoring rules. Production scientific
and job-specific scoring choices remain unresolved, and real configured-model
execution remains to be completed.

`set_condition()` is caller-only: a resource identity, enumerated condition and
reason, UTC report time and stable caller operation identity. There is no freeform
message. Conditions persist until the caller explicitly changes them; no automatic
expiry or job cancellation follows. The original observed timings survive an
outage notice. A late-arriving old measurement does not inherit today's outage
label: unrecorded execution-time conditions stay unspecified. Explicit recovery
also leaves earlier observations and snapshots intact.

The caller supplies one history path; no per-workspace default silently creates
isolated learning stores. Current development uses
`resources/run_statistics.sqlite`, across any future run workspaces that bind it.
The local resource alias `local-development` is explicitly supplied at import;
it is not a measured historical hardware fingerprint.

## Actual probe import and verification

```bash
.venv/bin/python cases/gene_001/register_run_statistics.py \
  --history resources/run_statistics.sqlite \
  --local-resource-id local-development
```

The importer verifies the retained native inputs/outputs, streams the observation
archive for the two phase-start identities and imports only the two measured
protected-service durations. It does not submit another job, import scientific
results into global history or change biological state. The reference-acquisition
helper's execution-time hash and resource condition were not recorded; these
remain unknown rather than being supplied from today's environment.

| Phase | Complete successful samples | Measured duration |
| --- | ---: | ---: |
| Reference acquisition, download required | 1 | 580.9212270560092 s |
| Single-query protein homology search, references available | 1 | 1.5410503179882653 s |

`cases/gene_001/run-expectations.json` records the actual class/snapshot bindings.
`cases/gene_001/run-expectations-verification.json` records actual replay evidence:
two measurements remain two, bindings are unchanged, native process creation was
forbidden during replay, and the scientific database and native receipt hashes
remain unchanged.
`cases/gene_001/verify_preparation.py` reproduces this check and exercises the
runtime's input-binding class against the two actual saved statistical snapshots.
It also verifies canonical evidence registration separately. This remains case
preparation, not a configured-model episodic run.
The cached database remains reusable. Its acquisition cost is not charged again
merely because another gene uses it. Successful timing does not establish a gene
function. The earlier unfinished minimap2 credit scaffold is not used.

Focused tests cover durable sharing across reopened connections, duplicate and
conflicting replay, immutable snapshots, exact compatibility, outcome/censoring
separation, caller outage/recovery and late receipts, read-only child access and
the restricted data boundary. Runtime integration tests described above extend
that evidence through the actual method-loop execution boundary. Neither group
verifies model-driven annotation, approved credit formulas or parallel execution.
Separate job-role tests cover the role binding and parent-selected delayed
commissions; they do not establish a production time/yield policy.

The current correction passed **40 tests** in 96.59 seconds across
`test_case_execution.py`, `test_homology_jobs.py`, `test_assigned_expectations.py`,
`test_homology_episode_runtime.py`, `test_resource_estimation_contract.py` and
`test_episode_timing_learning.py`. Those checks include prospective parent input
before any order, refresh after explicit protein acquisition, immutable parent
CPU allocation through a tiny native run, frozen forecast form references, and
actual measured timing reaching monitoring credit, updated expectations and a
subsequent scripted parent choice. No configured-model scientific investigation
or new production numerical formula was demonstrated by these fixtures.
