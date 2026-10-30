# Proposal amendment002: private counting without calibration

**Proposal only.** Root resolved the pixel-counting design toward a NEW count-only private helper inside the already proposed NEW `gene_annotation_episode/literature_controlled_response_figure_inputs.py`, with focused tests inside its already proposed NEW corresponding test file. No implementation or overall schema release follows from that decision. The sealed001 files and manifest remain unchanged.

This amendment supersedes only001's unresolved pixel-identity reuse option, the requirement for image height≥2 caused by that option, and its associated counter provenance fields. The future reader must never call `read_bar_ordinate` with identity/dummy calibration or construct a scientific cell merely to discard it. The old figure core remains entirely frozen. Applicable A105 components still operate on evidence items/experiments within papers; no top-level axis, universal paper grader, routing implementation or scientific scoring meaning is added.

## Exact private helper boundary

Proposed signature, not implemented:

```
_count_bar_runs(*, rgb_bytes: bytes, width: int, height: int,
                selection: CountSelection) -> CountResult
```

`COUNT_INTERFACE_002.json` declares the closed Python boundary, input/validation semantics and exactly which information the helper lacks. `COUNT_RESULT_SCHEMA_002.json` declares its complete closed JSON-compatible output. The input is **immutable row-major packed RGB bytes**, three unsigned bytes per pixel, for the full native selected image. It is not a PNG/JPEG file, Pillow object, path, callback, source record, model quotation or caller-provided scientific ordinate. The public selected request remains001's closed GraphMeasurementV2; the episode cannot nominate this private byte payload.

`width,height` are positive integers, excluding bool. Require `type(rgb_bytes) is bytes` and `len(rgb_bytes)==3*width*height`; no resizing, decoding, color conversion or extra padding occurs inside the counter. A malformed internal raster raises a repairable/internal contract error, never an empty scientific observation. Height1 is mechanically supported now. Endpoint clipping and conditional edge bounds can still make a one-row scientific ordinate unavailable downstream.

CountSelection has **exactly** these five fields, copied mechanically from the selected bar recipe:

```
roi: {left:int, top:int, right:int, bottom:int}
rgb_min: [int,int,int]
rgb_max: [int,int,int]
minimum_row_fraction: int|finite float
minimum_run_rows: positive int
```

ROI coordinates are nonnegative integers excluding bool, with left<right, top<bottom, right≤width and bottom≤height. Boxes are half-open in the native selected image with origin upper-left and y increasing downward. RGB bounds are inclusive integer 0…255 triples, excluding bool, with componentwise min≤max. The fraction must have exact Python type int or float, be finite if float, and satisfy0<f≤1; the run length is a positive integer excluding bool. Reject extra fields, including calibration, unit, value, edge tolerance, terminal edge and biological labels. Edge/tolerance belong to the later wrapper step and cannot affect pixel-run counting.

CountResult has exactly:

```
version: "controlled_response_bar_runs_v1"
raster_rgb_sha256: sha256 of the actual input packed RGB bytes
image_size: {width:int,height:int}
selection: exact original CountSelection
row_fraction_exact: {numerator: positive decimal integer string,
                     denominator: positive decimal integer string}
qualifying_runs: [{top:int,bottom:int}, ...]
status: "no_run" | "single_run" | "multiple_runs"
```

The exact row fraction has0<N≤D. Validation of supplied arguments raises `ExperimentalContractError(code,field)` using the finite errors declared in COUNT_INTERFACE_002.json; missing/extra call keywords raise ordinary Python TypeError; the helper has no dependency-unavailable fallback or scientific missing-value conversion.

Runs are nonempty, ordered, disjoint native row ranges; bottom is exclusive. Status is determined solely by run count0,1,>1. No calibrated pixel edge, ordinate, rate unit, confidence bound, covariance, score, source-authorization assertion or scientific cell can appear in this output. The RGB raster hash identifies these actual decoded bytes; it does not replace encoded original/crop hashes or confer source custody.

## Validated bytes and source/geometry consumers

The new wrapper, not the counter, owns all of001's source-authorization and decoding responsibilities:

1. Validate the public closed selection and declared image/reference closure. Prefetch every selected/original image and tick/unit/scale witness dependency through the **actual caller callback**, validating exact `{artifact_ref,content:bytes}` results before any049 broad catch. Preserve authorization and malformed-record exceptions; only001's explicit unavailable I/O classes become scoped partials. No independently supplied raster authorizes a source.
2. Retain the actual authorized encoded original and selected-image bytes with artifact references and SHA256. Authenticate text with `_Sources.witness`, preserving exact UTF8 offsets and source bytes. Image labels remain episode transcriptions authenticated only as bytes/geometry; no OCR claim is added.
3. Use frozen049 `_Inputs.image`/`.location` for original/crop pixel equality and mapped regions. Invalid crop/reference/ROI mappings remain repairable errors. No scaling, flipping, rotation or interpolation is inferred.
4. The NEW wrapper's private strict decoder validates the actual original and selected bytes before counting. It must enforce the frozen core's relevant accepted decoding guards directly, without invoking that calibrated core: PNG/JPEG; RGB/RGBA/L; one frame; complete PNG terminal IEND; successful verify/reopen/load; EXIF orientation1; image decompression warnings/errors handled as unsupported/decode dependency information. The existing049 decoder alone is insufficient because it has different terminal/orientation checks. These guards live in the same new module, with no new shared decoder file.
5. Verify the strict decoded dimensions/modes/pixels agree with the geometry used for049's crop match. In RGBA, inspect all alpha bytes in the selected ROI **and** its mapped original ROI before counting. Any alpha≠255 is unsupported in this bounded reader, even if a crop's permitted RGB conversion hid the alpha. Do not composite against a guessed background. Nonopaque pixels outside those ROIs do not change the selected count.
6. Construct full-image packed RGB bytes from that strict decoded selected frame: RGB unchanged; L replicated identically into R/G/B; RGBA converted by retaining RGB only after the selected and original ROI opacity checks. Those actual immutable bytes, their actual dimensions and the five copied recipe fields are the counter's only inputs. The helper never sees an RGBA raster or a silent color conversion. Release temporary decoder/image resources after construction.
7. Keep the encoded source identities, mapping, original unmodified recipe, counter module identity, label/unit/scale qualifications and resulting run ranges in the wrapper's normal extraction record. A decoded-raster hash is supplemental provenance; it cannot substitute for001's encoded byte hashes or source locators. The caller remains responsible for source authorization and later typed persistence.

A test may call the private counter on constructed RGB bytes to verify counting. Such a test exercises only the mechanical boundary; it does not establish source custody, opacity checks or actual scientific acquisition.

## Exact counting and parity with the frozen row rule

Let `f=Fraction(selection.minimum_row_fraction)` using the same integer/binary-float conversion as the frozen core. The helper must not silently use `Fraction(str(selection.minimum_row_fraction))`, parse a different decimal, apply an epsilon or round a row proportion. Let N/D be f in lowest terms with positive D. Retain N,D in row_fraction_exact.

For each native y from ROI.top through ROI.bottom−1, count exactly the pixels x in ROI.left through ROI.right−1 whose three raw RGB channel values are each within the selected inclusive bounds. If that count is M and ROI width is W, the row qualifies exactly when:

```
M * D >= W * N
```

Build maximal consecutive qualifying row runs, then retain only those with length≥minimum_run_rows, including a run ending exactly at ROI.bottom. No row outside the ROI participates. No top-edge clipping check occurs here; no run is selected or altered because of its location, sign, height, brightness or scientific interpretation. CountResult must expose all retained runs, including a boundary-touching run.

This provides the same threshold/run semantics as the already inspected frozen core while avoiding its coupled calibration and upper-edge behavior. Parity is established by this explicit rule and analytically specified fixture expectations. Future tests must **not** call the old calibrated function with dummy/identity values merely to recover a reference result. They may compare independent expected row/run fixtures and exact rational inequalities without fabricating a scientific cell.

A critical fixture distinguishes binary recipe semantics from decimal substitution: with W=10, minimum_row_fraction=0.1, the exact selected Python float is 3602879701896397/36028797018963968, slightly greater than1/10. Thus M=1 **fails** and M=2 passes. A decimal1/10 substitute would incorrectly accept M=1. This difference is a mechanical recipe fact, not a scientific uncertainty estimate.

## Consumer separation and exact output delta

The counter produces runs only. The existing proposed wrapper step then handles no/multiple runs and reads the nominated upper/lower terminal using001's exact signed equations and endpoint-specific clipping checks. Axis-scale authentication, tick parsing, rate-unit dimensions and conditional digitization intervals remain separate. No positive-only clamp or zero baseline is introduced. Graph origin and006's known-normal-profile exclusion remain unchanged; the counter cannot manufacture sampling uncertainty or C.

`GRAPH_RESULT_SCHEMA_002.json` is an explicit proposed revision of the pending001 graph-result schema with **only** these PixelResult changes:

- Replace `core_version` with `counter_version`, constant `controlled_response_bar_runs_v1`.
- Replace `core_sha256` with `counter_module_sha256`, the host-recorded SHA256 of the actual new module implementation bytes. It is implementation provenance, never a selected source value. The existing controlled reader/caller must bind that identity to its deployed version; this amendment does not invent a code-integrity mechanism.
- Remove `core_counting_calibration` entirely; the new path has no calibration scaffolding.

All other001 graph-result types remain unchanged, including qualifying_runs, original/crop byte identity, recipe, source qualifications and exact signed values/bounds. CountResult is an internal typed result; its exact fraction and decoded RGB hash remain available to the wrapper's operation provenance, while the pending public PixelResult retains the complete original recipe from which this fixed counter version reconstructs that fraction. No public selection-schema change is required by replacing the counting implementation. The v2 full controlled-response consumer delta remains001's **pending proposal**; neither it nor any of the three001 schemas is approved by root's counting decision.

The001 synthetic receipt remains a truthful historical probe of the old helper, not a proposed production algorithm. Its identity-calibration test calls must not be copied into the future implementation/tests. The001 expected output is likewise historical/illustrative; GRAPH_RESULT_SCHEMA_002.json supersedes its old counter fields for the pending new interface. No001 file is rewritten.

## Focused future tests and ownership

TEST_PLAN_002.md specifies meaningful fixtures for channel inclusivity, ROI boundaries, exact fractions, minimum run lengths, no/multiple runs, malformed rasters, opacity at original/crop boundaries, clipping, error bars and signed/reversed-axis responses. These are proposed tests, not written or executed production tests. The counter's invariant result under different downstream terminal choices is tested independently of signed mapping; downstream edge/unit/axis consumers retain their own responsibilities.

Ownership remains exactly two already proposed NEW files: `gene_annotation_episode/literature_controlled_response_figure_inputs.py` and `tests/test_literature_controlled_response_figure_inputs.py`. The private counter and strict decoder live inside the former; no third file or frozen/shared helper change is requested. Overall schema review, coding release, actual primary graphical evidence and selected-native typed delivery remain unfinished. This amendment involved no new paper/scientific-source/model read or scientific run.
