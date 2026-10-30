# Two knowledge fixture repairs

Only `tests/test_tool_knowledge.py` and this verification directory were changed.
No production runtime, root permission, library, scoring, goal or accounting
change was made.

The first fixture preserves its existing outcome, report, execution and credit
assertions, explicitly checks the root's empty tool catalog, and checks the
manual link on `fixture.measure` in the actual receiving child's catalog.

The recovery fixture now commissions an ordinary improvement child through the
existing runtime helper. That child completes the selected read and has one
recorded observation before interruption. After source mutation, recovery must
reuse the original read: a patched `ToolKnowledge.read` raises if any replacement
read occurs. The original full action row (including outcome, credit and timing),
observation row, completed model-call row, episode identities/assignments and
all frozen library bytes must match exactly. The pending decision also receives
its exact original context. The child then selects metadata retrieval, returns
only `{"changed": []}`, and the root makes the existing synthetic reasoning
commitment. The resulting four observations have deltas `[0, 0, 0, 1]`; the read
has credit zero and no record references. There is exactly one read action and
zero `FixtureTools` executions in this fixture.

## Executed evidence

| Check | Selection | Actual result |
| --- | --- | --- |
| check001 | Two original knowledge fixtures, before edits | 2 failed, 14.50 seconds; reproduced the original IndexError and missing-observation TypeError |
| check002 | All 6 knowledge tests, 4 existing root-boundary tests, 3 existing runtime recovery tests | 12 passed, 1 failed, 87.51 seconds |

All six knowledge tests passed. All three runtime recovery tests passed. The
root rejection, child-return discovery and metadata replay checks passed.

The separate unchanged failure is
`test_root_episode_boundary.py::test_metadata_then_real_child_translation_typed_return_and_root_reason`.
Its recorded commission uses `scientific_process_selection_v2`; the actual
schema requires v3 and `evidence_axis`, `thought_pattern`, `child_tool_info`.
The commission is rejected. Only the root exists and no runtime action was
completed. Its next scripted translation is rejected at the root, and the
following callback raises `KeyError: last_local_outcome`. This fixture is outside
the assigned edit scope and remains unchanged. The original failed log/XML and
the exact recorded feedback are retained.

Both checks used the existing `local_jobs` adapter, `.venv/bin/python`, absolute
test paths and isolated check directories, with 20 GiB RAM, 4 GiB scratch and
no wall-time cap. Each `receipt.json` records the command, policy, resource
metadata, output paths and source hashes. No hashed source changed during either
run. `EVIDENCE_001.json` records individual test results and the durable recovery
facts; `OUTSIDE_SCOPE_FAILURE_001.json` records the separate failure diagnosis.

## Exact identities

The test-file SHA-256 changed from
`01fd91cd0a0c17290147bc2006d0c3af92247a745e14c7f56fe1ea5d247f7465`
to `6befe59ef19266f168734bcbf4f303a338b363eb523d054da43c732ff15fd223`.
No other hashed existing file changed between the two checks.

The saved before and after recovery snapshots are byte-identical, both SHA-256
`36a2e88f079405cb095b4f5d01fe04dce696da1ea2a1e3fb8983ba6308e806b3`.
They are retained in
`check002/temporary/test_interrupted_read_recovery0/recovery_before.json` and
`recovery_after.json`. The original returned text is `Second λ line\n`; the
source is subsequently `Future revision\n`, while the run-frozen library
version, identity, digest and exact bytes remain original.

These are scripted engineering checks using the declared fixture controller
and credit function. They do not establish scientific scoring policy, detached
worker reconstruction, configured-model behavior, API/HPC execution or overall
tool-grader completion. The original immutable objective and all 16 principles
were read verbatim after source study and again before handoff.
