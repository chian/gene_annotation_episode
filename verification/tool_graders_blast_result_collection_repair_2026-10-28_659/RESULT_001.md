# Collection repair 659 result

Implemented the frozen [port](IMPLEMENTATION_PORT_001.md) in native_blast_utility_results.py. A new explicitly selected collect prepares the original authenticated retained capture once when no actual parsed result exists. A preparation receipt with result_artifact_ref=null no longer prevents that selected work. Same-action replay stays immutable. Parsed partial and native-failed results remain reusable. Current requested facts suppress an earlier unavailable view only when a later parsed body for the exact same captured bundle exists in this result episode and assignment.

The exact production change is [CHANGE_001.diff](CHANGE_001.diff). No operation names, arguments, schemas, prompts, numerical policy, runtime, native lifecycle or other production modules were changed by this owner.

## Completed verification

Ten distinct tests passed across the bounded runs below, all with the same production file SHA-256. The complete final test file was not rerun: only previously failed cases were selected after fixture corrections. Earlier run failures remain preserved as facts.

| Bounded529 run | Recorded result | Interpretation |
| --- | --- | --- |
| check119_collection659 | 5 passed, 3 failed, 2 setup errors; rc1 | Five projection-boundary cases passed. Other cases stopped on the synthetic v2 binding missing its required variants member. Fixture corrected. |
| check119b_collection659 | 4 passed, 1 failed; rc1 | Selected-host repair, repeated failed selections, and both parsed-partial/native-failed cases passed. Shared Workflow stopped because the synthetic handoff body was text rather than receipt JSON. Fixture corrected. |
| check119c_collection659 | 0 tests; rc4 | Invocation incorrectly included a second tests/ prefix. The failed invocation is retained; no test claim is made. |
| check119d_collection659 | 1 failed; rc1 | Shared Workflow fixture confused the provider's REASONING role with the episode role. Fixture now reads execution_assignment as the existing provider helper does. |
| check119e_collection659 | 1 passed; rc0 | Full selected shared Workflow case passed in 250.66 seconds; final bounded service terminal and quiescent. |

All five collected runs report unchanged source, dependencies, standard library and binaries; outside_modules=[] and unbound_mappings=[]; retained fixtures and native libraries unchanged. They use check005 dependencies, memory_max=21474836480, memory_swap_max=0, scratch_bytes=4294967296 and runtime_max=infinity. Scratch is the existing runner's monitored allocated-byte limit with possible sampling overshoot and per-file RLIMIT_FSIZE, not a filesystem quota. Final observed scratch was 621150208 bytes. Final service unit: gene-local-job-de542dc7f3e9487da08096112450e2ef.service.

[VERIFICATION_001.json](VERIFICATION_001.json) records exact cases, durations, complete receipts, audit outcomes, selected source pins and hashes of all evidence files. [SOURCE_SELECTED_002.json](SOURCE_SELECTED_002.json) records final source and relevant loaded-module pins. [READ_TRACE_001.md](READ_TRACE_001.md) records affected consumer inspection and responsibility tracing.

## Verified behavior

- The first explicit collection retained the injected original ambiguity failure with nonnull preparation and null parsed result. The old receipt, action, source and action-directory files remained unchanged after repair.
- Replaying that operation returned its original result without another parser or acquisition. Existing cached capture validation remains active; no original source file was reacquired. The test deleted its synthetic original input/attempt directories and forbade acquisition/native calls before repair and replay.
- A new explicit collection reused the original observation and retained capture, called preparation once in its new directory, and linked reused_from directly to the original acquisition. In the controlled aggregate fixture, requested typed fields were 3 sequences and 24 symbols, with 12 retained materializations and an available prepared-database manifest. These fixture numbers are engineering assertions, not acquired scientific measurements.
- Current requested facts and the parent's validated typed return contained the repaired status and selected data without the former 7 missing rows and 1 failure. Both bodies remained available in own history, with record grants retained.
- The original captured bundle earned acquisition credit once. Shared Workflow recorded exactly 2 result actions, 2 local observations and 2 estimation contexts; the local yield history was [2, 0]. Validated completion set the next expected-gain band to exact zero immediately. There was no extra result turn.
- Reconstructed host replay and frozen parent-return validation needed no parsing or projection worker and left the saved database unchanged. A new operation on the completed assignment was rejected by the existing completion rule.
- Three separately selected failed attempts each parsed once and linked directly to the original acquisition. They never manufactured new observations of native execution or reacquired files.
- Parsed partial results were reused for both native return codes 0 and 2. Projection-boundary cases retained different captured bundles, an unavailable body without a later parsed replacement, useful parsed partial bodies, and a later unavailable body following an earlier parsed body.
- _prior found the actual parsed body when the immutable index encountered an earlier failed preparation first. No numerical-quality preference was introduced.

## Pins and handoff limits

Production native_blast_utility_results.py SHA-256:
e4fd0825f2826b34ceac942183d20c7a498df8e341e535c51477b616e010f929

Final new test file SHA-256:
cc979e77994ba9074ddfae9e965ad65159338d2839927cf91a172e40768405d0

Frozen port SHA-256, unchanged:
f5e799f3365a3e63f475e515095f3872cde322094a75ffe96a79dee2a85d4422

The tests use controlled producer bytes, the actual deterministic result worker/publication validators inline under the outer bounded service, and scripted choices through shared Workflow. No native BLAST executable, external service or configured-model investigation ran. This worker did not read or mutate original113b acquired data or saved state. Authentic interrupted-tree continuation, original expectations/history preservation and final scientific-parent delivery on that saved run remain root/654-owned verification. This result completes the assigned implementation port and its controlled checks; it does not claim completion of the user's overall tool-grader objective.
