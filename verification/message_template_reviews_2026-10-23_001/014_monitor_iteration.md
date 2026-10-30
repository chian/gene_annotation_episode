# 014 — monitor the assigned running work

```text
TASK

Monitor {the_named_software_job_or_commissioned_work} on
{the_assigned_resource_when_applicable} to determine:
{the_parent's_exact_question_about_its_progress_timing_or_available_results}.
Return {the_specific_information_the_parent_needs} so the parent can
{the_parent's_original_decision_that_this_update_will_inform}.

Observe only {the_assigned_work_and_scope}, within
{the_complete_parent_and_caller_constraints}. Obtain the requested facts and
interpret them through the parent's declared result fields. Keep the requested
job, resource and allocation fixed. Monitoring does not authorize starting,
replacing, retrying, moving or cancelling that work.

Determine what another observation could tell you about this job that is still
unknown. A current execution state can distinguish queued work from running or
returned work. A retained log may explain what the program has reached. A closed
duration measurement can establish how long a particular interval took. A
dependency may explain which work the assigned episode is awaiting. Select the
information needed for the parent's question rather than repeatedly requesting
all fields or following a polling schedule.

Distinguish the episode's lifecycle from the native job or service state. An
episode's return being available does not establish that every computation it
launched has finished. A native result being available does not establish that
it was obtained, interpreted or incorporated into the gene annotation. Preserve
the actual native outcome, failure and output availability alongside the
reported lifecycle. Unknown status remains unknown; a failed status request is
not proof that the job failed.

Evaluate progress using the actual observations. Process liveness establishes
presence, not productive execution. Compare exposed log messages, reported work
counts, output availability and measurements when they can answer the question.
A loading message, batch count or other phase marker can be informative when
the job actually reports it. Missing markers, a quiet log or elapsed time alone
do not establish a stall. Output growth does not by itself establish completed
scientific work or a percentage of the search. Preserve the observation time
and the limits of each measurement.

Read a retained log window when its contents can clarify the job's progress or
failure. The window contains saved bytes from one observation, not a live view
of the whole file. Keep its log role, exact available range, original file
location when supplied, and observation time. An empty window, an unavailable
log and an unexamined log have different meanings. Use a new observation when
fresh exposed information is needed; rereading the saved window does not
refresh it. Do not infer text outside the retained range.

{When this is an HPC target: Examine the actually returned scheduler state,
queue, priority or scheduling-score fields, resource-use fields and scheduler
comments when they bear on the parent's question. Retain their native meanings
and observation times. A priority or estimated-start field is not a guaranteed
start time. Distinguish waiting in the queue from execution. Missing scheduler
fields remain unknown.}

Interpret timing by the interval actually measured. Queue wait, command or
service execution, and submission-to-completion turnaround are different
quantities. An unfinished elapsed measurement is a lower bound, not a completed
duration or a prediction of time remaining. A completed queue interval can be
known while the job is still running. A service-wall measurement does not
separately establish program-only runtime or queue wait.

Use a duration forecast only for the job/configuration and interval it actually
describes. Preserve whether it is a conditional-on-success estimate, how many
complete measurements support it, and relevant failed, incomplete or unmeasured
attempts. Historical minima and maxima are observed ranges, not guaranteed
prediction limits. Exceeding an observed maximum does not imply zero remaining
time. Unknown duration or report-arrival expectations remain unknown; do not
turn a total-duration mean into a report-arrival probability.

If the parent's question requires more information about an exposed direct
dependency, you may commission a monitor for that dependency. State the exact
work to observe, narrower question, constraints, explicitly supplied facts and
the typed information needed on return. The child chooses its own observations.
Use its admitted result with its original times and qualifications. This does
not grant access to private episode decisions, model calls, instructions or
yield histories, and does not authorize traversal through unexposed descendants.
No number, order, depth or cadence of monitoring children is prescribed.

You may select a wait for an actually available event/report or a chosen
reconsideration time when waiting can supply useful information. Choose the
condition using the pending work, received progress and available expectations.
Wait only on events supported for the selected work; native jobs do not all
provide the same notifications. Passing time or receiving a timer wake does
not itself supply progress. After a wake, distinguish the event received from
the status or result that still needs examination. A child return completes its
commission separately from the wait; neither the child's internal turns nor
the wait duplicate its information contribution.

Choose from these actual operations and common actions:

| Choice | Information or repair it supplies | Required inputs and limits |
| --- | --- | --- |
| progress.observe | Obtain an observation of the assigned work. | Choose unique requested_fields only from the originally permitted execution_status, measurements, log_windows, committed_record_refs, dependencies and result_available fields. This observes only the assigned target. |
| progress.read | Read an exact progress observation already received. | Select one delivered observation; this does not acquire fresh status. |
| progress.log | Read one retained log window from an observation already received. | Select the delivered observation and its available nonnegative log_index; this does not select an arbitrary file or new byte range. |
| {an_available_recursive_monitor_choice} | Investigate the requested progress of an exposed direct dependency. | {the_actual_child_commission_fields_scope_constraints_and_parent_defined_typed_return_requirements} |
| {an_available_wait_choice} | Await the selected supported event/report or reconsideration time. | {the_actual_event_or_time_condition_operands_and_restrictions} |
| {an_available_report_repair_choice} | Repair the specific recorded delivery failure. | {the_actual_affected_delivery_operands_and_existing_form_constraints} |

Use your own action-category yields to compare another observation, a saved
detail or log read, a dependency monitor, a wait or a delivery repair. Observed
totals describe completed own actions; expected next yield concerns another
completion of that category, with the stated uncertainty. Unavailable is unknown.
An informative log examination can clarify a decision even when its immediate
recorded gain is zero. Repeated facts, read timestamps and unfinished elapsed
time do not manufacture new monitoring information. Keep monitoring credit,
scientific investigation progress, annotation support and duration expectations
separate. The configured controller governs continuation; a quiet interval or
terminal job state does not introduce another stopping rule.

Return the information requested about {the_named_work}:

| Requested field | Type and allowed values | Exact progress, timing or result-availability meaning | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{all_original_parent_requested_fields_with_complete_meanings_and_constraints}

Update only the declared interpretation fields from information already
received. A selected future observation has no known result yet. Preserve the
parent's permitted meanings for unknown, negative, failed and partial outcomes.
The host fills recorded fields from delivered observations; closing this monitor
does not poll again or call another model to write a report. Return the original
form even if the monitored work remains active. Closing the monitor does not
cancel the target or its descendants and does not rewrite earlier credit.

Use the existing typed JSON response for selection and report_update. There is
no separate scientific-reasoning action in this monitor's available choices.
If an available own-history lookup is needed first, use its declared
request_context fields: {the_readable_existing_own_history_lookup_contract}.
It supplies supported detail for this same pending decision and creates no
completed action or yield observation. These complete TASK instructions are
included on every exchange, including after lookup or reconstruction.

STEERING

| Work being monitored | Resource / native state | Episode lifecycle, if observed | Result availability or failure | Observation time |
| --- | --- | --- | --- | --- |
{only_relevant_latest_delivered_status_rows_with_unknowns_preserved}

| Measured quantity | Actual value and units | Interval or observation meaning | Observed at / limitation |
| --- | --- | --- | --- |
{only_relevant_received_measurements_or_native_scheduler_fields}

| Log window | Exact saved location / retained range | Received text or reported progress fact | Observation time / limitation |
| --- | --- | --- | --- |
{only_needed_actually_received_log_text_or_exact_recorded_progress_values}

| Previous own observation, read or commissioned question | Specific fields, saved observation or window selected | Actual result | What remains unknown |
| --- | --- | --- | --- |
{only_relevant_own_attempt_and_admitted_child_result_rows}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty |
| --- | ---: | ---: | --- | --- |
{original_saved_own_category_rows_or_no_completed_observations}

| Exposed direct dependency / pending own work | Assigned question or actual relationship | Latest received progress and time | Supported event or wait information |
| --- | --- | --- | --- |
{only_dependencies_and_pending_work_that_affect_the_next_choice}

| Relevant job/configuration and measured interval | Expected duration / observed range | Statistical support and qualifications | Unknown information |
| --- | --- | --- | --- |
{only_compatible_existing_duration_or_wait_expectations_needed_now}

| Requested interpretation | Current value | Actual received basis or limitation |
| --- | --- | --- |
{current_requested_interpretation_rows}

| Failed action or delivery | Preserved partial result | Specific failed input or missing information | Repair-relevant fact |
| --- | --- | --- | --- |
{only_actual_actionable_failure_rows}
```

## Construction notes — outside the model prompt

Fill the opening from the original parent question, assigned execution target
and meaningful job/episode/resource description. Do not invent software, a
resource kind, an annotation candidate or a biological claim for a target that
does not supply one. Monitoring does not authorize literature monitoring or add
a new episode relationship. The assignment and actual caller capabilities still
define the eligible target.

TASK is detailed and recurring. STEERING is separately selected factual content,
with no narrative recap, IDs, hashes, revisions, configuration dumps, private
parent history or private child trajectory. Render only relevant rows and omit
inapplicable tables. Render the HPC paragraph only for an actual HPC target.
Requested result meanings and actual operation meanings stay in TASK; current
values stay in STEERING. The host's durable target/observation identities and
event cursors remain internal. Existing typed response and original return
schemas remain unchanged; readable operand binding is integration work, not a
new output parser or capability claimed by this draft.

| Fill and decision | Actual producer → selection → receiving use |
| --- | --- |
| What work to observe and why | Original request goal, contained scope, `monitor_assignment.target_handle`, parent `ReportContract.decision`, constraints and declared return meanings → name the actual work and parent question → choose useful observations without taking over its execution. |
| Which information may be obtained | Complete `MonitorEpisodes.catalog`, `permitted_common_actions`, `prepare_assignment`, `execute` and `allowed_children` → render three actual progress tools plus actually available child/wait/redelivery choices → no scientific reason action, arbitrary command/file access or descendant traversal. Requested fields cannot exceed the original assignment; child record types cannot expand those originally permitted. |
| Already received status and measurements | `ProgressProvider.observe/read_progress`, first-receipt `receive_outcome/receive_form`, `Workflow.progress_selection`, explicitly supplied initial observations and admitted child forms → select actual received field contents and original times → distinguish old facts, fresh work and unavailable information. |
| Native meanings | `progress_records` and `ExecutionProgressProvider`/`HomologyProgressProvider` → retain lifecycle separately from actual API/local/PBS native state, outcomes, outputs and closed intervals → no invented universal phase, percent completion, throughput or stall metric. API HMMER observations currently provide no native log windows or duration measurements. Local observations expose actual service status, bounded stdout/stderr and terminal service-wall timing. PBS retains actual `queue`, `Priority`, `base_score`, `project_priority`, resources/comments when present, queue wait from `qtime` to `stime`, turnaround from `qtime` to `obittime`, and the requested command's recorded wall duration. |
| Which log to read | Delivered snapshot's log windows → retain exact saved window, role, original file-range metadata and observation time when actually supplied → `progress.log` reads retained source bytes rather than polling a live file. Source metadata has original native offsets; snapshot window coordinates address the retained artifact. Do not confuse those two coordinate spaces or manufacture the original path/range if unprojected. |
| Whether deeper monitoring helps | Explicit `ProgressProvider.direct_dependencies` and original relation records → render only eligible direct work and its actual state/time → commission an independently iterating monitor for a selected dependency, with its own requested form. No private traversal or automatic fanout. |
| Whether waiting helps | `Workflow.pending_work`, `waiting_support`, actual received progress, supported event bindings and original compatible expectation snapshots → display only useful pending state, intervals/support and unavailable reasons → episode selects its event set or reconsideration time. Default `estimate_wait` supplies no event-probability or monitoring-gain model merely from a duration mean. Native notification availability must come from an actual binding. |
| Which own category yielded information | `decision_history.category_for/yield_table` → unchanged saved signed completed-own-action gains and category forecasts in completion order → compare observe/read/log, monitor child, wait and repair. Expected category bands are approximate uncalibrated presentation estimates conditional on category completion, not completion probabilities or replacement controller inputs. |
| What earned current monitoring credit | Explicit caller `ProgressInformationCredit`, `Workflow.source_credit_view` and received-progress selection → semantic status/dependency/availability/closed-duration facts with the original supplied baseline → one caller-scaled unit per newly informative received snapshot. Several novel facts in one snapshot still earn one unit; repeated facts, timestamps, unfinished elapsed time, output-byte growth and raw-log changes alone earn no unit. Useful log interpretation and current credit eligibility therefore remain distinct. |
| What to return | `MonitorEpisodes.facts/validate_report` plus `DecisionSource.finish` / `form_with_facts` → original delivered observations and last declared interpretations, frozen without fresh acquisition → parent receives only its original admitted form. Requested committed records retain the parent's permitted types. The parent's own integration and credit projection remain separate from child-local scores. |

## Concrete integration limits

1. `DecisionSource.next` still assembles a large context object and the provider
   still sends `json.dumps(context)`. The text/table renderer and complete
   recurring TASK construction are not implemented by this document. Current
   instruction assembly also appends monitor instructions to the default
   application instructions rather than supplying this role-specific task.
2. `MonitorEpisodes.decision_context` exposes assignment and observation
   references, not these selected factual contents. Received snapshots and own
   saved action outcomes can supply most cells, but the current own-outcome
   index is metadata and selected-input history lookup does not restore old
   outcome bodies. `progress.read/log` are actual selected tools, distinct from
   the in-decision own-history exchange. Do not pretend a hash or reference
   supplied the omitted result.
3. Raw local/PBS native details retain additional facts beyond the compact
   measurement and log lists. Their decision-specific projection needs exact
   field selection, meaningful labels and provenance, not a whole native-object
   dump. The renderer must preserve original observation times and native versus
   retained-log coordinates.
4. Physical job providers expose no dependent jobs by default and do not all
   publish events through the durable episode event port. An eligible target or
   progress snapshot alone does not prove a usable notification subscription.
   Waiting must expose this actual limitation instead of fabricating a cadence
   or report-arrival forecast.
5. This generic `MonitorEpisodes` binding has no practical completion-proof
   hook. A terminal native job state alone does not supply the practical
   exact-zero-future-yield exception. If the caller later binds a validated
   endpoint for this original monitoring assignment, that proof and the
   existing contextual estimator must establish the exception; it must not be
   added as a prompt-only stop rule. Scientific episode completion is unchanged.
6. A monitoring snapshot can retain useful log/queue/progress facts that the
   current caller-selected credit projector does not value. This review does
   not adjust that projector, add pseudo-scores, change raw gains or claim a
   timing-statistics export merely because an observation was delivered.

Inspected the required goal, episode structure, timing design and practical
endpoint records; the task/steering/directness contract; complete
`episode_monitoring.py`, `execution_progress.py`, `homology_progress.py`,
`progress_records.py`, `episode_services.py`, `episode_progress_credit.py` and
`resource_estimation.py`; complete relevant native API/local/PBS observation
methods; and complete shared decision/action/receipt/credit/form/return and
controller/model-input consumers. Current provider input serialization and the
own-yield and lookup interfaces were traced. No application code, tests, network
requests, SSH sessions, model calls, jobs or scientific runs were changed or
executed. Only this proposed template was added. It is ready for the user's
running feedback, not settled or implemented.
