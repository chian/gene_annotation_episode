# Proposed text prompt: `literature__next_decision`

This is one internal decision of the top literature episode. Braced names below are named fill placeholders; table bodies contain actual received records, never a model-written recap. Conditional blocks appear only when relevant. Human-readable handles resolve to the original records outside the model prompt.

```text
You own an iterative literature investigation. Choose the next work that can clarify your assigned scientific question, using what this episode has actually learned.

The scientific parent's goal is: {parent_scientific_objective}
Your literature question is: {assigned_literature_question}
The parent needs this information for: {requested_report_purpose}
Your fixed target and scope are: {target_identity_and_scope}
The binding constraints are: {parent_constraints_relevant_to_this_decision}

Decide which distinction in this question is worth pursuing now. Consider whether a different search approach, examination of a particular source, or interpretation of evidence already received could change that distinction. A source's subject, construct, organism and conditions may limit its relevance to the target. A useful qualification or negative finding can advance this investigation.

The relevant information already received is:

| Question or competing explanation | Recorded proposition or received interpretation | Actual source subject and conditions | Recorded qualification or unresolved distinction | Source/basis handle |
| --- | --- | --- | --- | --- |
{relevant_received_scientific_rows}

Your relevant prior attempts and returned strategy work are:

| Own attempt | Exact selected query, source selection or strategy question | Actual outcome or admitted strategy-return fields | Status and access limitations | Source/outcome handle |
| --- | --- | --- | --- | --- |
{relevant_own_attempt_and_strategy_return_rows}

Search results establish discovery. A delivered source does not establish that its contents were read or understood. Distinguish an unsuccessful search, unavailable access and a source-grounded negative result. Use the actual queries and returned distinctions when considering a revised strategy.

These are this episode's OWN action-category observations:

| Action category | Completed own actions | Total signed yield | Expected next completed-action yield: lower / central / upper | Availability or uncertainty | Attempts without completed observations |
| --- | --- | --- | --- | --- | --- |
{own_action_yield_rows}

Total yield excludes inherited credit. Expectations are conditional on completing that category again; unavailable is unknown, not zero. Bands are approximate working-model uncertainty, not calibrated guarantees. Acquisition may earn zero immediate progress before interpretation. The configured controller owns continuation.

{if_relevant_pending_work_block:
Outstanding work and information relevant to considering a wait:

| Commissioned strategy question | State and observation time | Progress actually returned | Original duration expectation and support | Supported wait estimate or unknown |
| --- | --- | --- | --- | --- |
{relevant_pending_strategy_rows}
}

{if_relevant_execution_expectation_block:
Execution expectations for a currently plausible operation:

| Operation and meaningful workload operands | Expected duration and measured interval | Complete / lower-bound / unmeasured support; observed range | Availability or limitation |
| --- | --- | --- | --- |
{relevant_execution_expectation_rows}
}

Your parent-defined return fields are:

| Field | Type and allowed values/reference kind | Parent's declared meaning | Current interpretation and its actual basis | Filled by you or recorded by the runtime |
| --- | --- | --- | --- | --- |
{parent_return_field_rows}

Update only your declared interpretation fields from evidence already available before the next action. Parent-supplied initial values are not your new judgment. Runtime fact fields report actual records; a subsequent tool result does not become a new interpretation automatically.

The useful available choices for this decision are:

| Choice | Available operation or child kind | Required meaningful operands | Information returned or committed; relevant limit |
| --- | --- | --- | --- |
{small_relevant_action_menu}

You may search/read directly. Commission a literature strategy child only for a narrower search-approach question that warrants iteration; supply its goal, contained scope, context/prior-search handles, constraints, and the typed return fields needed for your later decision. A one-off lookup is a tool action. The strategy child owns its choices; no child order or reading quota is prescribed.

Commit source-grounded scientific interpretations through the reasoning action, preserving exact source anchors and applicability to the fixed target. Keep source assertions separate from target inferences. Repeated discovery, delivery or reading does not create a new finding by itself. Annotation support, scientific progress, timing information and duration expectations retain separate meanings.

{if_relevant_repair_feedback: Actual failed action or report-delivery feedback: {failure_code_affected_operands_and_preserved_partial_work}}

Choose one action using the bound response form: select_action with selection and report_update. If exact details of your own earlier received attempts are needed first, use request_context with the declared lookup operands; that lookup continues this same decision and creates no action observation. Available lookup forms: {readable_own_history_lookup_fields_and_allowed_values}. Use the supplied readable handles; do not invent records or expose private child histories. The host executes the selected action.
```

## Exact decision and source mapping

The receiver decides the next useful literature action within its scientific assignment. It does not decide the scientific parent's broader priorities, inspect strategy/search/page private work, or follow a mandatory literature itinerary.

| Prompt fact | Actual producer and presentation requirement | Consumer and reason |
| --- | --- | --- |
| Parent goal versus own question/scope | `Workflow.build` stores each immutable `runtime_episodes.request`; `EpisodeGoal.child` preserves `task_context.root_objective`. Read only the immediate parent's objective metadata for `parent_scientific_objective`, and use this receiver's `goal.objective` and validated scope. The current child context does not separately expose its immediate parent's objective. | Establishes why the literature question matters without importing the parent's decisions or yield history. |
| Scientific distinctions and source meaning | `Workflow.working_state` → scoped `store.reasoning_view`; the assignment's `question_context_refs` and `source_refs`; actual source/observation/hypothesis/assessment/interpretation-account records; last received source windows and admitted direct-child forms. Use recorded text/typed values, exact anchors and existing qualifications. Do not generate missing interpretations. | Allows the literature owner to choose a discriminating investigation and avoid transferring an assay to the wrong subject. |
| Specific prior strategies and outcomes | This receiver's `runtime_actions.action` contains literal search operands or the commissioned strategy goal/purpose/assignment. Saved outcomes contain actual results; `EpisodeView.child_reports` supplies only admitted direct-child forms. `WorkflowServices.own_outcomes` currently supplies the first paged tool metadata, without selected queries, source contents or strategy returns; it is an index, not sufficient scientific context. `decision_history` own lookups expose saved selected inputs and published references. | Distinguishes a new approach from repeating the same search and gives the parent literature episode the strategy's requested scientific contribution. No child-private trajectory is loaded. |
| Own action yields | `decision_history.category_for` and `yield_table` join the receiver's saved selections to its original `runtime_observations`/completion identities. `DecisionSource.exchange_decision` builds the table; `model_snapshot` supplies it. Render existing signed totals, count, band/status and uncompleted attempts. | Supports choosing among this receiver's action categories. Neither parent yields nor child internal turns become its observations. |
| Pending work/time facts, only if useful | `Workflow.pending_work`, `waiting_support`, actually received progress, saved `resource_tool_estimates`/`native_execution_expectations`, and an actual returned wait estimate. Render original intervals/support and unknowns; do not infer a probability, wait gain or stall. | Makes an optional selected wait or costly source operation assessable. No arbitrary timer or action recommendation is introduced. |
| Requested return meanings and current basis | `request.report_contract.decision/schema`, `report_values`, `report_basis`, `interpretation_schema`, `FACT_MEANINGS`, and declared `x-source` bindings. `LiteratureEpisodes.fact_sources/facts` add no literature-specific fields; shared facts come from `Workflow.facts`. Render actual required fields, nested type/cardinality constraints, allowed values and meanings rather than install example fields. | `apply_response` validates/records the interpretation update; `finish` binds recorded facts and validates the original parent form. This keeps received information, committed contribution and return meaning aligned without a composer call. |
| Permitted action/operands | Complete `LiteratureEpisodes.assignment_schema`, `instructions`, `decision_context`, `catalog`, `_tool_arguments`, `execute` and report/credit methods inspected. Top-level literature allows direct acquisition/access tools; its only declared child is `literature_strategy`. `Workflow.catalog/action_schema` add shared reasoning/wait/repair and protocol lookup. Render a small relevant subset with a discover-more choice when supported, while retaining actual eligibility and dispatch validation. | `apply_response`/`selected` route the one selected action to existing tool/reason/commission/wait/repair consumers; source custody and scope validation remain authoritative. |

The existing next-decision assembly is `DecisionSource.next` → `call` → `exchange_decision` → provider. The proposed renderer belongs at that model-presentation boundary. Durable JSON, original snapshots, semantic reference validation and the machine response contract remain internal; readable handles need a deterministic, scope-checked mapping back to existing operands. A closed response schema does not justify sending the entire schema/context as the prompt.

## Deliberate omissions and limits

Omit run/episode/goal IDs, hashes, revision/version labels, implementation pins, full source-custody records, generic launch-library/configuration dumps and full tool manuals: none chooses the next literature investigation. Keep biological accessions, exact query terms, relevant source provenance, representation and quote/byte anchors when they distinguish evidence or enable the selected operation. A source's publication/version identity remains evidence provenance even though internal version tags do not.

Omit parent yield/controller history, private strategy/search/page histories, inherited gains as new yield, and child numeric scores that do not answer the requested scientific question. Show a separate annotation-support value only if the particular decision needs it; do not combine it with action yield. Show pending/time/resource details only when they change a live comparison.

This is a proposed text template, not an implemented renderer. No application edits, network requests, model calls, scientific runs or tests were performed. Read-only inspection covered the required project documents, the complete literature binding and relevant shared decision, source, action, history, return/fact and continuation-input consumers. Immediate-parent objective projection, meaningful reference labels, relevant-record selection and prior-outcome presentation still require implementation after human steering; none is claimed already present.
