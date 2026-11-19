# Aurora PBS work and current observations

[ALCF's PBS guide](https://docs.alcf.anl.gov/running-jobs/)
separates requesting a node allocation from executing tasks inside it. Account,
requested walltime and required filesystems are submission operands; output
streaming is enforced by the site. `qstat -Q` lists queues, `qstat -f` exposes
job details, and `qstat -x` includes retained completed jobs. These are native
scheduler commands, not additional episode-tool names.

Choose a submission script and native commands that satisfy the assigned
account, queue and allocation constraints. The charging account comes from
`configuration.account`, which must be `BioReason-Aurora-Test` for new Aurora
jobs under the user's updated instruction on 2026-11-04 UTC. Preserve any
assigned account, queue, resources, allocation or allowed account/queue choices.
Work using Flare requires `filesystems=flare`,
the chosen `select=...` and explicit `walltime=...` meeting the selected queue's
current rules. Preserve explicit parent queue and allocation constraints.
A PBS walltime resource operand is separate
from the scientific episode's continuation expectation.

The [Aurora job guide](https://docs.alcf.anl.gov/aurora/running-jobs-aurora/)
documents `mpiexec` for compute tasks within the PBS allocation and queue limits
that vary by queue. Inspect current limits when choosing: the manual run's
one-node `debug` allocation and five-minute request are historical observations,
not defaults for new jobs. Choose an execution script and launcher arguments
for the actual scientific job and its allocation. Preserve supplied scientific
inputs, software identities and output requirements when constructing or
adapting that script. A launcher or environment wrapper must not change the
requested scientific calculation.

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

For the native BLAST database and standard-database scientific profiles, the
original assignment may supply `scientific_manifest`: the actual run-plan file
path, SHA-256, byte count and native format. This is a scientific input operand,
not a scheduler instruction or an executable submission recipe. Use the exact
supplied manifest and its pinned producer/software/database identities when
authoring the native job. The general executor retains that file's bytes before
the actual submission command; the result reader links that immutable version
to the submitted script and native job, then checks the existing scientific
bundle and output hashes. An absent manifest remains an unavailable scientific
operand. Do not manufacture an old submission ledger or replace the original
manifest with a later file version.
