# HMMER decoder boundary review 514

Read-only inspection of the new R2 HMMER2 ASCII/HMMER3 binary decoding boundary.
This record is implementation evidence, not goal authority or a scope amendment.
No production/test file was edited by this reviewer. No application/scientific
module was imported, no test or native command was run, and no network request
was made. Findings below are source-derived triggers, not executed reproductions.

The full original user attachment and actual AGENTS.md were read. GOAL.md was
not read. The attachment objective and all ten operating principles were reread
after inspection calls; finalized 508 IMPLEMENTATION_CONTRACT.md and 511
CODING_HANDOFF_001.md were reread before this report.

## Inspected

- Complete `hmmer_model_binary.py`, `hmmer_model_legacy.py`, and
  `hmmer_model_source_cells.py`.
- Public new-format dispatch, occurrence validation, issue vocabulary and common
  record helpers in `hmmer_model_data.py`; the unchanged ASCII grammar was not
  re-audited in full.
- Complete `hmmer_model_calculations.py`, `hmmer_artifact_calculations.py`,
  `hmmer_statistics_calculations.py`, and `hmmer_emission_calculations.py`.
- Retained HMMER 3.4 source: complete binary writer/reader, HMMER2 compatibility
  reader, binary string reader, H2 scalar conversion helper, ASCII multiline COM
  writer; complete `h2_io.c`; relevant model flags/storage declarations and
  ASCII COM-reading branch.
- Header/body examples in the retained native ASCII and legacy2 conversion
  fixtures. Test names for relevant new saved-cell cases were inspected only;
  their existence is not execution evidence.

The reviewed code keeps the two new formats in the common record/cell sheet;
no separate entropy, mass, KL or confidence policy was introduced by their
decoders. Binary framing stops after lost boundaries or recognized stream
layout changes. H2 NULT slots remain generic, full transition labels are
retained, and terminal/initial H2 topology limitations reach shared components.
Statistics and consensus explicitly qualify comparisons to H3 conversion.
Historical unsupported extraction envelopes are not re-extracted by the
reviewed calculators.

## Concrete findings sent to owner 511

1. **Invalid NULE validation was not authoritative for dependent cells.**
   In `validate_hmmer_probability_cell`, an amino NULE cell with a
   helper-consistent uniform denominator 4 instead of actual K=20 failed its
   own recursive validation, but a dependent helper-consistent emission could
   still become present. The function recorded the invalid reference and then
   overwrote the result after source-cell equality. All shared probability
   consumers were affected. Expected: incompatible NULE makes a finite
   dependent score incompatible. Owner accepted; source now contains an early
   return for an incompatible recursive reference. No repair test was run here.

2. **Invalid binary counts were classified as missing.**
   `_Calculator.count` recognized only ASCII header errors. Actual binary
   NSEQ=-2 or invalid/nonfinite EFFN produces common null plus
   `binary_native_value_invalid`, but was published as missing, like native
   sentinel -1. Expected: invalid is incompatible; sentinel -1 remains missing.
   Owner accepted; source now recognizes the binary error for the corresponding
   count header. No repair test was run here.

3. **Unsupported binary tails were classified as established corruption.**
   Artifact `_Calculator.binary_content` omitted `binary_layout_unsupported`
   from its unavailable-layout guard. A complete valid model followed by four
   unknown magic bytes retained its prefix but returned invalid/fail. Expected
   under finalized 508: unknown/unknown for the unestablished layout. Source
   now includes that issue in the guard. No repair test was run here.

4. **Binary cell byte locators were not tied to their actual source slots.**
   Binary validation checked width and containment within the record only.
   Changing the first match cell bounds from record-start+[16,20) to
   record-start+[20,24), while retaining its raw bytes/probability, passed the
   same scalar decoder/equality check. Duplicate/overlapping cell bounds also
   passed. Expected: field/position/cell and retained bounds must agree with
   the declared binary layout, including supported partial prefixes. Sent to
   owner; any subsequent repair was not inspected by this review.

5. **Binary common counts were not joined back to their native evidence.**
   With raw NSEQ=3, native NSEQ.value=3 and projected header NSEQ=3 unchanged,
   changing only `sequence_count` to 7 was accepted by `_Calculator.count` and
   altered the ratio. `_representation_encoding` checked native-field shape,
   not this relationship. Expected: common NSEQ/EFFN must agree with decoded
   native values/sentinel semantics. This finding is limited to the newly added
   binary source-to-common count join. Sent to owner; any subsequent repair was
   not inspected by this review.

6. **Duplicate NULE headers became absent-reference results.**
   Actual duplicate H2 NULE headers make `_LegacyReader.single` return null;
   finite dependent cells and their shared validation then report missing,
   despite `header_duplicate` establishing an ambiguous/malformed reference.
   Expected: finite dependent components incompatible, original duplicate
   headers retained; truly absent NULE remains missing and `*` remains an
   independent structural zero. Sent to owners 511 and 513; any subsequent
   repair was not inspected by this review.

7. **Equivalent command logs compare changed across binary/ASCII metadata.**
   `_optional_meaning` falls back to raw COM token lists. Native ASCII emits
   `COM [1] foo` and `COM [2] bar`; its reader stores `foo\nbar`; binary retains
   that string, projected as one header. Thus numbered ASCII token rows differ
   from the unnumbered binary projection even when their ordered command log
   means the same thing. Expected: compare source-aware ordered command-log
   meaning while preserving both raw representations. Sent to owner; any
   subsequent repair was not inspected by this review.

The already assigned exact-zero NULE defect was not counted again. Its revised
source helper was seen retaining nominal zero while refusing a usable finite
log-odds probability; that observation is not a test result.

## Unverified

This review does not establish executed numerical results, authentic native
format coverage, saved replay success, selected producer/publication/requested
return integration, or live-resource completion. Root owns the integrated
verification. Remaining source, format, resource, message and alignment-map
obligations from the original goal are not closed by this report.
