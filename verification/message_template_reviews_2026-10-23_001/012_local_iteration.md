# 012 — run the assigned software on the local machine

```text
TASK

Run {assigned_software_and_job} on {the_selected_local_machine} with
{the_original_inputs_database_and_job_options}. Produce
{the_parent's_exact_requested_handoff_or_outputs}, within
{the_assigned_workspace_and_caller_owned_resource_limits}. Keep the original
job, its explicit environment and its requested endpoint fixed. The parent has
already selected local execution; do not substitute an API or HPC run.

The parent needs {the_exact_use_of_this_execution_result}. Work in
{absolute_assigned_workspace}; keep workflow-created run files, environments,
scripts, temporary files and logs there. Use existing software or data only
within the assigned access and storage constraints. Respect
{the_actual_memory_scratch_allocation_and_other_binding_limits}. No additional
wall-time budget, action limit or retry quota is imposed by this prompt.

The requested job is {the_original_argv_rendered_with_meaningful_input_paths_and_options}.
Its required environment is {only_job_environment_requirements_relevant_to_preparation_or_diagnosis}.
Starting this job uses the original bound command and explicit job environment;
changing your diagnostic-command environment does not replace them.

{Full selected software and local-resource instructions needed to prepare,
reuse, run or repair this particular job. State the actual executable, input
and database requirements, meaningful checks and failure interpretations.
Instructions describe how to work; they do not establish that this installation
or database is currently usable.}

Determine what preparation this job actually needs before choosing another
setup action. The supplied inventory describes environments, software,
databases, indexes and prepared operations that were recorded at a stated time.
A matching catalog means the recorded descriptions agree; it does not prove
that an executable runs, a database is readable or an index suits these inputs.
Use the received observations to decide whether to reuse an existing component,
examine a particular uncertainty, repair a failed component or prepare something
missing. Do not rebuild usable preparation merely because this episode is new.
A missing or inaccessible inventory leaves preparation unknown; it does not
prove that the software or data are absent.

Separate a broken setup from a poor choice for this run. A missing executable,
unreadable database, incompatible index or failed import can require repair.
Current loading, I/O, resource use or slow progress may instead call for a
diagnostic observation or an adjustment that the assignment permits. Use actual
command results and logs to distinguish these cases. Keep fixed job options,
data and caller allocations unchanged. If the needed change is outside your
assignment, return the specific failure or missing capability in the parent's
declared form rather than silently running different work. Do not infer a stall
from process liveness or elapsed time alone.

Choose a preparation command, file operation, working-context change or job
operation because it resolves a specific obstacle to {the_requested_job_result}.
Use exact prior commands, inputs and outcomes below to avoid repeating work
without a reason. A command that returned nonzero has an actual unsuccessful
outcome; examine its reported error and retained log locations before choosing
a repair. A malformed request or an operation that never executed is feedback,
not evidence that a diagnostic or job ran.

Set the working directory and persistent environment explicitly when later
actions need them. A cd or export inside one subprocess does not change the
next action. practical.context.set stores the directory and environment for
subsequent actions. A diagnostic command merges that context's environment with
its selected overrides. The requested job retains its own original explicit
environment and uses the current working directory.

Keep preparation commands separate from starting the requested job. Use
practical.job.start for the original computation. If it has already started,
observe that same execution rather than launch another copy. An uncertain
execution remains uncertain until reconciled against its original execution.
An explicit retry is permitted only for the exact execution already confirmed
failed; name that failed execution through the declared retry operand. A replay
of completed work retains the recorded outcome rather than executing it again.

Examine only the job information you need for this assignment. Status and
collection return actual native state, return code, path checks and selected
stdout/stderr tails. Use the reported offsets and log paths to recognize what
those tails omit; select a bounded file read when another portion matters.
Liveness does not establish productive execution. Distinguish an unavailable
observation from a failed job, an existing output path from a verified file
format, and job execution from the scientific interpretation of its results.

Finish exactly the practical job the parent requested:

{Endpoint-specific instruction, render exactly the assigned alternative:
- Usable handoff: establish an actual usable handoff for the original submitted,
  running or successfully completed job, with its bound status/result operations
  and all other original completion conditions satisfied. The computation may
  still be running when this launch assignment is complete.
- Completed outputs: establish successful completion of the original job and
  the original requested output-file checks, plus all other original completion
  conditions. State only what those checks establish; file presence alone does
  not establish content correctness or a biological conclusion.}

| Required condition for {assigned_job} | Actual check and its meaning | Credit for the validated condition | Required for this assignment's completion |
| --- | --- | ---: | --- |
{all_original_requirement_meanings_with_their_caller_supplied_units_and_completion_membership}

These are conditions to establish or preserve, not an ordered setup procedure.
Already established preparation is starting information. Reobserving an
unchanged condition earns no new progress; an observed loss retains its signed
effect. Each completed own action supplies its ordinary observation, including
actions with zero gain. Do not invent a per-command, per-file or scientific
bonus.

Only the actual checks of the original requested job can establish completion.
Do not declare completion yourself or replace it with a successful setup command.
When the recorded checks establish the requested endpoint, future expected
credit for this assignment becomes exactly zero immediately. The completing
action keeps its actual gain and the existing controller closes normally;
no extra zero-gain action, confirmation command or model-written completion is
needed. Before that endpoint, the configured controller governs continuation.
Yielding partial work is not proof that the requested job completed.

Select one available operation:

| Operation | When it helps run this job | Required inputs and important limits |
| --- | --- | --- |
| practical.inspect | Check the assignment's declared file conditions now. | No operands; it checks the declared paths, not arbitrary installed software or database contents. |
| practical.inventory.refresh | Read the chosen preparation catalog and compare it with the retained mirror. | path inside the assigned workspace; catalog equality is separate from component usability. |
| practical.context.set | Set the directory and environment for subsequent actions. | Absolute cwd inside the workspace and the explicit environment map; the directory must exist. |
| practical.directory.create | Create a directory needed for this job. | Absolute path inside the workspace. |
| practical.file.write | Write a needed script, configuration or input as the selected UTF-8 text. | Absolute workspace path and exact text; preserve the original job and inputs. |
| practical.file.read | Examine a selected part of a file or log. | Workspace path, nonnegative byte offset and positive byte limit; returned text is that window, not the whole file. |
| practical.command.run | Run one selected preparation or diagnostic command. | argv and explicit environment overrides; uses the current cwd and preserves actual nonzero outcomes and log locations. |
| practical.job.start | Start the original requested computation or explicitly retry its confirmed failed execution. | No operands for the original start; the declared failed-execution operand for a permitted retry. It cannot replace active or uncertain work. |
| practical.job.status | Observe the original job and available log/path facts. | No operands for your job; the declared received-handoff operand only when observing an explicitly supplied matching execution. |
| practical.job.collect | Observe the original job outcome and assess the declared output conditions. | Same permitted target forms as status; it does not parse or interpret output contents. |
{only_other_actually_available_instruction_or_inspection_operations_relevant_to_this_job_with_exact_operand_meanings}

This local execution episode has no child branches or explicit wait action in
its current binding. A selected command or job observation is an ordinary tool
action. Do not hide further model decisions in a command, impose a polling
cadence or add another execution workflow. Use duration information only for
the interval and configuration it actually describes. A command's receipt
duration is not automatically native-program runtime, queue time or a forecast
for a different workload.

Return the parent's exact requested information about {assigned_job}:

| Requested field | Type and allowed values | Exact handoff, output, failure or interpretation meaning | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_original_parent_return_field_meanings_and_meaningful_relationships}

Use the existing typed JSON response for one action selection and report_update.
Update only declared interpretation fields, using information already received;
the next selected action has no known outcome yet. Recorded fields come from
the actual command/job outcomes and checks. Preserve valid partial work and the
specific failed command, path or missing result needed for repair. Returning
a usable execution handoff does not establish the gene's biological function.

If a supported own-history lookup is needed to choose the command, use the
declared request_context exchange and finish this same decision after the
reply. Request only detail that lookup actually supplies. The lookup creates
no completed action or yield observation. Keep these complete TASK instructions
on every iteration and after a lookup or reconstruction.

STEERING

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty / unavailable reason |
| --- | ---: | ---: | --- | --- |
{actual_saved_own_category_rows_conditional_on_another_completion}

| Preparation relevant to {assigned_job} | Recorded location and relevant release or compatibility | Latest actual usability observation | Observation time / limitation |
| --- | --- | --- | --- |
{only_relevant_supplied_or_received_component_rows_no_component_ids_or_hashes}

| Catalog observation | Comparison with retained catalog | What remains unverified |
| --- | --- | --- |
{actual_catalog_observation_time_and_available_or_cached_status_comparison_and_limits}

| Working directory or relevant environment setting | Current value | Effect on the next selected command |
| --- | --- | --- |
{only_needed_actual_context_values_not_full_environment_dump}

| Requirement for {assigned_job} | Latest actual check | Observed result | Missing or failed condition |
| --- | --- | --- | --- |
{only_next_decision_relevant_original_requirement_statuses}

| Relevant previous command or operation | Exact discriminating inputs | Actual outcome | Error or remaining obstacle |
| --- | --- | --- | --- |
{only_needed_own_attempts_with_native_results_and_preserved_partial_work}

| Original job | Latest observed native state and return code | Useful log or output observation | Observation time and limitation |
| --- | --- | --- | --- |
{only_received_current_job_facts_with_semantic_target_label_and_no_native_handle_dump}

| Work being considered | Duration estimate or measured interval | Units and statistical support / unknowns |
| --- | --- | --- |
{only_compatible_actually_available_duration_information_needed_for_the_choice}

| Requested interpretation | Current value | Evidence or specific repair information |
| --- | --- | --- |
{current_requested_interpretation_values_and_actionable_feedback_only}

{only_needed_literal_received_log_or_file_window_with_actual_path_offset_and_observation_time}
```

## Fill and receiving-decision trace — outside the prompt

This is one proposed local internal-decision template. It preserves detailed
recurring TASK instructions and separately selects curt factual STEERING. All
braced sections expand to actual text or table rows; instructional alternatives
and these construction notes are not sent literally. Render only the assigned
endpoint, relevant representation/operation instructions and next-choice facts.
Include complete TASK on every call. Omit inapplicable STEERING tables. Unknown
information remains unknown. The user must see this draft for running feedback
before it is treated as settled or coded.

| Prompt content | Actual producer and selection | Decision enabled / limits |
| --- | --- | --- |
| Job, local resource, workspace, constraints and endpoint | Parent's concrete local request through `ExecutionEpisodes._match_request`, `_validate_request`, `prepare_assignment` and `_check_parent_inputs`; `ASSIGNMENT_SCHEMA` and `validate_assignment`. | Decide how to run this original job locally. Exact argv/job environment and caller-owned allocation stay fixed. The choosing launch parent, not this child, owns API/local/HPC choice. Render only environment values needed for this decision; keep unrelated or sensitive configuration outside the prompt. |
| Software/resource instructions | Actual selected `launch_instructions` sections materialized for a new call by `DecisionSource.call`; inherited selections retain original instructions. | Explain concrete preparation and failure repair for the assigned software. They are neither inventory nor observed usability. Source/reference/hashing envelopes remain internal. |
| Reuse and current preparation | Original assignment snapshot, latest own completed `practical.inventory.refresh` outcome and explicitly supplied observations; `ExecutionEpisodes.initial_decision_context` / `PracticalResourceEpisodes.decision_context`; `execution_inventory` validation/reconciliation. | Distinguish recorded presence, catalog agreement, dated/unavailable inventory and actual usable installation. Equality hashes stay internal; meaningful catalog-comparison outcomes and observation times are rendered. Refresh is selected work, never implicit context-side discovery. |
| Working directory and environment | `PracticalState.context`; actual `practical.context.set` transition and `LocalPracticalOperations._execute`. | Choose the next command correctly. Diagnostic commands merge context plus selected overrides. Requested-job start uses original job environment; context cannot silently replace it. |
| Progress and completion conditions | Original `progress_requirements`, caller credit values, `completion_keys` and endpoint; `assess_validations` and `project_practical_credit`. | See what actual conditions matter, without command-count bonuses or inventing requirements. Initially satisfied facts form the baseline; missing facts in unrelated outcomes are not new negative observations. Each meaningful required condition gets a readable label mapped internally to its original key. |
| Attempt/result rows and log windows | This episode's own saved selected inputs and actual practical receipts. `_execute` retains command exit status, job facts, path checks and native log tails; selected file reads retain exact byte windows. | Identify a specific repair or useful next diagnostic without importing another episode's private work. A log tail is not complete log coverage. Literal command arguments, paths and byte coordinates remain where needed; tracking identities do not. |
| Own category yields | `decision_history.category_for` / `yield_table`, using original own completed-action marginal gains in completion order. | Compare operations using saved signed totals and the existing conditional next-category expectation/uncertainty. This is presentation, not a replacement controller, completion probability or new score. |
| Actual job target | Original own execution or an expressly supplied, validated matching handoff; `PracticalResourceEpisodes._received_target`, selected `job.status` / `job.collect`, `LocalPracticalOperations`. | Observe the exact job without opening another episode's controller or substituting a newer attempt. Meaningful target labels resolve internally to original references. An execution identifier is an operand when genuinely needed for retry; the renderer must preserve that targeting through the existing typed contract without a host-ID dump. |
| Completion and next expectation | `PracticalState._completion` / `verify_completion` → `ExecutionEpisodes.completion_for_action` → `Workflow.controller_value` → `PracticalYieldEstimator`, installed by `Workflow.controller`. | Verified endpoint makes expected future gain exact zero with the final actual gain/history intact. Native job completion and usable handoff are different endpoints; closure from yield alone is not completion. No model/composer turn supplies the proof. |
| Requested return | Original typed form and requested use; `DecisionSource.apply_response`, `finish`, `Workflow.facts`, practical/execution `facts` and `validate_report`. | Field meanings stay in TASK; current interpretation values and repair feedback stay in STEERING. The host freezes facts from actual outcomes, without another reporting call. Output JSON and parent forms remain unchanged. |

## Concrete integration limits

1. The current provider still sends `json.dumps(context)` and continuing native
   chat frames. There is no local-specific TASK/STEERING text renderer. Current
   practical decision context includes complete assignments, inventory,
   configuration, proof and binding objects; this proposal selects their
   decision-relevant fields rather than claiming that wiring is corrected.
2. The local role exposes the ten practical operations above and shared
   instruction/inspection operations actually admitted by the runtime. It has
   no child or explicit wait choice in this binding. It does not supply an
   operation to change the original argv, job environment, allocation or
   endpoint. Required unsupported changes must remain a returned limitation.
3. Current output completion checks establish successful exact job execution
   plus declared file presence and other original conditions. They do not parse
   output formats, assess biological validity or verify that current file bytes
   belong to one immutable producing attempt. Additional checks cannot be
   silently invented by this template. Generic `practical.command.run` cannot
   self-declare the requested computation complete.
4. Generic practical receipts retain action timestamps and native observations;
   they do not by themselves provide universal prospective duration forecasts
   or export every command as a typed duration-learning sample. Show only actual
   compatible estimates/measurements and their interval meanings. No queue-time
   claim or workload extrapolation is introduced for local work.
5. The current own-attempt detail lookup retrieves selected inputs, not arbitrary
   previous result bodies or missing log passages. Relevant older results must
   come from this receiver's actual saved outcomes; presentation and readable
   reference resolution remain shared integration work. A lookup must not be
   described as recovering information it cannot return.

Read the required goal, episode/time design records, practical addendum and
original contract, and task/steering/directness instructions. Inspected complete
practical resource binding, local operation implementation, practical
records/validation/state/credit/estimator, receipt-information and inventory
modules, launch-instruction materialization, and relevant complete runtime
instruction/catalog/action-schema/next-decision/credit/controller/fact/closure
functions and provider dispatch. The execution-family local delegation and
handoff consumers were traced as well. This draft changes only this review
document. No application edits, tests, network requests, model calls, native jobs
or run-state changes were performed.
