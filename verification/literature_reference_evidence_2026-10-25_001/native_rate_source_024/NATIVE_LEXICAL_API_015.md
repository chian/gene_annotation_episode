# Exact native lexical interface at final 024 release

Module: `gene_annotation_episode.literature_rate_native_inputs`.
Final SHA256: `264328313d32a8ed0315eb4a80388be775a8c7c2b51ad25041aad071a295dc67`.
These are private owned helpers, not a new scientific operation or universal quantity ontology.

`_field_contexts(sources, witness, start, end) -> (prefix: str, suffix: str)`

- `sources` is the existing `_Sources` custody object; its `source(source_ref, representation)` supplies the actual artifact bytes.
- `witness` must already have passed `sources.witness(...)`. Its `start/end` are absolute UTF8 byte offsets; `start/end` arguments here are Unicode character positions within `witness['quote']`. The helper itself does not verify selected bytes or bounds.
- It computes actual absolute numeric/unit byte positions, keeps source context inside structural HTML/JATS cells/blocks, strips inline markup and decodes entities. A `<br/>` line break is inline context, not another field. Scientific bytes, enriched witnesses, source identities and positions remain unchanged.
- It returns lexical neighbours, not interpreted scientific meaning, independence, units, calibration, or comparability. A new consumer must validate its witness and local token bounds and own its scientific roles. Do not rewrite bytes or monkeypatch shared `_contexts`.

`_number(selection, sources, role, *, count_unit_guard=True) -> parsed_number`

- `selection` is exactly `{witness, number_start, number_end}`; offsets select a complete literal source number, never a JSON numeric operand. It verifies original custody and span, then uses `_field_contexts` and native semantic/lexical guards.
- Roles are `rate`, `spread`, `condition`. `rate` admits finite signed dimensional points and typed lower/upper limits plus approximation. `spread` and `condition` require exact points; spreads must be nonnegative. `condition` is used for count selection here and rejects explicitly dimensioned physical quantities when `count_unit_guard=True`. Count integrality/positivity and sampling interpretation are enforced separately by the caller.
- The sole current `count_unit_guard=False` caller is the source-defined unit coefficient, which is a dimensioned coefficient rather than a count. It retains exact-point and expression guards. This flag neither supplies scientific numbers nor authorizes quantity conversion.
- Output is `{selector, raw_number, value, relation, approximate}`. `selector.witness` is enriched with actual `artifact_ref`; `raw_number` is the exact selected token; `value` is its finite native float; `relation` is `point/lt/le/gt/ge`; `approximate` is a boolean. It performs no unit scaling. Selected scientific roles and supported syntax remain the consumer's responsibility.
- Unsupported source expressions, contradictory quantity roles and lexical clipping raise `ExperimentalContractError` with specific repairable codes. This bounded parser does not claim exhaustive natural-language coverage. Reuse for a different scientific quantity must preserve its actual qualifiers and source context and must not relabel a count or source rate as another measurement.

`_defined_unit(selection, sources, endpoint) -> existing_defined_unit_record`

This is the thin rate-specific native adaptation, not an amount-reader API. It keeps the original selected definition's exact record shape, field-aware outside boundaries, exact guarded coefficient and unchanged pure `_definition_scale` entity/endpoint/containment/bridge semantics. Canonical output remains `pmol/min/mg`; the rate sheet separately divides the exact scale by one million. Supported prose records are exactly equal to the existing defined-unit reader's records. Do not reuse U as a universal amount alias or cancel two independently defined units merely because their printed labels match.

For amount extraction, `_field_contexts` is the narrow reusable lexical primitive. Quantity/unit parsing and any amount-specific role/derived-field contract belong to that consumer. The rate helper's parsed value is the unscaled source literal, not the existing rate sheet's canonical operand or an annotation score.
