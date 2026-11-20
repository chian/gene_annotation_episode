# blast_database_preparation: the child episode, local part (2026-11-20)

Governed by `a101_tree.md`. The model is the router; code checks and carries out. `launch_local` is a TOOL of this
episode (no folder). The cluster leaves are built later by someone else. Nothing here changes `episode_runtime`,
`method_loop` or `yield_control`.

## The owner's rule for the tool (message of 2026-11-20, applied)

The model fills out one JSON (the controlled fields of the action). ONE deterministic function checks that JSON
against the commission, the records the episode holds and the bound resources BEFORE anything runs. If anything is
wrong it returns the things to fix (each a code and the field it concerns) through the system's own mechanism,
`action` raising `Rejected(feedback)`: no unit, no observation. If it passes, the job runs and must simply work on
the first call. After a passed check a job fault is an environment fault: reported once as `failed`, `retryable`
false, never something the model fixes by calling again.

`hold` is always a valid answer, so a model that has no valid launch (for example every local resource is below the
input size) is never stuck in rejections.

## Step zero: for each function, what already exists

| Function (file) | Exists and is called | Written new |
|---|---|---|
| `goal.py` constants | pattern of the head's `goal.py` | text |
| `read_from_parent.ASSIGNMENT_FORM`, `read_from_parent` | `method_loop` `RecordForm`/`ChoiceField`/`Field`; `blast_preparation_job.KINDS, MOLECULES, MASKING_*`, `validate_commission` | the form fields; the one `input_refs` -> `input_ref` step |
| `task.INSTRUCTIONS`, `output_schema`, `decide` | reference `old_execution_job_submission/local_job_execution/task.py` (shape); `progress_views.yield_table`; `job_access.read('resources'/'describe')` | this episode's own text; context |
| `task.action` | `rejection_feedback`; the check function below | model JSON -> `ToolCall` or `Rejected` |
| check function `preparation_problems` (`blast_preparation_run.py`) | `validate_commission`, `describe_fasta`, `compile_preparation`, store `holds`/`get_artifact`, route `describe` | the list of conditions |
| tool `launch_local` | `prepare_locally` (library) | one-line body |
| `prepare_locally` (`blast_preparation_run.py`) | `compile_preparation`, `checked_analysis_kind`, `execute_on_local_resource(wait=True)`, `evaluate` (receipt), `prepared_values`, `put_prepared`, `prepared_features` | composition; `software_identities`; the establishing tail was factored out of `acquire_prepared_data` so both use it |
| tool `hold` | - | returns the reason |
| `credit.credit` | `prepared_rows`, `prepared_credit` (given known keys) | passes the keys of the records the parent passed |
| `yield_estimator.yield_controller` | `yield_control.CompletionYieldController` | choice and reason (below) |
| `internal_summary` | `prepared_rows`, `prepared_features`, `describe_fasta`, `yield_table` | the summary rows |
| `final_to_parent` | `FAILURE_CODES`, `RecordForm` | the form |

## The check: every condition

(filled in with the code, below)

## Prediction, observed, head wiring

(below, added before and after the runs)
