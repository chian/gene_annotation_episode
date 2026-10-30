# 009 — examine particular passages for the gene annotation

```text
TASK

Read the supplied passages in {paper_title_or_actual_source_name} to answer:
{the_parent's_exact_biological_question_about_gene_and_candidate_function}.
Determine what those passages establish about {gene_and_organism}, which
qualifications change that conclusion, and what remains unsupported or unknown.

The parent needs {the_exact_result_and_annotation_decision_it_will_inform}.
Examine {assigned_source_and_permitted_derivatives}, within
{complete_assigned_scientific_scope_and_binding_constraints}. Evaluate
{candidate_function_or_other_biological_claim_actually_assigned}. Compare
{the_actual_parent_assigned_biological_alternatives_if_any} when that comparison
is part of the question; do not invent a function or competing explanation.

Start from these source locations:

| Supplied passage location | Representation | UTF-8 byte offset | Maximum bytes in the supplied selector |
| --- | --- | ---: | ---: |
{each_original_supplied_source_bound_span_as_actual_location_operands}

These locations tell you where to begin examining the paper. They do not mean
the passages were read or that their contents support the candidate annotation.
Choose which passage, neighboring context or other permitted part of this
source to examine next from the biological evidence still needed. Reading all
supplied locations in their listed order is not required.

{Full assignment-specific instructions for comparing or interpreting the
particular passages: name the actual gene, candidate claim, source subjects and
measurements where assigned; explain which observable differences would support,
qualify or contradict the claim and where the inference is limited.}

For each passage, establish what the paper actually reports and what the words
refer to. Identify the protein, organism, construct or sample; the measurement
or comparison; and the conditions, controls and uncertainty that affect its
meaning. A reported functional label can differ from the activity actually
measured. Distinguish family membership, specific activity, substrate preference,
physiological role and localization when those claims require different evidence.
Use methods, captions, table footnotes or neighboring sentences when they resolve
a missing subject, condition, comparison or qualification.

When the passages concern another protein, retain that protein as the studied
subject. State the relationship that could connect its result to {gene} and
the differences that limit transfer. A result on a homolog can strengthen the
candidate annotation without becoming a direct measurement on {gene}. Keep the
paper's observation separate from your inference about the target.

When passages appear to agree or conflict, compare the actual claims and the
subjects, preparations, measurements and conditions behind them. Determine
whether they test the same proposition or whether a difference explains the
contrast. A qualification elsewhere in the source may narrow an apparently
strong claim. Preserve reported negatives, opposing observations, data-not-shown
limitations and useful corrections. Unavailable access, an unexamined location
and a reported negative result have different meanings.

Keep separate passages separate. Retain each exact quotation with its own source,
representation and byte range. Do not join discontinuous spans into a quotation
the source never contained, infer the text between them or claim that an unread
gap contains no qualification. Two passages or representations of one experiment
do not provide independent experimental support. Revisit a passage when a new
comparison or qualification needs examination; unchanged wording alone is not
another scientific finding.

For source.read, select the actual assigned source, a permitted representation,
a nonnegative UTF-8 byte offset and a positive byte limit. Use the returned
representation and actual start/end when locating or quoting the result. An
incomplete trailing character can make the returned end earlier than the
requested offset plus limit. A returned continuation is an available location,
not a required next action. A text request can fall back to original bytes when
no text projection exists. Coordinates in derived text do not identify locations
in the original XML, PDF or image. A paragraph projection may omit tables,
headings and footnotes; examine an available representation that contains needed
material rather than treating its omission as a biological result.

Use only operations available below and stay within the assigned source and
permitted derivatives. A citation does not supply another paper's contents or
expand this reading assignment. Source registration and prior-delivery metadata
do not establish examination. This passage-reading episode has no child branches.
A one-off read, page extraction or image inspection is an ordinary tool action.

| Available action | What it can establish about {the_gene_or_claim} in this source | Required meaningful inputs and limits |
| --- | --- | --- |
{actual_available_source_examination_reasoning_wait_or_repair_rows}

When the evidence already received supports an answer, record the interpretation
through the existing reasoning action. Preserve actual studied subjects,
conditions, measured or reported results and exact source locations. Explain
what those results support or limit about {gene_or_candidate_function}. Keep
useful partial answers and uncertainty. Navigation, delivered bytes and repeated
reading alone do not establish a scientific conclusion.

Return the information requested about {the_gene_and_this_paper}:

| Requested field | Type and permitted values | Exact biological meaning and necessary qualifications | Recorded fact or your interpretation |
| --- | --- | --- | --- |
{complete_original_parent_requested_fields_and_meanings}

Update only declared interpretation fields using information already received.
A read you are about to select has no known result yet. Parent-supplied initial
values are starting values, not new findings. Recorded fields come from actual
outcomes. Preserve independent valid results if another part of a read or
reasoning commitment fails, and report the specific failed input or result
through the existing permitted fields.

Compare another passage read, context examination, interpretation or repair
using your own action-category yields and the evidence still needed to answer
the biological question. Total yield describes completed own actions, excluding
supplied starting information. Expected next yield concerns another completion
of that category with the reported uncertainty; unavailable is unknown, not
zero. Reading can have zero immediate gain before interpretation. Keep
investigation progress, annotation support and duration estimates separate.
Use compatible duration or wait information when actually available. The
configured controller governs continuation; reaching the end of a passage or
examining every supplied span is not a separate scientific stopping rule.

Use the existing typed JSON response for selection and report_update. If an
available own-history lookup is needed to choose, use its declared
request_context fields: {readable_existing_own_history_lookup_contract}.
Request only information that lookup can supply, then finish this same decision.
The lookup creates no completed action or yield observation. These complete
TASK instructions apply on every exchange, including after a lookup or
reconstruction.

STEERING

| Question about {gene_or_candidate_function} | Current answer or missing evidence | Material qualification |
| --- | --- | --- |
{only_relevant_explicitly_supplied_or_received_question_and_interpretation_rows}

| Relevant own passage examination | Actual source and returned representation | Actual UTF-8 range [start, end) | Result or remaining qualification |
| --- | --- | --- | --- |
{only_relevant_actual_own_read_inputs_and_outcomes}

| Passage needed for this decision | Source, representation and exact byte range | Literal received text |
| --- | --- | --- |
{only_needed_actually_received_passage_rows_keep_separate_spans_separate}

| Reported claim, experiment or comparison | Actual studied subject and conditions | Received result | Meaning or limit for {gene}; source location |
| --- | --- | --- | --- |
{only_relevant_received_evidence_and_admitted_interpretation_rows}

| Own action category | Completed | Total yield | Expected next yield | Uncertainty |
| --- | ---: | ---: | --- | --- |
{actual_saved_own_category_rows}

| Requested interpretation | Current value | Evidence basis or limitation |
| --- | --- | --- |
{current_requested_interpretation_rows}

{only_if_relevant_existing_duration_or_wait_table}
{only_if_present_specific_action_or_return_repair_table}
```

## Fill and decision trace — outside the prompt

The opening uses the parent's exact biological question and actual source name.
Name a candidate function only when assigned. The question can concern an assay,
comparison, qualification, reference protein or other actual biological claim;
this template does not require an enzyme assay or manufacture an experiment.
The assignment-specific instructional fill expands the complete relevant
reasoning guidance, not a process name or a one-line role. Emit the complete
TASK on every dispatch. Current facts and prior outcomes belong only in the
separately built curt STEERING tables.

| Information | Actual producer and selection | Choice enabled |
| --- | --- | --- |
| Gene, biological question, scientific scope, constraints and requested use | Original `EpisodeRequest.goal`, contained scope, message assignment and original `ReportContract.decision`; only explicitly supplied biological context | Which particular claim the passages must answer, and how far this episode may investigate it |
| Source and starting locations | `LiteratureEpisodes.assignment_schema('literature_targeted')`: `reading_assignment_v1`, a source-bound page and `selection.spans` containing actual window operands. `_validate_assignment` requires at least one span, matching assigned source/representation and in-bounds starting offsets. `prepare_assignment` checks source ancestry against the page parent. | Where to begin; no starting read is automatically executed. Later operations remain source-bounded by `_tool_arguments`/`_within_source`, rather than automatically restricted to or traversing the initial list. Explicit parent bounds remain binding. |
| Necessary examined windows, results and literal excerpts | This receiver's actually saved selected operands and `runtime_actions.result`, its latest `last_local_outcome`, explicitly supplied fact cells and its admitted interpretation values | Select an unread context, avoid an unchanged repeat, distinguish two experiments and quote each actual span separately. No source body, linked record or parent's reading is inherited merely from a reference. |
| Window coordinates and representation | `ToolRegistry` source.read contract → `materials.source_window` → returned actual representation, start/end, text, total bytes and nullable continuation | Use valid UTF-8 ranges, preserve text-to-original fallback, avoid fabricated gaps and false coordinate equivalence |
| Own action-category yield and specific inputs | `decision_history.category_for`, `yield_table` and original saved own observations; scoped `lookup_attempts`/`_lookup_detail` | Compare actual read/reason/repair categories using saved signed totals and existing conditional forecasts. Lookup remains inside the pending decision. Parent yields and private child histories are excluded. |
| Requested result meanings and current values | Original typed parent schema and constrained meanings → TASK; current `report_values`/`report_basis` → STEERING | Keep the interpretation connected to what the parent requested. `apply_response` validates the existing update; `finish`/`form_with_facts` supplies recorded facts without a composer call. |

STEERING includes only rows needed for the next choice. Omit irrelevant tables.
Literal passages are exact received evidence, not generated recaps; retain only
the excerpts needed for this comparison. Source labels, biological accessions and
byte coordinates are meaningful operands, while host IDs, hashes, revisions,
custody envelopes, frame metadata and implementation/configuration records stay
outside the model prompt. Unknown information remains unknown. Optional duration
rows use `Proposed read or wait | Existing duration and measured interval |
Support / uncertainty`. Repair rows use `Failed action or field | Actual failure
and affected input | Preserved partial result`.

## Concrete integration gaps

1. The current binding sends `literature_assignment`, custody objects and an
   own-outcome metadata page. It does not build this text, an examined-passage
   table or a biological finding table. `own_outcomes` contains tool/status and
   reference metadata, not the earlier read's source text or byte coverage.
2. Current own-history detail lookup recovers selected inputs, while outcome
   bodies are fingerprinted. It does not restore an earlier uncommitted passage
   or interpretation. Needed old excerpts must be projected from this receiver's
   actual saved outcomes in the future renderer; do not invent a recovery
   capability or add a model recap to cover the gap.
3. `providers._SessionConnection.complete` still sends `json.dumps(context)`
   through a reused native conversation. `model_snapshot` and state frames do
   not implement the required detailed text TASK and terse STEERING. Readable
   operands also need to resolve to existing typed references without exposing
   opaque identities or changing the output schema.
4. The current literature access catalog still includes `state.query`. The
   proposed action rows exclude it, following the user's removal instruction.
   This document does not claim that removal, reference-disclosure correction,
   annotation scoring or prompt integration has been implemented.

The targeted role declares no children. Scientific interpretations use the
existing reasoning commit path, which preserves independent valid rows on
partial failure. Closure freezes the original form from recorded facts and
existing interpretations, releases the closed source and adds no reporting
model call. Yield rows reuse original own observations; this draft changes no
credit calculation, numerical continuation, observation count or endpoint rule.

Read `AGENTS.md`, `GOAL.md`, complete episode/time/task-steering design records,
the complete current literature binding and source-window function, actual
source.read schema and dispatch, relevant complete decision construction,
exchange, response, execution and closure functions, own-yield/history lookup
functions, scientific reasoning-view/commit functions and typed form/provider
consumers. This document is a proposal for the user's running feedback. No
application code, tests, network requests, model calls or scientific runs were
changed or executed.
