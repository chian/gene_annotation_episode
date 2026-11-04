# One bounded local workflow per Codex window

The local budget covers Python coordinators, provider clients, native workers,
and all their descendants together. The launcher accepts one workflow at a
time per Codex window; other windows may run independently. A separate
per-worker gate remains inside each workflow. Limits are fixed in code,
not selectable by an episode or an ordinary launcher argument.

| Aggregate limit | Current value |
|---|---:|
| CPU | 100% of one logical CPU |
| Memory | 512 MiB |
| Swap | 0 |
| Tasks/threads | 64 |
| Runtime | 600 seconds |
| Scratch | 256 MiB, monitored with possible overshoot |
| Per-file size | 64 MiB, kernel limit |

Disk bandwidth is not enforced: the present user cgroup does not delegate the
I/O controller. This policy permits lightweight inspection and verification.
Heavy biological algorithms require a configured remote resource or the user's
explicit approval of a concrete local budget. Limits must not be increased
silently to make a test pass.

Run one command with a new output directory:

```bash
bash tools/one_workflow.sh runs/<unique-run> -- <command> <arguments...>
```

The shell launcher starts Python inside a resource-limited systemd service.
Its supervisor verifies the kernel CPU, memory, swap and task limits of a shared
parent slice before starting the payload. The stable `CODEX_THREAD_ID` identifies
the window's service, slice and exclusive lock at
`runs/workflow-windows/<thread-id>/workflow.lock`. A second workflow in that
window is rejected before Python starts. Different windows have separate slots
and aggregate budgets; their slices do not inherit the former global workflow
cap. Do not invent a new ID per run. Inspect this window's actual processes too:
older launches and surviving children may not hold the lock. A stale or incomplete
shutdown prevents new work in that window until its prior process tree is
quiescent. Cleanup selects only native services in the owning window's slice.

Native services join that same slice and bind to the driver's lifetime. The
default native capacity ledger belongs to the run and counts only that window's
slice; explicitly supplied shared resource ledgers retain their caller's scope.
Requests exceeding the whole-workflow budget are rejected before native
dispatch; older standalone per-job settings cannot override the aggregate cap.
The model connection retains one live provider process, retiring it before
switching episodes. A shared provider lock also prevents independent
connections from launching overlapping clients.

Budget identity includes the window ID, boot, supervisor PID and process start time.
An environment variable or a prior run's budget file cannot authorize another
workflow. Native and provider entry points reject missing or invalid budget
proofs. The A103 example checks the proof before importing scientific code.

Each run saves its command, verified bounds, memory peak, scratch observation,
exit status and cleanup evidence beneath its run directory. A normal return
requires the launcher to observe that the entire slice has no remaining
processes. A signal, resource failure or missing native result is not converted
into successful scientific work.

Memory peaks use one open `memory.peak` descriptor through reset and final
read. Memory events are recorded as this workflow's counter deltas, with the
before/after counters retained. These are the kernel's
[cgroup accounting semantics](https://docs.kernel.org/admin-guide/cgroup-v2.html).

Codex provider logs and SQLite writes go beneath the run directory using
`log_dir` and `sqlite_home`; authentication continues to use its existing home.
A consistent read-only snapshot of the existing session index avoids rebuilding
the entire interactive index in each batch client. Memories and unused native
tools are disabled for these ephemeral scientific conversations. The supported
storage settings are described in the
[official OpenAI documentation](https://learn.chatgpt.com/docs/environments/network-file-systems).

Repeated large contract schemas are interned in digest-verified Store artifacts.
Store readers restore the complete original JSON. SQL-visible scopes, tools,
scientific outcomes and receipts remain inline; this is a storage change, not
an information or credit filter.

`tests/workflow_budget_probe.py` checks real child processes, separate process
sessions, nested native services, rejected competing launches, oversized
requests, provider lifecycle and abandoned-child cleanup. Its provider is a
small RPC fixture; it performs no model calls or biological computation.
