# Aurora PBS work and current observations

[ALCF's PBS guide](https://docs.alcf.anl.gov/running-jobs/)
separates requesting a node allocation from executing tasks inside it. Account,
requested walltime and required filesystems are submission operands; output
streaming is enforced by the site. `qstat -Q` lists queues, `qstat -f` exposes
job details, and `qstat -x` includes retained completed jobs. These are native
scheduler commands, not additional episode-tool names.

The selected `practical.job.start` action accepts explicit `queue` and
`resources` values. The charging account comes from `configuration.account`,
which must be `BioReason-Aurora-Test` for new Aurora jobs under the user's
updated instruction on 2026-11-04 UTC.
The assignment's `constraints` can fix `account`, `queue`, `resources` and
`allocation`, or restrict `allowed_accounts` and `allowed_queues`. The binding
validates those relationships. Work using Flare requires `filesystems=flare`,
the chosen `select=...` and explicit `walltime=...` meeting the selected queue's
current rules. Preserve explicit parent queue and allocation constraints.
A PBS walltime resource operand is separate
from the scientific episode's continuation expectation.

The [Aurora job guide](https://docs.alcf.anl.gov/aurora/running-jobs-aurora/)
documents `mpiexec` for compute tasks within the PBS allocation and queue limits
that vary by queue. Inspect current limits when choosing: the manual run's
one-node `debug` allocation and five-minute request are historical observations,
not defaults for new jobs. The practical worker executes the assigned `requested_job`
exactly; it does not invent MPI launch options. If a generic job's `argv` needs
a launcher or wrapper, it must agree with the original assignment. Registered
native jobs retain their own closed invocation and software contracts.

For current planning or diagnosis, a selected command can inspect available
queues, PBS fields, account balances or filesystem measurements. The selected
command's actual arguments supply the relevant account and resource. Recorded
balance commands are `sbank-list-projects -u chian -r aurora` and
`sbank-list-allocations -u chian -r aurora`; old balances and expiry dates do not
establish current allocation availability. Retain
the observation's time and source. Native queue/priority/resource fields and logs inform
the episode's interpretation; no field alone proves productive execution or a
stall. Missing fields remain unknown. Keep queue wait, job execution, driver
duration and turnaround distinct. No fixed polling cadence, mandatory probe or
scaling law follows from these instructions.
