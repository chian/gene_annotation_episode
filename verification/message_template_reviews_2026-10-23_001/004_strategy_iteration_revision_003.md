# 004 — `literature_strategy__next_decision` — revision 003

```text
TASK

Find a productive literature search approach for answering: {full_assigned_biological_question_naming_gene_organism_and_claim_or_experiment}.

Choose and revise queries, providers and search limits to find studies that can support, qualify or contradict the claim in that question. Judge an approach by whether it retrieves evidence relevant to answering the question, rather than by hit count alone. You choose the search approach; a search child can decide which returned papers deserve examination.

Gene being annotated: {gene_organism_and_known_public_identifiers}
Gene or region this search concerns: {full_assigned_target_scope}
Constraints on this search: {full_parent_and_caller_constraints}
What the parent needs to decide from your result: {full_parent_requested_use}

Keep the biological question separate from each literal query. The question says what must be learned about the gene; a query expresses one way to find it through a provider's fields, syntax and filters. Changing an unsuccessful query does not change the gene, the proposed function or the question you were asked to answer.

Formulate queries using relevant gene names, established aliases, locus tags, protein accessions, family or domain names, proposed activities and assay or method terminology. Older papers may name an assayed protein differently from a current database entry. Distinguish an established alias from a term you propose to try. When a substrate, construct, phenotype, experimental method, organism or growth condition matters to the question, consider how a paper would describe it and whether the query can find that terminology. Preserve those subjects and conditions when interpreting what a search returned. A study of a reference protein is evidence to evaluate for this gene; its measured activity does not automatically transfer to the gene.

Compare ways a query can miss useful studies or retrieve misleading ones. Exact gene names and organism filters can miss historical names or experiments on homologs; broad family names can retrieve papers that do not test the proposed activity. A method term may find an assay buried in a paper whose title emphasizes another question. Different providers cover different publications and searchable fields. Filters and pagination can restrict what you have actually searched. Use the returned results to choose whether to keep a query, change terms, change filters, search another provider or examine information already retrieved. No sequence of those choices is required.

Distinguish an empty returned page, an exhausted reported result set, an unexamined later page, a failed request and an inaccessible article. Retain the exact query and limits that produced each outcome. None of these outcomes alone proves that the gene lacks an activity or that no study exists. Titles and snippets help find papers; they do not establish an assay result or its relevance to this gene. Source qualifications and negative results can motivate a better query even when they weaken support for the proposed annotation. An available source record does not establish that its contents were read.

Use an ordinary tool for a single search, acquisition or read. Commission a literature_search child when deciding which returned sources merit examination requires several choices that may change as papers are examined. Give that child the biological question, the returned results relevant to it, the narrower scope, constraints, explicitly supplied facts and the typed result you need. Let it choose which sources to examine. Do not pass your private history, yields or assumed access to source contents. Use only its requested admitted result to guide your next search approach; its internal actions do not become your own observations.

Available actions
| Choice | Available operation or child | Required operands and limits |
| --- | --- | --- |
{actual_available_tool_reason_child_wait_and_repair_rows}

Choose the next action from these alternatives using the question, received findings, actual search outcomes and your own yield information. A direct search or read, a commitment based on existing evidence, or a search child may be useful. Waiting or repair may matter when work is actually pending or a recorded failure needs attention. Use duration expectations when supplied; unknown durations remain unknown. The configured controller governs continuation. There is no required search order, reading quota, polling cadence or number of children.

Result requested by the parent
| Field | Type | Allowed values and exact meaning for the parent's question | Filled from recorded facts or interpreted by you |
| --- | --- | --- | --- |
{one_row_per_requested_field_with_complete_type_allowed_values_and_parent_meaning}

Return the information specified in this form. Use report_update only for its declared interpretation fields, preserving their meanings, uncertainty and material qualifications. Base an update on information already received; the action you now select has no outcome yet. The host fills recorded fact fields. Preserve valid partial work. Different candidate annotations concern the same gene; revisions of one annotation are not additional candidates. A controller yield does not establish that the biological question has been answered.

Keep the supplied typed JSON response contract unchanged. If an earlier own input is needed, request it through the declared request_context exchange and continue this same decision. When ready, return selection and report_update in that contract. The host executes the selected action.

Read the yield table as this episode's saved signed completed-action gains, excluding the starting baseline. Expected next category yield assumes that category is chosen and completed again. The reported uncertainty is an approximate working-model band, not a calibrated guarantee; unavailable is not zero. Acquisition may earn zero immediate credit before a later interpretation. Yield, annotation support and execution duration have separate meanings.

STEERING

| Explicitly supplied fact or received finding | Gene / assayed subject and conditions | Qualification affecting the next search |
| --- | --- | --- |
{only_relevant_supplied_fact_and_received_finding_rows_or_none}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty / unavailable reason |
| --- | --- | --- | --- | --- |
{own_category_rows_or_no_completed_observations}

| Own attempt | Exact provider query, filters and page / child question | Actual outcome | Qualification |
| --- | --- | --- | --- |
{only_relevant_own_attempt_rows_or_none}

| Requested interpretation field | Current admitted value | Basis limitation |
| --- | --- | --- |
{current_requested_interpretation_rows_or_none}

{pending_table_only_if_relevant}
{timing_table_only_if_relevant}
{actionable_feedback_table_only_if_present}
```

Optional headers: `Pending own work | Biological question assigned | Actual state / received progress`; `Work or wait | Existing duration / wait expectation | Support / unknowns`; `Attempt or delivery | Actual failure | Affected operand / retained partial work`. All STEERING rows are concise recorded facts; no narrative recap. Render the complete TASK on every call, after internal lookups and after reconstruction.

Brief source notes:

- Directness follows the appended correction in `docs/TASK_AND_STEERING.md`. Opening question, target scope, constraints and result meanings come from the actual parent request. Initial supplied scientific facts now appear only in STEERING, clearly marked as supplied.
- Existing literature strategy instructions, operation catalog and permitted search-child relationship supply available choices. Own action records and admitted requested child returns supply query/outcome pairs; `action_yields.rows` supplies unchanged totals, forecasts and uncertainty. No parent yields or automatic source knowledge are supplied.
- Host reference resolution and readable outcome projection remain implementation dependencies identified in the original draft. Host identities and tracking stay internal. Typed JSON responses and parent forms remain unchanged.
- Revisions 001 and 002 are preserved. This draft is for running user feedback; no application code, tests, network, model calls, process configuration or scientific run changed.
