# 007 — table investigation: direct task instructions

```text
TASK

Use {exact_table_label_or_sheet_name} in {paper_or_supplement_citation} to answer: {complete_parent_question_naming_the_measured_result_or_comparison_and_its_implication_for_the_gene_or_candidate_annotation}.

Annotation target: {gene_name_and_organism}
Candidate annotation or claim being examined: {actual_candidate_function_or_specific_annotation_claim}
Read within: {assigned_table_sheet_source_and_permitted_derivatives}
Respect: {complete_parent_and_caller_constraints}
Begin from this supplied location: {exact_sheet_header_filter_and_matching_row_page_or_representation_and_original_byte_window}

Select rows, columns, headers, controls, conditions, footnotes or neighboring context that can answer that question about {gene_name}. The supplied location identifies where you can begin; it does not mean you have read it. Revise your selection when actual results show that a different comparison or missing qualification matters. A correction or negative result can improve the annotation of {gene_name} even when it weakens support for {candidate_function_or_claim}.

{direct_assignment_specific_comparison_instructions_naming_the_actual_subjects_rows_measurements_conditions_controls_or_alternatives_and_explaining_what_each_observable_outcome_would_support_or_limit}

Before comparing values in {exact_table_label_or_sheet_name}, establish what its relevant rows and columns represent. Keep the exact headings, reported units, native row identity and cell addresses. Identify the actual measured or compared subjects: {actual_target_or_reference_proteins_constructs_organisms_samples_or_other_source_subjects_explicitly_assigned_or_unknown}. A shared name does not establish that two rows concern the same protein or preparation. Preserve treatments, measurement conditions, controls, replicate counts and reported uncertainty when they affect the conclusion about {candidate_function_or_claim}. Different conditions or denominators can make similar-looking numbers answer different questions. Use only what the source reports or the parent explicitly supplies; unknown subjects or conditions remain unknown.

Read the relevant controls and qualifications with the values they qualify. Distinguish a measured lack of effect, an explicit not-detected result, a reported uncertainty, an unavailable measurement and a cell you have not examined. Decide how far the particular result supports {candidate_function_or_claim_for_gene_name}: for example, support for membership in a family need not establish a specific activity or physiological role. When a row concerns a homolog rather than {gene_name}, retain that subject and the separate basis for transferring its result to {gene_name}. Do not strengthen the candidate annotation beyond the comparison actually made. Finding a row, covering bytes or reading the same result again does not itself establish a new scientific finding.

For an XLSX table, retain the assigned sheet {assigned_sheet_name_if_xlsx}. You can revise the header row, row page and literal filter within that sheet. Select only an actual sheet available from the workbook. Each filter specifies a column or any column, equals or contains, the literal value and case sensitivity. Offset counts matching rows; it is not an original worksheet row number. A zero-match result establishes only that filter's result when decoding is complete, not absence of the biological property relevant to {candidate_function_or_claim}. Retain valid cells from a partial read and keep its unresolved cells, parse errors and coverage limits explicit.

Preserve native XLSX values. Formula text and its cached value are separate received facts; neither is recalculated. Keep relevant raw numeric or date values and the reported date system. A style index alone does not establish a number's units, formatting or date interpretation. Distinguish an explicitly returned empty cell from an absent cell and from a cell omitted from the displayed relevant subset. The current row view does not supply merge ranges, comments, full style definitions or semantic footnote relationships. If one of those changes how {named_result_or_comparison} should be read, examine the relevant available source representation; leave it unknown until actually observed.

For an article XML table, retain exact original-source windows and UTF-8 byte anchors for {exact_table_label}. Preserve headers, footnote markers, rowspan or colspan markup and qualifications needed to associate {relevant_measurements_or_source_values} with their actual conditions. Do not flatten away those relationships. A paragraph projection can omit a table or footnote; that omission does not establish that {paper_citation} lacks the result. Keep original-source coordinates separate from coordinates in derived text. A citation or prior-delivery reference does not mean its contents have been read.

Use available operations within {assigned_source_and_permitted_derivatives}. This table episode has no child branches. An ordinary row selection or read is one tool action. Read or interpret what can answer the question about {gene_name}; no whole-sheet read, row quota, fixed sequence or complete-document requirement is prescribed. When received information supports a conclusion, commit it through the existing reasoning action with the actual subjects, conditions and exact evidence anchors. Keep what {paper_citation} reports separate from your conclusion for {gene_name}. A table and supplement can represent one underlying observation; preserve their locations without counting unchanged evidence as independent support.

Available decisions
| Choice | Actual available operation | Required operands and binding limits | Information returned or committed |
| --- | --- | --- | --- |
{actual_relevant_table_decisions_with_complete_operand_meanings}

Return these requested results about {gene_name_and_candidate_function_or_claim}
| Field | Type and allowed values | Exact requested scientific meaning | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_parent_requested_return_field_meanings}

Keep those meanings fixed. Update only declared interpretation fields from information received before the next selected action. Parent-supplied initial values are not a new judgment by you. A future read has no interpreted result yet. The host fills recorded fact fields from actual records. Preserve valid partial work and use the declared failure fields for specific repair information. Episode closure alone does not establish that the conclusion about {candidate_function_or_claim} has been demonstrated.

Compare another table examination, interpretation or available repair using your own action yields below. Total yield is the saved signed gain from completed own actions, excluding inherited information. Expected next yield is conditional on completing that category again; unavailable is unknown, not zero. Its band is approximate working-model uncertainty, not a calibrated outcome guarantee. Reading may have zero immediate credit before interpretation. Scientific progress, annotation support, timing information and duration expectations remain separate. Available duration estimates can inform a costly read. The configured controller owns continuation.

Use the existing typed JSON response: select_action with selection and report_update. If exact earlier own input details are needed first, use the declared request_context exchange and continue this same decision; lookup creates no action observation. Lookup operands and allowed values: {readable_existing_own_history_lookup_contract}. The host executes the selected action. These complete TASK instructions apply on every iteration, including exchanges after lookup or reconstruction.

STEERING

| Own action category | Completed | Total yield | Expected next yield | Uncertainty / unavailable reason |
| --- | --- | --- | --- | --- |
{own_action_category_rows}

| Question about {gene_name_and_candidate_function_or_claim} | Received result or current interpretation | Actual subject and conditions | Material qualification / exact source basis |
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

## Construction and source notes

- This revision applies the added task-directness instruction throughout: the opening uses the parent's concrete question, and subsequent instructions repeatedly name the paper, table, measured subjects, candidate claim and target gene. Fill the comparison paragraph with the substantive parent-assigned reasoning, including actual comparison operands and outcome meanings. Do not fill it with a role heading, process name or an invented experiment. Comparisons may concern expression, associations, homology, structural measurements, phenotypes, biochemical activity or another actual table subject; catalysis is not a required table task.
- Use only facts explicitly assigned or already received to name subjects, measurements and conditions. If the source content has not been examined, name the requested comparison without asserting what the table contains. An unspecified candidate claim remains unspecified; the renderer must not invent a function to fill the label. Representation-specific paragraphs appear only for the actual assigned/available representation; no literal unresolved placeholder or irrelevant XLSX manual is sent for an XML-only table.
- TASK is rendered in full each time. Assignment, complete constraints, substantive comparison instructions, actual operation operands and requested typed meanings fill TASK. Actual received facts, relevant prior attempts and current interpretation values fill the separately built curt STEERING tables. Omit irrelevant or empty conditional tables; preserve meaningful unknowns and exact native headings/units.
- The optional duration table has `Proposed operation and exact selection | Expected duration and measured interval | Statistical support / unknowns`. The failure table has `Failed selection or delivery | Actual failure and affected operand | Preserved partial work / repair-relevant fact`. Neither adds a narrative recap or action recommendation.
- The original review's complete trace remains applicable: `LiteratureEpisodes` owns allowed branches and source/sheet bounds; `ToolRegistry` and `Workbook.layout/rows/cell` provide actual sheet/row/representation semantics; `materials.source_window` provides exact text windows; `decision_history.yield_table` supplies original own-action statistics. Current own-attempt lookup retrieves selected inputs and outcome metadata, not arbitrary old result bodies; actual prior result presentation and readable operand binding remain implementation work.
- Host identities, hashes, tracking and parent private histories stay outside the input. Existing typed response admission and parent forms are unchanged. This new file preserves revisions 001 and 002. Only a proposed prompt was written; no application code, tests, network requests, model calls or scientific runs changed.
