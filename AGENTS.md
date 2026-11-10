# Repository layout

# Local execution policy

Keep instructions local to their subject. Machine resource bounds and research
stopping budgets are different categories. Permission or a requirement for one
does not authorize another. On 2026-11-04 the user clarified: no elapsed-time,
token, turn, action-count or cumulative-usage budgets; retain sane compute bounds.
The execution environment constrains CPU and RAM. The
application must not gain deadline or usage-budget configuration/enforcement.
Do not set a runtime maximum, even to an unlimited value. Do not substitute a
different stopping gate. The scientific continuation controller is separate.

Run one local workflow at a time per Codex window, not globally across windows.
Within a window, never overlap examples, investigations, tests, benchmarks, or
background runs. Count Python coordinators, model
provider processes, native workers, and all their descendants as one workload.
Use the single-workflow launcher for every local Python command.
Confirm the complete workload has exited before starting the next command.

The launcher manages ownership and machine resources: one CPU, 5 GiB RAM
(increased by the user on 2026-11-04), and no swap across the whole workload.
Do not increase those bounds or move another window's work without authorization.
Never introduce or enforce process/thread count ceilings or arbitrary time,
token, turn, action-count or cumulative-usage cutoffs, in code, launchers,
configuration, tests or assistant-run commands. Episode continuation belongs to
its credit-based iterator. The CPU and RAM bounds above do not authorize other
cutoffs. An assistant-written policy file is not authorization to introduce them.

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
may run their own workflows. Before starting or resuming a
test, inspect this window's actual workflow and child-worker processes. Do not
start another workflow in the same window while one is active. Follow the user's
iteration cycle: predict, test, inspect the evidence,
learn, then decide the next change and test.

The launcher uses the stable `CODEX_THREAD_ID` to hold this window's
`runs/workflow-windows/<thread-id>/workflow.lock` and select its own systemd
service and slice. Never invent a new ID to obtain another slot in the same
window. Check actual processes as well: older launches may not hold this lock,
and surviving children still occupy this window's slot. A busy slot means do
not launch; it is not a reason to stop another workflow. Cleanup must stay
within the owning window's slice.

# Required literature evidence processing

For A105 and A108, interpreting applicable evidence includes selecting its
purpose-specific grader and saving its subscoring sheet. An accepted scientific
interpretation must not receive credit before that sheet exists. Couple those
operations within the original action; preserve the ordinary iterator and
parent report/credit path. Metadata preparation alone is not an evidence
assessment. The only source-processing outcome that may omit grading is a
source-grounded finding that the examined material contains no applicable
experiment/result (A105) or contextual observation (A108). Missing measurements,
controls, uncertainty or identity/context links require partial/unresolved
grading. Acquisition or processing failure is not evidence absence. Save the
sheet even when the parent requests no cells for immediate delivery.

Grading coverage applies to actual experiment/result references, observations,
assessments and conclusions. Descriptive metadata remain context and must not
be presented as graded evidence or rejected merely because a grader does not
consume them. Metadata cannot satisfy missing scientific coverage.

An A105 result reference may describe an outcome of an assay. Grading must
follow its authenticated observation-to-assay link; do not require each such
result reference to become a separate experiment. Keep A108 original
observation identities explicit for its evidence counts.

Each A105/A108 evidence assessment must also retain its typed
`investigation_finding`: the actual source claim, actual source subject and
qualification, including unresolved target correspondence. This is the existing
scientific finding consumed by the iterator and parent; a saved numerical sheet
alone does not supply it. Do not manufacture target support to obtain credit.

A selected tool or reasoning unit that executes and returns must enter its
original iterator with its existing progress measurement, including an invalid,
failed or unavailable result. Rejection before a unit is acquired creates no
executed action or observation. Preserve the original action identity; do not
omit a returned invalid outcome from the iterator or invent progress for it.

# Evidence-axis bookkeeping

Read [the central evidence-axis ledger](docs/EVIDENCE_AXIS_LEDGER.md) before
reporting axis status. Confirm changes in executable code and, for execution
claims, retained results/receipts before recording them. Update the affected
scope and dated change history when work changes its status. Keep implementation
completion, workflow validation, shared-root integration and later extensions
separate. Do not downgrade completed work from an older unsuccessful run, a
missing scientific operand or a separate extension. Identify an actual regression
or explicit scope change before reopening it. Do not infer live process state
from an old report, equate scripted decisions with autonomy, or count saved
components as proof of an unexamined full-workflow goal.
