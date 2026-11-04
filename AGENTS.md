# Repository layout

# Local execution policy

Run one local workflow at a time per Codex window, not globally across windows.
Within a window, never overlap examples, investigations, tests, benchmarks, or
background runs. Count Python coordinators, model
provider processes, native workers, and all their descendants as one workload.
Use the bounded single-workflow launcher for every local Python command.
Confirm the complete workload has exited before starting the next command.

CPU and memory limits must cover the entire workload, not just native workers.
Fail closed if that boundary cannot be verified. Do not increase its limits,
bypass its single slot, or move a job to another local pool without the user's
explicit approval. Heavy biological algorithms require remote execution or
explicit user approval for a concrete local budget. Keep local work to editing,
saved-trace inspection, and lightweight bounded verification until then.

Put disposable execution output in the single top-level `runs/` directory.
Use a separate directory beneath it for each run when needed. This includes
logs, execution databases, temporary results, test execution output, copied
environments, dependency copies, and source snapshots made for a run.

Set tool working, temporary, cache, and output paths beneath that run directory.
For pytest, use `--basetemp=runs/<run>/tmp`; its default cache is already under
`runs/`. Disable Python bytecode writes or set `PYTHONPYCACHEPREFIX` beneath
`runs/` so imports do not scatter generated files through the source tree.

Do not create run-output directories in `verification/`, application source,
tests, research, or documentation. Ignore `/runs/` as one directory in Git.

Keep required test inputs and reusable test helpers with the tests, and keep
application code in its source directories. A run directory must not be the
only home of code or fixtures required by the project. Preserve required assets
before removing old generated output; do not classify a file as disposable
solely because it lives in a dated directory.

# Established HPC target and authentication

Use Aurora with charging account `BioReason-Aurora-Test` (the user changed this
from EpiCalib after the live allocation check on 2026-11-04 UTC). All remote workflow files belong
under `/lus/flare/projects/BioReason-Aurora-Test`, with disposable output in
`/lus/flare/projects/BioReason-Aurora-Test/chian/runs/`. The only workflow file
permitted in remote home is `/home/chian/WORKSPACE_DIRECTORY.md`.

The established route is `chian` through the `alcf-bastion` SSH alias, then SSH
from the bastion to Aurora using host-based authentication. Reuse the original
master at `/home/chia/.ssh/alcf-control/bastion.sock`. The user authenticates
once when ready. Never loop authentication, automatically replace the master,
or let a command fall back to a fresh login. Stop if the existing transport is
lost. See `gene_annotation_episode/launch_instruction_library/aurora-access.md`
for reuse-only options and the recorded keepalive setup. Preserve these
operational instructions when editing goal-specific guidance.

# Live test concurrency

Run only one full test workflow at a time in this Codex window. Other windows
may run their own separately bounded workflows. Before starting or resuming a
test, inspect this window's actual workflow and child-worker processes. Do not
start another workflow in the same window while one is active. Follow the user's
iteration cycle: predict, test, inspect the evidence,
learn, then decide the next change and test.

The bounded launcher uses the stable `CODEX_THREAD_ID` to hold this window's
`runs/workflow-windows/<thread-id>/workflow.lock` and select its own systemd
service and slice. Never invent a new ID to obtain another slot in the same
window. Check actual processes as well: older launches may not hold this lock,
and surviving children still occupy this window's slot. A busy slot means do
not launch; it is not a reason to stop another workflow. Cleanup must stay
within the owning window's slice. Per-workflow resource limits remain in force.
