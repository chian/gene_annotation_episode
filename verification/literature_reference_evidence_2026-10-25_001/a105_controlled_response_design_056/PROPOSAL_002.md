# 056 proposal: controlled four-arm source response

Proposal only. No production module, test, scientific TASK, episode, route or
credit rule is changed. The root supplied the scientific requirement after its
own case review and instruction reset. This worker opened no paper or retained
paper-specific packet and claims no independent scientific source coverage.

This is a component of the single incomplete A105 sheet. A future ordinary
literature investigation can select it for a relevant experiment/claim; it is
not a paper classifier, a general transport quality grade or another axis.

## Numerical meaning before the reader

Let the fixed role order be

    protein_condition1, empty_condition1, protein_condition0, empty_condition0.

The two factors are the assayed protein/control arrangement and the intended
protocol condition. The four responses must describe the same measured endpoint
on source-established compatible normalization bases. Define

    d1 = x[0] - x[1]
    d0 = x[2] - x[3]
    e  = d1 - d0 = [1,-1,-1,1] x
    V  = l C l-transpose, l=[1,-1,-1,1].

This is a protein-associated change between the two protocols, conditional on
the stated control/normalization relationships. It does not alone establish
isolated causal action, absence of contaminants, transport of a particular
chemical species, proton coupling or a physiological function. Other protocol
cochanges remain visible; the deliberately tested condition is the signal and
is never divided away as a quality penalty.

The component has twelve numerical representations, not twelve independent
proofs: four native response cells, d1, d0, e, V, sqrt(V), 1/V, optional signed
profile S and proposed bounded index B. The first seven preserve useful source
magnitude even when uncertainty/model reading is unavailable.

Only for an explicitly supported jointly normal source-mean model with known
positive V, complete observed point operands and no unresolved rounding/censor
mechanism:

    S = e*abs(e)/(2V), B=tanh(S/2).

These retain the current proposed signed-source meaning, not function
probability, an overall reliability category or final annotation credit.
Estimated C can support a stated variance estimate; it cannot be promoted to a
known-normal likelihood. Finite-sample/clustered/censored model readers remain
separate unimplemented capabilities until their actual model contracts exist.

## Worked synthetic sheet

All numbers here are invented. The normalization is expressly stipulated as the
same positive paired-reference protein-input mass for all four arms, including
the empty controls. It is not protein mass measured inside a protein-free arm.

| Cell | Input/calculation | Synthetic value | Unit/meaning |
| --- | --- | ---: | --- |
| protein_condition1_response | Source literal |12| nmol/min/mg paired-reference input |
| empty_condition1_response | Source literal |2| Same reference basis |
| protein_condition0_response | Source literal |5| Same reference basis |
| empty_condition0_response | Source literal |1| Same reference basis |
| condition1_controlled_response |12−2|10| Same specific amount-rate unit |
| condition0_controlled_response |5−1|4| Same unit |
| controlled_response_difference |10−4|6| Protein-associated protocol contrast |
| contrast_variance |l diag(1,.25,.36,.09) lᵀ|1.7| Squared specific amount-rate unit |
| contrast_standard_uncertainty |sqrt(1.7)|≈1.303840481| Same specific amount-rate unit |
| contrast_precision |1/1.7|≈.588235294| Inverse squared unit |
| source_profile_log_ratio |No normal model selected|null| Missing model, not zero |
| source_signed_index |No S|null| No invented confidence |

The source parser's canonical base is µmol/min/mg: .012,.002,.005,.001, giving
e=.006 and V=.0000017 in the corresponding squared base unit. Keeping a native
display alongside canonical values must not apply the factor .001 twice.

Adding a common uncertain offset with covariance .16 to every C entry leaves
V=1.7 because l sums to zero. That exact shared-error cancellation is different
from silently assuming four independent arms. Equal response values alone do
not establish a common offset or identity.

## Actual reuse audit and reproduced limits

`reproduce_interfaces.py` executed the existing functions on invented source
bytes with a non-ASCII prefix. It supplies source selectors, not pre-parsed
measurement numbers. Its retained receipt records:

| Existing path | What is usable | Actual limit |
| --- | --- | --- |
| rate-native _Sources/_number/_unit/_converted | Exact UTF8 custody, Unicode inner selectors, signed/censored/approximate literal parsing, explicit source-defined rate units and exact rational scaling | Public read_rate_source_inputs accepts exactly reference/test. Four named roles reject closed_fields_required at arms. |
| populate_rate_contrast | Existing two-arm descriptive differences/ratios; native partials | Actual pair calls gave .010 and .004 µmol/min/mg. Its uncertainty route is a two-group independence model; it has no full four-arm covariance input. Do not chain independent-SE outputs and lose cross terms. |
| assay input/activity correction | Custody machinery and separation of q,g,k,E,u,v | Actual nmol/min/mg q rejects incompatible_primitive_unit. Concentration-rate/molecule normalization cannot be used for these operands. |
| transport response | Same-curve concentration/Km correction, owned 3×3 covariance pattern | It is a response-factor operand, not this four-arm effect. No Km or saturation enters e. |
| figure measurement/input route | Deterministic linear-axis filled-bar edge extraction with retained pixel bounds | Its finite native units are percent, arbitrary signal and nanomolar. Actual nmol/min/mg calibration rejects unsupported_calibration_unit before decoding. Relabeling it arbitrary signal would be wrong. |
| visual049 _Inputs | Actual image decoding, source hashes, original/crop mapping and image/text witness authentication | Public binding reader assumes binding parameters/units and a known context; use only the already read deterministic custody primitives. Image quotations remain episode transcriptions, not OCR truth. |
| base044 repository | Actual selected-operation ownership, exact admitted subset, original runtime-form authentication, receive/reconstruction | Reuse these methods unchanged; holding a sheet reference does not grant all private cells. |

The research script separately evaluates the transparent proposed e/V formulas
using Fraction. That reference arithmetic is not a new installed calculator,
selected operation or scientific finding. It creates no Store, model request,
runtime observation or annotation credit.

## Proposed selected request: controlled_response_source_selection_v1

All keys are required; unavailable selections are explicit nulls. Scientific
numbers are never direct selected arguments. Pixel coordinates/thresholds are
mechanical recipe parameters, not measured response values.

    version, source_ref, images, arms, relationships,
    covariance_source_ref, covariance_status, model_kind, model_witnesses

`arms` has exactly the four named roles. Each arm is null or:

    source_kind
    subject, organism, genotype, construct, preparation, experimental_system
    protein_arrangement, subject_construct, condition, intended_factor_level
    endpoint, normalization, physical_observation
    measurement
    reported_uncertainty

The ordinary subject/context fields are nullable authenticated witnesses.
Endpoint, normalization, subject_construct, condition and physical_observation
use Meaning records:

    {status: known|unknown|conflicting, label:null|string,
     witnesses:[Witness], canonical_witness:null|Witness,
     canonical_correspondence:{value:same|unknown|conflicting,
                               witnesses:[Witness]}}

Known canonical IDs use the meaning dimension and the actual authenticated
canonical witness locator. A nonnull canonical ID requires known status, a
nonnull canonical witness, and an explicit same interpretation in the
canonical_correspondence record; unknown/conflicting correspondence gives a null
ID. Selecting the same canonical condition witness for differently worded source
conditions is an explicit source-conditionalias interpretation, supported by each
role's own witnesses and the correspondence witnesses. Equal labels never supply
that interpretation. Distinct known meanings use their own distinct canonical
witnesses. Own witnesses survive alias selection. The episode supplies these
interpretations; byte authentication does not establish their scientific truth.

`protein_arrangement` is witnessed protein_present|protein_free_control|
empty_vector_control|other_specified|unknown|conflicting. The names are meanings,
not numerical quality categories. The actual construct/genotype remains visible;
an empty vector does not establish absence of other proteins or uptake pathways.

`physical_observation` is a separately witnessed original observation/fit
identity Meaning, including unknown when unavailable. The reader also computes
a source-cell/token identity. These are
different: a new plot/crop/table can represent the same experiment, and identical
values can come from different experiments.

Witness is an exact UTF8 source span or the frozen049 tagged image witness.
The root `images` list uses049's image/source/original/crop contract. Every
selected source is authorized before bytes are exposed; actual mapping requires
the original pixel equality, not a caller's geometry claim.

### Literal measurement

    {kind: source_literal, number: NumberSelection, unit:null|UnitSelection}

NumberSelection retains the existing exact text witness plus number_start/end.
Text numbers reuse `_number(...,role=rate)` so signed readings, printed limits,
approximation and all clipping/arithmetic/unit-role guards survive. UnitSelection
reuses exact native unit/definition selection. A missing or unsupported unit
keeps native value/raw unit and leaves the canonical value unknown. No factor1
canonical unit is assigned. A complete unsupported source expression is retained
as a partial; a false quote/clipped selector is an actionable argument error.

Source_kind is per arm: primary_source, retained_extraction, synthetic_fixture.
Actual graph-derived origins are set by the graph measurement branch below,
not by an unchecked origin label on a transcribed numeric table.

### Graph measurement

    {kind: linear_bar, image_id, bar_selection, axis}
    axis={first:{pixel,tick:Literal},second:{pixel,tick:Literal},unit:Literal}

Literal uses exact|ambiguous|unreadable|conflicting with authenticated candidates
and fragments. Tick candidates can be exact text spans or image-region
transcriptions. A deterministic parser derives each tick value from the selected
raw expression; direct axis values and direct bar ordinates are not accepted.
An image quotation is explicitly investigating_episode_interpretation, with
image_bytes_and_geometry_only authentication. There is no OCR claim.

`bar_selection` has ROI, RGB bounds, minimum row fraction/run length and edge
tolerance, as in the existing pixel helper, but no caller-supplied scientific
calibration values. Internally parsed ticks form the helper calibration. The
existing native figure helper needs a scoped, separately versioned rate-unit
extension before this graph branch is implemented. Its pixel algorithm can be
reused; calling arbitrary_signal and changing its unit afterward is forbidden.
This is required implementation work, not current coverage.

Exact bar calibration yields a nominal graph ordinate plus the native conditional
digitization interval and original image/recipe identity. These bounds are not
SD/SEM, biological confidence or a censor threshold. Ambiguous tick candidates
remain alternatives; no favorable candidate, hidden mean or guessed axis is
selected. Failed/missing image/crop dependency affects that arm, not other valid
raw operands. Unsupported axis shapes remain explicit unavailable inputs.

### Reported uncertainty

    {statistic, magnitude, interval, confidence_level, count,
     repetition_basis, estimate_basis}

Each meaning is witnessed and permits unknown/conflicting. Numeric selections
are nullable source Literals. Known CI endpoints/level and SD/SEM magnitudes can
be independently missing. Known-source spread survives an unresolved statistic;
it must not be relabeled unreported. A count is the reported count only, never
the number of source witnesses or an inferred biological-preparation count.
Reuse a released count capability only after its exact interface/fingerprint is
reviewed; current055 ownership is not permission to import a moving interface.
Unsupported count syntax remains a raw partial. No count/spread supplies C by
itself. Local/global incompatible error descriptions retain both witnesses and
conflicting meaning.

## Experimental relationships and normalization

`relationships` has exactly the following fields:

    condition1_target, condition0_target, condition_levels_relation
    condition1_control_application, condition0_control_application
    subject_construct_across_conditions, control_reference_reuse
    nonintended_conditions, intended_factor

The two target fields are condition Meanings. The other categorical fields are
records {value,witnesses}, with only the following finite values:

- control_application: matched_condition_control|shared_reference_assumption|
  unknown|conflicting.
- subject_construct_across_conditions: same|different|unknown|conflicting.
- condition_levels_relation: same|different|unknown|conflicting; this is an
  explicit source interpretation, never inferred from differently spelled IDs.
- control_reference_reuse: distinct_observations|
  same_reference_with_stated_invariance|unknown|conflicting.
- nonintended_conditions: matched|different|unknown|conflicting.
- intended_factor is a nullable authenticated witness, not a categorical score.

There is no global four-arm endpoint/normalization status. Each derived cell
uses the exact canonical-ID comparisons specified below; unresolved condition0
cannot erase a valid condition1 pair. A known endpoint/normalization ID mismatch
is different; a missing ID is unknown; source-conflicting meaning is conflicting.
Canonical IDs are source-witness-bound interpretations, never equal-name tests.
Known differences outside the intended factor remain qualifications of the
actual protocol comparison; they are not converted to weights or silently
corrected. This component does not claim a common-condition counterfactual.

Particularly, nmol/min/mg protein and nmol/min/mg lipid have compatible-looking
physical dimensions but different biological denominators. A protein-free
liposome has no automatic positive BtsT/protein mass denominator. Subtraction
requires an actual common source basis, such as matched assay volume/lipid or
an explicitly defined positive paired-reference protein input. A measured basis
conversion must be separate identified data with its uncertainty; no such
conversion is inferred from a nominal mixing ratio. Normalization=None leaves
the comparison unknown, not perfect and not zero. True molecule turnover or
active incorporated amount is outside this component unless measured separately.

A reused control is never a new independent measurement. When a source explicitly
uses one reference under a stated invariance assumption, preserve that assumption
and its shared owner; identical rows/columns in C cause the correct cancellation.
The measured condition of that shared control stays its actual source condition,
even when applied to a second target condition. A target-role assignment does not
rewrite the measured condition. Exact per-cell application/reuse rules below
distinguish that case from unknown condition matching. Raw values survive both.

## Covariance/model source interface

`covariance_status` is known|estimated|unknown with witnesses in model_witnesses.
`model_kind` is none|known_joint_normal_source_means. Neither is inferred from
an error-bar label or count.

The finite structured source representation is controlled_response_covariance_v1:

    version
    primitive_order: exact four roles
    physical_observation_keys: exact four resolved physical owners
    primitive_units: actual per-operand units
    covariance: full4x4 actual source matrix
    origin: reported|derived|synthetic

This source is an actually received acquired analysis/data artifact, not a model
constructing a new numeric JSON dataset to bypass source reading. Parse duplicate
keys, nonfinite numbers and lexical underflow explicitly. Convert covariance
with both actual unit multipliers once, Ccanonical=D Cnative Dᵀ. Check symmetry
and PSD, including legitimate singular/shared-variable matrices; do not repair
or jitter. All principal minors can be checked exactly for4×4 Fraction matrices.
If owners alias, their known values and covariance rows/columns must agree.
Malformed selected JSON/shape, forged spans and unauthorized sources are
repairable request failures; the selected operation rejects those arguments.
An authenticated covariance artifact can itself contain duplicate JSON fields,
nonfinite/underflow data, wrong owners, asymmetry, non-PSD values or conflicting
alias rows. Those are actual invalid source data: keep the original artifact,
preserve valid raw responses/valid effects, mark the covariance failure
with finite codes and publish no covariance-derived model number. Never repair
the matrix or invent another model. Unsupported authentic source formats are
capability partials, not authorization failures.

Unresolved owner correspondence is distinct from an actually wrong owner: retain
the source matrix but leave its scientific operand binding unknown. Finite
covariance diagnostic codes are duplicate_json_key, nonfinite_number,
lexical_underflow, wrong_owner, asymmetric, not_psd, inconsistent_alias,
unresolved_owner and unsupported_representation, with actual source references.
They describe the data/interface failure, never an experiment quality number.

No covariance source gives unknown covariance, not independence. An actual but
unsupported source representation gives unsupported_covariance_representation
and explicit model_reader_capability=structured_covariance_only. That is missing
implementation, not a claim that the paper omitted covariance. PDF/prose-table,
estimated finite-sample, clustered and censored likelihood model reading remains
unimplemented until its own exact source contract is supplied. The source matrix
is preserved separately from reported SD/SEM/CI/reading intervals.

## Pure calculator and detached extraction

Proposed entry points:

    controlled_response_arguments_schema()
    read_controlled_response_inputs(arguments,read_source=...)
    populate_controlled_response(inputs)
    validate_saved_controlled_response(selection,extraction,calculation)

Extraction version: controlled_response_source_extraction_v1. It retains the
complete selection, source roster/hashes, actual authenticated witnesses,
per-arm native/canonical numbers, graph recipes/results, uncertainty partials,
canonical meanings, physical owners, relationship statuses, resolved covariance,
capability limits and implementation dependencies. No source data is rewritten
as a synthetic table. Definitions and diagnostics are supporting records,
separate from the numerical cells.

Calculator input version controlled_response_inputs_v1 has exactly:

    version, arms, relationships, covariance, variance_status, model_kind

Each nullable arm has exactly value,threshold,relation,approximate,unit,status,
endpoint_id,normalization_id,subject_construct_id,condition_id,
physical_observation_id,source_observation_id,origin,digitization_interval,
protein_arrangement,meaning_statuses.
status is point|bound|missing|ambiguous|conflicting|unsupported. A point has a
finite value and null threshold; a bound has null value and finite threshold;
other statuses have null value/threshold and retain candidates in extraction.
unit is a RATE_UNITS key or null; value/threshold are expressed in that actual
unit, and a null unit prevents a canonical numeric cell or derived contrast.
An authenticated native number with unsupported/unknown unit stays in extraction
and can appear only as matching-role raw supporting detail. The calculator does
not publish it as a dimensionless value. relation is eq for ordinary points,
lt/le/gt/ge for bounds, interval for graph points with reading bounds, and none
for other statuses. approximate is Boolean. origin is reported|graph_derived|
synthetic. digitization_interval is null or exactly {lower,upper}, finite and
containing the nominal value; it is permitted only for graph-derived points.
source_observation_id is nonempty for an authenticated observed primitive and
null for an actually missing one. Unknown meaning IDs are null.
meaning_statuses has exactly endpoint,normalization,subject_construct,condition,
physical_observation, each known|unknown|conflicting; an ID is nonnull iff its
resolved meaning status is known. Source-meaning or canonical-correspondence
conflict resolves to conflicting; unresolved correspondence resolves to unknown.
source_observation_id identifies the literal/recipe,
physical_observation_id the underlying observation. The calculator accepts
parsed values because it is a pure arithmetic boundary; the selected operation
cannot accept that parsed object as its request.

Pure relationships have exactly the nine selected relationship field names.
The target records resolve to {status,canonical_id}; categorical records resolve
to their finite value strings; intended_factor resolves to null or its actual
source witness ID. The complete witnessed records stay in extraction. Each arm's
protein_arrangement is copied from the witnessed selected field.

Pure covariance is null or exactly {primitive_order,physical_observation_ids,
units,matrix}. primitive_order is the fixed four-role list; the four owner IDs
must equal those actual resolved arm owners in that order. Each covariance unit
is a RATE_UNITS key with the corresponding operand's physical dimension; matrix
is the full finite symmetric PSD4x4 covariance in those source units. Both
response operands and covariance are converted independently into their common
canonical base once, using their own actual units. No covariance matrix is
constructed by squaring individually converted SDs. variance_status is exactly
known|estimated|unknown; unknown requires null covariance, while known/estimated
require the validated source matrix. model_kind is none|
known_joint_normal_source_means. Known-normal with missing/estimated covariance
produces no S/B; it does not authorize a replacement covariance/model.

The pure calculator raises ExperimentalContractError for malformed direct input
contracts (bad shape/enums, nonfinite operands, malformed covariance shape or
invalid covariance association). It has no source bytes to retain. The targeted
reader validates covariance independently and records an authentic invalid-source
failure; it then passes covariance=null, variance_status=unknown and model_kind=
none to the pure calculator, and retains the requested original model/status
and finite covariance diagnostic in extraction. Native typed model rows carry
that diagnostic next to the unchanged null pure-calculation cell; the wrapper
does not mutate the pure calculation or compose a second scientific result.
It does not erase valid d1/d0/e. A directly selected unknown/estimated model is
preserved as such; this invalid-source adaptation is not fabricated independence
or an alternative sampling model. Authorization and malformed selected-argument
errors propagate; they are never caught by this covariance-partial adaptation.

Output controlled_response_sheet_v1 preserves inputs and a fixed cells mapping:

    protein_condition1_response, empty_condition1_response,
    protein_condition0_response, empty_condition0_response,
    condition1_controlled_response, condition0_controlled_response,
    controlled_response_difference, contrast_variance,
    contrast_standard_uncertainty, contrast_precision,
    source_profile_log_ratio, source_signed_index

Each cell has value,lower,upper,relation,approximate,unit,status,origin,
unavailable_reason,formula_code,conditional_on,bound_kind. Values/bounds stay
nullable, and relation distinguishes eq/lt/le/gt/ge/interval/none. Printed-limit
arithmetic and conditional digitization bounds have different bound_kind values;
neither is a confidence interval. An exact zero noisy response or effect remains
zero; a source nondetection does not become zero. Negative noisy rates remain
signed. This component takes differences, never logs of rates or pseudocounts.

formula_code is fixed by cell: source_response for the four raw cells,
condition_control_difference for d1/d0, four_arm_condition_difference for e,
linear_joint_covariance for V, square_root_variance, inverse_variance,
signed_known_normal_profile, and tanh_half_signed_profile. origin is reported|
graph_derived|synthetic|calculated; a derived result involving any synthetic
operand remains synthetic, otherwise a graph operand gives graph_derived,
otherwise the derived result is calculated. The preserved input roster retains
each individual origin. Synthetic cannot silently become reported science.
bound_kind is none|reported_limit|conditional_digitization|mixed. Numerical
unit is the canonical unit, its declared square/inverse square, dimensionless
for S/B, or null when unknown. unavailable_reason is null or a nonempty unique
list of the finite reason codes below (stable lexical order is serialization,
not a priority ranking). conditional_on is a unique list of finite qualification
codes: shared_reference_assumption, unknown_control_reuse,
nonintended_conditions_different, nonintended_conditions_unknown,
nonintended_conditions_conflicting, approximate_source_reading,
conditional_digitization, estimated_covariance, known_normal_source_means and
synthetic_fixture. Actual witnesses and covariance-source diagnostics are
separate supporting records, not unrestricted prose in those fields.

For printed one-sided limits, fixed-sign linear interval arithmetic can produce
a conditional reported-limit contrast when informative. Opposing unbounded
limits give no finite effect bound. Missing arms are not zero and give no
finite point. Digitization intervals propagate by the same signed linear map,
preserving shared alias constraints rather than treating duplicate endpoints
as independent choices. Mixed bound meanings remain explicitly qualified and
do not create a sampling interval. Censored/ambiguous operands never supply
a point S; no density is evaluated at a reporting threshold.

Use exact rational sums for linear effects/variances and reject nonfinite or
nonzero-to-zero final conversions per cell. Zero known contrast variance is
retained as zero, but precision/S/B require positive variance. Unknown/estimated
variance and unknown/no normal model leave the relevant model cells null with
their own reasons. A contradictory normal model input is not silently changed
to an assumed independent model.

## Native persistence, typed return and reconstruction

Prospective selected operation: literature.controlled.response.populate.
Prospective typed namespace: literature_controlled_response_cells.
Assignment selection: requested_controlled_response_components. No new role,
episode, router, private loop or mandatory ordering is introduced.

The repository must authenticate received sources/scope/page ancestry before
any bytes, including covariance, images, original images and text witnesses.
Preauthorize callbacks so authorization errors propagate rather than turning
into local missing science. Authorized read/decode failures are per dependency.
Save original request/extraction/calculation/bindings/dependencies/outcome in one
transaction with exact selected-operation owner and content identities.

Each typed row carries the requested numeric cell, actual units, finite reasons,
bound semantics, per-arm subject/endpoint/normalization/condition references,
role states and the declared experimental relationships. Host hashes, arbitrary
diagnostics and unrestricted scientific prose do not cross as interpretation
fields. Model-reader limitations remain finite explicit capability fields.

Only a requested matching raw-response row may expand that role's native value,
candidate values, spread, count and CI pieces. Derived-only returns contain only
their selected derived numbers; hidden raw-role expansion is not authorized.
Full saved records remain available for explicitly selected later source work.
Text references retain actual full UTF8 anchors, with bounded marked display
previews when necessary. Image references retain real source/artifact/region
identity and interpretation attribution, without fabricated text byte anchors.

Reuse base044 fact_cells/validate_fact_values/receive_cells/received_cells and
the actual original runtime-form authentication unchanged. An owner can report
its selected cells; a parent/forwarding child can report only its exact admitted
subset. The source sheet is not recomputed or fully delivered just because the
receiver holds a reference. Renderer masks numeric-token labels and broad
overlapping text/image witnesses, including off-page token locations; unrelated
labels remain available. No model call composes a second report.

Saved validation checks structural/semantic associations, exact original request,
source/physical owners, immutable operation/outcome and selected/admitted rows.
Reconstruction uses saved artifacts only, not source acquisition, text parsing,
image decoding, scientific arithmetic or model reinterpretation. New records
and observations cannot be created by receive replay or reopening.

## Prospective ownership and implementation sequence

Nothing below is released by this proposal. Root must establish interfaces and
exclusive ownership before implementation. Prefer new separately owned files:

- literature_controlled_response_calculations.py and its dedicated tests.
- literature_controlled_response_inputs.py and its dedicated source tests.
- literature_controlled_response_validation.py and detached-contract tests.
- literature_controlled_response_storage.py and native/C4/reconstruction tests.
- Optionally a small controlled-response render module to minimize shared edits.

The first production release, if authorized, is pure calculator only. Graph
source input remains prospective outside that release and required for the full
targeted-reader deliverable. The graph branch requires either a reviewed, separately versioned rate-unit
extension of the native figure helper or a new rate-figure wrapper over a shared
pixel core. Extend supported units explicitly; preserve old behavior/tests.
Root must assign that bounded existing-file change separately; this worker owns
none of the figure modules. Figure storage/input v1 are not claimed to support
rate ordinates by the current probe or this proposal.

Only after those stages and explicit shared-file transfer: append the actual
operation/schema/fingerprint/dispatch/page-source checks, typed fact/receive
route and assignment selection in literature_episodes.py; add the lazy service
accessor; add mechanical return display/masking.052 currently owns those shared
files, and055 owns the kinetic modules/count tests. Both scopes remain untouched.
No existing rate, activity, assay, transport, domain/Store, base044, controller,
runtime, scientific TASK or final-credit file is proposed for a broad refactor.

The pure/calculator stage is not completion of this workload. Targeted source
reading, graph support, selected execution, typed delivery, saved reopening and
a root-owned primary-source example are required for the intended deliverable.

## Meaningful verification required after release

Verify complete signed four-arm arithmetic, one-sided-limit direction, missing
arms, partial failures, unknown/incompatible endpoint/normalization and distinct
biological denominators despite equal unit spelling. Verify legitimate shared
owners/common-offset cancellation and conflict rejection; no sample-size-derived
independence. Confirm existing two-arm/code behavior remains intact.

Verify source UTF8/Unicode selectors, qualifier/clipping/defined-unit guards,
actual image/crop mapping and source-parsed tick calibration; no model-authored
ordinate. Exercise ambiguous ticks/units, wrong crop pixels, incomplete bar edge,
local source failures and exact graph/printed-limit versus sampling semantics.

Validate structured covariance ownership, both-unit conversion, unknown/estimated
status, PSD/singular cases, duplicate JSON fields/underflow, unsupported model
formats and exact source-reporting qualifiers. A source model must be supported
before S/B, not selected because it yields a high number.

Run actual selected LiteratureEpisodes work with ordinary typed child return,
matching-row-only expansion, original owner versus admitted subsets and actual
C4 admission. Count only actual completed actions; internal parsing, arithmetic,
publication and reporting add no observations/credit. Use actual SQLite mode=ro
before the first reconstructed repository read, forbidding original source
artifacts, reader/calculator, image decoder, new receipt and repricing. Assert
the exact original sheets/parent facts and whole SQL remain unchanged.

Tampered selections, identity associations, covariance owners, bindings, saved
results, unrequested raw values and original typed receipts must fail the actual
custody/selection/ownership boundaries. A detached schema check alone does not
prove that path. Tests and fixture counts are not experimental graders or proof
of configured-model scientific extraction.

## Inspection and limits

Fully read for this code-only proposal: active attachment; root AGENTS/GOAL;
EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION and TASK_AND_STEERING; W04 amendment;
research AGENTS; all14 source modules in BASELINE_001 (rate calculation/reader/
native inputs/storage, activity calculation, assay inputs/storage, experimental
contracts, transport calculation/inputs/storage, complete C7, complete renderer
and WorkflowServices). Also fully read native figure measurement/input and the
frozen049 visual module. Latest039 and both040 direction records were read last.
One initial C7 display truncated; its complete1–205 range was reread in two
bounded portions before proceeding. No truncated read is claimed complete.

Figure storage was inspected only through bounded symbol/constant discovery,
not fully read or behaviorally audited. Generic runtime/C4/Store modules were
not newly read in full; this proposal reuses the fully inspected base044/C7
contracts and requires implementation-time complete changed-consumer review.
No paper/post-paper reset, network search, scientific model, live database,
provider history, old pin, external message or production test is claimed.

The proposal has no complete A105/goal or target-credit claim. Unknown scientific
inputs and unimplemented required functions remain distinct unfinished work.

## Review clarifications: exact boundaries and finite judgments

The proposed v1 arithmetic unit registry is the existing closed RATE_UNITS
registry: umol/min, nmol/min, mmol/min, uM/min, nM/min, per_min, per_s,
umol/min/mg and nmol/min/mg, including only its authenticated source-unit
aliases/definitions. Canonical response units are umol/min, uM/min, per_min and
umol/min/mg, respectively. The covariance conversion uses each operand's actual
multiplier; canonical variance unit is the square of that canonical response
unit, precision the inverse square, and S/B dimensionless. Compatible dimensions
never substitute for a common biological denominator. Unknown biological basis
permits an authenticated raw response, not a cross-arm comparison.

The worked table is a native-unit display. The saved/public calculated cells
use canonical units whenever conversion is known, with the original source
value/unit retained separately in extraction and disclosed only for the selected
matching raw role. An unknown/unsupported unit preserves the parsed native
number as a raw-response partial with null canonical value. Such a native number
must be labeled by its actual source-unit witness; it cannot appear as a
dimensionless canonical number. No derived cell uses an unknown-unit operand.

Partial computations use their actual dependency subsets. The following are
the exact applicability rules; a pair's own conditions do not inspect the other
pair. Unknown and different are distinct finite failure states, not penalties.

For pair j, consisting only of protein_conditionj and empty_conditionj:

1. Both selected arm observations must exist. The protein arm's arrangement is
   protein_present; the control arm's arrangement is protein_free_control or
   empty_vector_control. Unknown/conflicting arrangements preserve the raw arms
   and make that pair unavailable/conflicting. Other_specified does not
   silently establish an empty-control role.
2. Both endpoint IDs must be nonnull and equal; both normalization IDs must be
   nonnull and equal; known units must have the same physical dimension.
3. conditionj_target is known with a nonnull canonical condition ID. The protein
   arm's actual condition ID must equal that target ID.
4. With matched_condition_control, the control's actual condition ID must also
   equal the target ID. With shared_reference_assumption, the control's actual
   condition ID must be nonnull, and authenticated application witnesses must
   explicitly support using that reference for this target under the source's
   stated invariance assumption. Its actual measured condition need not equal
   the target and must not be rewritten to equal it. Unknown/conflicting
   application gives an unavailable/conflicting pair. The same-named condition
   does not pass either path without the explicit canonical correspondence.

The pair does not require cross-condition construct correspondence, a physical
control-reuse answer, covariance, a normal model, the intended-factor witness,
or any condition0 information when j=1 (and vice versa). If these local rules
hold, the pair is applicable even when a source response is a printed bound;
point/bound determination is separate below.

For cross-condition effect e:

1. Both pairs must be locally applicable. Their protein/control endpoint IDs
   must all be equal, and their normalization IDs all equal, with a common
   canonical physical unit dimension. A different normalization between two
   valid pairs does not erase either pair, but makes e unavailable.
2. Both protein subject_construct IDs must be nonnull and equal, and the
   witnessed subject_construct_across_conditions value must be same. Different,
   unknown or conflicting leaves the respective pair results intact and makes
   e unavailable/conflicting. This is identity/comparability, not a penalty.
3. Both target conditions are known, their canonical IDs are distinct, and
   condition_levels_relation is explicitly different; intended_factor is
   witnessed. The source interpretations identify the
   actual tested condition change. Equal/unknown/conflicting target meanings
   do not establish this two-condition contrast. Nonintended_conditions may
   be matched, different, unknown or conflicting: all remain explicit
   qualifications of the observed protocol contrast and do not rescale e.
4. Reuse is handled according to the exact rules below, without a requirement
   that the four arms be independent or four distinct physical observations.

Control-reuse truth rules for e:

- same_reference_with_stated_invariance requires known equal physical control
  owner IDs, consistent shared response/condition/endpoint/normalization data,
  and the stated source invariance witnesses. At least the application to a
  different target must be shared_reference_assumption. A reference directly
  measured in condition1 may be matched there and explicitly shared in
  condition0. That is one physical measurement used twice.
- distinct_observations requires known different control owner IDs and a
  witnessed distinct-observation interpretation. Different numbers, source
  locations or owner-key spelling alone never establish this interpretation.
- unknown preserves e as a conditional observed contrast if both local control
  applications above are established and there is no contradictory identity
  assertion. It adds unknown_control_reuse as a qualification, permits no
  duplicate counting or alias cancellation, and never creates independence.
  If equal known owner IDs already establish reuse, unknown does not authorize
  applying that actual observation to an unmatched condition: the explicit
  invariance/application requirement still applies.
- conflicting, or equal declared owners with incompatible values/condition
  meanings, makes e conflicting; independently valid local pair records stay
  retained with their own local source qualification. A covariance artifact
  that contradicts otherwise consistent owners is instead a covariance failure
  and does not erase an otherwise valid e.

Unknown physical identity/reuse does not by itself turn a reported magnitude
into missing evidence. V additionally requires a source model bound to the
exact four actual operand owners and their full joint covariance. Where those
associations cannot be established, V stays unavailable even if e is useful.
An explicitly source-bound full covariance can describe dependence without an
independence assertion; an unknown reuse label is not replaced by independence.

For V, standard uncertainty and precision, the effect must be applicable and
have an available point; the exact source-bound full covariance must be valid.
Known V=0 is retained as zero and standard uncertainty zero. Precision requires
V>0. Known/estimated status follows the actual matrix source. S/B additionally
require known positive V, the supported known-normal source-mean model and
uncensored, unambiguous, nonapproximate point operands. v1 does not supply a
sampling model for digitization error, so graph operands do not establish S/B
through the known-normal flag alone. The deliberately changed condition never
enters a denominator or quality coefficient.

Exact value/lower/upper behavior:

- With a known unit, an authenticated equality response has canonical value=x
  and lower=upper=null; an
  approximate equality additionally sets approximate=true. A printed limit
  has value=null and the appropriate lower or upper threshold, preserving
  strictness in relation (lt/le/gt/ge) and bound_kind=reported_limit. A missing,
  unreadable or conflicting response has no invented value or bounds; valid
  source candidates remain supporting extraction, not a chosen cell value.
  Unknown-unit native numbers remain partial supporting detail, with no
  canonical value/threshold/bounds substituted into the numerical cell.
- A supported graph point has its measured nominal value and conditional
  digitization lower/upper, with bound_kind=conditional_digitization and
  relation=interval. These are reading bounds, never a sampling CI.
- If all required operands are equality points, an applicable pair/e has the
  signed linear point value. With graph nominal values it also carries signed
  interval-propagated reading bounds. If any uncancelled required operand is
  censored, it has no point value: use the signed Minkowski sum of its actual
  reported ranges. Preserve strictness, set one-sided or interval relation,
  and use null for an infinite/uninformative side. Fully unbounded gives
  value=lower=upper=null and unavailable status, not zero.
- First reconcile an explicitly established physical alias with exact shared
  scalar/limit values and combine its signed coefficients. This can cancel a
  genuinely reused variable in e. It does not make d1/d0 separate observations.
  If a required role is actually absent, no alias inference fills it and no
  cross-condition point is fabricated. Ambiguous/conflicting source candidates
  are not resolved by choosing the one that makes cancellation work.
- Failed correspondence/role/application gives value=lower=upper=null for
  that derived cell, with its finite reasons. It never changes a valid raw arm
  or the other local pair. A valid e with unusable covariance keeps its value
  and bounds; only variance/model cells are null with their own reasons.
- Model/variance cells are point values without lower/upper. Estimated variance
  is explicitly conditional on an estimated covariance; no CI is manufactured.
  No S/B is evaluated at a censor threshold or from graph-reading spread.

The arithmetic is direct in the original four operands, with joint alias
constraints. Computing independent intervals for d1 and d0 and then subtracting
them can lose actual cancellation and is not the defined joint algorithm.

Cell statuses are available (point), bounded (informative bound without point),
partial (authenticated native number without a canonical number), unavailable
(missing necessary input), conflicting (incompatible asserted inputs), and
unsupported (required reader/model capability absent). Reasons are finite
machine-readable codes, with source witnesses separate. Initial reason codes
are missing_arm, unknown_unit, incompatible_unit_dimension, unknown_endpoint,
different_endpoint, unknown_normalization, different_normalization,
unknown_subject_correspondence, different_subject_correspondence,
unknown_control_application, conflicting_control_application,
unknown_protein_arrangement, conflicting_protein_arrangement,
incompatible_control_arrangement, unknown_condition_correspondence,
different_condition_correspondence, conflicting_condition_correspondence,
condition_levels_not_distinct, missing_intended_factor,
unknown_control_reuse, conflicting_control_reuse,
unsupported_source_expression, ambiguous_source_literal,
conflicting_source_literal, unavailable_source_dependency,
unsupported_graph_unit, unsupported_graph_geometry,
ambiguous_axis_calibration, unknown_covariance, estimated_covariance,
unsupported_covariance_representation, covariance_owner_conflict,
covariance_owner_unresolved,
invalid_covariance, nonpositive_variance_for_model,
observation_model_unselected, unsupported_observation_model,
unresolved_censoring_model, unresolved_reading_model and numeric_range_failure.
Malformed selection/authentication errors remain rejected requests rather than
scientific-unavailable cells. Report all relevant dependency reasons; do not
invent a total ordering that hides a second independent failure.

The following are necessary finite reader judgments, not proposed scientific
TASK/prompt text and not quality grades:

1. Which authenticated source observation belongs to each of the four declared
   protein/control and condition roles? Is any role missing, conflicting or
   genuinely the same physical observation reused?
2. What actual endpoint and normalization definition do those observations
   measure? Are the required endpoint/denominator meanings the same, different,
   unknown or conflicting? For empty controls, what common reference amount is
   actually used?
3. Is the control directly measured for this condition, explicitly reused under
   a stated invariance assumption, unknown or conflicting? What is the witnessed
   protein/construct correspondence between conditions?
4. Which intended factor changed, and what other recorded conditions changed or
   remain unknown? These answers qualify the actual comparison without a weight.
5. Does a numeric source expression represent a response, a bound, a graph
   calibration tick, spread or count? Is its interpretation exact, ambiguous,
   unreadable or conflicting? The reader nominates the expression; deterministic
   parsing supplies its numeric value and unit.
6. What is the reported uncertainty statistic/repetition basis, and which actual
   source observations does it describe? Does an acquired model source support
   the full joint dependence and a known-normal model, or is that model missing
   or unsupported by the implemented reader?

These judgments do not ask the reader to supply a calculated e, a covariance
entry invented from error bars, a quality coefficient, function credit or an
annotation-transfer score. A future selected reader must produce actual source
witnesses and preserve unresolved judgments rather than requiring a complete
positive answer before it can return useful partial evidence.
