# Local execution decisions

Use the supplied general `exec_command` tool to write scripts, prepare or reuse
the environment, inspect relevant state and invoke the selected scientific
program. Choose commands from the assigned job, actual resource instructions
and observed results. `cmd` accepts either shell text or an argument array for
direct program execution. `workdir` and `env` belong to that command; a shell's
`cd` or `export` does not modify a later command's environment.

Each selected command is one original episode action. Its actual arguments,
outcome, returned error and earned credit reach that same iterator, including
an executed command that fails or earns zero. The host retains immutable
execution records and scientific input/output file versions where required.
Do not write a parallel receipt ledger or treat a preparation command's success
as evidence that the scientific calculation ran.

Inspect actual failures and keep valid partial scientific output. If an
original command's outcome is unknown, investigate that recorded execution
instead of repeating it as though it never happened. The credit-based iterator
owns continuation; this library adds no action order, polling cadence or
stopping budget.
