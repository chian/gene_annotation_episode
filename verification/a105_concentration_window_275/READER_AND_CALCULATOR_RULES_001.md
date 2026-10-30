# Exact validation/calculation supplement to proposal001

This is an implementation contract proposal, not implemented validation. The
schemas are syntactically checked; the complete behavior below is still to be
coded after root review. No shared path is authorized by these artifacts.

`read` returns EXTRACTION, `compile` returns CALCULATION_INPUTS and `populate`
returns SHEET. Proposed schema and validation factory names are respectively
`concentration_window_selection_schema`, `concentration_window_extraction_schema`,
`concentration_window_calculation_inputs_schema`,
`concentration_window_sheet_schema`, `concentration_window_covariance_schema`,
`validate_concentration_window_extraction`,
`validate_concentration_window_calculation_inputs`,
`validate_concentration_window_sheet`. The last validator accepts optional
`inputs=` and recomputes complete selected sheet content when supplied.
Compilation accepts an already validated extraction and does not reclassify
source meanings. Saved extraction validation checks the same retained lexical
values, units, source-owner associations and scientific selections, without
source IO. A cold validator cannot independently prove the original source
bytes; custody belongs to their retained original artifacts.

Scalar syntax is signed decimal/exponent: `[+−-]?(digits[.digits?]?|.digits)
([eE][+−-]?digits)?`, with an entire numeric token. This notation is a grammar
description; implementation uses the existing scalar lexical guards. The
reader inspects the full cell or surrounding original text, including qualified
comparators, approximation, uncertainty, negation, arithmetic and unit
continuations. A selected `3` inside `13`, `3e2` or `<3` cannot become an exact
reported 3. `ND` without a limit has no exact value. Selected SD/SEM/count
passages remain uncertainty context, never alternative point estimates or C.
No numeric conversion from an arbitrary string is permitted.

Unit normalizations strip surrounding whitespace and recognized source markup,
collapse internal whitespace for matching, map µ and μ to u, and preserve case.
Concentration exact spellings after normalization are:

| Tokens | Multiplier into µM |
| --- | ---: |
| M, mol/L, molL^-1, molL−1 | 1000000 |
| mM, mmol/L, mmolL^-1, mmolL−1 | 1000 |
| uM, umol/L, umolL^-1, umolL−1 | 1 |
| nM, nmol/L, nmolL^-1, nmolL−1 | 1/1000 |
| pM, pmol/L, pmolL^-1, pmolL−1 | 1/1000000 |

Seconds: s, sec, second, seconds →1; min, minute, minutes →60;
h, hr, hour, hours →3600. Other spellings are retained with
`source_unit_unsupported`. Molarity and amount/mass rates, percent, dose and
arbitrary signal are not accepted as concentration. Adjacent explicit source
unit and selected unit must match; a unit may not be clipped from a rate. Unit
association must be supported by the selected header/shared-header/method.

Concentration basis must be native reaction concentration for derived chemical
comparisons in v1. No general dilution/back-calculation is implemented here.
`other_normalized_concentration` and `quenched_sample_concentration` are kept,
with `normalization_mapping_unresolved` for dependent cells. Source concentrations
already reported on native reaction scale do not receive a second dilution
correction. A missing blank or recovery does not get numerical defaults.

Workbook cell reading uses the existing Workbook decoder on authenticated
source bytes. Grid checks require: exactly one matching sheet key/name/part;
three different analyte columns; a different coordinate column; header/start/end
rows positive and distinct; quantities use their exact bound columns/rows;
analyte witnesses use bound header cells; coordinate witnesses use the bound
coordinate cell on the corresponding row. A shared-header unit has a witness
in the grid's header row and a supported applicable association. Applicable
method associations are witnessed interpretations, not inferred by proximity.
Read all cell XML bytes needed for token edges and cache flags, not merely a
selected substring. Duplicate cell addresses/parts, malformed XML, unresolved
shared strings and wrong bindings are structured errors. Do not choose the
first match. Formula and cached lexemes are retained in source custody, but
this version returns `formula_cache_point_unimplemented` rather than a physical
point. Formula recalculation is outside this reader.

Text readings require number, analyte and coordinate fields within the selected
record, except applicable shared header/method units with declared support.
For two-row records, each endpoint has its own record; shared analyte/header
witnesses must be structurally associated by the existing table parser.
Unsupported text layout returns an implementation reason if an otherwise
retained reading cannot be associated. An invalid quote or unsafe source
binding is a contract failure; missing or unsupported valid scientific material
produces partial readings/cells. It is never accepted as a fabricated point.

Every supported interpretation needs at least one distinct original-source
witness. Conflicting interpretation needs at least two distinct witnesses.
Witness existence does not prove the biological interpretation; it records
which evidence the episode used. The calculator takes those constrained
meanings, without a model call or name-based biological classifier.

Source location identity is byte based for text and original artifact/worksheet
part/cell/decoded subspan for workbook tokens. Byte positions refer to the
decompressed member, not ZIP container offsets. Retain member digest and the
corresponding XML cell span. Shared-string-derived fields also retain the
original shared-string entry location and digest. UTF-8 text byte boundaries
and decoded cell character indices must not be mixed. Physical experiment or
preparation identity remains unknown unless separately supported: equal values,
adjacent cells and serial timepoints do not establish independence.

An owner key identifies the retained scalar selection; dependency keys identify
the source observation plus any explicitly shared calibration/normalization
evidence. A null physical_owner_key means physical experiment identity unknown,
not unique. Exact repeated native source tokens are known reuse. Different
source tokens do not establish different physical observations. Exact repeated
start/end source readings must return `reused_physical_operand` for a supposed
change. Shared calibration is a dependence link, not a numeric covariance.

All derived point cells need point inputs, no approximation and established
native normalization. A source approximate point can be retained natively with
approximate=true; approximate downstream arithmetic is unfinished in this v1.
Bounded points remain native threshold/bound fields, with value=null; dependent
arithmetic gets `bounded_arithmetic_unimplemented`. Nondetection has no inferred
zero. Required unavailable operands accumulate all applicable reasons, rather
than selecting a flattering reason. Source unavailable, unselected, unresolved
relationships, implementation gaps and numerical domain limits occupy separate
reason arrays.

Per-analyte deltas need `same_series`, `same_window`, `concentration_basis`
supported. Chemical discrepancy/ratios/fate also need `same_aliquot_window`,
`calibration_linkage`, `endpoint_assignment` and applicable stoichiometry
supported. A native reading does not require all pair relationships. Coordinate
span is computed from source coordinates and units before elapsed-time meaning.
Source physical interval averages need `actual_sampling_time`, positive span
and the relevant delta. Scenario interval averages need source timing unknown
plus the explicit sensitivity stipulation; no scenario override of a known
plot-only or conflicting time interpretation. The two value populations never
merge. Stipulation is a meaning assumption, not invented sampling data.

Each cell's component/formula/unit/meaning/operand_roles must equal
COMPONENT_DEFINITIONS_001.json. Native origins follow authenticated source kind;
derived origins are calculated (or synthetic for wholly synthetic inputs), not
reported. A derived cell cannot be mislabeled primary-source reported merely
because all its inputs were reported. All cells from the selected window carry
one contribution key and their exact union of operand/model dependencies.
No contribution key implies a final annotation-credit quantity.

value/exact_value exist only for populated source cells. conditional values
exist only for conditional_scenario cells with the declared timing stipulation.
Unavailable cells have both value populations null and specific reasons. No
source value is promoted from a conditional scenario. Exact rational values
must be reduced with positive denominator, consistent with finite displays.
Native bounds use threshold and bound without pretending a physical point.

Covariance JSON is decoded with exact decimal token preservation. Retained
covariance_reading.matrix_exact contains the reduced rational matrix; it is
null only for unknown covariance. It must agree numerically with the retained
document and is tied to its original artifact digest. There is one optional
selected block, not a guessed assembly of independent incomplete blocks.
Role list is nonempty/unique, with exactly corresponding owner, unit and
dependency lists. Every listed role is a selected point estimator with matching
owner/dependencies and canonical unit. Matrix order and dimensions match those
roles. Symmetry and positive semidefiniteness are exact-rational checks, without
an arbitrary tolerance, truncation or jitter. Unknown matrix entries stay unknown.
A JSON number rejected for nonfinite/range reasons does not become zero.

For a component requiring a subset of roles, a valid C covering that subset
is sufficient; unrelated missing roles do not block it. For nonlinear components
use the declared first-order derivative, never a p-value. The matrix G C Gᵀ
contains only the eligible selected VAR_BASES whose means have the required
physical interpretation. Its row names and covariance source are explicit. A
ratio variance includes all cross-covariances; do not add independent variances
unless their zero covariance was explicitly supplied. No conditional timing
variance is implemented in this version. Stoichiometric coefficients must be
source-supported exact chemical coefficients; uncertainty/ambiguity there is
not silently treated as exact measurement knowledge.

Structured contract failures use ExperimentalContractError with `field` and
one of: `concentration_window_closed_schema_required`, `source_quote_mismatch`,
`source_artifact_mismatch`, `source_span_out_of_bounds`,
`source_span_utf8_boundary_required`, `concentration_window_sheet_binding_mismatch`,
`concentration_window_duplicate_cell`, `concentration_window_record_association_mismatch`,
`partial_source_numeric_token`, `source_unit_mismatch`, `interpretation_witness_required`,
`concentration_window_covariance_owner_mismatch`, `concentration_window_covariance_unit_mismatch`,
`concentration_window_covariance_dependency_mismatch`,
`concentration_window_covariance_matrix_invalid`, `concentration_window_saved_selection_mismatch`,
`concentration_window_saved_arithmetic_mismatch`. Existing helper contract errors
retain their original codes/fields rather than being flattened into success.
Unsupported valid material uses the schema's typed implementation reasons.
