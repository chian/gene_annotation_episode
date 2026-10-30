# Exact populating contracts — all UNIMPLEMENTED

These are targeted specifications for the cells in
ORGANISM_CONTEXT_NUMERICAL_SHEET_001.md. No reader function, model prompt,
registry entry or production scorer has been implemented.

## Records to populate

`OrganismContextQuestion`:

* `target_material_ref`; input kind `sequence | selected_file_record |
  bounded_snippets`; actual material boundaries.
* `organism_ref` and `strain_ref`, nullable; source of the assignment; allowed
  alternative assignments when unresolved. Do not generate a public name.
* `candidate_ref`, nullable during extraction, populated when a function emerges.
* `role_meaning_ref`, `scope_ref`, `scope_version`.
* `question_kind`: `organism_capability | sample_context_coverage`.
* `population_definition`: exact organism(s), life stages, compartment, host and
  time interval. `scope_is_exhaustive`: boolean with supporting record or false.
* `required_context_predicate_refs`; `alternative_route_refs`; any relevant
  external exposure requirement refs. Empty is different from missing.

`OrganismTraitObservation`:

* `original_observation_id`, `organism_context_id`, `state_id`, `sample_unit_id`,
  `collection_id`, `independent_cluster_id`; technical-repeat identifiers.
* `trait_code` and an explicit biological definition: e.g. neck width or the
  existence of a cytoplasmic access route to the stated site.
* `value_kind`: `number | numerical_interval | observed_state_set | censored |
  missing`; native `value/lower/upper`, units and interval inclusivity.
* `observed_state_codes`: a closed list defined by the concrete trait schema,
  not an unrestricted prose finding. Missing uses an explicit status.
* uncertainty type, detection method/limit, field of view or sampling coverage,
  correction history and source location.
* `origin`: `measured | source_reported | graph_derived | calculated | synthetic`.
* `original_axis_owner` and `shared_dependency_ids`.

`ContextualRelation`:

* `predicate_id`, `role_meaning_ref`, trait refs and their required units.
* `relationship_kind`: `necessary | alternative_route | domain_definition`.
* Supported and incompatible value regions or explicit observed state sets.
* Joint background/support refs; alternative routes; exceptions/counterexamples.
* `relation_basis`: `native_measurement | physical_definition |
  narrow_literature_interpretation`.
* For a narrow interpretation: exact proposition, biological subject,
  population, compartment/life stage, source-fact refs, permitted alternatives,
  and one of `supported_relation | incompatible_relation | unresolved_relation`.
  It returns no numeric intuitive confidence. Numeric native evidence cannot
  be discarded to invoke this branch.
* For clade-to-target use: trait-scope record, verified target scope membership,
  known exceptions, actual mapping/model operands if any. Missing mapping yields
  unresolved target trait values. No tree score is fabricated.

`OrganismContextComponents`:

* Native margins with exact operands, units and intervals.
* Requirement memberships `ell/u`, per-state joint `L/U`, conflict references.
* `permitted_unexamined_remainder`: boolean and reason; false needs exhaustive
  scope support. An unsampled life stage is not silently excluded.
* `global_necessary_exclusion_ref`, nullable; its scope must contain the whole
  capability question before it can establish O=0.
* `capability_lower/upper`, nullable `capability_point`.
* Coverage cells: sum of weights, supported/unresolved/incompatible weight;
  condition numerators/denominators; `coverage_lower/upper/point`.
* `selected_question_kind`, `selected_lower/upper/point`, display values,
  `sampling_interval` with method/actual denominator or null.
* `dependency_ids`, `missing_operand_codes`, `formula_ref`, `source_basis`.

## Targeted functions, each UNIMPLEMENTED

| Proposed function | Exact inputs | Exact populated output |
|---|---|---|
| `a108_read_organism_trait_literature` | One primary artifact; specified trait; organism/strain; selected passage, figure or table; role-scope context | OrganismTraitObservation values, native units, scope, source/measurement identity and uncertainty. “Not mentioned” is missing, not absent. |
| `a108_read_organism_trait_dataset` | Selected rows/images; observation-to-cell/organism mapping; calibrated measurement columns; sample and repeat design | The same observation fields. It cannot treat repeated images or aliases as new cells/organisms. |
| `a108_read_contextual_relation` | Emerged role meaning; source facts; a specific trait relation and allowed alternative routes | ContextualRelation with explicit domains and joint support. It does not infer necessary conditions from what is merely common in a clade. |
| `a108_interpret_narrow_organism_relation` | Only the explicit proposition, subject, population, scope and actual evidence/alternatives | A scoped state relation and evidence refs, or unresolved. Never an overall relevance percentage. This is the limited pseudo-grader responsibility. |
| `a108_map_clade_trait_to_target` | Trait generalization's exact lineage/phenotypic scope; target's supplied or established identity/context; documented exceptions and any actual transfer model | Target B sets and mapping status. Direct observations, counterexamples and unresolved identity remain visible. |
| `a108_calculate_trait_membership` | Native B sets; sourced D+/D−; uncertainty; exact units; joint support | Native margins, ell/u and per-state joint bounds using the sheet's formulas. Deterministic after the inputs are populated. |
| `a108_calculate_organism_capability` | Unique per-state bounds; alternative routes; unexamined remainder; optional whole-scope exclusion proof | O−/O+, point or null. ORs situations, never papers. Does not infer absence from no witnesses. |
| `a108_join_context_coverage` | Existing draft-014 ContextUnits; organism-state mapping to the same units; actual weights and denominator | Existing paired fraction with organism predicates included, plus condition numerators/denominators. Unpaired inputs return bounds. |
| `a108_populate_selected_context_result` | Original question_kind/scope; filled O and/or C; dependencies | One selected proposed A108 contribution and both clearly labeled diagnostics when available. It does not choose the higher result or wire W05. |

Readers may parse measurements deterministically or perform the explicitly
bounded interpretation when no applicable quantity exists. The arithmetic is
deterministic in either path. Literature and datasets populate the same cells.

## Defined missing outcomes

Use distinct codes for missing organism assignment, absent phenotype measurement,
missing detection limit, unsupported clade transfer, invalid necessary relation,
unresolved alternatives, unsupported joint domain, conflicting same-state data,
missing pairing, unexamined permitted states, and absent sampling design.
Retain usable numeric components with these outcomes. They are not runtime
stopping rules, mandatory experiment requests or approval requirements.

Component validation requires 0≤lower≤upper≤1; selected question and original
scope consistency; positive coverage denominator; one contribution per original
unit; no source-assay credit duplication; correct units; explicit origin tags;
and no synthetic observation promoted to a reported measurement. None of these
contracts is implemented by the local arithmetic fixture.
