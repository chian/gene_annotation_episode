# 011 — establish the assigned HMMER service handoff

```text
TASK

Establish a usable monitoring and result-retrieval handoff for the assigned {phmmer_or_hmmscan} search of {protein_name_and_organism} against {assigned_database} through EBI HMMER. Use the original requested search and any submission already established for it. The parent needs {exact_requested_handoff_and_its_intended_use}.

Search input: {assigned_protein_or_region_in_biological_terms}.
Search settings: {assigned_algorithm_database_parameters_and_result_page_size_with_their_meanings}.
Keep within: {complete_parent_scientific_scope_and_binding_resource_constraints}.

Carry out this search through the assigned service. Preserve its protein input, algorithm, database, parameters and constraints. Do not substitute another database, sequence, service, local run or HPC run. This binding runs one protein query with phmmer or hmmscan; documentation for another HMMER algorithm does not make that algorithm callable. The parent decides whether different work or another execution approach should be commissioned.

{Complete relevant software/service instructions explicitly supplied for this assignment, expressed as direct instructions for preparing and handing off this search. Include actual service restrictions and meaningful protocol requirements; exclude implementation commentary, library identities and unrelated resource manuals.}

Decide which next operation can establish what is missing from this search's handoff. Use the received preparation, submission and status facts below. Existing preparation can be reused for this same input and request; a saved description alone does not establish a live service or an accepted search. A fresh service response establishes only what that response actually reports at its observation time. When the requested database's availability, release or service restriction matters, examine actual supplied information or select the database-information operation. Missing or old information stays qualified; it does not require a preliminary request on every turn.

Distinguish instructions, database metadata, prepared input, accepted submission, observed execution and validated handoff. Reading a manual does not prepare or submit the search. Preparing the protein query freezes its actual sequence and submitted FASTA without contacting the service. Database metadata describes the databases the service reports; it does not establish acceptance of this particular search. A submission response can establish the original remote job, while a later status response can establish its observed state. Reuse these actual results instead of repeating unchanged work. The submit operation can prepare its assigned query itself; a separate prepare operation is useful when its result informs your choice, not a compulsory stage.

Interpret submission failures according to what is actually known. A confirmed local preflight failure, a response that could not be parsed, an unknown submission outcome and an identified remote job are different facts. A failed request or lost reply does not establish that the service created no job. Keep the original submission and its uncertainty. Never submit a replacement to resolve that uncertainty. When the original remote job is known, selected status or handoff checks address that same job. This binding exposes no operation for editing the request, abandoning its identity or retrying a different submission. Preserve the diagnostic and partial results so the parent can address work that requires a changed assignment.

Use a status response to distinguish a search that is submitted, running, completed, failed or unknown. A failed observation is not proof that the search failed. A repeated unchanged state is not new progress. Keep the observation time and any material provider qualification. Service configuration, a retained job identifier and a running state do not by themselves establish productive throughput or a completion fraction. Report such measurements only when they were actually returned and requested; otherwise leave them unknown.

Choose among these actual bounded operations. Each takes empty arguments and uses this assignment's fixed input and search settings:

| Operation | What it does for this search | Important limit |
| --- | --- | --- |
| api.hmmer.databases | Obtain one current service database response. | Does not select a database, prepare a query or submit a job. |
| api.hmmer.prepare | Prepare and retain the exact assigned protein query and request. | Performs no HTTP request; preparation alone is not the handoff. |
| api.hmmer.submit | Submit the original assigned request once, retaining its actual response. | An existing or uncertain original submission is never replaced by another POST. |
| api.hmmer.status | Obtain one status response for the original submitted search. | Requires the original remote job to be known; does not validate the handoff by itself. |
| api.hmmer.check_handoff | Obtain one status response and validate that the original search can be handed off for monitoring and results. | A submitted, running or completed original search can supply this endpoint; a failed or unknown search cannot. |

{Only relevant actually available instruction lookup operations, with readable names, complete meaningful operands and limits. Their results supply instructions, not service observations or new capabilities.}

The assignment ends when the actual handoff check validates the original search and the requested handoff is recorded. The physical search can still be submitted or running. Obtaining a submission response alone is not this validation; waiting for all search results is not required to establish this handoff. The separate results episode acquires the parent's selected result page, and the scientific parent interprets those results. You have no result-page acquisition operation or child branch in this role. Do not add a private polling loop, fixed request cadence or mandatory order of operations.

Compare further useful checks, preparation and instruction examination using your own action-category yields and the facts still missing for this handoff. Total yield describes completed own actions. Expected next yield concerns another completion of that category, with its stated uncertainty; an unavailable estimate is unknown. These are operational gains, not annotation support or scientific confidence. Compatible duration information can inform a choice, but HTTP response time, service execution time, queue wait and total turnaround have different meanings. Do not infer an unmeasured interval or remaining duration from a running state.

The configured controller governs continuation. When the original handoff is validated, the runtime immediately sets expected future credit for this assignment to exact zero while preserving the final actual gain and earlier observations. No extra zero-gain action, final polling turn or model-written completion declaration is needed. Yielding with a partial result or failure is different from completing the handoff.

Return exactly the information requested by the parent:

| Requested field | Type and allowed values | Exact meaning for this search and its handoff | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{all_original_parent_requested_fields_with_complete_constraints_meanings_and_necessary_relationships}

Keep these meanings fixed. Use the existing typed JSON response for one available tool selection and the declared interpretation updates. Base an interpretation on information already received; the tool you now select has no known result yet. Recorded handoff and completion fields come from the actual validated outcomes. Preserve useful partial work, a failed observation and an uncertain submission under the parent's declared meanings. The parent-supplied initial interpretation is a starting value, not a new judgment by you.

If an available own-history lookup is needed to choose the next operation, use its declared request_context fields: {readable_existing_lookup_fields_and_allowed_values}. It supplies only the prior detail that lookup actually supports, continues this same decision and creates no completed-action observation. The host executes the selected operation. Include these complete TASK instructions on every decision exchange, including after a lookup or reconstruction.

STEERING

| Assigned search: preparation or submission fact | Actual received value | Material limit or uncertainty |
| --- | --- | --- |
{only_relevant_supplied_or_received_query_preparation_and_original_submission_facts}

| Database or service fact affecting this search | Actual reported value or restriction | Observed at | Qualification |
| --- | --- | --- | --- |
{only_relevant_supplied_or_received_service_and_requested_database_facts}

| Original search | Latest observed state | Observed at | Reported progress or failure |
| --- | --- | --- | --- |
{only_the_assigned_search_and_actually_received_status_facts_or_explicit_unknown}

| Relevant own attempt | Exact operation and request details that distinguish it | Actual outcome | Repair-relevant fact |
| --- | --- | --- | --- |
{only_next_choice_relevant_attempts_with_actual_outcomes_and_qualifications}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty / unavailable reason |
| --- | ---: | ---: | --- | --- |
{original_saved_own_category_rows}

| Requested interpretation | Current value | Actual basis or limitation |
| --- | --- | --- |
{current_requested_interpretation_values}

{only_if_compatible_duration_information_affects_the_next_choice:
| Proposed operation | Expected duration and measured interval | Statistical support / unknowns |
| --- | --- | --- |
{actual_compatible_estimates_with_units_and_interval_meaning}
}

{only_if_actual_failure_or_return_feedback_needs_attention:
| Failed operation or returned field | Recorded failure and affected input | Preserved partial result | Submission or access uncertainty |
| --- | --- | --- | --- |
{actual_actionable_failure_rows}
}
```

## Fill and boundary trace — outside the model prompt

Braced instructions are deterministic construction positions, not literal text
or raw objects sent to the model. Emit the detailed TASK on every call. Build
STEERING separately from explicitly supplied or actually received facts, with
curt factual rows only. Omit irrelevant rows and inapplicable tables. A missing
datum remains unknown when it affects the choice. No runtime identity, hash,
revision, session frame, full request dump or private history is rendered.

| Fill or decision | Actual producer and selection | Receiving use |
| --- | --- | --- |
| Protein, algorithm, database, settings and constraints | Original validated `api_execution_assignment_v1`, selected and checked by `ExecutionEpisodes.prepare_assignment`, `_match_request`, `_versions` and `HMMERAPIExecution._assignment/_constraints`. Resolve a biological name only from explicit supplied target metadata. | Identify the exact search whose handoff must be established. Do not manufacture a gene label, infer a sequence from a citation, expose original record IDs or expand parent receipt ancestry into facts. |
| Handoff purpose and requested fields | Original child goal and parent `ReportContract.decision/schema`; declared field meanings, constrained values and fact ownership. | Distinguish this usable-handoff assignment from result acquisition and scientific annotation. Current API assignment supports only `endpoint=usable_handoff`; do not invent a configurable completed-output endpoint for this role. |
| Full service instructions | Exact sections materialized from the assignment's retained `launch_instructions`; relevant actual callable meanings from the bound catalog. | Supply substantive preparation/protocol/recovery guidance about this search. Titles and library identifiers cannot replace instruction bodies. Omit historical implementation commentary and unrelated resource sections from the model-facing instruction text. |
| Available operations | Complete `HMMERAPIExecution.catalog/execute`; `ExecutionEpisodes.permitted_common_actions` permits only tool actions for `launch_api`; shared `Workflow.catalog` also exposes actual instruction operations. | Render the five fixed-assignment operations and only useful actual instruction capabilities. No generic shell, environment setup, editable request, result-page acquisition, child, wait, reasoning-commit, cancellation or retry capability is fabricated. |
| Preparation and submission facts | `HMMERAPIExecution.decision_context`: actual saved preparation and original job description; relevant exact selected outcomes. | Show only preparation availability, protein length when relevant, original submission outcome/addressability and current qualification. Whole FASTA, request hashes and local/remote job identifiers do not help select these zero-argument operations. Their exact identities remain durable host operands. |
| Database and availability facts | Explicit supplied initial information, or the recorded outcome of this episode's `api.hmmer.databases`/other available instruction examinations. `ExecutionEpisodes.initial_decision_context` supplies already recorded caller information and capability configuration. | Include only the assigned database and restrictions that change the next choice. Configuration availability is `unknown`, not proof of a live endpoint. A database response is not an input-limit, authorization or search-acceptance claim unless it actually reports that fact. Never fetch data during prompt construction. |
| Original status | This episode's actual status/check outcomes, including `_native_status`'s validated present identities, mapped state, native value and source observation time. | Distinguish failure of observation from failure of the search. Status views expose no guaranteed throughput, completion fraction, queue estimate or logs; do not synthesize them. Preserve observations as dated facts. |
| Exact attempts and own yields | Own selected `runtime_actions` and original outcomes; `decision_history.category_for/yield_table` joins saved own completed-action observations. | Show exact operation/outcome pairs needed to avoid repetition. Category uses actual `tool/<operation>` rather than the biological purpose of the search. Keep original signed totals, existing conditional estimate/band and unavailable status. Do not import parent or monitoring-episode histories. |
| Duration | Only an actually supplied compatible `resource_tool_estimates` or other declared original duration snapshot, with its measured interval and support. | Omit the optional table when no relevant producer supplies it. This API implementation does not itself publish a queue/runtime/turnaround forecast or a duration-transfer law. HTTP request timestamps are not an execution-duration measurement. |
| Completion and return | `_completion` verifies a saved successful handoff-check result and original target. `completion_for_action` → `Workflow.controller_value` → captured original completed-action context → `PracticalYieldEstimator`/verifier → ordinary controller. `DecisionSource.finish` freezes `form_with_facts`; `ExecutionEpisodes.facts` delegates actual API handoff/completion fields; original-form validation and parent admission retain field meanings. | Preserve the final actual gain and closed history while giving exact-zero future expectation. Recorded handoff facts require no report-composer model call. The later monitor observes the original target independently and does not reopen this launch. |
| Repair and current return values | Exact `_failure`/argument feedback, `report_values/report_basis`, and actual common return validation feedback. | Render the affected operation or requested field, useful partial outcome, submission phase/outcome, known addressability and any reported service delay that matters. A reported delay is not an automatic wait or a new wait capability. |

## Concrete implementation boundaries

1. The current provider serializes the context with `json.dumps(context)`.
   `DecisionSource.next/call/exchange_decision` supplies large structured state
   frames and may retain native chat. A deterministic TASK/STEERING text builder
   and complete-TASK redispatch are still needed; this review does not implement
   either. Existing typed JSON output and parent forms are unchanged.
2. `launch_api` currently binds HMMER specifically. There is no generic API
   installer, arbitrary HTTP operation, environment setup or editable request in
   this role. Reuse means the saved exact preparation/original job, plus actual
   retained service information. Do not describe a reusable prepared-service
   catalog or automatic compatibility check that this path lacks.
3. All five API actions have empty operands. Native request and job identities
   belong in host validation; they need not appear in the decision text. Parent
   reference fields still require a reviewed readable presentation binding to
   their existing typed values. This template does not introduce aliases or
   change the output schema.
4. API operational credit counts received unique qualified handoffs (and, only
   in the separate results role, acquired canonical result records) using the
   caller's existing units. Preparation, metadata and repeated status do not
   receive invented per-step bonuses. Current `_failure` returns `status=failed`;
   shared runtime retains its diagnostics without a completed-action observation.
   This differs from a completed practical command with a nonzero exit code;
   neither behavior is changed or relabeled by this prompt.
5. Common catalog code can expose irrelevant scientific inspection and knowledge
   operations. Only capabilities actually useful and permitted for this assigned
   API search belong in the proposed choice table. This review does not claim
   the catalog is already filtered or remove SQLite/record-inheritance code.
6. Exact prior outcome rows must come from this receiver's saved outcomes.
   Existing `request_context` detail retrieves selected inputs, not arbitrary old
   response bodies. A fingerprint is not a restored service response. Supplying
   older relevant results without a model summary remains shared presentation
   work; the template promises only what the actual lookup supports.

Read the mandatory project goal, full episode/time design records, practical
endpoint document and original additive contract, and task/steering/directness
requirements. Inspected complete current `api_execution.py`,
`execution_episodes.py`, `execution_contracts.py`, `launch_instructions.py` and
`practical_yield.py`; relevant complete shared decision assembly/exchange/action/
closure, credit/controller/fact consumers, HMMER client and remote-identity/job
description paths; original yield-category producer; provider text dispatch; and
the three API launch-instruction sections. These are source inspections, not
deployment verification. No application edits, tests, network calls, model calls,
job submissions, process changes or scientific runs were performed. Only this
draft was added, for the user's running feedback before settlement or coding.
