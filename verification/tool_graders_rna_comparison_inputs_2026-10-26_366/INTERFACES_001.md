# RNA comparison input interfaces

This additive workload-A handoff implements only the accepted 362 PLAN_001 and
CONTRACT_ADDENDUM_001 input boundaries. The original authority, user direction,
existing sheets and fixed tool rows remain unchanged. No integration or
numerical-calculator completion follows from this handoff.

The contracts module exports these pure ports:

```python
validate_rna_comparison_selector(value: dict) -> dict
validate_rna_comparison_parameters(value: dict) -> dict
validate_rna_comparison_sheet(value: dict) -> dict
validate_rna_comparison_components(value: dict, *, sheet: dict) -> dict
validate_rna_comparison_projection_request(value: dict) -> dict
validate_rna_comparison_issue(value: dict, *, sheet: dict | None = None) -> dict
```

The inputs module exports:

```python
populate_rna_comparison_sheet(selector: dict, *, operands: dict[str, dict]) -> dict
build_rna_correspondence(baseline: dict | None, variant: dict | None,
    *, request: dict) -> dict
```

The last port takes original 354 sheets (or None for unavailable members), not
RetainedOperand wrappers. Its exact return, approved by root on 2026-10-26, is:

```text
{request, state, columns, matches, baseline_to_variant, variant_to_baseline,
 baseline_length_nt, variant_length_nt, issues}
```

State is valid, invalid or missing_input. Columns and matches are always arrays;
the unused representation is empty. Lengths are nonnegative integers or null
when no original coordinate extent is available. Maps contain every known local
coordinate in order, using exactly `{index,state,counterpart_index,column}`.
Partial maps use unknown for unlisted coordinates; complete maps use gap only
for an explicitly supplied alignment gap. No topology changes are computed.

ResolvedOperandData remains exactly `{original_sheet,original_bundle_software,
received_failure}`. The operands dictionary has all and only non-alias selected
members, including declared absent members with all three fields null. A saved
sheet must be present; an absent retained artifact is a host failure, not a new
native missing-energy record. Aliases contain no second source operand.

ClosedInputPath is an RFC 6901 pointer into the actual ComparisonSheet, such as
`/operands/0/original_sheet/topology/pairs/0` or
`/comparisons/0/resolved_selections/0/indices`. It must resolve against the actual
closed instance. Null leaves can be addressed, but no child below null exists.
Indices are canonical decimal array positions; names/accessions never provide
implicit membership. Issue references are scoped to selected members,
comparisons and selections. Standalone map issues have null contextual IDs;
the sheet constructor supplies their comparison ID.

Root approved this invalid-selection representation: scientifically invalid
positions/intervals/region keys retain the exact selection with indices=[] and
a required invalid_site_selection issue naming that selection_id and comparison.
The invalid selector is rejected as usable, without discarding valid source
data. Its site components must be invalid/unavailable, never present zero.
A deliberately empty valid union remains distinct and may have a present zero
count with an unavailable zero-denominator fraction. Wrong types and unknown
fields raise ValueError. Sheet validation rejects missing qualifications or
forged resolved indices.

Public schema exports are RNA_COMPARISON_SELECTOR_SCHEMA,
RNA_COMPARISON_PARAMETERS_SCHEMA, RNA_COMPARISON_SHEET_SCHEMA,
RNA_COMPARISON_COMPONENTS_SCHEMA and RNA_COMPARISON_PROJECTION_REQUEST_SCHEMA.
Shared component shape exports are NUMERIC_CELL_SCHEMA, COMPARISON_ISSUE_SCHEMA,
SITE_CHANGE_SCHEMA, PAIR_CHANGE_SCHEMA, ENERGY_COMPARISON_SCHEMA and
POPULATED_SCAN_SCHEMA. No output projection or registered fact schema is owned
here; workload C imports the request definitions.

The complete finite CompatibilityField names are:

```text
energy_kind unit baseline.structure_association variant.structure_association
model.engine model.engine_version hard_constraints soft_constraints
parameter_artifact.sha256 parameter_artifact.size_bytes
parameter_load_return parameter_save_return other_observed_settings.name_set
effective_settings.temperature_c effective_settings.dangles effective_settings.noLP
effective_settings.noGU effective_settings.noGUclosure effective_settings.special_hp
effective_settings.logML effective_settings.min_loop_size effective_settings.max_bp_span
effective_settings.circ effective_settings.gquad
other_observed_settings.backbone_length other_observed_settings.backtrack
other_observed_settings.backtrack_type other_observed_settings.betaScale
other_observed_settings.circ_alpha0 other_observed_settings.circ_penalty
other_observed_settings.compute_bpp other_observed_settings.cv_fact
other_observed_settings.energy_set other_observed_settings.helical_rise
other_observed_settings.nc_fact other_observed_settings.nonstandards
other_observed_settings.oldAliEn other_observed_settings.pf_smooth
other_observed_settings.ribo other_observed_settings.salt
other_observed_settings.saltDPXInit other_observed_settings.saltDPXInitFact
other_observed_settings.saltMLLower other_observed_settings.saltMLUpper
other_observed_settings.sfact other_observed_settings.uniq_ML
other_observed_settings.window_size other_observed_settings.alias
other_observed_settings.pair other_observed_settings.rtype
software.worker_source_sha256 software.rna_module_sha256
software.rna_extension_sha256 software.viennarna_distribution_version
```

The two structure_association fields are checks of each energy against its own
original structure and model. All other named comparisons retain section 8's
exact meanings and the pinned generation proof from addendum001.

Finite constants are COMPARISON_REASONS, COMPARISON_METRICS, COMPARISON_UNITS,
COMPARISON_FORMULAS, PAIR_METRICS, SITE_METRICS, ENERGY_METRICS,
SCAN_ENERGY_METRICS, SCAN_MEMBER_RANK_METRICS, SCAN_SITE_METRICS, SITE_TRANSITIONS, PAIR_RELATIONS,
PAIRING_STATES, ENERGY_STATES, RANK_CLASSES, PREDICATES, COMPATIBILITY_FIELDS,
CELL_STATES and CELL_ORIGINS. METRIC_SPECS maps formula ID to its fixed metric,
allowed units and origins for representation validation only. It is a constant
lookup, not a formula interpreter. All arithmetic remains workload B's ordinary
Python functions. The schema and calculator tags remain exactly those in 362.

Root approved the section 9/10 aggregate-versus-member clarification:
SCAN_ENERGY_METRICS contains only aggregate energy_components metric names.
SCAN_MEMBER_RANK_METRICS is exactly (member_rank_start, member_rank_end); both
remain in COMPARISON_METRICS and COMPARISON_FORMULAS. A scan_energy request cannot
select those member metrics. Explicit scan_members fields rank_start/rank_end
select the corresponding per-member cells without changing the rank population.

Component validation checks shapes, finite/typed cells, requested selections,
original values and coordinate/member relationships; it never imports workload B
or reruns numerical calculators. Publication later compares the supplied result
against deterministic recalculation. Input validation may rederive maps and
selection unions to reject forged saved input representations.

All constructors retain deep copies. They perform no Store/file/network/native
scientific calls, select no model/resources/representatives and add no observation,
credit or continuation behavior. Full retained sheets are internal data; only the
parent's nonempty explicit projections select return content.
