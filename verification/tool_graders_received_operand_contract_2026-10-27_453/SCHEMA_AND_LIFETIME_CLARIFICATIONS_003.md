# Additive precision to 453/001

This record tightens two technical phrases and completes the private/public
data contract. It supersedes only those ambiguous phrases in the unapproved
453/001 proposal, not any user requirement or existing implementation.

## Three schemas, in the existing order

The wording in 001, "decode ... against the saved generation schema first,"
means the **adapted semantic input schema**, not the provider's already encoded
output schema. The actual source requires this distinction:

1. `original_action_schema`: immutable original exact action and report schema.
2. `operand_action_schema`: a detached copy of 1 with the strict marker allowed
   only at the declared leaf locations. This retains the original schema's
   encoded-assignment/tool-argument annotations and complete schema resources.
3. `generation_schema`: the existing `_action_generation_schema` conversion of
   the exchange envelope containing 2. This is supplied to the provider.

`_decode_action_response` consumes 2, so it can identify and parse existing
JSON-encoded assignment/argument fields. Validate the decoded response against
2; resolve markers; validate the result against 1; admit/execute using 1's
ordinary existing path. Merely supplying 3 to the existing decoder would leave
an assignment encoded as a string and is not the proposed implementation.

Refine the design stub in 001 as follows:

```python
def received_operand_schemas(
    original_action_schema: dict,
    *, enabled_uses: tuple[str, ...],
) -> OperandSchemaPair:
    # Return operand_action_schema and generation_schema;
    # preserve original_action_schema separately and exactly.
    ...
```

Exact original operation-contract lookup remains unchanged. TASK information
explains the marker substitution and its allowed locations; the provider
generation contract includes those alternatives. There is no claim that the
original operation itself now accepts a choice marker.

The slot enum in an adapter failure is explicitly
`query_ref | reference_ref | handoff_ref | saved_sheet | saved_sheet_file | null`.
The phrase "four exact slot kinds" in 001 was a counting error; these are the
five actual field names. A failure exposes neither the exact private descriptor
nor a private receipt identity.

## Exact family carrier records

The family ports return one private carrier for each actual requested delivery
occurrence; all fields below are required, and an inapplicable field is null:

```text
AuthenticatedReceivedField = {
  family: protein_structure | genomic_overlap,
  receiver: exact BindingContext identity/scope,
  witness: exact successful received return and its frozen-prefix membership,
  field: {top_level_name, declared_x_source, row_ordinal},
  returned_value: exact original typed returned value,
  kind: structure_sequence | protein_saved_sheet | genomic_overlap_saved_sheet,
  original_origin: exact authenticated result identity,
  handoff_ref: exact selected original handoff,
  allowed_uses: existing granted use values,
  supplied_metadata: exact request/selector/labels already supplied to receiver,
  received_measurements: exact separately requested projection occurrences
}
```

`received_measurements` is an ordered sequence, never a merged "latest" row.
Each occurrence retains its witness, exact original selector/parameters and
original returned projection. The carrier contains no newly read native data.
The private record type can hold exact existing typed records rather than
introducing a second copy of every scientific schema. Its equality and
canonical serialization compare full values, not only hashes.

`ReceivedOperandSnapshot` has required version/run/receiver/decision/scope,
original schema and catalog associations, frozen received prefix and entries.
Each entry has required choice/kind/allowed-use/allowed-slot list,
exact original operand(s), original origin, witness list and scientific view.
The scientific view is a family-specific closed projection with explicit
availability; it does not inherit arbitrary keys from `returned_value`.

`ReceivedOperandPage` is exactly `{view, use, total, offset, limit, choices}`,
where `view="received_operands"`, the three use values and page bounds are
those in 001, and each choice has exactly `{choice, kind, scientific_view}`.
001's abbreviated host-side page omitted the required discriminating `view`;
the explicit form here enables the existing lookup renderer without inference.
An empty requested page is an empty choices list; it does not change total,
invent an operand or choose a replacement.

`ResolvedReceivedSelection` is exactly `{selection, resolution}`. `selection`
is the expanded ordinary selected action. `resolution` is private and contains
the saved binding association, the exact raw selected action, and one ordered
row per replaced slot with choice/witness/exact copied value. Persist the
resolution before ordinary admission; a restart verifies it against the same
saved raw response and snapshot. An invalid selection creates no runtime action.
The original report update is unchanged and validated under its original form.

## Exposure, repeated lookups and durable identity

Choice integers address entries only within one saved decision. The private
snapshot owns the stable integer assignment. The existing dispatch envelope
and journal bind every response to that decision; a model cannot supply a run,
episode, source, hash or binding identifier to redirect resolution.

Exposure is the set union of choices in actual successfully journaled public
pages or explicit initial displays from this saved snapshot. It is rebuilt from
the exact frozen initial display and public exchange prefix. Repeated pages do
not add a new scientific contribution. A failed lookup exposes nothing.
Reconstruction validates every reply against its original query and snapshot.
Do not add an in-memory-only exposure flag or silently widen a saved page.

A later decision gets its own snapshot and numbers. It can expose an old
received object again if the existing receipt authority still permits it. That
is retrieval of an old contribution, not new scientific work. Historical
actions keep their exact original operands and numbers in old public exchanges
keep their old decision meaning. Never translate old choices using a later map.

No original-and-later calculation collapse is permitted. A selectable saved
sheet may have several associated received projections with differing exact
parameters; each remains a distinct calculation occurrence. In the retained
overlap example, threshold 1 bp and threshold 4 bp are separate sections even
though unfiltered fields and the sheet identity agree.

The model can choose among duplicate labels using the local choice addresses.
If it needs scientific distinctions absent from supplied information, it owns
that uncertainty and may choose appropriate further work. The adapter does not
invent a label, infer identity from content equality, pick a preferred option,
request new acquisition, or force the user to decide as a runtime gate.

## Presentation scope

The no-host-ID guarantee here covers the proposed protein/overlap scientific
display and these families' carried result operands. It does not claim that
every unrelated existing prompt has already been repaired. Scope and other
existing exact contracts are unchanged. The worked model assignment fragment
omits common scope/goal/purpose/form fields solely to focus on the operand
substitution; its complete exact original assignment and form are retained in
the internal half of `RETAINED_SELECTION_EXAMPLES_001.json`.

The JSON examples are transport/data examples. They are not model-facing
context blocks or approval of complete TASK/STEERING wording. All concrete
scientific table and task text still awaits the user's running feedback.
