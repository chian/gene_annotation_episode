# B3 populated native sheet verification

This bounded constructor workload is implemented and tested. GenomeComparison
as a scientific service and the full authoritative tool-library goal remain
unfinished. These fixtures are synthetic; no scientific program, service task,
live native result acquisition or episode communication was executed here.

The implemented entry point is `build_native_sheet` in
`gene_annotation_episode/bvbrc_proteome_sheet.py`, with the exact frozen B3
signature. It consumes A result envelopes, B1 values, the supplied NativeJoins
value and explicit representation links. It calls the public saved-data
validators and returns NativeSheetResult. B4 consumes its actual validated
output in the tests. B3 never calls A, B1 or B2 to redo their work.

Only the new builder, `tests/test_bvbrc_proteome_sheet.py`, and this verification
directory were edited by worker169. Shared contracts, schema assets, B2, B4,
historical fixtures, execution, prompts, W05, evidence-axis and literature code
were not edited. PID1056858 was not signaled, stopped, restarted or replaced.

## Inspected paths and authority reset

Read the authoritative attachment verbatim in bounded chunks, repository
AGENTS.md, the permanent tool-grader direction, and the current
C-L206-GenomeComparison progress row. Read proposal001, correction002,
DATA_SHAPES_PROPOSAL_002's relevant closed definitions, the historical filled
sheet and component examples, construction005 and ownership006.

Inspected the complete actual A parser/validator, B0 saved-input validator, B1
readers/indexer, shared saved-sheet validator and B4 calculator. Reviewed the
shared validator's additive raw-claim and representation corrections. Reread
the original objective and all sixteen original design principles after that
substantial examination, before coding, and after the implementation/tests;
then reread the exact B3 contract, witness correction, complete invalid-sequence
count correction and accepted construction/ownership contract. These records
are implementation evidence, not authority to change the user's goal.

## Retained semantics

- Caller-selected primary only; every supplied A envelope and B1/NativeJoins
  value is copied without mutation. Invalid nonprimary envelopes survive.
- Native numbers, decimal lexemes and source fields copy exactly. Invalid JSON
  neighbors do not erase usable cells. Uncertain TSV layouts retain cells but
  cannot supply semantic numerical components to B4.
- Complete invalid `AA-?1` and empty input strings contribute actual symbol
  counts 5 and 0 when their ID occurrence is joined. These are not protein
  lengths or executed denominators. Incomplete identified records can retain
  ID joins with null full symbol counts.
- Original track keys and missing comparison indices remain explicit. Metadata
  links use the joined-result array positions, independently of link_index.
  Separate source assignments remain separate.
- Locator-only execution/occurrence claims remain unqualified. Execution
  denominators and complete membership remain unavailable. Full directional
  attachments are accepted only as absent or explicitly unavailable.
- Representation comparison uses supplied one-to-one ordinal/association
  correspondence. Equal finite decimal values can have different lexemes.
  Actual conflicts from usable pairs take precedence over unrelated unusable
  mappings; bad mappings retain scoped diagnostics and raw requested links.
  Entirely empty maps cannot establish equality, including empty projections.
  Duplicate/self mappings are malformed. Primary values are never replaced or
  counted twice. Extra sources without links receive a correspondence
  requirement without an invented mapping.
- Partial envelope status alone does not imply missing bytes. A complete native
  artifact with an invalid scalar keeps native_invalid_cell; only actual body
  or object incompleteness requests complete bytes. An invalid nonprimary
  envelope with unavailable source facts requests producer execution facts.

## Exact verification results

All runs used `.venv/bin/python -m pytest -q
tests/test_bvbrc_proteome_sheet.py`, with the corresponding JUnit XML path.

| Receipt | Outcome | Interpretation |
| --- | --- | --- |
| pytest_001.log / pytest_001.xml | 61 passed, 1 failed, 11.43 seconds | Malformed A envelope was rejected at the final sheet boundary instead of the initial supplied-contract boundary. Added an explicit envelope-state input check; retained failed receipt unchanged. |
| pytest_002.log / pytest_002.xml | 72 passed, 13.93 seconds | Added duplicate/unresolved joins, invalid/empty subject counts, explicit representation edge cases and metadata tests. |
| pytest_003.log / pytest_003.xml | 72 passed, 13.75 seconds | Final source, including actual completeness-based byte requirements, explicit no-B2-call assertion and truncated joined-input requirements. |

The tests use actual A/B1 functions over synthetic bytes, explicit synthetic B2
handoff values, the complete shared saved-sheet validator and actual B4.
They cover malformed global inputs, wrong sources/digests, invalid nonprimary
envelopes, duplicate requests and identifiers, missing/ambiguous/conflicting
joins, exact copying, source completeness, symbol counts, missing tracks,
metadata row ordering, JSON/TSV reorder/equality/conflicts, empty results,
directional unavailability and saved-sheet parameter recalculation.

After packaged schemas are warmed, the pure-path test rejects file access,
socket creation, subprocess creation, all five B1 reader/indexer calls, A
parsing and B2 construction. B3 construction and B4 recalculation still pass.
No validator is stubbed in any test.

## Filled numerical example

`write_example_001.py` executed successfully and retained the original synthetic
native JSON, two FASTA inputs and parameter bytes with checked source digests,
the exact builder arguments, populated sheet result, two calculated component
results and `NUMERICAL_CHECKS_001.json`. It never overwrites a historical file.

Native identity fractions `.875, .000, .625` produce percentages
`87.5, 0, 62.5` and mean identity `0.5`. Native subject endpoint-difference
fractions `.990, .500, .750` have mean `56/75`, or `0.7466666666666667`.
The explicit joined subset has 3 reference occurrences, 2 subject occurrences,
1 subject with multiple references, 1 excess distinct pair and 1 demonstrated
subject full-sequence group. Identity >=.6 and endpoint fraction >=.7 select
2 rows; changing identity to >=.9 selects 0. Source/arguments/sheet remain
unchanged. Executed denominators and population fractions remain null.

The same sheet digest in both component records is
`68205caa9d9ceb8266af4e51eebb84d9501e2d63af714bc5a3fd7259cb33d640`.

## Remaining work

Root owns composition with actual B2, application/selected-child result binding,
typed return/episode verification and accounting. This worker did not verify
that larger path. Decoded execution/producer occurrence witnesses, retained full
directional reports and original execution membership remain missing interfaces.
Real service artifacts, deployed version/custody evidence, live execution and a
complete GenomeComparison scientific capability are not established here.

Final owned-file and relevant dependency hashes are recorded separately.
