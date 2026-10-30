# B003 nucleotide search reader and calculator verification

These artifacts verify pure native readers, numerical sheet construction and
calculators for HMMER 3.4 `nhmmer` and `nhmmscan`. They do not establish the
production child-owned invocation, publication or typed episode return path.
The B003 root integrator owns those separate bindings and verification.

## Implemented interfaces

`gene_annotation_episode.nhmmer_inputs` exports:

- `parse_nhmmer_artifacts(*, program, artifacts, artifact_refs, engine_version)`
- `build_nhmmer_sheet(native, *, inputs)`
- `iter_nhmmer_tblout_rows(stream, *, program, artifact_ref)`
- `iter_nhmmer_stdout_records(stream, *, program, artifact_ref)`
- `iter_nhmmer_stdout_queries(stream, *, program, artifact_ref)`

`gene_annotation_episode.nhmmer_grader` exports
`calculate_nhmmer_scores(sheet, *, parameters=None)`. Only `None` and `{}` are
accepted calculator parameters; unknown parameters raise a specific error.

The stream iterators consume supplied text/binary line iterables or file objects;
they never open paths. Table rows include original line numbers, UTF-8 byte
spans, row occurrences, raw text/tokens, parsed measurements and scoped issues.
The stdout record iterator buffers one local locus, emitting header,
query-start, locus, query-end and completion records. The query iterator emits
query metadata/statistics without collecting loci. Repeated query names retain
distinct occurrence identities. Invalid UTF-8 stream rows retain original bytes
as hex along with their actual byte offsets.

The full parser preserves the supplied artifact text and custody references.
The sheet keeps all original native representations, typed quantities, explicit
metadata, length sources, normalized intervals and join decisions. Reciprocal
unique matches alone join tblout/stdout loci. Ambiguous matches remain separate
and carry issues. Metadata mismatches, conflicting lengths and indistinguishable
duplicate names do not establish a coverage denominator or union identity.

Native `hmm` positions always address the model, while `ali` and `env` address
the physical nucleotide sequence. `nhmmer`'s length field supplies sequence
length; `nhmmscan`'s supplies model length. Query header `[M=]` and `[L=]` have
their own meanings. Sequence/MSA input length never substitutes for a missing
constructed-profile length. Descending reverse coordinates retain their native
direction and normalize to `[min(from,to)-1, max(from,to))`.

Scores return named locus scalars plus separate native/derived sections and
component records with numerators, denominators, input fields, units and scoped
unavailability. There is no combined confidence. Native E-values, bits, bias,
accuracy and inclusion flags remain native facts. Paired/insert/delete counts
require a validated actual display. PP display characters yield interval bounds
over sequence residues with available PP; deletion columns and missing symbols
remain explicit. Unions require an identified query occurrence and unique
supplied target identity, and stay separate by strand. Nucleotide model cutoff
margins use explicit per-hit/`sequence_bits` cutoffs, never `domain_bits`.

## Native inspection and actual executions

Inspected the installed complete `nhmmer.man` and `nhmmscan.man`, relevant
`nhmmer.c` / `nhmmscan.c` query, native output and search-space paths,
`p7_tophits_TabularTargets`, nucleotide `p7_tophits_Domains`,
`p7_alidisplay_Print`, and `p7_pli_Statistics`. Also read the existing
`phmmer_format.py` and bounded local-job adapter before using that runner.
The authoritative objective and entire DESIGN PRINCIPLES block and B003 were
reread after substantial native inspection and again at tool closure.

`run_native.py` created explicit synthetic 100-nt query data, three tiny target
sequences (120, 120 and 121 nt), and a three-row identical synthetic MSA. These
are generated test inputs, not biological measurements. Real installed HMMER
3.4 programs then produced all retained output:

| Run | Actual program/mode | Native result |
| --- | --- | --- |
| prepare_build | hmmbuild --dna | 100-position model |
| prepare_press | hmmpress | Actual pressed model database |
| nhmmer_sequence | single unaligned query sequence | 3 loci |
| nhmmer_profile | supplied profile | 3 loci |
| nhmmer_msa | native model construction from MSA | 3 loci |
| nhmmer_z_watson | profile, -Z 0.1, --watson | 2 loci |
| nhmmer_z_both | profile, -Z 0.1, both strands | 3 loci |
| nhmmscan | three query sequences against pressed model | 1 locus/query |

All eight commands exited 0 through the existing `run_local_job` adapter, with
20 GiB RAM, 4 GiB scratch and no wall-time budget. Each receipt retains exact
argv, binary digest, policy and actual enforcement facts: systemd cgroup memory,
zero swap, monitored allocated scratch plus hard per-file limit, no wall timer.
Preparation outputs receive no scientific confidence score.

All native stdout, tblout, stderr, input FASTA/Stockholm/HMM, pressed model files
and execution receipts are retained. No API, HPC, database BLAST or pending NCBI
job was used. Ordinary unit tests do not execute HMMER.

## Filled numerical examples

The gapped locus in all four primary search modes has model span 100, sequence
span/envelope 101, 98 paired positions, 3 insertions, 2 deletions and 103 display
columns. Model length is 100; actual sequence length is 121. Therefore:

- model-span coverage = 100/100 = 1;
- sequence-span/envelope coverage = 101/121 = 0.8347107438016529;
- paired-model coverage = 98/100 = 0.98;
- paired-sequence coverage = 98/121 = 0.8099173553719008.

| Program/query construction | E-value | Score bits | Bias bits | Native accuracy | PP lower/upper mean bounds (101 residues) |
| --- | ---: | ---: | ---: | ---: | --- |
| nhmmer / single sequence | 3e-26 | 78.7 | 0.7 | 0.93 | [0.8846534653465346, 0.9470297029702971) |
| nhmmer / profile | 3.2e-34 | 105.7 | 0.7 | 0.95 | [0.9004950495049505, 0.95990099009901) |
| nhmmer / MSA | 3.2e-34 | 105.7 | 0.7 | 0.95 | [0.9004950495049505, 0.95990099009901) |
| nhmmscan / sequence against model | 1.1e-34 | 105.7 | 0.7 | 0.95 | [0.9004950495049505, 0.95990099009901) |

The reverse exact locus uses native `ali_from=110, ali_to=11`, normalized
interval `[10,110)`, 100 paired positions and coverage 100/120. No translation
or function is inferred.

Search-space context remains distinct: actual nhmmer statistics report 3 target
sequences and 722 searched nucleotides for both strands, versus 361 under
`--watson`. Both `-Z` examples separately retain the declared 0.1 **million
nucleotides**, and the original exact supplied argv. Their forward exact-hit
printed E-values are 1.7e-36 (both strands) and 8.4e-37 (Watson). The reader does
not treat these native search counts as the `-Z` assertion or reconstruct an
E-value. nhmmscan instead retains 1 target model/100 model nodes and, for its
120-nt forward query, 240 searched nucleotide positions. It does not treat model
count, model length and nucleotide search space as interchangeable.

`filled_examples.json` contains all 17 resulting loci. Each run contains its
saved populated `sheet.json` and `scores.json`. `recalculate_examples.py`
recreates them from the retained text without running any native analysis.

## Verification and limits

Executed:

```text
.venv/bin/python -m pytest tests/test_nhmmer_inputs.py tests/test_nhmmer_grader.py -q
57 passed
```

Tests include retained real output and explicitly synthetic edge cases:
role inversion, reverse/one-position coordinates, invalid envelopes, gaps,
missing/zero/negative/nonfinite fields, invalid UTF-8, truncated rows/queries,
duplicate names/occurrences, ambiguous joins, wrong identities/versions,
conflicting lengths, overlapping and duplicate union members, PP bounds/gaps,
native inclusion flags, cutoff scopes and finite arithmetic overflow. Complete
native termination, supplied output completion and hit-population/page metadata
remain separate. Dfam and per-position declared formats are retained as
unsupported, not parsed as tblout.

The saved-sheet test removes native artifacts entirely and blocks file access,
network sockets, subprocess creation and native parser entry points. Numerical
recalculation still gives the same result and leaves the saved sheet unchanged.

Unverified production work remains explicit: no worker-owned test selected
nhmmer/nhmmscan through a real episode resource child, retained its artifact
through source custody, published these sheets, and delivered a typed return to
the receiving episode. The root owns those bindings and their tests. Other
native versions, FM-index execution, actual RNA-alphabet inputs, singleton-MSA
`--singlemx`, Dfam and per-position format readers were not executed/implemented
by this workload. Native queries represented only by tblout cannot recover
indistinguishable repeated query occurrences; the reader records that missing
association instead of assigning it by rank.
