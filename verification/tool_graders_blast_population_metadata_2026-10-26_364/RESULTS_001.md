# U06 workload B: supplied-source population metadata

Implemented the accepted packet 361 ports and Addenda 001/002. Root owns U06
acceptance/accounting; C owns actual worker/iteration/typed-return integration.
This packet does not claim a live database deployment or completed U06 route.

## Files and interfaces

Production changes are confined to:

- New `gene_annotation_episode/native_blast_database_population_metadata.py`.
- `gene_annotation_episode/native_blast_database_metadata.py`.
- `gene_annotation_episode/native_blast_standard_database_metadata.py`.
- `gene_annotation_episode/native_blast_standard_database_contracts.py`.

New tests are in `tests/test_native_blast_database_population_metadata.py`.
The only old test change is the root-authorized one-line v3 registry tuple in
`test_native_blast_database_metadata.py`; see OWNERSHIP_EXCEPTION_001.md.
No old scientific expectation, VDB contract, prompt, controller, status row or
tally was changed by B.

The exact new public signatures are:

```python
native_blast_database_sequence_population_metadata_schema() -> dict
extract_native_blast_database_population_associations(
    *, search, prepared_inputs, source_records, database_profile
) -> dict
validate_native_blast_database_population_associations(
    association_inputs, *, search, prepared_inputs, source_records, database_profile
) -> list[dict]
```

The schema is exactly sequence metadata v2 plus the required per-search
database_population_associations list, using the accepted v3 tuple. Extraction
returns the declared `native_blast_database_population_associations_v1` object
with `associations` and existing-shaped `issues`. The saved validator returns a
detached unchanged list. It invokes no metadata extraction/population, native
parser, numerical calculation, external source read or executable.

Both native metadata routes retain the original JSON source roots/pointers,
original metadata payload root, original captured bundle and original selected
manifest. New v3 fields never appear in old v1/v2 envelopes. Original report
source_ref is forwarded only for a v3 sequence sheet. Before the iteration call,
the native adapter removes the new field from ordinary sequence_metadata rows
and supplies the separate `{search_key, associations}` mapping unchanged.

SOURCE_RECORD_SELECTION_001.md and additive 002 specify exact deterministic
record selection, original wire versus resolved provenance, saved validation,
and C's sealed capture checks. They were sent to root and C. The private shared
search-selection helper is `_population_search_units(search, prepared, records)`.

## Concrete numerical examples

The deliberately synthetic report uses two proved full target sequences,
functions F/G, bit scores 20/18, and a separately supplied JSON census with
N=110, F=100, G=10. The native operand `/selected/db/target` stays unchanged;
the manifest and census semantic database `target` stays unchanged. The supplied
assertion pins that operand, original manifest digest, semantic identity, and
original census digest/size/pointer.

| Saved inputs / calculation | Unadjusted F,G | Representation-adjusted F,G |
| --- | --- | --- |
| Qualified source assertion, T=1 | 0.8, 0.2 | 2/7, 5/7 |
| Same saved inner sheet, T=2 | 2/3, 1/3 | 1/6, 5/6 |
| Missing source/pointer, wrong manifest/operand, or report-source alias | native function weights preserved where reference metadata is available | null |
| Explicit empty association list with path/name mismatch | 0.8, 0.2 | null |

The census fractions 10/11 and 1/11 remain different measurements from adjusted
weights. The new relation is a source-asserted population identity qualification;
it is not confidence, external verification, annotation credit or truth.

Actual filled output is retained under
`final_007/temporary/pytest/test_population_source_asserti0/` and the five
`test_all_standard_programs_keep*` directories: supplied inputs, full sheets and
components. These files were written by actual passing tests. Their envelopes
and assertions are synthetic; the test file labels them accordingly.

## Checks actually run

Every test command was executed by the project `.venv/bin/python -B` through
`local_jobs.run_local_job`, with 20 GiB RAM, 4 GiB scratch, wall_seconds=None,
an owned small run directory and owned temporary directory. Each run retains
`command.json`, `receipt.json`, `stdout.txt`, `stderr.txt` and actual temporary
artifacts. The command arrays, cwd, environment and policy are exact, not a
reconstructed shell transcript. The runner is `run_checks.py` in this packet.

| Run | Actual result | Meaning |
| --- | --- | --- |
| targeted_001 | 2 passed, 15 failed | New-path local variable collision; failure retained and repaired |
| targeted_002 | 17 passed | Initial source, unavailable/conflicting and saved-forgery cases |
| expanded_003 | 34 passed | Five standard modes, tables, multi-prefix, aliases, siblings and partial-source retention |
| expanded_004 | 49 passed | PSI sequence/PSSM/MSA/rounds, DELTA explicit sequence, tblastn PSSM, sidecar and census qualifications |
| regression_005 | 592 passed, 1 failed | Historical metadata/contracts/sidecars plus VDB census/saved relations; sole failure was old exact registry enumeration |
| final_006 | 50 passed | 49 new cases plus authorized registry expectation; saved profile consistency |
| final_007 | 51 passed | Final source address and search checks plus native coherent source-redirection forgery |

The final focused command selected the complete new test module and
`tests/test_native_blast_database_metadata.py::test_record_v2_registry_dispatch_is_exact_and_leaves_vdb_v1_closed`.
No unchanged broad test set was repeated merely to replace the expected registry
list. The earlier 592 passing checks remain evidence at their recorded source
state; final source pins identify the subsequent bounded changes.

The final receipt records memory.max=21474836480, memory.swap.max=0, unlimited
runtime, control-group termination, and actual native_returncode=0. Scratch is
monitored visible allocated bytes with possible overshoot, as the existing local
job receipt states; no stronger enforcement claim is made here.

Meaningful cases cover standard blastn/blastp/blastx/tblastn/tblastx, tblastn
PSSM, PSI sequence/PSSM/MSA and two original rounds, explicit DELTA sequence stage,
JSON15/table7/headerless table6, ordered multi-prefix operands, database-sidecar
census selection, complete original FASTA locators, valid duplicate declarations,
valid-plus-unresolved/conflicting siblings, unavailable original bundle size,
null release/scope, incompatible release/scope, missing/zero function counts,
malformed JSON/pointed record, source identity and byte-digest report aliases,
and saved source/value/operand/list/report-identity forgery. The no-I/O saved test
blocks population/extraction, open/Path reads, sockets and subprocesses while
validating and changing only temperature; serialized saved sheets remain exact.

## Source inspection and evidence limits

The immutable attachment, actual AGENTS.md, required design/execution/steering
documents, relevant inventory rows and packet 361 were read. The immutable
purpose and all sixteen principles were reread during implementation and after
source examinations. BEFORE_SHA256_001.txt records initial owned source/test and
authority pins; AFTER_SHA256_001.txt records final owned source/test pins and
unchanged authority. No Git metadata is present in this checkout.

Inspected paths include both metadata adapters, standard contracts, both native
workers, iteration handoffs, standard numerical row production, both result-view
contracts, publication request/custody/projection checks, both result owners and
return validators, selected dispatch/receiving/admission/completion methods in
execution_episodes, execution_progress descriptors, and shared local jobs,
receipts and communication boundaries. The existing dynamic result descriptors
need no B-owned row or prompt changes. The native result workers and publication
closure changes remain C-owned.

Historical regressions include retained native paired-output format fixtures;
those establish format/geometry only. All new database assertions and envelopes
are deliberately synthetic. B did not execute local database BLAST, use HPC or
network access, acquire external records, install software, or run a model.
B's tests reach metadata preparation, report parsing, direct sheets and numerical
calculation; the actual child-owned worker/publication/receipt/receiver evidence
is C's separate integration workload. Standard and PSI/DELTA still do not gain a
VDB-style episode-accessible saved-function selector from this change.
