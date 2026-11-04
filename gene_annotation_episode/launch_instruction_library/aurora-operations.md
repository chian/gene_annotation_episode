# Actual practical HPC operations

These operations exist in the opt-in practical HPC binding. Their presence in
this library does not make them available in a different binding. The caller
must supply a real `pbs_ssh` configuration: `workspace`, `ssh_argv`,
`python_executable` and `account`. No transport, credentials, queue or software
is discovered or selected automatically by that configuration.

| Callable operation | Actual selected work |
| --- | --- |
| `practical.inspect` | Observe the original assignment's declared path predicates. |
| `practical.inventory.refresh` | Read a selected structured catalog within the workspace and reconcile the local mirror. |
| `practical.context.set` | Persist a validated cwd and explicit environment for later actions. |
| `practical.directory.create` | Create a selected directory in the assignment workspace. |
| `practical.file.write` | Write the exact selected UTF-8 text within that workspace. |
| `practical.file.read` | Read a selected byte window, retaining original bytes and offsets. |
| `practical.command.run` | Run one selected preparation or diagnostic command on the configured remote host, retaining its outcome and logs. |
| `practical.job.start` | Submit the fixed requested job with selected `queue` and `resources`; the caller owns the account. |
| `practical.job.status` | Observe the original PBS execution, exposed scheduler fields and log tails. |
| `practical.job.collect` | Observe that execution and validate the assignment's requested output predicates. |

`cd`/`export` within a command affects that subprocess only. Use the context
operation for persistent changes. The requested job's explicit environment is
not replaced with a preparation command's environment. The worker applies
workspace-confined temporary/cache defaults and records native submission state.

The original attempt is identified by a saved intent, submission token and,
when known, the actual PBS ID. Reopening reconciles that identity; an interrupted
or failed SSH/qsub reply does not establish scheduler rejection. Unknown work
is not resubmitted. An explicit `retry_failed_execution_id` may start a new
attempt only for that confirmed failed original execution. No retry is made
automatically, and retry without an actual PBS ID is unsupported.

Status/collection can receive `receipt_ref` from a scoped prior practical
handoff. They check the original job/resource identity and record the receiving
episode's observation. Native completion and declared output predicates, not a
prose claim, establish the endpoint. Existing output alone need not establish
that this job produced it; use the assignment's exact hash predicates where
required. Log tails are bounded; select a further file window when useful.

An available operation description does not establish a live connection,
configured deployment or completed job. Only the actual selected operation's
outcome and original execution receipts establish those observations.
