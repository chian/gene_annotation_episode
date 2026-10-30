# Rfam native batch table adapter verification

This additive receipt covers the independently assigned pure native-table
workload only. It does not close the Rfam inventory row or claim new live
execution or complete episode communication.

## Implemented boundary

Owned production file: `gene_annotation_episode/rfam_batch_table.py`.
Owned tests: `tests/test_rfam_batch_table.py`.
No existing Infernal parser, calculator, JSON contract, permanent decision,
historical receipt, shared service, publication, or typed-return file was edited.

The three exported callables are:

```python
validate_rfam_batch_file_input(input_identity, *, submitted_content: bytes) -> None
populate_rfam_batch_tblout_sheet(content: bytes, *, input_identity, capture,
    submitted_content: bytes, report_membership=None, model_metadata=None) -> dict
parse_rfam_report_membership(content: bytes, *, capture: dict) -> dict
```

The file validator checks the exact complete file bytes and SHA256; complete
ordered FASTA membership; unique first-token native names; exact case-preserving
sequence bytes, lengths and hashes; unique occurrence keys; ordered selection
ordinals; nonempty original references; and declared transformation/mapping
references. Original headers and original ordinals remain null when not known.
Repeated subjects, original records, and identical sequences retain distinct
selection occurrences. Duplicate native names are rejected for attribution.
Unheaded files, unsupported sequence symbols, and sequence whitespace are not
silently repaired or renamed.

The wrapper validates supplied capture hashes, original job/file/submission
relations, native query filename, cmscan 1.1.5 SCAN declarations, and native
format-1 header. It calls `populate_infernal_search_sheet` directly, retains its
full sheet unchanged, and creates an explicit metadata-index-to-occurrence
mapping. Original ordinals are never placed into Infernal metadata's unresolved
`occurrence` field. Actual native row grammar and numerical calculations are
not duplicated.

An HTTP body ending is insufficient to establish native completion. If the
single terminal `# [ok]` is absent or misplaced, the wrapper supplies
`complete=False` to the existing Infernal reader. Missing native profile fields
remain partial; conflicting profile values are unsupported. Original job/file
conflicts reject attribution. Independent valid numerical cells survive partial
rows and bodies. Foreign native query rows remain in the full sheet without an
invented occurrence binding, and qualify the complete population as unknown.

As agreed with root and recorded in the additive contract clarification,
`supplied_model_metadata` is a separate finite-JSON object or null. This format
does not identify the original model digest/release, so supplied family lengths
are retained unbound and `model_metadata=None` reaches Infernal. The wrapper
does not replace a missing model denominator. Wrapper issues are closed records
with `code`, `severity`, `field`, `native_query_name`, and `source_line`; the
exported enum is `RFAM_BATCH_TABLE_ISSUE_CODES`. Native issues stay unchanged
inside the saved Infernal sheet.

## Numerical meanings

| Field | Source/calculation | Units and population | Missing behavior |
| --- | --- | --- | --- |
| `submitted_length_nt` | Exact supplied FASTA sequence symbol count | nt, one selected input occurrence | Invalid manifests reject attribution |
| `reported_row_count` | Count of retained Infernal rows with the proven unique native query name | Native row representations, one original occurrence; no independence claim | Positive observed counts survive partial populations; absent rows are null unless native/input/report completeness permits zero |
| `reported_set_complete` | Complete captured native stream, valid profile, retained row population, original input membership, and optional report agreement | Boolean qualification of reported rows under original settings | False for incomplete or contradictory population information |
| Report `length_nt` | Native `Query: name [L=n]` | nt, one report query | Invalid/missing query declarations remain issues |
| Report `reported_hit_count` | Native `Total CM hits reported:` integer | Native CM hit representations, one report query | Null for absent, invalid or duplicate count declarations |
| Source line fields | One-based actual lines of query/count/closure markers | Source locators, not scientific scores | Missing closure/count lines remain null |

Score, E-value, bias, GC, model/query spans, denominators, and strand-separated
unions use the unchanged definitions in `infernal_search_grader.py`. The wrapper
adds no score, model probability, annotation aggregation, or credit observation.
Zero reported rows means no match reported under retained thresholds; it does
not establish biological absence. A report is optional and is never acquired
by either parser. Its supplied names, lengths, counts, source identity and
closure are checked; its display strings are not interpreted here.

## Retained native example

The native source is the original six-query job retained at
`verification/tool_graders_rfam_transport_2026-10-26_234/live/multi`.
No file from that directory was modified and no new service request was sent.

- Original submitted file SHA256:
  `4dc1529db76f089ec36caf8f3d176028d3bb5c828a1d04bfd130e72f92f515f4`.
- Original native table SHA256:
  `46b3e1c6554f1f20d7869e447298beb782ad2cf6735196bd11a39be80e5fad25`.
- All native source and generated artifact hashes are recorded in
  `examples_001/receipt.json` and `examples_001/examples/manifest.json`.

| Native query | Score bits | E-value | Query span/length nt | Query fraction | Model fraction | Strand |
| --- | ---: | ---: | --- | ---: | --- | --- |
| rfam_example_original | 104.6 | 1.4e-24 | 119/119 | 1.0 | null | + |
| rfam_example_repeat | 104.6 | 1.4e-24 | 119/119 | 1.0 | null | + |
| rfam_example_reverse_complement | 104.6 | 1.4e-24 | 119/119 | 1.0 | null | - |
| rfam_example_prefix70 | 51.3 | 9.5e-11 | 70/70 | 1.0 | null | + |
| rfam_example_insertion | 95.5 | 3.5e-22 | 120/120 | 1.0 | null | + |
| rfam_example_deletion | 95.2 | 4e-22 | 118/118 | 1.0 | null | + |

GC values are respectively .49/.49/.49/.50/.48/.48; all native bias values are
0.0 bits. Model spans are 120/120/120/71/120/120 positions. The prefix retains
native `3'` truncation and pass 3. The repeated sequences retain different
metadata indices 0 and 1 and different original occurrence keys. Each original
query has one reported table row. The model fractions remain null because
full original model lengths are unavailable, so the numerical sheet is partial
even though the reported row population is complete.

`examples_001/examples` contains the complete native input identity, capture,
report membership, parser result, Infernal sheet, and separate reported/included
calculator outputs. The sheet was saved and reloaded before calculation.
Socket construction, connection creation, and subprocess launch were forbidden
during parsing and recalculation. Changing `hit_scope` left the saved sheet and
per-hit measurements unchanged; all native hits here have inclusion `!`.

## Verification performed

`run_003` passed **78 tests**. Earlier additive receipts remain in `run_001`
(74 passed) and `run_002` (78 passed). `examples_001` separately verified and
saved the filled native numerical example. All runs used the existing
`run_local_job` runner with 20 GiB RAM, 4 GiB scratch, and no wall-time cap.
Receipts record actual enforcement metadata, source hashes, stdout and stderr.
Scratch enforcement retains the existing monitored-allocation limitation and
hard per-file limit. Source hashes were unchanged during each run.

Coverage includes retained native six-query output and original file hashes;
exact shared Infernal sheet equality; row reordering; equal sequences and
repeated original subjects with distinct selection occurrences; duplicate native
names; full input populations containing a no-hit occurrence; complete zero
tables; partial body, footer, declaration, row and numeric cell cases; original
job/file/source conflicts; foreign native names; wrong version, program, mode,
format and job filename; sequence length/hash and coordinate-boundary conflicts;
duplicate/overlapping rows without double-counted unions; optional report
membership with source lines; report count/length/name/file/job/closure conflicts;
metadata provenance missing/invalid; and acquisition-forbidden saved replay.
All altered tables/reports and no-hit/zero fixtures are explicitly synthetic.

The original goal was read in full before implementation. Its objective and
all sixteen principles, plus both exact batch contracts, were read verbatim
after native-output study and again at closure, including root's additive
metadata/issue clarification. Complete Infernal reader/calculator sources and
the BLAST scoring-sheet example were reviewed. The current root-owned service,
publisher, composed table calculator, and typed projection consumers were
reviewed for interface compatibility; the observed in-progress publisher/view
calculator-shape mismatch was reported to root without editing shared files.

## Handoff and limits

Root owns selected-file POST, original-handle recovery/fetch, publication,
typed projections, receiving episode validation, and shared accounting. This
worker did not execute that complete communication path. A receiving adapter
must qualify its population using the wrapper's `reported_set_complete`,
because optional report contradictions and foreign rows are additional facts
outside the shared Infernal calculator's table-only view. Actual original
reference/mapping custody and report-source custody remain the caller's duty.

No new live Rfam submission, external acquisition, literature work, W05 change,
HPC job, local database BLAST, episode loop, model prompt, or credit change was
performed. Original model provenance/lengths and rich report alignment parsing
remain outside this table-only adapter. No whole-tool completion is claimed.
