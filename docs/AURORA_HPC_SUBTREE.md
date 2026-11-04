# Aurora HPC episodic workflow

The implementation is an iterative HPC parent with a prediction child and the
existing `launch` → `launch_hpc` branch. Routine monitoring and result parsing
are direct parent tools. See [HPC_EPISODES.md](HPC_EPISODES.md) for the contracts,
information passed between loops, credit, monitoring updates and current limits.
A106 remains paused. Controller placement is described in
[EXECUTION_WIRING.md](EXECUTION_WIRING.md); scientific work portfolios run inside
Aurora allocations, while the existing episode/model workers remain local.

## Fixed user requirements

- Target Aurora, charging new PBS jobs to `BioReason-Aurora-Test`, as selected
  by the user after the live allocation check on 2026-11-04 UTC.
- Put all remote workflow files under `/lus/flare/projects/BioReason-Aurora-Test`.
  Use `/lus/flare/projects/BioReason-Aurora-Test/chian/runs/` for disposable output.
- Run one workflow at a time per Codex window. Heavy biological computation belongs on HPC.
- The user authenticates once when ready. Preserve the original bastion master;
  never retry authentication or fall back to another login.

The recovered access, storage, software and scheduler details are in
`gene_annotation_episode/launch_instruction_library/aurora-*.md` and the durable
target/authentication constraints are also in root `AGENTS.md`.

## Transport and caller configuration

[aurora_execution_resources.json](../examples/aurora_execution_resources.json)
is the explicit resource dictionary for `ExecutionServiceFactory` or the
assembled caller's `execution_resources`. Use a fresh run subdirectory for each
new live demonstration and preserve that directory for resumption. It now names
the dedicated environment installed and checked on Aurora on 2026-11-04 UTC.
Future availability still requires actual observations, not historical inventory.

[aurora_ssh.sh](../tools/aurora_ssh.sh) accepts the single remote command appended
by the PBS binding. It reuses `/home/chia/.ssh/alcf-control/bastion.sock`, then runs
SSH on the bastion to `chian@aurora.alcf.anl.gov`, allowing only the established
host-based authentication on that second hop. It preserves the request on stdin
and the worker's stdout, stderr and exit status. It does not initialize a master,
ask for tokens, retry, or terminate the shared connection.

The local alias already has `ControlPersist yes`, `ServerAliveInterval 60` and
`ServerAliveCountMax 3`. Reuse-only clients explicitly use `ControlMaster=no` and
`ProxyCommand=/bin/false`; the latter prevents a new connection if the master is
lost. OpenSSH documents both the normal multiplexing fallback and persistence
in [ssh_config](https://man.openbsd.org/ssh_config#ControlMaster). Aurora's host
name follows the [ALCF access guide](https://docs.alcf.anl.gov/account-project-management/accounts-and-access/logging-in-with-tokens/);
the two-hop route comes from this project's retained instructions.

The old Python keepalive unit is inactive. The master's native SSH keepalives
avoid starting another Python workflow. A network failure, server expiry or
machine restart can still destroy a session; on loss, stop and report it without
attempting another authentication. No credentials belong in repository files,
run receipts or chat.

## Current live preparation

The user authenticated once. All subsequent commands reused that bastion master.
Read/write/traverse access to the BioReason project, personal workspace and runs
directory was confirmed. Live sbank queries showed EpiCalib expired on 2026-11-01;
the user then selected BioReason-Aurora-Test, with 39,955.5 node-hours available
and allocation end 2026-11-15. Queue `debug` is enabled and started, permits 1–2
nodes, and has a five-minute minimum and one-hour maximum walltime.

Prepared remote run:
`/lus/flare/projects/BioReason-Aurora-Test/chian/runs/gene-annotation-hpc-20261104T022708Z`.
It contains a dedicated `env/`, the source snapshot, package/build caches,
temporary files and logs. Python 3.12.12 came from the site's framework runtime;
the existing Gentner environment was not changed. Package installation and
`pip check` succeeded. All declared dependency imports and the actual PBS
operation and execution-service modules imported successfully on
`aurora-uan-0010` at 2026-11-04T02:32:51 UTC.

The source archive SHA-256 is
`93e0e16c7e26d675814bf5cf389f08a84309d9d9a25ae403156679b2dff9476c`.
The installation log, package versions and native environment receipt are in
the remote run's `logs/` and copied locally beneath
`runs/aurora_environment_20261104T022708Z/logs/`.

## Live useful-work validation

The user rejected the prepared five-minute `environment_check.pbs`. It is a
historical file, **not an approved job or the next milestone**. Do not submit it.

Read-only live acquisitions on 2026-11-04 captured actual queue records, queue
limits and the status page's computed scheduling scores. The parser joins by
exact PBS job ID and distinguishes those scores from PBS `Priority`. Required
small historical test inputs are retained in `tests/fixtures/hpc/`; complete
disposable acquisitions are in `runs/hpc_design_20261104/observations/`.

The autonomous BLAST episode submitted original PBS job
`9038182.aurora-pbs-0001.hostmgmt.cm.aurora.alcf.anl.gov` and monitored its queued,
running and completed states. Its retained result reports 512 protein queries,
482,697 database sequences and 1,864 hits. Result-reader and closed-launch replay
repairs allowed the same episode to finish without another submission. Local
receipts remain under `runs/aurora_blast_episode_20261104_01/`; disposable run
output is not committed.

The environment snapshot above predates the HPC modules. Launch stages the
current standalone allocation runner and manifest; deployment of episode
controllers themselves additionally needs current source. The new forecast-
valued monitor calendar has focused verification but has not yet controlled a
new live job. Multi-job portfolio valuation and queue-model calibration remain
future work.
