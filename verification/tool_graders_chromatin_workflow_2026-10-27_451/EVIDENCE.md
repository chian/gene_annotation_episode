# Cooler Workflow verification status

The original six-case Workflow workload passed on check001's immutable source
snapshot. The current seven-case workload has not yet passed: check002 exposed a
shared response-transport schema contradiction before native execution.
check003 reached the repaired boundary and then terminated with SIGSEGV during
an incomplete periodic stack sample. check004 is running with only that periodic
test fixture removed and the same production snapshot. The separately owned
transport repair passed 56 focused checks before the source freeze. No fixture
bypass or production edit is part of this packet.

| Attempt | Actual outcome | Scope |
| --- | --- | --- |
| [check001](CHECK001_EVIDENCE.md) | 6 passed, 0 failed; terminal and quiescent | Original acquisition, explicit saved calculation after source-copy removal, received authority, credit and immediate practical endpoint, closed replay, actual missing-p1 partial acquisition |
| [check002](CHECK002_TRANSPORT_DEFECT.md) | 0 passed, 2 failed, 5 setup errors; terminal and quiescent | Seven current cases, including the new composite resolver assertions and complete-empty sparse population case; stopped at launch-to-local provider schema validation |
| [check003](CHECK003_CRASH.md) | Interpreter return code -11; terminal and quiescent; no pytest result | Repaired launch_local commission admitted; no native Cooler job started |
| check004 | Running; no final result yet | Same seven scientific/authority cases and production/input snapshot; periodic diagnostic fixture removed |
| probe001 | Return code 0; terminal and quiescent | Retained original-domain selected commission validates |
| probe002 | Return code 0; terminal and quiescent | Actual provider schema reproduces the required-member failure |
| probe003 | Return code 0; terminal and quiescent | Explicit null violates the exact software literal and survives decoding into an invalid original-domain value |

All attempts use the existing bounded local lifecycle with 20 GiB RAM, 4 GiB
scratch, zero swap, and no wall-time budget. Executed source and interpreter pins
were unchanged for all collected attempts. Failed attempts remain intact. The three probes
read the original check002 Store in SQLite read-only mode and did not acquire
scientific data or commission Workflow work.

check003 command:

```sh
.venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_bounded.py launch check003
```

Original handle: `check003/handle.json`; unit
`gene-local-job-4182b72b5217486ab127732d6f7d9ee6.service`.
The full manifest is `check003/source_pins_before.json`. The frozen runtime SHA256
is `5792936769bea8c91dcb4a51422f14f5d7bf10c08b22bc52d1a31038837954cf`.
The test and fixture helper were unchanged from check002. The repeated stack
sample was incomplete at the interpreter crash and is not proof of crash origin.

check004 command:

```sh
WORKFLOW451_PRODUCTION_SNAPSHOT=/home/chia/repos/gene_annotation_episode/verification/tool_graders_chromatin_workflow_2026-10-27_451/check003/source_snapshot .venv/bin/python -B verification/tool_graders_chromatin_workflow_2026-10-27_451/run_bounded.py launch check004
```

Original handle: `check004/handle.json`; unit
`gene-local-job-67594a2eaa654fa2a62a6a51fac644d6.service`.
Its full snapshot differs from check003 only in the owned test (sampler removed),
administrative runner (explicit snapshot origin), and scope note. Production
packages, supplied inputs, publication, and fixture helper are byte-identical.
Pytest's separate fatal-fault reporting remains enabled.

The root agent takes over monitoring and collection of this existing handle at
the live-run [handoff](HANDOFF.md). At handoff it is active with zero restarts;
the first actual Cooler producer exited0 in9.096802932s. Pytest is still in the
first shared fixture, with no completed test results. The handoff records the
exact collect command, source pins and all seven remaining assertions.

check001 measured E–P contact 6, same-distance mean 4 (8/2), and fold 1.5;
E–Q contact 0, mean 0 (0/1), and a null fold qualified as zero_denominator.
Changing the saved threshold from 2 to 1 changed only the E–P threshold flag.
The original result received one caller acquisition unit of 2; saved calculation
received 0. Partial p1 loss preserved p0 values and the one actual job unit, with
p1 explicitly missing and practical completion false.

The current all-empty sparse case and composite shared-resolver assertions
remain unverified. These records establish only the stated synthetic Cooler
route and exact snapshots. They do not establish HIC support, biological
validation, HPC deployment, model-facing templates, or completion of the full
original tool-library goal. No inventory count changes are authorized here.
