# 049: source-image binding-cell reader proposal

Status: proposal only; no implementation or integration has been made. Root must
acknowledge this interface before coding. No paper, retained paper packet,
actual_observations, private provider history, or live-run state was opened.

## Purpose and ownership

An ordinary investigating episode can inspect a received image through the
existing image.view path and nominate literal table-cell transcriptions. This
one-off pure reader checks bytes, image geometry, declared literal grammar and
known view mappings. It neither looks at pixels with a model itself nor decides
which comparison, parameter meaning, paper, experiment or next action to use.
It is a supporting reader for the existing A105 IC50/reported Hill Kd component,
not another axis, another grader family, a paper classifier, or A101/W05 work.

Exclusive prospective edits:

* NEW gene_annotation_episode/literature_binding_visual_inputs.py
* NEW tests/test_literature_binding_visual_inputs.py
* NEW files in this a105_binding_visual_reader_049 directory

No edits to existing readers, calculators, storage, services, C7, renderer,
operation catalog, model prompts or frozen/base044 files. A later caller adapter
and selected native visual operation need their own integration work.

## Closed callable boundary

Proposed API:

    read_binding_visual_inputs(arguments, *, read_source)
    binding_visual_arguments_schema()

read_source(source_ref, representation) is the existing caller-owned acquisition
boundary. It must authorize received/scope/page ancestry before returning exactly
{artifact_ref, content: bytes}; representation is original or text. The reader
does not authorize parenthood from a provider label, user-supplied artifact name,
filename or MIME claim. It records callback-resolved artifact refs and computes
byte hashes itself. Source receipt, original-document/page attribution and scope
remain the adapter's duties, as in the existing assay reader.

The following are closed structures: all listed fields required, no extras.
Arrays below contain references to declared entries; duplicate IDs are rejected.
Nullable fields accept explicit null, never an inferred default.

    arguments = {
      version: "binding_visual_inputs_v1",
      table_id: nonempty literal label,
      images: [Image],
      context: {subject: Interpretation, state: Interpretation,
                experiment: Interpretation},
      parameter_kind: {value: "ic50" | "reported_hill_kd",
                       witnesses: [Witness]},
      unit: Transcription,
      uncertainty_basis: {value: "fit_to_averaged_curve" |
                           "between_independent_fitted_parameters" | "unknown",
                          witnesses: [Witness]},
      minimum_experiment_count: null | {literal: string, witness: Witness},
      cells: [Cell]
    }

    Image = {image_id: string, source_ref: string,
             original_source_ref: string,
             mapping: null | {original_region: Box,
                               colour_conversion: "preserve" | "rgb"}}
    Interpretation = {value: nonempty literal label, witnesses: [Witness]}
    Witness = TextWitness | ImageWitness
    TextWitness = {kind: "text", source_ref: string,
                   representation: "original" | "text",
                   start: integer, end: integer, quote: string}
    ImageWitness = {kind: "image", image_id: string,
                    region: Box, quote: nonempty string}
    Transcription = {status: "exact" | "ambiguous" | "unreadable" | "conflicting",
                     candidates: [ImageWitness], fragments: [ImageWitness]}
    Cell = {cell_id: string, image_id: string, cell_region: Box,
            ligand: Interpretation, expression: Transcription}
    Box = [x0, y0, x1, y1]  # exact nonnegative ints, half-open stored pixel axes

Every context and ligand interpretation requires at least one witness. The
parameter-kind enum requires at least one witness. A non-unknown uncertainty
basis requires at least one actual footnote/Methods witness; the reader checks
that witness's custody, not that the scientific interpretation follows from it.
An unknown basis may have zero witnesses. A count requires a witnessed positive
integer literal; text witnesses must contain that exact token and image witnesses
must nominate it as the quote. A count is the declared source minimum count, not
an independent-preparation count. It never creates a sampling model.

No number, spread, numerical confidence, quality score, covariance or scientific
default is accepted as a direct argument. Numerical operands come solely from
the selected literal expression/unit/count strings. No SD/SEM meaning is inferred
from a symbol or column label, and no known covariance follows from fit spread.

## Actual image formats and source/view geometry

Initial support is deliberately bounded to Pillow-decoded single-frame PNG and
JPEG with selected mode L, RGB or RGBA. Frame is exactly zero. An image must be
successfully loaded; actual image.format, actual size and actual frame count are
read from bytes. Empty, corrupt, multiframe, unsupported-mode/format images are
structured source failures. EXIF rotation, contrast, resizing, deskew, OCR and
arbitrary affine mapping are unsupported. A PDF must first be rendered through
the existing page operation; this reader accepts the resulting received raster.

If mapping is null, source_ref must equal original_source_ref and all boxes are
in that decoded original image. A wrapper is supported only with an explicit
integer original_region and a bounded preserve or rgb mapping. The reader loads
both original and wrapper bytes, checks dimensions and compares the complete
wrapper pixel bytes with original.crop(original_region), optionally converted
explicitly to RGB. It verifies mode equality after the declared conversion too.
The wrapper cannot be cropped again by an undeclared chain. A nested crop can be
nominated directly against the original if this same actual equality holds.
This accepts actual identity image.view representations and exact lossless crop
views, including a PNG crop of a decoded JPEG; it does not accept recompressed
JPEG crops whose pixels differ. It records the explicit conversion as such.

Each ROI must be a nonempty integer rectangle within the actual image size. A
cell candidate's expression ROI must map inside its canonical cell_region on
the same original. A candidate can use another declared, validated view of that
original; its mapped location is checked, rather than comparing crop-local
coordinates from different views. Unit
and Methods witnesses may lie elsewhere in declared images or retained text.
Source hashes, original/wrapper dimensions, actual format/mode, explicit mapping,
software/Pillow version and canonical original boxes remain in the output.

These checks authenticate which bytes and rectangles were supplied. They do
NOT verify that the image contains the nominated text, that no comparator or
footnote was missed, or that it is scientifically the correct cell. Image quotes
are explicitly attributed to the investigating model's visual interpretation.
Text witnesses alone can be checked as exact UTF-8 byte spans using the existing
assay witness rules. No automatic OCR or pixel-text verification is claimed.

## Transcription and literal parsing

Exact requires precisely one candidate and zero fragments. Ambiguous and
conflicting each require at least two distinct candidate quotes. Unreadable
requires zero candidates and may retain visible fragments. The episode explicitly
chooses these states; the reader never changes an ambiguous state into exact by
choosing a successfully parsed candidate. All candidates and fragments survive.

An exact expression supports the existing reader's full grammar: positive point
number, optional printed comparator >, >=, <, <=, ≥ or ≤; optional ± nonnegative
reported spread only on an uncensored point; or literal n.d. Units are exactly
nM, uM, µM, μM or mM. It normalizes supported numerical rows to nM through the
existing table reader. Approximation signs, intervals, Unicode forms the existing
parser does not support, inconsistent units and other expressions remain raw
with explicit unsupported-expression/unit status; there is no silent repair.

Exact source n.d. alone becomes the existing reader's unreported/null operand.
An unreadable or ambiguous image is never n.d., zero, absent experiment, or an
invented reported row. A literal count must be a complete positive integer token
in its witness; source language and the caller's interpretation define its
minimum-count meaning. An ambiguous count has no numerical count: caller passes
null and retains its source in the other qualification witnesses, pending a
future richer qualification contract if necessary.

## Physical-cell identity and dependence

Each cell has a stable original-coordinate cell_region distinct from its tighter
expression ROI. The reader derives the old visual locator from the actual
original source ref, resolved original artifact ref and mapped cell_region.
Wrapper IDs, candidate list positions and crop-local ROIs never become a new
physical observation. Exact same canonical locator groups the same cell.
Contradictory readings or labels on that locator are retained as a conflict;
equal values at distinct locators remain distinct locations.

Overlapping boxes alone establish neither sameness nor independence. The reader
reports overlaps as unresolved geometry and never merges them, counts them as
replicates or declares independence. Different boxes claimed for the same visual
cell cannot safely prove identity; the episode must explicitly use a common
original cell_region or retain that ambiguity. Identical hashes for separately
named original sources do not prove common scientific provenance. The adapter
must bind alternate views to an actual original before calling this reader.

IC50 and reported Hill Kd remain distinct. The reported parameters are descriptive
printed estimates/limits; a printed threshold does not establish a true-parameter
or confidence bound. Arm/context/ligand attribution is a witnessed episode
interpretation. One table can describe many assays; this reader processes only
the explicitly selected comparison context, and makes no independence claim.

## Closed output and honest existing-reader bridge

    output = {
      version: "binding_visual_extraction_v1",
      table_id, context, parameter_kind, unit, uncertainty_basis,
      minimum_experiment_count,
      images: [ImageResult], cells: [CellResult], source_refs: [string],
      geometry_overlaps: [{left_cell_id, right_cell_id}],
      compatibility: {
        status: "complete" | "partial_requires_adapter" | "unavailable",
        table: null | binding_parameter_table_v1,
        included_cell_ids: [string], withheld_cell_ids: [string],
        reasons: ["withheld_transcriptions" | "physical_cell_conflict" |
                  "source_unavailable" | "unit_not_exact" |
                  "unsupported_expression" | "unsupported_unit" |
                  "no_representable_cells"]
      }
    }

ImageResult contains only image_id, source_ref, artifact_ref, byte_sha256,
original_source_ref, original_artifact_ref, original_byte_sha256, actual_format,
actual_mode, width, height, frame_count, mapping, pillow_version, and error.
For a failed image, unavailable measured fields are null and error is
{code, field}; independent valid images/cells remain available.

CellResult contains exactly cell_id, canonical_locator (nullable), subject,
state, experiment, ligand (each the original witnessed Interpretation),
expression (the complete original Transcription), mapped_candidates,
mapped_fragments (arrays of {witness, original_region}),
physical_cell_key (nullable), parse_status, parsed_measurement (nullable), and
error (nullable {code, field}). parse_status is parsed, reported_unavailable,
ambiguous, unreadable, conflicting, unsupported_expression, unsupported_unit or
source_unavailable. parsed_measurement contains only value, relation,
reported_spread and unit from the existing parser; there is no uncertainty model
or scoring value. Physical conflicts keep all candidates and suppress any
apparently exact chosen operand.

The compatibility table has exactly the old required keys: version, table_id,
parameter_kind, unit, uncertainty_basis, minimum_experiment_count, rows; each row
has subject,state,experiment,ligand,expression,locator. It includes only exact,
supported, nonconflicting source cells and uses the canonical original locator.
It may contain a true exact n.d. row. It cannot encode the withheld states.
Complete means all nominated cells and shared unit are representable. Partial
means some exact cells survive but at least one nomination is withheld. A failed
or ambiguous shared unit makes the compatibility table null; count/basis remain
their explicitly supplied unknown values, with source witnesses retained.

This pure function does not fabricate a retained JSON source/artifact ref or call
populate. Future adapter work must retain this full output, serialize the
derived table as a new retained source with actual original-image ancestry, and
preserve withheld-cell reasons through typed return/rendering. Existing storage
can ingest the table bytes only after that custody work. It currently does NOT
accept this output or distinguish omitted unreadable cells from missing arms.
Therefore partial_requires_adapter is deliberately not advertised as safe for
the existing bare populate route. Exact partial measurements remain available
to the investigating episode even when no current calculator can consume the
complete transcription result. A later targeted consumer extension is needed
for those reasons; that is outside this file ownership.

## Synthetic verification planned after acknowledgement

Tests will generate small PNG/JPEG fixtures with arbitrary synthetic labels and
numbers (no042 operands), and call the pure reader with in-memory byte sources.
They will check closed fields/types, byte-derived image facts, valid/bad boxes,
unsupported/corrupt/multiframe inputs, actual crop equality and RGB conversion,
canonical identity across crops, overlapping-but-not-merged cells, conflicts,
units/limits/spread/n.d., unsupported syntax, partial exact arm retention, the
four transcription states, witness byte mismatch, witnessed count/basis, no
fabricated sampling model, and round-trip old-reader compatibility for complete
tables. Partial outputs must retain raw candidates and explicitly refuse the
unqualified old route. Tests cannot prove visual transcription correctness.

## Inspection record

Read the full active goal attachment, root AGENTS, W04 amendment, binding reader,
storage, contracts, binding calculations, binding model inputs, binding models,
binding model storage, assay inputs
(including _Sources), and image_evidence implementation. Inspected image.view
execution/source creation and image input resolution in tools.py. The existing
image preparation verifies pixel preservation for its identity PNG display;
resolve_image_input checks selected-view identity and actual PNG dimensions.
Neither provides source-text transcription. Latest039 and040 direction was read
last before writing this proposal. No test or production operation was run.
