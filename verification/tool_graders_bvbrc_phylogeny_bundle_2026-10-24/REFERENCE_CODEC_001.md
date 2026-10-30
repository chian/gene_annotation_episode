# Finite reference codec

`encode_reference(kind: str, analysis_id: str, identifier: str) -> str`
`decode_reference(reference: str, *, expected_kind: str | None = None) -> tuple[str, str, str]`

Encoding is `bvbrc_phylogeny_<kind>:<E(analysis_id)>/<E(identifier)>`, where E is UTF-8 percent encoding retaining RFC3986 unreserved characters only, uppercase hex escapes. Decode requires exact re-encoding equality. Namespaces are tree, split, alignment, family, feature, genome, population, function, comparison, requirement, role, reason. The outer returned fact row source_ref supplies actual admitted publication scope; this codec confers no custody. Every identifier resolves in that analysis of that publication. Internal indices remain separate typed integer fields.

Scalar catalog in SCALAR_CATALOG_001.json names every supported metric, exact selector keys, actual component collection, optional subcollection and exact Quantity field. Whole-tree scalars and branch/distance selectors include the original TreeSlotRef and population_id; original tree-request branch units are enforced. No new arithmetic is introduced.

Array selectors and exact keys:

- `branch_rows`: `metric, analysis_id, population_id, tree, node_indices`; kind `branches`.
- `site_rows`: `metric, analysis_id, population_id, columns_0based`; kind `sites`.
- `family_membership_rows`: `metric, analysis_id, family_ids`; kind `family_membership`.
- `function_composition_rows`: `metric, analysis_id, population_id`; kind `function_composition`.
- `relationship_comparison`: `metric, analysis_id, comparison_id`; kind `relationship_comparisons`.
- `missing_requirements`: `metric`; kind `requirements`.
- `qualifications`: `metric, analysis_id, slot_id`; kind `qualifications`.
