# Current pages and reference inspection

This development tree exposes one ordinary `state.query` path for exact records,
historical pages, current revision pages and semantic reference filters. Queries
do not revise scientific state, invalidate observations, infer dependency truth,
or choose the Episode's next investigation. A selected successful read is one
ordinary action with its actual progress; automatic working-view construction
is not a selected action.

## Follow the working view

Each list under `reasoning_view.pages` supplies `next_query` as well as its
offset, limit, total, next offset and current-only flag. Pass that exact query
to `state.query` to continue the same selection and order. For example:

```json
{"kind":"assessment","current_only":true,"offset":10,"limit":10}
```

Current assessment and annotation pages use the authoritative current revision
pointers and their existing key order. Historical pages default to
`current_only:false` and preserve the existing record-ID order. Immutable record
kinds have the same membership under either selector. A collection can change
between separate calls when new work commits; each individual page's records,
count and continuation are read from one database snapshot.

The virtual `kind:"subject"` pages assigned original inputs, features and products
in that order, with stable IDs within each group. It does not materialize the
whole subject inventory to produce one page. This changes the ordinary query
path; it does not claim that every other current-input surface is bounded.

## Inspect actual references

The optional nonempty `references` array OR-matches actual reference positions:
`ref`, `*_ref`, members of `*_refs`, and `dependencies`. Actual provenance fields
inside anchors, including source and artifact references, remain references.
A row's own ID and an ID merely mentioned in quoted text do not create edges.
Duplicate requested references normalize to one selector. Every supplied
reference must exist at the boundary.

For example, an Episode can query current assessments naming a changed
hypothesis, including through `assumption_refs`, using:

```python
arguments = {
    "kind": "assessment",
    "current_only": True,
    "references": [changed_hypothesis_ref],
    "limit": 10,
}
```

The page contains `reference_matches` with `record_ref`, `reference_ref` and the
exact `field_path`. Its `next_query` retains all selectors. This is a projection
of existing authoritative records, not a second dependency registry. A reference
does not by itself say whether an assumption is necessary, sufficient, disputed
or an alternative. The owner interprets those relationships and may revise its
assessments or annotations while retaining unchanged measurements.

## Exact reference mode

`{"refs":[...]}` retrieves exactly those records. `{"refs":[]}` retrieves an
empty list. Exact reference mode cannot be combined with `kind`, `offset`,
`limit`, `current_only` or `references`: those requests return the specific
`exact_refs_cannot_be_combined_with_page_selectors` contract feedback instead of
silently ignoring a selector. Its structured `detail` names the actual supplied
`conflicting_fields`, identifies `selection_mode:"exact_references"`, and gives
`allowed_fields:["refs"]`. The parameter description also explains the separate
mode. This feedback does not drop arguments, retry the call, or choose a new
query for the Episode. Historical rows remain readable by exact reference.
Existing assigned-scope checks still apply; reusable external evidence does not
become a new target through either query mode.

## Verification scope

Local fixtures in `tests/test_state_query.py` and
`tests/test_state_query_tools.py` exercise current-page continuation across
revisions, reverse-reference paths including anchors, exclusion of quoted IDs,
scope, SQL subject paging, exact-empty mode, conflicting selectors and durable
replay. These checks establish the ordinary access path. They do not demonstrate
that a model has used a changed biological assumption to repair its dependents.
