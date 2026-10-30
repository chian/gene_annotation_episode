# GenomeAlignment selected Workflow verification

The original Workflow closed naturally. Its original pytest command exited 1:
**one test passed and one failed in 15998.186 seconds (4:26:38)**. The failure is
the fixture's role-filter assertion at line 580: `Choices.complete` receives
model role `REASONING`, whereas the test filtered for episode roles. The four
remaining tests were not executed because the original command used `-x`.
This is the authoritative original outcome, not a six-test pass.

The separate root-owned candidate006 passed **all six tests in 971.274 seconds**
at its recorded source revision. Its history remains separate from this run.
The corrected candidate identifies calls by actual episode ID, expects the
saved association kind `task_result_manifest`, and restores parser owners after
explicit recalculation before discovering aliases for the strict replay barrier.

## Original execution and source history

The exact command is in [RUN_COMMAND_001.json](RUN_COMMAND_001.json). It ran once
in session 40024, pytest PID 1056858, using unique directory
`runs/mauve-v4-d00v9ick`. No timeout, restart, interruption, controller change,
source-pin replacement or in-place fixture correction occurred.

[TERMINAL_RECEIPT_001.json](TERMINAL_RECEIPT_001.json),
[pytest_001.xml](pytest_001.xml) and [pytest_001.txt](pytest_001.txt) retain the
actual result. [FROZEN_TEST_SOURCE_001.py](FROZEN_TEST_SOURCE_001.py) preserves
the exact original fixture, including its mistakes, with SHA256
`0c86be100dbd4daf2f66f521740af43072f647670e67c419075bcc02ed720d8d`.

Both original final source guards contain **299 used paths**, no used changes,
and no used path missing a prospective hash. All **814 original before-hashed
paths** remained unchanged. The independent terminal audit also compared the
used before/after values and rehashed the then-current files successfully.
See [TERMINAL_SOURCE_AUDIT_001.json](TERMINAL_SOURCE_AUDIT_001.json) and the
original run's `SOURCE_GUARD_WORKFLOW_CLOSED.json` and
`SOURCE_GUARD_AFTER_TESTS.json`. Forty-one unrelated new proteome Python/JSON,
test and fixture files are listed separately and are not claimed as tested.

Original adapter pin:
`3a3a9f046b4f3ae3e8fa32812422f0937b95fddc5e6e216caa696a173136bf90`.
Original scientific binding pin:
`3d24bf5740f2b28bc8aa17d34c9ee0ccb680f58875eb409c837dd990cfe45059`.
These remain historical facts. Later root-owned working-tree changes are
prospective and are not changes during this closed run.

`pyproject.toml` was outside the recorded source closure, although pytest named
it as startup configuration. Its pre-change bytes are retained in
[PYPROJECT_AT_CLOSURE_CHECK_001.toml](PYPROJECT_AT_CLOSURE_CHECK_001.toml).
Root's packaging-only changes and unchanged pytest configuration are recorded
separately in [CONFIG_CHANGE_001.json](../tool_graders_bvbrc_proteome_packaging_2026-10-25/CONFIG_CHANGE_001.json)
and [CONFIG_CHANGE_002.json](../tool_graders_bvbrc_proteome_packaging_2026-10-25/CONFIG_CHANGE_002.json).
No before hash or original guard was amended to accommodate them.

## Actual path and retained measurements

The real `Workflow`, shared `method_loop`, execution service factory, registry,
scientific library and original commissions ran. Existing A101 and P01 entries
filled `evidence_axis` and `thought_pattern`; actual `child_tool_info` selected
`bvbrc.genome_alignment` and `material.parse`. The original first test passed
the selected-library, three-slot, child-ownership and HTTP-route assertions.

Scripted choices and loopback AppService/Workspace replies are controlled
fixtures. Production primitives performed eight HTTP requests through prepare,
submission, status, task-info, Workspace metadata, capabilities and downloads.
The task-info UUID → metadata receipt row → job-result manifest → output member
chain reached actual custody, native parsing, D sheet/calculators, E publication
and F typed returns. These components were not replaced with fabricated success.

The retained Mauve v4 file has 1007 bytes and SHA256
`a0e700b702070ebd061f6ca5c5b0d9338ad8c330ad16b94c9a0090041cd8cd88`.
The closed original records contain five native intervals, complete acquired
bytes, matching full sheet/components, and the following requested values:

| Measurement | Saved value | Meaning |
| --- | ---: | --- |
| Native member 0 coverage | 690 / 693 = 0.9956709956709957 | Explicitly selected native segments; native declared length denominator |
| First selected segment gap count | 0, available | Measured zero remains distinct from missing source symbols |

Coverage retains union `[[0,578],[581,693]]` and complement `[[578,581]]`.
Original maps are empty, XMFA source inputs and observed argv are null, and
genome census is unknown. The native artifact's object association is
`task_result_manifest`; byte-version status remains unknown. E retains 18
missing requirements and 27 diagnostics. No producer or staged-input witness
was invented to erase them.

Both original receiving boundaries preserve the exact requested frozen values:
results → scientific process, including its duplicate delivery, and scientific
process → root. The latter contains exactly numbers, missing requirements and
qualifications. These closed records were inspected in
[ORIGINAL_WORKFLOW_INSPECTION_001.json](ORIGINAL_WORKFLOW_INSPECTION_001.json).
That inspection is explicitly distinct from the four pytest cases that did
not run after the original failure.

## Original accounting and continuation

All five episodes closed with state `yielded`. The original journal contains
26 actions, 26 observations, 27 scripted provider calls, five report attempts
and 219 record receipts.

| Role | Own actions | Observations | Scripted provider calls | Final actual gain | Future estimate at closure |
| --- | ---: | ---: | ---: | ---: | --- |
| Root | 8 | 8 | 8 | 0 | Ordinary estimator upper bound 0.07619158557694622 ≤ cost 0.1 |
| Scientific process | 8 | 8 | 9 | 0 | Same ordinary estimator bound |
| Launch | 1 | 1 | 1 | 2 | Exact zero |
| API | 2 | 2 | 2 | 2 | Exact zero |
| Results | 7 | 7 | 7 | 3 | Exact zero |

The extra scientific provider call requests redelivery and creates no own
action or observation. Root/scientific gains are the caller's explicit zero
engineering credit; their estimator was not replaced. The practical roles
preserve their last positive gains and close immediately at exact-zero future
expectation, without an extra zero action. The results episode also retains
its earlier gain for acquiring the manifest while scientific output was still
missing. Full original credit arrays are in the inspection receipt.

## Separate candidate replay and recalculation evidence

[CANDIDATE_EVIDENCE_LINK_001.json](CANDIDATE_EVIDENCE_LINK_001.json) records the
read-only inspection of root's [candidate006 pass receipt](../tool_graders_form_reference_validation_2026-10-25/CANDIDATE_WORKFLOW_PASS_003.json)
and actual XML. Both candidate source guards have 300 used paths with no changes
or missing before hashes. Its strict saved replay blocked 173 scientific
implementations/aliases plus native, process and network entry points. Saved
own replay, reads, Workflow redelivery, both-parent validation/admission and
forged-value/unrequested-field rejection passed with no HTTP calls and no
change to its 26 actions, 26 observations, 27 calls, five report attempts or
215 receipts. These are that candidate's counts, not the original run's counts.

Separate explicit recalculation returned an equal sheet for the same plan.
Removing the first selected 13-base segment produced 677/693 coverage while
preserving the original 690/693 sheet. The candidate also passed the retained
partial-publication and numeric-action-order assertions. None of these later
test passes is attributed to the original `-x` run.

## Presentation and execution limits

This is a controlled engineering verification with retained native output.
It establishes neither live BV-BRC access, new Mauve execution, configured-model
execution, local scientific executable/HPC deployment, nor a biological
annotation. The fixture's task association with the retained native bytes is
explicit. Worker160's separate host verification covers the other native
formats; this single v4 Workflow does not replace that evidence.

`Choices.complete` bypasses `ModelConnection` and `providers._presentation`.
Scientific text is rendered separately from captured legacy contexts. The
provider's scientific bootstrap/update/lookup/legacy branches use the real
scientific renderer; other roles retain JSON fallback. This fixture does not
prove a configured-provider exchange or all-role TASK/STEERING compliance.

Both the original and candidate saved science presentations visibly include
690/693 and zero gaps with recurring detailed TASK. However, all nine captured
contexts lack `action_yields`, making the test's conditional yield-column
assertions vacuous. Six later STEERING blocks have 326 lines / 20053 bytes and
say “Own completed actions: None supplied.” Parse/source/material tracking
also remains visible. Thus passing the candidate tests does not establish
complete curt steering or tracking removal. This is retained as
[PRESENTATION_LIMIT_002.md](PRESENTATION_LIMIT_002.md) and root's
`CONTROLLED-PRESENTATION-LIMIT-030`, rather than patched around in this worker.

The one root-authorized cold lookup profile on a private read-only copy is
documented in [PERFORMANCE_DIAGNOSTIC_001.md](PERFORMANCE_DIAGNOSTIC_001.md).
It returned true in 11.51230967999436 profiled wall seconds with 30,977,136
calls and unchanged copied records. It was not another Workflow, an original
run restart or a forecast of total completion time.

Only the owned new test and this verification directory were edited by this
worker. No production, shared, evidence-axis, literature, W05 or existing test
source was edited. After terminal inspection, the immutable objective, all
16 design principles, and complete accepted 014/015/016 and D/E/F contracts
were reread before this handoff.
