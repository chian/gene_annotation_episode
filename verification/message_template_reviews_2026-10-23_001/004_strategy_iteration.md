# 004 — `literature_strategy__next_decision`

Draft for human steering. This is one strategy episode's internal next decision: **which search approach is productive?** It does not take over the search child's question of which returned papers deserve examination. Nothing below is implemented.

## Complete proposed model input

```text
You are investigating which literature search approach is productive for this assignment. Keep the information sought separate from the literal provider query. Revise terms, provider choices or search scope from actual outcomes. A single search/read is a tool action; a search child can investigate which returned sources merit examination. No search sequence or reading quota is prescribed.

Information sought: {assigned_information_objective}
Parent needs this result for: {requested_report_purpose}
Fixed annotation target: {target_name_and_organism_with_known_identifiers}
Assigned scope and constraints: {assigned_scope_and_constraints}

Relevant scientific context
| Issue or candidate interpretation | Known target/source subject and conditions | Evidence or limitation relevant to formulating a query |
| --- | --- | --- |
{relevant_scientific_context_rows_or_explicit_none}

All candidate annotations above concern the same fixed target. Source proteins, organisms and experiments retain their own identities. A newer annotation revision does not create a new target.

Your own previous approaches and actual outcomes
| Own attempt | Approach or assigned search-child question | Provider and exact query, filters and page | Actual outcome or admitted child return | What is still unknown |
| --- | --- | --- | --- | --- |
{own_attempt_rows_or_no_prior_attempts}

Relevant known search/source information
| Search or source | Title/topic and available publication identifiers | Actual search/read outcome or source conditions | Why it bears on the next approach |
| --- | --- | --- | --- |
{decision_relevant_source_rows_or_explicit_none}

Titles and search summaries are discovery information. A failed search, an empty returned page or an unread source does not establish biological absence. Source delivery alone does not establish understanding.

Your own action yields
| Action category | Completed own actions | Observed total yield | Expected yield if completed again | Uncertainty or unavailable reason | Attempts without a completed observation |
| --- | --- | --- | --- | --- | --- |
{own_action_yield_rows_or_no_observations}

These are this episode's saved signed gains, excluding inherited credit. Category expectations are approximate working-model bands conditional on completing that category again; unavailable does not mean zero. Acquisition can earn zero immediate credit before interpretation. These values do not measure a parent's or child's private history, biological truth or duration. The configured controller owns continuation.

{pending_work_and_relevant_timing_table_if_any}

Available choices
| Choice | Available operation or child | Required operands and constraints |
| --- | --- | --- |
{available_choice_rows}

Parent's requested return
| Field | Declared type and allowed meaning/values | Current admitted value | Basis or recorded-fact source |
| --- | --- | --- | --- |
{requested_return_field_rows}

{actual_feedback_if_any}

Choose the next useful action for the information sought. Use the supplied structured response contract unchanged. If earlier own inputs are needed, request that context through the declared request_context exchange and continue this same decision. When selecting work, return selection and report_update in that contract. Update only the parent's declared interpretation fields, using evidence already received before the selected action; recorded fact fields come from the host. Preserve valid partial work, negative findings and uncertainty. The host executes the selected action.
```

The optional pending-work block has the headers `Own commissioned work | Assigned question | Actual state and received return/progress | Relevant duration/wait expectation and its support`. It appears only when such information can change this decision. All other tables are present with an explicit empty state when no rows exist. An absent or unmeasured value is printed as unknown, never fabricated.

## Producer → presentation → consumer fill map

| Template input | Exact existing producer or record | Presentation and decision use |
| --- | --- | --- |
| Assigned information objective | `DecisionSource.next`: `goal = self.request.goal.as_record()`; `literature_assignment.question_context_refs` from `LiteratureEpisodes.decision_context` | Copy the assigned question in plain text. Resolve the supplied context references to actual known records; a reference alone is not a usable question. Keep the objective separate from query syntax. Do not import the parent's private decision history. |
| Requested purpose | `DecisionSource.next.requested_report_purpose`, from the original `report_contract.decision` | Copy the parent's actual requested distinction; do not generate a new assignment. |
| Target, scope and constraints | `DecisionSource.next.scope`, `working_state`; `Workflow.working_state` → `Store.reasoning_view`, especially `subjects`, `features`, `products`, `contexts`, and assigned question records | Render the fixed biological entity, organism, actual known locus/accession names, relevant coordinate restriction and explicit assignment constraints. GOAL.md identifies this case as E. coli K-12 MG1655 ybhP/b0790/P0AAW1; production must obtain these from actual supplied records, not insert GOAL.md as invented episode evidence. Multiple interpretations/revisions remain attached to this one target. |
| Scientific context rows | Existing received `working_state.hypotheses`, `assessments`, `observations`, `annotations`, `terms`, `contexts`, and records selected by `question_context_refs` | Project only distinctions, synonyms, source subjects and conditions that affect search formulation. Distinguish a target hypothesis from a source claim and preserve the qualification. Retain original delivered record versions internally; do not substitute unseen revisions. |
| Own prior approaches and exact queries | `runtime_actions.action`, scoped by current run and episode. `decision_history._record` exposes selected `inputs`; `_lookup_detail` can recover exact selected input fields. For tool searches: `arguments.query` or `arguments.term`, database, size, cursor/offset. For a child: selected `goal`, `purpose`, `assignment` | Render actual operands, not a generated description of what a query probably was. Child commissions show the strategy's assigned question; the child's private queries are unavailable unless its admitted requested form actually returns them. A prior approach label can use recorded assignment/reasoning text only; otherwise leave that interpretation unstated. |
| Outcomes paired with own attempts | `runtime_actions.result`; latest result through `DecisionSource.next.last_local_outcome`; completed direct-child forms from the ordinary admitted-return path (`view.child_reports`); `LiteratureEpisodes.decision_context.own_literature_outcomes` calls `WorkflowServices.own_outcomes` | Pair the exact action with its actual status, returned page/count/pagination fields where actually supplied, structured failure and requested typed child result. `own_literature_outcomes` is a useful owner-scoped index but **only metadata**: it omits selected queries, outcome bodies and child actions. Do not treat it as complete prior strategy history. |
| Known result/source descriptors | Supplied `prior_search_refs`; existing received source records; native search response in acquisition outcome `result.provider_result`; source metadata and admitted source-bound observations | Render provider-returned titles/topic descriptors, public PMID/PMCID/DOI and actual query coverage or known source conditions only when they affect the search approach. The search importer retains native provider structure instead of imposing a universal hit schema. Preserve that distinction and unknown counts. No complete article body is needed here. |
| Own action-yield table | `DecisionSource.exchange_decision` → `yield_table(journal, current episode, before=current decision, parameters=bound category parameters)` → `model_snapshot(...).action_yields.rows` | Reuse `category`, `completed_actions`, `total_yield`, `expected_yield.status/unavailable_reason/band`, and `attempted_uncompleted`. Display point/lower/upper only for a usable band, with original uncertainty meaning. Keep the signed totals and completed-occurrence semantics unchanged. No gain/time conversion, rescaling or new score. |
| Pending work and timing, when relevant | `DecisionSource.next.pending_work`; `DecisionSource.call.waiting_support`, `resource_tool_estimates` and original duration snapshots when actually bound | Render only this episode's real commissions, exposed states and relevant existing estimates. Preserve measured-duration meaning and missingness. No timing estimate selects an action or prescribes a wait. Do not invent timing for literature search services merely because XLSX estimation exists. |
| Available choices and operands | `LiteratureEpisodes.permitted_common_actions`, `catalog`, `_CHILDREN['literature_strategy']`; `Workflow.catalog` and `action_schema` | Show available direct searches/reads/state access, reasoning, a `literature_search` child, selected waiting and repair only as actually available. `public.ncbi.search` is restricted here to PubMed. A search child's assignment has question-context and search-result references. Render operand names/types/ranges as text/table cells; keep the original output schema and actual capability checks. No automatic child order. |
| Requested return table | `requested_form`, `current_report_update`, `current_report_basis_refs`, `available_report_facts`; `interpretation_schema` strips top-level `x-source` fields from model-authored updates | Recursively render the parent's actual field paths, types, enum/const/semantic-format restrictions, meanings and current values. Mark host-filled facts explicitly. There is no universal hardcoded strategy report. Consumer remains `DecisionSource.apply_response` → `validate_form`, `Workflow.validate_report` and `LiteratureEpisodes.validate_report`; fact publication remains host-owned. |
| Feedback | `DecisionSource.next.feedback`, report-delivery status or structured actual action failure | Include the exact actionable error and affected semantic operand; no model call to restate it, and no implication that an attempted failed operation supplied a completed observation. |

The presentation consumer is currently `_SessionConnection.complete`: it sends `json.dumps(context)` as the turn's text. In exchange mode `DecisionSource.exchange_decision` supplies `state_frame(model_snapshot(...))`, while `outputSchema` independently carries the closed response schema. A future renderer for **this template only** would replace that model-facing text with the draft above; durable raw context, state-frame reconstruction, numerical inputs and the structured response schema remain unchanged.

## Explicit gaps to settle before implementation

1. The current exchange lookup's `own_attempt_detail` can recover **selected inputs only**. `_record.outcome_summary` is a fingerprint and durable locator, not a readable outcome. A current-run/current-episode projection of actual saved outcomes and admitted forms is needed to fill the paired outcome column without a new scientific operation or a generated summary. Do not tell this model that the existing lookup already supplies those bodies.
2. `literature_assignment` holds reference arrays; `literature_source_custody` is empty for a strategy assignment because this role has neither `source_refs` nor a page. Resolve `question_context_refs`/`prior_search_refs` into actual decision-relevant descriptors. Raw arrays alone do not supply the scientific question or search results.
3. The current interface requires persistent opaque reference operands (`domain.REF`; ordinary tools reject reasoning aliases). Removing those IDs from text requires a durable, reversible mapping between readable operands and the original references at the presentation boundary. That mapping is not present in this path. The schema's structure/types and recorded identities must stay unchanged; do not silently pass invented names to current validators. This is an implementation dependency, not a proposed new response format.
4. Bootstrap/update revision hashes, raw schema dictionaries and restoration envelopes are internal. A renderer must reconstruct the authoritative current state before rendering this complete text and preserve already answered own-context exchanges. Reprinting a partial delta as though it were a complete prompt would lose required context.

## Deliberate omissions

- Parent action history/yields, child-private history and model reasoning: wrong owner. Only admitted requested child returns belong here.
- Full source articles, raw provider payload dumps and unrelated scientific records: do not decide which search approach to try. Retain source descriptors and known relevant conditions; source examination remains available work.
- Hashes, opaque durable IDs, version/revision/configuration records and binding manifests: preserve internally for identity, replay and validation. Biological public accessions and exact literal queries remain visible because they formulate searches.
- Full controller histories, fit diagnostics and annotation-support formulas: the existing own-category table provides the required next-action information without changing numerical continuation. Annotation support is distinct from investigation progress and does not need a second scoring table for this strategy decision.
- Hypothetical result counts, inferred query synonyms, invented strategy-success classifications and invented duration/probability estimates: no corresponding recorded fact. Unknown remains unknown.

Read-only inspection covered AGENTS.md, GOAL.md, docs/EPISODE_STRUCTURE.md, docs/TIME_AWARE_ESTIMATION.md, the complete literature binding, relevant complete runtime decision/exchange/action/report paths, own-attempt and category-yield projection, source import/catalog and model transport. No code, tests, network, model calls, running investigation or process configuration changed.
