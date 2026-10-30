# HMMER preparation contract handoff — workload 259

This is preparation evidence for the ten fixed A-L076 rows. It does not implement
the tools, validate episode integration, change accounting, or complete the full
308-row goal. Only this verification directory was written by this workload.
Each complete proposed contract is under [contracts](contracts/COMMON.md).

All ten exact executables and their C sources are present under
`resources/software/infernal-1.1.5/hmmer/src/`. Native help identifies HMMER 3.4
(Aug 2023). There are **90 retained native invocations: 10 help calls and 80 tiny
examples**. Eighty-six exited 0 and four deliberately exercised failures exited
1. Every receipt used existing `local_jobs` with 20 GiB RAM, 4 GiB scratch, and
no wall limit; systemd cgroup enforcement is recorded. No installation, remote
job, database search, substitute program, credential or guessed deployment was
used. [EVIDENCE_MANIFEST.json](EVIDENCE_MANIFEST.json) gives exact arguments,
native receipts, executable/source hashes, per-invocation input/output occurrence
identities and 457 retained evidence-file hashes. The manifest explicitly labels
its hashes retrospective; it is not a claim that production custody was verified.

## Concrete contracts and independently checkable examples

| Original row | Exact contract / native examples | Concrete retained quantities and checks |
| --- | --- | --- |
| alimask | [alimask.md](contracts/alimask.md); alignment/model mask and both coordinate-map modes | `2-4,4-6` gives five unique masked columns of 14, fraction 5/14. Hand/RF model range 2-4 maps to alignment 2-4. Preserve one-based inclusive coordinates and mask union, not summed overlapping lengths. |
| hmmbuild | [hmmbuild.md](contracts/hmmbuild.md); protein, DNA, RNA, annotated protein, single-sequence matrix | Protein: 3 sequences, 14 input columns, 12 match states, EFFN 3, re/pos 4.376 bits. Position 5 F/Y counts 2/1 give native negative-ln tokens 0.40547/1.09861. Single-matrix re/pos 0.628 independently recalculates to 0.6282749545 from saved probabilities and explicit native amino background. |
| hmmconvert | [hmmconvert.md](contracts/hmmconvert.md); ASCII 3/a–f, binary, binary-to-ASCII, legacy 2 | Protein ASCII 6670 bytes; native binary 2725 bytes; explicitly selected binary-to-ASCII call reproduces original 6670 bytes. Annotated outputs demonstrate revision-dependent CONS/MM/MAXL fields. 3/a VMU is preserved under its native meaning and differs from modern VITERBI location. |
| hmmemit | [hmmemit.md](contracts/hmmemit.md); core/alignment/simple/fancy consensus and four profile styles | Core output is three 12-aa generated sequences, total 36 aa. Fancy consensus has one unknown position of 12 at thresholds 0.8/0.9. Profile modes have observed totals 126/137/159/148 aa despite requested expected length 20. |
| hmmfetch | [hmmfetch.md](contracts/hmmfetch.md); single key, unindexed/indexed key files, index | Name+accession aliases emit one model without SSI but two model occurrences with SSI. The 165-byte index reports one primary name and one accession. Indexed missing/duplicate keys exit 1 after a valid model prefix; unindexed missing keys exit 0 and omit missing records. |
| hmmpress | [hmmpress.md](contracts/hmmpress.md); private-copy press | One model yields h3m/h3i/h3f/h3p sizes 2725/165/9918/3216, total 16024 bytes. Duplicate names exit 1 and remove partial outputs. Four-file presence is distinct from complete binary-content validation. |
| hmmsim | [hmmsim.md](contracts/hmmsim.md); 19 native numerical examples | Viterbi local: 1000 saved double scores, fitted mu -6.4146 and lambda 0.7137; independent fit -6.41457636/0.71374992. E10 16.1746 recalculates to 16.17456475. Filter count 368/1000 = 0.368. Alignment length mean 4.439 and sample SD 1.86165108 match native output. |
| hmmstat | [hmmstat.md](contracts/hmmstat.md); protein/DNA/RNA/annotated models | DNA: native relE/info/p_relE/compKL 1.01/1.01/0.89/0.01 bits; independent values 1.00749217/1.00748657/0.89064223/0.00635582 from full saved emissions/transitions, explicit background and p1=350/351. Native rounded values remain separate. |
| makehmmerdb | [makehmmerdb.md](contracts/makehmmerdb.md); DNA both/fwd, RNA, amino, ambiguity, invalid bin | DNA source lengths 16+12=28; native FM block N=29 includes sentinel; both-direction database 314 bytes versus forward-only 226. Ambiguous source has 6 masked positions of 18, fraction 1/3. Native amino output exists but the downstream FM reader rejects its alphabet. |
| hmmerfm-exactmatch | [hmmerfm-exactmatch.md](contracts/hmmerfm-exactmatch.md); locations/count-only, forward/default reverse, ambiguity, zero | Forward tiny example reports 15 validated location occurrences but count-only reports 16 raw intervals. Default reverse locations report 17, with one boundary-invalid record and an omitted valid reverse match. Four ambiguous queries produce Q=1/H=3/R=0 after filtering, versus count-only Q=4/H=6/R=0. Zero example Q=0/H=0/R=2 has a valid empty location file. |

These examples establish native quantities and exact format distinctions. They
are not production parser tests, calculator tests, or complete episode-path
verification. Calculations in the contracts were performed directly from saved
native bytes without another native analysis or acquisition. No annotation
confidence or biological observation is assigned; emitted sequences and simulated
scores retain their generated identity.

## Shared-format decomposition and nonoverlapping coding boundaries

The common artifact/quantity/association envelope is in
[COMMON.md](contracts/COMMON.md). A record key includes invocation artifact
occurrence, record kind and ordinal. Identical bytes may share storage but cannot
merge input roles, repeated keys, repeated models or query lines. Native values,
derived values, validation checks and unknown states remain separate.

The following are proposed ownership boundaries, not new assignments or changes
to root's already-issued M1 ownership. File names below are proposed and can be
mapped to root's actual module names while keeping the ports and ownership.

| Boundary | Exact responsibility / proposed owned files | Required input and downstream handoff |
| --- | --- | --- |
| M1: model data, already separately assigned by root | Complete HMMER3/a–f ASCII amino/DNA/RNA headers, emission/transition arrays, original tokens, annotations and locators; generic distribution-mass residual, entropy, explicit-background KL and count ratios. `hmmer_preparation_models.py`, `hmmer_preparation_model_calculations.py`. | `extract_hmmer_models(content, *, occurrence, format, engine_version)` produces complete model records. Consumers are M2/M3/M4/M5, not scientific search publication. Native 3/a VMU, protein cutoff pairs and nucleotide single cutoffs remain distinct. No hmmstat occupancy/profile-statistic implementation here. |
| M2: model construction/inspection | alimask, hmmbuild, hmmstat operation readers, associations and tool-specific calculators. `hmmer_preparation_inspection.py`, `hmmer_preparation_inspection_calculations.py`. | M1 arrays plus complete supplied Stockholm records; exact ports in three contracts. Own RF/model/alignment correspondence, mask unions, summary/model joins, effective-count denominators, hmmstat occupancy and transition-dependent profile entropy. Native singlemx summary/model names differ; plain name equality cannot join them. |
| M3: model artifact operations | hmmconvert, hmmfetch, hmmpress; key parsing, conversion-loss declarations, current-attempt SSI associations and four-file press validation. `hmmer_preparation_artifacts.py`, `hmmer_preparation_artifact_calculations.py`. | M1 model populations plus complete original/produced bytes and exact source/index occurrence bindings. Own conversion and retrieval associations; do not implement another HMM probability parser. Binary/legacy decoding must remain explicit unsupported/unknown unless a separately established decoder is supplied. |
| M4: generated sequences | All hmmemit modes; FASTA/Stockholm sequence occurrences, model-to-emission membership and generated consensus validation. `hmmer_preparation_emission.py`, `hmmer_preparation_emission_calculations.py`. | M1 probabilities/consensus/masks; `parse_hmmemit_fasta`, `parse_hmmemit_stockholm`, `populate_hmmemit_sheet`, `calculate_hmmemit_components`. Reuse generic FASTA/Stockholm geometry only where the supplied reader preserves occurrences and annotations. No scientific observation publication. |
| M5: simulation statistics | hmmsim Viterbi/MSV/Forward/hybrid and local/unilocal/glocal/uniglocal styles, actual supported fast variants; binary score vectors and optional native summaries/plots. `hmmer_preparation_simulation.py`, `hmmer_preparation_simulation_calculations.py`. | M1 model identity plus original score-vector order, N, native ABI and exact parameters. `extract_hmmsim` then `calculate_hmmsim`; own distribution fits, tail membership, tenth-highest order statistic, alignment sample variance, and native-vs-recalculated comparisons. Generated scores are not observed alignment evidence. |
| M6: FM database and exact match | makehmmerdb and hmmerfm-exactmatch; source FASTA/segment records, ABI-specific metadata/packed T, ambiguity masks, query lines, exact-match locations and diagnostic counts. `hmmer_fm_preparation.py`, `hmmer_fm_calculations.py`. | Pure FM decoder/metadata output feeds the exact-match extractor. Source sequence occurrence and source/index lineage are required for independent location validation; raw interval counts and validated locations never share one metric. No dependency on M1 HMM probabilities. |
| Integration, shared owner | Request/role/format registry, pure dispatch and saved-sheet projection, child-owned native execution/capture/return bindings. New `native_hmmer_preparation_*` family, matching schema/tool-info/result-view modules; shared existing consumer edits stay with one integration owner. | Consume the exact pure ports above. Each module returns closed issue codes, typed numerical rows and pass/fail/unknown/not_applicable checks. Native execution, parsing, calculation and projection remain separate steps within the already-selected action; no private episode loop or new decision owner. |

M2–M6 can proceed independently once the common occurrence envelope and M1 model
record output are fixed; M6 is independently implementable immediately. Emission
and simulation have different native formats and meanings and should not share a
parser merely because both generate samples. Binary press outputs and FM indexes
also require different binary contracts. Generic Shannon/KL mathematics may be
shared while hmmstat's occupancy and transition terms remain tool-specific.

## Exact consuming-function handoff

The relevant existing paths were read as complete files, including local job
execution and lifecycle, the native HMMER request/compiler/driver/acquisition/
results modules, `native_hmmer_result_worker.py`,
`native_hmmer_result_publication.py`, `infernal_preparation_schema.py`,
`infernal_preparation_models.py`, native Infernal preparation local/worker/job
schema/results/result-worker/result-publication/returns modules,
`practical_execution_operations.py`, `practical_resource_episodes.py`,
`resource_episodes.py`, and `resource_tool_information.py`.

1. `resource_tool_information.bound_resource_tool_contracts` exposes only actually
   configured child routes. Add preparation descriptions and actual callable
   contracts there through the configured adapter; descriptions alone grant no
   execution capability.
2. `ResourceEpisodes.prepare_assignment` preserves the scientific parent's job,
   immutable input versions, constraints and caller allocation;
   `PracticalResourceEpisodes` owns its iteration through the shared method loop.
   `LocalPracticalOperations.validate_assignment` currently recognizes existing
   native families, so preparation needs its own explicitly configured request
   family. Its selected `practical.job.start` path should call one new preparation
   compiler/driver using the existing local lifecycle. Preserve explicit retries
   and exact selected program/mode; do not infer substitutions.
3. `LocalPracticalOperations.observe_execution` supplies exact attempt status and
   requested logs. A preparation role registry must identify stdout's actual
   format: it can contain binary models, generated FASTA, Stockholm, or text.
   Do not generalize its existing hmmalign stdout special case into text decoding
   of every preparation stdout. Private mutable model copies are required where
   native indexing/press behavior can overwrite or delete sidecars.
4. Model the receiving side on `NativeInfernalPreparationResults.execute`:
   selected `execution.results.collect` observes the exact assigned attempt,
   captures its complete bundle, invokes preparation grading, publishes original
   custody and delivers selected typed facts. Its production code is evidence of
   a reusable pattern, not an HMMER preparation binding already in place.
5. Reuse the semantics of
   `native_infernal_preparation_result_worker.qualified_occurrences` and
   `effective_parameters`: occurrence identity is bundle-relative direction,
   role and ordinal, separate from byte storage identity; an input must still
   match selected bytes; current-attempt index linkage is proved, not asserted by
   metadata. That worker's `_grade` is the proposed HMMER worker's direct consumer
   shape: supplied verified bytes -> pure tool parser -> populated sheet ->
   separate calculator. Proposed dispatch is `grade_hmmer_preparation(...)`;
   `recalculate_hmmer_preparation(sheet, *, parameters)` needs no native process.
6. Reuse the separation in `prepare_native_infernal_preparation_grading` and
   `publish_selected_preparation_result`: bounded parsing/calculation retains
   full sheets; saved-result projection reads them without regrading; only the
   requested small rows, quantities, checks and artifact references reach the
   receiver. Stable custody excludes volatile worker timing. The existing
   `NativeInfernalPreparationReturns` pattern validates the original commission,
   scope, typed form and frozen facts and deduplicates redelivery.

Do not route this through `native_hmmer_result_publication.
publish_selected_native_hmmer_rows`, which creates biological observations.
The existing HMMER `_profiles` helper is metadata extraction, not a probability
body reader. Infernal's model reader accepts only nucleotide HMMER3/f framing
and does not supply amino bodies. Those implementations cannot substitute for M1.

## Native defects and limits that must remain visible

- `hmmerfm-exactmatch` r direction is **reversed string**, not reverse complement.
  Printed coordinates are one-based forward starts or reverse right endpoints.
  Its boundary filter has an off-by-one error and applies a forward-length test
  to reverse endpoints. It can emit invalid locations and omit valid ones.
  Native count-only intervals include cross-sequence and ambiguity-replacement
  matches that location mode later filters. Equal aggregate counts can conceal
  different incorrect memberships. Q and R are not always a partition of queries.
- `makehmmerdb --amino` writes a database that this native `fm_readFMmeta` rejects.
  Retain the produced bytes and explicit unsupported downstream route. FM format
  has no version/magic framing and is ABI-sensitive; metadata or packed-T parsing
  does not establish complete BWT/SA validation. No protein FM search was guessed.
- `hmmsim --fwd --ffile` can exit 0 with an empty requested filter file because a
  source-level error is ignored. Hybrid calibration and fast+hybrid/fast+alignment
  modes have unresolved/invalid native semantics identified in the contract.
  Missing calibration, invalid fits and absent optional outputs are not zeros.
- `hmmpress` failure cleanup can remove existing optimized sidecars, even when
  overwrite refusal caused failure. Use a private operation directory; no shared
  prepared database was subjected to that behavior here.
- `hmmfetch` preserves native indexed/unindexed differences and valid output
  before errors. A key line is a request occurrence, not a set element. Source
  hashes alone do not prove an imported SSI was built for the selected model file.
- HMMER2 ASCII uses quantized odds and cannot use the HMMER3 negative-ln-probability
  decoder. Native binary and optimized sidecars remain retained opaque data where
  decoding is unsupported; a successful explicit conversion is a separate native
  operation. Full model bodies and all repeated records remain available.
- Native `alimask` reads only the first MSA, has a fixed range-array bound, and
  unsafe ali2model handling after the last match column. Other Easel alignment
  formats require their own established readers. Arbitrary format support was not
  inferred from extensions.

The immutable complete objective and all 16 principles were reread after each
tool and substantial native/source study, followed by the current exact contract.
No additional audit or production workload is started by this handoff.
