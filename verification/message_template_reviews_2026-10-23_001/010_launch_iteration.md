# 010 — choose how to launch the assigned software job

```text
TASK

Launch {software_and_analysis} on {the_exact_assigned_inputs} and obtain {the_usable_execution_handoff_the_parent_needs}. The parent will use that handoff to {the_original_requested_follow_on_work}. Preserve {the_original_job_parameters_database_requirements_and_required_outputs} within {the_complete_parent_scope_constraints_and_caller_owned_allocations}.

Choose among the permitted API/service, local-compute and HPC requests below. Select an approach only where the parent left the choice open. Keep a required environment, software/database choice, input, resource allocation or storage location fixed. A different environment does not authorize changing the analysis. If an assigned request cannot be fulfilled, retain the actual limitation or failure rather than silently substituting another job.

| Permitted approach and environment | Exact job to commission | Fixed inputs, parameters and constraints | Resource child that investigates execution |
| --- | --- | --- | --- |
{one_row_per_actual_permitted_parent_supplied_request_with_its_full_relevant_job_and_constraint_meanings}

Compare the approaches before commissioning. Determine which can run this software on these inputs, what preparation is already recorded, what remains unverified, and what time or resource costs are actually known. Use the recorded workspace and allocation for that environment. A configured operation establishes that an execution path is bound; it does not establish current authentication, service availability, software readiness or queue conditions. Missing information remains unknown rather than making an environment available or unavailable by assumption.

Distinguish reusable preparation from this run's conditions. An existing environment, software installation, database release, index or prepared operation may remove repeated setup work. Check that the recorded preparation corresponds to the assigned software, database and inputs. Matching local and remote catalogs establish agreement about the recorded inventory, not present usability of its files or executables. A cached catalog whose remote read failed remains dated, qualified information. Use the actual observations returned by a resource child when judging whether preparation can be reused or needs repair. Current queue, filesystem or service conditions can change how to run the job without changing the underlying setup.

Use relevant software and resource instructions to understand how each permitted request can be carried out. The instructions selected for this job appear below in full; they describe what to do and how to interpret the possible outcomes. They do not establish that setup was performed or the resource is currently usable. When more instructions would help, use the available launch-instruction search, section-read and selection operations. Preserve the parent's selected instructions when supplying additional relevant instructions to a child. Reading instructions is optional; it is not a required stage before every commission.

{full_substantive_selected_software_and_resource_instructions_needed_to_choose_or_commission_this_job_without_library_hashes_or_tracking_envelopes}

Compare timing information only for the work and interval it describes. Keep preparation, queue wait, execution and submission-to-completion turnaround distinct. A local service-wall measurement is not an HPC queue observation. A historical successful-duration mean and observed range do not guarantee completion or establish the chance of failure. Retain the supporting sample counts, unsuccessful or unfinished measurements and unknown intervals when they affect the choice. Do not infer an unreported remaining time by subtracting elapsed time from a mean, or transfer a small experiment's duration to a different workload without a supplied model. Missing duration history does not prohibit commissioning. Timing estimates inform your choice; they do not select an environment for you.

Commission the corresponding resource child to investigate how to run the selected request: an API/service episode for its service protocol, a local-compute episode for that machine's preparation and native execution, or an HPC episode for its environment, scheduler and submission work. These children have different execution decisions. Give the child the exact selected request, its inputs and constraints, relevant software/resource instructions, explicitly supplied starting facts and the typed result needed to use its handoff. The child chooses its own preparation, execution and repair actions within that assignment. Do not perform the child's setup or submission as a hidden loop inside this launch decision.

Ask for the actual usable handoff and the declared facts needed to identify the original work, environment and handoff status. Define any requested interpretation fields with their types and allowed meanings before commissioning. Receiving a preparation receipt, a configured tool or a child that merely closed does not establish a usable execution handoff. A returned handoff must concern the original assigned request. Retain valid partial work and the exact missing result when the handoff is not yet usable.

Use the actual pending-child information to choose what to do while a child runs. Select an available wait when its requested report or event can inform your next choice. Passing time alone establishes neither progress nor failure. If a prior attempt has an uncertain submission or execution outcome, preserve that uncertainty and the original work; do not treat it as a confirmed failed attempt or commission a replacement merely because no reply has arrived. No fixed polling interval, automatic retry, cancellation rule or child sequence is prescribed.

{only_for_an_actually_permitted_Aurora_request: Keep all software, environments, databases, caches, inputs, temporary files, logs and run/output directories under /lus/flare/projects/BioReason-Aurora-Test. Charge new PBS jobs to EpiCalib. Aurora home may contain only the small /home/chian/WORKSPACE_DIRECTORY.md tracking file. Pass these constraints to the HPC child; the charging account does not change storage.}

Choose one next action from the actual available operations or child commissions:

| Choice | What it obtains or changes for this launch | Required meaningful inputs and binding limits |
| --- | --- | --- |
{actual_available_capability_read_instruction_operations_permitted_resource_child_commissions_wait_reasoning_or_repair_contracts}

Use your own action-category yields to compare further information gathering, commissioning, waiting or repair. Total yield describes completed own actions, excluding supplied starting information. Expected next yield concerns another completion of that category, with the stated uncertainty; unavailable is unknown. A child's internal actions are not your observations. Keep this launch's operational progress, scientific annotation support, monitoring information and execution-duration estimates separate.

This launch assignment is complete when an actual received and validated usable handoff for the original job is established. The handed-off computation may still be running; this endpoint does not claim completed analysis or a gene annotation. Validated launch completion immediately makes further expected credit for this assignment zero, preserving the final actual gain. The ordinary controller then closes it without another model turn or a synthetic zero-gain action. Until that endpoint is established, the configured controller governs continuation and may yield with partial or pending work.

Return exactly the information requested by your parent:

| Requested field | Type and permitted values | Complete meaning for this software job and handoff | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{every_original_parent_requested_field_with_complete_type_meanings_and_cross_field_qualifications}

Use the existing typed JSON decision response with selection and report_update. Update only declared interpretation fields, using information already received; the action now selected has no known outcome yet. Recorded handoff and completion facts come from actual outcomes. Preserve partial results and specific failures that permit repair. If an available own-history lookup is needed, request the relevant earlier own inputs or available result detail within this same pending decision; the lookup creates no completed-action observation.

STEERING

| Permitted environment | Bound way to run this job | Actual observed availability | Observation time and limitation |
| --- | --- | --- | --- |
{only_actual_bound_permitted_resource_rows_with_unknown_authentication_or_deployment_explicit}

| Reusable preparation for this job | Environment and actual location | Recorded software/database release or operation | Catalog observation and current usability limitation |
| --- | --- | --- | --- |
{only_relevant_received_inventory_components_and_their_actual_dependencies}

| Approach and exact proposed work | Measured interval | Existing duration expectation and observed range | Sample/outcome support and unknowns |
| --- | --- | --- | --- |
{only_compatible_actual_supplied_duration_rows_without_invented_queue_or_transfer_estimates}

| Own action category | Completed | Total signed yield | Expected next yield | Uncertainty or unavailable reason |
| --- | ---: | ---: | --- | --- |
{actual_own_completed_action_category_rows}

| Previous attempt or received child answer | Exact selected approach, job and relevant inputs | Actual result | Missing handoff, qualification or repair fact |
| --- | --- | --- | --- |
{only_next_choice_relevant_own_attempts_or_originally_requested_admitted_child_fields}

| Pending execution child | Assigned work | Latest received progress and observation time | Available wait information |
| --- | --- | --- | --- |
{only_relevant_pending_commissions_and_actual_received_progress}

| Requested interpretation | Current value | Actual basis or required repair |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_present_specific_failed_action_or_delivery_table_with_affected_inputs_and_preserved_partial_work}
```

## Construction and decision trace — outside the prompt

This is the `launch` episode's own next-decision boundary. Its decision is which
permitted concrete request to commission, which useful information to obtain,
or what received/pending result requires waiting or repair. The assignment and
selected instruction contents define the complete recurring TASK. Recorded
inventory, capabilities, actual outcomes, forecasts, returned fields and own
yield history fill the separately constructed terse STEERING. Emit the complete
TASK after every lookup or reconstruction; omit irrelevant rows, inapplicable
tables and representation/resource paragraphs. Do not shorten instructions with
the steering budget.

| Filled part | Authoritative producer and selection | Receiving use |
| --- | --- | --- |
| Original job and permitted requests | `ExecutionEpisodes._launch`, `_validate_request`, `_permitted`, `allowed_children`, and original parent goal, scope, constraints and typed contract. `prepare_assignment` / `_match_request` preserve exact request equality apart from allowed additive launch-instruction selections. | Compare only actual permitted API/local/HPC requests. Keep original software work, resource constraints, allocations and immutable inputs. Do not fabricate a resource or select a replacement analysis. |
| Actual capabilities and starting inventory | `ExecutionEpisodes.initial_decision_context` → `_resource_information` / `capabilities`; caller-owned `ExecutionServiceFactory.resources` and `initial_information`; shared binding initial-context hook in `DecisionSource.call`. | Supply configuration and already recorded inventory before the choice. Current capability availability is literally `unknown` with caller-configuration provenance; this is not an authentication/deployment probe. |
| Inventory meaning and reuse | Complete `execution_inventory.validate_component/catalog/snapshot` and `reconcile_inventory`. Components name preparations and actual bound operation contracts; comparison and timestamps qualify the catalog. | Project only preparations relevant to this assigned software/job. Matched catalog digests do not prove current file usability. Unavailable remote reads preserve dated cache information. Inventory cannot add callable tools or choose work. |
| Detailed software/resource guidance | `LaunchInstructions.materialize` plus original assignment's selected sections; global search/entry/read/select operations from `Workflow.catalog`. `retain_inherited_selection` preserves parent selections. | Render exact substantive section text without library identity/hash wrappers. Show actual instruction-operation meanings. Initial facts do not move into TASK merely because instructions mention an environment. |
| Timing | `DecisionSource.call` captures bound execution expectations and `ResourceToolEstimator.estimate_context`; `_project` preserves interval, sample/outcome support and unknowns. | Render only actual compatible prospective rows and their meanings. No forecast is invented from resource configuration, database size or a different workload. Queue wait, program runtime and total turnaround remain distinct. |
| Own attempts and received children | Saved own selected actions/outcomes and only originally requested admitted direct-child forms; `method_loop._model_inputs` verifies parent-admitted reports. Runtime child preparation preserves the exact selected request. | Distinguish pending, confirmed failure, unknown submission and actual usable handoff. No parent history, child-private action sequence, arbitrary source content or recursive receipt closure is a display selection. |
| Own yields | `decision_history.yield_table`, original observations and completion identities. Its category fit is conditional on that category completing again and is an approximate uncalibrated working-model band. | Show signed totals, actual completed counts and existing availability/uncertainty. This presentation changes no controller, score, sample or closed observation. |
| Operational facts and endpoint | `ExecutionEpisodes._received`, `_context_target`, `facts`, `project_credit`, `_proof_for_action`, `completion_for_action`, and `verify_completion`. Qualified handoff counts use original received information as baseline. | Launch completion requires a usable handoff matching the original request. Setup-only or unrelated handoffs cannot complete it. Native job completion is a separate fact. |
| Credit and continuation | `Workflow.source_credit_view` selects the role's operational binding. Outcome recording precedes received-information projection. `controller_value` supplies actual completion evidence; `ExecutionContextController` freezes it. `PracticalYieldEstimator` verifies the endpoint, preserves history and returns exact-zero future credit; `YieldController` uses its ordinary comparison. | One own completed action produces one observation; child internal work is not flattened into launch history. Actual final gain survives immediate endpoint closure. |
| Parent return | Original typed contract meanings plus existing `report_values`; `DecisionSource.finish` → `Workflow.facts` / `ExecutionEpisodes.facts` → `form_with_facts` → original-contract admission. | Complete field meanings stay in TASK; current interpretation values stay in STEERING. Recorded handoff/completion fields are host-filled. No report-composer model call or new universal form. |

## Concrete integration limits

The current provider still sends `json.dumps(context)` as model input, and the
runtime supplies tracking envelopes, assignment objects and inventories rather
than this designed text. A deterministic text renderer and readable operand
binding remain implementation work; existing typed response fields and parent
forms must remain unchanged. Host IDs, digests, revisions and recovery records
stay internal. A database/software release remains visible only when it affects
the actual requested work, rather than as transport version metadata.

The top-level launch catalog's own operation is `execution.capabilities`, which
returns already recorded initial information; it performs no new discovery or
inventory refresh. Actual local/PBS preparation and inventory refresh belong to
the selected resource child. The prompt does not invent a top-level refresh,
SSH, queue-probe, submit, monitor-child or result-acquisition capability.

Existing duration machinery can supply caller-bound prospective execution
classes. Reading `initial_decision_context` alone does not derive compatible
API/local/HPC duration or queue forecasts for every request. Where no actual
matching estimate is supplied, the table states unknown or is omitted; this
draft does not claim that generic prechoice timing coverage is implemented.

Current receiver-selection/receipt code can follow existing inherited reference
sets. The proposed renderer must not use that closure as permission to expose
unrequested linked records or inherited source contents. This draft does not
claim the separate removal of that mechanism, SQLite, or initial record seeding
is complete.

Read AGENTS.md, GOAL.md, the complete episode/time-estimation records, practical
execution document and original additive contract, and task/steering/directness
requirements. Read complete `execution_episodes.py`, `execution_inventory.py`
and `launch_instructions.py`; the relevant complete runtime call/exchange,
next-decision, action-selection, execution, credit, completion and closure
functions; service/initial-context wiring; forecast projection; category-yield
construction; typed model-input selection; provider serialization; and the
practical estimator/controller path. This file is a prompt proposal for the
user's running feedback. No application code, tests, network requests, model
calls, execution bindings or scientific runs were changed or performed.
