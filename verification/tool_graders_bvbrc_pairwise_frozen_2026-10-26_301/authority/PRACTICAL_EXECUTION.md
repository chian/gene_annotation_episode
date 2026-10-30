# Practical execution and validated completion

This is an additive record of the 2026-10-22 implementation. The read-only
`EPISODE_STRUCTURE.md`, the immutable goal and older implementation records are
preserved. The later user direction recorded below takes precedence for this
specific practical endpoint behavior.

The user's words:

> Each "turn" is a command, open a window, gather information, move to the right directory, whatever, write code, setup env, setup scripts etc., and all the necessary steps need a credit assignment and a validation check.

> once you have confirmed "completed" you need to switch the credit expection to zero right away.

## Mechanism

The parent commissions an existing resource-specific episode with the job,
constraints and original typed return form. Its ordinary shared `method_loop`
owns each next choice. Creating a directory, selecting a working context,
writing exact bytes, running a preparation command, refreshing inventory,
starting the requested job and examining its status/results are separate
available operations. There is no required order or separate setup workflow.
There is no private model loop inside a tool.

The opt-in `PracticalResourceEpisodes` binding currently supplies `launch_local`
and/or `launch_hpc`, according to explicitly bound resources. It does not replace
the older resource binding in existing runs or add scientific/literature episode
types. A caller chooses this binding for those roles; duplicate role bindings
cannot coexist in one registry. Existing API execution is not routed through
local or PBS operations.

Each selected action freezes its intent before execution. Its immutable receipt
records the original operands, working context, actual outcome, validation
assessments and timestamps. Replaying a completed action reads that receipt.
A valid command returning nonzero remains a completed action with an
unsuccessful native outcome. Malformed/unexecuted requests produce feedback and
no action observation. An uncertain native side effect remains explicit and
must be reconciled against its original identity; it is never blindly repeated.

Repair can be followed by an explicit `practical.job.start` selection naming
`retry_failed_execution_id`. A new attempt requires that exact current job to
have a confirmed failed terminal outcome. The selected retry receives its own
durable native identity; replay of either attempt preserves its original result.
Active or unknown work is not replaced. A nonzero `qsub` client exit preserves
the original client outcome but does not prove scheduler rejection. Submission
remains unconfirmed until identity-verified recovery. Retrying a submission
without an actual job ID is currently explicitly unsupported; no replacement
submission is made to resolve that uncertainty.

Command outcomes expose bounded stdout/stderr tails with byte offsets and full
log paths. `practical.file.read` supplies an explicitly selected byte window and
its original bytes, allowing further inspection without pretending that a tail
contains the complete log. Safe filesystem and inventory-validation failures
are recorded as failed outcomes; the episode can choose a repair next.

Working context explicitly contains cwd and environment. `cd`/`export` inside
a subprocess does not alter the next turn. The context-setting operation
validates and persists the transition, without incrementing its revision for an
unchanged context.

## Validation, credit and terminal expectation

The original assignment supplies named, closed predicates with explicit caller
credit units. They are desired facts, not an ordered procedure. Available
predicates cover working context, actual file/directory presence, exact file
hash, an observed command outcome, usable requested-job handoff and completed
requested-job outputs. More domain-specific validators can be added as actual
contracts rather than unconstrained claims.

Initially established preparation is baseline cumulative credit. Each own
completed action supplies its actual new cumulative score once. Repeated facts
gain zero; an observed loss remains a signed loss. An unrelated action does not
erase earlier command evidence merely because its result lacks that fact.
Validation and valuation remain separate: a correctly executed action can earn
zero. The implementation supplies no arbitrary per-command/file bonus or
automatic numerical weights for unknown kinds of preparation.

Only actual requested-job primitives can establish the endpoint. A generic
preparation command cannot self-declare the requested job complete. Successful
environment setup alone is insufficient. A launch endpoint may finish after
establishing a usable native handoff while its job continues; an output endpoint
requires the original requested job's successful outcome and its declared
output checks.

The completing receipt yields a proof tied to run, episode, assignment digest,
operation, receipt digest and original validation keys. Runtime adds its actual
completed-unit and decision identities to the frozen estimation context. The
opt-in estimator verifies those identities and the authoritative receipt, then
returns an exact-zero future band immediately, before the statistical minimum
window if necessary. The completing action's actual gain is retained. The
existing controller comparison closes the episode with its ordinary yield-stop
mechanism; no synthetic zero observation or extra model turn is added. A typed
`practical_completed` fact distinguishes task completion from yielding partial
work. New operations cannot mutate an already completed practical assignment.

The parent can request `practical_receipt_refs` in the original typed form.
A later resource episode can supply `{"receipt_ref": "source_..."}` to
`practical.job.status` or `practical.job.collect`. The receiver validates that
saved source's scope, job and resource identities, then observes the original
native execution and its own declared output predicates. The launch need not
have declared the later output checks. The receiving episode records its own
observation; the closed launch's receipts, controller and credit remain fixed.
This is a resource operation receiver, separate from the existing recursive
monitor episode's progress-provider schema; this build does not replace that
schema or claim a new general PBS monitoring integration.

This does not add a scientific acceptance gate, change the default estimator,
combine scientific/monitoring scores or invent a duration-transfer model.

## Inventory and initial information

`execution_inventory.py` defines strict component/catalog/snapshot records.
Components independently describe environments, software, database releases,
indexes and prepared parameterized operations. Prepared operations name a real
bound callable and its exact input schema. Inventory cannot install a new tool
or replace the run's fixed tool map.

The caller explicitly reconciles remote catalog bytes and its local mirror
before the choosing episode's first decision. `PracticalServiceFactory` accepts
those already recorded snapshots and supplies them to the scientific parent as
well as the resource episode. Construction/reconstruction performs no remote
discovery. The child's assignment retains the original selected snapshot.
The choosing episode also receives the actual bound workspace, local limits
or PBS charging account before its first choice. Missing initial inventory is
explicitly null; transport command operands are not needed in that decision
input. Infrastructure does not infer an alternative workspace or allocation.

Matching digests establish catalog equality, separately from current physical
usability. Unavailable remote inventory retains a dated cached catalog with an
explicit unavailable status. Invalid catalogs cannot replace the mirror.
Subsequent `practical.inventory.refresh` is an ordinary selected operation; its
receipt preserves the original bytes, validated catalog and reconciled snapshot.
No refresh occurs automatically each turn. File presence checks use stat;
large database bytes are hashed only for an explicit hash predicate.

## Caller configuration

```python
from gene_annotation_episode.practical_service_setup import PracticalServiceFactory

factory = PracticalServiceFactory(
    resources={
        "local": {
            "kind": "local",
            "workspace": "/absolute/project",
            "policy": {
                "memory_bytes": 1073741824,
                "scratch_bytes": 10737418240,
                "wall_seconds": None,
            },
        },
    },
    initial_information={"local": already_recorded_inventory_snapshot},
)
# Pass factory and factory.as_record() as episode_service_factory and
# episode_service_binding to the ordinary caller. Its scientific credit
# configuration remains caller-owned. A supported standard caller reconstructs
# the same saved factory, resources, inventory, role definitions and settings.
```

The ordinary parent `episode_child` selection remains the single commissioning
action; it supplies the assignment and requested typed form. The existing
durable commissioning machinery supplies its execution handle and independent
worker placement. No second autonomous execution workflow is introduced.

The practical assignment's exact schema is exported as `ASSIGNMENT_SCHEMA`.
It includes the original requested argv/environment, resource kind, endpoint,
workspace, initial context, inventory snapshot, progress requirements,
completion keys and constraints. The caller supplies original credit units;
the episode cannot change them or its endpoint during the assignment.

PBS configuration uses `kind="pbs_ssh"`, explicit `workspace`, `ssh_argv`,
`python_executable` and `account`. `ssh_argv` must preserve the appended remote
command as one command string; use a real quoting-preserving transport wrapper
for a multihop login. No hostname, credential or allocation is guessed.
The episode selects native queue/resources explicitly before submission.
Submission token, original PBS job ID, queue/priority fields, logs and observed
timestamps remain distinct records. Loss of a submission reply triggers original
identity reconciliation, never a replacement `qsub`. Unknown current scheduler
state stays unknown. Aurora defaults remain BioReason project storage and
`EpiCalib` charging; home receives only its existing small tracking index.

## Evidence and limits

The focused tests execute real tiny local systemd-backed commands/jobs through
the shared Workflow, with scripted decisions rather than a model. They cover
setup, reuse, failed executed commands, malformed unexecuted requests, immediate
endpoint closure, a continuing submitted job, exact replay and typed parent
returns. Separate tests exercise immutable records, inventory reconciliation,
proof qualification and saved caller reconstruction before provider entry.

PBS tests execute the actual remote-worker code locally against controlled
`qsub`/`qstat`/`qselect` fixtures. They exercise native selection, account/storage
constraints, command receipts, queue facts and uncertain-submission recovery.
They establish protocol behavior, not an ALCF deployment. No new ALCF job or
configured-model scientific investigation was run for this build. Duration
records retain their actual measurement meanings; missing duration expectations
remain unknown. Operational credit tuning and additional validators remain
explicit caller choices, not hidden acceptance rules.

The fixed implementation checklist and exact module handoffs remain in
[the original contract](PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md).
