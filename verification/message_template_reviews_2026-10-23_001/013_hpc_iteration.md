# 013 — run the assigned job on the selected HPC environment

```text
TASK

Run {assigned_software_and_exact_requested_job} on {the_selected_HPC_environment},
using {the_assigned_input_files_or_database}. Deliver
{the_parent_requested_usable_job_handoff_or_completed_job_outputs} so the parent
can {the_exact_requested_use_of_that_handoff_or_output}.

Keep this requested job unchanged:

| Job requirement | Exact assigned value |
| --- | --- |
| Program and arguments | {original_requested_argv_expressed_as_an_exact_command_or_argument_list} |
| Job environment | {the_original_requested_environment_overrides} |
| Project workspace | {the_actual_bound_absolute_workspace} |
| Charging account | {the_actual_bound_account} |
| Queue, allocation and other limits | {every_relevant_parent_or_caller_constraint_and_allowed_choice} |
| Result that finishes this assignment | {usable_handoff_or_completed_outputs_explained_in_terms_of_this_job} |

Prepare, reuse, inspect or repair only what this job needs. Choose one available
operation at a time, inspect its actual outcome and use that result to choose
the next operation. Individual commands, file operations and PBS observations
are actions within this episode. This HPC assignment has no child branches in
the available binding; keep the work on the assigned environment rather than
switching to local execution or an API service.

{Full selected instructions for this software, its inputs and this HPC
environment: how to establish the required executable, environment, database,
launcher or wrapper; what each relevant check establishes; and the limits on
reuse or repair. Render substantive instructions here, not library identifiers,
section indexes or a short process name.}

Use the recorded preparations to decide what may already be reusable. Compare
the executable, environment, database or index needed by this job with the
actual supplied component descriptions and observations. Matching local and
remote catalogs establish agreement about recorded preparations; they do not
establish that a file still exists, a module still loads or the program works
with the assigned inputs. A dated cached catalog remains useful with its age
and access limitation. Inspect a relevant uncertainty when it could change your
choice. Do not reinstall an environment, rebuild an index or download a database
merely because this is a new episode. Repair a missing or incompatible component
when actual evidence calls for it; retain preparations that still meet the job.

Keep setup requirements separate from current run conditions. A working
executable can remain reusable while queue availability, account balance,
filesystem load or a resource request makes a different permitted submission
more useful now. Use actual current observations when those conditions matter.
A selected diagnostic command can obtain needed queue, filesystem or environment
information; no probe is compulsory. Preserve the parent's explicit queue and
allocation constraints. If those constraints cannot be met, retain the specific
conflict for the requested return rather than substituting a different job,
account, allocation or environment.

For Aurora, keep software, environments, databases, caches, inputs, temporary
files, logs and run directories under
/lus/flare/projects/BioReason-Aurora-Test. Charge new PBS jobs to EpiCalib using
the bound account. The only workflow file allowed in Aurora home is
/home/chian/WORKSPACE_DIRECTORY.md, the small directory index. Set working,
output, temporary and cache locations explicitly in project storage. Follow
the selected site instructions for the required filesystem and queue resource
clauses; an old test's queue, walltime or account is not a default for this job.

Use the supplied connection and actual remote interpreter. Their presence in
configuration does not establish current authentication. A failed transport
does not establish a failed job submission. Keep authentication or connectivity
problems specific to the actual attempted operation; do not guess hosts or
credentials. Access requiring human authentication needs the user's assistance
through the parent or caller, not invented credentials stored in the task.

Use practical.context.set for a working-directory or environment change that
later preparation actions must retain. A subprocess cd or export affects that
subprocess only. Preparation commands use the saved working context and their
explicit overrides. The requested job retains its original argv and job
environment; setting a preparation environment does not replace them. If the
job needs a module-loading wrapper or launcher, prepare it consistently with the
assigned command rather than silently changing that command.

Before selecting a submission, choose the actual queue and resource clauses
allowed by the job and current observations. The bound account remains fixed.
Preserve the original attempt when a submission reply is missing or ambiguous.
A nonzero qsub client result alone does not prove scheduler rejection. Observe
or reconcile the original submission; do not submit replacement work to resolve
uncertainty. An explicit retry may name the original execution only after its
actual terminal failure is confirmed. Retrying an unconfirmed submission without
an actual PBS job identity is unsupported by these operations.

Interpret scheduler and log observations for what they show. A queued job is
not yet executing; a live process does not establish useful progress. Queue,
priority, resource-use, native state, timestamps and selected stdout/stderr
windows can help distinguish waiting, preparation, active computation or a
possible problem. A log tail is a bounded window, not the complete log; read
another selected file window when needed. Preserve observation times and unknown
fields. Keep queue wait, requested-command wall duration and total turnaround
separate. Use duration expectations only for their actual measured interval and
statistical support. An old small-job duration does not establish this job's
runtime, and elapsed time alone does not establish a stall or authorize a retry.

The original assignment defines what must be validated:

| Required fact about this job or its preparation | What actual evidence establishes it | Required for finishing? | Assigned operational credit |
| --- | --- | --- | --- |
{original_requirement_predicates_in_readable_terms_with_original_credit_units}

Existing satisfied preparation is starting information, not new work. Actual
selected-action outcomes supply validation. Repeated unchanged facts gain zero;
an observed loss retains its signed effect. A correctly executed command can
earn zero, and a command that returns nonzero is still an actual executed action.
Keep valid partial results and use the failed command, path, resource clause or
missing observation to choose a repair. Do not award yourself credit or replace
recorded checks with a prose claim of success.

Use only the available operations below. Choose them for what the job needs;
their order is not prescribed.

| Available operation | What it does for this HPC job | Required inputs and limits |
| --- | --- | --- |
| practical.inspect | Observe the assignment's declared file checks now. | No operands. |
| practical.inventory.refresh | Read the selected preparation catalog and reconcile its local mirror. | Exact catalog path within the assigned workspace. |
| practical.context.set | Persist cwd and explicit environment for later preparation actions. | Existing project cwd; complete explicit environment map. |
| practical.directory.create | Create a selected project directory. | Exact path within the workspace. |
| practical.file.write | Write the selected UTF-8 content. | Project path and exact text. |
| practical.file.read | Read a selected file or log window. | Project path, nonnegative byte offset and positive byte limit. |
| practical.command.run | Execute one preparation or diagnostic command on the assigned host. | Exact argv and explicit environment overrides; uses the current working directory. |
| practical.job.start | Submit the original requested job to PBS. | Allowed queue and nonempty resource-clause list; an explicit retry additionally names the confirmed failed original execution. |
| practical.job.status | Observe the original requested job, available PBS fields and log tails. | No operands for this episode's job; an actually supplied prior handoff can be selected through its declared receipt operand. |
| practical.job.collect | Observe the original job and validate its requested output checks. | Same target restriction as status. |
{only_additional_actual_instruction_retrieval_operations_relevant_to_this_assignment_with_their_required_operands}

Finish the assignment only on the original validated result. If the parent
requested a usable handoff, an actual submitted or running job can satisfy it
when its original execution and usable follow-up operations are verified; the
scientific computation need not have finished. If the parent requested completed
outputs, preparation or submission is insufficient: the original job must have
its successful outcome and all original output checks. Existing files alone do
not establish that this job produced them or that their contents have been
scientifically interpreted.

Verified completion immediately makes the expectation for further progress on
this assignment exactly zero. The completing action keeps its actual gain and
all earlier observations remain unchanged. The configured controller closes
the episode through its ordinary comparison; do not select another action just
to demonstrate zero gain or compose an extra completion report. Before verified
completion, the same controller governs continuation from actual observations.

Return the information the parent requested about this HPC job:

| Requested field | Type and allowed values | Exact meaning for this job and its handoff or outputs | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_original_parent_requested_field_meanings_and_constraints}

Use the existing typed JSON response for selecting an operation and updating
declared interpretation fields. Base those interpretations on information already
received; the next selected operation has no known result yet. Recorded fields
come from actual outcomes. Preserve useful partial work and specific missing or
failed results under the original allowed meanings. An available own-history
lookup supplies a needed earlier detail for this same decision and creates no
action observation. These complete TASK instructions apply on every exchange,
including after lookup or reconstruction.

STEERING

| Job requirement | Latest actual validation | Remaining limitation |
| --- | --- | --- |
{only_relevant_current_original_requirement_results}

| Current preparation context | Actual value |
| --- | --- |
| Working directory | {actual_current_cwd} |
| Environment affecting the next preparation command | {only_relevant_explicit_current_overrides} |

| Component needed by this job | Recorded location and relevant release or capability | Catalog observation and mirror comparison | Actual usability observation or unknown |
| --- | --- | --- | --- |
{only_needed_recorded_components_with_actual_observation_times_and_limits}

| Relevant attempt | Exact selected inputs | Actual outcome | Specific repair or unanswered question |
| --- | --- | --- | --- |
{only_relevant_own_command_file_context_inventory_or_submission_attempt_rows}

| Current PBS or filesystem observation | Actual value | Observation time and limit |
| --- | --- | --- |
{only_received_queue_priority_resource_filesystem_or_log_facts_needed_for_the_next_choice}

| Time quantity for this job | Measured interval or duration expectation | Statistical support or unknown |
| --- | --- | --- |
{only_actual_compatible_queue_execution_turnaround_or_prospective_duration_rows}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty |
| --- | ---: | ---: | --- | --- |
{original_saved_own_action_category_rows}

| Requested interpretation | Current value | Evidence basis or repair |
| --- | --- | --- |
{only_relevant_current_requested_interpretation_rows}

{only_if_needed_literal_received_command_output_or_log_window_with_original_path_byte_range_and_observation_time}

{only_if_present_actionable_failure_table_with_affected_operation_inputs_preserved_partial_result_and_specific_repair_fact}
```

## Fill and decision trace — outside the prompt

This template is a proposed text input, not an implemented renderer. TASK and
STEERING are built independently. TASK is included in full every call. Its
job, software, inputs, environment, constraints, validation meanings and return
contract remain the original assignment. Relevant current observations and
initially supplied facts enter only terse STEERING rows. Omit inapplicable rows
and conditional sections. Site-specific paragraphs appear for the actual
assigned site; Aurora is not silently substituted for another bound HPC site.
An absent candidate, database, measurement or setup observation stays absent or
unknown. No biological finding, annotation score or parent yield enters this
resource decision merely because the job concerns a gene.

| Source and exact selection | Prompt use and receiving decision |
| --- | --- |
| Original `ExecutionEpisodes.prepare_assignment` request, `_match_request`, `_check_parent_inputs`, practical `validate_assignment` and exact caller resource configuration | Name this software job, inputs, original argv/environment, workspace, account and permitted choices. Preserve the launch parent's selected request and allocations. Do not expose assignment/run/episode hashes or transport configuration. |
| Exact selected launch-instruction section bodies from `LaunchInstructions.materialize`, supplied by `DecisionSource.call`; actual relevant instruction operations from `Workflow.catalog` | Render substantive software and site instructions as TASK. These instructions supply ways to prepare this job, not proof of deployment, new capabilities or scientific evidence. Do not render library/section hashes or indexes as instructions. |
| `PracticalResourceEpisodes.decision_context`, `PracticalState.context/receipts/credit_view`, original `progress_requirements` and `completion_keys` | Render original validation meanings in TASK, current context and actual satisfied/missing facts in STEERING. Preserve baseline, signed losses, actual completed-action counts and unchanged credit units. A context environment change does not rewrite `requested_job.environment`. |
| `execution_inventory.validate_snapshot/reconcile_inventory`, assignment snapshot and newest selected inventory-refresh receipt | Render only components this job needs, their paths/capabilities, recorded age and semantic mirror result. Equality proves catalog agreement, not executable/database usability. No automatic per-turn refresh or hash-number dump. |
| Actual `PBSPracticalOperations` selected command, file and job outcomes | Retain exact needed operands, native return code, project paths, bounded original output and observed PBS facts. Current conditions inform reuse, repair or submission choices without replacing the assigned job or adding a hidden scheduler. |
| PBS `job_result` and exact-attempt `observe_execution` | Preserve actual queue/priority/resource/native-state fields, log offsets and observation times. Queue wait uses actual qtime/stime; requested-command wall duration comes from the exit receipt; total turnaround requires actual qtime/obittime. Only an actually supplied duration representation is rendered, with its original meaning and support. Missing fields are unknown. |
| `PracticalState.completion_proof/verify_completion`, `ExecutionEpisodes.completion_for_action`, `Workflow.controller_value` and `PracticalYieldEstimator` | Distinguish a usable-handoff endpoint from completed-output validation. The last actual action's verified proof supplies an exact-zero future estimate, retaining its real observation and prior history. A model flag or generic command cannot establish completion. |
| Existing `decision_history.yield_table`, original own controller observations and category expectations | Render signed totals, counts, expected next completion yield and actual uncertainty/unavailability. The category band is an approximate uncalibrated working-model band, not a success probability or scientific confidence. No parent history or refitting is added by presentation. |
| Original typed return contract, `DecisionSource.apply_response/finish`, `Workflow.facts`, practical receipt publication and original report validation | Full result meanings enter TASK; current interpretation values enter STEERING. The host freezes factual fields from actual recorded outcomes. No new report-composer call, unrestricted prose return, altered typed output or score transfer. |

## Concrete integration limits

1. `ExecutionEpisodes` delegates `launch_hpc` to `PracticalResourceEpisodes`.
   The actual role permits only tool actions and no children or wait action.
   Iterative setup is possible through command/file/context operations, but
   nested HPC environment episodes are not implemented by this binding. This
   template adds none. It is not evidence that all accepted HPC nesting exists.
2. Current `PracticalResourceEpisodes.decision_context` supplies whole assignment,
   configuration, receipt/progress, inventory and estimator objects; the provider
   sends `json.dumps(context)`. The detailed TASK/curt STEERING renderer and
   deterministic relevant-cell selection remain implementation work. A template
   document does not fix that path.
3. Current ordinary tool and retry/receipt arguments require machine reference
   values. Readable target selection must bind back to those existing values
   outside the model text. This review proposes no output-schema change or
   implemented alias resolver. Internal PBS attempt/submission identities remain
   essential for correctness without becoming prompt bookkeeping.
4. Configuration initially reports resource availability as unknown, and the
   supplied inventory is a recorded snapshot. There is no hidden current queue,
   filesystem, module or authentication probe. A selected command can inspect
   those conditions; a selected inventory refresh updates the recorded catalog.
   General job-specific HPC duration forecasts are not established merely by
   exposing PBS timestamps or the global estimate interface.
5. PBS native status and exact-attempt observations expose real queue/resource
   fields and log tails, but generic recursive `MonitorEpisodes` integration
   is separate. Do not claim that this resource role's status operation proves
   that missing integration.
6. A transport/remote exception in `PBSPracticalOperations._invoke` can propagate
   before `PracticalResourceEpisodes.execute` saves a finished practical receipt.
   The current connected path does not guarantee every such failure becomes a
   recorded repair row. Preserve uncertain original side effects; do not invent
   a returned failure or retry to make the template look complete.

Read: the mandatory goal, episode/time, practical completion and task/steering
documents; complete `execution_episodes.py`, `practical_resource_episodes.py`,
`practical_pbs_operations.py`, `execution_inventory.py`, `launch_instructions.py`,
`practical_execution_records.py`, `practical_execution_state.py`,
`practical_execution_credit.py`, `practical_yield.py`,
`practical_receipt_information.py`, actual Aurora instruction sections; and the
relevant complete shared call/instruction/catalog/next/apply/execute/closure,
credit, completion-context, category-yield and provider input consumers.

Only this proposed review document was added. No application code, tests, SSH,
network requests, model calls, real jobs or scientific runs were performed or
changed. The draft is ready for the user's running feedback; it is not settled
or implemented.
