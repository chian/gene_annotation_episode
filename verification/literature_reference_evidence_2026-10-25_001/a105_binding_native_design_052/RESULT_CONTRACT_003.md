# Implemented052 source-input contract and next projection boundary

First-stage reader only. The new799-line reader and542-line synthetic test file
are stable. No storage, native catalog entry, service, renderer, typed-return
namespace or scientific TASK was added. The larger integration workload remains
unfinished. This contract supersedes the prospective reader shapes in001 where
they differ;001 and002 remain unchanged design/history records.

Entry points:

    binding_interaction_arguments_schema()
    read_binding_interaction_inputs(arguments, read_source=...)

INPUT_SCHEMA_003.json is the actual generated closed request schema. The module
docstring and manual relationship validation supply the further constraints.
All request keys are required. Roles use the four full names exported as ROLES,
not the shorthand rr/rt/tr/tt used in the discussion. Unknown role/measurement,
unit, whole uncertainty or individual uncertainty selections are explicit nulls.

The actual interval request is {lower,upper,unit_relationship,unit}, with lower
and upper independently null or a full exact/ambiguous/unreadable/conflicting
Literal. This replaces001's whole-interval literal and permits independent source
endpoint missingness. Confidence level and exact/minimum counts are separately
nullable Literals. No numeric operand, quality grade or covariance is supplied
as a direct number. The source callback returns actual bytes/artifact identity.

## Frozen dependencies and scientific ownership

The reader pins actual053 calculator ac7ea12c105e16df5085942090ec8e3f96c618b4f5866283325c46c92804b432,
frozen049 visual mechanics8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718,
the existing literal parser e117105486773280edf1dba796ab2be10c61feb6a9c0ad407ba876e2332714a1
and experimental contracts0d7d4cb57f63c66ae36912e369fbcea557a6b9646c727ed1c60eac229ca3bccc.
It records its own actual source hash and Pillow version. A missing or changed
dependency is an implementation error before any scientific source read; it
does not return a scientific unknown instead.053's nullable uncertainty pieces
are actually exercised by the new reader checks, not only planned.

The investigating episode owns source transcriptions, scientific meanings,
canonical correspondences and actual physical-fit attribution. Text witnesses
authenticate exact UTF-8 byte spans; image witnesses authenticate supplied bytes,
actual format/dimensions and checked crop geometry. Neither proves the nominated
text or scientific interpretation. No model, OCR or source acquisition occurs.

All selected source/representation references are passed to the caller callback
once before parsing. domain.ContractError propagates as an action/authorization
failure. Other authorized read/decode failures remain local dependency failures.
The eventual repository must authorize receipt, scope and assigned-page/original
ancestry before exposing bytes; the pure reader has no Store authority.

## Exact result tree

Every object below has exactly its listed keys. Nullable means explicit null.
Raw strings/diagnostics belong to the retained extraction, not an unrestricted
parent report. Actual scientific typed projection is still future work.

Top-level result:

    version: binding_interaction_source_extraction_v1
    source_ref, source_kind
    selection: complete detached request
    parameter_kind: EnumResult
    images: [ImageResult049]
    roles: {role: RoleResult for role in ROLES}
    relationships: {name: EnumResult for name in048.RELATIONS}
    geometry_overlaps: [{left_role,right_role}]
    calculation_input_status: declared finite code
    calculation_inputs: null | corrected048 closed input
    source_refs: distinct selected source refs in stable acquisition order
    source_representations: [SourceResult]
    implementation_dependencies: {sha256,reader_sha256,pillow_version}
    interpretation_attribution: investigating_episode_interpretation

SourceResult={source_ref,representation,artifact_ref,sha256,error}. Actual source
metadata/hashes are recorded; a failed dependency keeps null measured facts.
Error is null or {code,field}; exception messages/private diagnostics are omitted.
ImageResult049 retains its unchanged fixed image/source/original hash, format,
mode, dimensions, frame count, explicit crop mapping, Pillow version and error.

EnumResult={value,witnesses,status,interpretation_attribution}; status is
interpreted or source_unavailable. Conflicting interpretation requires distinct
actual authenticated witness locations. Duplicating one witness is a repairable
argument error, not a second contradictory source or a fabricated read failure.

WitnessResult={witness,artifact_ref,canonical_locator,authentication,
interpretation_attribution,error}. authentication is exact_utf8_byte_span,
image_bytes_and_geometry_only or null. Image canonical_locator is exactly
{original_source_ref,original_artifact_ref,image_region}; text uses its actual
source/artifact plus exact byte span for calculator witnesses.

LiteralResult={status,declared_status,candidates,fragments,
interpretation_attribution}. Candidates/fragments are WitnessResult arrays;
status retains the nomination state, or source_unavailable, or not_selected.
No ambiguous candidate is selected or averaged.

RoleResult:

    selection_status: selected|not_selected
    parameter_kind: null|EnumResult
    definitions: null|{field:MeaningResult for field in ID_FIELDS}
    physical_fit: PhysicalResult
    measurement: MeasurementResult
    uncertainty: UncertaintyResult
    calculation_operand: null|corrected048 operand
    unavailable_reasons: declared finite codes

MeaningResult={status,label,witnesses,canonical_witness,canonical_id,
interpretation_attribution}. status is known/unknown/conflicting/source_unavailable.
Known canonical IDs derive from the meaning dimension and an authenticated
canonical witness locator. Own actual witnesses survive alias mapping. Equal
labels do not establish identity; unknown definitions retain null canonical IDs.

PhysicalResult={status,canonical_witness,witnesses,physical_fit_id,
interpretation_attribution}. status is known/unknown/source_unavailable. The ID
requires a separately selected source physical identity. It is never populated
from the source-cell key, row order, construct, preparation or equal number.

MeasurementResult={parse_status,canonical_locator,source_cell_id,expression,unit,
native_measurement,canonical_measurement,candidate_measurements,error}.
expression/unit are LiteralResult. Native/canonical measurement is null or
{value,relation,reported_spread}; relation preserves eq/lt/le/gt/ge/unreported.
The canonical representation is nM only when an exact supported source unit is
available. Parsing at factor1 describes the native printed number; it does not
assign an unknown unit to nM. Unknown units preserve native values and raw unit
candidates with canonical_measurement=null.

Each candidate measurement has exactly candidate_index,witness,native,canonical,
canonical_unit,error. It is a nominated alternative, never a selected measurement.
Exact n.d. remains reported_unavailable even when its separate unit is unknown;
it is never expanded into not-determined/nondetected or converted into zero.

UncertaintyResult={selection_status,meanings,interval,confidence_level,exact_count,
minimum_count,reported_spread_status,canonical,unavailable_reasons}. meanings is
null or {statistic,basis,repetition_basis:EnumResult}. canonical is null or the
corrected053 dictionary, preserving its actual statistic, independently nullable
CI endpoints/level, SD/SEM magnitude missingness and count meanings.

Whole canonical uncertainty null means unresolved/not supplied, not the source
assertion statistic=unreported. Actual reported spread presence survives that
unknown meaning; native_reported_unit_unavailable is distinct from no spread in
the selected expression. A contradictory descriptor is retained in the sidecar
while the uncertainty projection is null, preserving the valid source parameter.

An interval result has exactly lower,upper,unit_relationship,unit,canonical_values,
canonical_unit,canonical_status. Scalars below supply each endpoint. Explicit
selected endpoint positions survive as a two-element canonical array, even when
both are null. No interval selection is distinct from that explicit array.
Known ordering is checked using exact source decimal tokens before float rounding.
A nonzero printed interval that collapses numerically is retained as a range
failure with unknown canonical endpoints, never an exact zero-width CI.

ScalarResult={literal,status,value,relation,approximate,percent,raw_number,
qualification_origin,error}. Exact source token boundaries and mechanically
observable adjacent text qualifiers are retained, including UTF-8, nested source
markup and encoded comparison signs. No source wording is rewritten. Unknown
word counts/unsupported numeric forms remain explicit unsupported partials.
Qualified count thresholds never become exact counts. A minimum count accepts
only an exact integer or an explicit inclusive lower bound; strict/upper/approximate
bounds remain native qualifiers without inventing an exact/minimum count.
Confidence probabilities retain actual percent conversion and distinguish an
out-of-domain source value from a finite source probability that rounds to an
unusable numerical endpoint. Neither yields a fabricated level0 or1.

The exported MEASUREMENT_STATUSES, SCALAR_STATUSES, UNCERTAINTY_REASONS,
ROLE_UNAVAILABLE_REASONS and CALCULATION_INPUT_STATUSES are the actual finite
vocabularies. Other small status sets are enumerated above or in the unchanged049
image contract. Host source error codes are retained diagnostics; they are not
arbitrary scientific judgments or new report fields.

## Calculation readiness is not scientific completion

calculation_input_status=ready means a validated same-definition048 input can be
supplied, even when some operands/relationships are unavailable. It does not mean
the comparison or its score is populated. The reader never calls the048 calculator.

Unknown/conflicting/unavailable common kind gives calculation_inputs=null and
an explicit common-kind status. No ic50/Hill default is selected. All actual
per-role raw/native/canonical measurements and kinds survive independently.
Known role kinds that disagree with the selected common kind also retain their
actual measurement/kind but are excluded from that common-kind calculation.
Unknown context IDs still permit a genuine raw048 operand; only affected derived
contrasts are withheld. The unaffected within-form pair remains useful.

The four-role source-cell check detects actual original-cell reuse/conflicts
across all selections and crop wrappers. A conflicting or ambiguous rereading
cannot be discarded in favor of an exact copy. All candidates survive. Overlap
alone neither merges cells nor establishes independence. Physical-fit identity
remains separate; a shared control retains both identities across later calls.

## Required next-stage eight-row projection boundary

This section specifies prospective storage/typed-return behavior for root's
handoff; it is not implemented by the first-stage reader.

The public component vocabulary is exactly parameter_rr,parameter_rt,
parameter_tr,parameter_tt,reference_subject_ratio,test_subject_ratio,
interaction_ratio,log_interaction. It contains dependent native representations
within A105. The model/covariance reader and four model-dependent source returns
remain unimplemented required work, stated explicitly as implementation status.

Raw parameter rows must be projected from the retained RoleResult, including
when calculation_inputs=null or the role was excluded from the common kind.
Using only048's raw cells would incorrectly erase those useful source results.
Derived rows may use only the authenticated actual048 calculation when ready.

| Condition | Matching requested raw parameter row | Derived rows |
| --- | --- | --- |
| Common kind unknown/conflicting | Actual per-role kind, canonical nM point/threshold where supported, native number and source qualifications survive; common kind stays unknown/conflicting | Null with actual common-kind reason; no invented ic50/Hill or substitute calculation |
| Role kind disagrees with common kind | Actual role kind and its genuine numerical result survive; comparison-ineligible status remains explicit | Affected comparison remains unavailable; unaffected common-kind pair may survive |
| Unit unknown/unsupported | Canonical value/unit unavailable, while actual native value, raw unit witnesses and candidates remain available | No factor1 nM operand or invented conversion |
| State/construct/context unknown | Raw point/threshold survives with null canonical identity and specific field status | Only contrasts requiring that unknown correspondence are withheld |
| Partial CI/SD meaning/magnitude | Actual known statistic/endpoints/level/count pieces remain, independently unknown pieces stay null | Native arithmetic may survive; no uncertainty-derived covariance or likelihood |
| Ambiguous/conflicting/unreadable source cell | No chosen point; explicitly nominated parsed alternatives/fragments and exact source state survive | No averaging, replacement with n.d., or statistic from a threshold/candidate |

Each requested row can retain four-role metadata/statuses and actual witness
references. Numerical role expansion is allowed ONLY on the matching explicitly
requested parameter row. For example, parameter_rr may supply rr's native/
canonical/candidate numbers, spread, CI endpoints/level and counts; it must not
expand rt/tr/tt numbers. A request containing only interaction_ratio/log_interaction
gets those actual selected derived numbers, with all raw role/uncertainty/count/
candidate values null and delivery_status=not_requested. Source meanings and
missingness remain visible. Raw witness references preserve custody without
automatically exposing their unrequested numeric labels.

Source-cell/candidate/uncertainty identities and overlapping broad text/image
witnesses must be masked from automatic generic expansion. Missing location
fallback stays restricted to the actual affected source. Explicit later source
access remains possible; the child's full saved sheet is not silently delivered
because a parent holds a sheet reference. Actual typed rows must be validated
against the reporting episode's selected or exact admitted subset through the
unchanged044 machinery, then admitted to the distinct parent through ordinary C4.

The next repository must retain the full request/extraction/calculation and
source binding snapshots transactionally, authenticate original artifacts and
operation, and reconstruct without calling this reader, decoding images,
reacquiring scientific sources, invoking048, inferring uncertainty or calling a
model. No extra controller observation belongs to internal parsing/calculation,
publishing, form construction or reopening. None of that integration is claimed
by the first-stage synthetic reader evidence.

## Actual populated synthetic examples

EXAMPLE_003_*.json retain complete actual reader results and separately labeled
pure calculator demonstrations; EXAMPLE_PROJECTIONS_003.json is their concise
projection. EXAMPLE_RECEIPT_003.json records seven actual reader calls and six
pure calculator calls, unchanged protected code hashes and no runtime/model/
scientific-source execution. These are not primary-source examples.

| Example | Retained raw information | Actual derived result |
| --- | --- | --- |
| complete |5,40,2,4nM, exact source locations and interpreted mappings | Ratios8 and2; D4; logD ln4; model score null |
| partial_uncertainty | Whole rr uncertainty unresolved; rt explicitly SD with missing magnitude | D4 survives; source uncertainty states stay distinct |
| partial_ci | rr CI lower4.1nM known; upper/level unknown; statistic remains CI | D4 survives; no inferred model |
| unknown_context | rr/rt state truly unknown, without invented witness/ID | Their points survive; reference ratio/D unavailable; test ratio2 survives |
| ambiguous_rt | rt alternatives40 and46 retained, no selected rt point | Test ratio2 survives; D unavailable |
| unknown_unit | rr native5 retained, canonical nM unavailable | Test ratio2 survives; D unavailable |
| unknown_common_kind | All four actual per-role values/kinds survive | No fabricated048 input or derived result |

## Terminal checks and limits

Actual final command:

    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -p no:cacheprovider -q tests/test_literature_binding_interaction_inputs.py --tb=short

Actual result:60 passed in2.95s, exit0. These cover the above states, actual source
callback/UTF-8/image crop paths, aliases, known versus unknown identities,
synthetic measurement origins, supported unit conversion, count/CI qualifiers and
range behavior, propagated caller authorization errors, local source failures, finite codes
and dependency mismatch. The tests use only the newly owned fixture module and
invented source bytes; no older test file or paper packet was imported.

One exploratory test fixture used a number embedded directly in a label
(low0.0041). It correctly returned an incomplete-token partial, so the fixture
was corrected to a complete source token. The source parser was not relaxed.
Earlier overlapping pass counts are not added to the final60.

The published source/test hashes were captured after the terminal run; no source
edits followed. The example export independently verifies its before/after code
hashes. No pre-test hash snapshot is claimed for the terminal test invocation.
This establishes the bounded pure reader and its compatibility with corrected053,
not scientific interpretation truth, primary extraction quality, actual model
selection, selected LiteratureEpisodes execution, typed parent delivery, saved
reopening, complete A105, final annotation credit or the deferred router.
