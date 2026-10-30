# 018 — annotation root → literature: task-directness revision

```text
TASK

Find and examine published evidence to determine **{the parent's exact biological question about annotating the named gene or candidate function}**.

Gene/protein: **{fixed target name and supplied biological accessions}**.
Organism/strain: **{supplied organism and strain, or unknown}**.
Use your answer to help the parent **{the exact annotation decision this evidence will inform}**.
Examine **{assigned proteins, activities, biological conditions and any relevant sequence-region bounds}**.
Follow **{the complete binding scientific and resource constraints}**.

Determine what the publications establish about **{the named activity, biological role or other property being assessed}**, what they leave uncertain and whether their findings can support that annotation for **{gene}**. When the parent asks you to compare candidate functions, compare **{the exact parent-assigned functions or explanations}** using the observations that could distinguish them. If no candidate function has been assigned, answer the parent's biological question without inventing one.

Search using names and concepts that could locate the relevant evidence: supplied gene/protein names and accessions, established aliases, the proposed activity or reaction, related characterized proteins, organism names and experimental terminology. Choose terms according to what you need to learn about **{gene or candidate function}**. A query is one way to locate that evidence; its wording does not redefine the biological question. Use actual returned sources and earlier supplied search results to decide whether different terms, coverage or a different source could reveal information still missing.

Examine what each relevant paper actually measured or observed. Identify the studied protein, organism, construct or sample; the assay or other observation; its result; and the conditions, controls and qualifications that affect the conclusion. Read the relevant methods, results, tables, figures or supplementary material when they determine whether a claim is justified. A title, abstract assertion or copied annotation label can identify a paper to examine; it does not establish that the proposed function was experimentally demonstrated for **{gene}**.

For a paper about a homolog or another organism, separate what was established for the studied subject from the inference about **{gene}**. Preserve the relationship connecting the subjects and the differences that limit transfer. Determine whether the evidence supports a shared family, a particular activity, substrate specificity, cellular role, organismal role or localization; these claims may have different support. A measurement on a related protein remains a measurement on that protein, even when it strengthens the proposed annotation.

When publications appear to disagree, compare the actual subjects, constructs, substrates, measurements and conditions before combining their conclusions. Determine whether they test the same claim and whether an experimental or biological difference explains the contrast. Preserve informative negative results, corrections, data-not-shown limitations and uncertainty. Repeated accounts of the same experiment are not independent evidence. A failed search, unavailable article or unexamined passage is an access or examination limitation, rather than evidence against a protein function.

Choose the search, source examination or interpretation that could most improve the answer about **{gene or candidate function}**. You may search or read directly. Commission a literature-strategy child when choosing how to locate the needed publications warrants a narrower iterative investigation. Give that child the biological question, scope, constraints, explicitly supplied facts and exact typed information needed on return; it chooses its own searches. A one-off search or read remains a tool action. No paper count, prescribed search order or complete-document requirement is imposed.

| Available action or operation | What it can obtain or establish for this gene and question | Required meaningful inputs and restrictions |
| --- | --- | --- |
{actual_available_search_read_reason_strategy_child_wait_and_repair_rows}

Record conclusions about **{gene}** through the existing reasoning action, retaining the actual studied subject, relevant conditions and exact source basis. Keep a paper's reported result separate from your inference about the annotation. Evidence already received may justify an interpretation without another lookup. Acquiring or rereading a paper alone does not establish a new scientific finding.

Return these exact requested results:

| Requested field | Type and allowed values | Full biological meaning and required qualifications | Your interpretation or recorded fact |
| --- | --- | --- | --- |
{every_original_parent_requested_field_with_its_complete_constraints_and_meaning}

Use the existing typed JSON response, with its declared action selection and interpretation-update fields. Update an interpretation from information already received; an action you are about to select has no known result yet. Recorded fields come from actual outcomes. Keep useful partial answers and specific failures that permit repair. A supplied initial interpretation is a starting value, not a new conclusion by you.

Use your own action-category yields as observations become available. Total yield concerns completed own actions; expected next yield concerns another completion of that category, with its stated uncertainty. An unavailable estimate is unknown. Keep investigation progress, candidate annotation support, monitoring information and duration expectations separate. The configured controller governs continuation. An own-history lookup supplies a specific earlier detail for this same decision and does not complete an action.

STEERING

| Candidate function for {gene} | Supplied claims and supporting evidence | Material uncertainty | Its own supplied annotation score |
| --- | --- | --- | --- |
{only_explicitly_supplied_candidate_rows_needed_for_this_question}

| Supplied observation or interpretation | Actual protein/organism and conditions | Exact result | Qualification and supplied source location |
| --- | --- | --- | --- |
{only_explicitly_parent_selected_fact_cells_preserving_subject_units_and_limits}

| Known query or source lead | Supplied result | Access or examination status |
| --- | --- | --- |
{only_explicitly_supplied_queries_or_source_leads_that_affect_the_first_choice}

| Requested interpretation | Supplied starting value | Basis or limitation |
| --- | --- | --- |
{only_relevant_original_initial_interpretation_values}

| Proposed search or examination | Supplied duration estimate and measured interval | Support and uncertainty |
| --- | --- | --- |
{only_relevant_prospective_timing_facts_explicitly_supplied}
```

## Construction notes — outside the model prompt

This revision preserves the original 018 draft. It applies task directness
throughout, as well as the opposite verbosity policies for detailed recurring
TASK and curt factual STEERING. The actual parent biological question supplies
the opening; a candidate function is named only when the parent assigned one.
The two braces surrounding each instruction fill expand to actual text, not
serialized objects. Renderer instructions and these construction notes are not
sent to the model.

The original child goal, contained scope, binding constraints, stated annotation
decision and complete typed return meanings supply TASK. Current candidate
claims and scores, observations, source leads, supplied prior query results and
initial interpretation values belong only in initial STEERING. Every fact cell
must be explicitly selected by the parent from information it actually received.
A citation attributes a supplied result without supplying article contents.
Reference validation, parent receipt ancestry and linked-record traversal do
not select additional knowledge for this child.

Omit irrelevant rows and inapplicable tables. Preserve unavailable values as
unavailable when they matter. A scope-wide progress score cannot stand in for
the candidate's annotation score. The child begins with no completed own-action
observations, so this commission contains no invented yield table and no parent
yields. Later iteration steering uses the child's own outcomes and existing
category estimates while retaining this complete TASK.

The boundary remains parent-selected `episode_child` → contained assignment →
`LiteratureEpisodes.prepare_assignment` → shared episode decision. Parent
`question_context_refs` and `source_refs` are validation operands, not a
field-disclosure specification. The original review records the complete shared
commission, receipt, form, reasoning-view and provider trace; it remains
applicable. The complete current literature binding was reread for this
revision, including its permitted direct operations, optional strategy branch,
assignment validation, execution, report validation and credit delegation.

The model receives designed text and tables. Existing typed JSON output and the
original parent return contract remain unchanged. This document does not add
fact-selection mechanics, readable-reference binding, a report-composer call,
scores, a stopping rule or a new episode relationship. Those are not claimed
implemented by editing this draft.

Read `docs/TASK_AND_STEERING.md`, including the user's directness correction,
the original 018 review and complete `gene_annotation_episode/literature_episodes.py`.
Only this new review document was written. No application code, tests, network
requests, model calls, scientific runs or other templates changed. This draft
awaits the user's running feedback before being settled or coded.
