# Proposal001: acquire a signed rate ordinate from witnessed pixels

**Proposal only. No production reader, test, new scoring sheet or runtime integration is released.** Frozen007 remains unchanged, including its legacy `graph_rate_reader_unimplemented` response. The proposed new version supplies only mechanical graph operands for the accepted A105 controlled-response sheet. It does not decide four-arm comparability, isolation, shared-control ownership, covariance, statistical interpretation, A101 transfer, W05 credit or literature routing.

## Decision requested

**Unresolved reuse choice:** root has not accepted the pixel-identity calibration adapter. No such wrapper has been implemented. The primitive proof uses mechanical identity scaffolding only to expose existing runs; future production reuse or a separately authorized NEW count-only core must be decided by root after reviewing this boundary.

Approve or revise the exact v2 selection/output delta and ownership of two NEW files before implementation. The bounded first wrapper accepts plain registered rate units and a known linear scale. Unresolved labels, unsupported units/scales and unreadable pixels preserve independent authenticated information. A future real primary figure and actual selected-native typed delivery remain unfinished.

The intended future unit is an evidence item/experiment within a paper selecting applicable A105 extraction/sheet components; a paper may contain several such items. This is neither a new top-level axis nor a universal paper grader. Routing implementation remains deferred.

Root approved preparation of this explicit versioned proposal after identifying two missing007 nominations: which end of a bar is its response, and what supports a linear axis. Sibling056 confirmed008 introduces no graph-facing schema/result change. Its only approved semantic clarification concerns conflicting exact original source values that collide after float projection; that rule is preserved.

## Exact selected interface and minimal delta

`SELECTION_SCHEMA_V2_001.json` is the full closed007 root schema with only these changes:

1. Root version becomes `controlled_response_source_selection_v2`.
2. `GraphMeasurement.terminal_edge` is required: `upper|lower`.
3. `GraphMeasurement.axis.scale` is required, using the new closed `AxisScale` type.

Every other007 definition is copied unchanged. The kind remains `linear_bar`: it nominates use of this linear reader, rather than attesting that the underlying source is linear. A request honestly recording a logarithmic/nonlinear/unknown/conflicting source scale is structurally valid and receives an unsupported/unresolved partial, without two-tick calibration.

`AxisScale` has exactly:

```
status: known | unknown | conflicting
kind: linear | logarithmic | nonlinear | null
basis: source_text_literal | image_episode_interpretation | unresolved
witnesses: Witness[]
```

Known requires nonnull kind, a resolved basis and at least one witness. Unknown/conflicting requires kind=null and basis=unresolved; conflicting must retain the actual conflicting witnesses. Conditional relationships are semantic validations as well as the declared schema constraints.

`GRAPH_REQUEST_SCHEMA_001.json` defines the separate closed wrapper request:

```
{version: controlled_response_rate_figure_selection_v1,
 images: Image[], measurement: GraphMeasurementV2}
```

The callback is a host argument, never a model-selected executable or path:

```
read_controlled_response_rate_figure(arguments, *, read_source) -> GraphResult
read_source(source_ref, representation) -> {artifact_ref: nonempty str, content: bytes}
```

No selected ordinate, numeric tick value, scale multiplier, biological denominator, uncertainty, covariance or graph-derived score is accepted. Selected numbers are byte offsets, image boxes, pixel coordinates and threshold/row/tolerance recipe parameters. Tick numerals and unit text occur only inside source witnesses or explicitly qualified image-label quotations. JSON Schema validation must reject nonfinite Python floats in addition to ordinary schema validation. Aliases may be resolved only by the existing caller; a plain invocation uses existing persistent references.

## Exact outputs and007/008 impact

`GRAPH_RESULT_SCHEMA_001.json` declares every wrapper object with closed fields, including SourceRecord, ImageRecord, WitnessRecord, AxisScaleRecord, AxisLiteralRecord, GraphUnitRecord, PixelResult, MeasurementExtractionV2 and NativeProjection. The standalone wrapper root is:

```
{version, selection, sources, images, axis_scale,
 axis_literals:{first,second,unit}, measurement, operand_projection, diagnostics}
```

Its version is `controlled_response_rate_figure_extraction_v1`. `selection` preserves the exact original request. `axis_literals` preserves every candidate/fragment and exact authenticated lexeme or attributed image transcription; graph results do not masquerade as007 text NumberCandidates. `measurement.candidates=[]`; the original graph nomination is in `measurement.selection`. All graph witnesses are retained in `graph_witnesses`, unresolved fragments in `fragments`.

`EXACT_DELTA_001.json` declares a separately proposed `controlled_response_source_extraction_v2` consumer result, retaining007 fields with these graph additions:

- Add `graph_digitized` to MeasurementExtraction.reading_status.
- Permit PixelResult in MeasurementExtraction.pixel_result for v2 graph; old/text branches retain null.
- For graph, UnitRecord becomes the declared GraphUnitRecord: its selection is the original AxisLiteral, rather than pretending it was a007 UnitSelection. Definition witnesses remain null in this bounded release.
- Add `ArmExtraction.graph_details`, null for text/absent measurements, otherwise exactly `{axis_scale,axis_literals:{first,second,unit}}` with the closed wrapper record types.

No old object is silently reinterpreted. Frozen008 still implements v1 and retains its graph-unimplemented branch. An explicitly released future v2 adapter must validate the full v2 selection, authorize the complete parent selection closure, call this wrapper for each graph arm, copy the graph records, and join the numerical projection with its independently authenticated007 meaning/context IDs. It then passes exactly frozen006 `controlled_response_inputs_v1`, with no calculator API change. Do not pass v2 arguments through unmodified008, monkeypatch its branch or add extra fields to v1. The v2 adapter/registration/shared renderers remain separately owned and unapproved here.

Graph NativeProjection is exactly the numerical subset of a006 arm: value, threshold, relation, approximate, unit, status, origin, digitization_interval. A successful reading supplies finite native value, threshold=null, relation=interval, approximate=true, status=point, origin=graph_derived, and finite `{lower,upper}`. The adapter supplies endpoint/normalization/construct/condition/physical/source IDs, arrangement and meaning states from the normal007 path, never from bar height. Failed projection supplies no numerical operand; no zero or arbitrary alternative is inserted.

## Source authorization and immutable bytes

Perform these operations in the future wrapper, in order:

1. Validate closed structure, unique declared image IDs, all references, boxes and finite mechanical parameters before any callback. Enforce exact/ambiguous/unreadable/conflicting AxisLiteral cardinality: exact has one candidate and no fragments; unreadable has no candidate; ambiguous/conflicting has at least two distinct nominations. Retain all selected alternatives.
2. Build the entire wrapper dependency closure: every declared image's selected and original source representation, every text witness in ticks/unit/scale candidates or fragments, and every image witness's selected/original image source. The future parent v2 reader also prefetches its larger arm/meaning/covariance/model closure. Deduplicate only identical `(source_ref,representation)` requests.
3. Invoke the **actual caller callback** on the closure before constructing049 `_Inputs`. Validate callback results as the exact two-key object, nonempty artifact reference and immutable bytes. Preserve the original content, artifact and SHA256; do not accept an independently supplied file as authorization. No substitute resolver, selected artifact bytes or cache from another operation may grant access.
4. Authorization exceptions and malformed callback records propagate unchanged. All ContractError/ExperimentalContractError from the callback propagate, regardless of their names. PermissionError, unexpected exceptions and unexpected OSError propagate. Only FileNotFoundError with errno=ENOENT and OSError with errno=EIO or ETIMEDOUT are the bounded wrapper's explicit source-unavailable I/O exceptions. A caller using a different genuine unavailable signal needs an explicit reviewed adapter, not a broad catch. If a dependency is unavailable, its exact selected witnesses remain with unavailable authentication; their quotes are not promoted to raw authenticated literals.
5. Only after prefetch, instantiate049 `_Inputs` on a sealed cache reader. That reader has no external lookup or fallback and returns only validated authorized records or the previously recorded explicit unavailable I/O exception. Authenticate text directly through `_Sources.witness`; do not entrust text forgery validation to049 broad catches. A mismatched quote, out-of-bounds span or split UTF8 code point is a repairable selection error and propagates.
6. Use049 image/crop verification and original-region mapping. Require actual selected crop decoded pixels/mode/size equal the selected original region under `preserve|rgb`. No resize, flip, rotation or nominal coordinate transform is inferred. Unmapped source must equal original source. Check errors explicitly: bad mapping/ROI/region/reference is a repairable request failure, while genuine image decode/format limitation is scoped dependency/capability information.
7. Apply the stricter existing pixel-core format/orientation/terminal validation to both selected and original bytes. They must be PNG/JPEG, single frame, RGB/RGBA/L, full valid bytes, EXIF orientation1. A crop cannot hide an unsupported original orientation, malformed bytes or alpha issue. Check RGBA alpha in both selected ROI and mapped original ROI; any alpha other than255 is unsupported in this release, including a crop saved with RGB conversion. No hidden RGB or guessed background compositing is measured.

The existing049 broad catch actually converts an authorization ContractError without a `.code` into `source_read_failed`. The synthetic receipt demonstrates this existing boundary defect; the proposal requires upstream preauthorization rather than editing049. Source guards and decode checks are ordinary typed reader behavior, not a new reviewer/approval gate in an episode.

## What authenticates a tick or an axis

Text witnesses authenticate exact UTF8 bytes and their source locator. They do not automatically prove that the selected passage describes the selected panel. Image witnesses authenticate actual bytes and mapped geometry only. Their quotations, including a perfectly legible numeral, remain **investigating-episode transcriptions**, never OCR output or a software attestation of scientific truth.

For each exact tick, require the entire trimmed candidate quote to be one signed decimal/scientific literal:

```
[+−-]?(digits[.digits?]? | .digits)([eE][+−-]?digits)?
```

Here digits means ASCII `[0-9]+`; Unicode minus is normalized only for numerical parsing, and the original spelling survives. No inequalities, approximation, comma grouping, expressions, powers rendered as `×10`, ranges, unit suffixes or relative-percent expressions are treated as tick values. For text, derive the whole-quote NumberSelector and run frozen native `_number` in its unrestricted-sign `condition` role, including existing full-source/field boundary and qualification guards. A parsed point must be relation=point and approximate=false; only then obtain the exact Fraction from the retained lexeme. Its finite helper projection is not the calibration operand. A text helper numeric-range failure retains its authenticated raw quote and returns a tick-capability partial in this first wrapper, even if a hypothetical larger exact calculation could cancel it. No bypass of the existing lexical guards is claimed. Image ticks use the same strict whole-literal grammar but lack full text-context checks; output explicitly records episode_image_transcription. Their truth, selected coordinates and panel association are conditional inputs.

AxisScale source_text_literal requires all selected witnesses be text, have one of the full trimmed case-insensitive phrases `linear scale`, `linear axis`, `logarithmic scale`, `logarithmic axis`, `log scale`, `log axis`, `nonlinear scale`, `nonlinear axis`, `non-linear scale`, `non-linear axis`, and agree with the selected kind. Text boundary/field context must not clip a larger term or explicit adjacent negation; a caption requiring a broader semantic interpretation is unsupported by this narrow literal basis. Phrase matching establishes that the phrase is present; its association with this axis remains the episode's witnessed interpretation. `image_episode_interpretation` requires at least one geometrically authenticated image witness; the episode may interpret visible tick layout or an explicit graphical scale label. No automatic OCR/visual linearity claim is made. Two selected tick labels **alone** never establish linearity. Every known scale also retains the interpretation diagnostic. Unknown/conflicting scale is preserved; logarithmic/nonlinear scale is explicitly unsupported. Pixel counting and raw witnesses may still be returned, but axis/ordinate/projection remain null.

Unit literals follow the same exact-candidate and qualification rules. For text, use frozen native `_unit` for boundary checks and `_plain_unit` for its existing registered aliases and exact scale. For image quotations use `_plain_unit` with the image-transcription qualification. Select the native RATE_UNITS key matching canonical dimension and exact scale; do not force all data into a base unit before006. Supported keys are umol/min, nmol/min, mmol/min, uM/min, nM/min, per_min, per_s, umol/min/mg, nmol/min/mg. Preserve printed unit and exact native-to-base factor separately. Concentration rate, amount rate, turnover rate and specific amount rate are distinct dimensions. A mg denominator is a physical unit, not proof that the biological mass/construct/condition normalization matches another arm; those meanings stay in007.

`U/mg` cannot be safely inferred from the frozen graph AxisLiteral: it lacks the accepted full source-defined endpoint/unit bridge nomination. Preserve it with unsupported + graph_unit_defined_bridge_unselected; do not give it factor1 or read an unselected definition. Extending graph unit nominations to the full accepted source-defined bridge requires another explicit selection/output delta. Unknown units, percentages and arbitrary signal are likewise no rate operand. This is a concrete bounded coverage limit, not a conclusion that these sources lack evidence.

## Reuse the deterministic pixel runs, not the old scientific cell

The actual frozen `read_bar_ordinate` already supplies validated bytes/hash/dimensions and consecutive threshold-qualified row runs. Reuse that count result without changing its file. Its existing public scientific calibration supports only relative_turnover_percent, arbitrary_signal and nanomolar, interprets float coordinates as exact binary Fractions, and always reads the run's upper edge. Directly supplying a rate unit fails, and directly calibrating a negative lower-edge bar is wrong.

The new wrapper may call that frozen function with a **host-generated pixel identity calibration** `(pixel0,value0),(pixel1,value1),unit=arbitrary_signal`. Those zero/one operands define the pixel coordinate identity only; they are neither nominated nor recorded as scientific ticks. The function's cell/pixel_edge is discarded. The wrapper records core version/hash and the finite identifier `host_pixel_identity_not_scientific_data`, takes only its actual qualifying_runs, validates the chosen endpoint itself, and computes scientific mapping from the separately authenticated labels. Identity calibration requires image height≥2; shorter images are unsupported. Validate selected mechanical axis coordinates lie in `[0,height)` even if scale later proves unsupported. ROI must lie inside the selected image.

All boxes are native selected-image half-open `[left,top,right,bottom)` rectangles, with origin at upper left. Axis pixel coordinates are vertical y coordinates in that same selected image; rows increase downward. Tick y positions need not lie inside the bar ROI. Crop positions map to the original by adding its top offset, without scale changes.

The core's qualifying rule is exact relative to the selected recipe's actual Python numeric representation: a pixel matches iff all three RGB channels lie within inclusive low/high bounds. A row qualifies iff `matched_count / ROI_width >= minimum_row_fraction`. Consecutive rows of at least minimum_run_rows are retained, with run bottom exclusive. The frozen core uses Fraction(float) for recipe fraction/tolerance, so the wrapper uses that same exact binary mechanical interpretation, records the unmodified recipe and does not silently substitute decimal mechanical semantics. Integer coordinates and integer source offsets remain exact. It does not quantize or recompress bytes.

No retained run means unreadable; multiple runs means ambiguous. Do not pick the tallest, highest, lowest or favorable run. Connected same-color error bars/labels can form a single false run; RGB thresholds do not distinguish biological bar means from annotations. The episode must choose a suitable ROI/color/endpoint and repair interference when known. Antialiasing, compression and outline-only bars can exclude pixels or move threshold boundaries. The tolerance is an explicit conditional allowance, not a calibrated error probability or a guarantee that an inappropriate ROI identified the right object. No RGB threshold is auto-tuned against a desired answer. Finite diagnostics describe limitations, never penalties to scientific credit.

## Signed ordinate and conditional bounds

For a sole retained run `[T,B)`, chosen terminal edge and tolerance `t>=0`:

| selection | nominal pixel p | pixel lower L | pixel upper U | endpoint clipping condition |
|---|---|---|---|---|
| upper | T+1/2 | T−t | T+1+t | T=ROI.top |
| lower | B−1/2 | B−1−t | B+t | B=ROI.bottom |

An endpoint touching its ROI boundary is unreadable, with all runs/bytes/witnesses retained. Opposite-end baseline clipping alone does not prove terminal clipping: preserve it as a selection limitation and do not extrapolate a zero baseline. If conditional bounds extend outside `[0,height)`, retain the actual run and edge but withhold the calibrated reading; do not clip the interval to the image or invent unseen pixels. Filled bars that cross zero, start above zero, or float between bounds are not automatically identified as means. The selected terminal edge and object identity remain conditional episode interpretations.

Let authenticated exact tick values be `v1,v2` at selected pixel coordinates `p1,p2` (the latter use the same binary-mechanical Fraction convention). Require p1≠p2 and v1≠v2. Define exactly:

```
s = (v2−v1)/(p2−p1)
f(y) = v1 + (y−p1)*s
nominal = f(p)
interval = [min(f(L),f(U)), max(f(L),f(U))]
```

The slope may be positive or negative. Neither tick order, axis direction nor negative response is clamped. Unequal tick spacing is not a defect for two points; the mapping is conditional on the witnessed linear-axis interpretation. Equal coordinates/equal values are degenerate and supply no calibrated ordinate. A broken/logarithmic/nonlinear axis, multiple scales, unselected printed multiplier or missing unit does not receive a default linear factor. Printed axis multipliers such as `×10³` require a future full source-bound multiplier nomination and are unsupported now, never silently ignored by selecting only the base unit. The present image qualification cannot automatically discover omitted labels; it does not attest that an investigator chose the complete unit label.

Exact native values and bounds are recorded as numerator/positive-denominator strings. Project the nominal to a finite native float only at the006 boundary. Nonzero underflow/overflow withholds the native operand but preserves exact graph values; a separate canonical display failure does not erase a valid native operand. For bound export use frozen006's decimal-float semantics: compare exact bound with Fraction(str(exported_float)) and move with nextafter toward the appropriate infinity until containment holds; reject nonfinite results. Include the projected nominal inside exported bounds. Record rounding. Existing core `_float` instead checks Fraction(float); do not use its scientific cell as the export. The synthetic receipt checks this distinction.

These are **conditional digitization bounds**, holding selected tick values/positions, unit, linearity, object identification and recipe fixed. They do not incorporate tick transcription error, calibration uncertainty, sampling variability, replicate counts, SD, SEM, CI or covariance. Error bars remain separate source evidence interpreted only by the accepted uncertainty reader. The wrapper never creates C from a range, assumes arm independence or promotes a graphical interval to a confidence interval.

006 may propagate available native intervals through its existing dependency-aware linear arithmetic; meaning and dimension failures remain its responsibility. Its final bound float rendering currently uses nearest rounding, so this proposal does not claim universal outward containment for every downstream rendered006 cell. Exact wrapper bounds remain authoritative for digitization. Changing006 rendering is outside this proposal. Graph origin and interval force the accepted006 optional-known-normal S/B profile off, even with separately supplied joint C; V/SE, when genuinely supported under006, remain distinct. No calculator semantics are amended.

## Synthetic examples, not experimental evidence

The compatibility script constructs and saves actual PNG bytes; it reads no paper. In every numerical example, source tick strings are `4` at row20 and `0` at row60 in umol/min, so slope is −0.1 per pixel and tolerance is0.5:

| constructed run and selected edge | nominal | conditional interval |
|---|---:|---:|
| [20,60), upper | 3.95 | [3.85,4.05] |
| [60,80), lower | −1.95 | [−2.05,−1.85] |

For reversed ticks `−4` at20 and `0` at60, the same lower edge gives +1.95 with [1.85,2.05]; the upper run gives −3.95 with [−4.05,−3.85]. The bounds use a full one-pixel edge cell plus tolerance; they are not a symmetric claimed confidence interval.

The actual frozen helper calibrated directly with the negative bar reads its top at60.5 and returns −0.05. That counterexample motivates terminal_edge; it does not revise any score. A clipped lower terminal at ROI.bottom is accepted by the old top-only helper but must be withheld by the new lower-edge wrapper. Conversely an upper baseline clipped at ROI.top can coexist with an observable lower response edge; no mandatory zero-based bar model is inferred.

A narrow ROI through a connected error-bar stem yields a single qualifying run [40,80) even though the constructed bar starts at60. A disconnected same-color cap/label creates multiple runs. Transparent black pixels also qualify after the old helper drops alpha. The receipt preserves each actual helper result and shows proposed limits rather than presenting these failures as valid new graph acquisitions.

## Provenance, ownership and remaining work

BASELINE_001.json identifies27 full snapshots of authority/contracts/helper source, including the accepted006 hash. READ_PROVENANCE_001.md distinguishes complete reads from partial transitive utility reads. No primary source, retained paper packet, unstable008 implementation, provider record, private history, credential or full process argv was opened. No full post-paper reset is claimed because no paper was read; future primary review must follow the complete goal procedure and its own fresh bounded workload.

Synthetic checks run the frozen pixel/crop/text primitives and validate proposed schema structure/rejections. They do not run a new source-prefetch implementation, graph wrapper, scientific grader, v2 adapter, persistence/runtime path or real literature case. Selection schemas preserve numerical-injection rejection, not truth of an image quote or axis/object interpretation.

Requested future implementation ownership is exclusively two NEW paths:

- `gene_annotation_episode/literature_controlled_response_figure_inputs.py`
- `tests/test_literature_controlled_response_figure_inputs.py`

Any additional NEW private helper would need explicit coordination first. No writes to056's controlled-response text reader/tests,059 shared files, frozen049/figure/source helpers,006 calculator, prompts, storage, routing or score count are requested. A future fresh coder must read this sealed contract, source authorization consumers and complete accepted006/007 paths; actual source-bound graph delivery and eventual v2 consumer integration need separately released work. This proposal closes a design gap only, not authentic experimental graph coverage.

## Deterministic partial projection and retained identity

All dependencies are read/validated before outcome classification. Preserve every independently acquired label/unit/scale/pixel result. Root measurement status uses the first applicable state in this fixed order: dependency_unavailable, conflicting, ambiguous, unreadable, unsupported, graph_digitized. This priority affects only the summary enum; it does not erase less severe diagnostics or any valid neighboring arm. PixelResult.status applies to its own acquired pixels and calibrated ordinate: unavailable image→dependency_unavailable; multiple runs→ambiguous; no run/selected-edge clipping→unreadable; acquired pixels without supported axis/unit/calibration→unsupported; full exact ordinate→measured. Native float range failure keeps exact PixelResult measured but MeasurementExtraction unsupported and no numerical projection.

NativeProjection maps graph_digitized→point, dependency_unavailable/unreadable→missing, and other failed summaries to the same unsupported/ambiguous/conflicting enum. Failed projections have value/threshold/interval=null, relation=none, origin=graph_derived and approximate=true; a supported native unit may survive. Successful ones have threshold=null and relation=interval. The v2 adapter never uses a failed projection as a numerical operand. CanonicalDisplay is separate and may remain unavailable with a valid native projection.

A successful source_observation_id is a generated content identity over reader/version, both original and selected byte hashes/artifacts, selected and mapped ROI, selected recipe, terminal edge, exact tick lexemes and source locators, mechanical tick coordinates, unit record and scale witnesses/interpretation. It is null when no finite native projection is produced. Different recipes/crops do not falsely claim identical source readings. Different generated reading IDs never establish distinct biological experiments; physical observation ownership still comes from007 source meaning records. No UID can confer custody or independently certify a shared-control relationship.

The future text-label wrapper must additionally reject a visibly adjacent printed scale multiplier in full authenticated field context (e.g. `×10`, `x10`, `*10` with exponent, or a selected whole unit label containing such expression) instead of stripping it to the base unit. An image-only nomination cannot mechanically rule out omitted multipliers, error bars or panel labels; that limitation is explicit in its conditional attribution. Known interference or incomplete label nomination calls for repair, not a numeric penalty, favorable default or zero.

`SYNTHETIC_OUTPUT_001.json` is a hand-constructed expected record conforming to the proposed output schema, assembled from the synthetic primitive receipts; it is **not** a captured output of an implemented wrapper. Its schema validation demonstrates type/shape compatibility only.
