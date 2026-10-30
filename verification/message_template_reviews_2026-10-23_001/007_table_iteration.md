# Proposed text prompt: `literature_table__next_decision`

One decision of the table investigation, for human steering before implementation. Braced names are fill placeholders. Tables contain actual received values or declared parent meanings; no generated recap, new interpretation or automatic source read fills them. Human-readable handles require an internal mapping to existing source, sheet and record operands.

```text
You own an iterative investigation of this table for the assigned scientific question.

Your question is: {assigned_table_question}
Your page parent needs this information for: {requested_report_purpose}
Your fixed target and scope are: {target_identity_and_scope}
Your assigned source and table/sheet are: {source_citation_and_exact_table_label_or_sheet_name}
Your binding constraints are: {relevant_parent_constraints}
The supplied starting selector is: {sheet_and_literal_filter_or_original_source_byte_window}
That selector is context, not evidence that its rows or passage have been examined.

Choose which rows, columns, controls, conditions, footnotes or comparisons to examine or interpret next. Revise a selection when actual outcomes warrant it. Preserve the source's subjects and conditions when judging what a result means for the target. A qualification, negative finding or corrected comparison can advance the investigation.

The relevant question context already received is:

| Question or competing explanation | Recorded proposition or received interpretation | Actual subject and conditions | Qualification or unresolved distinction | Basis handle |
| --- | --- | --- | --- | --- |
{relevant_received_question_context_rows}

Your actual table access so far is:

| Own attempt | Exact sheet, header row, literal filter and matching-row offset/limit; or representation and byte window | Returned native rows/cells or exact passage | Actual outcome, continuation and limitations |
| --- | --- | --- | --- |
{relevant_own_table_attempt_rows}

For each XLSX filter, retain column, equals/contains, literal value and case sensitivity. Offset counts matching rows; returned worksheet row numbers and cell addresses retain their original identity. Zero matches establishes only that filter's result when decoding is complete. A failed or partial read does not establish absence.

The relevant rows actually returned are below. Column headings reproduce the source's exact header text and reported units; extend the columns only for the received fields needed for this question. A missing header stays unknown.

| Native row | {column_letter_1}: {exact_header_1_and_reported_unit} | {column_letter_2}: {exact_header_2_and_reported_unit} |
| --- | --- | --- |
{actually_received_relevant_native_rows_with_cell_addresses}

| Cell, header, control or footnote | Exact received content | Recorded relationship, qualification or representation limit | Source/basis handle |
| --- | --- | --- | --- |
{relevant_cell_details_conditions_controls_and_footnotes}

Retain formula text separately from its cached value; neither is recalculated. Preserve raw numeric/date values and relevant style/date-system information. Distinguish an explicit empty cell, an absent cell and an unexamined cell. Preserve an observed merged range without filling unobserved cells; when merge information is unavailable, leave the relationship unknown. Do not infer units, control identity or column relationships from layout alone. For article XML, retain the exact original-source excerpt and its byte anchors, including table headers, footnote markers and relevant rowspan/colspan markup. Do not flatten away their relationships.

The source was assigned for a question; that does not require loading the entire table. Supplied prior-delivery handles establish provenance only. Prior interpretations are identified as such; an observation elsewhere in the paper is not automatically an observation in this table.

These are this episode's OWN action-category observations:

| Action category | Completed own actions | Total signed yield | Expected next completed-action yield: lower / central / upper | Availability and uncertainty | Attempts without completed observations |
| --- | --- | --- | --- | --- | --- |
{own_action_yield_rows}

Total yield excludes inherited credit. Expectations are conditional on completing the category again; unavailable is unknown, not zero. Bands are approximate working-model uncertainty, not calibrated guarantees. Reading can earn zero immediate progress before interpretation. The configured controller owns continuation; there is no reading quota or stop action.

{if_relevant_execution_expectations:
| Available XLSX operation and meaningful selection operands | Expected duration and measured interval | Complete / lower-bound / unmeasured support; observed range | Availability or limitation |
| --- | --- | --- | --- |
{relevant_existing_execution_expectation_rows}
}

Your parent-defined return fields are:

| Exact field | Type, allowed values and reference kind | Parent's declared meaning | Current interpretation and actual basis | Filled by you or recorded by runtime |
| --- | --- | --- | --- | --- |
{parent_return_field_rows}

Update only the declared interpretation fields from information already available before the selected next action. Parent-supplied initial values are not your new judgment. Recorded fact fields describe actual records; a later tool result does not automatically revise an interpretation.

The useful available actions for this decision are:

| Action | Available operation | Required meaningful operands | Information returned or committed; relevant limit |
| --- | --- | --- | --- |
{small_relevant_table_action_menu}

This table investigation has no child episode branches. For an XLSX row assignment, source.xlsx.rows must retain the assigned sheet; rows, header selection and literal filter can be revised. Original XML table reads use source.read with representation original and bounded UTF-8 byte windows. Select only available operations within the assigned source and its permitted derivatives.

Commit source-grounded interpretations through the reasoning action, preserving actual subjects, conditions, exact anchors and target applicability. A table and supplement can express the same underlying observation: retain their distinct representations without treating unchanged evidence as a new finding. Navigation, repeated reads and repeated wording do not establish new scientific progress. Scientific progress, annotation support, timing information and duration expectations remain separate.

{if_relevant_actual_failure: Failed selection or report feedback: {code_affected_operands_and_preserved_partial_rows_or_records}}

Return the declared typed JSON response unchanged: select_action with selection and report_update. If exact details of your own earlier received attempts are needed first, use request_context with the declared lookup operands; it continues this same decision and creates no action observation. Available lookup fields and allowed values: {readable_own_history_lookup_contract}. Use supplied meaningful handles. The host executes the selected action.
```

## Exact receiver, producers and consumers

The receiver chooses the next table-specific examination or interpretation for its assigned question. It does not select new papers, revise the scientific parent's overall objective or follow the page episode's private history. The proposed text replaces only model-facing presentation at `DecisionSource.next` → `call` → `exchange_decision` → provider; saved JSON contexts and response/dispatch/return contracts remain internal and unchanged.

| Prompt information | Exact current producer and operands | Decision/consumer it serves |
| --- | --- | --- |
| Assigned question, purpose and fixed bounds | This receiver's `EpisodeRequest.goal`, `message.scope`, `report_contract.decision/schema` and `episode_assignment`; `LiteratureEpisodes.assignment_schema` defines a reading assignment with `page` and either `_TABLE` or `_WINDOW`. | Identifies which table distinction matters. `prepare_assignment`, `_validate_assignment` and shared composition preserve ownership/scope. Do not invent a separate parent objective from private history. |
| Source and initial selector | `_PAGE` carries `source_ref`, representation/artifact custody, `question_context_refs` and `prior_delivery_refs`. `_TABLE` carries `source_ref`, `sheet_key`, `offset`, `limit`, `header_row`, `where.column/match/value/case_sensitive`; `_WINDOW` carries representation and byte offset/limit. `_validate_page` checks the exact retained artifact. | Shows the assigned table/sheet or passage and binding source without treating a starting selector as executed work. Actual biological citation/version identity may distinguish evidence; internal version tags do not belong in the text. |
| Question context and prior interpretations | `decision_context` supplies the validated assignment and source custody; scoped `Workflow.working_state`/`Store.reasoning_view`, actual question-context records, received source windows and explicitly supplied typed forms provide content. | Lets the table owner identify needed comparisons and relevance limits. Merely listing a reference is not receiving or examining its contents. |
| Exact own row filters and outcomes | `runtime_actions.action` records actual selected tool arguments; `runtime_actions.result` records the outcome. `DecisionSource.next` supplies the last actual outcome; `Workflow.history_read(records)` can return previous exact selections/outcomes in the older protocol. `WorkflowServices.own_outcomes` supplies only paged tool/status/reference metadata. `decision_history.lookup_attempts` supplies selected-input values/previews and publication handles in the exchange protocol. | Avoids repeating the same literal filter, distinguishes matching-row offset from native row identity, and permits deliberate rereading/repair. Only this receiver's records are eligible. A table episode has no direct-child branches; an explicitly supplied earlier form can inform it, but no private page/parent history is imported. |
| Sheet names and native row/cell contents | `ToolRegistry._spreadsheet_arguments` → `_document_async` → `xlsx_native` → `Workbook.layout/rows/cell` → `_publish_document`. `source.xlsx.sheets` returns actual sheet names/relationships and availability. `rows` returns `sheet`, `header`, `rows`, original row numbers/ordinals/cell addresses, `where`, match/page metadata, errors/failures and completeness. Cells retain `value`, `raw_value`, type, style index, formula text/attributes, cache flag and cell error. | Enables deliberate choice of rows, headers, condition columns and literal filters. Display only received relevant rows; rendering must neither run a new selection nor load the whole workbook. The caller-selected header is not semantically inferred. |
| XML table, footnotes and exact anchors | `source.read` dispatches to `materials.source_window`; it returns the actual representation, text, artifact identity, `start/end`, `total_bytes`, continuation and available representations. `public.literature.read` supplies a paragraph projection that can omit table/headings/footnotes; table access uses retained original bytes. | Preserves actual table/footnote relationships and evidence anchors. Raw XML excerpts remain source text, not an object dump. `source_window` enforces UTF-8 boundaries and adjusts a split terminal character. |
| Eligibility and source/sheet constraints | Complete `LiteratureEpisodes.catalog`, `_tool_arguments`, `execute`, `instructions`, `resolve`, report and credit methods inspected. Table role has access tools, no acquisition tools and no children. Source operations must stay within the assigned source or descendant custody. An assigned XLSX `sheet_key` is checked on actual `source.xlsx.rows` dispatch. `execution.estimate` is restricted to XLSX sheets/rows branches. | The small menu describes actual enabled alternatives, not a compulsory reading order. Shared `Workflow.catalog/action_schema/selected` retains reasoning, available inspection tools, waits and repair as actually bound. Catalog exposure alone is not evidence of a completed operation. |
| Own category yield | `decision_history.category_for/yield_table` joins this receiver's saved selections and original controller observations in completion order; `exchange_decision` supplies it through `model_snapshot`. Render `rows.category/completed_actions/total_yield/expected_yield` including band/status/unavailable reason and `attempted_uncompleted`. | Informs whether another row read or interpretation may be useful; does not invent per-filter forecasts. These category bands have no controller effect. Parent history, inherited credit and hypothetical new observations are excluded. |
| Existing duration expectations, conditionally relevant | `DecisionSource.call` adds `native_execution_expectations` and `resource_tool_estimates` when bound. `execution.estimate` can explicitly propose XLSX work. `ordinary_execution` shares technical workload preparation with execution; timing/statistics and `ResourceToolEstimator` supply measured interval, availability, original support and range. | Helps compare costly operations before selection without a compulsory forecast call, extrapolation or action recommendation. Keep timing distinct from scientific gain and do not expose execution-class digests/configuration records. |
| Parent form/current basis and closing return | `request.report_contract`, `interpretation_schema`, `report_values/report_basis`, `FACT_MEANINGS`, declared `x-source` metadata. `apply_response` admits interpretations and saves their actual visible basis. `finish` + `Workflow.facts` + `form_with_facts` create the original requested form from those interpretations and actual recorded facts. `LiteratureEpisodes.fact_sources/facts` add no table-specific fields. `validate_report`/`validate_form` resolve references before parent admission. | Keeps the exact parent-defined field names, nested types, allowed meanings and actual basis intact. Returned fact fields do not stand in for an unperformed table interpretation. No report composer or new field convention is proposed. |

## Omissions and established gaps

Omit full input objects, full tool schemas/manuals, run/episode IDs, hashes, implementation tags, revision labels, raw source-custody/configuration records, generic launch information and unrelated scientific records. Keep exact biological identifiers, source citation, table/sheet labels, original header names/units, cell addresses, literal filter values and source anchors where they distinguish evidence or enable selection. Internal readable-handle resolution must preserve original scope, source, sheet and reference operands; that adapter is a proposal, not existing behavior.

The current compact literature outcome index is the first page of selected tool metadata, not the latest scientific table state. Its tool filter includes XLSX rows and source reads but excludes XLSX sheet inventory, archive operations and PDF info/page. It omits selected filters and row bodies. The exchange own-attempt lookup intentionally exposes selected inputs and published references, not old outcome bodies; an XML `source.read` publishes no new record references. Consequently, a fresh conversation cannot recover every earlier examined XML row from that lookup alone. Existing saved own outcomes contain the facts, but presenting relevant exact older outcomes without replaying work still needs a bounded received-outcome presentation path. Do not fill the gap with a model recap.

The XLSX adapter does not project merge ranges, comments, actual style definitions, formatted date values or semantic footnote relationships. It reports the date system and style indices and preserves original package bytes, formulas and caches. An empty returned `<c>` can be distinguished from a missing `<c>` in a returned row, but omission from the displayed relevant subset must never be presented as a blank cell. A missing row/header, malformed row identity, unresolved string, partial parse or unobserved merge stays qualified/unknown. Native XLSX numeric values are lexical strings; converting them to display numbers must not discard their exact values or invent units. Original package parts can be investigated with available inventory/extraction/source operations when selected; no automatic expansion is proposed.

`source.xlsx.rows` currently reads all cells in each selected row, not a selected-column subset. Its matching scan can traverse the sheet to establish match counts; the proposed presentation does not claim the episode examined every scanned row. Presentation selects relevant already-received columns without discarding exact returned cell identity. For an assigned sheet, the actual row operation rejects a different sheet; its separate estimate request currently checks source ancestry but does not apply that sheet-mismatch condition. This is an existing validation distinction, not authorization to change sheets.

Relevant record selection, semantic handles and exact received-outcome rendering remain implementation work after human steering. The draft neither changes scoring/controller math nor adds quotas, gates, fixed action order, a new composer or process changes. No application edits, tests, network requests, model calls or scientific execution were performed. Read-only inspection covered the required project documents, complete literature binding, native XLSX adapter and source-window path, plus shared decision/history/action/typed-return/credit consumers. This file is a proposal only.
