# 049 implementation handoff

Implemented only the new pure supporting reader and synthetic tests after root
accepted PROPOSAL.md with the four refinements. This does not implement another
axis, a completed A105 grader, paper routing, source acquisition, OCR, a model
call, a native operation, storage, return rendering or annotation-credit transfer.

Owned production and test additions:

* gene_annotation_episode/literature_binding_visual_inputs.py
* tests/test_literature_binding_visual_inputs.py

The reader's request schema is available from binding_visual_arguments_schema().
read_binding_visual_inputs(arguments, read_source=...) is pure: the callback
returns caller-authorized received bytes; the reader records actual Pillow
format/mode/dimensions, source hashes and validated original/crop geometry.
Single-frame PNG/JPEG L/RGB/RGBA only; no implicit EXIF rotation or pixel editing.
RGB conversion and crop mapping must be explicit and reproduce the full actual
wrapper pixel array. No provider metadata is accepted as proof of that mapping.

Each returned interpretation and witness explicitly attributes semantic choices
to the investigating episode. An image witness authenticates only image bytes
and geometry. A text witness checks an exact retained UTF-8 byte span. Neither
check proves scientific attribution or the nominated uncertainty/count meaning.
Literal expression parsing reuses the existing binding reader's grammar and
unit conversions without fabricating a retained table artifact or source receipt.

The exact, ambiguous, unreadable and conflicting states retain all nominated raw
quotes/fragments. Literal n.d. retains its raw text and means only an unavailable
operand in this compatibility schema; no meaning such as nondetected or not
determined is inferred. Other unavailable states never become n.d. Source callback
failures are caught per dependency and preserved on affected witnesses/images;
independent valid cells survive. A failed qualification witness blocks the table
view but leaves valid literal parameter measurements visible, without inventing
a count or uncertainty basis.

Original source/artifact/cell-region locators, not wrapper IDs or expression
ROI variations, own physical identity. Different readings or ligand labels on
one exact canonical locator suppress those operands as conflicting. An unresolved
reading of that same owner prevents an exact wrapper reading being selected
silently. Overlaps are reported and are neither merged nor declared independent.

Output details clarified during implementation:

* Witness results wrap the original witness and add artifact_ref,
  canonical_locator, authentication, interpretation_attribution and error.
  Interpretation and transcription results carry explicit attribution as well.
* Each cell retains mapped_candidates and mapped_fragments, plus the original
  witnesses inside expression. Each parsed measurement is canonical nM.
* The compatibility table keeps its source unit and literal expressions exactly;
  the old reader normalizes these when it reads that table.
* Count witness token boundaries are checked against actual neighboring retained
  text bytes, preventing a selected `3` inside `13` becoming a source count.
* The reader accesses only the existing _measurement/_SCALES helpers read-only.
  A future public literal parser API would remove this private-helper dependency.

## Remaining adapter and integration work

Compatibility status complete means all nominated cells can be represented in
binding_parameter_table_v1. It does not authorize a source reference or certify
scientific correctness. partial_requires_adapter preserves exact usable rows
while explicitly retaining withheld-cell reasons; unavailable has no safe table.

No current storage/episode operation accepts the new reader request or complete
output. A future caller must authorize source ancestry, retain the full result,
retain the derived table as actual bytes with original-image source parents,
and wire a selected native operation plus typed return/rendering. It must carry
withheld states forward: passing only the partial table to the old populate route
would incorrectly lose the difference between unreadable and missing rows.
No such route is claimed implemented here. Existing C7/services/renderer/storage
and all other existing files were left unedited.

## Terminal evidence

Initial isolated command:

    .venv/bin/python -m pytest -q tests/test_literature_binding_visual_inputs.py

Result: 49 passed in 0.74s, exit 0.

Recorded final command and exact output are in terminal_test_evidence.json:

    .venv/bin/python -m pytest -q tests/test_literature_binding_visual_inputs.py tests/test_literature_binding_reader.py tests/test_literature_binding_calculations.py tests/test_literature_binding_model_inputs.py tests/test_literature_binding_models.py

Result: 579 passed in 2.41s, exit 0. Synthetic in-memory fixtures only. No paper,
live provider/model, storage operation or episode runtime was executed.

implementation.patch is a stable full-file additions patch for the production
and test files. MANIFEST.json records SHA-256 and byte lengths for those files,
this handoff, the accepted proposal, the exact terminal evidence and the patch.
The manifest excludes itself to avoid a recursive hash definition.
