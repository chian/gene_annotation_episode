# 006 — `literature_page__next_decision` — revision 003

```text
TASK

Examine {paper_citation_or_actual_source_name} to determine {concrete_biological_question_about_annotating_gene_as_candidate_function}. Choose the passages, tables, figures, methods or supplementary material that can answer that question, interpret what they establish, and change where or how you read when the evidence calls for it.

Gene: {gene_name_or_public_accession} from {organism}
Candidate function or biological role being evaluated: {actual_candidate_function_or_explicitly_unspecified}
Claim, assay result or comparison to check in this paper: {complete_concrete_scientific_question}
What the parent needs from this paper: {complete_requested_scientific_result_and_its_use}
Source and representation you may examine: {actual_paper_or_supplement_identity_and_assigned_representation}
Other binding limits: {complete_parent_and_caller_constraints}

Find which protein, organism, construct or experimental preparation the paper actually tested. Identify the relevant measurement, controls and conditions before using a result to support the proposed function of {gene_name_or_public_accession}. If the experiment tested a homolog, report the homolog's result and the limits on transferring it to this gene. Do not describe a homolog's assay as an assay of this gene. Check whether the reported evidence establishes family membership, a particular biochemical activity, substrate preference, a physiological role or localization; retain the level it actually supports. An author's functional label and the experiment behind that label are different information.

Choose your next read by asking what is missing from the evaluation of {candidate_function_or_concrete_biological_claim}. A result may need a methods passage to identify the assayed construct, a table footnote to establish the condition, a control comparison to interpret the effect, or a neighboring sentence to reveal a qualification. Use observed headings, table labels, captions, sheet names and references to locate that information. If the passages already examined are sufficient for a supported interpretation, interpret them rather than reading additional material merely to increase coverage. The paper need not be read in full or in a fixed order.

Choose the representation that can expose the needed evidence. A paragraph projection may omit a table, heading or footnote. If the proposed function depends on such material, examine the available original representation or appropriate native table/page operation rather than treating its absence from the projection as a biological negative. Retain the actual representation returned: a text request can fall back to original bytes when no text derivative exists. UTF-8 positions identify locations in their own representation; normalized PDF text offsets do not identify positions in the original PDF. Keep physical page numbers separate. For supplementary workbooks, use the observed sheet and cell coordinates. Headings, units, conditions and footnotes remain unknown until supplied or examined. Interpret a figure image only when the pixels have actually been supplied; rendering it alone is insufficient.

Distinguish a missing scientific result from a failed attempt to obtain it. An empty row selection, extraction failure, inaccessible file and a reported negative assay are different outcomes. A sheet or archive inventory identifies available material without establishing its contents. Re-reading a passage or viewing a second representation of one assay does not supply independent experimental evidence. Keep separate passages and their locations separate; do not concatenate them into a quotation. Preserve a contradiction, missing control or transfer limitation even if it weakens the proposed annotation of {gene_name_or_public_accession}.

Select a direct read when the needed passage or table selection is a one-off operation. If interpreting the relevant table requires iterative choices of rows, comparisons, controls or footnotes, you may commission a literature_table child to investigate that specific question. If finding the answer requires following the paper's document-order context, a literature_ordered child can make those reading choices. If several supplied passages and their neighboring qualifications need investigation, a literature_targeted child can examine those separate spans. None is a mandatory stage. Give a child the concrete question about this gene and this paper, the source boundary, binding limits, explicitly selected starting information and the exact requested result fields. The child chooses how to investigate that question.

Examine only {paper_citation_or_actual_source_name} and its permitted actual derivatives. A citation to another paper does not supply the cited paper's contents. Do not replace this reading assignment with a new literature search. When a reading child returns, use only its admitted requested result, retaining the actual assayed subject, conditions and limitations. The return does not expose private child reads or history, and the child's internal actions are not your action observations.

Available next choices for evaluating {candidate_function_or_concrete_biological_claim} in this paper
| Operation or child | Specific scientific use | Required operands, allowed values and binding limits | Returned information or committed result |
| --- | --- | --- | --- |
{actual_available_source_reason_child_wait_and_repair_contract_rows}

Commit an interpretation of the paper's evidence through the existing reasoning action, using the actual subject tested, the relevant observations and exact source locations. State separately what the experiment shows and what can be inferred for {gene_name_or_public_accession}. Preserve useful partial results, contradictory findings and conditions that remain unexamined. Bytes delivered, navigation and repeated reading are not by themselves new scientific support.

Result requested for {concrete_biological_question_about_the_gene}
| Field | Type, allowed values and reference meaning | Exact scientific information requested | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_parent_requested_return_field_meanings}

Retain or revise only the declared interpretation fields in report_update, using evidence received before the next action you select. The result of that next action is not known yet. The runtime supplies the declared recorded facts; do not compose replacements or request an extra report-writing call. Preserve the meaning of a negative finding, a qualification and an unanswered question in the parent's exact allowed values.

Use your own action-category table to compare the next reading or interpretation choices. Its totals are the saved signed gains from your completed actions, excluding starting information. Expected next yield is conditional on completing that category again; its uncertainty is an approximate working-model band. Unavailable is unknown, not zero. A read may have zero immediate yield before later interpretation. Keep scientific progress, annotation support and duration separate. Use compatible duration or wait information when it is available. The configured controller owns continuation; there is no reading quota, required child order, polling cadence or scientific acceptance gate.

Return the existing typed JSON response: select_action with selection and report_update. If an available own-history lookup is needed to choose your next read or interpretation, use request_context with the declared operands, then continue this same pending decision. The lookup provides only the detail its actual contract supports and does not guarantee restoration of earlier source text. It creates no action observation. The host executes your selected action. This complete TASK appears on every iteration and after any lookup or reconstruction.

STEERING

| Own action category | Completed | Total yield | Expected next yield: lower / value / upper | Uncertainty or unavailable reason |
| --- | --- | --- | --- | --- |
{own_action_category_rows_or_no_completed_observations}

| Observed part of this paper or supplement | Usable location or selection | Known content or access limitation |
| --- | --- | --- |
{only_next_decision_relevant_observed_navigation_rows}

| Previous read or admitted reading result | Location and approach | Actual result for the gene/function question | Subject, condition or limitation |
| --- | --- | --- | --- |
{only_next_decision_relevant_own_attempt_and_received_result_rows}

| Requested result field | Current value | Evidence or limitation |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_needed_exact_previously_received_passage_or_currently_supplied_image_with_actual_source_representation_and_coordinates}

{only_if_relevant_pending_table:
| Pending reading work | Specific question about the paper | Latest received progress and observation time | Available wait information |
| --- | --- | --- | --- |
{necessary_pending_rows}
}

{only_if_relevant_duration_table:
| Proposed operation or wait | Actual measured interval | Expected duration and observed range | Sample/outcome support or unknown |
| --- | --- | --- | --- |
{compatible_existing_duration_rows}
}

{only_if_present_actionable_feedback_table:
| Failed attempt or delivery | Actual failure and affected operand | Preserved partial result | Repair-relevant fact |
| --- | --- | --- | --- |
{necessary_failure_rows}
}
```

This revision applies the user's task-directness correction throughout the
recurring TASK. The fill points name the actual gene, proposed function, paper
and concrete biological question from the commission. They are not filled with
slot labels or process-construction terminology. If no function or assay was
specified, state that explicitly and render the real biological question; do
not invent a candidate or experiment. Evidence and prior outcomes remain terse
STEERING rows, not recurring task instructions.

The original and revision 002 are preserved. Their producer/consumer traces and
unimplemented presentation dependencies still apply. Stable assignment and
parent-result meanings fill TASK; only explicitly supplied or actually received
facts, own outcomes, admitted child results and original yield/duration support
fill STEERING. Internal identities and tracking stay outside model text. Existing
typed JSON outputs and parent-return forms remain unchanged.

Read the new directness section of `docs/TASK_AND_STEERING.md` and revision 002.
No application changes, tests, network requests, model calls or scientific runs.
