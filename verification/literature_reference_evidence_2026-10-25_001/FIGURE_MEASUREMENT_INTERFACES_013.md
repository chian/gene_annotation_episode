# Native bar-ordinate extraction for experimental numerical cells

This fixed first implementation follows the original CofC/CofD case and its
post-paper authority reset. It populates graph-derived relative-turnover
measurements and representation-difference components; it does not decide partner
necessity, measure molar flux, or implement A107 genomic/coexpression scoring.
There are still ten axes. The cells support A105 source evidence and later
experimental partner rationale, with target transfer/W05 deferred.

## Responsibility and ownership

Fresh coding owner: gene_annotation_episode/literature_figure_measurements.py
and tests/test_literature_figure_measurements.py only. Coordinator owns native
selection recipes, source/axis verification, populated examples and handoff.
No changes to Store, ToolRegistry, LiteratureEpisodes, prompts, controllers,
original cases, historical receipts, or live code pin in this workload.

The reader is a pure deterministic function over supplied JPEG/PNG bytes and
closed numeric selection parameters. It makes no network/model/SQL calls and
performs no scientific interpretation. Use installed Pillow; do not add packages.
No source pixel values, error-bar semantics or axes are inferred from prose.

## Input and exact extraction

Export read_bar_ordinate(image_bytes, selection). All objects closed; finite
numbers exclude bool. Selection exactly:

```
roi: {left:int,top:int,right:int,bottom:int}  # half-open native pixel bounds
rgb_min: [int,int,int]  # inclusive 0..255
rgb_max: [int,int,int]  # inclusive 0..255, each max>=min
minimum_row_fraction: finite number in (0,1]
minimum_run_rows: positive integer
edge_tolerance_pixels: finite nonnegative number
calibration: {
  first: {pixel:finite number,value:finite number},
  second: {pixel:finite number,value:finite number},
  unit: relative_turnover_percent | arbitrary_signal | nanomolar
}
```

The two calibration pixel positions differ, as do their ordinate values.
Pixel positions are native vertical coordinates within the image. ROI must be
nonempty and entirely within the original image. Strictly validate every field,
integer, array shape and unit before allocating/counting. Accept only nonempty
JPEG/PNG byte strings. Do not change image size, orientation or colour mode
silently: convert decoded RGB/RGBA/L to RGB only for colour counting; reject
nontrivial EXIF orientation rather than silently transforming source coordinates.
Reject malformed/unsupported images with a specific ContractError code.

For each native row in the ROI count pixels passing all three RGB ranges.
It qualifies when count/ROI_width >= minimum_row_fraction (compare exactly
with rational arithmetic). Find maximal contiguous qualifying row runs and
discard runs shorter than minimum_run_rows. No run gives an unavailable
measurement; more than one gives ambiguous_bar_runs. Never choose a favourable
or largest run. A unique retained run's top row is the mean fill edge; thin
black uncertainty bars do not become a coloured mean edge merely by sharing
the ROI. Pixel threshold/ROI selection remains an explicit interpretation.

For top row y, use centre y+.5 and edge domain
[y-edge_tolerance_pixels,y+1+edge_tolerance_pixels]. These conventions and
tolerance are supplied digitization assumptions, not empirical confidence.
Map through f(p)=v1+(p-p1)*(v2-v1)/(p2-p1), preserving decreasing axes. Derive
with exact Fraction intermediates; value is the nearest representable finite
float, bounds rounded outward to enclose the exact endpoint images. A cell
whose finite value is unrepresentable becomes unavailable numerical_model_range;
do not invent infinity. Do not clip measurements to 0..100.

Return exactly:
```
version: literature_bar_ordinate_v1
image_sha256: lowercase SHA256
image_size: {width:int,height:int}
selection: exact deep copy of input
qualifying_runs: [{top:int,bottom:int}]  # half-open, only retained runs
pixel_edge: {top_row:int,centre:finite,lower:finite,upper:finite} | null
cell: {
 value: finite|null, lower:finite|null, upper:finite|null,
 unit:<calibration unit>, origin:graph_derived,
 bound_kind:conditional_digitization_not_confidence_interval,
 status:populated|unavailable,
 unavailable_reason:null|no_bar_pixels|ambiguous_bar_runs|numerical_model_range
}
```

Contract errors distinguish malformed selection, image, calibration and ROI.
Use stable explicit codes. Missing or ambiguous mean edges preserve full
selection, dimensions and retained runs. No image bytes are copied into JSON.

## Numerical representation comparison

Export compare_ordinate_cells(first, second). Each input is exactly the closed
cell above. Require same unit and origin/bound semantics; allow unavailable
inputs with their reasons. Populated cells have lower<=value<=upper and finite
numbers. Output exactly `{version:literature_ordinate_difference_v1,cell}`.
Result cell same shape, origin=derived and same bound_kind. For two populated
cells compute first.value-second.value; range
[first.lower-second.upper,first.upper-second.lower] with exact rationals and
outward rounding. This is an outer digitization difference domain, not a CI.
Unknown input gives unavailable_reason=missing_ordinate; unit mismatch is a
specific ContractError. Overflow gives numerical_model_range. No scalar quality
grade, probability, independence assumption, replicate count or final annotation
score is produced by this difference. Source representation identity and
scientific comparability are the caller's separate declared responsibilities.

## Required verification and first original case

Use actual in-memory native images in tests, plus the retained original Figure2
and Figure6 image hashes in the coordinator's examples. Cover axis direction,
exact pixels, outward bounds, anti-aliased edge tolerance, narrow black error
bar versus coloured mean fill, gaps/multiple runs, out-of-image ROI, malformed
closed fields/booleans/calibration, nontrivial EXIF orientation, unavailable
inputs, signed comparison, no clipping and large finite arithmetic.

The original source text says65% for MycB3-CofC with Mjan-CofD. Figure6B appears
consistent, whereas Figure2C appears near75%; the native recipe must quantify
this without treating two representations as independent experiments. Raw
pixel uncertainty is not reported biological SD. The source reports n=3
biological replicates without resolving protein-preparation independence here.
No omitted-partner measurements or exact molar response calibration are supplied
by the inspected material. Keep their sheet cells unknown.
