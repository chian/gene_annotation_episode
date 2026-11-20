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

## Prediction for run 1 (written before any run)

Input: the first 12 records of `globins45.fa` (12 sequences, 1771 letters, 1915 bytes as written), protein,
`parse_seqids` true, `hash_index` false, `db_version` 5, `prepared_unit` 1.0. One local resource `local`
(scratch bound 64 MiB), bundled BLAST+ 2.17.0.

1. Model decision 1: `launch_local`, resource `local`, kind `database_build`. The check passes (no rejection).
2. Unit 1: one job; the receipt shows build, info and check each returning 0; the prepared-data row is `usable`,
   native summary 12 sequences and 1771 letters, `counts_match` true, `integrity_ok` true, `inventory_complete`
   true, 6 to 9 files (`.phr .pin .psq`, plus the `.pdb .pot .ptf .pto` and `.pog`/`.pos`-type files that
   `-parse_seqids` adds). Outcome status `usable`, `retryable` false.
3. Credit 0.0 before, 1.0 after unit 1 (equal to the target).
4. The completion controller sees the target reached (forecast exactly zero) and ends the episode by `yield_stop`
   after 1 unit. Zero model calls after the first.
5. Return: credit 1.0; finding `usable`, 12, 1771, `files_count` as in 2, no failure code; `prepared_data_refs`
   holding the one row.
Risks I expect: `blastdbcheck -full` may fail on this bundled BLAST+ (an earlier attempt's commit says it raises an
internal exception on every valid database); if so the build is `failed` with `native_nonzero_exit` and that is a
defect of the preparation library to fix, not of the episode.

## The check: every condition

`preparation_problems` (`blast_preparation_run.py`) returns the list of `{code, field, detail}`; empty means the call
simply runs. In order: `resource_not_bound` (resource_id); `resource_not_local` (resource_id); `kind_differs_from_
commission` (kind); `commission_invalid` (commission; the library's own `validate_commission` error as detail; the
check stops there); `input_not_held` (input_ref); `input_not_parsable` (input_ref; `describe_fasta` error);
`input_above_local_bound` (resource_id; input bytes above the resource's `policy.scratch_bytes`); `program_missing`
(program; each BLAST program the job runs must be an executable of the configured directory); `python_missing`
(python); `job_not_compilable` (commission; `compile_preparation` raises, including its own declared-versus-derived
kind comparison). `action` raises `Rejected` with `{status: invalid, category: launch_local_check, problems}`.

Note on `input_not_held` and `input_not_parsable`: `internal_summary` reads and counts the input (the facts shown to
the model), so a commission whose input is not held or does not parse fails the run at the first summary with its own
error (AGENTS.md: a wrong commission fails); the check still tests both, and they are the conditions a changed input
would hit. The model cannot repair a wrong commission, so these are not offered as fix-lists that would loop.

## Head wiring, observed, run records

(added after the runs)
