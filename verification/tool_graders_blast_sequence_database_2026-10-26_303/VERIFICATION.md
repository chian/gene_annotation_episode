# Shared sequence-database fields and deterministic functions

The deliverable is the implemented field definitions and functions described in
[FIELDS_AND_FUNCTIONS.md](FIELDS_AND_FUNCTIONS.md), with the exact frozen shapes
from CONTRACT_001 and its two additive source ports. Filled sheets are retained
verification outputs, not a replacement for those definitions and functions.

`gene_annotation_episode/blast_sequence_database.py` exports:

- `populate_blast_sequence_database_sheet(search, *, report_source,
  search_binding, query_binding, reference_metadata, description_bindings,
  sequence_identity_bindings, target_context=None, database_profile=None)`;
- `calculate_blast_sequence_database_components(sheet, *, model=None)`.

The population function copies the complete native search and explicit supplied
relationships into `blast_sequence_database_result_sheet_v1`. The separate
calculator returns `blast_sequence_database_result_components_v1`, containing
the existing database numerical sheet, conditional function weights, full and
selected coordinate context, selected coverage, original row identities and
source-qualified issues. Both functions are pure supplied-data operations.

The only shared legacy change is the approved optional geometry/context path in
`blast_database_grader.py`. Null arguments retain prior values and schema.
Qualified geometry reaches both correspondence and sequence-identity links,
while execution identity remains PSI/DELTA where selected. RPS/profile and VDB
targets cannot enter sequence-population weighting. The exact source of
`calculate_database_probabilities` is unchanged: see
[formula_comparison.json](formula_comparison.json).

The consumer uses producer 304's exact decompressed member digest and producer
307's exact original table layout. It distinguishes absent member evidence from
a conflicting digest and never substitutes the container digest. It does not
guess table format or delimiter. Native JSON indices, member ordinals, full
SearchKeys, original malformed-sibling ordinals, table line membership and
native singular description pointers remain checked before legacy association.
Report indices are checked against exact native JSON report pointers; tables
require their original nonarchive identity and exact reconstructed SearchKey.

## Final focused verification

[check005/command.json](check005/command.json) records the actual command using
the repository `.venv/bin/python` and existing `local_jobs`. The selected files
are the two new test modules, existing database and explicit-association tests,
BLAST and BV-BRC grader consumers, native coordinate conventions and collection
tests. The result is **454 passed, one warning, 1.85 seconds**. The warning is the
intentional duplicate-name ZIP fixture. Full stdout, stderr, JUnit, local-job
receipt and before/after source hashes are retained in `check005/`.

The 33 scoped source/test hashes are identical before and after this final run.
This is scoped evidence, not a stable-source assertion over the entire shared
checkout. New cases cover incorrect report indices even when two JSON reports
are identical, valid nonzero and object-form indices, invented table member and
report indices, and noncanonical iteration-array indices.

The suite also verifies all ordinary-program geometry conflicts, compatible
PSI/DELTA geometry with real executable identity, sequence/PSSM/MSA bindings,
wrong same-length operands, absent digest/master/query inputs, selected/full
denominators, original malformed HSP ordinals, member/round cross-link rejection,
metadata and census qualification, original precision, no-hit distinctions,
table layout missingness/conflict, detached native-context tampering and saved
JSON/table recalculation while file, socket and process operations are forbidden.

[check005/receipt.json](check005/receipt.json) records 20 GiB RAM
(`memory.max=21474836480`), swap zero, 4 GiB scratch policy
(`4294967296`), and no wall cap (`runtime_max=infinity`). The service lasted
2.343820292 seconds and observed 450560 scratch bytes. Scratch enforcement is
the existing visible-allocated-byte monitor with possible overshoot, plus a
per-file hard RLIMIT_FSIZE; this is not a filesystem sandbox.

## Actual complete verification outputs

The current outputs are in
[example_export003/EXAMPLE_SUMMARY.json](example_export003/EXAMPLE_SUMMARY.json)
and `example_export003/examples/`: six complete populated sheets, their complete
default and temperature-2 calculations, and twenty complete retained paired
format/geometry examples. Every output was written inside the monitored local
job directory. The exporter exited zero; its eight scoped before/after hashes
match. Its receipt records the same 20 GiB/4 GiB/no-wall policy, 0.645204045
service seconds and 2600960 observed scratch bytes.

The synthetic PSI example has native bit scores 20 and 18. At temperature 1,
kernel masses are F=1 and G=0.25, unadjusted weights F=0.8 and G=0.2. Explicit
matching population counts F=200 and G=50 produce adjusted weights 0.5/0.5.
At temperature 2, unadjusted values are approximately 2/3 and 1/3. The first
hit's paired query union is four amino acids: full coverage 4/12, selected
coverage 4/8=0.5 for interval [2,10), reference coverage 4/10. The overlap test
counts six distinct query positions once, giving 6/8=0.75. A malformed first
native HSP preserves the later HSP's original ordinal 1 and observed union 4,
with complete coverage explicitly null.

The retained NCBI archive is the existing
`verification/w04_blast_graders_2026-10-24_001/live_api/result.body` (2911 bytes),
not a new request. Its container SHA-256 is
`38908947ffab7a09a8260c6c6933b53cd35c066a3630e5e072c61be0a51c771f`.
Original member ordinal 1, `DTKE1D4G016_1.json` (12592 bytes), has SHA-256
`e343568a2833a49ce7667779b8e9763cf9cb0229d3f24893a26cbb643e40bbe0`.
All seven hits remain: maximum bit scores are 527.709, 38.1206, 32.3426,
31.9574, 31.5722, 31.187 and 31.187. The first has 253 identical pairs and
reference coverage 1. Query full/selected identity, functions and census were
deliberately left unavailable because they were not supplied as authenticated
bindings; no numerical function weighting or full-query coverage is invented.

The twenty paired artifacts come from the retained 293 native-fixture manifest.
Their bytes and hashes are checked by the exporter. Their pairwise mode remains
unchanged and they only verify shared format/geometry. For example, native
blastx reverse JSON endpoints 3..242 with frame -3 and tabular endpoints 242..3
both represent 240 nucleotide positions and 80 paired amino-acid columns.
Native bit-score precision remains 170.629 in JSON and 170 in the table.
Synthetic PSI/DELTA source contexts and metadata are explicitly labeled; these
paired artifacts are not relabeled as real PSI/DELTA database experiments.

## Preserved earlier receipts and limits

- `check001` retained a collection error caused by pytest's reserved `request`
  parameter name; the new test parameter was renamed.
- `check002` ran the broader existing consumer/workflow set to natural
  completion: 435 passed and one new floating-point literal assertion failed
  after 1113.66 pytest seconds. The test now uses approximate equality for
  normalized thirds; the mathematical model was not changed. The existing
  workflow tests passed. Four source snapshots in `source_used/` do not prove
  stable provenance of that whole concurrent checkout; this earlier run is not
  claimed as final whole-workflow integration validation.
- `check003` retained 437 passed, one warning; `check004` retained 445 passed,
  one warning. Later source-identity counterexamples produced final `check005`.
- Top-level `examples/` and `EXAMPLE_SUMMARY.json` belong to export001. That
  first exporter wrote outside its monitored job directory. Export002 corrected
  output placement; export003 is the current source revision. Earlier outputs
  and receipts remain historical facts and are not silently overwritten.

No new database BLAST, API or HPC search or software installation was performed.
This task does not establish authentic PSI/DELTA native execution, iteration
aggregation, HPC deployment, publication, typed episode-return delivery, or
completion of any entire scientific mode. Existing consumer regressions are
separate from these unfinished paths. Acquisition still owns authentication of
artifact references, actual sequence bytes and supplied provenance records.

Only the four authorized production/test paths and this verification directory
were edited by this worker. Collector digest/layout changes belong to 304/307.
The tool inventory, permanent contracts, episodes, W05 and literature work were
not edited. Original objective and all sixteen design principles were reread
verbatim after substantive source/native study, followed by the exact frozen
shared port, contract and addenda before handoff.
