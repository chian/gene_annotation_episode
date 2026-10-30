# Two runtime replay regressions, 2026-10-24

Both original failures precede the completed-controller-input reuse change.
They reject their first selected operation before reaching execution or
`Workflow.controller_value`. The approved repair changes only the two named
functions in `tests/test_runtime.py`; production behavior is unchanged.

## Original failure and comparison

The original selected suite remains in
`../runtime_original_controller_input_2026-10-24/`: 28 passed, 2 failed.
`test_runtime.before.py.txt` and `original_test_functions.json` retain the
original test source. The original test-file SHA256 is
`f12351de1656c4597f5d8860b6ea9fc2636507bd82b8fe9cfacca3c8a96c008a`.

`diagnose.py` ran those two tests unchanged in two fresh Python processes:

```text
.venv/bin/python verification/runtime_replay_regressions_2026-10-24/diagnose.py current verification/runtime_replay_regressions_2026-10-24/current
.venv/bin/python verification/runtime_replay_regressions_2026-10-24/diagnose.py before_controller_input_reuse verification/runtime_replay_regressions_2026-10-24/before_controller_input_reuse
```

The second process removes only the new completed-observation lookup block from
`Workflow.controller_value`, in memory. Its saved method and exact diff are in
`before_controller_input_reuse/`. This compares otherwise-current code with and
without that single change; it is not an assertion about an unavailable complete
historical checkout.

| Variant | Original tests | Fixture executions | Controller-value calls | Actions / observations / semantic operations per test |
| --- | --- | --- | --- | --- |
| Current | 2 failed in 9.45 s | 0 | 0 | 0 / 0 / 0 |
| Without completed-observation reuse | 2 failed in 9.35 s | 0 | 0 | 0 / 0 / 0 |

Each variant retains exact commands, timestamps, before/after hashes, pytest
output, JUnit results, function-call traces, SQLite databases and complete table
projections. `comparison.json` records the quantitative comparison. Both runs
used the same test and production source bytes. The runtime SHA256 throughout is
`f15783d6068cfda5adbb3a52e91efdf7dd94b85dd7e59e335303218ae3d8cc04`.

## Exact rejection and iteration path

Both fixtures first return this selection in the annotation root:

```json
{"kind":"tool","tool":"fixture.measure","arguments":{"result":"completed","page":0}}
```

`_run_bound_workflow` records `root_episode_commissioning_v1` for the new run.
`restricted_root` identifies the annotation root; `Workflow.catalog` returns
`[]`, `action_schema` removes tool branches, and `permits_common_action` also
rejects root tool execution. The actual saved selection branches are `reason`,
`wait`, `child`, `episode_child` and `redeliver_report`.

`DecisionSource.apply_response` validates the response against that schema and
returns `None` with this feedback:

```json
{"status":"invalid","category":"action_contract","detail":{"code":"schema_validation","issues":[{"path":[],"rule":"anyOf"}],"more_issues":false}}
```

`DecisionSource.next` continues to a second model request without completing an
action. These scripted injected providers use `decision_protocol=None`; neither
a composition lookup nor a decision-exchange loop occurs.

For `test_resume_recovers_published_operation_before_runtime_response`, the
single-response iterator is exhausted on that second request. Python raises
`RuntimeError: coroutine raised StopIteration`, which does not match the expected
synthetic crash. The result-publication crash hook is never reached.

For `test_caller_native_resource_changes_preserve_original_history_on_resume`,
the second scripted response is its explicit `KeyboardInterrupt`. The test then
finds zero observations where its obsolete direct-root-tool setup expected one.
The initial resource snapshot is present and correct; no completed operation or
resource-change replay has occurred at that failure.

Neither case reaches `DecisionSource.execute`, native dispatch, semantic
publication, controller input, observation or return admission. The recent
controller-input reuse block cannot cause either original failure.

## Approved test-only repair

The root continues to have an empty tool catalog. It commissions the existing
`improvement` child, which owns `fixture.measure` through the same shared
`method_loop`. Its parent-defined return form contains typed observation
references populated from `last_outcome_refs`.

The publication-interruption test selects one child and one child tool action.
It preserves the original crash hook after semantic publication but before
runtime result publication. Before resumption there is one semantic operation,
an unfinished child action and no observations. Resumption makes no provider
call, reuses both episode identities and the same operation key, and invokes the
idempotent fixture twice in total while publishing only once. The child receives
one tool observation; its parent receives one child-return observation. The root
still reports one completed own action. Every gain is zero, and the typed return
matches the original operation's references.

The resource-history test completes the first child and its parent return before
interrupting the next parent decision. After changing only the fixture's CPU
and executable hash, resumption selects a second child and its page-1 operation.
There are two root observations and one observation per child: four total, with
zero gains. The test preserves the original resource settings and manifest,
first closed child row and archive descriptor, every original archive byte,
completed action/model/observation/estimation/form/admission rows, and original
semantic operation. It verifies exactly two executions and two publications,
with no replay execution of the first completed operation.

`test_runtime.diff` is the exact reviewable change. An AST comparison establishes
that only the two authorized test functions changed. `production-before.json`
and `production-after-repair.json` agree for all 231 non-cache files under
`gene_annotation_episode/` and `method_loop/`.

The repaired pair passed: **2 passed in 21.22 s**. Its retained trace and state
are under `repaired-pair/`. The original selected 30-test suite is repeated by
`run_selected_suite.py`, with results under `selected-suite/`: **30 passed in
119.33 s**. `production-final.json` still matches the original 231-file
production manifest. `CHANGE_BOUNDARY.json` records the final source hashes and
the exact two-function AST change boundary.

The generic runner's `repaired-pair/RUN.json` label "unchanged scripted tests"
means the test source stayed unchanged **during that run**. Those two test
functions were deliberately repaired before that run. The pre-repair tests,
original failures and exact repair diff remain retained separately; the label
does not mean the repaired pair used the original obsolete fixtures.

## Scope and reset

These are scripted synthetic runtime regressions. They establish action
ownership, durable publication/replay, constrained return and observation
accounting. They do not establish native cmsearch execution, native timing,
model-selected decisions, scientific validity, network access or live resources.
No NCBI BLAST verification or historical scientific run was touched.

The complete immutable goal, AGENTS.md and required execution, estimation,
task/steering and practical-execution records were read before runtime study.
After study, the original objective, all 16 design principles and the current
replay contract were reread before implementing this test-only repair. The
same objective, principles and replay contract were reread before final handoff.
The authoritative goal SHA256 remains
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
