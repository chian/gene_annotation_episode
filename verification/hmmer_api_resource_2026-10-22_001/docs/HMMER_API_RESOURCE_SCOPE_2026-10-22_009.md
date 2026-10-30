# Original job scope and one actual sequence reader

Complete connected review found a missing shared contract. B accepts ordinary
HMMER sequence operands, including features and reusable external references.
C inherited native rooted-query assumptions and cannot reconstruct the assigned
scientific scope of a rootless reference. A B-accepted job must not be returned
as a usable handoff while C rejects its monitoring receiver. The correction is
to preserve the assigning parent's actual job scope, not guess another target,
reclassify evidence as a target, or silently narrow accepted scientific work.

## P: immutable scope custody and pure sequence-reading port

Extend the new provider order call with required keyword `scope: dict`.
It is the normalized original scope supplied by B's `prepare_assignment`.
It does not enter the existing normalized provider request, provider_job ID or
public_search_order_v1 object; their existing byte/identity meanings stay fixed.
In the same order transaction, P saves one immutable scope sidecar with exactly:

```text
version="public_search_order_scope_v1", registry_ref, job_ref,
scope, scope_sha256
```

`scope` is Store.validate_scope of the actual caller value. `scope_sha256` is
SHA256 of its canonical JSON UTF-8 bytes. It is original assignment custody,
not another mutable job status or another semantic execution handle. Reusing
an order with different scope fails identity_conflict. Existing jobs lacking
this new proof fail unavailable_binding; no historical scope is fabricated.
These API jobs are new isolated engineering work, not existing live jobs.

The new public read port is:

```python
ProviderJobOperations.open_scope(job_ref: str) -> dict
```

It returns a detached exact sidecar after validating registry/order identity,
scope digest and Store scope shape. It performs no HTTP or repair. The existing
inspect object remains unchanged; C/B need not inspect private scope tables.

P also adds this pure method to its existing frozen three-attribute ports object:

```python
PublicSearchPorts.sequence_symbols(subject_ref: str, *, scope: dict) -> str
```

It delegates to the actual bound ToolRegistry's existing
`_check_sequence_operand(subject_ref, scope)` and
`_sequence(subject_ref, molecule_model="protein")`. Those existing operations
read actual stored sequence/feature/read-subject bytes, validate rooted geometry
when it exists and permit scoped use of registered rootless evidence. They do
not import, translate, infer biological molecule identity, execute HTTP/native
work, assign annotation credit or create another target. This is an explicitly
described primitive material-read port, not an investigation hidden in a tool.
The actual registry is already owned by result_publisher.tools. No attribute or
serialized identity is added to PublicSearchPorts.

## B: selected scope is part of original-order qualification

B uses ports.sequence_symbols for new requests and original-order byte
validation, replacing its duplicate sequence-reading implementation. New order
creation passes the actual assigned scope to P. Repair loads open_scope and
requires the same original job scope. Assigned launch/results contexts require
their original scope to match the order sidecar; a parent checking/receiving an
existing proof may contain that original scope, without rewriting it.
Handoff/proof qualification checks original scope custody in addition to the
existing request/registry/input/receiver facts. No HTTP or scientific decision
is added to closure validation.

## C: actual assigned scope, independent of query roots

C's _registered reads open_scope and sequence_symbols. It rebuilds the existing
normalized request from exact FASTA, compares the parsed single submitted
sequence with the actual material read through the same protein-processing
model, and returns the original saved job scope. It does not require direct
sequence_ref, target roots, intrinsic target coverage or biological aa assignment
when those are absent from an otherwise valid ordinary HMMER operand. Scope
containment and exact commission/order identity still constrain receipt and
dependency exposure. External references remain evidence about the fixed target.

P/C update their new fixture order calls to pass explicit original scopes. B/C
verify a rooted sequence feature without sequence_ref and a source-grounded
external reference with no original-target roots through real prepare, checked
handoff, progress scope, observation and result-publication consumers. A changed
scope sidecar/assignment must fail identity validation without another HTTP.
No guessed fixed-gene geometry or synthesized ownership is allowed.

## Submission uncertainty detail

An actual client failure may capture no declared submission_outcome. Preserve
that raw captured fact. When projecting a failed selected submit receipt, absent
client outcome means unknown, rather than null or not_sent. The existing
submission_uncertain failure and no-blind-retry behavior remain unchanged.
P verifies this projected receipt alongside raw capture preservation.

All three exclusive file owners remain the same; root integrates the unchanged
outer setup/adapter/progress ports. Earlier source/test inputs and logs remain
preserved with their narrower original claims. This correction is isolated and
does not mutate the live source, target, scientific conclusions or history.
