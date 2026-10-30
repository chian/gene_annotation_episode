# Twenty additional Infernal modes through the production Workflow

The final run, `modes_003`, passed **20 tests in 600.24 seconds** with no failures,
errors, or skipped cases. It executed the original selected native commands
through the shared production Workflow fixture. This is an explicit scripted
engineering investigation, not a configured-model scientific investigation.

The local receipt records 20 GiB RAM, 4 GiB scratch, no wall-time cap, return code
zero, and 139,571,200 bytes of observed scratch allocation. The enclosing local
job measured 601.144126527 seconds. Native job timing is retained separately in
each original attempt; neither number is an annotation score.

Useful evidence:

- [Complete numerical and typed examples for every mode](modes_003/EXAMPLES.md)
- [Machine-readable index, native artifact paths, hashes, selectors and full typed forms](modes_003/EVIDENCE_INDEX.json)
- [Final local execution receipt](modes_003/receipt.json)
- [Pytest results](modes_003/tests.xml)
- [Source hashes before execution](modes_003/sources_before.json), [after execution](modes_003/sources_after.json), and [689 imported Python modules](modes_003/imported_sources.json)
- [Earlier run with 18 passes and two test-expectation failures](modes_002/EVIDENCE_INDEX.json)

## What the twenty tests establish

The explicit mode list is disjoint from the seven base integration cases and
together they equal the original 27-case producer index. Each mode validates the
real library entry, resource route, request schema, actual program and mode,
original compiler-produced argv, selected native flag, immutable original input
bytes, and every captured input, working copy and output occurrence. Retained
bytes, sizes, digests, formats and source associations remain inspectable.

Each real result reaches a populated sheet and separate calculations. Only the
selected quantities, checks and artifact occurrences reach the actual parent
form. Parent form authentication, received facts, action/observation accounting,
result completion and practical future-gain zero are exercised through the
production Workflow. The parent has no receipt permission or Workflow resolver
permission for the unrequested full sheet and calculation artifacts.

Every case has zero scientific observations and root scientific gains `[0, 0]`.
The one completed results action contributes the caller's one acquisition unit
(configured value 2), with one local observation. Multiple algorithms, rows,
files and diagnostic facts do not become additional acquisition contributions.
The saved-sheet recalculation check forbids native process creation, socket
creation, grading dispatch and native parser entry points.

## Actual numerical examples

All values below are preparation measurements, predictions, derived composition,
or model statistics. They do not measure annotation correctness. The linked
full artifacts preserve native tokens, individual algorithms, units, states,
input provenance and complete arrays.

| Native selection | Retained numerical result and meaning |
| --- | --- |
| `cmbuild / refine` | 3 training sequences, 12 alignment columns, 12 consensus nt, 4 modeled base pairs and 0 bifurcations. Paired consensus fraction is `2 × 4 / 12 = 0.6666666666666666`; the numerator and denominator remain separate. The refined alignment remains a distinct 3-by-12 output. |
| `cmconvert / legacy_ascii` | One parsed input and one parsed output model, CLEN 12 nt. Legacy output has no calibration blocks or filter HMM; these are expected format semantics. |
| `cmconvert / maximum_likelihood_hmm` | One output HMM with LENG 12 nt. CM-only CLEN stays missing. |
| `cmconvert / filter_hmm` | One output HMM with LENG 12 nt. CM-only CLEN stays missing. |
| `cmconvert / binary` | One parsed input model and three retained output artifacts. Output model count is null/missing because binary model content is opaque. Zero decoded model rows is not a biological empty population. |
| `cmemit / sample_unaligned` | Two generated sequences have 11 and 12 residues, each with 8 G/C residues. GC fractions are `8/11 = 0.7272727272727273` and `8/12 = 0.6666666666666666`. Alignment columns and gap fractions are unavailable for these FASTA sequences. |
| `cmemit / sample_aligned` | Two rows and 12 columns. Nongap residue counts are 11 and 12; gap counts are 1 and 0, with gap fractions `1/12 = 0.08333333333333333` and 0. Generated alignment annotations and model associations remain retained. |
| `cmfetch / key_file` | Two original input models, one returned 72-nt model, two requested keys, one satisfied key and one missing key. `requested_keys_satisfied` is fail, while native rc is 0 and complete requested result acquisition is true. |
| `cmfetch / index` | One native model, name and accession indexed. Source/attempt/stem bindings pass. Decoded index content remains unknown; output model count is null/not_measured. |
| `cmcalibrate / forecast` | The tiny fixture prints a zero-second prediction, retained as present/native_prediction. Its one-second display precision does not establish zero execution time. |
| `cmcalibrate / memory_estimate` | Native 1-CPU and 4-CPU predictions are 72.1 MB and 288.4 MB: 72,100,000 and 288,400,000 bytes using decimal MB. These preserve displayed precision and are not measured peak RSS. |
| `cmcalibrate / split_commands` | Native stdout reports 2 commands; the separate inert commands artifact also contains 2. Both source rows are retained. They are two representations of the selected operation, not independent experiments, and neither generated command is executed. |
| `cmcalibrate / partition_scores` | Requested 0.02 Mnt gives 2 total 10,000-nt chunks. Partition 1 of 2 receives 1 chunk, hence 10,000 nt for each algorithm. Complete GC/GI/LC/LI arrays contain 3,149 / 3,035 / 4,409 / 3,812 scores. |
| `cmcalibrate / merge_scores` | Each algorithm's new model header reports 20,000 calibration nt. GC/GI/LC/LI random-hit counts are 6,330 / 6,207 / 8,366 / 7,127. Missing original partition-request provenance remains explicit. |
| `cmstat / scores_at_evalue` | At native E = 0.01, local Inside / local CYK / glocal Inside / glocal CYK thresholds are 45.32 / 36.71 / 41.88 / 42.23 bits. Full-precision saved-fit calculations are stored separately. |
| `cmstat / scores_at_pvalue` | At native P = 0.01, the same algorithm order gives 4.14 / 2.60 / 2.66 / 2.18 bits. |
| `cmstat / evalues_at_score` | At 10 bits and 10 Mnt search space, native E-values are 4,406.56 / 1,593.45 / 1,859.13 / 1,697.07. |
| `cmstat / evalues_at_ga` | GA is absent in the original model. Threshold and corresponding E-value stay null; they are not replaced with zero. |
| `cmstat / evalues_at_nc` | NC is absent in the original model. Threshold and corresponding E-value stay null. |
| `cmstat / evalues_at_tc` | TC is absent in the original model. Threshold and corresponding E-value stay null. |

For the three numerical cmstat modes, the tests independently check
`D = search_space_nt / calibration_dbsize_nt × random_hit_count`, the applicable
exponential conversion, and the native printed quantities. Explicit parameter
changes are then checked with native execution and parsing forbidden:

- Reducing E from 0.01 to 0.001 adds `ln(10)/lambda` to the derived threshold.
  The local-Inside example changes from 45.3239102053337 to 51.5824655395025 bits.
- Reducing P from 0.01 to 0.001 gives the same algorithm-specific shift.
  The local-Inside example changes from 4.135400668337612 to 10.39395600250642 bits.
- Changing search space from 10 to 20 Mnt doubles the derived E-value at 10 bits.
  The local-Inside example changes from 4406.559995419342 to 8813.1199908387.

Each case's `RECALCULATED_EXAMPLE.json` is indexed with its hash. Original native
data, sheet values and historical completed actions are unchanged.

## Requested failure facts and retained unknowns

Only key-file fetch and merge request the optional failure source. Key-file fetch
returns one deduplicated `association/artifact_key_request_unsatisfied` fact,
with original handoff/source references and the exact key-request locator. Its
affected occurrence is `{direction: input, role: keys, ordinal: 0}`.

Merge returns ten distinct facts: two original partition-input metadata failures
and eight affected per-algorithm calculation failures. Each refers to its actual
partition input (ordinal 0 or 1). The original requests of those previous jobs
were not supplied; embedded command text is not promoted to authenticated
request metadata. Useful native calibration measurements remain retained.

The full exact six-field failure rows, requested numerical states and selected
artifacts appear in each complete typed example. Failures add no observation,
confidence score, bonus, automatic repair or follow-up native operation.

## Source checkpoint and precise limits

The tested mode module SHA-256 is
`5fce2721e86186ca09b425acb8bd299a14315f5f09be751f8ccb05880c5da1b6`.
The conservative full-package before/after snapshot changed only three files:
`literature_partner_source_fields.py`, `literature_partner_native_inputs.py`, and
`literature_partner_storage.py`. They are unrelated to this preparation path and
absent from the 689-module pytest import manifest. Their exact changes remain in
the receipt; the entire checkout is not claimed frozen. The preparation,
Workflow, receipt, resolver and consumed test sources did not change during the
run. No native work was repeated for the unrelated literature changes.

The original objective, all sixteen design principles and reset instructions
were reread verbatim after source/native study and before this report. Its
attachment SHA-256 remains
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The exact native-mode, sheet, projection and additive failure/visibility contracts
were reread. R5 supersedes the older per-action population wording.

This run proves V1 receipt exclusion and actual resolver denial. It does not
verify V2's newer requirement that reference-membership checks avoid artifact
byte reads; that focused sentinel and repair are owned by root/workload 258.
The retained hash checkpoint distinguishes this run from subsequent changes.

These twenty small native fixtures do not exhaust all CLI modifiers, multiple
model populations, alternate alignment formats, expert traces or present-cutoff
GA/NC/TC cases. Binary content remains undecoded; HMM header extraction does not
establish state-table equivalence. The seven base modes and nested scientific
library construction are verified in their separately owned workloads. No LLM,
external service, network acquisition, installation or HPC execution occurred.
No production source or inventory row was edited by this workload.

Earlier failures remain in their original receipts: `modes_001` and
`diagnosis_001` exposed the new test's provider-role assumption, while
`modes_002` exposed its one-model key-file and one-row split assumptions.
Those were verification-code corrections, not concealed production failures.
