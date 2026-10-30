# Preserve old runtime receipts when the new binding table does not exist

Additive compatibility finding while004's fixed-source checks were running.
No additional shared file ownership is needed. The current older-runtime test
removes one binding row; that is weaker than a real pre044 Store, which lacks
the new nonoptical per-view delivery table altogether.

An eager CREATE in the base constructor would write new schema before the
read-only original-runtime-proof path could be used. SQLite mode=ro would fail
before forwarding despite the authoritative successful original form/contract
being present. This is an implementation gap in reconstruction, not missing
scientific information or permission to rewrite older history.

Defer creation of the new per-view binding table until an actual new receive
needs to record its binding. A binding lookup returns absent if that table does
not exist. Existing old runtime rows continue to authenticate against their
original form/contract and public selection where needed; their lookup and
explicit repeated receive create neither table nor binding. Old trusted manual
rows without binding still return the explicit unavailable-binding limitation.
Optical004's own existing table creation/layout/digest remain unchanged.

The existing two-boundary C4 fixture should DROP the whole new binding table
after its forged-row check, then verify original subset forwarding and repeated
receive with whole SQL unchanged. Reopen the actual database in SQLite mode=ro,
disable original scientific bytes/parser/calculator, and reconstruct/forward both
receivers. C4's transactional replay can run within an existing read_snapshot
and nested savepoint; this does not weaken actual read-only enforcement.

Atomic interruption tests should accept the stronger rollback outcome where
the newly created delivery table itself is absent, as well as zero receipt rows.
An actual successful new receive must still create exactly the needed per-view
binding transactionally. This correction adds no action, observation, policy,
source reacquisition, scoring meaning, model call or scientific interpretation.
