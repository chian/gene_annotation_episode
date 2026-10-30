# Local native job limits

Caller configuration is the `[local_jobs]` table in the TOML supplied with
`--config`. Packaged starting defaults are:

```toml
[local_jobs]
memory_bytes = 21474836480
scratch_bytes = 4294967296
```

These defaults are 20 GiB memory and 4 GiB monitored scratch per native job.
Time is unset. Caller configuration can change these settings; episodes cannot
override them in tool arguments. Tool capabilities expose the effective policy; run initialization and
native source provenance record the selected resource binding. These settings
are separate from the numerical estimator's existing configuration.

`local_jobs` uses a separate user-systemd service and cgroup for the selected
command. It checks the actual cgroup memory and swap boundaries before releasing
the command. `MemoryMax` is a hard cgroup memory boundary, not a virtual-address
limit or a promise that allocation will succeed. Swap is disabled for that job.
No work wall-time limit is activated by default. The runner supports an explicit
operational timeout for callers and isolated engineering tests; this does not
choose a future time/credit policy. Cancellation
waits for worker cleanup before the caller removes temporary files. If the local
boundary cannot be established, work returns operational preflight feedback;
it does not fall back to unprotected execution.

The blocking adapter and detached execution now share `native_lifecycle` and one
protected worker. The worker owns the aggregate scratch monitor; it remains live
after the submitting process exits. Detached jobs keep a standard durable handle,
native receipt and systemd completion receipt. Elapsed execution ends at the actual
completion hook, even when collection happens later. Native child and wrapper exit
identities remain separate. Missing completion evidence stays unknown. See
[HOMOLOGY_EXECUTION.md](HOMOLOGY_EXECUTION.md) for the actual handoff interface,
recovery evidence and remaining runtime integration work.

Standard output/error and native temporary files go to the job directory. An
aggregate allocated-byte monitor stops a job over its scratch limit, with
possible overshoot between samples. `RLIMIT_FSIZE` supplies a hard per-file limit
of the same size. This is **not a hard aggregate filesystem quota**, a filesystem
sandbox, or a limit on accumulated durable run history.

Pairwise alignment and Pyrodigal run in Store-free worker processes rather than
inside the workflow host or its SQLite transaction. Infernal, minimap2 and native
PDF commands use the same boundary. Algorithms, complete selected operands and
scientific ownership remain unchanged. Version/help probes are separate bounded
native processes. Resource use across a complete multi-process tool call or a
whole investigation is not an aggregate per-job limit.

A resource failure carries the affected resource, limit, enforcement metadata
and actual available exit evidence through operational feedback. An OOM claim
requires actual systemd/cgroup evidence. It does not itself change scientific
state, award credit or create a completed-action yield observation. Already
committed scientific work survives. Independent valid batch contributions remain
distinct from failed members. No algorithm substitution or automatic retry follows.

These boundaries cover native workers. Material parsing, host-side result
publication/projection, remote acquisition, model transport, durable storage and
the workflow host as a whole do not yet have an aggregate resource boundary.
Passing a small enforcement check is not a whole-pipeline resource benchmark or
biological annotation validation.

The actual cgroup OOM engineering test requires explicit
`GENE_EPISODE_TEST_OOM=1`. It deliberately kills a tiny isolated Python worker and
can trigger GNOME's application-stopped notification even when machine-wide
memory is plentiful. Routine test runs skip that one destructive worker test;
they do not suppress desktop memory notifications.
