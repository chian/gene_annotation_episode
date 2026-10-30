# Preparation reference visibility — focused verification 258/001

The focused boundary run passed **22 tests**. A subsequently added results-role
sentinel test exposed an **unresolved avoidable artifact read** in the public
reference-access helper. This is separate from the auxiliary-file communication
defect whose correction these passing boundary cases exercise. No production
file was edited by workload 258.

## Authority and scope

The exact work contract is
`../tool_graders_infernal_preparation_2026-10-26_247/REFERENCE_VISIBILITY_HANDOFF_001.md`.
The immutable user goal was read in full, including all 16 design principles.
After substantial code study its objective and all principles were reread before
writing tests. Before this handoff the complete immutable goal, including all
16 principles, was reread verbatim, followed by the exact visibility contract.

Read context: `AGENTS.md`, `GOAL.md`, `docs/EPISODE_STRUCTURE.md`,
`docs/TIME_AWARE_ESTIMATION.md`, `docs/TASK_AND_STEERING.md`,
`docs/PRACTICAL_EXECUTION.md`,
`docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md`,
`docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md`, and the Infernal
preparation rows in the fixed `WORK_STATUS.json`. That historical inventory
was read, not changed or used to redefine completion.

The complete changed production modules inspected were `episode_receipts.py`,
`execution_episodes.py` and `native_infernal_preparation_results.py`. Also read
the complete `native_infernal_preparation_returns.py`, `episode_return_records.py`,
`episode_bindings.py`, `episode_journal.py`, and preparation tool-binding module.
The relevant complete Workflow initialization/build, binding-context,
receive-outcome, receive-form and resolver paths and Store metadata/reference
paths were inspected. This does not claim a complete review of all 4,176 lines
of `runtime.py` or all of `state.py`.

## Test boundary

Owned files are only:

- `tests/test_native_infernal_preparation_reference_visibility.py`
- This verification directory.

All data bytes, sources and saved runtime actions/forms in the test are labelled
synthetic. They are not native Infernal measurements or evidence of working
scientific execution. The tests instantiate the real Store, Journal,
EpisodeReceipts, Workflow, ExecutionEpisodes and typed-return authenticator.
They call the real `Workflow.resolver` and a separately constructed
`ExecutionEpisodes(None, ...)`, exercising the fallback without Workflow service
callbacks. They do not run a model or an episode loop.

The explicit child-form case substitutes only a declared completed-results
port. The real return reader checks the original context, immediate parent,
saved commission, requested schema, frozen form/facts, and reference types. This
is focused boundary evidence, not the full nested production proof. Workload
257 owns the actual nested Workflow/native cases; none was duplicated here.

The tests block network connection, subprocess/native launch and preparation
grading/publication entry points. During assertions they also block
`Store.get_artifact` and direct `Path` reads under the Store artifact directory.
Record metadata and file size/mtime snapshots verify unchanged custody while
the known synthetic bytes establish exact content IDs. No scientific artifact
is read to calculate or infer a visibility verdict. No numerical sheet, grader,
W05 aggregation, literature processing or scientific credit is added or run.

## Passing cases

`probe_001` completed with 22 passed in 116.41 pytest seconds (117.15 measured
service-wall seconds). It verifies:

- All five receipt kinds keep a preparation source without implicitly admitting
  its bundle or auxiliary artifacts. Explicitly selected artifacts survive;
  repeated delivery changes neither receipt rows nor source/artifact metadata.
- Suppression is specific to the exact preparation provider/version. Other
  providers and the ordinary Infernal bundle version retain recursive receipt
  behavior and normal artifact resolution.
- Global Store scope and synthetic historical polluted receipt rows alone do
  not authorize the unrequested bundle or auxiliary artifacts, in either
  Workflow or the reconstructed execution owner.
- An independent completed or partial own action explicitly returning the same
  content-addressed bytes retains access. Old polluted rows are not rewritten
  to achieve that outcome, and unrequested sibling artifacts stay denied.
- Failed, invalid, pending, other-run, other-episode and nested-only references
  cannot substitute for explicit successful delivery.
- Original supplied-assignment and supplied-subject references retain access
  when those same bytes also appear in preparation custody.
- Unknown records and semantic identifier namespaces remain outside this
  provider guard. Normal namespace checks reject using an artifact as a source,
  subject, preparation name or execution handoff.
- Authenticated explicit child references are admitted and resolved; unrequested
  bundle and auxiliary artifacts are denied. Repeating admission preserves the
  receipt history and creates no runtime observation.

## Remaining read-path defect

`sentinel_003` selected the new
`test_unrequested_results_reference_does_not_reopen_original_bundle` only:
**1 failed, 22 deselected**, 7.79 pytest seconds. Its expected assertion is:

```python
assert results.retained_reference_access(context, b.unrequested, 'artifact') is False
```

Instead the read sentinel raises:

```text
retained_reference_access                  native_infernal_preparation_results.py:328
  -> resolve                               native_infernal_preparation_results.py:386
  -> _own_bodies                           native_infernal_preparation_results.py:258
  -> _validate_body                        native_infernal_preparation_results.py:256
  -> Store.get_artifact(bundle_ref)        native_infernal_preparation_results.py:136
AssertionError: Metadata-only visibility verification attempted forbidden work
```

The fixture uses synthetic target and capture-replay ports to reach this real
owner/receipt-validation path without native work. The target is not presented
as a valid native deployment and its dummy bundle is never opened. The tested
reference is absent from the selected result's explicit references. Its denial
therefore needs no scientific contents. The exact trace proves the attempted
bundle read; it does not claim that the sentinel allowed a later sheet read.
Source inspection also shows downstream prepared-grading validation can inspect
retained artifact files.

Proposed narrow boundary, reported to root: the guard should inspect exact
explicit references in original action/receipt/context/form metadata and reject
an unrequested reference before reopening full result validation. Existing
positive result/form validators retain their authentication responsibility.
Do not create an authority cache, new workflow layer or receipt migration.
Root owns production repair; the failing regression is retained without xfail.

`sentinel_002` is retained as an unsuccessful fixture-development attempt. It
failed earlier because synthetic receipt files lacked the canonical trailing
newline. That fixture error was corrected before `sentinel_003`; it is not
reported as a production defect.

## Resource and source records

`run_tests.py` adapts the existing 247 bounded runner. All runs used the existing
`run_local_job` service with **20 GiB RAM, 4 GiB scratch and no wall-time cap**.
The controller is not used for these verification processes. Receipts contain
the actual systemd cgroup enforcement and complete before/after source hashes.

The maximum observed scratch was 15,966,208 bytes in `probe_001`; each sentinel
run observed 1,617,920 bytes. No HPC/API resource or native scientific program
was invoked. The outer bounded test process itself is an actual local job.

All boundary modules were unchanged during every recorded run, including
`episode_receipts.py`, `execution_episodes.py`,
`native_infernal_preparation_results.py`, and
`native_infernal_preparation_returns.py`. The broad source snapshot for
`probe_001` also captured concurrent changes in three unrelated literature
modules; they are listed in its receipt rather than hidden. Neither sentinel
run captured any source changes. `SOURCE_AND_RUN_SUMMARY_001.json` records the
relevant hashes and exact resource observations.

No complete scientific tool or full user goal is declared complete by this
verification slice. The remaining result-role guard regression needs a
production correction and a subsequent test run.
