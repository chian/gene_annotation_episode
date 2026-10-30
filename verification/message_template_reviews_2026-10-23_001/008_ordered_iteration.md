# Proposed text prompt: `literature_ordered__next_decision`

This is one decision inside the ordered-reading episode. Every iteration receives two distinct blocks. TASK supplies the detailed assignment and instructions needed to do the investigation. STEERING supplies only concise facts needed for the current choice. Braces name fill slots; table headers show their presentation. Facts come from actual records already received by this episode. The host retains exact identities and scope-checked operand mappings internally. This proposal does not change the bound JSON response contract.

```text
TASK — supplied in full every iteration

Investigate this scientific question through useful reading of the assigned
source in document order: {assigned_question}

The page parent needs your result for: {parent_return_purpose}
Your fixed target and scope: {target_identity_and_scope}
Your binding constraints: {parent_constraints}

Assigned source and starting context:

| Source | Supplied representation and what it contains | Starting byte offset / requested limit | Relevant access or representation limits |
| --- | --- | --- | --- |
{assigned_source_row}

You own the investigation within that question. Use each actual reading outcome
to decide whether the useful next work is to continue, reread, change the examined
window, examine a qualification or comparison, or interpret evidence already
obtained. The assigned starting window supplies an initial point of attention;
it has not been executed merely by being supplied. No complete-document
requirement, reading quota or compulsory sequence applies. Your available work
consists of ordinary source operations and scientific reasoning within the
shared episode loop.

Read for the distinction the parent is trying to resolve. Determine which actual
subject, organism and construct each relevant statement concerns, what was
measured or reported, under which conditions, and which comparison or control
supports its interpretation. Preserve separate observations when constructs,
conditions or outcomes differ. Methods, results, controls and qualifications
may clarify each other; choose their examination from the question and actual
outcomes. A title, source delivery or copied annotation label does not establish
the biological claim. A source's assay on another protein does not become an
assay on the fixed target. Keep its reported proposition separate from your
reasoned judgment of applicability to this target and competing explanations.

Use source structure and obtained evidence to revise what context is useful.
Keep the exact representation of each passage. A text projection may omit XML
headings, tables and footnotes; relevant retained original bytes remain available.
Do not combine separate source spans into a fabricated quotation. If choosing
source.read, name the actual source and representation and select a valid UTF-8
byte offset with a positive byte limit. A continuation returned by the prior
read enables exact continuation; it is not an instruction to take that action.
The actual end may differ from requested offset plus limit because a UTF-8
character cannot be split. Rereading or changing the window is an explicit
selection, and a text fallback must retain the representation actually returned.

Only actual returned ranges establish what bytes this episode received. Delivery
history does not establish reading or understanding, and a gap between ranges
stays unexamined. End of one representation does not establish absence in the
paper. Distinguish a source-reported negative result, data not shown, an access
failure and a passage not yet examined. Preserve partial reads and useful
qualifications instead of filling unknowns. Repeated reading or navigation
coverage alone is not a new scientific finding.

Commit scientific interpretation through the reasoning action. Ground extracted
subjects, conditions and observations in actual source text with exact source,
artifact byte span and quotation. Retain uncertainty, assumptions, alternatives,
corrections and limitations on transfer. Source-grounded negative findings and
qualifications can advance the investigation. Scientific progress and annotation
support remain separate quantities; a useful correction may lower support.

The parent's original return contract is:

| Field | Required type, allowed values and reference kind | Parent's declared meaning | Filled by your interpretation or by recorded facts |
| --- | --- | --- | --- |
{parent_return_contract_rows}

Update only these declared interpretation fields from evidence already available
before the selected next action. Parent-supplied initial values are not your new
judgment. Retain the actual basis of each interpretation; a later tool result
does not automatically revise it. Runtime fact fields report actual recorded
work. Preserve valid partial findings and unresolved distinctions in the allowed
form, without inventing findings prose or adding a report-composition step.

Select one action through the existing bound response form, with selection and
report_update. For needed own earlier selected inputs, request_context uses
these declared lookup fields and values: {readable_own_lookup_contract}. It
continues this same decision without a completed-action observation. Use only
supplied meaningful labels that resolve to actual records. The host executes
the action and validates the original response and return contracts.

Your yield table describes OWN completed action categories. Totals exclude
inherited credit. Expectations condition on completing that category again;
unavailable is unknown, not zero. Bands express approximate working-model
uncertainty, not calibrated guarantees. Reading may earn zero immediate progress
before interpretation. The configured controller owns continuation; document
coverage and apparent question resolution introduce no new stopping rule.

STEERING — current facts only

| Current distinction still unresolved | Recorded basis or unknown |
| --- | --- |
{current_question_distinction_rows}

| Own read | Source and actual representation returned | Returned UTF-8 byte range [start, end) / total bytes | Returned continuation, or end of this representation | Actual outcome or access limitation |
| --- | --- | --- | --- | --- |
{actual_read_window_rows}

| Currently needed passage already obtained | Actual source, representation and byte range | Literal text, escaped only for Markdown display; or no passage obtained |
| --- | --- | --- |
{current_needed_passage_rows}

| Provenance: supplied context or own contribution | Source proposition or recorded interpretation | Actual subject, organism and construct | Conditions, comparison/control and measured result | Qualification, negative finding or unresolved distinction | Exact source/basis label and anchors |
| --- | --- | --- | --- | --- | --- |
{relevant_scientific_evidence_rows}

| Action category | Completed own actions | Total signed yield | Expected next completed-action yield: lower / central / upper | Availability and uncertainty | Attempts without a completed observation |
| --- | --- | --- | --- | --- | --- |
{own_category_yield_rows}

| Return interpretation field | Current admitted value | Actual basis; or parent-supplied initial value |
| --- | --- | --- |
{current_return_interpretation_rows}

| Choice | Bound operation | Required meaningful operands | Information returned/committed and relevant limit |
| --- | --- | --- | --- |
{small_relevant_action_menu}

{if_relevant_failure_block:
| Failed attempt | Recorded failure | Affected operands | Preserved partial work |
| --- | --- | --- | --- |
{recorded_failure_rows}
}

{if_relevant_timing_block:
| Plausible operation | Expected duration and measured interval | Actual statistical support and range | Unknowns or limitations |
| --- | --- | --- | --- |
{relevant_execution_expectation_rows}
}
```

## Receiver, facts and consumers

The receiver decides the next action within its assigned scientific reading question. The page parent chooses the source, relevant question context, initial window, constraints and requested return meanings. The ordered reader owns later choices and scientific interpretation. It has no declared child roles (`_CHILDREN['literature_ordered']` is empty); a read is an ordinary tool action. No new child, traversal order or stopping condition is proposed.

| Fill slot / fact | Actual source and presentation rule | Consumer / why needed |
| --- | --- | --- |
| TASK: `assigned_question`, `parent_return_purpose`, `target_identity_and_scope`, `parent_constraints` | `DecisionSource.request.goal`, validated `scope`, immutable `episode_assignment`, `request.report_contract.decision`, and source-linked records named in `page.question_context_refs`. Render actual question and target context, not raw goal/scope identifiers. Read only relevant supplied constraints. The detailed role/process instructions remain present every iteration. | Distinguishes the scientific question from the mechanical starting window; gives the reader the task itself, including how source meaning, conditions and qualified inference bear on it. |
| `assigned_source_row` | Complete `LiteratureEpisodes.assignment_schema`, `_validate_assignment`, `_validate_page` and `_artifact`: reading assignment contains `page` plus `selection={source_ref, representation, offset, limit}`. `_PAGE` binds source, representation/artifact, question context and prior deliveries. Source records supply actual accession/URI/provider and retained representations. Show the title/public accession when actually known; otherwise identify the source by its actual available provenance, without invented metadata. | `_tool_arguments` and `_within_source` enforce the assigned source lineage; initial selection is not autoexecuted. Requested representation may differ from the representation actually returned by a text fallback. Internal artifact identity remains exact without printing hashes. |
| STEERING: `current_question_distinction_rows`, `actual_read_window_rows`, `current_needed_passage_rows` | Use only recorded current hypotheses/return interpretations to name an unresolved distinction, otherwise mark it unknown. `runtime_actions.action/result` contains this receiver's completed/partial reading work; current `last_local_outcome.result` contains its latest result. `Tools._perform('source.read')` delegates to complete `materials.source_window`. Its authoritative output is `source_ref`, `artifact_ref`, `start`, `end`, `text`, `total_bytes`, actual `representation`, availability and `next_offset/next_query`. Render concise exact measured ranges and separately mark failed attempts. Insert only the presently useful literal returned passage. | Later reading uses actual UTF-8 continuation and actual representation, rather than requested limit arithmetic. `source_window` validates bounds/start boundaries, trims incomplete trailing UTF-8 characters, and returns a nullable continuation. The same exact artifact/span/quote grounds a later reasoning commit. No fetched full article is inserted just because it was assigned. |
| `relevant_scientific_evidence_rows` | `Workflow.working_state` → `Store.reasoning_view` and explicit supplied question-context records; actual terms/source subjects/contexts/observations/hypotheses/assessments/accounts and exact read windows. Preserve the record's source proposition, measurements, `condition_refs`, `assumption_refs`, applicability and investigation-finding qualification. Separate inherited context from new own work. Show absence of records as unknown, never compose an interpretation in a presentation call. | `DecisionSource.apply_response` admits a selected reasoning action; `execute` commits through `Store.commit_reasoning`, preserving independent valid rows on partial failure. Source and target subjects and assay controls constrain the scientific inference. A current source body is not evidence of an already committed interpretation. |
| `own_category_yield_rows` | `decision_history.category_for/yield_table` join this episode's own saved selections to original signed marginal observations and completion identities. `DecisionSource.exchange_decision` → `model_snapshot` exposes category counts, `total_yield`, expected band/status and uncompleted attempts. Render original values without smoothing. A category not observed has no learned estimate. | Supports comparing this episode's own read/reason/access alternatives. Category fits explicitly have `controller_effect='none'`; actual completed action goes through recorded outcome → `source_credit_view` → `controller_value`/completion → configured controller. Parent yield, child-private work and inherited credit are not observations. |
| TASK: `parent_return_contract_rows`; STEERING: `current_return_interpretation_rows` | Original `request.report_contract.schema/decision`, `interpretation_schema`, `report_values/report_basis`, declared field descriptions, allowed values and `x-source` meanings. Shared `FACT_MEANINGS` supplies only requested recorded facts; literature adds no specialized fact fields. TASK expands the original nested restrictions and meanings legibly. STEERING gives only current admitted values and their actual basis or initial-value status. | `apply_response` validates/adopts interpretation values before action results; `finish` binds actual facts via `form_with_facts`; original admission uses the parent's schema and meaningful-reference checks. This avoids model-generated recorded facts or a second report composer. |
| Action menu / lookup / feedback | Complete literature `catalog`, `_tool_arguments`, `execute`, report and credit methods; `Workflow.catalog/action_schema/selected/execute`; actual failed outcome/feedback. Ordered reading permits source access but no acquisition search tools and no children. Relevant operations may include source.read, exact state.query, PDF access, reasoning, or a supported repair. Display only needed operand meanings, with more bound capabilities discoverable through the existing supported interface. | Retains source-lineage/schema enforcement and selectable repair while making the immediate alternatives readable. The typed response contract remains unchanged. No operation or lookup can be invented by the renderer. |
| Optional timing rows | Only actual `resource_tool_estimates/native_execution_expectations` relevant to a plausible available operation, with original measured interval/support. Literature `execution.estimate` only includes XLSX operations. Ordinary source.read has no inferred duration model. | Can inform a costly access choice without adding gain/time scoring, a wait cadence, or unsupported extrapolation. Omit when it does not bear on this reading decision. |

## Omissions and concrete gaps

Omit opaque run/episode/goal/record IDs, hash/revision/custody/configuration dumps, implementation pins, generic resource/launch instructions, parent yield history and private episodes' histories. Keep a publication's substantive edition/status only when it distinguishes evidence; keep biological accessions, source/representation labels and byte positions when needed for source selection or exact evidence anchors. A deterministic, scope-checked readable-label mapping must resolve response operands back to existing references without changing the response schema. It is proposed work, not present behavior.

The current presentation does not yet supply this template. `LiteratureEpisodes.decision_context` sends the assignment/custody objects and the first page of `own_literature_outcomes`. `WorkflowServices.own_outcomes` exposes tool/status/reference metadata only, with a default eight records; it supplies neither read ranges nor passage contents. It is not an examination ledger, and `prior_delivery_refs` explicitly proves neither coverage nor understanding. `DecisionSource.next` does supply the latest full ordinary source.read outcome, because `local_outcome_preview` only clips declared native publication batches.

An additional concrete limitation matters for this receiver: under `decision_exchange_v1`, `episode.history` is removed, while `decision_history.lookup_attempts` exposes selected inputs and published references plus outcome fingerprints. `_lookup_detail` permits selected inputs only, never earlier outcome prose. A source.read normally publishes no new records. Thus today's request_context cannot recover an old returned passage or its exact continuation after conversation loss. It can recover the selected operands for an explicit reread, but that is new selected work. A future renderer can project actual previous reading ranges from saved own `runtime_actions` and supply needed previously received excerpts without a new interpretation/composer call; this is a presentation gap requiring implementation and human steering, not an existing capability claimed here.

Source text, navigation coverage, scientific progress, annotation support, monitoring information and duration expectations remain distinct. Do not set scientific future yield to zero merely because a document ended or a parent question appears answered; the practical resource endpoint exception does not apply to this literature role. Preserve partial reads, unsuccessful access, negative findings, correction losses and original completed observations.

Read-only review covered AGENTS.md, GOAL.md, the complete episode-structure/time-estimation documents and later practical contract, the complete literature binding and relevant shared decision assembly/response/action/return/credit paths, own-outcome/history/category consumers, source.read schema/dispatch, complete source_window, scientific record meanings and reasoning-view/commit paths. No application edit, test, model call, network request, scientific run or process change was performed. Only this proposal file was written.
