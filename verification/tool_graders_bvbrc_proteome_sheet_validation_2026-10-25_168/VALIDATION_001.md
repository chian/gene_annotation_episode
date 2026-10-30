# Saved GenomeComparison sheet validation receipt 001

This is an implementation receipt for saved-data validation. It does not change
the authoritative goal, proposal001, correction002, frozen schema, historical
filled examples, B0/A implementation, original verification process 161, or any
scientific completion claim. Only this worker's three new implementation/test
files and this verification directory were written.

The full original objective and all sixteen principles were read verbatim at
entry, after complete source inspection before implementation, and again before
this receipt. Proposal001, correction002, SHEET_VALIDATION_004, B4_FREEZE_003 and
B1_PARAMETER_SOURCES_002 were read in full. The existing A native contracts, B0
data contracts, B1 input readers and B4 calculator were inspected completely.
The relevant fixed GenomeComparison inventory row was inspected, not edited.

The original constraints remain controlling:

> Native-output parsers, metadata extractors and calculators operate on supplied data. They make no network requests, submit no jobs, invoke no LLM and choose no resource.

> Measured zero, missing, not measured, failed, truncated and incompatible are different states.

> Do not join independently sorted lists, pick an arbitrary first record or infer an accession relationship merely from a shared taxon.

> The retained artifact may be large. The episode-facing projection should be small and specific.

Installed public functions are `proteome_sheet_schema(name)` and
`validate_proteome_sheet_data(name, value)`. Entry points are NativeSheet,
NativeSheetResult, NativeCalculationParameters, NativeComponents and
NativeComponentsResult. At root's explicit request, NativeJoins and
NativeJoinsResult additionally validate relationships represented in the saved
join object; the input/projection/metadata context is checked when that object
is embedded in NativeSheet. No standalone join object is claimed to contain
absent source evidence. Errors retain ProteomeDataError(code, path); returns
and schemas are detached copies.

The schema asset is byte-identical to DATA_SHAPES_PROPOSAL_002.json, SHA256
739ee63e0e6eea56398c8482a1143dec8b7f7f073041de3edfa4a06af654d9ae. All 33 existing
B0 definitions and all 16 A definitions compare equal. No formula language or
runtime acquisition is introduced. Static packaged schemas may be loaded;
input artifact IO is never performed by validation.

NativeSheet validates each retained native projection once with A and each
retained index/inventory/snapshot once with B0. It validates primary identity,
exact native cell copies, row/track populations, original input mapping,
declared operand/metadata links, retained occurrence bounds, sequence groups,
table-layout qualification and explicit alternate representations. Indexes for
native links, execution links and metadata identities avoid repeated full-array
searches per joined field. It does not create or choose a join.

Root clarified two identity-local details during implementation, without changing
the frozen shapes: a usable exact ID may link a retained occurrence even when
its sequence is incomplete/invalid; an unrelated invalid metadata cell does not
erase a valid exact identity. A complete normalized illegal string AA-?1 keeps
symbol count 5 and an empty complete string keeps count 0. Both remain invalid
sequences and are excluded from valid protein-length comparisons and sequence
groups. Incomplete strings retain missing full counts. This follows B1
correction002 and the distinct B3 symbol-count meaning.

Locator-only exact-execution and producer-occurrence claims cannot supply an
admitted proof. Raw requested claims survive separately. Exact execution
denominators and complete-executed membership remain unavailable. Full reports
accept only None or an unavailable attachment with zero reports/operand links
and a retained requirement. The missing real witness/report interfaces remain
unfinished full-goal work.

NativeComponents validation checks selected-track/association identities,
parameter domains, source-field references, array count partitions, usable and
unknown states, declared summary membership and ratio operand copies. It does
not recompute a mean, percentage or threshold decision. A standalone component
contains only a source-sheet digest: validation checks its syntax and preserves
it but cannot compare it to a sheet that was not supplied. B4 computes the
actual digest and verifies its numerical formulas separately.

Actual checks:

- First own suite: 90 passed, 2 failed because a new synthetic metadata fixture
  used query_source_field instead of frozen query_source. The fixture was
  corrected; no contract was weakened. The following own suite had 92 passes.
- Expanded own suite: 100 passed in 3.12 seconds. The preserved original filled
  sheet retains fractions [.875, 0, .875] and unknown exact-input denominators;
  original independent components retain comp4 identity mean .4375. These are
  synthetic contract examples, not new service measurements.
- Own suite plus actual B4 consumer: 154 passed in 6.87 seconds after final
  indexing/exact-copy changes.
- Final recorded command, pytest_001.log/xml: 485 passed in 10.25 seconds across
  this worker's 100 tests, B4's 54 tests and the existing A/B0/B1 tests. The command
  is recorded in RECEIPT_001.json. It exited successfully.
- Adversarial tests cover copied values/source fields/keys, duplicate tracks,
  malformed scalars, denominator promotion, false completeness, input occurrence
  and metadata relationships, duplicate/cross-input IDs, unavailable witnesses,
  partial/invalid neighbors, table layout and alternate-representation conflicts.
- A validation test blocks file IO, sockets, subprocesses, native/input parsers
  and the calculator, and spies on A/B0 calls: each saved part is validated once.

The final shared test run exercises supplied synthetic/native-format fixture
paths and deterministic saved-sheet recalculation. This task performed no live
GenomeComparison execution, no acquisition, no Store access, no job submission,
no model call, no scientific process launch and no episode communication.
Production adapter/publication binding, package-data installation, actual native
service artifacts, execution/occurrence witness decoding and full directional
report parsing remain outside this delivered validation boundary. Root and the
separate B2/B3 owners retain their work. The full goal is not complete.
