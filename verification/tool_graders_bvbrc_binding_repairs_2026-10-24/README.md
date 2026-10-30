# API result ordering and AppService support-return repairs

Two binding defects were reproduced and repaired. No shared `method_loop`,
scientific formula, controller, or episode relationship was changed.

1. `APIServiceExecution._action_paths` sorted hashed directory names. Its
   `_own_outcomes` consumers therefore did not receive chronological operations.
   `BVBRCHomologyReturns._latest` reversed that list and selected an earlier
   partial publication. The complete pairwise Workflow admitted four nulls
   although the final saved calculation contained 3 aligned residues, identity
   1, and query/reference coverage .6/.6. The repair sorts by the numerical
   decision index in each immutable selected-operation key. It retains every
   outcome and the existing receipt/custody checks.
2. `ExecutionEpisodes.received_report_facts` forwarded AppService support
   receipts for execution roles that already supplied that field through their
   own facts. Actual create/upload/submit succeeded, then API report construction
   raised `received_report_fact_conflict`. The hook now forwards these fields
   only for annotation and scientific_process, matching its source declarations.
   API, launch, and results retain their existing owning fact providers.

The old pairwise Workflow finished with 2 failed and 75 passed tests in 1737.71
seconds. Its 16 actions/observations and four admitted reports remain unchanged.
Both failures concern stale returned values; its replay check was not reached.
The original records and expected-versus-actual export correction are retained
in the pairwise verification directory. A repaired full run is separate and
pending at this checkpoint; this file claims no passing repaired full run.

## Verification and fixture correction

`tests/test_api_service_result_ordering.py` contains six focused regressions.
The first test initially wrote invalid receipt bytes without the required
trailing newline. The initial ordering-test failure therefore did not prove
ordering. `before-repair.log` and `candidate-focused-diagnostic.log` retain that
fixture error. The fixture now uses the production `_immutable` writer.

With the corrected fixture, the original binding returns indices `[3,0,10,6]`
instead of `[0,3,6,10]`; the three inappropriate execution-role forwarding cases
also fail. The annotation/scientific forwarding cases pass. See
`original-corrected-fixture.log`. The same six checks pass against the candidate
and applied production code, with incomplete operations omitted and all stored
bytes unchanged.

The candidate run of API service recovery and MinHash return-boundary tests
passed all 16 existing cases. Its combined invocation reports 21 passes and
the one invalid-fixture failure above; the corrected focused run passes all
six. Thus 22 distinct cases pass across these runs, not 27. The candidate imports
were asserted to originate from its isolated package. Production's two edited
files are byte-identical to those candidate files (`production-focused.json`).

The separate AppService transfer Workflow passed four tests in 85.36 seconds,
including actual typed support/handoff return and reopened replay without new
native/model calls. It executed from this candidate; its evidence compares all
299 candidate package source/data files to applied production. See
`../tool_graders_bvbrc_appservice_transfer_workflow_2026-10-24/RESULTS.json` and
that directory's README and byte comparison. This is not a second test run.

The isolated candidate was used so the original pinned full Workflow could
finish before production changed. These are controlled native responses and
scripted decisions. No live service job, configured-model science, or full
goal completion is claimed.
