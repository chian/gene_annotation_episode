# Planning verification337/001

Only additive files under this337 directory were written. No production module,
test, library, scope/accounting record, historical artifact or observation was
edited. The checkout has no `.git` directory at this working root; a scoped
`git status` therefore was unavailable. Original retained file hashes were
explicitly checked before and after the reproduction instead.

## Actual execution

`run_reproduction.py` launched `reproduce.py` through the existing `local_jobs`
API using `.venv/bin/python -B`, memory21474836480 bytes (20 GiB),
scratch4294967296 bytes (4 GiB), and no wall cap. The recorded result was exit0,
service wall0.914297933 seconds, observed scratch1196032 bytes. The receipt records
the memory/swap/cgroup limits. No BLAST executable, native database search,
network/API request, HPC access/submission, installation or download was run.

Receipt and immutable outputs are under `check001/`:

- `receipt.json`, `selection.json`, `stdout.txt`, `stderr.txt`.
- `source_snapshot.json` and exact inspected reproduction dependencies under
  `source_snapshot/gene_annotation_episode/`.
- `summary.json`, direct public303 sheet/components, actual standard R
  calculations/rows, and public-wire rejection results.

All report/source examples used in this execution are retained **synthetic**
M332 fixtures. Retention does not turn them into native database measurements.

## Results

The complete current standard preparation/population/saved validation reproduced
the exact retained failing sheet, and calculation reproduced the saved components.
It preserved the input objects. Direct public303 using the two already verified
original proof bindings produced:

- `blast_sequence_binding_source_identity_conflict`;
- `blast_description_binding_metadata_record_conflict`;
- `blast_sequence_database_reference_length_unqualified`.

Both native hit groups remain, with maximum bit scores20 and18, zero matched
metadata records, no accepted functions and null function weights. Standard
qualification reports `full_sequence_source_identity_conflict`. The actual
standard R calculator and row builder consume those same public303 components
and emit8 numerical rows.

The actual public v1 wire validator rejects an added original-record field with
`closed_payload_shape_invalid`; a fabricated FASTA JSON pointer `/records/0`
fails with `source_locator_not_supported`. These are validator results, not
assumptions inferred from type declarations.

The retained valid JSON-source baseline recalculates exactly: bits20/18,
F/G masses1/.25, unadjusted weights .8/.2, representation-adjusted weights
2/7 and5/7 for its supplied matching census. No proposed v2 implementation was
run or claimed. The proposal reuses that numerical oracle after fixing addresses.

The full FASTA file and its two per-record symbols/digests/lengths are printed
in `summary.json` and the implementation contract. These are complete original
FASTA bytes extracted from retained supplied inputs, not rewritten aliases.

Original failing-fixture hashes before/after were identical:

| File | SHA256 |
| --- | --- |
| supplied_inputs.json | 4173b72ae87ee463e13c89f308345bb17fd2a37d0de400220d360ce32e11da2e |
| sheets.json | 94ff1e96ff868b5fed01637a1a2a84ee662fd09f6a1b442ccd59401773039d50 |
| components.json | c7c07f8a9c335290f56341b7426e64b87f60dac3891264729350f6949d19dc5d |

## Inspection boundaries

Complete principal implementation reads covered public303, the generic database
grader, native6 metadata, standard metadata, standard calculators, standard
result worker and native database results. Relevant full consumers inspected
included native6 sheet calculation and worker/reuse/identity paths, iteration
input/dependency handling, VDB binding shape, original FASTA parser, standard
and native job validators, standard selector and E descriptor/catalog/request
functions, and relevant native/standard/public303 association tests. The source
snapshot pins the dependencies used by the actual reproduction. Concurrent
R333/E336 edits are not claimed to have been tested after that snapshot.

No new v2 schema/parser/calculator code, v2 production binding, full new
episode-return verification or live-resource capability is established by this
planning task. The required future cases and nonoverlapping coding ownership
are in `IMPLEMENTATION_CONTRACT_001.md`.
