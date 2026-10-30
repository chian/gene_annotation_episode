# Episode-owned readings of printed relative signals

Design067, not an implementation or an adopted scoring policy. Own outputs are
confined to this new directory. No primary paper/image was opened, no model or
workflow ran, and no production/test file changed. The root's retained YeaG
packet was read, followed by this worker's own complete post-packet reset.
READ_PROVENANCE_001.json records actual complete reads and specific code ranges.

## Decision and missing implementation

Recommend a NEW selected `literature.ratio.source.populate` operation and a
versioned source-reading/sheet contract. It accepts visual-only or mixed
prose/visual source nominations and retains its transcriptions inside the
ordinary immutable output. It invokes a separate deterministic calculator.
It is a representation reader for the existing relative-signal component
meanings, not another experimental scorer or top-level evidence axis.

The alternative is a separately selected transcription-retention operation
followed by existing ratio population. That requires a versioned population
adapter anyway: current v1 always requires a JATS percentage and numeric visual
labels; it cannot consume an unreadable label, a visual-only paper or a printed
limit. A retention tool alone would therefore leave the real gap open. It also
makes two selected actions necessary for a single finite read/calculate task.
A separately selected retention tool can be useful later for deliberate reuse,
but is not a prerequisite or mandatory stage. The recommended operation saves
the full transcriptions as part of its one actual selected contribution.

Neither option supplies OCR, graph/gel classification, band segmentation,
densitometry, calibration or molecular-activity interpretation. Models identify
the actual representation, printed expressions and experimental meanings;
parsers and calculators perform numerical work. Raw band quantification needs
its own case-grounded measurement contract.

## Case conversion after the worker's own reset

The retained YeaG case compares separate tagged WT/variant complementation arms
in Delta-yeaG. Figure3C's anti-His summaries use tagged plasmid WT in the same
displayed blot as denominator. This is replacement, not a coexisting WT/mutant
pool, and principally qualifies A106 recovery-growth comparability. It does not
establish direct A105 activity, calibrated molecular amount or active fraction.
K116A's recovery result is not a Figure6B survival experiment.

The useful extraction fields are the actual variant/reference constructs and
recipient; molecular arrangement; measured signal and endpoint; normalization;
the numerator/reference printed expressions and original image/frame/regions;
their association to this comparison; and whether repeated displays concern
one physical measurement. Blot loading, exposure, linearity, uncertainty,
biological repetition and covariance remain unknown in this retained case.

| Retained factual comparison | Ratio r | r-1 | ln(r) |
|---|---:|---:|---:|
| K116A / tagged WT |0.64|-0.36|-0.4462871026284195|
| R232A / tagged WT |0.48|-0.52|-0.7339691750802004|
| Y382stop / tagged WT |0.96|-0.04|-0.040821994520255166|
| K426A text / image | candidates1.00,1.12 | candidates0,0.12 | candidates0,0.11332868530700327 |

K426A has no scalar. The candidates are source representations, not a sampling
interval. These are inherited root-verified facts, not a new native execution
by067. Root's `view_image` inspection and local content handles are not an
application `image_view` receipt; future actual use must obtain its own proper
native custody. A source-provenance table alone would not be the requested
sheet: the numerical ratio, difference and log ratio above are the components.

These three transforms describe one comparison; do not add them as independent
support. Lower expression is a measured comparability difference outside an
intended sequence substitution, not a universal confidence weight. If calibrated
amounts and a suitable direct-rate model were separately established, replacement
arms can use `per_amount_response_ratio = rate_ratio / amount_ratio`, once.
Synthetic0.20/0.64=0.3125. A separately established coexistence model instead
uses `total_response = WT_fraction*WT_response + variant_fraction*variant_response`.
Synthetic fractions0.60/0.40 and total0.68 with WT response1 give variant0.20.
Neither calculation is licensed for YeaG recovery lag by this blot. W05 final
credit and A101 target correspondence remain outside the design.

## Exact public interfaces and version boundaries

`INTERFACE_001.json` defines every closed object, allowed value and relationship.
It is the normative compact type declaration; all listed fields are required,
nullable unknowns remain explicit, and undeclared fields are rejected.

Proposed NEW pure APIs:

```text
relative_signal_source_arguments_schema() -> SelectionV2Schema
read_relative_signal_source_inputs(selection, *, read_source, read_view)
    -> RelativeSignalExtractionV2
validate_relative_signal_source_selection(selection) -> detached SelectionV2
validate_relative_signal_source_extraction(extraction) -> detached ExtractionV2
populate_relative_signal_v2(extraction) -> RelativeSignalSheetV2
validate_relative_signal_saved(selection, extraction, sheet, saved_outcome)
    -> None
```

Selection version `relative_signal_source_selection_v2`; extraction version
`relative_signal_source_extraction_v2`; retained visual record version
`relative_visual_signal_v2`; sheet version `relative_signal_sheet_v2`.
The sheet keeps exactly the existing seven named component meanings. The new
version adds explicit reading-state, censor-domain and incomplete-roster fields;
it does not reinterpret an existing v1 object.

`read_source(source_ref, representation)` returns exactly artifact_ref and
immutable bytes, after actual caller receipt/scope/ancestry authorization.
`read_view(view_ref)` returns the exact native view metadata, actual display
and original bytes, and its authenticated own-action receipt, as declared in
INTERFACE_001.json. The callbacks are host arguments, never model-selected
paths, bytes, executable functions or artifact assertions.

The native operation is
`LiteratureRatioSourceRepository.populate(context, selection, operation_key)`.
Proposed provider `literature.experimental.relative_signal_source`, saved
version `literature_relative_signal_source_record_v2`, operations table
`literature_ratio_source_operations`, received table
`literature_ratio_source_received`. The closed recorded-fact return is
`literature_ratio_source_cells`, selected through
`requested_ratio_source_components`. Existing v1 operation/provider/projection
and every historical pin remain unchanged. All prior19 operations/18 projections
stay available; the future descriptor explicitly adds one operation and one
return view. This does not change model-package066's frozen accepted010 baseline.

## Source and viewed-image custody

1. Validate the complete closed request, finite coordinates, transcription
   cardinalities and references before source access. Collect all declared text
   and view dependencies, including semantic witnesses, not only readable cells.
2. Resolve every dependency through the actual caller before any helper can
   turn errors into partial data. Permission/authorization/contract/malformed
   callback and unexpected provider/programming errors propagate. Only explicit
   ENOENT and EIO/ETIMEDOUT availability failures become scoped dependency
   partials; no broad `except Exception` substitutes for authorization.
3. A native view must be in this episode's received references and scope, with
   tool origin and exact `selected_native_image_frame_v1` representation.
   Its input source, original artifact, displayed source/artifact, frame,
   native geometry, identity transforms and request metadata must agree.
   Resolve actual bytes with Store.get_artifact, which verifies content hashes;
   do not trust a model-provided artifact/byte pair. Check identical artifact
   handles resolve to identical byte hashes across this operation.
4. The host must also bind the view to this episode's actual completed
   `image.view` action/result, within this run. An arbitrary globally stored
   source/view or a parent's private image is insufficient. This is a required
   input provenance relationship, not a new episode or scientific acceptance
   gate. It does not require the view to be the immediately preceding action.
   No provider history or private reasoning is inspected. The existing runtime
   supplies pixels only to the reasoning call following its own completed view;
   metadata custody does not prove the model understood the image.
5. The original input source and each exact text witness source must themselves
   have been received; view possession does not authorize arbitrary ancestors.
   Apply the existing page/reading assignment ancestry to every direct source.
   Retain provenance ancestors without treating them as received scientific
   knowledge. The display image's coordinates are half-open stored pixel axes;
   no EXIF rotation, crop, resize or contrast adjustment is silently inferred.
6. Authenticate UTF8 quotes exactly. Image expressions are attributed episode
   transcriptions authenticated as actual view/geometry only. They are never
   called mechanically verified image text. Record the original frame number,
   native artifact hash, rendered PNG hash, both actual source references and
   all selected numerator/reference/fragment regions.

`image_evidence.prepare_image` supports explicit selected frames, including
TIFF and an explicit RGB conversion. Reusing the old binding `_Inputs.decode`
directly would incorrectly limit that native-view path to one-frame PNG/JPEG.
Use the existing native view/Store contract; inspect its exact display PNG and
dimensions, without inventing a new geometric transform. No pixel-density
measurement or source re-encoding is necessary for printed-literal reading.

An inherited already-populated sheet is consumed through its admitted typed
cells. If another episode wants a fresh visual interpretation, it selects its
own ordinary `image.view`; it does not acquire the original episode's private
pixel context by receiving a source reference.

## Reading semantics and numerical population

The representation list is the selected received roster, not a claim of an
exhaustive literature search. Each representation retains its own association
to the declared comparison and physical-measurement witness. A model-supplied
local label or equal number does not establish measurement identity.

Supported nominations are: a selected JATS percentage through the existing
finite reader; a printed normalized ratio; a printed percentage; or an explicit
pair of printed signal values. Pair alternatives are nominated jointly, not
formed by an automatic Cartesian product of ambiguous numerator/denominator
readings. A visual-only comparison requires no fabricated JATS percentage.

Transcription states are exact, ambiguous, unreadable or conflicting. Exact
means one nominated complete expression, not known truth about a latent amount.
Ambiguous means alternative readings; conflicting means incompatible retained
source expressions, not a statistical confidence interval. All candidates and
unreadable fragments/regions survive. Unknown association to the same comparison
keeps that row's native parsing but withholds the aggregate comparison scalar.

Parse complete finite nonnegative decimal/scientific expressions and explicit
`< <= > >= ≤ ≥` qualifiers. Preserve exact lexemes. Reported `0` gives a reported
zero ratio when its denominator is positive, not zero molecules/nondetection.
`ND`, `n.d.`, blank and unsupported expressions remain unavailable; their spelling
does not establish a detection threshold or meaning. Unsupported negative signal
expressions are retained with a specific partial reason, never clamped to zero.
Source-defined normalized expressions must have their actual reference meaning;
an arbitrary band at another exposure is not automatically its denominator.

Deterministic numerical rules:

| Native form | r calculation | Necessary restriction |
|---|---|---|
| printed ratio | parse complete expression | source-supported ratio/reference association |
| printed percent | parsed expression/100 | preserve `%` and qualifier |
| pair of printed signals | numerator/denominator | common reported scale, supported pair, positive denominator |
| exact known scalar | difference=r-1; log=ln(r) | log requires r>0 |
| censored expression | transform reported estimate domain | never replace threshold by point or call domain a confidence interval |

Source literal division/multiplication uses exact decimal rationals first.
Finite float exports must not overflow or turn a nonzero into zero. Preserve
exact numerator/denominator strings and a specific numerical-range partial if
no finite export exists. No pseudocount, jitter, rounding-based equality or
favorable candidate selection is permitted.

For an explicit nonnegative `<0.10` signal over exact1, retain reported ratio
domain[0,0.10), difference[-1,-0.90), and positive-branch log domain(-infinity,
ln(0.10)). These constrain the reported quantity under the literal interpretation,
not the true protein amount or its sampling error. Exact zero has no log point.
Unbounded ends have explicit flags plus null endpoints, never JSON Infinity.
Denominator domains containing zero do not yield a finite scalar; retain the
native inputs and `positive_denominator_not_established` instead of inventing1.
No general correlated-censor likelihood is implemented or claimed by this route.

Do not intersect conflicting source representations into an empty scientific
domain or average them. Keep each representation's numeric/domain alternatives.
Full scalar r is populated only if every declared representation is resolved,
all comparison links are supported, all readouts are finite exact points, and
the known ratios agree exactly under their retained numerical semantics.
Unreadable/ambiguous/censored/unsupported or unknown-linked rows block that
full scalar while preserving usable candidates and native cells. A known source
conflict remains explicit even when another row is unresolved. Exact duplicate
readings collapse for arithmetic, but their custody aliases remain; none creates
a preparation count, variance reduction, independent evidence or extra credit.

The four calibrated amount/functional-response/observation-model cells remain
unavailable in this specific representation route. Their reasons must describe
route capability or unselected input, not assert the entire paper failed to
report something the operation never searched for. The existing v1 hardcoded
`*_unreported` labels remain historical; do not rewrite old sheets. The new
route explicitly identifies those conversions as outside its implemented scope.
Separate amount and experimental-effect work still owns those requirements.

## Persistence, typed return and reconstruction

The exact request, authenticated extraction/transcriptions, sheet and original
outcome are committed atomically with ordinary tool-origin sources/references.
The payload retains source and view receipt rosters, physical-identity meanings,
literal originals, calculations and unknowns. Host identities stay outside the
model-facing TASK/STEERING. Result references are real committed records, not
locally fabricated handles.

Same operation key plus different arguments/scope fails. Same selected work
replays its original committed outcome after checking the actual current caller
custody, without source bytes, OCR, parsing, fitting or new model work. Saved
validation checks request/selection equality, full output membership, exact
payload/outcome/calculation artifact association, source/provider/version,
direct/provenance roster and entity/owner bindings. It checks extraction shape
and relationships from saved records without source reacquisition or fresh
scientific interpretation. It does not invoke the numerical population function
to reconstruct historical cells.

The parent chooses a closed top-level recorded-fact field with exactly the new
projection, optional separate restricted interpretation fields, and requested
component subset. C1 retains its submitted/expanded declaration and original
assignment. Children select their own source reads/views and population action
inside ordinary LiteratureEpisodes/shared method_loop. At C4 the reporting
episode's facts must equal its original saved subset and meaningful bindings.
The parent's received table copies only the admitted subset, not the whole
private sheet. Repeated delivery is idempotent; another reference to the same
sheet does not grant unrequested cells. Whole recorded-fact schemas use only
the existing closed communication grammar, not unrestricted strings, unions
or `$ref` tricks inside returned values.

An image-view action has its own ordinary completed-action observation; the
selected population action has its own. Internal retention, parsing, arithmetic,
publication, validation and report construction create none. A returned child
completes its original parent commission once; child internal operations are
not several parent observations. Existing admit_return/CompletionLedger own
admission, completion order and controller input. No scorer/controller cost,
scientific progress formula, stop rule, timer or approval mechanism changes.

Read-only proof must first project real received cells in a fresh mode=ro,
query_only process with source/image readers, calculators, model calls,
mutations and receiver callbacks forbidden. Permit only selected saved output/
request artifacts; deny original paper/image bytes. Check original declaration,
sheet and admitted subset identity, total_changes0 and unchanged targeted
observation counts. Existing admissions replay their saved branch with no new
form composition or receipt insertion. This is future verification, not a claim
that067 executed native persistence or C4.

## Ownership and implementation order

No coding is released by this proposal. Proposed nonoverlapping owners:

1. A fresh pure-reader owner: NEW literature_ratio_source_inputs.py,
   literature_ratio_source_calculations.py, literature_ratio_source_validation.py,
   targeted NEW tests and its own artifact directory. It consumes the closed
   declared schemas. Existing ratio v1, image_evidence, helper parsers and
   experimental calculators remain unchanged.
2. A fresh repository owner after that API is settled: NEW
   literature_ratio_source_storage.py and NEW repository/readonly tests. It may
   reuse base ownership/admission mechanics only after verifying every consumer;
   override read/validation/projection for the exact new contract.
3. One explicitly assigned integration owner controls shared episode_services.py,
   literature_episodes.py, literature_experimental_prompt.py and descriptor/fact
   schema routes, plus NEW literature_ratio_source_prompt.py and connected tests.
   Coordinate these shared files with065's later controlled-response integration.
   No concurrent reader author edits the shared catalog or registration.

Preserve all existing scientific roles/child relationships and capabilities.
Record the new descriptor and original schema generation for workers/recovery.
The other tool-grader session and066's original model pin stay untouched. Parent
must print the concrete instructions and numerical examples for feedback before
a fresh implementation tranche. No user permission request is inferred.

TEST_PLAN_001.md and EXAMPLES_001.json distinguish source-grounded inherited
values, synthetic examples and prospective checks. No implementation, general
gel coverage, configured-model accuracy, primary-source acquisition or completion
of an evidence axis is established by these design artifacts.
