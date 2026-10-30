# Original group inputs with no fetched sequence members

Accepted additive clarification, 2026-10-25, following worker142's trace of the
pure function operands. This supplements012 without changing signatures.

An original auto_groups or feature-group InputBinding may contain no MemberFact
and no inline FASTA. It can therefore be absent from AssociationSet.original_members
even though its original request binding is known and valid.

The adapter authenticates AutoGroupEntry.input_binding_id and
FeatureGroupSource.input_binding_id against the exact original request bindings.
The pure MetaCATS extractor, which has no complete original binding inventory,
validates their nonempty syntax and internal entry/pointer/category relationships.
It must not require a sequence member as proof that the original binding exists.
Every supplied nonempty member_key still resolves exactly to common original_members;
those keys may belong to a separate input binding for actually fetched sequences.

A known original request with zero fetched sequences retains its requested group
provenance and unresolved sequence associations. It does not fabricate a member,
sequence, complete aligned population or successful retrieval. No equality of
labels/evidence substitutes for these explicit relationships.
