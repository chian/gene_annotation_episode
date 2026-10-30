# Pure parent-return data boundary

Root-owned implementation within C4,2026-10-27. This is an internal typed-data
boundary, not a model prompt, scientific calculator or receipt authority.

`chromatin_interaction_return_views.py` defines exactly these existing439 source
names: chromatin_interaction_projection, chromatin_interaction_saved_sheets and
chromatin_interaction_failures. Their values are arrays of RequestedProjection,
SavedSheetBundle and Failure respectively. RequestedProjection already limits
the scientific fields and carries their needed qualifications. This boundary
neither recalculates those fields nor selects a different scientific subset.

Pure exported ports mirror the existing typed-return mechanism:

- `chromatin_fact_sources() -> dict`: closed array source schemas and meanings.
- `requested_chromatin_sources(schema: dict) -> tuple[str, ...]`: source names
  requested by the parent's top-level form properties, retaining first order.
- `validate_chromatin_fact_values(source: str, value: object) -> list`: ordinary
  named-record validation and precise saved identity/format relationships.
- `select_chromatin_return_facts(groups: dict, *, schema: dict) -> dict`: only
  explicitly requested validated source arrays. Missing requested data rejects;
  no fabricated empty array, arbitrary first/latest row or private-output grant.

Schemas derive from C1's named standalone records, retaining only reachable
local definitions. Nested source schemas get distinct local ids for the existing
form validator. Saved bundles require sheet format chromatin_interaction_sheet_v1
and table formats chromatin_contact_tables_v1:{bins,contacts,weights,cell_states,
dense_values}. Artifact identity strings must match their declared SHA values.
Repeated table bytes can serve different declared populations/roles; preserving
an ordered bundle is not deduplication or independent scientific evidence.

These checks establish data shape only. Root's later results/received-return
integration must establish actual original request, captured bytes, selected
projection, exact complete sheet/table bundle and admitted parent delivery.
Possessing a matching digest grants no authority. This module reads no Store,
native output, network, file or model; it changes no credit or completion.

Verify every projection variant, selected-source isolation, saved identity and
format checks, embedded form schema resolution and mutation independence. Use
small symbolic records only for these shape checks and label them accordingly.
They are not native results or proof of a full episode path.
