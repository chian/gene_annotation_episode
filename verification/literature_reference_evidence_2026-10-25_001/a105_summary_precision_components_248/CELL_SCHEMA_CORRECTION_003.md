# Additive sheet-cell correction003 — PLAN ONLY

Root250 demonstrated that002 allowed mean_variance to carry the parameter's
formula and count unit. This is a schema defect. No production component has
been released; frozen001/002 are preserved. TASK, scientific formulas, prior
count/SD ownership correction, independent SD scale correction and the other
three standalone002 schemas remain unchanged.

`SHEET_SCHEMA_003.json` replaces each named cell schema in BOTH source_cells
and the nonnull scenario_cells branch. Each formula_code is now a CONST equal
to `summary_precision_` plus that cell's own name. It cannot be copied from a
different named cell. `CELL_SCHEMA_DELTA_003.json` gives the exact RFC6902 patch
from SHEET_SCHEMA002, together with the compact per-cell domain table.

| Named cells | Allowed populated unit | Allowed populated numeric domain |
|---|---|---|
| reported_parameter | uM, per_min, uM^-1min^-1 | finite number |
| reported_sd, mean_standard_error | same three canonical units | finite number ≥0 |
| mean_interval_halfwidth | same three canonical units | finite number >0 (the optional t route requires positive SD) |
| mean_interval_lower, mean_interval_upper | same three canonical units | finite number; no clamp at zero |
| mean_variance | uM_squared, per_min_squared, uM_inverse_squared_min_inverse_squared | finite number ≥0 |
| source_summary_count, independent_preparation_count, statistical_estimator_count, mean_interval_df | count | integer ≥1 |
| relative_reported_sd, relative_mean_standard_error | dimensionless | finite number ≥0 |
| mean_interval_confidence_level | dimensionless | const0.95, the selected proposed level |
| mean_interval_t_multiplier | dimensionless | finite number >0 |

Populated cells require status=populated, a numeric value in the named domain,
a nonnull unit in that cell's domain, null unavailable_reason and a populated
qualification. Source cells permit only source_reported or
derived_source_supported_conditions. Scenario cells additionally permit
conditional_on_stipulated_assumptions, which requires at least one declared
stipulated assumption; other populated qualifications require an empty
stipulated_assumptions list. Source cells always require an empty stipulated
list. These are representation checks, not a new scientific acceptance rule.

Unavailable cells require status=unavailable, value=null,
qualification=unavailable, source_exact_value=null and a nonnull reason from
the existing closed ReasonCode set. Counts/df retain unit=count even when
unavailable. Relative quantities/level/t retain unit=dimensionless. Only the
dimensioned parameter, SD, variance, SE, halfwidth and endpoint cells may have
unit=null, and only while unavailable, when that source dimension/unit is not
known. Known units must still be retained by semantic validation. An unavailable
scenario cell may retain the declared attempted assumptions; it gains no value.

For populated cells source_exact_value remains Rational OR null: SE, t
quantiles and endpoints can be irrational or evaluated numerically. This
correction does not manufacture exact fractions from rounded floats. Actual
finite-number and exact-value agreement remain calculator/domain checks.

The schema supplies per-cell unit DOMAINS, not a default unit or a guarantee of
agreement with input dimension. The calculator must still select the actual
parameter canonical unit, the independent actual SD canonical unit and its
squared form; validate matching dimensions for relative quantities/endpoints;
preserve known partial units; validate value/formula/operands/conditions; and
reject tampering. Choosing per_min for a source catalytic-efficiency SE may be
inside the broad cell domain but still fails that semantic agreement check.

`CELL_CONFORMANCE_EXAMPLES_003.json` contains a complete illustrative actual242
sheet shape: ordinary statistical n/SE remain unavailable; explicit scenario
variance1.8e−11 and SE.000004242640687119285 retain their stipulated conditions.
Irrational SE/t/endpoint source_exact_value is null. This is a PROPOSED output
shape and arithmetic example, not execution of unimplemented production code.

The same file includes positive partials (unavailable parameter while a known
SD and mean SE survive), unavailable count/dimensionless units and declared
scenario assumptions. Negative probes include root250's wrong formula/unit
pair, every named cell with a different formula or invalid unit, populated
null units, null-valued populated cells, unavailable cells with values or null
reasons, inappropriate qualifications and source cells claiming stipulations.
They execute through the ACTUAL unchanged domain.validate_schema and the
standalone Draft202012 validator. Generic report grammar is not edited.

Read scope for this correction: complete root250 probe; complete existing
domain._validator/validate_schema functions; the001/002 proposed cell contract
and002 sheet schema through deterministic structural access. No new paper or
private provider material. Frozen001/002 entries are independently rehashed,
TASK bytes compared, and all owned commands are terminal before handoff.
