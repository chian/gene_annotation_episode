# Proposed exact own-outcome intermediate

This is an internal deterministic projection, not model-facing JSON, a new fact
source, or a new scoring sheet. It is returned only for the owning UniProt
results episode's exact acquisition. Other services and other tools retain
their existing path. No application implementation is included.

## Port and immutable operands

`UniProtReturns.own_outcome_view(context: BindingContext, outcome: dict) -> dict`

The caller is the new UniProt branch of
`Workflow.local_outcome_preview(outcome, *, decision_index=None, source=None)`.
`DecisionSource.next` passes `source=self`; the branch uses
`Workflow.binding_context(source)`. Required identities are checked internally:

1. Role `results`; original results assignment and handoff; target service
   `uniprot`; selected acquisition `api.uniprot.collect`; same run/episode/scope.
2. Exact original parent report schema. Extract its one registered selected
   source using R's `requested_uniprot_selection`; no extra selection storage.
3. Original acquisition receipt's action key, snapshot, and saved outcome.
   R/`read_result` must select that exact action, not any result indexed by the
   same source. Compare the full saved outcome and original assigned request.
4. The existing P/B publication, native bytes, actual stored bindings and only
   requested sequence-artifact bytes are authenticated through R's existing
   proposed reader. A presentation call does not publish or reparse to create
   new observations. Parsing/projection for selected text remains deterministic.

Integrity conflict uses R's existing declared boundary diagnostic. It must not
fall back to the raw native outcome. An unrequested selected source produces
`selection_state=not_requested` and zero selected pages; it never implies
all-fields selection. A partial acquisition whose source survived but publication
did not has `publication_state=unavailable`, nullable parser facts, and the
actual existing projection failure. Do not manufacture a page or record count.

## Closed top-level shape

All shown properties are required; there are no additional properties. `?`
means nullable, never an inferred zero. The outer status is copied unchanged.

```text
OwnOutcomeView = {
  status: completed | partial,
  record_refs: [],
  changed_record_refs: [],
  result: {
    representation: "uniprot_own_outcome_view_v1",
    operation: "api.uniprot.collect",
    selection_state: requested | not_requested,
    publication_state: available | unavailable,
    acquisition: Acquisition,
    requested_pages: DecisionPage[],
    failures: R.Failure[]
  },
  feedback: null | { category: ExistingFeedbackCategory, code: ExistingFeedbackCode }
}

Acquisition = {
  native_response_retained: boolean,
  operation: record | search | unknown,
  response_body_state: (complete_json | invalid_json | invalid_envelope)?,
  parser_projection_state: (complete | partial | invalid)?,
  native_record_count: nonnegative_integer?,
  parser_eligible_record_count: nonnegative_integer?,
  bound_record_count: nonnegative_integer?,
  selection_extent: one_record | one_selected_page | not_established,
  pagination_metadata_available: boolean?,
  next_state: (present | absent | unknown | invalid | not_applicable)?,
  whole_query_complete: boolean?,
  issues: R.Issue[],
  unselected_issue_count: nonnegative_integer
}

DecisionPage = {
  page_selection_index: nonnegative_integer,
  status: R.PageStatus,
  page_fields: R.PageFieldReply[],
  records: DecisionRecord[],
  issues: R.Issue[],
  source_grant_status: not_requested | available | unavailable,
  failures: R.Failure[]
}

DecisionRecord = {
  record_selection_index: nonnegative_integer,
  requested_record_ordinal: nonnegative_integer?,
  state: bound | parser_unpublishable | binding_omitted | not_in_response | unavailable,
  fields: R.RecordFieldReply[],
  issues: R.Issue[],
  sequence_grant_status: not_requested | available | unavailable,
  failures: R.Failure[]
}
```

`R.<name>` means exactly the corresponding definition under `return_schema.$defs`
in `../tool_graders_uniprot_requested_returns_2026-10-28_601/PROPOSED_SELECTED_RETURN_SCHEMA_002.json`.
It is not a new, copied interpretation of those definitions. `R.RecordFieldReply`
includes request index, the original selected field clause, availability status,
the exact typed scalar/window/collection, and constrained failures. Record and
page selection arrays preserve parent clause order; selected native members
preserve their original order and owner-local ordinals. No hidden preview limit
or shortening is applied to the explicitly requested values.

`requested_record_ordinal` follows R's exact schema nullability for unmatched
accession clauses. It is an original native position, never an index into the
filtered publication list. No witness, `source_grant` or `sequence_grant` object
is copied into this intermediate. Empty outer reference arrays are presentation
fields only; they do not replace the actual outcome arrays or own receipts.

## Exact construction

* Authenticate the actual current outcome. Do not call `facts(context, schema)`
  and copy its all-acquisition history into the next decision.
* For every original `assigned_page` selection clause, call R's one-page
  `project_uniprot_page` on **this exact outcome's** authenticated publication,
  native bytes, outer status/count/errors/qualifications, and that clause.
  `received_publication` is invalid for this results-role assignment under R's
  existing selection rules. Repeated acquisitions of this same assigned page
  remain separate original facts at closure, without being dumped here.
* Copy each projected `PageReply` to `DecisionPage` by the exact field list above.
  Copy each `RecordReply` to `DecisionRecord` by the exact field list above.
  This removes only witness/material-grant objects. Never flatten selected
  values, reinterpret ECO codes, count studies, translate coordinates again, or
  recompute P's observed sequence length.
* `Acquisition` copies P's corresponding page values, renaming
  `projection_state` and `publishable_record_count` as shown. Its bound count
  copies outer `result.count` and must equal `len(publication.records)`.
  `native_response_retained` comes from successful original snapshot/source
  custody validation, not a claimed filename or service label.
* `Acquisition.issues` is the stable de-duplicated union of page-wide issues and
  issues affecting selected record/field/grant clauses, selected using R's
  origin/index semantics. It contains no unselected field text. Retain the
  count of omitted issues in `unselected_issue_count`; count each original
  origin/index once even when clauses overlap. A no-selection view keeps only
  page-wide material acquisition issues plus that omitted count.
* `feedback` copies category/code only. Field-level error context is already
  present in selected typed issues/failures. Never leave raw `feedback.rows`,
  diagnostic artifact refs or arbitrary exception text as a second route.
* No `operation_ref`, source/native artifact/reference/sequence IDs, content
  digests, run/episode IDs, saved contexts, native sections or unrequested
  sequence/name/description fields occur at this outer boundary.

Selected replies still contain their exact native provenance pointers and
scientific identity checks such as a sequence-window checksum, as required by
R. Those internal typed values are filtered structurally by the text renderer:
custody/sequence checksums and native pointers are not printed as tracking text.
Native feature/evidence owner relationships become concise semantic labels;
explicitly selected biological accessions, GO/ECO tokens, values and units remain
facts. An explicitly selected checksum still remains exact in the parent typed
return; this continuation text needs only its supplied availability/conflict
qualification.

## Text-render input, separate from this outcome

The renderer receives the existing reconstructed decision state and the view
above. It obtains these separate quantities without deriving new ones:

| Information | Exact existing input | Rendering rule |
| --- | --- | --- |
| Full recurring work | `DecisionSource.instructions(context)`, original goal/scope/assignment, selected substantive instruction sections, original report schema | Expand full TASK every time. No history budget applies. |
| Own category yields | `action_yields.rows` from `decision_history.yield_table` | Category; completed actions; total signed yield; expected next yield; uncertainty/unavailable reason; uncompleted attempts. Do not invent missing rows or values. |
| Continuation | `controller.estimate.expected_next_gain`, its band/status, existing continuation cost | Preserve exact supplied values. This is distinct from category-conditional expectations. Never replace a category estimate with the terminal controller estimate. |
| Current requested interpretation | `current_report_update`, constrained by original interpretation schema | Render only necessary declared interpretation values, if any. Recorded R facts are populated by the host. |
| Waiting | Already received `pending_work`, relevant `waiting_support`, compatible duration facts | Render only when they affect an available wait; no invented UniProt pending job or polling cadence. |
| Failure repair | Actual constrained `feedback` and selected issues/failures | Specific requested target/field, actual state, code/meaning. No paragraphs of raw native data. |

No parent's yield table, private report composition, automatic own-history lookup,
child-private reasoning, global latest publication, new score or instruction to
select more work is an input to this view.
