# Axis wave A107 (`partner_presence_evidence`): what blocks or limits the grading route (19 November 2026)

Scope: `LOST_CONTENT_a107.md` rows 1 to 12 and `IMPORT_FIX_NOTES.md` (A107 HPC execution).

## 1. System: a resumed closed run recomputes the initial credit from present custody (runner)

Failure seen in the real leaf model run (`runs/ma107_2`, run `a107_leaf_model_run`): the first run closed after 24
units (`completion {"credit": 1.0, "ended_by": "yield_stop", "units": 24}`, unit 23 `controller_step.decision.stop =
true`). `resume(...).run()` did not stop at unit 23: it decided two new units (two new model calls) and stopped at unit
25, then raised `JournalError('recorded_episode_completion_differs:...')` (`episode_runtime/journal.py:151`,
`close_episode`).

Cause: on resume the yield controller is rebuilt from `credit(initial summary, records)`; the reader already holds every
record the Episode produced in its recorded units (receipts reload from the journal before the controller is built), so
an episode whose credit or summary reads an inventory (`records.list`, a work-table `select`) gets the credit of the
end of the run as its initial credit (here 1.0 instead of 0.0). The replayed deltas then start with -1.0, the
estimator switches to its signed model and the stop decision differs.

Episode side (done): every A107 literature summary now derives its sheets from the units in `view.outcomes`
(`literature_partner_findings.current_sheet_features(reader, outcomes)`), so the initial summary is that of an empty
view. The head's `received_evidence` still reads every held source (`records.refs()`), and every other episode whose
credit reads an inventory has the same exposure.

Suggested fix (runner, not made here): journal the initial credit when the controller is built (`parent_inputs` or a
new column) and build the controller from the recorded value on resume, or hand `credit` of the initial summary a
reader limited to the receipts of position 0.

## 2. Library not carried: the A107 tool registry (access tools other than read and locate)

`tools/partner_presence_evidence/evidence_operations.A107ToolRegistry` and `tools.ToolRegistry` need `clients`,
native executables and (A107) an `ActionInvocation` of the removed recorder (`execute_async(..., invocation=...)`
raises `a107_tool_action_requires_invocation_and_operation_key` for `invocation=None`). The literature leaves and the
source examination therefore offer only `source_read` (`readers/partner_presence_evidence/source_bytes.source_window`)
and `source_locate` (`readers/partner_presence_evidence/source_locations.locate`), which run on the scoped store, plus
the partner graders. Not offered until the registry is carried: `state.query`, `source.sequence.*`,
`source.experimental.records`, `image.view`, `source.archive.*`, `source.xlsx.*`, `source.pdf.*`,
`execution.estimate`. The upper literature episodes (relevance, strategy, published evidence) still call the
registry through the `tool_catalog` / `public_clients` services for their search and acquisition tools; those calls
are unchanged and untested.

## 3. Row 12 (the A107 axis scorer) not restored

`root/evidence_axis_scoring.py` (`score_axis`) at `60889621e` scores evidence units (`experiment_id`,
`measurements[].fact` with `metric_id` of `entries/A107.json`: partner E-value, bit score, coverage, coexpression
statistic, partner counts) and an axis judgment. No A107 code produces such units: the partner sheet's cells are rate
components, not those metrics, and mapping one onto the other is new science. The file is also part of the old shared
root, which AGENTS.md says is never restored. Wanted: an owner decision on which saved sheets supply which
`A107.json` metrics; then the scorer can be restored verbatim as `grading/partner_presence_evidence/` and fed from
`scoring_sheet.scoring_sheet`.

## 4. HPC planning (`hpc_work_planning/task.py`) still on the old ledger

`hpc_work_planning/task.py` imports `jobs.hpc.partner_presence_evidence.hpc_ledger.HPCLedger`, which does not exist,
and uses `ledger.path` (`launch_input_path`, `export_closed`, provenance). It was not in the IMPORT_FIX list for A107
(only the execution sister was adapted). The execution sister now takes `ledger` (the `HpcLedger` id) and
`ledger_row_refs` in its assignment and passes the id to every tool; the planning parent must send both in its
`msg_to_child` once it is carried onto `jobs/hpc_ledger.HpcLedger` (`HpcLedger.open(ctx.store, commission)`,
`ledger.ledger`, `ledger.refs()`).

## 5. Head stubs outside the grading route (left)

`partner_presence_evidence/task.py` `process_execution` raises `NotImplementedError('unplaced:execution_planning.read')`
and `hpc_allocation_execution/task.py` raises `BLOCKED-ON-JOB-SERVICE` for the job ledger handoff record; neither is a
grading item.
