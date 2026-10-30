# Unexecuted accounting attempt

The root accounting wrapper incorrectly supplied the repository root as the
bounded job's working directory. The native lifecycle rejected its scratch
preflight with `local_job_resource_limit` in `prepare_job` before the accounting
script ran. No scientific tool or test ran and no status update was written.

The wrapper's actual process exited 1. This note records the observed traceback;
it is not a fabricated native execution receipt. The corrected retry uses its
own small execution directory. No subagent or subagent job was stopped.
