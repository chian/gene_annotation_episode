# Homology shared Workflow verification

This workload owns only `tests/test_bvbrc_homology_workflow.py` and this
verification directory. It changes no production code, prompts, annotation
credit, evidence-axis sheet, or continuation policy.

The test uses the actual shared `Workflow`, Store, selected action journal,
original typed commissions, custody reader, AppService executor, publication
host, Homology parser/sheet/calculator and typed return hooks. A controlled
`NativeClient` supplies explicitly synthetic AppService/Workspace responses.
Socket connections and urllib transport are forbidden. No live BV-BRC service,
BLAST analysis, HPC execution, or configured model is exercised.

Caller-supplied JSON fixtures retain the original query sequence, sequence
digest, member identity, exact native query mapping and declared database
selection. The existing scientific child performs two real `material.parse`
actions and returns their retained source references through its original typed
form. Root tools remain unavailable. AppService inputs are then supplied through
the real root-to-launch-to-API commissions, and scientific metadata through the
real root-to-results commission. No previous-run source inheritance, synthetic
runtime action rows, custody mocks, or parser/publication replacements are used.

The scripted choices select API preparation/submission, followed by task-info,
Workspace metadata, capability acquisition and task-manifest download. The
next selected Workspace metadata operation names the acquired manifest member;
another selected capability/download acquires the raw Homology result. This
sequence is a fixture, not a production itinerary. The native manifest's exact
path/UUID association and Workspace type/metadata receipt survive in the bundle.
The producer's immutable byte version remains unproven.

Only root and input-preparation continuation use fixture-specific action counts.
The launch, API and results episodes use their ordinary practical endpoint
estimates and controller comparison. No production turn cap or stopping rule is
added.

The one-query synthetic native document preserves all three hits and five HSPs.
The requested scalar values are:

| Quantity | Observed value | Meaning |
| --- | ---: | --- |
| Reported hit count | 3 | All hits in the selected native query result. |
| First-hit query paired coverage | 0.60 | Six distinct paired query positions / ten query amino acids. |
| First-hit reference paired coverage | 0.75 | Six distinct paired reference positions / eight reference amino acids. |

Repeated and overlapping HSPs leave six repeated pair representations visible
in the sheet. Raw hit titles do not supply inferred function assignments. The
conditional function weights remain unavailable. Recalculating the saved sheet
with temperature 1 instead of 2 changes the unannotated reference kernel mass
from `1 + 0.5 + 0.25 = 1.75` to `1 + 0.25 + 0.0625 = 1.3125`, preserving the
original saved sheet, components and returned coverage/count values.

The manifest-only publication is an explicit partial result: hit count and
coverages are null, with typed acquisition requirements. It is retained after
the later complete publication. Only the final cumulative publication supplies
the returned numerical rows. Publication/reading does not add calculator or
report-composition model actions. Verified actual action counts are root 3,
scientific preparation 2, launch 1, API launch 2 and results 7. The API/results
endpoint estimates became exact zero on their completing actions, retaining
the final actual gain and adding no zero observation or synthetic turn.

The first full-path run exposed missing original-task binding for selected
results Workspace metadata. Its examination summary is retained in
`initial-production-failure.json`. The next run exposed the corresponding
closed-schema omission; its exact test output and selected-action evidence are
retained as `metadata-schema-failure.*`. These were reported to the production
owner. The test did not bypass the failing operation.

The next full run completed the native result publication and retained the exact
three requested numerical values. All 15 selected actions, model decisions and
observations were recorded, and the results child closed with exact future zero.
The parent nevertheless rejected `report.measurements[0].field` with
`unknown_reference`: the general received-reference hook handled the results
child's own Homology field before its own-reference resolver could run. This
failure is retained in `return-admission-failure.PYTEST.txt`,
`return-admission-failure.attempt.json` and the complete
`return-admission-failure-state/`. The run failed its real parent-admission
assertion; its child form alone is not a successful parent return.

After the production resolver correction, the first two full-path tests passed.
The run recorded `2 passed, 1 failed in 688.48s`; the remaining failure was a test
comparison at the wrong boundary. The AppService executor replays its original
`outcome.json`, while the shared runtime adds `pending_work_after_action` before
recording `runtime_actions.result`. The corrected test compares replay to the
actual saved executor outcome and separately requires the entire runtime row,
including its pending-work snapshot, credit and timing, to remain unchanged.
No production or shared-loop change was made for that test correction.

That completed run, its test output and the exact mismatching runtime action are
retained as `admitted-return-replay-diagnostic-state/` and
`replay-assertion-diagnostic.*`. `admitted-return-examples/` contains exports from
those actual records, including the full native bytes, original model calls,
populated sheet/components, admitted parent form and numerical example. Its
`suite_status` explicitly preserves the incomplete test-suite result; it is not
presented as an all-tests pass. Export used the actual publication reader with
network transport forbidden.

The corrected three-test suite passed: **3 passed in 657.93 seconds**. Exact
command, output and elapsed time are retained in `pytest-result.json` and
`PYTEST.txt`. `examples/numerical-example.json` gives the actual values and action
counts; the same directory retains complete native files, original source
materials, original model calls/selections, admitted reports, the populated
sheet and original/recalculated components. `exported-files.json` supplies their
byte counts and digests. The export uses the real saved-publication reader and
makes no native call.

This run tested adapter digest
`0e12e3f2bf4a0f29d38a7108a22214ec58160f1e7d638d34d12350f3c90e85e1`.
The complete passing state, examples and test output are also retained under
`passed-pin-0e12e3f2bf4a-*`, indexed by `PINNED-RUNS.json`. The separately owned
pairwise subject-proof repair is outside this database-identification run;
these records do not claim verification of a later adapter digest. No further
run was started after the passing suite and its export.
