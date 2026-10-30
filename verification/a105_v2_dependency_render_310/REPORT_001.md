# A105 V2 dependent-measurement return presentation

## Bounded correction

The V2 A105 worksheet validator already accepted a source-bound
`same_physical_measurement` link between two returned Pa0142 kinetic parameter
cells. The receiving parent prompt still recognized only the V1 context marker
in `literature_experimental_prompt._worksheet_context`, and the A105 worksheet
renderer also recognized only V1. Thus the V2 link could be admitted without
the one-sheet relationship appearing as controlled parent STEERING.

The two existing presentation files now recognize both V1 and opt-in V2. V1
remains the default and its relation wording is unchanged. The new V2 relation
is rendered as: “one shared original physical measurement; dependent contrasts,
not independent experimental evidence.” This is a received interpretation of
the source-bound typed link, not a new numerical score or statistical covariance
claim. Source IDs and raw numeric-token metadata are omitted from this display.
The correction does not alter the worksheet validator, kinetic calculator,
reader, TASK content, controller, credit, or episode action accounting.

## Verification

`tests/test_literature_a105_v2_dependency_render_310.py` reuses the earlier
selected Pa0142 two-contrast episode test and its read-only cold reconstruction.
It captures that test's actually validated typed return and renders a receiving
literature parent's prompt. The check confirms the recurring TASK is identical
with and without the child return; STEERING contains one A105 worksheet, both
reported parameter-ratio cells, and one explicit shared-measurement relationship.
It checks that the V1 form still renders through the original path without the
new relation and that V2 version IDs, source IDs, numeric-token keys and
measurement-reference keys are not exposed in STEERING. This is scripted
provider/controller execution, not configured model-backed assessment.

Final focused run: `.venv/bin/python -B -m pytest -q
tests/test_literature_a105_v2_dependency_render_310.py --tb=short -x` →
**1 passed in 22.91 s**.

A joined run of the existing V1 integration file plus this test reached
**16 passes**, then failed at `method_loop.durable.DurableExecutionError:
identity_conflict` during the V1 test's cold binding recompose. The P205 agent
was concurrently editing production files included in that binding's code
identity. The failure is not yet diagnosed as a regression or concurrency
artifact. The parent will rerun the V1 file after the P205 edits settle. No
further broad test was run against the changing tree.

## Provenance and limits

This workload read the immutable user goal, replacement root AGENTS, complete
episode/time/tool/task documents, task/steering and evidence-axis amendments,
the verbatim direction/recovery, numerical review, complete research AGENTS,
current A105 worksheet, kinetic input contract, and the relevant full prompt
rendering path. The latest user instruction was applied last. It reused the
existing Pa0142 selected test; it did not collect or interpret a new paper.
No general A105 reliability/validity/relevance compilation or W05 credit was
added.
