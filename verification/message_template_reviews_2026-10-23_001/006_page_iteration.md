# 006 — `literature_page__next_decision`

Review draft only. No application changes, tests, model calls, network requests,
or run changes were made. This template addresses one decision: **where and how
to examine one assigned source to answer the assigned question**. Its consumer
is the page episode, rather than a search strategist, paper selector, or root
annotator.

## Proposed model input

The following is the complete proposed text template. Braced slots are filled
from the producers below. Render tables as Markdown, rather than serialized
objects. Omit an optional table when there are no applicable recorded rows and
say what is unknown. The declared structured JSON output contract stays separate
and unchanged.

```text
You own this within-source investigation. Decide where and how to examine the
assigned source to answer the question. Earlier outcomes can change your reading
approach. A specified one-off read is a tool call; a reading child owns a narrower
iterative question.

Question: {assigned question and the parent's requested information}
Scope and constraints: {readable fixed subject, relevant supplied context,
source restriction, and explicit parent constraints}

Assigned source: {recorded title if known; provider; accession/publication
identifier or URI; retrieval date if known}
Assigned representation: {representation, actual artifact format and size if
recorded; distinguish text fallback to original}
Source relationship: {recorded original/derivative relationship, if relevant}

Observed navigation and access:
| Part or representation | Observed locator / selection | Known content or access limitation |
| --- | --- | --- |
{actual observed headings, table labels, sheet names, physical pages, archive
members, byte continuations, and extraction limits relevant to this choice}

Your examination so far:
| Own action or received reading result | Examined part and approach | Actual outcome / committed interpretation | Still unknown |
| --- | --- | --- | --- |
{actual own selected windows, selectors, statuses, and relevant returned facts;
admitted direct-child values and committed interpretations only}

Pending reading work: {own outstanding reading children and their last observed
states, or none; relevant received progress and duration expectations if any}
Latest feedback: {actual failure or report-repair information, if any}

Available approaches:
| Approach | Available operation or child | Selection needed |
| --- | --- | --- |
{bound ordinary source operations with their necessary operands}
| Table investigation | literature_table | Selected sheet/rows or original-source byte window; narrower scientific question and requested typed return |
| Ordered reading | literature_ordered | Assigned source representation and starting byte window; narrower question and requested typed return |
| Targeted passage investigation | literature_targeted | Separate source-bound byte spans; narrower question and requested typed return |
{other actually available common actions, including reason, wait, and report
redelivery where relevant; do not prescribe a reading order}

Known duration expectations, when relevant:
| Proposed operation / operands | Measured interval | Expected seconds and observed range | Successful samples / other outcome support | Limitation |
| --- | --- | --- | --- | --- |
{existing compatible forecasts only; unknown remains unknown}

Your own category yields:
| Completed action category | Completed actions | Total observed signed yield | Expected yield if completed again | Uncertainty / unavailable reason |
| --- | --- | --- | --- | --- |
{existing own action_yields rows, including available estimate and bounds}

These yields exclude inherited credit. Each received reading child's completion
is one own category occurrence; its internal actions are not yours. An unavailable
estimate is not zero. The bands are approximate working-model uncertainty, not
calibrated guarantees. A read may have zero immediate yield before interpretation.

Return requested by your parent:
| Field | Declared type and allowed meaning | Current value and recorded basis |
| --- | --- | --- |
{the parent's actual requested fields; distinguish recorded facts from your
interpretation fields and preserve allowed values, nullability, and meanings}

{OPTIONAL: exact previously selected passage needed for this decision, with its
readable source identity, actual representation and UTF-8 start/end offsets;
or actual selected image plus the original view/coordinate facts}

Choose one available action using the existing structured response contract:
select_action with selection and report_update. If you need your own earlier
attempts, use request_context and continue this same decision after its reply.
Update only the declared interpretation fields; the runtime supplies recorded
fact fields. Commit scientific interpretations through reason using actual
source subjects, conditions and anchors, and distinguish source claims from
applicability to the fixed target. Navigation, byte coverage and repeated reading
alone earn no scientific credit. Preserve unknowns and separate passages.
The configured controller owns continuation; no reading quota or full-document
requirement applies.
```

The three child rows appear only when they are actually available in this
episode's generated action contract. They describe alternatives, not a required
sequence. A source body is not included merely because it exists. Source title,
content organization, table labels and experimental content stay unknown until
actually supplied or observed.

## Exact producer → presentation → consumer map

| Template part | Existing authoritative producer and relevant fields | Presentation and receiving use |
| --- | --- | --- |
| Assigned question and requested information | `runtime.DecisionSource.next`: `goal = request.goal.as_record()`, `requested_report_purpose = request.report_contract.decision`; `Workflow.binding_context` retains original `request`; `LiteratureEpisodes._PAGE.question_context_refs` identifies supplied records. | Show the actual objective/purpose in words and relevant supplied question records with readable labels. The page episode uses these to decide what information a source read must distinguish. Do not substitute the parent's search query or the overall annotation goal. The current specialist context supplies references rather than materializing their meanings. |
| Fixed scope and constraints | `DecisionSource.scope`; original `BindingContext.request`/assignment; `LiteratureEpisodes._PAGE.source_ref`, `representation`, `artifact_ref`. `prepare_assignment`, `_validate_page`, `_within_source` and `_tool_arguments` enforce these operands. | State the fixed subject and meaningful source boundary. Preserve explicit constraints. The page may operate on that source and actual derivatives; a new unrelated source or acquisition/search is outside its role. No new memory/time/concurrency quota is inferred. |
| Source identity | `WorkflowServices.read_record` → store source record: `provider`, `accession`, `uri`, `retrieved_at`; `domain.RECORD_SCHEMAS['source']`; optional recorded `publication_identifiers`; any actually received linked bibliographic record's `label`/`accession`. | Show provider plus accession/publication identifier/URI. A title is shown only when actually recorded and linked to this source; the source schema has no universal title field. DOI/PMCID are public bibliographic identity, rather than internal opaque record IDs. No article read or network lookup is performed to decorate the prompt. |
| Representation and custody | `LiteratureEpisodes.decision_context.literature_source_custody`; `_artifact`; assigned artifact record `size`/media type; `materials.source_window` returns the actual `representation`, `available_representations`, `total_bytes`; `tools._publish_document` returns `source_derivative` facts and `parent_source_refs`. | Show actual representation, known format/size and original/derivative relationship. `text` without `text_ref` falls back to original bytes; do not falsely label that content a paragraph projection. PDF derivative byte offsets are normalized text coordinates, rather than original PDF offsets; physical page numbers remain separate. Internal artifact IDs, hashes and implementation/software versions stay in saved records. |
| Observed navigation | Original selected own action arguments and result in `runtime_actions`; `materials.source_window`: `start`, `end`, `next_offset`, `next_query`, `text`; `tools._publish_document`: actual archive `members`/pagination, PDF `page_count`/page/coordinate system; actual XLSX result `sheets`, selected rows/cell addresses/header information; admitted reading results only. | Show exact already observed names, selectors, positions and limitations. A byte offset is a usable locator, not a heading. An inventory is navigation rather than evidence that any member/table was examined. Do not auto-extract headings/tables from unselected article bytes or infer a complete content map from partial windows. |
| Own examination and outcomes | `DecisionSource.last_outcome`/`last_outcome_index` and `local_outcome_preview`; own durable `runtime_actions.action` and `.result`; relevant committed scientific records in `working_state`; `view.child_reports` contains admitted direct-child forms. `LiteratureEpisodes.decision_context.own_literature_outcomes` is a metadata index only. | Render factual selectors and status, actual pertinent returned values and constrained committed interpretation relationships. Avoid a new model summary/composer. Label unsuccessful/partial attempts accurately. Inherited `prior_delivery_refs` are provenance, not examination coverage. A read window shows delivery, not understanding or absence from the whole source. Direct-child facts cross only through the original admitted typed form. |
| Pending work and feedback | `Workflow.pending_work(self)` returns this episode's commissions; `DecisionSource.feedback`, `report_deliveries`; existing `waiting_support` progress and duration inputs from `DecisionSource.call`. | Show only pending reading work and the facts needed to choose a follow-up/wait or repair. Do not expose descendants' private histories or treat a quiet interval as exhaustion. Preserve explicit selected waits and current runtime ownership. No automatic polling, follow-up, retry, cancellation or wait is introduced. |
| Ordinary next approaches | `LiteratureEpisodes.catalog(context)` filters actual `services.tool_catalog(scope)`: `_ACCESS_TOOLS`; `Workflow.catalog` appends applicable common inspection/instruction tools and removes `episode.history` under the decision exchange protocol. | Present available operations as text with exact required operands and optional defaults/allowed values where needed. Examples include source byte reads, native structure inventory, exact sheet rows, PDF text/page extraction and image viewing. Retain bound options without making an infrastructure choice about their scientific value; no full catalog/schema/configuration dump. A rendering operation alone does not deliver pixels; `image.view` does. |
| Three reading children | `_CHILDREN['literature_page']`; `assignment_schema(role)`; `prepare_assignment`; `runtime.Workflow.action_schema`, `available_child_roles` and `selected`. | Show only available `literature_table`, `literature_ordered`, `literature_targeted` alternatives. Table selection is either `_TABLE` (source, observed sheet key, offset/limit, nullable selected header/filter) or `_WINDOW`; ordered selection is one `_WINDOW`; targeted selection is an array of separate `_WINDOW` spans. Child assignments retain their complete page custody/question/provenance operands internally. The parent supplies narrower goal/scope/purpose, original typed schema and initial interpretation values. No child auto-runs or predetermined order/number is added. |
| Duration table | `DecisionSource.call` supplies existing `resource_tool_estimates` and native expectations; `ResourceToolEstimator` fields include `status`, `successful_duration_samples`, `expected_total_seconds`, observed minimum/maximum, `forecast_duration_measure`, `outcome_support`; literature catalog's `execution.estimate` is limited to XLSX sheets/rows branches. | Show a forecast only for its actual proposed compatible operands, measured interval and original support. Failed/censored/unmeasured outcomes and absent history remain explicit. Do not turn duration into scientific yield or invent a duration estimate for a reading child/PDF/read from another operation's samples. This table selects no action or resource. |
| Own category yield table | `runtime.DecisionSource.exchange_decision` calls `decision_history.yield_table` with this `episode_id` before this decision; `model_snapshot` adds `action_yields`; rows contain `category`, `completed_actions`, `total_yield`, `expected_yield.status`, `.band`, `.unavailable_reason`, `attempted_uncompleted`. `yield_table` uses original saved controller marginal gains, ordered by completion. | Copy numbers and statuses exactly into readable rows; display the band estimate/lower/upper as available. Keep attempted/uncompleted separate if shown. No parent/child yield history, inherited cumulative baseline, score recomputation, rescaling or new controller effect. An absent category row is unobserved; do not fabricate a zero-yield row for an untried alternative. |
| Parent's requested return table | `requested_form`, `requested_report_purpose`, `current_report_update`, `current_report_basis_refs` in `DecisionSource.next`; original `TypedReportContract`; `communication.interpretation_schema` excludes `x-source` fact fields. | Render each actual field name with type, arrays/items, nullability, allowed codes/semantic reference meaning and description. Use exact current interpretation values and already recorded basis. Mark runtime-owned fact fields as facts; never ask the model to compose them. The table is a human-readable description, rather than a JSON schema dump. No fixed page-report form is invented. |
| Optional selected passage/image | Previously received exact own `source.read.result.text` plus actual source/representation/`start`/`end`; supplied already selected passages; current `visual_evidence` is derived from the most recent completed own `image.view` in `DecisionSource.next`. | Include only the actual selected passage/visual needed for this choice, retaining exact anchors and separate spans. Do not include an entire article, all prior source bodies, or a reading child's private image/reads. Do not restore an older image after another action. |
| Same-decision lookup and dispatch | `DecisionSource.exchange_schema`/`exchange_response` and `decision_history.lookup_schema`; `exchange_decision` → `provider.complete`; `providers._SessionConnection.complete` currently constructs user text using `json.dumps(context)` and passes the existing `outputSchema`; `apply_response` → `selected` → specialist validation/execution. | The proposed text renderer replaces the user text presentation for this template. The `select_action`/`request_context` response contract, JSON decoding, tool/assignment validation and actual dispatch remain unchanged. Lookup services the pending decision and creates no action observation. |
| Fact return, credit and continuation | `LiteratureEpisodes.fact_sources`/`facts` return no extra literature-specific facts; common `Workflow.facts` supplies actual changed scientific records and original report basis; `form_with_facts` inserts selected `x-source` facts; `LiteratureEpisodes.validate_report` → `validate_form`; `credit_view` → `WorkflowServices.scientific_credit`; common completed-action/controller path. | Existing parent-defined typed JSON closes through the same validation and projection. One completed own action supplies one local observation. The template introduces no new score, category estimator, completion gate or stop action. Navigation/reading is not independently assigned scientific value by a label. |

## Current presentation gaps, not claims of existing behavior

1. `LiteratureEpisodes.decision_context` currently returns assignments/custody
   largely as references; it does not materialize the question, readable source
   identity, known navigation or selected passage. These are projection needs
   using actual supplied/received records, rather than authorization for new
   acquisition or an extra model composer.
2. `WorkflowServices.own_outcomes` returns metadata with `result_ref = None`.
   The literature caller selects the earliest page (default eight rows) and
   filters out PDF info/page, archive inventory/extraction and XLSX sheet
   inventory. It does not include examined source windows or content. In
   particular, `source.read` publishes no new record references, so its metadata
   row cannot reconstruct either selected text or its actual returned bounds.
   The authoritative already-delivered selectors/results are in the episode's
   own `runtime_actions`; presentation must use those facts without claiming a
   complete examination from that bounded index.
3. Under `decision_exchange_v1`, `request_context` currently returns own attempt
   metadata, bounded selected inputs and publication references. Detail lookup
   slices **selected inputs only**. `outcome_summary` fingerprints a saved
   outcome; it is not its text. Therefore this lookup does not currently restore
   exact earlier uncommitted `source.read` outcomes after conversation loss.
   The prompt must not promise that ability. Exact already received navigation
   and relevant selected content must be presented from authoritative saved
   own results, or left explicitly unavailable. No lookup expansion is made in
   this review.
4. The no-opaque-ID input requirement needs a shared presentation binding:
   readable source/record designators must map unambiguously to the original
   references before unchanged validation. Current tool/reason/child JSON
   operands require exact references. Display labels alone do not implement
   that inverse mapping. This draft neither invents executable aliases nor
   silently changes the output schema; this integration remains explicit for
   the root review.

## Omitted material and why

| Omit from this page prompt | Reason |
| --- | --- |
| Whole internal JSON context/frame, schema/configuration dumps, revision/base hashes, implementation pins, run/episode IDs and opaque source/artifact IDs | Internal storage/replay/binding information does not tell this episode where to read. Keep it durable internally; expose readable identity, exact usable coordinates and declared field meanings. |
| Search-provider queries, candidate paper lists, parent/root search history and alternative whole-investigation plans | This decision is within one assigned source. Those belong to other receiving decisions unless a specific already supplied fact is needed to interpret this source. |
| Full article/supplement, every old tool body, all parent receipts, archived contexts and child-private histories | The decision needs relevant observed navigation, exact own outcomes and admitted child values. Bulk inclusion weakens scope and can falsely imply reading/understanding. |
| Parent yields, child internal yields, inherited baseline as new gain, raw estimator training history and controller/configuration internals | Only this episode's existing own category yield/uncertainty informs its next reading approach here. Its controller stays authoritative. |
| Annotation-support vector/account dump and global timing/scientific history | No role in choosing the next within-source examination unless an explicitly supplied narrow fact is relevant. Never conflate annotation support with investigation progress or duration. |
| Invented headings, inferred table coverage, assumed absence, fabricated transfer estimates, reading order/quotas and completion/approval gates | These are not recorded facts or authorized decisions. Unknowns stay unknown; the episode owns choice and the configured controller owns continuation. |

Inspected: complete `literature_episodes.py`, `episode_services.py`,
`episode_bindings.py`, `decision_context.py`, provider dispatch, shared runtime
decision/context/action/child/form/fact consumers, `method_loop` direct-child
input/report boundary, `communication.py` form guard, category-yield producer,
source-window and document publication paths, and the required design records.
No scientific/model execution or behavioral verification is claimed.
