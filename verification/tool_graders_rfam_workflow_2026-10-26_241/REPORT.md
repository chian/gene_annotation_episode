# Controlled Rfam composed Workflow verification

The final full suite passed **15 tests in 113.27 seconds** in `tests_004`.
After root restricted Rfam numerical fact ownership to results episodes, the
updated construction check passed **1 test, 14 deselected, in 21.31 seconds**
in `tests_005`. These are overlapping checks, not 16 distinct tests. The full
suite has unchanged before/after source hashes; `rfam_batch_publication.py`
changed during `tests_005`, which is therefore a moving-source check. The full three-case suite predates
that single shared ownership advertisement change; the focused final check
uses the changed ownership source. Its loaded publication version is not
established by before/after hashes, so it is not a stable verification of the
final shared source. Root will run the final stable combined verification after
the publication/return handoffs. No production file was edited by this worker.

The owned implementation is `tests/test_rfam_composed_workflow.py`; its bounded
runner is `run_tests.py`. Each run retains exact commands, source hashes,
stdout/stderr, JUnit results, policy and native lifecycle receipt. `SUMMARY.json`
contains the actual selected rows, populations, operational gains and replay
results. Every full Workflow run preserves its Store, immutable API intents and
receipts, original forms, model decisions, action/observation records, source
artifacts, full parse/sheet/calculation and rendered scientific presentations.

## What actually ran

The existing Workflow constructs a scientific process using the frozen A101
evidence axis, P01 thought pattern and two selected tool-information entries:
`api.rfam.submit` and `api.rfam.fetch`. The scientific episode commissions
launch; launch commissions the API resource episode; that episode selects one
submission. The scientific episode separately commissions results, which selects
one fetch. Existing production parsers, calculators, publishers and return
readers deliver only the original requested `rfam_result_rows` and
`rfam_result_populations` through results → scientific_process → annotation.
The caller configuration is `{kind: api, service: rfam_batch, timeout: 12.5}`.

Only model decisions, root/scientific continuation estimates and HTTP responses
are controlled fixtures. Source publication, typed admission, recorded outcomes,
operational credit and practical completion are not replaced. Socket connection,
HTTP opener, subprocess and hidden sleep entry points are forbidden inside the
test. No live request, model inference, local scientific program or HPC job ran.
This verifies the composed in-process shared method_loop path; it does not
claim detached worker/process recovery or a configured-model investigation.

| Case | Retained numerical result | Qualification |
| --- | --- | --- |
| Single | 104.6 bits; E = 1.4e-24; native GC = 0.49; query span 119 nt; span fraction 119/119 = 1; full model coverage unavailable | Response body is byte-exact from the previously retained live single result. This test's fresh submission/request custody is controlled; it did not submit that historical job. |
| Complete empty | Zero available rows, zero selected rows, complete reported population; both query-strand unions zero | Explicit synthetic identity-bearing complete JSON. No live no-hit behavior is claimed. |
| Selected batch | Three saved hits; two requested rows at 30 and 40 bits, with query span fractions 70/119 and 80/119; `more_rows=true`; four distinct input occurrences | Explicit synthetic native-format table with generated names. Caller-selected original FASTQ members are ordered second, first, second, first. Native rows are deliberately ordered occurrence 2, 0, 1; occurrence 3 has complete zero reported hits. |

The single saved display calculation also preserves 120 represented model
positions, 118 determinate consensus comparisons and 75 equal symbols. Those
unrequested cells remain in saved artifacts. Model coverage is unavailable
because a full same-model denominator was not supplied; display endpoints do
not supply one. Batch original member references and source ordinals survive
repeated selections, and separate selection ordinals create four distinct
query occurrence keys even though all sequence bytes are equal.

## Observations, continuation and replay

Each case has six model decisions, six completed own actions and six local
observations: root 1, scientific 2, launch 1, API launch 1, results 1. There are
exactly two controlled native calls, submit and fetch. No status observation,
polling itinerary, parsing turn, report-composition model call or extra terminal
zero turn is inserted. Production practical continuation returns exact zero
immediately for launch, API launch and results, while retaining configured final
operational gains 3, 3 and 2. Three publication source records count as one
acquired result. Root/scientific fixture gains remain zero; no annotation or
scientific observation record is manufactured.

Saved recalculation is equal to the retained calculation. A fresh Store,
ToolRegistry, Workflow and API execution binding reopen each completed run with
transport, parser, calculator and model entry points forbidden. The archive and
complete episode/action/model/observation/form/admission histories remain equal;
original selected API operations also replay their exact saved outcomes.

The final focused construction check additionally verifies that launch and API
launch advertise no own Rfam numerical fact families, results advertises both,
and scientific/annotation parents advertise them through received reports.
No direct root or scientific Rfam execution operation is exposed.

## Limits and retained development attempts

`tests_004` enforced 20 GiB RAM, 4 GiB scratch and no wall-time cap using the
existing systemd cgroup runner. All retained fixture runs are inside its
monitored working directory; observed allocated scratch was 25,821,184 bytes.
The receipt states the existing monitor's possible scratch overshoot semantics.
`tests_005` uses the same policy. Earlier runs placed persistent test artifacts
outside the runner's monitored cwd; their 4 GiB per-file limit was present, but
their aggregate fixture storage was not included in its scratch measurement.
The final runs correct that harness limitation.

`tests_001` retained four passes and one harness assertion failure: it compared
an API outcome to the runtime-enriched outcome containing
`pending_work_after_action`. The correction compares original API outcome to
original API outcome and retains full runtime-history equality. `tests_002`
retained ten passes and one caller fixture setup error: a multi-record FASTA
creates separate targets, not the read library assumed by the test. The fixture
now uses the existing FASTQ selected-read path. `tests_003` passed all fifteen
checks before the final scratch containment and exact-gain assertions. No failed
run was removed or overwritten. These failures did not identify production
consumer defects.

This workload does not independently rerun the malformed, partial, forged,
transport, monitoring or rich native-format suites owned by the other Rfam
workloads. It establishes the actual composed path for the three cases above.
Live-resource status, detached execution, broader accounting and final source
pinning remain the parent's separate responsibilities. Literature, W05 and HPC
are outside this verification. The original goal objective and all sixteen
principles were reread verbatim after study and at closure, followed by the
current contracts; `CONTEXT_RESET.json` records their identities.
