# HMMER preparation W1 verification

This workload owns only the two new Workflow test files and this evidence
directory. It exercises the existing `Workflow`/`method_loop`, practical local
start, original native attempt, C1 capture, G2 workers, D1 grading, V1 requested
projection, and R1 typed returns. Production changes belong to their named
owners. The immutable full goal remains 308 fixed rows; this evidence does not
change that scope or publish completion on its own.

`run_verification.py` launches pytest through `local_jobs` with 20 GiB RAM,
4 GiB scratch, and no wall-time cap. Every native case uses existing tiny
HMMER 3.4 fixtures and the exact pinned installed executable. Native driver and
grading worker receipts, complete artifact bytes, filled sheets, calculations,
original requests, typed forms, and controller histories remain under each
check's `temporary` directory. All captured production-module and test hashes
are retained before and after each run.

## Verification coverage

The 36 workflow tests cover all 26 modes plus repeated acquisition, status then
collect, missing rows, changed native output, unavailable bundle/grading,
saved-result replay, indexed aliases, unindexed missing keys, and an actual
failed indexed retrieval with a valid model prefix.

The 76 nested tests run one real native example per program through selected
`evidence_axis`, `thought_pattern`, and `child_tool_info` construction slots.
They exercise results → scientific_process → annotation through both requested
typed forms, catalog/instruction/callable contracts, numeric/population/artifact
tampering, narrower forms, withheld artifacts, frozen original forms, duplicate
delivery, saved returns without native/worker/parser/calculator work, and saved
sheet recalculation with file/network/native/parser work forbidden. Return
replay also forbids reading the full grading, sheet, or calculation artifacts.

Decisions and scientific termination horizons are explicit engineering test
fixtures. Practical endpoint proofs, exact-zero future expectation, and the
ordinary controller comparison are production behavior. There is one local
observation per selected completed action. Successful result collection has
operational gain 2; repeated collection of the same original bundle has gain 0.
Selected status followed by collection gives [0, 2] and no extra zero turn.
Scientific and annotation gains remain zero.

| Program | Actual modes | Independently checked example |
| --- | --- | --- |
| alimask | mask_alignment, mask_model, model_to_alignment, alignment_to_model | 3 sequences, 14 alignment columns, 12 RF positions; overlapping ranges mask 5/14 columns |
| hmmbuild | build_alignment, build_single_sequence_matrix | 3/14/12 sequence/source-column/model-position counts; single sequence 1/12/12; actual empty single-matrix resaved alignment |
| hmmconvert | ascii, binary, legacy_hmmer2 | ASCII one source and one output model, 611 probability cells, maximum difference 0; binary/legacy decoded output count unknown |
| hmmemit | sample_core_unaligned, sample_core_aligned, consensus_simple, consensus_thresholded, sample_profile | Consensus ACDEFGHIKLMN, length 12; thresholded ACDExGHIKLMN; seeded profile lengths 15, 72, 39 |
| hmmfetch | single_key, key_file, index | Unindexed two alias keys → one source/one output; explicit SSI aliases → two outputs; one resolved/one missing key and valid failed-prefix retention |
| hmmpress | index | One model/name/accession, four members; binary/profile sizes 2725, 9918, 3216 bytes and exact path-dependent SSI size |
| hmmsim | viterbi, msv, forward, hybrid | Full 1000-double/8000-byte vectors; Viterbi mean −5.619071923450204 bits, tenth highest −0.6476082390605439 bits, filter 368/1000, alignment mean 4.439 |
| hmmstat | summary | Explicit DNA parameters: mean entropy 0.9925134248800135 bits and mean match KL 1.0074921672642938 bits; independent exp(−cost) calculation |
| makehmmerdb | build | Two sequence occurrences, 28 source symbols, 314 database bytes |
| hmmerfm-exactmatch | locations, count_only | Seven supplied query occurrences, native Q=5/R=2, H=17 locations or H=19 count-only; 17 emitted locations with 16 valid and one invalid |

SSI size is not a fixed scientific constant. Easel allocates filename padding
from the full invocation path length while writing its basename. The retained
relative-path example is 165 bytes; these private absolute-path jobs use
`165 + len(actual_model_path.encode()) - len(b'models.hmm')`. The pressed bundle
sum uses that exact actual size. Internal SSI/pressed payload validation remains
explicitly unknown where no supported decoder exists.

The Viterbi independent fit uses a declared equation-residual tolerance of
1e-10. Its E10 is 16.1745647507907 for these jobs; the independent reference
16.174564750739254 agrees within 1e-9 sequences. Tests additionally evaluate the
Gumbel survival equation directly. Native rounded summaries remain separate.
Forward's actual empty filter file remains an empty artifact, not a zero count;
Hybrid's native undetermined pmu remains incompatible/null.

## Exploratory records and corrections

Exploratory failures are retained, not rewritten into passing evidence.

| Check | Recorded outcome | Diagnosis |
| --- | --- | --- |
| check001, check002 | local-job scratch preflight rejected before pytest/native launch | Harness initially used the whole repository as cwd; changed to the isolated check directory with absolute test paths |
| check003 | 1 failed | Fixture expected a list where frozen selector transport supplied a tuple |
| check004 | 1 failed | Requested row/check dependencies correctly added an input artifact; fixture expected outputs only |
| check005 | 1 failed | Fixture omitted E1's declared model aggregate row-key mapping |
| check006 | 13 passed, 19 failed | Older loaded fixture expectations plus the confirmed saved-order production defect; sources changed during this exploratory run |
| check007 | 61 passed, 5 failed | Two A1 saved-order failures; SSI size, S1 fit tolerance, and S1 input-disclosure fixture assumptions |
| check008 | 4 passed, 1 failed | Actual failed indexed fetch correctly marked its retained output count incomplete, while the fixture demanded present |

The confirmed production defect was A1 optional-field list ordering after
canonical JSON storage. Initial native annotation objects had MAP/CONS/RF/MM/CS
insertion order; canonical JSON loaded CONS/CS/MAP/MM/RF. Saved recalculation
therefore returned a different list. Root fixed deterministic field ordering in
`hmmer_artifact_calculations._optional_values` and verified 115 component cases,
including ten canonical/reversed-key regressions. W1 retains exact equality;
it does not normalize away differences.

Other corrected fixture assumptions include binary/legacy diagnostic comparison
rows remaining present with unknown measurements, F1 aggregate keys, and the
specific `native_hmmer_preparation_retained_grading_unavailable` failure code.
Retained output-derived S1 quantities do not request model-body artifacts.

Final checks passed: `check009` has 36 passing workflow tests in 1172.28 seconds;
`check010` has 76 passing nested tests in 750.07 seconds. Together they executed
52 original tiny native attempts, including the expected failed indexed-fetch
attempt. There are no skipped tests. `EVIDENCE_INDEX.json` links all 52 cases,
the 26 filled numerical examples, and their complete retained sheets and
calculations. `FINAL_MANIFEST.json` pins the completed run receipts and tested
verification-file hashes.

Both final receipts record concurrent edits only in
`literature_rate_native_inputs.py` and `literature_rate_storage.py`. Therefore
their whole-repository `sources_unchanged` flag is false. HMMER preparation,
shared execution/receipt paths, and both test files were unchanged during each
completed run. The literature operations were not selected by these fixtures.
Later translation/extraction changes to `tools.py`, `sequence_ops.py`, or the
knowledge index are outside these completed tested-source snapshots. Do not
reinterpret the retained receipts as verification of later source revisions.

## Limits

This verifies tiny local native execution and scripted episode communication.
It does not claim a configured-model scientific investigation, annotation
confidence, API deployment, HPC deployment, or all optional native argument
combinations. Binary/legacy model decoding and opaque SSI/pressed internals
retain their declared unknown states. These limits remain explicit work where
the original goal requires additional capability; neither a successful practical
endpoint nor this verification erases them.
