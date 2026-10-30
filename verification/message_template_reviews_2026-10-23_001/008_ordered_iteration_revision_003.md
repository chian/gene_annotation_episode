# 008 — read the assigned paper for the gene annotation

```text
TASK

Read {paper_title_or_actual_source_name} to determine {the_parent's_exact_biological_question_about_gene_and_candidate_function}. Establish what the paper actually demonstrates, which experimental conditions limit that result, and what it can support about annotating {gene_and_organism} as {candidate_function_if_assigned}.

Answer this question so the parent can {the_parent's_exact_annotation_decision}. Examine {assigned_source_and_permitted_derivatives}, within {full_assigned_scientific_scope_and_binding_constraints}. Begin with {assigned_representation_and_starting_window}; supplying that window does not mean it has been read. Choose subsequent reading or interpretation from what you actually learn. Continue in document order when that gives useful context; reread, change the window or examine a qualification when the evidence calls for it. A complete-paper read, fixed window size and compulsory traversal order are not required.

For each claim relevant to {gene_or_candidate_function}, identify the protein, organism, construct or sample studied, what was measured, and the substrate, conditions, controls and uncertainty needed to interpret the result. Read the neighboring methods, results or qualifications when they could change that interpretation. Preserve separate results for different constructs, conditions or measurements. A title or copied annotation label does not establish the claimed activity.

Distinguish the activity demonstrated in this paper from the proposed function of {gene}. When an assay used a homolog or another organism, retain the actual experimental subject and the relationship that could justify transferring its result. Compare the source's evidence with {parent_named_candidate_functions_or_actual_biological_alternatives}; state what distinguishes those explanations and what remains uncertain. Family membership, substrate specificity and physiological role can require different evidence. Keep the paper's reported observation separate from your inference about {gene}.

Read qualifications as part of the result. Determine whether an apparent disagreement concerns the same protein, preparation, measurement and conditions. Preserve reported negatives, conflicting evidence, data-not-shown limitations and partial results. An inaccessible passage, unexamined range or missing text projection is not a biological negative. A useful correction can improve the answer while weakening support for the candidate annotation.

Select source windows using the actual representation and valid UTF-8 byte positions. For source.read, give the assigned source, representation, nonnegative byte offset and positive byte limit. Use the returned start, end and continuation when choosing another window. The actual end can be earlier than the requested offset plus limit because a UTF-8 character cannot be split. A returned continuation permits the next read; it does not require it. If a requested text view falls back to the original representation, preserve the representation actually returned and its own coordinates.

Keep each quotation tied to the exact representation and returned byte range. Do not join separate spans into a quotation the source never contained. A text projection may omit XML headings, tables or footnotes; select actual available source access when those details matter. Receiving some source bytes does not establish examination of intervening gaps or understanding of the whole paper. The end of one representation does not establish that the paper contains no other relevant evidence.

When the received passages support an answer, record the interpretation through the existing reasoning action. Retain the actual subject, conditions, measured result, source location, exact quotation and limits on transfer to {gene}. Repeated reading and additional byte coverage alone do not supply another scientific finding. A citation attributes a result without supplying its other source contents or granting access to other papers.

Choose the next read, examination or interpretation from the actual available operations:

| Choice | What it can establish about {gene_or_candidate_function} in this paper | Required meaningful inputs and limits |
| --- | --- | --- |
{actual_available_source_operation_or_reasoning_rows_without_state_query_or_child_options}

This reading episode has no child branches. Use your own action-category yields to compare another read or interpretation, together with the evidence still needed for {the_exact_biological_question}. Total yield describes completed own actions, excluding supplied starting information. Expected next yield concerns another completion in that category, with the stated uncertainty; an unavailable estimate is unknown. Keep investigation progress, annotation support and duration estimates separate. The configured controller governs continuation; reaching the last byte is not a scientific stopping rule.

Return the information the parent requested about this paper and {gene}:

| Requested field | Type and permitted values | Exact biological meaning and required qualifications | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_original_parent_return_field_meanings}

Update the declared interpretation fields using evidence already received, preserving these meanings and allowed values. A read you are about to select has no known result yet. Recorded fact fields come from actual outcomes. Keep valid partial work and identify the specific failed input or missing result when repair is needed. Use the existing typed JSON response for selection and report_update. If an available own-history lookup is needed to choose, use its declared request_context fields: {readable_existing_lookup_contract}. It continues this same decision and creates no completed-action observation. Request only detail the actual lookup can supply.

STEERING

| Question about {gene_or_candidate_function} | Current answer or missing evidence | Material qualification |
| --- | --- | --- |
{only_relevant_initially_supplied_or_received_biological_question_rows}

| Relevant own read | Source and actual returned representation | Received UTF-8 range [start, end) / total bytes | Returned continuation or end | Result or access limitation |
| --- | --- | --- | --- | --- |
{only_relevant_actual_own_read_rows}

| Passage needed for this decision | Source, representation and exact byte range | Literal received text |
| --- | --- | --- |
{only_needed_previously_received_passage_rows}

| Experiment or claim in {paper} | Actual protein/organism and conditions | Measured or reported result | Limits for {gene}; exact source location |
| --- | --- | --- | --- |
{only_relevant_explicitly_supplied_or_received_evidence_rows}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty |
| --- | ---: | ---: | --- | --- |
{actual_saved_own_category_rows}

| Requested interpretation | Current value | Basis or limitation |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_relevant_existing_duration_table}
{only_if_present_actionable_failure_table}
```

## Fill and source notes — outside the prompt

The opening uses the parent's exact biological question. Where no candidate
function was assigned, omit that phrase rather than inventing one. The paper,
target, permitted source bounds, starting selector and binding constraints come
from the original request and validated reading assignment. The starting window
is an assignment operand, not an executed read. Full requested field meanings
enter TASK; explicitly supplied facts, received passages, actual own outcomes
and current interpretation values enter STEERING. Include the complete TASK on
every exchange, including after a lookup or reconstruction. Omit irrelevant
rows and inapplicable tables; retain unknowns that affect the next choice.

Reviewed the complete current `LiteratureEpisodes` binding and complete
`materials.source_window`, the original 008 review and its producer/consumer
trace, and the mandatory task/steering/directness contract. Consulted the project
goal, episode structure and time-aware-estimation records. The binding supplies
source-bounded ordinary operations and no children for ordered reading. The
source-window function supplies actual representation, start/end, total bytes,
available representations and exact nullable continuation; it trims an
incomplete trailing UTF-8 character and rejects an invalid starting boundary.
These are operational selectors and evidence coordinates, not host tracking.

The proposed action table excludes `state.query` in accordance with the user's
instruction to remove it. Current code still exposes it in the binding's access
catalog; this document does not claim that removal is implemented. Keep that
implementation gap outside the model task. Existing typed JSON response and
parent return contracts remain unchanged.

Prior coverage and exact passages must come from this receiver's actual saved
outcomes. A delivery reference, source registration or citation does not imply
examination or supply linked records. The current own-outcome index provides
metadata; the current selected-input lookup does not recover arbitrary earlier
source passages. This remains a presentation gap to implement rather than an
invitation to invent result recovery, depend on previous chat survival or add a
model summary call. The proposed text renderer and readable operand resolution
are not yet implemented.

STEERING yield rows reuse original completed-own-action observations and the
existing category expectations. No gains are rescaled, parent histories copied,
or completion rule added. Optional duration rows contain only compatible actual
estimates with their measured interval and support. Optional failure rows state
the failed action or field, affected inputs and preserved partial work.

Original 008 is preserved. This revision changes only this review document. No
application code, tests, network requests, model calls or run state changed.
The template is ready for the user's running feedback, not settled or coded.
