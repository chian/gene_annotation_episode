# Separate saved structure validation from numerical verification

The real E replay trace reaches scientific arithmetic through D's calls to native component validators. It reaches interval unions, interval lengths, multiplicity, complements, fraction division, count aggregation and entropy. F reproduces this through pure, own-result and received-result paths. Calling these functions validators does not move those calculations out of the calculator responsibility. The prior D instruction to call existing native numerical validators was insufficiently precise about this boundary; this additive correction resolves it without replacing historical reports.

## New exact native interfaces

Each function accepts one saved component dictionary and returns a detached, structurally validated dictionary with identical values:

- `mauve_v4_calculation_contracts.validate_mauve_v4_component_structure(value: dict) -> dict`
- `mauve_backbone_contracts.validate_mauve_backbone_component_structure(value: dict) -> dict`
- `mauve_backbone_contracts.validate_mauve_bbcols_component_structure(value: dict) -> dict`
- `xmfa_calculation_contracts.validate_xmfa_alignment_component_structure(value: dict) -> dict`
- `xmfa_calculation_contracts.validate_xmfa_coverage_component_structure(value: dict) -> dict`

Preserve the existing `validate_*_components` signatures and full numerical checks for calculator/producer verification. They can share structural code with the new functions, but a saved-structure call must never enter the numerical verification branch. No ambient mutable flag, monkeypatch, disabled assertion, generic schema bypass, additional persistence or new scoring language.

Structural validation retains exact closed fields; finite numeric types; native/method/unit/population identities; state/null rules; allowed ranges; selected members/pairs/requests/order; original document and source relationships; coordinate conventions and bounds; interval shape/sorted-disjoint representation; required links; requirement/diagnostic references; and equalities between already-stored operand fields. It does not rederive scientific quantities from sequences, selected ranges or populations: no interval union/intersection/complement construction, interval-length totals, multiplicity or count aggregation, fraction recomputation, entropy/logarithms, sequence comparison or alignment calculation. Unknown, measured zero, missing, partial and incompatible values keep their exact saved meanings.

This does not make a caller-authored numeric dictionary authoritative. Existing original publication/content hashes, immutable source bindings, configured implementation identity, original selector and frozen typed-value equality establish authenticity on the host path. Pure structural validation proves shape and relationships, not that arbitrary caller-authored numbers were scientifically calculated correctly. Existing full validators and native numerical tests continue to verify that distinct responsibility.

## D consumer change and ownership

The correction workload exclusively owns the three native contract modules above, `gene_annotation_episode/bvbrc_genome_alignment_calculation_contracts.py`, new `tests/test_genome_alignment_saved_structure.py`, and `verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/`. Root owns all shared host/library/runtime wiring and accounting. Do not edit E/F files, their tests, existing source/pin receipts, existing native calculators or original design documents.

D's `COMPONENT_VALIDATORS` maps the five numerical component kinds to the new structure functions. Existing coordinate and inverse-coordinate validators may remain only after verifying their full saved call path has no scientific recalculation. D's source snapshots, plan/request/document checks and native correspondence checks remain. Inspect D's complete saved path for inline arithmetic and preserve only structural relationships as defined above. Report any necessary change outside owned files before editing it.

## Verification and handoff

Use the actual retained native examples and explicit synthetic original-task/source witnesses already supplied. Verify all seven D families, including partial, missing, zero, reverse, duplicate and overlapping cases. Strict replay barriers cover public parsers/calculators/source comparisons and internal scientific helpers, including `math.log2` and other reached numerical primitives; examine inline arithmetic as well. The barriers must pass through actual E saved projection and F pure/own/received paths, not only a new function in isolation. Preserve the original failed receipts.

Prove that full native validators still reject incorrect recomputed values, new structural validators still reject identity/shape/state/relationship corruption, and the authenticated saved path rejects changed values by original content/frozen-value checks. Recalculation remains an explicit operation and can invoke actual calculators with new parameters without acquisition; a saved projection does not. Retain command results and before/after source hashes; dependent facade pins must be recomputed prospectively after this change. Do not rewrite saved run pins or claim the full Workflow is verified.
