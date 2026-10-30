# Exact retained RNA comparison projections

Workload C implements the accepted 362 PLAN_001 and addenda 001–005 only in
`rna_structure_comparison_views.py`. This source is a pure projector and exact
fact-schema provider, not an episode, host authenticator, scientific calculator,
prompt renderer or tool-completion record.

The public ports are exactly:

```python
project_rna_comparison(sheet: dict, components: dict, *,
    projections: list[dict], result_receipt_key: str,
    calculation_key: str) -> list[dict]

validate_rna_comparison_projection(value: dict, *, sheet: dict,
    components: dict, selection: dict, result_receipt_key: str,
    calculation_key: str) -> dict

rna_comparison_fact_sources() -> dict
```

`RNA_COMPARISON_PROJECTION_RESULT_SCHEMA` is the complete closed eight-family
union. `PROJECTION_QUALIFICATION_SCHEMA`, `STRUCTURE_VALUE_SCHEMA` and
`SELECTED_MEMBER_VALUE_SCHEMA` are its exact subshapes. `PROJECTION_SOURCE` is
`execution_rna_structure_comparison_projections`; the source dictionary has the
existing `type`, `meaning`, `report_schema` convention. The report schema's
`items` is the exact result union and its `x-source` is that source name.

A owns request schemas, finite metric/reason/formula/transition enumerations,
and representation validation of supplied sheets/components. C imports those
definitions and never imports either numerical calculator. It validates the
explicit projections by the original selector relationships, then selects
retained cells, rows and original strings. Full input sheets/components remain
unchanged. Outputs and exported source dictionaries are detached copies.

Both supplied keys are required and exactly follow addendum004. C checks their
format and equality to expected supplied context, never derives/authenticates
Store authority. D/E must derive and authenticate identities against the actual
original collect action, inputs, scientific question, parameters and calculator
version, and must compare complete components against deterministic recalculation.

All requested array order is preserved except `scan_members`' declared-order
selection. Counts group pair metrics/state first at selection_id=null, followed
by requested site selections. Original structure fields are selected separately;
invalid original text is preserved with invalid state while pairs remain null.
Position rows retain complete partner/coordinate relationships from supplied
components, using the selection's actual coordinate member and resolved indices.

Scan predicates use exact stored `order`, `baseline_tolerance_band` and member
`energy_state` classifications with explicit OR; there is no energy recomparison,
epsilon or implicit threshold. Exception selection excludes baseline and aliases;
explicit member selection can name either. An explicit limit retains matched,
returned and omitted counts and the selected-window qualification. Aliases never
gain extra population weight. Requested numerical member fields must be actual
nonnull retained cells, including unavailable cells; C never constructs one.

Addendum005 records the gaps reported before implementation: nullable unavailable
site-population counts, common-identity-only top-level population_id, bounded scan
member/issue qualifications and exact delivery distinctions. Scan energy/sites
qualify only the baseline by member ID; scan members qualify baseline and returned
IDs. Aggregate reasons/counts retain excluded-member context without returning
every member or structure. Full detailed issues remain internal.

Validation reconstructs the exact projection and uses type-sensitive equality.
Shape validity alone is not numerical proof. C can reject forged projected
metrics, rows, original strings, coordinates, partners and keys relative to the
supplied validated components; it cannot authenticate original receipt authority
or establish arithmetic independently of D's later recomputation.

The existing communication compiler presently recognizes only the original RNA
source dictionary. Registering this exact new dictionary is root's assigned
shared integration work. C does not edit communication, old views, worker/host,
prompt, controller, credit, inventory or historical authority files.
