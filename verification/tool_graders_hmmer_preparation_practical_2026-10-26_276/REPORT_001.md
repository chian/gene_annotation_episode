# Workload276 — exact local HMMER preparation binding

This is the L1 implementation and verification record under frozen contract261.
The immutable original objective and all 16 principles were read in full and
reread before handoff. Its SHA-256 remains
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The full 308-row goal is unchanged. No permanent design or progress record was
edited by this workload.

## Implementation

- Practical assignments accept P1's exact preparation request schema and
  validator. The local configuration validates I1's exact program/mode/software
  bindings. A preparation request must have a local resource and its original
  resource identity; mismatched bindings and caller allocations are rejected
  before native work.
- Only selected `practical.job.start` dispatches to
  `prepare_local_hmmer_preparation`; the existing durable lifecycle owns native
  start/resume. Ordinary preparation commands keep their existing behavior.
  Explicit retries preserve the original failed attempt and create a distinct
  selected attempt. Replays restore the original receipt without native work.
- Requested-job facts and progress observations validate the original P1 plan.
  Claimed output paths come from that plan's actual selected outputs and bundle,
  rather than unrelated assignment predicates. Observations retain the selected
  execution identity even after a later explicit retry.
- Declared `hmmer_binary` stdout is exposed as availability, bytes and writer
  closure only. It is never opened as a log by the practical status/progress
  path. Selected stderr and text-mode stdout retain ordinary log behavior.
  C1 still retains complete binary bytes and both stdout/converted-model role
  associations.
- The existing target descriptor advertises the V1 projection catalog and
  exact selectors/fact sources. Preparation result alternatives are status and
  collect, with the R1 collector's exact implementation name and return fields;
  there is no generic file-read parser alternative. Scientific annotation score
  remains false.

No episode type, private decision loop, credit formula, controller rule,
continuation rule, timer or automatic acquisition was added. Existing practical
receipts record outcomes; the existing progress provider records monitoring
observations. The new tests use these paths rather than a standalone helper.

## Verification

Both batches ran through `run_tests.py` and the existing `local_jobs` lifecycle
with memory 21474836480 bytes (20 GiB), scratch 4294967296 bytes (4 GiB), and
wall_seconds=null. Their receipts confirm cgroup memory/swap enforcement and
runtime_max=infinity. Existing regression fixtures retained their own smaller
caller allocations. Every file listed in each batch's `intent.json` remained
unchanged during that batch; see `source_stability.json`.

| Batch | Result | Scope |
| --- | --- | --- |
| check001 | 40 passed, pytest 34.89 s; service 35.538655940 s | New retained/native/practical/progress integration suite |
| check002 | 100 passed, 1 failed, pytest 321.44 s; service 322.202960213 s | Existing practical state, operations loop, receipts, execution progress, yield and runtime suites |

`check002` is not a green batch. Its failed existing test is
`test_practical_runtime.py::test_parent_receives_only_requested_verified_completion_and_receipts`.
The fixture's child completion, receipts and exact-zero future-gain assertions
passed. It then selected `state.query`, although the actual annotation parent's
schema has only reason/wait/episode_child/redeliver_report. The saved next call
contains action_contract/schema_validation(anyOf) feedback, and the fixture's
fixed two-call assertion fails on the retry. There was only one completed
parent action. `check002/failure_analysis.json` records the actual response,
allowed kinds and feedback; the original SQLite journal and failure output are
retained. The root owner was informed; this workload did not edit shared tests
or change allowed parent actions to accommodate the fixture.

### New suite: retained data and controlled contexts

- All 26 exact retained requests validate through both the assignment schema and
  configured practical operations. These are the actual267/check005 requests,
  with current hmmsim requests taken from270/check005. This matrix does not
  rerun all 26 native modes. Native preparation/start/resume/status calls are
  forbidden during these checks, establishing no pre-choice execution.
- Eight invalid cases cover unbound mode, software digest, version, missing
  resource identity, HPC request, argv mismatch, changed caller allocation and
  duplicate binding.
- A controlled reservation test freezes a real P1 reservation while suppressing
  native submission. It checks wrong run, episode, operation, attempt, resource
  and invocation identity. This case is not a native execution.
- Binding contexts, chosen actions, SQLite episode/action rows and the input
  sequence are engineering fixtures. They exercise actual
  PracticalResourceEpisodes, action receipts, ExecutionProgressProvider and the
  shared ProgressProvider. They do not establish model decisions or full shared
  Workflow commissioning/admission for this family.

### New suite: actual local native executions

There were five HMMER 3.4 executions through `practical.job.start`:

| Program/mode | Executions | Actual result |
| --- | --- | --- |
| hmmconvert/binary | 1 | Exit 0; 2725-byte model output |
| hmmstat/summary | 1 | Exit 0; exact selected text log window retained |
| hmmbuild/build_alignment | 1 | Exit 0; caller `--cpu 2` retained in selected options and realized argv |
| hmmfetch/single_key | 2 | Both exit 1 for explicitly selected absent key NO_SUCH_MODEL_276; second execution requires the first failed execution identity |

One additional ordinary `/usr/bin/printf` preparation command ran through
`practical.command.run`; it did not create a HMMER plan or requested-job fact.
The outer pytest job is distinct from these six submitted inner native jobs.
The separate reservation fixture created a prepared handle without submission.

The binary bytes have SHA-256
`4d3f4b96321b7383137f3b19814fb1c1d7310e247da4dc0b84d2f879a2cd565c`.
During actual progress observation and practical status, opening that binary
path is forbidden by the test. Both operations succeed, expose its 2725-byte
size and writer closure, and expose stderr alone as a log. C1 subsequently
returns the full identical bytes under two distinct role associations sharing
one artifact reference. The recorded duration is 0.738105131
`systemd_service_wall_seconds`; it is not algorithm-only time or queue wait.
Full evidence is in
`check001/temporary/test_actual_binary_start_progr0/evidence.json`.

The binary case also supplies an unrelated output predicate. That path is not
claimed as a native output, the original completion predicate remains false,
and practical credit does not increase. Same-action and same-observation replay
preserve state bytes and forbid native prepare/start/resume/status/target reads.
The failure/retry case preserves the first bundle bytes, observes the original
failed execution after retry, and replays both original selected starts without
additional executions.

## Source custody

Full source/request hashes are retained in each batch's `intent.json`. Core
production/test SHA-256 values are:

| Path | SHA-256 |
| --- | --- |
| gene_annotation_episode/practical_execution_records.py | 3f613c9e0989bc6b95a2bf62345d65cd97a7ee16174212df371d1294e4c2c99f |
| gene_annotation_episode/practical_execution_operations.py | 233bafdccbdc0478a03b86fd372c454697fe61acb71ddce0e8e43ac8337fe42c |
| gene_annotation_episode/execution_progress.py | 80badf6f091c56c7788e12e47bae6ee72098313df6b94a4f48605629e3002445 |
| tests/test_hmmer_preparation_practical_integration.py | 3174e02c783a59dc2bec79eb1bd59895e12fd799ebd580deda8867f36f97a1b3 |

Native binary conversion used the installed 3.4 executable
`resources/software/infernal-1.1.5/hmmer/src/hmmconvert`, SHA-256
`906291d58ec6733f7ec48537c4e907811da5cf232a0bebcccf52f272eaf4fafd`.
Each retained plan/bundle records its exact executable/version/digest, request,
resource, allocation, run, episode, operation and execution identity.

## Remaining scope

API and HPC HMMER preparation deployment are explicitly unfinished. No remote
access, software installation or database BLAST was attempted. This workload
does not claim scientific grader/calculator verification, R1 typed return
admission, G2 publication, model-driven execution or the complete shared episode
path. Root owns the shared Workflow verification and publication; workload275
owns result/return/failure integration. The descriptor alone is not proof that
those later paths have completed.
