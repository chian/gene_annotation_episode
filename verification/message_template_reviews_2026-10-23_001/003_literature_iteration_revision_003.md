```text
TASK

Find and interpret published experiments addressing {specific_biological_claim_in_parent_words} for {gene_name_and_biological_accession}. Determine {exact_candidate_annotation_or_biological_question_in_parent_words}.

Use the evidence to inform this annotation decision: {parent_exact_biological_decision}.
Evaluate this gene and these assigned features or positions: {full_assigned_gene_scope}.
Follow these constraints: {full_parent_defined_constraints}.
Compare these proposed activities, roles or explanations: {parent_named_biological_alternatives_or_explicitly_unresolved_question}.

Choose work that could change whether {specific_biological_claim_in_parent_words} is supported, contradicted or limited for {gene_name}. Identify what measurement would distinguish the named explanations and how different possible results would affect the annotation. Search for that evidence, examine a relevant publication, interpret evidence already received, or ask a strategy child to determine how to find the needed experiments. Use previous results to revise what you search for or read. Related proteins and study organisms supply evidence about {gene_name}; they are not additional annotation targets.

Build searches around the proteins, activities and experiments in this question. Use relevant gene names and accessions, reported synonyms, substrate or reaction names, family/domain terms, organism names and experimental methods. Search for experimentally characterized relatives when their measurements could bear on {specific_biological_claim_in_parent_words}. Keep the biological claim separate from the literal query sent to a provider. Compare the exact previous queries and their returned sources before changing terms or search approach; cosmetic rewording or rediscovering the same paper supplies no new evidence. A search with no useful result can reflect terminology, indexing or access limitations. It does not demonstrate that the protein lacks an activity or that no experiment exists.

Read each experiment for what was measured and on which material. Identify the assayed protein, organism, construct or mutation, method, substrate or biological condition, controls and reported result where they affect the claim. Examine the relevant methods, results, tables, figures and qualifications as needed for that interpretation. A title, search snippet or copied annotation label can identify a source; it cannot establish an experimental result for {gene_name}. Distinguish measured molecular activity from family membership, inferred physiological role and localization whenever those differences affect the proposed annotation.

When an experiment used another protein, state what was demonstrated for that protein and examine the evidence connecting it to {gene_name}. Sequence similarity or identity may support that connection while leaving substrate specificity, measured activity or physiological role unresolved. Keep the source's assertion separate from the inference transferred to {gene_name}. Preserve differences in assayed constructs, organisms and conditions that limit the transfer. Do not convert a predicted annotation on a relative into a measured function of this gene.

When papers or experiments appear to disagree about {specific_biological_claim_in_parent_words}, compare the actual measurements, constructs, substrates and conditions. Determine whether they test the same claim and whether those differences can explain the contrast. Retain opposing results and their qualifications rather than merge them into one observation. Preserve reported negatives, data-not-shown limitations and uncertainty. Missing access is an access limitation. Repeated accounts of the same underlying experiment are not independent evidence. A source-grounded correction or a finding that an assay cannot support transfer can improve the investigation while reducing annotation support.

Record conclusions about {gene_name} through the reasoning action. Preserve the actual assayed subjects, source representation, exact quotations and source anchors. Separate reported observations from your inference about the candidate annotation. Interpret evidence already available when it can answer the question; a new source or experiment is not required on every turn. Reading, navigation and source delivery alone do not establish a new finding.

For a search problem that needs repeated choices, commission a literature strategy child to answer the narrower biological search question you need resolved: which approach can locate experiments bearing on the specified activity, role or alternative explanation? Give it the exact gene/protein names, biological claim, contained scope, constraints and explicitly selected initial facts it needs. Specify the typed return fields and what each must mean for your later annotation decision. A supplied reference does not establish that its contents were delivered or read. Do not copy your history, yields or source access into the child. The child chooses and revises its searches. Use its admitted returned fields and material qualifications to decide what the publications establish; its private search trajectory is not part of the return.

A one-off search or source read is a tool action. You can search/read directly; strategy is the only child branch available here. Select a wait only when useful pending information warrants it. There is no required search sequence, child sequence, reading quota or complete-document requirement. Duration and yield estimates inform your choice; the configured controller governs continuation. Do not add a stop action, acceptance gate, turn budget, required experiment or polling cadence.

Return these parent-requested fields about the publications and their bearing on the annotation:

| Field | Required type, allowed values and reference meaning | Exact biological question or recorded fact this field answers | Your interpretation or runtime-recorded fact |
| --- | --- | --- | --- |
{complete_original_parent_return_field_meanings}

Update report_update only from evidence available before the action you select. Preserve the parent's field meanings and allowed values. Parent-supplied initial values are not your new judgment. Runtime fact fields describe actual records; do not compose replacements. Later tool output does not automatically revise your interpretation. Keep valid partial results and use the actual failed operands and failure code when a search, source read or return needs repair.

Choose among the available operations using their actual operands and restrictions:

| Operation or child kind | Gene, experiment, source or search question it can address | Required operands and restrictions | Returned evidence or committed result |
| --- | --- | --- | --- |
{relevant_available_operations_and_existing_operand_contracts}

The own-action table records signed gain excluding inherited credit. Expected next yield is conditional on completing the same category again. Unknown estimates remain unknown. Approximate bands do not guarantee the next result or estimate the chance an action completes. Source acquisition may earn zero immediate progress before interpretation. Keep scientific progress, annotation support, monitoring information and duration expectations separate.

Use the existing typed JSON response: select_action with selection and report_update. If an exact detail from your own previous queries or received results is needed first, use request_context with the existing own-history lookup fields: {readable_existing_lookup_fields_and_allowed_values}. A lookup continues this same decision and creates no action observation. The host executes the selected action.

STEERING

| Own action category | Completed | Total signed yield | Expected next yield: lower / value / upper | Uncertainty or unavailable reason | Uncompleted attempts |
| --- | --- | --- | --- | --- | --- |
{own_action_category_rows}

| Own prior query, source read or commissioned search question | Actual result / admitted strategy return | Access or interpretation limit |
| --- | --- | --- |
{necessary_specific_prior_attempt_rows}

| Candidate biological claim | Received experimental result or current interpretation | Assayed protein, organism and conditions | Transfer limit / conflicting result / unresolved claim | Publication and exact evidence basis |
| --- | --- | --- | --- | --- |
{necessary_received_evidence_rows}

| Requested interpretation field | Current value | Actual evidence basis / parent-supplied initial value |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_needed_pending_or_timing_table:
| Pending search question or proposed source operation | Observed state / awaited information | Measured interval or expected duration | Statistical support / unknown | Wait information actually available |
| --- | --- | --- | --- | --- |
{necessary_pending_or_timing_rows}
}

{only_if_needed_failure_table:
| Failed search, source read or return | Failure code and affected operands | Preserved partial result | Repair-relevant fact |
| --- | --- | --- | --- |
{necessary_failure_rows}
}
```

This revision applies task directness throughout the literature prompt. Biological placeholders take the parent's exact gene, claim, candidate and alternative wording; they do not introduce a candidate, additional scope or inferred finding. Full TASK is supplied on every iteration, including lookup and reconstruction exchanges. Only the factual STEERING tables change with prior work. Prior drafts are preserved; the template remains proposed for running human feedback.

| Information trace | Source | Next decision it informs |
| --- | --- | --- |
| Gene, candidate claim, comparison and return meanings | Immutable child assignment, explicitly assigned context and constraints, original parent purpose/form; parent biological objective metadata only | Which publication, experiment, search or interpretation can answer the actual annotation question |
| Previous queries and received evidence | Own saved selected operands/outcomes; explicitly received scientific records and admitted strategy-return fields | Whether to repeat, revise a search, examine a publication or qualify transfer to the gene |
| Own yields | Existing own observations and `decision_history.yield_table`, unchanged | Compare action categories without importing parent/child internal histories or changing score mathematics |
| Current return, pending work and failures | Existing report values/bases, own commissions, actually received progress/estimates and actionable failure records | Interpret already received evidence, await useful information or repair a selected action |

JSON remains internal input data and the existing typed output/parent-form contract. Rendering is direct text and tables; no model call composes facts. Host IDs, hashes, revisions and custody bookkeeping stay outside the prompt. Biological accessions, publication identity, query literals and source anchors remain when they affect the evidence or selected operation. Validation references alone supply no inherited source knowledge.

Only this revision document was added. No application edits, tests, network requests, model calls or run changes. Read `docs/TASK_AND_STEERING.md` including the task-directness correction and the preserved revision 002; the earlier complete literature/shared-path trace remains applicable.
