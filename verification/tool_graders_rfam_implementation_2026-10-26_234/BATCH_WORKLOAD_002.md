# Additive Rfam batch implementation contract

The original goal remains authoritative. This adds the next workload to
WORKLOADS.md after review of transport234/BATCH_NATIVE_CONTRACT.md; no previous
receipt or permanent decision is replaced. It does not mark Rfam complete.

## Accepted native-table port and exclusive ownership

A fresh worker owns only `gene_annotation_episode/rfam_batch_table.py`,
`tests/test_rfam_batch_table.py`, and a new verification directory ending 238.
Read the complete current Infernal parser and calculator before reusing them.
Do not edit them or the JSON contracts owned by numerical235. No network,
subprocess, model, episode, Store, or acquisition calls in the new module.

Implement transport234's exact closed RfamBatchFileInputIdentity,
RfamBatchTableCapture, and RfamBatchTableParseResult shapes and named numerical
semantics with this explicit additional input:

```
validate_rfam_batch_file_input(input_identity, *, submitted_content: bytes) -> None
populate_rfam_batch_tblout_sheet(content: bytes, *, input_identity, capture,
    submitted_content: bytes, report_membership=None, model_metadata=None) -> dict
```

The validator raises ValueError with a stable code for invalid input; the parser
returns the closed rejected/unsupported/partial/complete result and issue list.
Exact submitted bytes are necessary to validate that the frozen manifest really
describes the submitted file. Hash equality alone is not a sequence/header join.
Validate the exact file SHA256 and length, complete ordered FASTA membership,
unique native first-token names, exact sequences and sequence lengths/hashes,
unique occurrence keys, selection ordinals, original input references and declared
coordinate transformations. Original headers may be null when the existing
selected material did not retain exact header bytes. Do not manufacture them.
The caller supplies one explicit occurrence per selected subject, even when a
subject or its sequence is selected twice. An externally supplied ambiguous file
is rejected for attribution, not silently split or deduplicated.

Use the existing native Infernal table parser and calculator semantics, including
the full saved Infernal sheet. Do not produce invented JSON hits or a second
table grammar. The wrapper adds only authenticated original-occurrence mapping
and complete input population. Validate cmscan, 1.1.5, format 1, original job
filename and original source capture as specified in transport234's proposal.
Custody beyond supplied values is the publication owner's responsibility.

Do not pass original ordinals into Infernal metadata's `occurrence` field.
Preserve metadata indices and the explicit native-name-to-original-occurrence
map. A missing complete model length stays missing; raw score/E/bias/GC, query
span fractions and strand-separated unions remain usable. Model metadata may
only bind with original-model provenance; do not bind a contemporary family
length by accession alone. If that provenance cannot be established from this
format, retain an explicit unbound requirement, do not fabricate it.

The optional report membership extractor has the supplied-data-only signature
`parse_rfam_report_membership(content: bytes, *, capture: dict) -> dict` and
returns the exact source-qualified record in transport234's proposal. Its
capture is the same closed table capture with representation=out. It extracts
actual query names/lengths, reported hit counts, line locators and closure.
It is not a hidden prerequisite for supported table arithmetic. Wrong report
job, partial membership, contradictory counts, duplicate/foreign names and
length conflicts remain explicit. Do not infer report-to-display correspondence.

Root consumes the wrapper in `rfam_batch_publication.py`, saves its full sheet,
and calls `calculate_infernal_search_scores(sheet, parameters={hit_scope:reported})`.
Root will implement requested projections and source-authenticated returns.
Therefore do not introduce a new calculator, final annotation score, return
form, model prompt, or alternative API service in this workload.

## Parallel root workload and handoff

Root owns the additive v2 request accepting an ordered nonempty subject_refs
list, exact generated unique FASTA names/bytes, API submission and recovery,
publication, stored full sheets/calculations, typed projection and receiving
episode validation. The existing v1 single-sequence request remains supported.
No automatic resource or output-format selection is added. A batch request's
selected JSON response is retained as unattributed with an explicit table
acquisition requirement; acquisition of tblout is an episode selection.

The parser's exact function and record contracts are root's dependency, not the
completion of all parser tests. Notify root of any proposed contract change
before implementing it. Root must not mutate the worker's files concurrently.

## Verification and context discipline

Run transport234's full minimum batch verification list, including retained
six-query native output, reordered rows, repeated sequences with distinct
occurrences, duplicate names, complete zero/no-hit input populations, partial
body/rows/footer, file/job conflicts, foreign names, wrong version/mode,
report count conflicts and acquisition-forbidden saved-sheet recalculation.
Preserve native versus synthetic fixture attribution and source hashes.
Use 20 GiB RAM / 4 GiB scratch with no wall-time cap and the bounded runner.

Read the entire original goal before coding. After substantial native/output
study, reread its objective and all sixteen design principles verbatim, then
this contract and transport234's contract before translating evidence to code.
Repeat at closure. Preserve the existing episodes, three construction slots,
typed communication, one observation per own action, current credit formulas,
and independent replay. No literature work, W05, HPC, or local database BLAST.

## Clarification after parser review

The table wrapper additionally retains `supplied_model_metadata` as a finite
JSON object or null. Metadata without original-model provenance stays unbound;
it is not hidden inside a diagnostic. Wrapper issues are closed records with
`code`, `severity` (error|warning), `field` (string|null), `native_query_name`
(string|null), and `source_line` (positive integer|null). Original Infernal
issues remain unchanged inside the sheet. Missing original header/ordinal is
null; a declared non-unchanged sequence transform requires its actual mapping
reference.
