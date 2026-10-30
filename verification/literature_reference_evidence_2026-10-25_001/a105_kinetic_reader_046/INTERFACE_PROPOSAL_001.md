# Native kinetic-parameter reader046: proposed finite boundary

Code/interface design only. No primary paper, retained scientific packet,
actual observations, model history or live scientific state was opened. No
shared file has been changed. Calculator045's released001/002 contract and the
parent-approved forthcoming003 missing-unit refinement are dependencies.

## Ownership and public functions

Proposed NEW files only: `gene_annotation_episode/literature_kinetic_inputs.py`,
`tests/test_literature_kinetic_inputs.py`, and this verification directory.
No existing parser, prompt, catalog, storage, episode or dependency changes.

Public functions: `kinetic_arguments_schema()` and
`read_kinetic_inputs(selection, *, read_source)`.
`read_source(source_ref, representation)` returns exactly
`{artifact_ref: nonempty string, content: bytes}`. Its caller owns actual
received/scope/page authorization; this pure reader verifies selected bytes.
Only original/text representations, exact UTF8 source witnesses and native
literal numerical tokens are supported. No source acquisition, OCR, raw curve
fitting, selected operation, Store, model, controller or numerical scoring.

The return's `calculation_inputs` exactly matches045's closed canonical input.
The reader does not call `populate_kinetic_contrast` or create scoring cells.
Tests may pass the extracted input to that calculator to establish compatibility.

## Closed selection shape

Root fields:

    version: a105_kinetic_source_selection_v1
    source_ref: actually received root source
    source_kind: primary_source|synthetic_fixture
    numerator: operand selection or null
    denominator: operand selection or null
    comparison: {subject_relationship,parameter_definition_relationship,
                 substrate_arrangement,comparison_scope,
                 nonintended_conditions_relationship}

Each comparison field is `{value: one exact045 enum, witnesses: [Witness...]}`.
Unknown permits no witness; conflicting needs two distinct source locations;
other values need at least one. These are explicit scientific interpretations,
not numerical grades and not scientifically proved by quote matching.

Each operand selection:

    parameter_kind: {value: Km|kcat|catalytic_efficiency|unknown|conflicting,
                     witnesses: [Witness...]}
    subject: {organism,genotype,molecule,construct} [Witness or null]
    context: {substrate,preparation,experiment,experimental_system,
              conditions,endpoint,normalization} [Witness or null]
    measurement_identity: Witness or null
    measurement: {number: NumberSelector,unit: Witness or null} or null
    qualification: {value: reported_point|source_qualified_approximate|
                           unknown|conflicting,witnesses: [Witness...]}
    uncertainty: {
        statistic: {value: sd|sem|ci|unspecified|unreported,witnesses:[Witness...]},
        magnitude: NumberSelector or null,
        interval: IntervalSelector or null,
        unit: Witness or null,
        unit_relationship: {value: same_as_parameter|explicit_unit|unknown,
                            witnesses:[Witness...]},
        confidence_level: Witness or null,
        count: NumberSelector or null,
        repetition_basis: {value: biological_preparations|technical_measurements|
                                  unspecified,witnesses:[Witness...]},
        estimate_basis: {value: fit_to_averaged_curve|between_fitted_parameters|
                               unknown,witnesses:[Witness...]}}

Witness is exactly `{source_ref,representation,start,end,quote}`: byte offsets
in original/text source, exact unmodified quote. NumberSelector is exactly
`{witness,number_start,number_end}`: Unicode character offsets in verified quote,
never a caller-supplied number. IntervalSelector has one witness plus
lower_start/lower_end/upper_start/upper_end; only complete `[lower, upper]` or
`(lower, upper)` literal intervals are supported in this initial route. Other
interval syntax remains unimplemented; neither endpoint becomes a point.
Confidence-level witness is a complete literal percentage, e.g. `95%`; its
conversion to.95 is deterministic. No confidence level is supplied by default.

SD/SEM/CI and known repetition/fit bases need supporting source witnesses.
Unspecified does not become SD. CI uses interval endpoints with magnitude=null;
source spread, interval, confidence level and repetition count stay separate.
Absent uncertainties are allowed. A nonnull unsupported uncertainty unit
preserves raw spread/interval but leaves normalized uncertainty unavailable.

## Exact parsing, units and partials

Reuse only fully read exact custody `_Sources` and native `_number` /
`_field_contexts` helpers (and their complete lexical helper paths). Native
number parsing preserves recognized upper/lower limits and approximation;
clipped signs/digits/exponents, percentages in parameter roles, arithmetic,
numeric intervals as scalars and uncertainty-as-parameter selections reject.
Dedicated interval parsing verifies the complete selected interval syntax and
whole-token bounds; percent confidence levels are separate from parameter
numbers. Numeric conversion uses exact decimal Fractions before finite float
rounding. Underflow/overflow cannot manufacture zero or infinity.

Canonical targets: Km→uM; kcat→per_min;
catalytic_efficiency→uM^-1min^-1. Finite case-sensitive SI source units include:

- Km: M,mM,uM,nM (µ/μ spellings accepted).
- kcat: per_min/per_s, min^-1/s^-1,1/min/1/s.
- Efficiency: inverse M,mM,uM,nM times inverse min/s; recognized explicit
  negative-power or reciprocal-product forms only.

Thus M^-1s^-1 multiplies by60/1,000,000; mM^-1min^-1 by1/1,000;
uM^-1min^-1 by1. Preserve case; M and mM never merge. Strip recognized inline
markup/Unicode superscript spelling only for parsing; raw bytes remain exact.
Reject clipped unit compounds and conflicting explicit adjacent units even
when a compatible remote header was selected. A complete unsupported unit is
retained as a structured partial, with no canonical value or guessed scale.

Unknown/conflicting parameter kind emits a null calculator operand and full
retained row with specific reason. Known kind with absent/unsupported unit or
unknown/conflicting qualification emits a missing/conflicting045 operand with
unit=null and parent-approved003 `unavailable_reason`; raw numerical token,
unit and all source context remain in the extraction. Point/censored operands
have the actual matched canonical unit. Approximate points remain flagged;
censored thresholds remain censored;045 withholds inappropriate model scores.

`measurement_id` derives from the exact numeric token byte locator, never a
model string. `physical_measurement_id` derives only from a selected exact
measurement-identity witness, otherwise null. A common paper/label never
supplies preparation or physical identity. Actual selected numeric start/end,
not the containing paragraph span, become045's source locator. Copies of the
same token cannot create distinct pair observations by relabeling fields.
An operand with no number uses its parameter witness for an unavailable-record
locator/ID, explicitly distinct from a physical observation; if neither exists,
the calculator operand is null. All raw selections remain retained.

## Output and scientific applicability

Closed extraction fields: version,source_ref,source_kind,operands,comparison,
calculation_inputs,input_unavailable_reasons,source_refs,implementation_dependencies.
Each retained operand contains enriched literal/interpretation witnesses,
original number/unit/uncertainty records, exact canonical projection and
explicit reasons. Roster contains actual callback-accessed source refs.

The finite scientific question is comparison of reported kinetic parameters
for substrates in separate assays of an actual molecule/construct. Reader
preserves per-row conditions/endpoints and distinguishes reported protocols
from common-condition claims. It does not infer matched conditions, catalytic
product identity, active enzyme amount, intrinsic affinity, physiological
preference, experimental reliability, source-to-target transfer or independence.
No automatic quotient of kcat/Km means, model/covariance reader, joint score,
parameter fitting or experimental correction belongs to this workload.

Synthetic verification: exact UTF8 custody/callback denial; all three parameter
dimensions and inverse scales; native bounds/approximation; unknown/unit
partials; conflicting explicit units; clipped tokens/units; raw uncertainty,
CI/percent/count semantics; shared token/physical owner; immutable inputs;
045 compatibility and missing-model nullS. No primary-source or runtime/model
success is claimed by these tests.

## Read coverage

Full active goal,rootAGENTS,W04 correction/history,045001/002; complete
experimental_contracts,assay_inputs,partner_source_fields,rate_native_inputs,
optical_inputs. Latest040 then039 human instructions read last before this
proposal. This is code design, so no new post-paper reset is claimed or needed.
