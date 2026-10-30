# Own-outcome intermediate — additive decision-relevance correction 003

This supersedes the copied `DecisionPage`/`DecisionRecord` selected-value
branches in 002 for the concrete retained-response boundary in TASK002. 001
and 002 remain preserved. The full TASK002 is unchanged. No application or
prompt implementation is included.

The parent-defined typed return and this episode's decision view have distinct
purposes. `R.PageReply` and `R.RecordFieldReply` remain complete typed returns;
their values are not copied into the own-decision intermediate. The correction
does not narrow the original requested return or alter the retained
`outcome.result.uniprot_publication`.

## Unchanged authentication and port

`UniProtReturns.own_outcome_view(context: BindingContext, outcome: dict) -> dict`

`DecisionSource.next` passes the actual source to
`Workflow.local_outcome_preview(outcome, *, decision_index=None, source=None)`.
The UniProt branch uses `Workflow.binding_context(source)` and the original
report contract, assignment, handoff and selected action. Authenticate the
exact receipt `operation_key` through `UniProtReturns.read_own` /
`APIServiceExecution.read_result`, and compare the entire supplied outcome with
the saved outcome. Do not take a first source match or aggregate own history.
The reader's custody checks, selected projection and original native bytes are
unchanged. Boundary conflicts never fall back to raw outcome JSON.

At this inspection, `UniProtReturns.read_own(..., operation_key=...)`,
`APIServiceExecution.read_result(..., operation_key=...)` and
`project_uniprot_page` are present in source. The own-outcome projection and
its runtime/provider wiring remain the unimplemented subject of this proposal.
Source presence is not a claim that their execution was verified here.

## Corrected closed shape

All shown object properties are required; no additional properties. `?` means
nullable, never an inferred zero. Empty reference arrays are presentation
fields and never replace the full acquisition's receipt or credit input.

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
    acquisition: {
      native_response_retained: boolean,
      input_policy: same_retained_response,
      response_body_state: (complete_json | invalid_json | invalid_envelope)?,
      parser_projection_state: (complete | partial | invalid)?
    },
    requested_coverage: Coverage[],
    conditions: Condition[]
  },
  feedback: null | { category: ExistingFeedbackCategory, code: ExistingFeedbackCode }
}

Coverage = {
  page_selection_index: nonnegative_integer,
  record_selection_index: nonnegative_integer,
  requested_record_reply_count: nonnegative_integer,
  bound_record_reply_count: nonnegative_integer,
  other_selected_fields_available: boolean
}

Condition = {
  target: {
    page_selection_index: nonnegative_integer?,
    record_selection_index: nonnegative_integer?,
    native_record_ordinal: nonnegative_integer?,
    field_selection_index: nonnegative_integer?,
    acquisition_field: (legacy_label | legacy_term)?
  },
  stage: acquisition | native_parser | binding | selected_return | legacy_projection,
  code: ExistingDeclaredCode,
  selected_status: available | partial | unavailable | not_applicable,
  native_state: present | absent | null | invalid | unknown | not_applicable,
  member_extent: null | {
    matched_count: nonnegative_integer,
    indeterminate_count: nonnegative_integer,
    unavailable_count: nonnegative_integer
  }
}
```

`same_retained_response` is deliberately the only input policy in this concrete
template. It is verified against the immutable empty selector and the original
prepared action's `cache_original`. Do not infer it from a service name. A
different original acquisition mode needs its actual applicable instructions
and decision trace before this concrete template is reused; do not silently
render it as retained input or fall back to raw values.

`ExistingDeclaredCode` means an exact P/B issue or projection-error code, or an
R selected-failure code. It is not unrestricted diagnostic prose. Its origin is
the declared `stage`; no new scientific reason or retry classifier is inferred.
The original structured code and its selector/native-position association must
be retained for every displayed condition. When an existing code's structured
member qualification is needed (for example fuzzy location), the deterministic
mapping uses that existing qualification to choose the fixed rendering phrase;
it does not quote native values or arbitrary exception text.

Targets are request locators, not biological identities or material references.
The renderer resolves their field names using the immutable original selection
already described in TASK002. It may print an original native position and a
selected field name. It does not print a returned accession, source pointer,
sequence checksum, witness ID or native member value. A page-level failure uses
null subordinate locators; this is a condition, not a fabricated null-ordinal
`R.RecordReply`. Every actual record reply keeps R's non-null native ordinal.

## Deterministic reduction

1. Authenticate and project this exact outcome using the original selected
   schema. Use R's selected replies only as internal inputs to this reduction.
   Do not call the all-acquisition `facts` path for a next-decision view.
2. For each original record-selection clause, `Coverage` counts its record
   replies and the replies with `state == bound`. Repeated/overlapping clauses
   retain separate request indices; these are reply counts, not unique-protein
   counts, credit or confidence. In the fixture's one all-native-records clause,
   the counts are 3 requested and 2 bound. Missing publication yields no coverage
   row plus `publication_unavailable`, not invented zeros.
3. Emit a record-level condition for an unavailable selected record. Its field
   failures are covered by that condition rather than duplicated seven times.
   Emit the relevant narrower conditions for selected partial/unavailable
   fields and any acquisition qualification that explains outer partiality.
   In the fixture these are the malformed record, legacy name representations,
   indeterminate selected collections and absent requested fields.
4. Copy `selected_status` from the affected R field, or map the existing R
   record state to its declared unavailability. Native state copies the
   corresponding qualified field/container state. An outer legacy error can
   coexist with `selected_status=available` and `native_state=present`. Do not
   force a usable selected window to partial merely because a legacy label or
   another selected field failed. `not_applicable` is used only when the
   acquisition condition has no selected cell to which status could attach.
5. For a qualified selected collection only, `member_extent` copies R's matched,
   indeterminate and unavailable counts. The fixture thus preserves 2 matched /
   1 indeterminate for the requested cross-reference collection and 1 matched /
   1 indeterminate for the requested feature collection. It carries no member
   rows, identifiers, properties, coordinates, evidence or excluded count.
   Matched does not imply that every nested requested property is available;
   any requested nested failure retains its own condition. No counts are used
   as scientific scores.
6. `other_selected_fields_available=true` only after checking every selected
   field outside those explicit field/record conditions is `available` in R.
   Unknown/missing replies are a boundary diagnostic, not silent availability.
   Present empty collections need no exception row. Native absent/null/invalid
   requests keep the original distinct condition. A false availability flag
   must be accompanied by the actual specific unresolved condition; it cannot
   stand in for a dump of remaining values.
7. The text renderer merges only semantically identical, adjacent qualifications
   for the same original request, such as the two legacy-name representation
   errors or two absent selected fields at one record. It retains all their
   internal codes. It never generates a new scientific interpretation.
8. Keep outer status, response-body validity and parser status separate. Do not
   copy whole-page totals in place of selected coverage. No query-total,
   pagination, release, text-length, residue, native coordinate or biological
   scalar property exists in this intermediate.

When the original schema has no selected source, preserve the earlier
`selection_state=not_requested` rule, empty requested coverage and only the
material acquisition condition. This does not select all native fields.
Missing publication preserves the existing saved acquisition and specific
failure. It never triggers a reparse of historical data to invent a publication.

The full typed return still carries original selections, requested values,
native field states, membership rows/counts, intervals, evidence, pointers and
explicit grants exactly as R requires. Projection for this message cannot
mutate those facts or install a second return schema.

## Separate rendering inputs: available choices and continuation

The own outcome supplies acquired facts. The reconstructed decision context
supplies the actual callable catalog and already received wait/progress facts;
those are not invented by `own_outcome_view` or read from private history.

* For TASK002, the catalog's sole acquisition is empty-argument
  `api.uniprot.collect`; knowledge operations can supply instructions but cannot
  edit the native response or enable another tool. The fixture may state that
  no native-content/parser-repair operation is supplied because that was
  checked against this catalog. This is an operation-availability fact, not a
  decision to stop or a general claim that every failure is irreparable.
* An existing repair condition or relevant wait target is rendered only from
  actual received information and only when usable with an available action.
  The fixture supplies none. Shared timer waits remain selectable; no pending
  UniProt job or expected future data change is inferred from partiality.
* The existing own category-yield table and controller values are copied
  unchanged. Category expectation remains distinct from the controller's
  continuation expectation. No failure count, record count or projection is a
  new observation or new score.
* `feedback` contains only the existing constrained category/code. Raw rows,
  exception paragraphs, stored contexts and reference handles are not secondary
  ways to expose the removed values. Actual repair-relevant feedback belongs in
  the precise condition it qualifies.

Compact before `runtime._references_in`. Keep specialist `Workflow.working_state`
assignment-only; do not add native records or copy the typed return into it.
The narrow results text renderer must also exclude native values from duplicated
feedback, `execution_progress`, target descriptions, raw forms, schema traversal,
saved-frame reconstruction and request-context continuation. Its fallback
cannot be `json.dumps` of the full original result. These are unchanged required
future integration checks, with this stricter value-free own view.

No automatic retry, different selector, new page, return action, stop action,
approval gate or extra completion turn is introduced. Full TASK002 recurs;
the latest partial STEERING is `STEERING_FIXTURES_003.md`.
