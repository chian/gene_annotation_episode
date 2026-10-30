# Proposed API iteration text for the user's review

This preserves the detailed recurring TASK in 011 revision 002 and makes its
inputs and lookup/reconstruction behavior concrete. Braces below are host-filled
text/template slots, not instructions to a model to invent their contents. The
selected service's full substantive instructions and concrete operation rows
are expanded on every call. Empty optional steering tables are omitted. Missing
information material to a choice is stated explicitly.

```text
TASK

Run {the_assigned_analysis_search_or_data_query} through {the_selected_service} using {the_supplied_sequences_selected_file_contents_snippets_or_named_subjects}. Return {the_specific_verified_response_or_monitoring_and_result_retrieval_information_requested_by_the_parent}, so the parent can {the_exact_requested_use}.

Keep the following work fixed:

| Assigned input or requirement | Exact value | Meaning and constraint for this work |
| --- | --- | --- |
{complete_original_inputs_request_settings_database_or_collection_output_requirements_and_binding_constraints}

{supplied_sequence_or_selected_input_text_when_needed_to_understand_the_assigned_work}

Work within {the_assigned_scope_and_caller_owned_resource_limits}. Preserve the selected service and original request. An omitted optional setting remains omitted in the assignment; any displayed service default is identified as a default. Choosing another query, dataset, sequence or execution environment requires the responsible parent's assignment. An API error does not authorize substituting different work. A publicly searchable name or candidate annotation is not required when the parent supplied sequence or selected input contents.

Use the selected tools and service instructions for this work:

{for_each_selected_tool_the_real_name_description_resources_and_complete_substantive_instructions}

{complete_explicitly_selected_supplemental_service_instruction_sections_and_any_relevant_instruction_text_received_in_this_unfinished_decision}

Decide what is still needed to establish {the_requested_result}. Use the actual preparation, request and response facts below to choose the next useful operation. Reuse preparation that corresponds to these inputs and settings. A retained response differs from a description of a request that has not been made. Examine additional service information or perform a supported check when it could change the next choice; neither is a compulsory preliminary stage unless the service's actual contract requires it.

Keep instructions, recorded setup, current access and this request's outcome separate. Instructions explain the service. A bound operation establishes that its declared request can be attempted. Neither establishes current authentication, service availability, database contents or acceptance of this work. A response establishes only what the service reported at its observation time. Missing or dated information stays unknown or qualified.

For this assignment, {the_actual_service_response_kind_and_exact_handoff_meaning}. For an immediate query, a validated retained response can establish the requested handoff; there is no remote job, queue or running state to invent. For an asynchronous job, distinguish accepted submission, observed execution, result readiness and acquired results. A usable original-job handoff can complete this launch assignment while the analysis continues. Apply this service's actual evidence requirements; do not impose another service's submission or status sequence.

Interpret failures according to what is known. A request rejected locally before sending, an unsuccessful HTTP response, a malformed response, an unknown submission outcome and a confirmed failed job are different facts. Preserve valid partial work and retained responses. If a request is confirmed not sent, choose only a repair or later attempt that this binding actually supports. If submission may have occurred, retain that uncertainty and use supported recovery or observation of the original work. A missing reply does not justify replacement submission. Failure to observe a job is not evidence that the job failed.

Interpret each response within its actual coverage. Preserve relevant subject names, native fields, units, scores, coordinate conventions and qualifications. A record or database functional label concerns its actual source subject; it does not establish a measured function of the annotation target. An empty page or no-hit search concerns the original query and settings. It differs from failed access or a result that has not been examined.

Preserve this service's continuation meaning: {the_actual_pagination_or_nonpagination_meaning}. A cursor, offset or page number identifies only the continuation that service reports. Do not treat one page as the whole population. Continuation information identifies possible further work without selecting it. Result acquisition remains the separately assigned work; do not expand this launch into collecting every page or interpreting the gene annotation.

Use observed service states and progress only for what they establish. Retain observation time, native status and material qualifications. Repeated unchanged status is not new progress. A running label alone does not establish throughput, completion fraction or a stall. Such measurements remain unknown unless actually received. Keep a last valid observation distinct from a later failed observation.

Use supplied duration expectations and provider request limits with their stated meanings. An actual earliest-permitted request time constrains that request; it does not select a polling cadence. A reported relative delay with an unknown sampling time is not an exact current earliest time. Select an explicit wait only when it is available and useful for this assignment. Keep HTTP response time, queue wait, service execution and total turnaround distinct. A provider estimate is not a measured duration, and elapsed time does not establish unreported remaining time. Unknown or incompatible expectations remain explicit.

Choose one next action from the actual operations available for this assignment:

| Available action | What it obtains or establishes | Required meaningful inputs and permitted values | Conditions and limits |
| --- | --- | --- | --- |
{actual_request_scoped_service_operations_and_relevant_permitted_common_actions_with_complete_operand_meanings}

Where an operation takes empty arguments, its input is the original assignment above. Empty arguments do not leave the work unspecified. A selected service request performs one bounded operation; later choices use its actual outcome. No operation is a private polling or retry workflow. Do not invent a child branch, result-read operation, replacement submission or wait capability.

Compare useful preparation, requests, observations, instruction examination, waiting and repair using your own action-category yields and the facts still needed for {the_requested_result}. Total yield is the saved signed gain from completed own actions, excluding inherited credit. Expected next yield concerns another completed action of that category, with its stated uncertainty. An unavailable estimate is unknown, not zero; a model band is not a calibrated guarantee. An attempt without an actual completed-action observation supplies no completed-action gain. A completed operation reporting a native failure remains a completed operation with its recorded gain. Keep operational progress, scientific annotation support, monitoring information and duration expectations separate.

This assignment completes when actual recorded facts validate {the_original_usable_handoff_endpoint_and_its_service_specific_evidence_requirements}. A merely prepared request is insufficient. Completion can mean retained immediate data or a usable original remote-job handoff, according to this assignment. It does not claim completion of an unfinished computation or the scientific investigation. Validated completion immediately sets future expected credit to exact zero while preserving the final actual gain and earlier observations. The ordinary controller then closes without an extra model turn or synthetic zero-gain action. Until then, the configured controller governs continuation and may yield with useful partial work.

Return exactly the parent's requested information:

| Requested field | Type and allowed values | Complete meaning and necessary relationships | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{all_original_parent_requested_fields_with_full_meanings_constraints_and_relationships}

Update only declared interpretation fields using information already received. The action you select now has no known outcome yet. Recorded request, response, handoff and completion facts come from actual outcomes. Do not compose substitutes or request a report-writing call. Preserve useful partial results, specific failures and uncertainty under the parent's declared meanings. Parent-supplied initial interpretation values are starting values, not new judgments by you.

Use the existing typed JSON response for action selection and declared report updates. If information is needed before selecting, use one of these existing internal lookups:

| Lookup | Required fields and meanings | What it can supply |
| --- | --- | --- |
{available_request_context_choices_with_actual_fields_allowed_values_and_limits}

An own-attempt detail lookup supplies recorded selected inputs, not arbitrary past response bodies. Instruction lookups supply instructions, not service observations or new capabilities. Continue the same unfinished decision after a lookup. A lookup creates no completed-action observation. Previously answered lookups remain answered after reconstruction. These complete TASK instructions apply on every exchange.

STEERING

| Fact affecting the assigned work | Actual received value | Observation time or supplied basis | Limitation |
| --- | --- | --- | --- |
{only_relevant_explicitly_supplied_or_received_preparation_access_database_service_and_response_facts}

| Original request or job | Latest valid outcome or native state | Observed at | Handoff/result availability and qualification |
| --- | --- | --- | --- |
{actual_original_work_rows_or_explicit_missing_information_without_fabricated_job_fields_for_immediate_queries}

| Relevant own attempt | Specific operation and distinguishing inputs | Actual outcome | Repair information or remaining requirement |
| --- | --- | --- | --- |
{material_distinct_received_attempts_including_failures_and_changed_observations}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty or unavailable reason |
| --- | ---: | ---: | --- | --- |
{original_saved_own_category_rows_without_inherited_parent_credit}

{when_interpretation_fields_are_present:
| Requested interpretation | Current value | Received basis or limitation |
| --- | --- | --- |
{current_declared_interpretations}
}

| Operation or available wait | Timing fact or expectation | Interval, units and statistical support | Observation time and unknowns |
| --- | --- | --- | --- |
{compatible_received_timing_and_provider_limits_or_explicit_unknown_for_a_timing_question_affecting_this_choice}

{when_actionable_failure_is_present:
| Failed request or returned field | Specific failure and affected input | Valid partial result | Submission/access/recovery uncertainty |
| --- | --- | --- | --- |
{actual_actionable_failures}
}

{when_an_internal_lookup_has_supplied_additional_decision_relevant_facts:
| Requested detail | Actual information supplied | Limit or remaining missing information |
| --- | --- | --- |
{deterministic_projection_of_answered_lookups_in_this_unfinished_decision}
}
```

The caller expands the selected service's real instructions and request meanings;
it does not show all service families in one prompt. Current inspected bindings
cover HMMER, UniProt, NCBI BLAST and BV-BRC public Data API. BV-BRC AppService is
not bound by the public Data API. No runtime prompt implementation is claimed.
