# Existing local protein resource ports, 405

2026-10-27. Implements approved contract 380/018 with the additive method-name
correction 380/019. This is a completed narrow resource-port increment. The
scientific tool remains unaccepted; the fixed total remains 112/308.

## Changes and ownership

Only the approved production ports were edited:

- `practical_execution_records.py` embeds C390's unchanged requested-job schema
  and dispatches its semantic validator, requiring local kind and explicit
  resource identity.
- `practical_execution_operations.py` validates the exact operation/comparison
  mode/full Software binding and original allocation. It uses C390's original
  reservation helper, run-plan reader, confined-file helper and existing native
  lifecycle. Selected start, status, collect and explicit failed-attempt retry
  keep the original native identity. Log windows are selected stdout/stderr;
  native results and bundle expose availability, byte length and writer closure.
  A bundle path being present is not scientific validation. Bounded reads only
  accept selected original output paths or the original bundle.
- `execution_progress.py` changes only `describe_execution_target`, `_native`
  and `returnable_handoff`. It reports the exact operation, explicit comparison
  mode or null, and `native_protein_structure_bundle_v1`; authenticates recorded
  attempt ID/key/path; and permits a recorded failed protein attempt to be
  returned for partial-result/diagnostic acquisition.

The new `_protein_plan` accepts the same identity keywords as `_rna_plan`:
`run_id`, `origin_episode_id`, `original_operation_key`, `attempt_id`, and
`resource_id`. Identity disagreement uses `original_commission_mismatch`.
Native status is read after original-plan authentication. Retry also authenticates
the original plan before status and rejects unknown, cancelled, absent-returncode,
successful or lifecycle-killed work as a confirmed failed attempt. Refused retries
retain the original attempt identity in their factual outcome.

No resource adapter, episode type, loop, scheduler, timer, parser, calculator,
scientific score, prompt, library wording, form schema, literature or W05 change
was introduced. ExecutionEpisodes and the detailed operation-information
integration remain root-owned. C390's contracts, implementation pins, selected
driver/worker commands and bundle schema are unchanged.

## Inspected paths

Read the complete original practical records, operations, resource binding,
state, receipt publication, execution progress, native lifecycle, local_jobs and
protected worker modules. Read C390's complete request/run-plan contracts,
local reservation reader and driver; C392's complete capture consumer; the
existing ExecutionEpisodes request validation, assignment, target/selector,
selected execution, generic result acquisition, received-handoff, fact and
resolve consumers. These are inspections, not full episode-path tests.

Read AGENTS.md, the immutable original attachment, episode/time/practical design
documents, the original tool-grader principles and relevant inventory row before
coding. Read the approved 018 contract before coding. Root confirmed 019 after
inspection showed the existing method is `returnable_handoff`, rather than the
name `collectable_handoff` in 018. Reread the original objective and all sixteen
principles, 018/019, and the scientific-sheet/native-envelope portions of 380
before handoff.

## Executed checks

All pytest work ran through `local_jobs.run_local_job`, with 20 GiB RAM,
4 GiB scratch, verified zero swap, and no wall limit. Each check executed its
own retained source snapshot. Snapshot file bytes were read-only and before/after
SHA-256 manifests were equal; no source drift occurred. The complete policy,
cgroup evidence, selected command/environment, logs and native failures are
retained. No bare pytest, network service, model, HPC job or database search ran.

| Packet | Exact selection | Result |
| --- | --- | --- |
| check001 | `tests/test_native_protein_structure_local_resource.py` as retained before the added recovery test | 36 passed in 267.55 seconds |
| check002 | Added reservation-recovery test plus complete `tests/test_practical_execution_state.py` | 25 passed in 12.24 seconds |

These are 61 distinct checks: 37 new protein/resource checks and 24 existing
practical-record regressions. Check002 adds one test; it does not rerun the
36 check001 cases. Its remaining 24 cases validate ordinary assignment/receipt
semantics without native science.

The production code under test is identical in both snapshots. The second
snapshot's test file adds only the prepared/submitting recovery case. Complete
executed pins are `check001/source_pins_before.json` and
`check002/source_pins_before.json`; final owned-file pins are
`handoff_source_pins.json`.

## Actual native work versus injected cases

Actual resource actions used `PracticalResourceEpisodes.execute`, persisted
PracticalState receipts and real Store/Journal publications, with scripted
selected actions. All four operation/mode bindings invoked the real C390 driver
and scientific worker on tiny synthetic PDB structures:

| Operation/mode | Actual retained native result |
| --- | --- |
| inspect | One chain with 4 atoms |
| extract_sequence | `AGST`, with complete sequence/residue-map files |
| compare / fit_then_evaluate_ca | 4 mapped pairs; evaluation RMSD 1.6480662780998447e-16 Å |
| compare / evaluate_declared_transform_ca | 4 mapped pairs; evaluation RMSD 0.0 Å |

The structural correspondence includes distinct fixed residue 10/10A and moving
101..104 numbering. The examples are synthetic test inputs, not observed biology.
Exact result paths and reported values are in `native_examples.json`.

The failure/retry case genuinely changed an input after its selected digest was
fixed. The real C390 driver returned 1 and sealed a failed bundle with
`input_digest_mismatch`; its worker never started, so the bundle truthfully has
`worker_argv=null` and worker `returncode=null`. After the test restored the exact
original input bytes, a separate explicitly selected retry created another
attempt and its real worker completed with 0. The original failed bundle, logs,
request and receipt remain unchanged. Reading the original failed handoff after
that retry still observes its original execution. No native failure was hidden
or replaced.

Injected engineering cases cover unknown/cancelled/absent-returncode/killed or
successful lifecycle states, wrong retry ID, wrong receipt attempt ID/key/path,
changed plans, prepared/submitting recovery callbacks, binary/non-log output
bytes, an invalid-but-present bundle, path symlinks and wrong request identities.
These establish refusal, availability and protocol behavior; they are not claims
of real cancellation, OOM, scheduler or native scientific failures.

An actual ordinary generic local job also ran through the same resource binding,
status/collect/progress route under the same limits and produced its original
stdout. It was not routed through the protein driver. Actual start/status/collect
and monitoring replay used saved receipts without another launch or status read.

## Source pins

| Source | SHA-256 |
| --- | --- |
| practical_execution_records.py | b7a67e93026ae5bc75d6430dbc71e1dc4314a3707d359319bc3436ae9ca9ebbd |
| practical_execution_operations.py | d32e936e13d56b655176720ed2053b2a2a87ef23a5f799c4b5ee39e374206421 |
| execution_progress.py | 51b8f955421f3338d11d0ce2873ad525e4f064d76adc91f69713d1c21ea490c0 |
| Final test_native_protein_structure_local_resource.py | d755fcd59c51c46caadc798fe197c2ecefd4f397879c683e5d044a1647fabd48 |
| Reused native_protein_structure_contracts.py | 13e1f7c4e9e60fed6283ab66aea03dd3b54de4767941d6509f496c2188cdaea0 |
| Reused native_protein_structure_local.py | 62353bbce4971b0a3d5742693899ba9c0f398a4912014329a648b312d2210805 |
| Reused native_protein_structure_driver.py | 96de11758185f516b1b9a991c5d3b3f5b2dc0c3a392a70911b04a5ef301d9fee |

## Limits of this increment

The harness uses the existing resource action binding and real native lifecycle;
it does not run a model-driven episode or the full scientific parent → launch →
local child → result host → typed parent return chain. It deliberately leaves
its declared practical output endpoint unsatisfied to test later status/collect
selections, so it claims no new episode-level terminal-estimator result.

Original scientific operand authority, received-use permission, complete C392
capture integration, result preparation/publication, typed scientific return,
parent delivery, saved-sheet recalculation and full selected-tool integration
remain outside 405. Root and the corresponding lanes own those ports. Bundle
availability, native success, capture completeness, scientific availability and
requested delivery completeness remain separate. No progress-accounting row was
edited and no tool acceptance is claimed.
