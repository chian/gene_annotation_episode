# HMMER preparation producer — workload 267

Implemented the frozen P1 request/compiler, schema, one-command native producer
and existing-lifecycle reservation boundary. The final full verification is
[check005/receipt.json](check005/receipt.json): **225 tests passed**, with
**77 actual native executions covering all 26 declared tool/mode pairs**.
This is a producer/component handoff. It does not establish complete episode
integration, library binding, result acquisition, numerical grading or typed
return delivery.

Exact callable names, Job/Compiled/RequestedJob/Plan/Bundle rows, failure
relationships and directory constants are in [FIELDS.md](FIELDS.md). The
approved original-SSI-path correction is recorded separately in
[SSI_ORIGINAL_PATH_HANDOFF_001.md](SSI_ORIGINAL_PATH_HANDOFF_001.md).

## Ownership and inspected paths

Changed only the four new `gene_annotation_episode/native_hmmer_preparation_*`
modules, their four corresponding test files and this verification directory.
No existing episode/runtime, tool-library, scientific grader, accounting or
annotation-credit file was edited by this workload. The producer imports F1's
pure FM extractor for supplied-index preconditions; it never calls a scientific
calculator. Root owns LocalPracticalOperations routing, acquisition/publication
and eventual typed return delivery.

Read the full immutable user goal, AGENTS.md, GOAL.md, EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, PRACTICAL_EXECUTION and its original additive contract;
P1, the complete 259 report and ten tool contracts. Read the complete reused
Infernal preparation contracts/schema/driver/local implementations and the
existing native_lifecycle/local_jobs/worker paths and relevant shared custody
and durable-state helpers. Native source inspection covered each selected
tool's options, invocation/output semantics and dangerous paths; alimask and
hmmconvert were read completely. This does not claim a full audit of every C
file in HMMER/Easel. Source identities are recorded below.

The original objective and all 16 principles were reread verbatim after
substantial native investigation and in the final per-tool reviews. Frozen P1
was reread before delivery. Those user requirements remain authoritative;
passing component tests do not redefine the larger assignment's completion.

## Actual producer verification

The final command was:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/run_tests.py check005
```

The harness and every real native test used existing `local_jobs` at
20 GiB RAM, 4 GiB scratch and no wall-time cap. The receipt verifies
`MemoryMax=21474836480`, zero swap, `RuntimeMax=infinity`, control-group
termination, and the existing monitored scratch enforcement with possible
overshoot. No filesystem sandbox is claimed. Pytest elapsed time was 86.24 s;
the actual outer service-wall measurement was 86.875729278 s. Observed scratch
was 10,493,952 bytes. There were no installs, network calls, API tests or HPC
runs. The existing 259 tiny inputs supplied new producer-path executions;
259's old receipts were not counted as tests of this new path.

[check005_native_cases.json](check005_native_cases.json) lists every actual
case's program/mode, original plan, sealed bundle, native return code, artifact
byte counts, recorded ABI and per-case local-lifecycle receipt hashes. The
separate bounded [audit002/receipt.json](audit002/receipt.json) revalidated those
77 original bundles and all 26 successful declared program/mode pairs without
executing any native command. Synthetic custody/preflight tests are not counted
as native executions.

| Tool | Producer-path verification and retained facts |
| --- | --- |
| alimask | All four modes; hand, fast/no weights, given weights, default PB and explicit PB ali2model; three gappy fragment maps compared against actual native model2ali. With symfrac .65/fragthresh .6, no-weight/given maps are [3,5,6,7,8], PB is [3,5,6,8]. Two MSAs plus trailing non-ASCII bytes verify native first-MSA consumption while every original byte stays retained. Unsafe ranges and unsupported maps prevent invocation. |
| hmmbuild | Both declared modes, supplied BLOSUM62 matrix, redirected summary and resaved alignment. Ordinary alignment build produces a nonempty Stockholm resave. Single-sequence matrix build exits zero but leaves requested -O empty because native SingleBuilder does not create postmsa; the empty artifact is preserved. |
| hmmconvert | ASCII, binary and HMMER2 output; six explicit 3/a–f revisions from binary input; binary stdout begins native 3/f magic and has two distinct aliased role occurrences without text decoding. An invalid-alphabet second record exits one and retains the complete first model. |
| hmmemit | All five modes and all four profile settings. Seed42, N3, L20 generated profile totals are local126, unilocal137, glocal159, uniglocal148 residues. Simple consensus is ACDEFGHIKLMN. The samples remain generated model data. |
| hmmfetch | All three modes, actual private SSI creation followed by a separately selected indexed fetch, native missing-key failure with one complete model prefix, independent original model/SSI artifact paths, rejection of mismatched staged stems, and unselected ambient caller SSI left untouched. |
| hmmpress | Four-file private bundle, immutable source/private copy identities, and native duplicate-name refusal without modifying or deleting old caller sidecars. Synthetic copy mutation separately verifies typed changed-copy failure. |
| hmmsim | All four algorithms across four alignment styles, plus optimized Viterbi/MSV/Forward. N1000 produces 8000 score bytes per model with recorded C-double ABI. Viterbi fs mean is -5.619071923450204 bits; selected filter threshold .1 gives368/1000; traceback has1000 rows. Forward filter files remain empty native outputs. Unsafe optimized Hybrid/traceback combinations are rejected without substitution. |
| hmmstat | Selected summary operation retains full original model input, native stdout/stderr and exact execution identity. This producer does not calculate entropy or assign biological credit. |
| makehmmerdb | DNA, forward-only DNA, RNA, amino writer and ambiguous DNA. Extracted native source-symbol counts28,28,28,40,18 are checked from retained output bytes. Amino writer success is retained with reader incompatibility. Valid selected block size is unchanged. |
| hmmerfm-exactmatch | Location and count-only native commands; complete actual hits/logs retained, including count-only's existing empty hit file. Tests prevent invocation for malformed/long/unterminated query lines, wrong imported ABI, contradictory source binding, truncated FM data, in-range incorrect SA/counters, corrupted BWT/segments, incompatible reader spacing and amino FM input. |

Pure tests also cover all 26 request/schema roundtrips, exact selected options,
native option bounds and mutually exclusive settings, output aliases/overlaps,
reserved paths/environment, immutable request equality and finite uninterpreted
grading parameters. Custody tests cover missing/wrong/stale inputs, FIFO input,
software identity failure, missing/empty/partial outputs, byte/role/identity/
timestamp/failure-context tampering, moved complete retained directories,
sealed replay without execution, and unsealed/missing-handle uncertainty without
replacement work. Reservation tests prove no dispatch and strict reopening of
the original request, allocation, owner, driver environment and paths. One
actual reservation -> existing native dispatch -> CLI producer -> original
bundle path was run. No model-loop or parent/child message path was run here.

Earlier receipts remain unchanged: check001 had199 passes/2 test-expectation
failures; check002 had215 passes/2 fixture-expectation failures; check003 had9
targeted passes; check004 had224 full passes before the approved independent-SSI
correction. Corrections were: explicit filter threshold .1 instead of native
default .02; a full malformed second model instead of a truncated header that
native treats as EOF; the correct FM header offset; and acknowledging native
empty singlemx -O. Before bounded verification, a direct pure compiler/schema
smoke run exposed an incorrect fixture filename; no native command ran in that
smoke run, and it is not counted as constrained verification.

## Source-derived preconditions and unresolved coverage

Alimask preflight's PB branch follows Easel's distinct fixed .5 span-based
fragment/count definition and strict gap_fraction<.5 consensus rule, normalized
canonical residue weights, then selected old fragment marking using residue
count<=fragthresh*alen, then native float32 occupancy. Source boundaries are
alimask.c197–232 and381–399, esl_msaweight.c183–260/383–474,
esl_msa.c2177–2244 and vector/alphabet definitions. This is a safety precondition,
not a second scientific grader or a hidden native mapping call.

Explicit unfinished producer binding remains:

- Ali2model with GSC/BLOSUM weights; PB sampling above50,000 sequences; fast
  mapping without an explicit alphabet; and preflight input parsing outside
  Stockholm/Pfam. These return specific unsupported cases. No hand/fast/weight
  selection is silently substituted. All native alignment formats remain
  declared and the unfinished branches remain required work.
- Native execution tests here use Stockholm for build/mask and FASTA for FM
  construction. Other declared Easel alignment/sequence formats have pure
  compiler support but were not executed through this producer. Pfam mask output,
  HMMER2 input, every binary revision as input and every option combination are
  also not newly verified here. Binary/legacy output retention does not establish
  a numerical decoder. Model signature preflight does not validate every HMM
  probability body; native parser failures retain their actual results.
- The observed C int width is4 bytes. Source `1000000 * GetInteger(block_size)`
  multiplies signed int before assignment, so block_size2148 overflows even
  though native's superficial limit is3500. The compiler accepts positive values
  through2147, preserving the exact selection. A different native C ABI is not
  established by these tests.
- F1 supplied-index validation checks reader compatibility, exact counters,
  sampled suffix positions, LF/text consistency, segment partitions and bounds.
  It is not a claim of globally correct native search: exactmatch's reverse
  boundary defect and post-free diagnostic remain unmodified native behavior.
  Query U normalization is not silently performed; current query binding accepts
  only literal canonical A/C/G/T (including case) with required LF termination.
- Native --singlemx applies matrix construction only to one-sequence MSAs;
  consumers must retain actual per-MSA count/estimator meaning. Forward empty
  filter output and singlemx empty resaved MSA are not fabricated measured zeros.
- Only exact declared HMMER3.4 local ordinary-file execution is bound. No MPI,
  stall, stream-input, remote API or HPC producer route is established. Root's
  later acquisition, library, result-worker and episode communication tests are
  still necessary. The producer creates no scientific/controller observations.

## Reproducible identities

[check005/intent.json](check005/intent.json) records the final four modules,
four tests and exact F1 extractor hashes before execution.
[check005_source_manifest.json](check005_source_manifest.json) records78 files:
the owned implementation/tests, reused Python paths, instructions/contracts,
all ten actual binaries and their C source, relevant Easel/HMMER source, and
the immutable original goal (SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`).

Final manifest SHA256:
`09b188ff84dd89021d70e11e43959c622716b57f30d8d74440785b6698047994`.
Final native-case inventory SHA256:
`1ac655502d673ce9d61c8eada0d7d95c17a812222568a07b8d3dde1dd5cc5bae`.
The earlier `source_manifest.json`/`native_cases.json` remain the check004 audit
snapshots; they were not overwritten after the interface correction.
