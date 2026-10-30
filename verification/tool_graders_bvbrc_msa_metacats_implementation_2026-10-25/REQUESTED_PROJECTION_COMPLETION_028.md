# Requested numerical completion and unrelated retained requirements

Additive root decision, 2026-10-25, for the new MSA/MetaCATS version1 adapters.

The original bundle builder records missing output-byte requirements only for
`OutputRequirement.required=true`. Its status must still be ok before the
original practical result assignment can be considered satisfied.

The new scientific adapters separately define status ok as satisfaction of the
parent's exact requested projection. They preserve other missing scientific
inputs and qualifications internally. For example, an alignment can supply an
exact member count while an original-member map or deployed software version
remains unknown. Those unrelated missing facts do not negate the measured count.

The host's earlier `_requested_status` treats every retained adapter requirement
as an unfinished endpoint. For the new `(bvbrc_msa,1)` and `(bvbrc_metacats,1)`
contracts, completion therefore uses both the original bundle's required-output
status and the adapter's requested-projection status. It still retains the full
missing-requirement list. Partial/invalid/failed projections and missing required
artifacts remain incomplete. No requirement is erased or converted into a value.

The existing behavior is preserved for older adapters because saved publication
reads recompute this status; silently changing their interpretation would alter
historical completion proofs. The new explicit adapter contracts have no such
earlier production interpretation to replace. No controller formula, extra turn,
monitoring rule or scientific acceptance gate changes. Existing practical
completion handles the validated original endpoint as before.

Root owns the narrow publication change and its tests. Agent148 verifies the
actual new episode endpoint and preservation of requested native values.
