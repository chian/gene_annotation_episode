# 004 — `literature_strategy__next_decision` — revision 002

```text
TASK

Investigate which literature search approach can obtain useful information for the assigned scientific question. Own the iterative choice of search terms, provider and search scope, revising your approach from actual outcomes. Productive searching means finding information that can distinguish the relevant explanations or expose a material limitation; a large hit count alone does not establish productivity.

Information objective: {assigned_information_objective_in_full}
Parent's intended use of your result: {requested_report_purpose_in_full}
Fixed target: {biological_target_name_organism_and_known_public_identifiers}
Assigned scientific scope: {assigned_scope_in_full}
Binding constraints: {parent_and_caller_constraints_in_full}

Explicitly supplied starting facts
| Subject or issue | Supplied fact | Conditions and qualification |
| --- | --- | --- |
{explicitly_supplied_starting_fact_rows_or_none}

The information objective describes what you need to learn. A literal provider query is one attempted expression of that objective, with its own syntax, fields, filters and coverage. Keep the two separate. An unproductive query can justify changing the expression without changing the assigned question.

Use biological names, established aliases, locus or protein accessions, family/domain terms, candidate functions and relevant experimental terminology where they help formulate the search. Distinguish established synonyms from terms proposed for searching. Preserve the actual organism, assayed protein or construct, substrate, phenotype and conditions when those distinctions affect relevance. Searching for a reference protein's activity does not make that protein the annotation target or transfer its assay result to the target. Different candidate annotations concern this same fixed target; historical revisions of one annotation are not additional candidates.

Consider what alternative vocabulary, identifier, provider or scope could retrieve the missing distinction. A narrow organism or exact-name query can miss older terminology or evidence on related subjects; a broad family term can retrieve many studies that do not distinguish the target's specific activity. Provider coverage, field syntax, filters and pagination can also explain a result. Use actual outcomes to decide whether to retain, revise or replace the approach; no particular sequence of changes is required.

Interpret search outcomes within their actual coverage. Distinguish a successful empty page, an exhausted reported result set, an unexamined later page, an inaccessible article and a failed request. None alone proves scientific absence. Titles and snippets identify possible sources; they do not establish the underlying biological claim or its applicability. A known source's qualifications or a useful negative finding can change the next search even when it weakens an annotation claim. Do not infer unseen contents from source registration or delivery.

A single selected search, acquisition or read is an ordinary tool action. When evaluating which returned sources deserve examination warrants an iterative investigation, you may commission a literature_search child. Give it the selected question, narrower scope, constraints, explicitly supplied facts and the parent's requested typed return meanings. It owns its source-selection decisions. Do not transfer your private history, yields or source access to it, and do not count its internal actions as your own observations. Its requested admitted result can inform your next strategy decision.

Available work
| Choice | Available operation or child | Operands and binding limits |
| --- | --- | --- |
{actual_available_tool_reason_child_wait_and_repair_rows}

Choose among the available actions using this assignment, actual received outcomes and your own yield information. A search/read, an evidence-based reasoning commitment or an iterative search child may be useful; selected waiting or repair may matter when actual pending work or feedback warrants it. No action order, search quota, polling cadence or complete-document requirement is prescribed. Duration expectations inform the choice when available. The configured controller owns continuation.

Parent's requested result
| Field | Type | Allowed values and substantive meaning | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_parent_requested_return_field_meanings}

Return only that parent's declared information through the existing typed contract. Interpretations must express what your received evidence actually supports, including remaining uncertainty and material limitations. Recorded facts come from the host. In report_update, retain or revise only the declared interpretation fields using information received before the selected action; an action you are about to select has no interpreted outcome yet. Preserve valid partial work. A controller yield does not establish scientific completion.

Use the supplied typed JSON response contract unchanged. If necessary, request earlier own inputs through the declared request_context exchange, then continue this same decision with the complete TASK. When ready, return selection and report_update in that contract. The host executes the selected action.

Yield-table meanings: observed totals are this episode's saved signed completed-action gains, excluding its starting baseline. Expected next category yield is conditional on completing that category again. Its band is an approximate working-model uncertainty, not a calibrated outcome guarantee; unavailable is not zero. Acquisition can have zero immediate credit before a later interpretation. Yield is distinct from annotation support and execution duration.

STEERING

| Own action category | Completed | Total yield | Expected next yield | Uncertainty / unavailable reason |
| --- | --- | --- | --- | --- |
{own_category_rows_or_no_completed_observations}

| Own attempt | Exact provider query, filters and page / assigned child question | Actual outcome | Qualification |
| --- | --- | --- | --- |
{only_next_decision_relevant_own_attempt_rows_or_none}

| Received lead or current interpretation | Relevant subject and conditions | What it adds or limits |
| --- | --- | --- |
{only_next_decision_relevant_received_lead_rows_or_none}

| Requested interpretation field | Current admitted value | Basis limitation |
| --- | --- | --- |
{current_requested_interpretation_rows_or_none}

{pending_table_only_if_relevant}
{timing_table_only_if_relevant}
{actionable_feedback_table_only_if_present}
```

Optional headers are `Pending own work | Assigned question | Actual state / received progress`; `Proposed work or wait | Existing duration / wait expectation | Support / unknowns`; and `Attempt or delivery | Actual failure | Affected operand / retained partial work`. They contain factual rows, never narrative recaps. Unknown values remain unknown.

The complete TASK is rendered on every iteration, after each internal lookup and after reconstruction. STEERING is built separately; its brevity never reduces TASK. This draft remains for the user's running feedback and is not settled or implemented.

Brief source and fill notes:

- The assignment, scope and requested result meanings come from the original request, `literature_assignment`, `requested_report_purpose` and `requested_form`. Starting facts must be explicitly selected as supplied information. A host validation reference or parent's source access does not deliver knowledge.
- `LiteratureEpisodes.instructions`, its complete strategy/search binding, catalog and child relationship supply the role distinction and available operations. Runtime `DecisionSource` supplies actual received state/forms; `interpretation_schema` keeps host-filled facts outside model-authored report updates.
- `action_yields.rows` already supplies own category totals, expectations and original uncertainty. Exact own query operands come from saved selected actions; results must come from that same episode's recorded outcomes or admitted requested child returns. `own_literature_outcomes` alone is only an index, and current `own_attempt_detail` retrieves selected inputs rather than outcome bodies.
- Text rendering must keep host IDs, hashes and frame/version/configuration tracking internal. Readable operand resolution remains an implementation dependency because current ordinary tools require persistent references. Keep durable identities, the existing JSON response schema and typed parent forms unchanged.
- Read `docs/TASK_AND_STEERING.md` and the replacement AGENTS.md appendix for this correction. Original draft preserved. No application code, tests, network, model calls, process configuration or scientific run changed.
