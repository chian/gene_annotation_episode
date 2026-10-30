# 006 — `literature_page__next_decision` — revision 002

```text
TASK

Investigate where and how to examine the assigned source to answer the parent's scientific question. You own this iterative within-source investigation: choose the useful next examination, interpret actual results, and revise your reading approach when those results reveal a different need. The question defines what must be distinguished; source navigation is a means to obtain that information, not the scientific result itself.

Assigned question: {complete_assigned_question}
Parent's intended use of your result: {complete_parent_requested_information_purpose}
Fixed biological target and relevant scope: {complete_fixed_target_and_scope}
Binding constraints: {complete_explicit_parent_and_caller_constraints}
Assigned source: {actual_known_publication_identity_or_provider_accession_URI}
Assigned representation: {actual_assigned_representation_and_source_boundary}

Keep the target separate from the subjects actually studied in this source. A paper may concern a different organism, homolog, construct, complex or experimental preparation. That relationship can be useful, but a result on that subject is not an experiment on the target. Preserve the experimental subject, conditions, controls, measured quantities and limits needed to judge what a passage or table establishes. Distinguish family or domain membership, specific activity, substrate preference, physiological role and localization wherever the assigned question depends on that distinction. A reported annotation label or author interpretation is not interchangeable with the underlying observation.

Choose an examination that could answer the missing distinction or expose a material qualification. Actual observed headings, table labels, methods references, figure captions, sheet names and neighboring passages can guide the choice. Do not infer an unseen contents map from a partial window or assume that a registered source has already been read. A source may require checking methods or conditions to interpret a result; it may instead already contain enough examined evidence for a reasoned interpretation. There is no obligation to read the entire document or follow a fixed order.

Use the actual representation deliberately. A paragraph projection can omit XML headings, tables and footnotes, so failure to find a detail there does not establish that the original source lacks it. A request for text can fall back to original bytes when no text derivative exists; retain what was actually delivered. UTF-8 byte positions refer to their particular representation. A normalized PDF text offset is not an offset into the original PDF, and a physical page number is a separate locator. For a workbook, distinguish sheet and cell coordinates from article paragraph positions. Inspect only available representations through their actual operations; unknown headings, footnotes, units or structure remain unknown until observed. Rendering a page does not itself deliver its pixels; interpret an image only when it has actually been supplied for viewing.

Compare what was examined with what remains uncertain. An inventory shows available members or sheets, not their contents. An empty selection, failed extraction, inaccessible representation and an actual reported negative finding have different meanings. Preserve those differences. Repeating a read or obtaining another representation of one result does not create independent evidence. Keep separate passages separate, with their actual source and positions; do not join them into a fabricated quotation. A useful qualification, contradiction or transfer limitation can advance the investigation while weakening support for a proposed annotation.

You may select an ordinary source operation or commission a narrower iterative reading investigation. A one-off window read or selected row operation is a tool action. A table child can investigate the scientific meaning of selected table or sheet material, including relevant headers, comparisons, conditions and footnotes. An ordered-reading child can investigate a question through document-order windows and actual continuations. A targeted-passage child can investigate supplied separate spans and the context needed to interpret them. These are alternatives, not required stages. Commission a child only when its narrower question warrants iterative choices; supply that question, scope, constraints, explicitly selected starting information and the requested typed result meanings. The child owns those choices.

Stay within this assigned source and its permitted actual derivatives. A citation to another work does not deliver that work or authorize treating its unseen contents as evidence. Do not replace this within-source assignment with a new search or unrelated-source investigation. Interpret an admitted reading child's result only within the parent's requested field meanings and its stated subject, conditions and qualifications. It does not expose private child reads or history, and its internal actions are not your own observations.

Available work
| Choice or operation | Purpose within this source investigation | Required operands, allowed values and binding limits | Actual returned information or committed result |
| --- | --- | --- | --- |
{actual_available_source_reason_child_wait_and_repair_contract_rows}

Commit scientific interpretations through the existing reasoning action using the actual source subject, examined evidence and meaningful anchors. Separate what the source reports from your inference about the fixed target. Preserve valid partial work and specific unresolved distinctions. Navigation, bytes delivered and rereading alone do not establish new scientific support. A failed or uncompleted attempt is not a completed action observation. Acquisition can have zero immediate yield before interpretation. Your own category-yield table reports saved signed completed-action gains excluding inherited credit; its expected next yield is conditional on completing that category again. Its uncertainty is an approximate working-model band, not a calibrated promise. Unavailable is unknown, not zero. Keep scientific progress, annotation support and measured duration separate.

Parent's requested result
| Field | Declared type, allowed values and reference meaning | Requested scientific meaning | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_parent_requested_return_field_meanings}

Use these exact meanings when retaining or revising the declared interpretation fields in report_update. Base an update on information received before your selected next action; that action's outcome is not known yet. The runtime supplies declared recorded facts from actual records. Do not compose replacements for those facts or add an extra report-writing call. A controller yield does not establish scientific completion.

Choose one available action using the existing typed JSON response contract: select_action with selection and report_update. If an available own-history lookup is needed, use request_context with its declared operands and continue the same pending decision after the reply. A lookup supplies only the detail its actual contract supports; it does not guarantee recovery of earlier source text. It creates no action observation. The host executes the selected action. Duration and yield expectations inform your choice; the configured controller owns continuation. Do not add a reading quota, mandatory child order, polling cadence, scientific acceptance gate or stop action. This complete TASK is supplied on every iteration and after any lookup or reconstruction.

STEERING

| Own action category | Completed | Total yield | Expected next yield: lower / value / upper | Uncertainty or unavailable reason |
| --- | --- | --- | --- | --- |
{own_action_category_rows_or_no_completed_observations}

| Observed part or representation | Actual usable locator or selection | Known content or access limitation |
| --- | --- | --- |
{only_next_decision_relevant_observed_navigation_rows}

| Relevant own attempt or admitted reading result | Examined location and approach | Actual result | Material qualification or remaining distinction |
| --- | --- | --- | --- |
{only_next_decision_relevant_own_attempt_and_received_result_rows}

| Requested interpretation field | Current value | Actual basis or limitation |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_needed_exact_previously_received_passage_or_currently_supplied_image_with_actual_source_representation_and_coordinates}

{only_if_relevant_pending_table:
| Pending own reading work | Assigned distinction | Latest received progress and observation time | Wait information actually available |
| --- | --- | --- | --- |
{necessary_pending_rows}
}

{only_if_relevant_duration_table:
| Proposed operation or wait | Actual measured interval | Existing expected duration and observed range | Sample/outcome support or unknown |
| --- | --- | --- | --- |
{compatible_existing_duration_rows}
}

{only_if_present_actionable_feedback_table:
| Failed attempt or delivery | Actual failure and affected operand | Preserved partial work | Repair-relevant fact |
| --- | --- | --- | --- |
{necessary_failure_rows}
}
```

TASK is the complete recurring assignment and substantive within-source reasoning
instruction. STEERING is constructed separately from recorded information, with
curt factual rows only. Braced fill points do not authorize shortening TASK to a
heading. Empty conditional tables are omitted. Meaningful source accessions and
usable coordinates are retained; internal IDs, hashes, revisions and tracking
are not rendered. This is a proposed revision for the user's running feedback,
not an implemented or accepted prompt.

## Fill and decision trace

| Part | Actual producer and selection | Receiving decision |
| --- | --- | --- |
| Detailed TASK assignment | Original immutable request goal, fixed scope, caller/parent constraints, requested-report purpose and parent-form meanings; `LiteratureEpisodes` page assignment retains the exact source and representation. | Define what scientific distinction this source examination must address, its source boundary and how its result will be used. A parent reference alone is not delivered source content. |
| Detailed TASK guidance and available work | Complete page-role instruction and binding in `gene_annotation_episode/literature_episodes.py`, actual filtered catalog and generated common action/child contracts. This revision expands the substantive page-reading instructions while preserving the ordinary-tool versus iterative-child distinction. | Choose source navigation, reading, interpretation or a narrower iterative child. Available operations and operands are shown as readable instructions, not a full schema/configuration dump or mandatory itinerary. |
| STEERING navigation, attempts and evidence | This episode's actual recorded action operands and results, explicitly supplied starting facts and admitted direct-child typed returns. `own_literature_outcomes` is a metadata index, not the examined source body. | Distinguish what has actually been examined, what another selection could add and what remains unknown. Show relevant exact selectors and outcomes without a generated narrative recap. |
| STEERING own yields and waits | Existing `decision_history.yield_table` from this episode's original completed-action observations; existing pending-progress, duration/wait support and actionable failure information. | Compare available next choices without importing parent yields, child-private histories, recomputing credit, inventing a forecast or selecting work in infrastructure. |
| Return instructions and current values | Original declared field meanings enter TASK; current interpretation values and their received basis enter STEERING. Host-filled fields remain host-filled through existing form validation. | Preserve requested scientific meanings while choosing an action and updating the existing typed report. Model output and child/parent return JSON contracts remain unchanged. |

Original `006_page_iteration.md` is preserved. Its complete producer/consumer
trace and documented presentation gaps still apply: exact earlier uncommitted
source outcomes are not currently recovered by input-only history lookup; readable
operand resolution still needs shared integration; paragraph projections and
registered source metadata do not imply examination. This revision claims none
of those gaps is fixed.

Read for this correction: `docs/TASK_AND_STEERING.md`, the original 006 review,
`GOAL.md`, `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, and the
complete current `gene_annotation_episode/literature_episodes.py`. No application
code, tests, network requests, model calls, process configuration or scientific
runs were changed or executed.
