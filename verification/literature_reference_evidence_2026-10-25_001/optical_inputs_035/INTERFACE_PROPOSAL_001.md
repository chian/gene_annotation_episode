# Optical source operands035 — proposal before implementation

Only this new proposal file has been written. No module, tests, prompts,
shared helpers, scientific source packets or runtime state have been changed.
The active attachment and complete authority/W04/TASK-STEERING set, current
amount/assay readers, native scalar/context reader and source-field dependency,
calculator033 and its interface were read. No paper or retained case was read.
This is a finite source reader for the existing optical calculator, not a new
sheet, score, recovery factor, observation or episode. TASK feedback remains
pending. Exactly ten axes remain; A105 is first and the full goal is unfinished.

## Entry points and custody

`optical_arguments_schema()` returns a detached closed JSON schema. All declared
properties are required; absence is represented by explicit null/unknown.
`read_optical_rate_operands(selection, *, read_source)` returns a detached
ordinary dict/list record and never calls calculator033. `read_source(ref,
representation)` authorizes the actual received source and returns exactly
`{artifact_ref: nonempty string, content: bytes}`. `_Sources` caches each exact
ref/representation and verifies literal UTF8 witnesses. Root original bytes are
always authorized/read, even for an entirely partial selection.

Notation below is exact record syntax, with `?T` meaning T or null:

```
W = {source_ref: REF, representation: original|text,
     start: nonnegative int UTF8 byte offset, end: positive int UTF8 byte offset,
     quote: nonempty string}
N = {witness: W, number_start: nonnegative int, number_end: positive int}
M = {number: N, unit: ?W}
I(enum) = {value: enum, witnesses: list[W]}
Q = {measurement: ?M, measurement_identity: ?W,
     condition: ?W, measured_entity: ?W, interval: ?W}
```

N positions are Unicode character positions inside its exact W.quote; number
positions are converted to actual absolute UTF8 offsets for custody/identity.
An interval is retained literal context, not numeric arithmetic operands.
Known I values require at least one verified witness; conflicting requires at
least two distinct verified spans. The reader cannot decide whether two passages
truly conflict or whether a chosen relationship is scientifically warranted.
Unknown needs no witness but preserves any supplied witnesses.

Exact top-level selection fields:

```
{
 source_ref: REF,
 source_kind: primary_source|retained_extraction|synthetic_fixture,
 molecule: ?W, construct: ?W, preparation: ?W, condition: ?W,
 measured_entity: ?W,
 signal_kind: I(absorbance_slope|absorbance_difference|static_absorbance|unknown),
 signals: {sample: ?Q, blank: ?Q},
 calibration: {epsilon: ?Q, path_length: ?Q, wavelength: ?Q},
 relation: I(applicable_extinction_relation|not_applicable|unknown|conflicting),
 blank_role: I(matched_no_reaction_background|condition_reference|
               component_omission|unknown|conflicting),
 same_endpoint: I(same|different|unknown),
 matched_window: I(same|different|unknown),
 rate_window: I(source_supported_rate_interval|interval_mean_only|
                static_only|unknown),
 covariance_source_ref: ?REF
}
```

Q is shared mechanically across optical quantities; it does not assert that
epsilon/path/wavelength have a time interval. Null fields remain null. Per-Q
condition/entity preserve differences between sample, blank and calibration;
root context is never silently copied into missing per-Q fields.

## Exact output representation

```
{
 version: a105_optical_inputs_v1,
 source_ref, source_kind,
 context: {molecule:?EW, construct:?EW, preparation:?EW,
           condition:?EW, measured_entity:?EW},
 signal_kind: EI,
 signals: {sample:?R, blank:?R},
 calibration: {epsilon:?R, path_length:?R, wavelength:?R},
 relation: EI, blank_role: EI, same_endpoint: EI,
 matched_window: EI, rate_window: EI,
 covariance_source: ?{source_ref, artifact_ref, data: exact parsed source JSON},
 calculation_inputs: exact calculator033 operands below,
 input_unavailable_reasons: {sample_slope:list[code], blank_slope:list[code],
                            epsilon:list[code], path_length:list[code],
                            covariance:list[code]},
 dependencies: list[{primitive_roles:list[string],
                     measurement_keys:list[string],
                     physical_observation_keys:list[string],
                     primitive_observation_ref:string}],
 source_refs: list[REF] in first-authorized order,
 lexical_dependency: exact dependency metadata
}
EW is W enriched only with artifact_ref. EI is I with EW witnesses.
R = {
 meanings:{measurement_identity:?EW, condition:?EW,
           measured_entity:?EW, interval:?EW},
 number:?{selector:{witness:EW,number_start,number_end}, raw_number:string,
          value:finite native number, relation:point|lt|le|gt|ge,
          approximate:boolean},
 unit:?{witness:EW, raw_unit:string, canonical_unit:?string,
        multiplier:?finite positive number, unavailable_reason:?code},
 value:?finite converted number,
 status:observed|censored|unavailable,
 approximate:boolean,
 measurement_key:?string, physical_observation_key:?string, owner_key:?string,
 source_origin:reported|synthetic, origin:reported|synthetic|derived,
 unavailable_reasons:list[code]
}
```

R.value preserves a converted threshold when censored and a converted source
estimate when approximate. Neither is projected as an exact calculator scalar.
R.number retains the actual lexical relation and approximation; no source bytes
are rewritten. Unit unsupported/missing leaves R.value null while preserving
R.number and raw unit. Origin becomes derived only for nonidentity conversion;
source_origin retains reporting/fixture origin. A missing Q or measurement
is represented directly, never as zero. Unknown signal meaning does not erase
the selected source observations.

## Finite unit grammar and scaling

The reader owns optical units. It will not call existing amount/rate unit
parsers. Unit lexical normalization only removes inline XML/HTML tags, decodes
entities, removes whitespace, converts Unicode minus/superscript minus/one and
micro variants, and accepts `^` or no caret for inverse exponents. Original
witnesses/raw units remain exact. No arbitrary prose or dimensional inference.

| Quantity | Supported visible spellings | Canonical unit | multiplier |
|---|---|---|---:|
| slope | absorbance/min, AU/min, absorbance min^-1, AU min^-1 | absorbance/min | 1 |
| slope | absorbance/s, AU/s, absorbance s^-1, AU s^-1 | absorbance/min | 60 |
| slope | mAU/min, mAU min^-1 | absorbance/min | 1/1000 |
| slope | mAU/s, mAU s^-1 | absorbance/min | 3/50 |
| static/difference | absorbance, AU | absorbance | 1 |
| static/difference | mAU | absorbance | 1/1000 |
| epsilon | mM^-1 cm^-1, 1/(mM cm), L mmol^-1 cm^-1 | mM^-1cm^-1 | 1 |
| epsilon | M^-1 cm^-1, 1/(M cm), L mol^-1 cm^-1 | mM^-1cm^-1 | 1/1000 |
| epsilon | uM^-1 cm^-1, 1/(uM cm), L umol^-1 cm^-1 | mM^-1cm^-1 | 1000 |
| path | cm | cm | 1 |
| path | mm | cm | 1/10 |
| path | m | cm | 100 |
| wavelength | nm | nm | 1 |
| wavelength | um | nm | 1000 |
| wavelength | m | nm | 1000000000 |

Slope/static lexical unit parsing accepts the union so that a unit contradicting
the supplied signal kind is preserved with a dependent unknown, not relabeled.
Unqualified `/min`, `min^-1`, A340/min, OD/min, dimensionless, U/mg and nmol/min
are unsupported. No optical coefficient or wavelength default is supplied.
No sign is inferred from the word depletion; signed source tokens stay signed.

Use exact decimal Fraction(token)*Fraction(multiplier) with one final float
conversion. Overflow or nonzero underflow returns a repairable
`numerical_model_range` failure. Exact source point epsilon/path/wavelength
must be strictly positive; invalid exact denominators are malformed operands,
not unknown scientific evidence. Qualified thresholds are retained without
turning their bounds into exact denominator inputs.

## Lexical validation boundary

Reuse `_number(...,role='rate')` solely for its signed literal scalar,
relation/approximation, arithmetic/range/uncertainty and full-token guards. Its
historical role name assigns no optical meaning. Reuse `_field_contexts` only
for neighbours inside the real HTML/JATS cell/block. `<br/>` remains inline;
structural cells/paragraphs end context. Scalar and unit witnesses are validated
before any context lookup. Original bytes are never normalized before custody.

The new reader checks full optical unit boundaries on both sides (including
following `/`, inverse factors or physical `per` continuations), and compares
any immediately printed optical/physical unit with the separately selected
unit. An explicit supported mismatch is a repairable
`source_optical_unit_mismatch`; a printed unsupported physical unit cannot be
overridden by a remote supported unit. A shared header unit may be selected
explicitly when no adjacent unit is printed. A null unit stays unreported and
does not infer the adjacent unit automatically. Clipped numeric and clipped
unit selections fail; arithmetic/ranges are not silently reduced to a point.
Bound/approximation selections supported by `_number` remain partial records;
unsupported compound/negated/postfix qualifiers fail with existing specific
codes. This is a finite syntax contract, not unrestricted language understanding.

Dependencies pin actual inspected generations: native reader
55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500,
source fields20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17,
and `_Sources` module52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e.
The native lexical API note's older264328 generation is historical; this
proposal uses the actual active generation as the amount adapter does.

## Identity and covariance

measurement_key hashes only numeric token custody (source_ref, artifact_ref,
absolute UTF8 start/end), following existing amount conventions. It does not
include role labels or number equality. physical_observation_key hashes the
selected exact measurement_identity witness custody; equal prose in different
spans establishes no equality. owner_key hashes measurement_key, per-Q meanings,
root context and signal/calibration role meaning, preserving semantic owner
distinctions without manufacturing independent numerical tokens.

Build connected groups of the four primitive observations linked by equal
nonnull measurement_key OR equal nonnull physical_observation_key. Group refs
are deterministic `identity('literature_optical_observation', sorted custody
keys)`; no value/label equality links groups. Missing numeric observations get
null refs. Different groups establish no independence. Known reuse across
incompatible canonical dimensions or differing canonical values fails. Reused
groups must have equal canonical covariance rows/columns. Dependencies retain
all original role/measurement/physical identities even when one ref is reused.

Covariance JSON has exactly:

```
{version:a105_optical_covariance_v1,
 primitive_order:[sample_slope,blank_slope,epsilon,path_length],
 primitive_measurement_keys:[four exact keys],
 primitive_physical_observation_keys:[four nullable exact keys],
 primitive_owner_keys:[four exact keys],
 primitive_units:[four exact raw unit strings],
 covariance:[[four finite numbers] x 4],
 origin:reported|derived|synthetic,
 covariance_status:known|estimated|unknown}
```

Reject duplicate keys, nonfinite/bool values, missing or mismatched owner/unit/
order, wrong shape, nonsymmetry, negative diagonal or indefinite matrix. Numeric
owners/units must exist even if approximate/censored; unsupported unit conversion
cannot authorize covariance. Validate raw symmetry before float conversion.
Scale every entry with both exact operand factors; retain raw data and origin.
Use the same normalized PSD eigensolver tolerance as033; no jitter or clipping.
Unknown status preserves supplied matrix but keeps variance unavailable in033;
absent matrix projects null/unknown and reason covariance_unreported. Estimated
remains estimated. No independence/zero matrix is synthesized.

## Exact calculator-input projection and dependent reasons

```
{version:a105_nadh_optical_rate_operands_v1,
 sample_slope:?finite number, blank_slope:?finite number,
 epsilon:?finite number, path_length:?finite number,
 covariance:?canonical4x4 matrix, covariance_status:known|estimated|unknown,
 relation:<I.value>, blank_role:<I.value>, same_endpoint:<I.value>,
 matched_window:<I.value>, rate_window:<I.value>,
 primitive_observation_refs:[four nullable group refs]}
```

Only exact point/nonapproximate slopes with canonical absorbance/min AND
signal_kind=absorbance_slope project to the two slope fields. Other signal
kinds keep both nullable scalar inputs unavailable without rewriting the
selected rate_window. Exact supported positive epsilon/path project unchanged.
Wavelength is retained only in extraction and never enters the formula.
Relationship enums are copied verbatim, so033 alone owns their conditional
rate/variance reason precedence. This reader preserves separate operand reasons:
source_measurement_unreported, source_optical_unit_unreported,
unsupported_source_optical_unit, censored_source_operand,
approximate_source_operand, optical_signal_not_slope,
optical_signal_kind_unknown, optical_signal_unit_mismatch. More than one
applicable reason is retained in the listed deterministic order.

## Meaningful synthetic checks planned

1. Plaintext signed sample=-.012/blank=-.002 AU/min, epsilon=5000 M^-1cm^-1,
path=10 mm projects (-.012,-.002,5,1); separate033 returns2 uM/min.
2. Equivalent mAU/s and AU/min representations give the same q; raw covariance
converts with both factors, preserving signed cross terms and variance. The
existing synthetic033 diagonal/cross example gives0.0024 (uM/min)^2.
3. Same lexical sample value under slope/difference/static/unknown meanings:
only an actual slope input projects; amount/time never becomes absorbance.
4. No blank/path/epsilon and epsilon-only source partials retain available
fields, with no defaults and no fully populated optical rate.
5. Matched background versus condition reference or omission passes different
source meanings unchanged; calculator remains unavailable for nonbackground.
6. Explicit known/unknown/conflicting relation witnesses; at least two distinct
conflict spans required, while custody never claims semantic conflict validation.
7. Real UTF8 byte offsets with Unicode minus/micro, inline superscripts/entity
qualifiers, structural-cell isolation and inline br context.
8. Censored and approximate source numbers preserve thresholds/flags but do not
populate exact inputs. Clipped signs/digits/exponents/units, hidden arithmetic,
ranges, omitted or contradictory physical units fail or remain unknown as above.
9. Same token reused by sample/blank, and physical reuse across different tokens,
share refs and covariance rows; equal values in distinct tokens do not alias.
10. Covariance reordered/wrong owner/raw unit, duplicate JSON keys, bool/nonfinite,
indefinite matrix, inconsistent shared rows and status unknown/estimated.
11. Detached mutation checks, schema closure, source authorization/cache, wrong
UTF8 span/custody, source numerical overflow/underflow and invalid denominator.

No source/storage/C7/typed integration, primary-source optical rate or actual
model execution is claimed. Root inspection of this concrete interface is the
next engineering coordination step before implementing the two owned new files.
