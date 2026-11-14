# Aurora PBS work and current observations

[ALCF's PBS guide](https://docs.alcf.anl.gov/running-jobs/)
separates requesting a node allocation from executing tasks inside it. Account,
requested walltime and required filesystems are submission operands; output
streaming is enforced by the site. `qstat -Q` lists queues, `qstat -f` exposes
job details, and `qstat -x` includes retained completed jobs. These are native
scheduler commands, not additional episode-tool names.

The selected `practical.job.start` action accepts a queue and a list of PBS
resource strings; the bound account must be `EpiCalib`. For Flare work the
request needs `filesystems=flare`, the chosen `select=...`, and an explicit
`walltime=...` meeting the chosen queue's rules. The episode chooses the allowed
values from the actual job and current information. A PBS walltime request is a
resource operand, not a new scientific continuation cutoff. Preserve any
explicit parent queue/allocation constraints.

The [Aurora job guide](https://docs.alcf.anl.gov/aurora/running-jobs-aurora/)
documents `mpiexec` for compute tasks within the PBS allocation and queue limits
that vary by queue. Inspect current limits when choosing. The manual test's
one-node `debug` allocation and five-minute request are historical observations,
not defaults for new jobs. The practical worker executes the assigned argv
exactly; it does not invent MPI launch options. If that argv needs a launcher
or a wrapper, it must be prepared consistently with the assigned job rather
than silently substituted after commissioning.

For current planning or diagnosis, a selected command can inspect available
queues, PBS fields, project balances or filesystem measurements. Examples of
recorded balance commands are `sbank-list-projects -u chian -r aurora` and
`sbank-list-allocations -u chian -r aurora`. Observe only what is needed and
retain its time/source. Native queue/priority/resource fields and logs inform
the episode's interpretation; no field alone proves productive execution or a
stall. Missing fields remain unknown. Keep queue wait, job execution, driver
duration and turnaround distinct; the manual run recorded different values for
them. No fixed polling cadence, mandatory probe or scaling law follows from
these instructions. Source rows A4, A7–A8.
