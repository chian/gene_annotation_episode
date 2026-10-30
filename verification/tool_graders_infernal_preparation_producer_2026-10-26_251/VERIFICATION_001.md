# Infernal preparation producer and reservation verification — 251

This workload implements the frozen [producer handoff](../tool_graders_infernal_preparation_2026-10-26_247/PRODUCER_HANDOFF_001.md)
in two new modules and two new test modules. It does not change the compiler,
scientific Infernal v1 path, practical dispatch, graders, publication, episode
messages, credit or continuation. No existing inventory row is completed here.

The five public APIs are `validate_preparation_plan`,
`run_native_infernal_preparation`, `validate_preparation_bundle_files`,
`prepare_local_infernal_preparation` and `local_infernal_preparation_plan`.
The driver retains one compiler-selected native command and its exact explicit
environment. It supplies no inherited `INFERNAL_NCPU`, retry, hidden command,
index discovery, consumer submission or resource substitution. The local adapter
only reserves or qualifies the original existing native-lifecycle reservation.

## Retained evidence

The final bounded suite is [producer_003/receipt.json](producer_003/receipt.json):
**111 passed in 26.07 seconds**, with no source-hash changes during the suite.
[producer_003/tests.xml](producer_003/tests.xml) identifies every test.
Earlier receipts remain as historical evidence: producer_001 had 100 passes;
producer_002 had 105 passes. These overlapping totals are not additive.

The existing local_jobs/native_lifecycle boundary verified 21,474,836,480 bytes
RAM, zero swap, 4,294,967,296 bytes scratch and `RuntimeMaxUSec=infinity`.
The final outer worker observed 13,176,832 allocated scratch bytes. Scratch
enforcement retains the existing monitored-usage/possible-overshoot semantics;
this work does not claim a filesystem sandbox. There is no invented wall cap.

[NATIVE_PRODUCER_INDEX_001.json](NATIVE_PRODUCER_INDEX_001.json) indexes 35 genuine
preparation bundles with full input, working-copy and output file SHA-256/size
identities. These cover all 27 frozen native program/mode cases plus focused
cases. Its separate `reservations` list contains actual original targets,
assignments, plans, handles, lifecycle receipts and bundles for four local
reservations. Those four tests execute `prepare_local_infernal_preparation` →
existing `native.start_prepared` → driver CLI → native command → sealed bundle.
The index script reads these original records and does not relocate or rewrite
their realized commands. Preserve the indexed original bytes.

Concrete retained reservation examples:

| Selected operation | Native return code | Actual retained facts |
| --- | ---: | --- |
| cmemit consensus | 0 | Generated FASTA is 37 bytes; sequence `GCGCaaAAGCGC`. Empty stdout and stderr retain real zero-byte SHA-256 identities. |
| cmcalibrate calibrate | 0 | Original and staged CM remain 9,695 bytes; separate mutable copy changes from 9,695 to 10,538 bytes. The copy and selected calibrated-model output name the same actual file. |
| cmcalibrate merge_scores | 0 | Original CM remains 9,695 bytes. Explicit partition files are 134,671 and 127,704 bytes; immutable copies are `work/partition.1` and `work/partition.2`. Mutable model becomes 11,117 bytes. |
| cmcalibrate failed selected tiny-tail configuration | 1 | The surviving model copy is still 9,695 bytes; stdout is 1,381 bytes and stderr 116 bytes. The nonzero return code is retained; surviving bytes are not relabeled as successful calibration. |

Additional actual native tests preserve the `cmfetch` unindexed key-file rc0
case with an absent requested key, an explicitly produced SSI supplied to a
separately selected fetch, and a produced cmpress quartet consumed by a
separately selected actual cmscan through the existing scientific producer.
That scan is a test-selected consumer only. Production preparation invokes no
automatic follow-up. Native success, complete byte custody and requested-key
fulfillment remain separate meanings.

Synthetic faults verify unavailable/nonregular input, incorrect selected sizes
and hashes, wrong executable identity, insufficient scratch, partial copies,
command-start failure, nonzero exits, missing outputs even with rc0, changed or
missing mutable/immutable copies, modified retained bytes, symlink/path escape,
manifest association conflicts, typed failure contexts and original allocation
checks. Replay forbids native calls and network calls and works from a complete
retained directory after original inputs/software/location are removed. An
unsealed attempt is uncertain and never executes again. A missing native handle
with an existing reservation is also uncertain, even before an attempt directory
appears; the adapter does not create a replacement physical identity.

## Source pins and responsibilities

Final production module SHA-256 values:

* `native_infernal_preparation_driver.py`: `af01418dd47e6cc1c28710271a295ade86ce1b2d98a36bfd7fe5dff265fb81fd`
* `native_infernal_preparation_local.py`: `03ed971b8db1c8b3494bf36357469d2cf577792de2046a70cdc619a118009281`

The receipt includes exact test, compiler, shared-driver, local lifecycle/worker,
frozen contract, native fixture index and executable hashes. The producer checks
the selected executable digest before invocation. Engine-version text is the
caller-declared value; no hidden version-probe command is added.

The immutable goal, AGENTS.md, GOAL.md, full episode/time/practical design and
original practical contract were read. Complete scientific Infernal driver/local,
preparation compiler, native_lifecycle, local_jobs and local worker paths were
inspected before reuse. The original objective and all sixteen principles were
reread verbatim with the exact producer handoff after source study and before
closure. No external installation, network acquisition or HPC job was performed.

## Remaining boundaries

| Fixed row | Evidence supplied by producer251 | Row status |
| --- | --- | --- |
| native/cmbuild | Build/refine selected native output custody | Incomplete: whole requested tool path not established here |
| native/cmcalibrate | All six modes; mutable/original identity, partitions, failures and actual reservations | Incomplete: whole requested tool path not established here |
| native/cmconvert | All five modes retained | Incomplete: whole requested tool path not established here |
| native/cmemit | Three modes retained; actual consensus reservation | Incomplete: whole requested tool path not established here |
| native/cmfetch | Three modes retained, rc0 missing-key qualification and explicit SSI staging | Incomplete: whole requested tool path not established here |
| native/cmpress | Actual quartet and separate native consumer verified | Incomplete: whole requested tool path not established here |
| native/cmstat | Seven modes retained | Incomplete: whole requested tool path not established here |

Root owns practical dispatch, schema acceptance, tool information, grading,
publication and complete parent/child integration. Capture252 consumes the exact
retained reservation targets. This workload does not establish episode-message
delivery, numerical grading, annotation credit, configured-model science or any
HPC/API deployment. The overall goal remains unfinished.
