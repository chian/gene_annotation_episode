# Additive correction002: seven formats, narrowly supported scientific links

This is an additive refinement for root review. PLAN001, interface001, both
earlier TASK proposals, all prior verification and FINAL_MANIFEST001 remain
unchanged. There is no coding release or production/test/goal/progress edit.
The successful existing joint AP selected/cold proof is not rerun.

## Exact constructor scope correction

The constructor supports the following SEVEN EXISTING FIELD FORMATS. This
corrects interface001's unnecessary two-family restriction. It does not assert
seven completed assays, scientific graders or adequate A105 coverage. All seven
use the same ordinary form/fact mechanism and finite string component rosters.

| Family | Exact registered source | Existing assignment key | Count | Schema factory |
|---|---|---|---:|---|
| Native kinetic | literature_kinetic_cells | requested_kinetic_components | 5 | literature_kinetic_storage.kinetic_cells_schema |
| Summary precision | literature_kinetic_summary_precision_cells | requested_kinetic_summary_precision_components | 30 | literature_kinetic_summary_precision_storage.summary_precision_cells_schema |
| Endpoint contribution | literature_endpoint_signal_cells | requested_endpoint_signal_components | 10 | literature_endpoint_signal_storage.endpoint_signal_cells_schema |
| Product coupling | literature_product_coupling_cells | requested_product_coupling_components | 11 | literature_product_coupling_storage.product_coupling_cells_schema |
| Calibration recovery | literature_calibration_recovery_cells | requested_calibration_recovery_components | 14 | literature_calibration_recovery_storage.calibration_recovery_cells_schema |
| Within-assay compilation v2 | literature_compiled_assay_v2_cells | requested_compiled_assay_components_v2 | 22 | literature_compiled_assay_storage.compiled_assay_v2_cells_schema |
| Common comparison v3 | literature_compiled_assay_v3_cells | requested_compiled_assay_components_v3 | 35 | literature_compiled_assay_storage.compiled_assay_v3_cells_schema |

SEVEN_FAMILY_MAPPING_002.json gives EVERY exact component code in original
order, plus each family/assignment/factory and sample. It was obtained by
metadata inspection of the same coherent joined_pin008; all six corresponding
current storage files match that pin. SEVEN_FAMILY_ORIGINAL_SCHEMA_FORMATS_002
retains the exact seven original standalone schema documents. No source data,
model, selected operation, state directory or scientific calculator ran.

The component vocabularies remain:

* Native kinetic: numerator_parameter, denominator_parameter,
  parameter_difference, parameter_ratio, log_parameter_contrast. The four
  supplemental kinetic log-model cells are outside this native family.
* Summary: each of source_ and scenario_ prepends the same fifteen names:
  reported_parameter, reported_sd, source_summary_count,
  independent_preparation_count, statistical_estimator_count,
  relative_reported_sd, mean_variance, mean_standard_error,
  relative_mean_standard_error, mean_interval_df,
  mean_interval_confidence_level, mean_interval_t_multiplier,
  mean_interval_halfwidth, mean_interval_lower, mean_interval_upper.
  In particular source_source_summary_count is the correct existing code.
* Endpoint: total_amplitude, corrected_amplitude, additional_amplitude,
  retained_fraction, additional_fraction, and each of those names with
  _variance appended.
* Product coupling: reported_product_activity, reported_cofactor_activity,
  product_per_cofactor, productive_fraction, calculated_coupling_percent,
  reported_coupling_percent, displayed_coupling_difference_pp,
  reconstructed_product_activity, product_per_cofactor_variance,
  productive_fraction_variance, productive_fraction_standard_uncertainty.
* Calibration: nominal, measured, signed_difference, recovery, relative_bias,
  percent_bias, inverse_recovery, reported_measured_spread, measured_sd,
  measured_cv, reported_recovery, displayed_minus_reported_recovery,
  correction_for_other_measurement, recovery_variance.
* Compiled v2: the sixteen existing original components plus the six named
  estimand-propagated uncertainty components, listed exactly in mapping002.
* Common v3: the twenty existing estimate_<role> components plus fifteen
  comparison/model components, listed exactly in mapping002. This is the
  CURRENT v3 format, not the unreviewed258 comparison namespace.

The signatures and output object remain:

```
a105_worksheet_template(section_requests, *, context_field="assessment_context")
    -> {submitted_form, assignment_rosters, section_roles}

validate_a105_worksheet_links(form, schema, assignment, *, read_public_record)
    -> None or declared ContractError

render_a105_worksheet(parts, form, *, section, table, public_records)
    -> None
```

Each returned `section_roles` element is exactly
`{field, source, components, numerical_role}`. The first three values are the
unchanged selected input element; the fourth is the fixed host-only code below:

| Family | numerical_role code |
|---|---|
| Native kinetic | reported_kinetic_estimates_and_descriptive_contrasts |
| Summary precision | summary_random_precision |
| Endpoint contribution | finite_endpoint_readout_contribution |
| Product coupling | product_reporter_stoichiometric_relationship |
| Calibration recovery | calibration_standard_recovery |
| Compiled v2 | within_assay_measurement_equation |
| Common v3 | functional_quantity_model_comparison |

These codes select existing section meanings for presentation. They are not
new scores, numerical cells, confidence categories, applicability guarantees or
independence judgments. In particular calibration_control_kind and a conditional
common-model scope remain in the original rows and cannot be overridden by this
host presentation role. The constructor neither rescores nor flattens them.

An input element is exactly `{field, source, components}`. A source must be one
of the seven table entries, and its components must be unique strings from that
row's exact finite vocabulary, retaining requested order. A section may contain
multiple actual experiments' rows under the family contract. One field per
source family remains required because facts are keyed by family; a second field
with the same source would receive the same family facts rather than a separate
component subset. A duplicate field/source raises the existing proposed
constructor error rather than implying independent experiments.

Only caller-selected families appear. There is no default all-seven worksheet,
forced operation order, auto-population or assertion that every source can fill
every component. Existing unavailable and conditional rows are valid results.
The constructor can preserve an explicitly empty roster, without treating it
as permission or a requirement to populate any cells. The original assignment
and requested-form meanings still define the task.

## Exact format examples

Each of these is a FORMAT example, not a joint experimental assessment:

```
{field: "native_parameter", source: "literature_kinetic_cells",
 components: ["numerator_parameter"]}
{field: "precision", source: "literature_kinetic_summary_precision_cells",
 components: ["source_reported_sd"]}
{field: "endpoint_signal", source: "literature_endpoint_signal_cells",
 components: ["retained_fraction"]}
{field: "product_coupling", source: "literature_product_coupling_cells",
 components: ["product_per_cofactor"]}
{field: "calibration", source: "literature_calibration_recovery_cells",
 components: ["recovery"]}
{field: "within_assay", source: "literature_compiled_assay_v2_cells",
 components: ["corrected_activity"]}
{field: "comparison", source: "literature_compiled_assay_v3_cells",
 components: ["product_reference_contrast"]}
```

The three corresponding exact JSON artifacts are:
SEVEN_FAMILY_REQUESTS_FORMAT_EXAMPLE_002.json,
SEVEN_FAMILY_ASSIGNMENT_ROSTERS_EXAMPLE_002.json, and
SEVEN_FAMILY_DECLARATION_FORMAT_EXAMPLE_002.json. Each numerical form field is
exactly `{"$ref":"episode-fact:<existing-source>"}` before the ORIGINAL host
expands it. The seven-family declaration adds the same closed nonnumerical
assessment_context from001, with field/component enums instantiated for the
actually chosen section requests. Original schemas retain their native roots,
local $defs and exact component/formula/unit/status pairing. The format grammar
check passes with those unchanged original documents; no alias runtime, new
constructor or semantic-link implementation is claimed executed.

## Positive links stay narrower than format support

Constructor support for a family does not make its physical operands eligible
for another family's equation. The existing numerical rows already carry
their scientific meanings and uncertainty limits. Any family can be present
with no cross-section links, or explicitly unresolved links, while preserving
all its valid requested numerical results.

The proposed positive-link implementation remains limited to these routes:

| Relationship | Permitted route and necessary delivered evidence |
|---|---|
| same_reported_parameter | Requested native kinetic numerator_parameter or denominator_parameter, quantity=cell_value, to summary source_reported_parameter, quantity=cell_value. Match the side's public measurement anchor to a summary parameter dependency location, compatible parameter kind/units and actually delivered subject/context. A source number match alone proves neither mean identity nor complete estimator hierarchy. |
| same_reported_spread | Requested native side's own reported_spread to summary source_reported_sd.cell_value. The selected native row must deliver uncertainty_values and the public magnitude anchor; summary must supply the matching spread dependency. Both must retain SD and compatible units. A neighboring side's withheld spread does not qualify. |
| same_count_report | Requested native side's reported_count to summary source_source_summary_count or source_independent_preparation_count.cell_value. Require the same public count token/dependency and compatible actual count/repetition meanings. For independent_preparation_count specifically preserve supported physical-preparation meaning/row applicability. Equal count values cannot prove this. This link never promotes physical n to statistical n. |
| conditional_precision_of_report | A source reported_sd or independent_preparation_count cell and an explicitly conditional scenario_mean_variance or scenario_mean_standard_error from the SAME summary receipt, with matching delivered SD/count dependencies and the original stated model premises/stipulations. It links precision to its selected report; it does not establish the central estimate is the arithmetic mean. |

If necessary public records, role-specific dependency locations, subject or
uncertainty meanings were not returned, a positive link is unsupported; retain
an unresolved link. Do not open full private child sheets to repair it. A
scenario field without stipulations does not automatically acquire a new
conditional qualification. The initial conditional link route above is for
actually conditional rows; other scenario/source identities retain their native
meaning without a forced positive link.

For endpoint, product, calibration, compiled-v2 and common-v3 sections the
new cross-section positive quantity-link operations are NOT implemented by
this proposal. Their selectors allow quantity=cell_value only; same-report,
same-spread, same-count or conditional-precision declarations involving these
families return a specific unsupported-link diagnostic unless marked unresolved
or conflicting with actual delivered support. This is a narrow implementation
limit on a new linkage checker, not a claim that the source lacks a real
relationship. Existing within-family dependencies/formulas stay intact.

For example endpoint already computes C=F D and D=C+G; compiled-v2 already
computes (q-g)v/(kEu) with explicit physical roles; product/calibration/common
calculators already retain their own sums, ratios and uncertainty. Return those
existing results rather than invent a new worksheet multiplier. Missing actual
source g, active amount, assay linkage or covariance stays missing. No endpoint
fraction becomes an initial rate, mean precision becomes accuracy, or ratio
agreement becomes molecular attribution.

Nonnumerical assertion links remain constrained interpretations about actual
delivered endpoints and named weaknesses. They do not activate a numerical
join, grade source reputation, or calculate W05/A101 transfer. If an endpoint
bridge or effect-isolation control is unresolved, that limitation survives.

Rate-grid/gel complex selectors, extra namespaces and future258 integration
are explicitly outside this constructor refinement. No seven-family biological
dataset/example is fabricated: the positive controlled proof remains the same
AP native+summary pair, and the separate endpoint example remains its own
Mvh/Hdr assessment.

## Prompt proposal correction and ownership

Prefer reusing the COMPLETE existing detailed EXPERIMENTAL_TASK as the recurring
child base. It already covers supplied-material discovery, actual subjects,
experimental relationships, native measurements/uncertainty, targeted reading,
iterative decisions, typed returns and ordinary accounting. Replacing it with
the new eight paragraphs would create unnecessary duplicate general guidance
and prompt churn. The earlier eight-paragraph and AP-specific composed drafts
remain historical proposals, not adopted runtime instructions or a new episode.

The parent's base remains its COMPLETE existing REFERENCE_PARENT_TASK, with the
actual parent question/scope, followed only by relevant full scientific aspect
instructions. It is not replaced by the child's generic task.

The real gap remains generic native kinetic parameter instructions: existing
KINETIC_MODEL_TASK describes a supplemental two-estimate covariance/log model.
NATIVE_KINETIC_TASK_PROPOSAL_003.txt supplies direct single-parameter and
requested descriptive-contrast guidance as one reusable scientific insert,
not an AP episode/template. Keep the existing full summary/endpoint/product/
calibration/compiled/common TASKs when the exact selection trace makes them
relevant. TASK_SELECTION_TRACE_002.md defines that trace, including capability
markers, lookups, history/failure and both parent/child boundaries.

The proposed pure TASK module therefore holds the new generic native kinetic
insert and selection metadata/helpers, reusing existing common/aspect texts;
it does not need another common A105 eight-paragraph constant. The previously
proposed exclusive file ownership is unchanged. Existing numerical reader/
calculator files, descriptors/history, production/tests and all old261
artifacts remain untouched. Later integration can adjust the exact relevant
selection helper and both prompt builders only after root review.
