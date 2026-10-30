# 007 — table investigation: corrected TASK and STEERING

```text
TASK

Investigate the assigned table or sheet to determine what its actual measurements, comparisons and qualifications establish for this scientific question. You own repeated choices about which rows, columns, headers, conditions, controls, footnotes or neighboring source context to examine, and how to interpret what you have actually received.

Assigned scientific question: {complete_assigned_table_question}
Parent's intended use of your result: {complete_requested_report_purpose}
Fixed biological target and scientific scope: {target_identity_and_complete_assigned_scope}
Assigned source and table or sheet: {source_citation_and_exact_table_label_or_sheet_name}
Binding constraints: {complete_parent_and_caller_constraints}
Supplied starting selector: {exact_sheet_header_filter_and_matching_row_page_or_representation_and_original_byte_window}

The starting selector is a proposed place to begin, not evidence that a read occurred. Choose the next examination or interpretation from the scientific distinction that matters. For example, distinguishing activity from a background signal may require the relevant control, whereas distinguishing substrate preferences may require measurements on the same preparation under comparable conditions. These are alternative reasoning needs, not a compulsory sequence. A useful qualification, corrected comparison or negative finding can advance the investigation while weakening the proposed annotation.

Establish what each relevant row and column actually represents before comparing values. Preserve exact source headings, reported units, native row identity, cell addresses and the source's subject: target protein, reference homolog, construct, preparation, organism or sample. Keep substrates, treatments, measurement conditions, controls, replicate counts and reported uncertainty when they affect the comparison. Use only information actually reported or explicitly supplied. A similar name does not establish the same assayed subject; different conditions or denominators can make apparently comparable numbers answer different questions.

Read controls and qualifications as part of the result. Distinguish a measured lack of effect, an explicit not-detected statement, a source-reported uncertainty, an unavailable measurement and a location not yet examined. A table can support family membership, a particular activity or a physiological interpretation to different degrees. An assay on a homolog is evidence about that homolog; any implication for the fixed target requires a separately supported connection. Preserve a source-grounded limitation instead of strengthening a label beyond the measurement. Do not convert discovery of a row, byte coverage or repeated wording into a scientific finding.

For XLSX, select the actual sheet through available sheet information. A row operation on an assigned sheet must retain that sheet; header choice, row page and literal filter can be revised. A filter specifies column or any column, equals or contains, its literal value and case sensitivity. Offset counts matching rows, not original worksheet row numbers. A zero-match result establishes only that literal filter's result when the returned decode is complete. It does not establish scientific absence. A partial parse, unresolved cell or failed read remains qualified; retain valid returned cells rather than discarding them.

Use native cell values faithfully. Formula text and its cached value are separate received facts; the operation recalculates neither. Preserve relevant raw numeric or date lexical values and the reported date system. Style indices alone do not establish formatting, units or date interpretation. Distinguish an explicitly returned empty cell from an absent cell and from a cell omitted from the prompt's relevant subset. The current XLSX row view does not supply merge ranges, comments, full style definitions or semantic footnote relationships. Leave those relationships unknown until actual selected source access supplies them; do not fill them from layout or expectation.

For article XML tables, use exact original-source text windows and their UTF-8 byte anchors. Headers, footnote markers, rowspan or colspan markup and nearby qualifications can change which value belongs to which condition. Preserve observed relationships rather than flattening them away. A paragraph projection can omit tables and footnotes; an absent projection is not an absent source result. Keep original-source coordinates separate from coordinates in a derived text representation. Source citations and prior-delivery references do not mean their contents have been examined.

Choose only operations available for this episode and within the assigned source and permitted derivatives. An ordinary read or row selection is one tool action. This table episode has no child branches. No whole-sheet read, row quota, fixed order or complete-document requirement is prescribed. When already received information supports an interpretation, use the existing reasoning action to commit it with the actual subjects, conditions and exact evidence anchors. Separate source observation from your interpretation for the target. A table and a supplement may represent the same underlying observation; retain their distinct locations without treating unchanged evidence as independent support.

Available decisions
| Choice | Actual available operation | Required meaningful operands and binding limits | Information returned or committed |
| --- | --- | --- | --- |
{actual_relevant_table_decisions_with_complete_operand_meanings}

Parent's requested result
| Field | Type and allowed values | Exact requested scientific meaning | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_parent_requested_return_field_meanings}

Keep those return meanings fixed. Update only declared interpretation fields from information received before the selected next action. Parent-supplied initial values are not a new judgment by you. A selected future read has no interpreted result yet. Recorded fact fields are filled from actual host records. Preserve valid partial work and report specific declared failure information that permits repair; episode closure alone does not establish scientific completion.

Use your own yield information to compare another examination, interpretation or available repair. Total yield is the saved signed gain from completed own actions, excluding starting inherited information. Expected next yield is conditional on completing that category again; unavailable is unknown, not zero. Its uncertainty band is an approximate working-model band, not a calibrated outcome guarantee. Reading may have zero immediate credit before interpretation. Keep scientific progress, annotation support, timing information and duration expectations separate. Existing duration information can inform a costly selection when available. The configured controller owns continuation.

Return the existing typed JSON response contract unchanged: select_action with selection and report_update. If exact earlier own input details are needed first, use the declared request_context exchange and then continue this same decision. A lookup creates no action observation. Lookup operands and allowed values: {readable_existing_own_history_lookup_contract}. The host executes the selected action. This complete TASK applies on every iteration, including exchanges after lookup or reconstruction.

STEERING

| Own action category | Completed | Total yield | Expected next yield | Uncertainty / unavailable reason |
| --- | --- | --- | --- | --- |
{own_action_category_rows}

| Relevant scientific distinction | Received result or current interpretation | Actual subject and conditions | Material qualification / exact source basis |
| --- | --- | --- | --- |
{only_next_decision_relevant_received_question_context_rows}

| Own examination | Exact sheet, header, literal filter and matching-row page; or representation and byte window | Actual result | Coverage or failure limitation |
| --- | --- | --- | --- |
{only_next_decision_relevant_prior_attempt_rows}

| Native row | {column_letter_and_exact_source_header_with_reported_units} | {other_needed_column_letter_and_exact_source_header_with_reported_units} |
| --- | --- | --- |
{only_relevant_already_received_native_rows_and_cell_addresses}

| Relevant control, cell or footnote | Exact received value or passage | Condition, relationship or representation limitation | Exact source location |
| --- | --- | --- | --- |
{only_needed_received_controls_formula_cache_details_footnotes_or_xml_windows}

| Requested interpretation field | Current admitted value | Actual basis / parent-supplied initial value |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_relevant_existing_duration_table}
{only_if_present_actionable_failure_table}
```

TASK and STEERING are rendered separately. TASK above is included in full on every call; only its assignment, capability and requested-form placeholders are filled. Scientific results, exact prior attempts and current interpretation values fill STEERING. Its tables contain factual cells only. Empty or irrelevant conditional tables are omitted; missing values remain unknown where they affect the choice. Table columns extend only for relevant actually received fields, preserving native headings and units. A returned empty cell must remain distinguishable from an unrendered cell.

The optional duration table has columns `Proposed operation and exact selection | Expected duration and measured interval | Statistical support / unknowns`. The optional failure table has `Failed selection or delivery | Actual failure and affected operand | Preserved partial work / repair-relevant fact`. Neither table adds an action recommendation, private history or narrative recap.

## Decision and information trace

- Assignment, scope, constraints, source/sheet bounds and complete requested return meanings supply TASK. The existing source selector is an assignment operand, not an executed read. Substantive table reasoning is stated above rather than delegated to a short role label or manual list.
- Actual selected row filters and source windows, their saved outcomes, explicitly supplied facts and this receiver's admitted interpretations supply STEERING. The parent episode's private history, yields and source access do not. Citation attribution does not hydrate source records.
- `LiteratureEpisodes` supplies the fixed reading assignment, actual allowed operations and source ancestry/sheet validation. Its table role has no children. `ToolRegistry._spreadsheet_arguments/_document_async`, `Workbook.layout/rows/cell` and `materials.source_window` establish the actual received representation and operand meanings used here.
- XLSX results preserve native cell and row identities, lexical values, formula/cache distinctions, error and completeness information. They do not project merges, comments or semantic footnote relationships. Original package parts can be examined only through actual selected available source operations; the renderer performs no acquisition or scientific interpretation.
- `decision_history.yield_table` supplies existing completed-own-action category observations and estimates. `lookup_attempts` currently exposes selected inputs and outcome metadata, not arbitrary prior received result bodies. Exact older result presentation remains implementation work; do not synthesize a model recap to fill that gap.
- Exact parent form meanings stay in TASK; existing `report_values/report_basis` supply current STEERING values. Shared response admission and closure keep typed JSON outputs and parent-defined forms unchanged. Human-readable operand binding remains implementation work; machine identities stay outside the input text.

Read the mandatory task/steering contract, original template review, complete current literature binding, complete native XLSX path, exact source-window implementation, relevant tool dispatch/contracts and own-yield/lookup consumers. The original draft is preserved. This is a proposed prompt for human feedback; no application code, tests, network requests, model calls or scientific runs were changed or executed.
