# AppService monitor handle resolution verification

This additive repair addresses the actual shared Workflow failure at
`report.target`: an authentic AppService TaskHandoff was rejected with
`unknown_reference` when returned as `monitoring_target_handle` in the
`execution_handle` namespace. The requested target field is retained.

## Production change and custody

`BVBRCAppServiceHost.resolve(context, reference, namespace)` now routes an
AppService receipt in the monitor's `execution_handle` or `execution` namespace
to `AppServiceMonitor.resolve_target`. The helper reconstructs the original
TaskHandoff through the existing authenticated handoff/target readers. It then
uses the existing `_possession` proof for the assigned target or `_dependency`
proof for an actually received dependency. It makes no request and creates no
record, observation or credit.

The assigned target requires the original monitor assignment and saved parent
commission, original submission identity, and custody before commissioning.
Same-target recursive monitors retain the full commission chain. Dependency
handles require an actual completed progress observation/read or an explicitly
requested typed dependency return, including its original snapshot, selection,
physical submission relationship and applicable receiving cutoff. Visibility
in Store or an inherited receipt ledger alone is insufficient.

Workflow validates initial interpretive fields inside `build` before saving
the child or its parent action. Only assigned-target resolution permits this
interval, and `custody.authenticate(allow_unsaved=True)` still requires the
exact already saved parent model selection and original schema. An action row
alone cannot authorize it. Dependency resolution and native `progress.observe`
continue to require a saved monitor context.

Claimed AppService references with invalid custody or an incompatible receipt
return `False`; references owned by another binding retain the existing `None`
deferral. Ordinary launch/results support and handoff namespaces retain their
existing behavior.

The inspected consuming path is `Workflow.resolver` →
`EpisodeBindingRegistry.resolve_received_reference` →
`ExecutionEpisodes.resolve_received_reference` → AppService host → monitor
proof. `APIServiceExecution.resolve` and `ExecutionEpisodes.resolve` also
consume the host's tri-state result. Existing monitor fact projection and
typed report validation still check the requested value against the immutable
assignment and received observations. No runtime, prompt, grading, controller,
frozen record or accounting implementation was changed.

## Executed verification

The new file is
`tests/test_bvbrc_appservice_monitor_handle_resolution.py`. Its 31 distinct cases
cover authentic receipts, exact typed target validation, wrong task, forged
reference/context/commission, missing and late receipts, incomplete original
submission, ordinary launch/results namespaces, saved model selection during
initial construction, recursive monitors, and authentic or forged dependencies.
The repeated positive resolution check observes zero database writes, no new
files, zero native calls and zero controller observations.

The first targeted run had **30 passes and one test assertion failure in
332.31 seconds**. The rejected missing-receipt case correctly raised the typed
boundary error; the test had incorrectly searched its human message for the
structured code. The corrected test asserts the exact diagnostic
`{category: report_format, code: unknown_reference, field: report.target}` and
passed separately in **9.39 seconds**. Production code did not change between
those runs. Original and corrected logs, command metadata and JUnit records are
retained here as `targeted*`.

The existing production regressions also passed: **72 passed in 550.87
seconds** using `.venv/bin/python -m pytest -q
tests/test_bvbrc_appservice_native_monitor.py
tests/test_bvbrc_appservice_host.py`. These retain the saved-context requirement
for native observation, original selections/custody, recursive dependencies,
native/log qualification, interruption recovery and ordinary launch/results
receipt behavior. Exact command metadata, stdout and JUnit output are retained
as `regression*`.

The separate Workflow owner ran
`tests/test_bvbrc_appservice_monitor_workflow.py` against these unchanged
production files: **1 passed in 98.04 seconds**. That test keeps the original
target field, interrupts after retaining the stdout response, reopens Store
and Workflow, forbids new model/native calls, admits the original typed
returns, and replays the complete closed history unchanged. Its retained
evidence is in
[`second-run.log`](../../../verification/tool_graders_bvbrc_appservice_monitor_workflow_2026-10-24/second-run.log).
Its earlier failure remains in the same directory's `first-run.log`.

An independent read-only query of that successful run's retained database
produced [workflow-numerical-evidence.json](workflow-numerical-evidence.json):

| Episode role | Completed own actions / observations | Actual marginal credits |
| --- | ---: | --- |
| API launch | 2 | 0, 2 |
| Launch | 1 | 2 |
| Monitor | 2 | 0.5, 0.5 |
| Scientific root | 2 | 0, 0 |

All three typed returns succeeded, for seven observations total and zero
scientific annotations. The monitor's selected native choices are exactly
`query_tasks` and `stdout`. These values are the fixture's actual recorded
operational/monitoring credits under its explicit caller units, not scientific
confidence measurements or a new scoring formula. The evidence file includes
the source database path and hashes of both changed production files.

## Scope and limits

The checks use production Store, journal, receipts, custody, native operation
bindings, typed returns and shared Workflow. Native service responses and
decisions are explicit synthetic fixtures. There was no live BV-BRC request,
configured model, detached worker, HPC job, scientific grading run, or new
annotation-confidence score. This repair establishes the monitor handle
communication path, not completion of a scientific tool family or of the
overall tool-grader goal.

The original objective and all 16 design principles were reread verbatim from
the authoritative attached goal, followed by the current native-monitor
contract. Those instructions retain authority over this implementation note.
