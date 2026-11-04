# Shared local resources

Every new Episode decision receives host-supplied `resource_context` before the
parent chooses work or commissions a child. This includes annotation, A101,
launch and results roles. The scientific prompt displays it in steering.
Archived or interrupted decisions retain the exact snapshot originally sent;
subsequent decisions receive a fresh view.

The context contains the host/account resource identity, CPU/RAM/scratch budget,
maximum active local jobs, reserved allocations, available job slots and
capacity, and the states of outstanding native jobs. Actual launch capabilities
also supply their configured job limits. This is the caller's allocated budget
for application jobs. The existing per-job `local_jobs` policy continues to
control memory, scratch and optional work time.

Packaged host defaults are one concurrent job, one CPU, 20 GiB RAM and 4 GiB
scratch. The small A101 examples request one CPU, 1 GiB RAM and 64 MiB scratch.
Callers configure the shared budget before first use with `[local_resources]`:

```toml
[local_resources]
max_running_jobs = 1
cpu_threads = 1
memory_bytes = 21474836480
scratch_bytes = 4294967296
```

All runs on the same host/account share a capacity registry beneath the common
Git repository's `runs/local-resources/` directory. Worktrees and execution
source snapshots resolve to that same common repository. A deployment can set
`GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY` to an explicit shared directory beneath
`runs/`; every participating process must use that same directory. It is a
host-level setting. Separate per-run directories would separate coordination.
An existing registry rejects conflicting limits from another caller. The
binding is retained in tool resources and native handles for reconstruction.

Before any new native dispatch, the shared native lifecycle atomically reserves
a job slot and the requested CPU, memory and scratch allocation. This covers
blocking tools, detached jobs and result workers using that lifecycle. Homology
forwards its selected CPU allocation; other native preparations allocate one
CPU by default. The service enforces its CPU allocation with a verified cgroup
quota, RAM with `MemoryMax`, and zero swap. Scratch retains the existing
monitored aggregate limit, with possible overshoot, and hard per-file limit.

An occupied budget returns `local_resource_busy` with `retryable: true`, current
capacity and `retry_same_prepared_job: true`. No native service is submitted for
the blocked request. Its prepared handle remains available for a later retry.
A busy A101 result parser also preserves its prepared worker and propagates
the retryable result before caching an outcome or publishing a parse snapshot.
A request larger than the total budget returns a permanent resource-limit
failure. The Episode chooses its subsequent action through its ordinary loop.

Reservations survive the submitting process. An observed terminal, quiescent
service frees capacity even if no collector remains; confirmed cancellation
also frees it. A dead owner of a never-dispatched preparation and reservations
from a previous boot are reclaimed. Uncertain execution keeps its reservation.
Active application services without a known reservation conservatively occupy
the whole budget. Failed capacity probes report unknown capacity and prevent
new dispatch. Planning snapshots grant no capacity: launch checks again inside
the atomic reservation.

`tests/test_local_resource_capacity.py` launches actual independent competing
processes and checks exclusion, original-handle retry, submitting-process exit,
cancellation, oversized requests and uncertain execution. The real LacY and
AtpG cases also check that parents and children receive the resource context
and that the scientific prompt displays it before choosing work.
