# A110 scientific meaning repair proposal125

Engineering proposal for the fixed literature task; no goal or governing amendment.
No primary paper or paper-specific packet was read. Production is unchanged.

## Existing defect

`literature_reaction_inputs` retains alternatives as `{key,prediction}`. The pure
calculator retains per-model residuals, errors and contrasts with those private
keys. `_metadata` exposes only `alternative_predictions:[number,...]`; the
parent cannot identify the reaction/hypothesis behind a comparison. Resource
keys, consumption coefficients and limiting-key relationships likewise have no
public source-supported substance/process meanings. The calculator's15 existing
components and conditional model remain useful and need no formula change.

## Versions and ownership

- Existing operation `literature.reaction.populate` and its argument schema stay
  exact. Existing retained data v1, extraction v1, saved record v2 and
  `literature_reaction_cells` stay exact.
- Add retained `a110_source_reaction_measurements_v2`, extraction
  `a110_reaction_inputs_v2`, saved `literature_reaction_record_v3`, and
  `literature_reaction_semantic_cells`, a second closed return view of the same
  numerical sheet. No new operation, assay, axis or score.
- Owner125: reaction inputs/storage/prompt; NEW reaction_meanings and
  reaction_meanings_render; NEW tests and this artifact directory.
- Shared changes proposed only in LiteratureEpisodes fingerprint, fact-source
  schema, route, version/empty-family checks; and reaction-definition rendering
  in the existing scientific prompt. Other owners' hunks remain untouched.

## Retained v2 shape

Top-level closed fields are `version,ratio,budget,meanings`. Ratio/budget retain
all existing numerical shapes. `meanings` has exactly `ratio,budget`; each is
null exactly when its numerical section is absent.

`meanings.ratio` has `claim,alternatives`. Claim has:

- `definition`: nullable source witness for the model or hypothesis name/definition.
- `reaction`: nullable witness for its specific reaction/chemical relationship.
- `function_relation`: nullable witness for its relationship to the investigated function.
- `prediction_evidence`: nullable witness supporting the specified prediction.
- `prediction_basis`: source_reported, source_supported_inference,
  conditional_assumption or unresolved.

Each alternative adds its private `key` to the same fields. Alternatives match
exactly the actual numeric alternative roster by key, independently of list order.
Claim meaning remains present even if its numerical prediction is unavailable.

`meanings.budget` has `resources,demand`. Each resource adds its private
`resource_key` to these fields:

- nullable witnesses: definition, entity, property, biological_setting,
  supply_evidence, coefficient_evidence;
- supply_basis and coefficient_basis, using the same four-value basis enum.

The demand has nullable definition, process, biological_setting and evidence
witnesses plus demand_basis using that enum. Resource meanings match the actual
raw resource roster before private source/artifact namespacing.

Missing witnesses remain null and add no scoring gate. All numerical cells
retain their existing conditional meaning regardless of missing definitions.
Source-supported interpretation is allowed; no requirement that the paper use
our terminology verbatim. Literal witnesses establish exact source custody,
not biological truth or numerical calibration. A conditional assumption need
not have a fabricated source witness. Source_reported versus inference versus
conditional basis travels with the actual prediction/coefficient/demand.

## Public scientific view

The semantic view preserves every old numerical component and qualification.
It adds closed arrays/objects with durable reference/term/context links:

- model_definitions: model_ref, role, definition_reported, reaction_ref,
  function_relation_ref, prediction_evidence_ref, prediction_basis, prediction,
  unit. Claim first, then the original alternatives in their actual roster order.
- comparison_member_refs: the exact alternative model_refs participating in the
  existing minimum-over-declared-alternatives convention. A missing alternative
  stays missing. A separate minimum-member field, if implemented, must use exact
  comparison arithmetic; rounded equal values must not fabricate ties.
- resource_definitions: resource_ref, definition_reported, entity_ref,
  property_ref, biological_setting_ref, supply_evidence_ref,
  coefficient_evidence_ref, supply_basis, coefficient_basis, coefficient and the
  explicit fixed-consumption role `resource_unit_per_demand_unit`. This need not
  disclose private unrequested supply values or resource domains.
- demand_definition: demand_ref, definition_reported, process_ref,
  biological_setting_ref, evidence_ref, demand_basis, value, unit.
- nominal_limiting_resource_refs: existing exact calculator budget-detail keys
  mapped to actual resource references; unknown capacity gives no fabricated
  physical limiter. Logical bounds remain qualified model bounds.

Definitions become anchored durable records with scientific quote labels.
Unknown definitions use distinct scoped generic handles with null anchors; they
assert neither chemical identity nor source support. Raw keys, generated
accessions and host IDs never substitute for scientific names.

No new per-alternative numerical outputs are necessary: existing comparison
membership and named predictions repair this defect. Adding all residual/error
cells to every selected return would expand numeric disclosure beyond the
original component selection and is excluded from this minimal proposal.

## Persistence, custody and rendering

New v3 payloads retain source-anchored meanings and their published binding map.
The operation outcome includes those record references, allowing ordinary exact
selected delivery and the existing scoped record-display closure. Semantic
projection has a separately lazily installed receipt table; construction and
read-only reconstruction do not execute DDL. Old v1/v2 records cannot silently
upgrade to the semantic view; semantic records cannot silently downgrade to the
old view. Empty wrong-view returns receive the existing style of version error.

Saved reads use original payload/outcome/records only, with no source reacquisition
or calculator pass. New payload hash and exact outcome metadata must agree;
reference values cannot be swapped to relabel a prediction or coefficient.

Render one scientific model panel and resource panel per selected sheet in own
next-decision and received parent steering. Display names from actual received
records only, including records beyond the standard24-row working page. Missing
possession is `meaning unavailable in the received scientific records`, not a
Store lookup. Display bases and unknowns alongside the same selected cells.

Proposed TASK addition: For the actual claim and each genuine alternative,
preserve the source-supported reaction or functional meaning, prediction scale,
and whether the prediction is reported, inferred, conditional or unresolved.
Keep each resource's substance/property, biological setting and coefficient
meaning linked to that same resource, and identify what the demand measures.
Missing descriptions do not erase conditional quantitative results. Names or
stoichiometric expectations alone do not establish measured product identity,
consumption, coupling or physiological availability.

## Acceptance evidence

Constructed case only: two distinct named alternatives have equal predictions;
matching units/numbers must not collapse their scientific identities. A different
prediction remains linked to its own model. Two same-unit resources retain their
actual substances/coefficient/demand roles. Unknown meaning and absent
alternatives preserve old numbers/missing behavior. Invalid/reordered/duplicate
rosters, source mismatch and unavailable page ancestry are checked before source
bytes. Parent receives only its selected existing components in the original
closed form, with exact scientific metadata and no additional observation.

Actual ordinary child/parent iteration, exact subset forwarding, receipt forgery
and first read-only reconstruction must be demonstrated. Fresh read-only reopen
forbids source/reader/calculator/model calls and writes. Preserve portable legacy
v2 outcome/form fixtures exactly. Run old reaction input/storage/calculator and
constructed integration regressions; distinguish primary-source fixture tests
from new primary validation. This work alone does not implement native report
numeric extraction or establish the entire fixed literature goal complete.
