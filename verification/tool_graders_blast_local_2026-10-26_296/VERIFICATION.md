# Workload 296: local paired BLAST lifecycle and complete capture

This records the implementation of CONTRACT_ADDENDUM_006.md. It does not change
the fixed BLAST scope, scientific calculations, episode structure, or accounting.

Implemented ports are `prepare_local_blast`, `local_blast_plan`,
`is_native_blast_target`, `validate_original_bundle`, `capture_local_bundle`,
`original_source_payload`, and `publish_original_source`. Configuration and the
practical assignment/start/status/collect paths have narrow `native_blast`
branches. The current Python interpreter invokes the existing 294 producer
through the ordinary durable native lifecycle. Preparation does not dispatch.

The reservation checks original run, episode, operation, attempt, resource,
request, workspace, driver command, worker request bytes/environment, caller
policy, control paths, and producer-owner agreement. Start/status/collect expose
the original attempt and operation identities for the existing progress reader.
Status reads selected native stdout/stderr and report/bundle availability; it
does not parse scientific results. Explicit retry requires the original failed
execution and a known nonzero return code. Uncertain execution is not replaced.

Capture uses the existing content-addressed Store file APIs. It preserves the
bundle, both original staged inputs, and every sealed output, qualifying byte
hashes, lengths, roles and paths. Wrong bytes remain invalid artifacts. Missing
or malformed bundles preserve valid staged inputs and unsealed output bytes
without treating those outputs as sealed originals. A failed native command can
have complete custody of its actual partial outputs. Scientific validity is not
inferred from complete acquisition. Capture intent, plan and receipt are durable;
replay qualifies retained artifacts and does not reopen the live job. Source
publication verifies the supplied bundle and artifact associations against those
retained bytes.

## Verification actually run

All tests and native executions used `.venv/bin/python` and the existing
`local_jobs`/`native_lifecycle` resource enforcement: 20 GiB memory, 4 GiB
scratch, zero swap, no wall cap. No software was installed. No database BLAST,
network search, API invocation, HPC job or configured-model run was performed.

| Retained run | Outcome | Scope |
| --- | --- | --- |
| `initial_contract_failure/` | 1 failed | Initial assignment schema rejected the new native request before its integration branch was added. |
| `lifecycle_first/` | 29 passed, 17.27 s | Five real paired programs, reservation/owner qualification, practical Workflow, original handoff, receiver and replay. |
| `capture_first/` | 55 passed, 69.61 s | Original manifests, complete files, partial/failure cases, tampering and replay. |
| `full_first/` | 86 passed, 1 failed, 153.84 s | Test expected an owner error for the malformed digest `other`; target-schema validation correctly rejected it earlier. Fixture corrected to a valid wrong SHA-256. |
| `final_checks/` | **117 passed, 99.20 s** | 93 workload tests plus 24 existing practical-state regressions, including the subsequent custody/source hardening. |

The groups overlap and are not additive coverage counts. Every run retains its
command, stdout, stderr, native enforcement metadata and receipt. The final run
retains actual complete producer outputs and Store artifacts below its pytest
directory; intentionally corrupted fixtures remain labeled by their test names.

Fresh native executions in the final run:

| Program | Query/subject input bytes | Original JSON15 report bytes | Native return code |
| --- | --- | --- | --- |
| blastn | 269 / 271 | 1118 | 0 |
| blastp | 273 / 265 | 2715 | 0 |
| blastx | 267 / 105 | 2274 | 0 |
| tblastn | 104 / 269 | 2274 | 0 |
| tblastx | 266 / 268 | 9104 | 0 |

`native_examples.json` records the exact native bundle paths, input/output
identities, hashes, lengths, resource policy and verified cgroup for these five
executions. Inputs and executable identities reuse workload 294's selected
fixtures; this workload does not reinterpret their scientific measurements.

The actual `PracticalResourceEpisodes` Workflow selected `practical.job.start`,
closed after one original completing action at exact zero expected next gain,
and retained its Store handoff. A receiver selected `practical.job.collect` and
closed after one action. The original closed receipts remained unchanged. The
Store progress reader qualified the original handoff, and acquisition captured
all five file associations. Workflow and capture replay ran with native
start/resume/status forbidden and preserved one physical handle. A separate
capture replay still succeeded after the live attempt directory was moved out
of reach. These are real native execution and shared-loop engineering tests
with scripted decisions, not configured-model scientific reasoning.

`filled_workflow_example.json` and `filled_capture_example.json` retain these
concrete examples and their original evidence paths. The filled capture has
`bundle_validated=true`, `complete=true`, five artifact associations, zero
invalid artifacts and zero failures. Its query and subject are 269 and 271
bytes, stdout/stderr are separately associated zero-byte artifacts, and its
report is 1118 bytes. Their exact hashes are retained in that file.

Additional coverage includes wrong program/mode/software/resource/allocation,
owner and driver swaps, request rehashing, duplicate/swapped/escaped manifest
paths, inconsistent outcome/failure fields, invalid timestamps, missing bundle,
missing output, failed command, failed staging, wrong staged bytes, actual
zero-byte successful tabular6 output, synthetic malformed report bytes with a
matching synthetic manifest, symlink escape, retained-byte loss/corruption,
source/bundle swaps, receipt artifact swaps, original status/collect without
parsing, and selected confirmed-failure retry. Report corruption tests establish
custody/parser separation; corrupted bytes are not reported as native science.

## Scope of this handoff

Launch, original-owner qualification, native status, complete acquisition,
custody publication and offline replay are verified here. Root owns the
`ExecutionEpisodes`/progress/library assembly, numerical parser and calculator
consumption, scientific publication, requested typed numerical returns, and fixed
progress rows. This workload does not claim that end-to-end scientific return
integration is complete. Native parser/calculator work from 293/294/295 was not
modified or duplicated as proof of Workflow completion. Database programs,
PSI/DELTA/RPS/VDB and nonlocal resource bindings remain separate required work.

`source_sha256.json` pins the implementation, tests, affected existing consumers,
original immutable goal, and addendum 006 inspected for this handoff. The full
original objective and all sixteen design principles were reread after native
verification; all applicable 292 contracts were reread before handoff.
