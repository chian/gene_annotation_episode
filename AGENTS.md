# Repository layout

Episode folders (`gene_annotation_episode/episodic_workflow/root/` and the
nine axis folders beneath it) contain only episode bindings and their tests.
The library lives in `gene_annotation_episode/episodic_workflow/episode_support/`,
grouped by what the code does. The system is three top-level packages of the
repository, beside `gene_annotation_episode/`; none is inside `episode_support/`:
`episode_runtime/` is the generic runner (linking, the run journal, custody, the
Store under custody, resume) and holds the episode base type
`method_loop/episode_type.py`; `method_loop/` is the generic method loop the
runner is built on; `yield_control/` holds the yield estimators.

# Private episode bindings

Every episode is its own private binding. An episode never inherits from,
subclasses or shares a behaviour module with another episode: tuning one
episode must not change any other. Every episode binding inherits directly from
the system's episode base type, `EpisodeBinding` in `method_loop/episode_type.py` (not in the
generic `method_loop`), which carries the system
behaviour (recording, custody, tracing, replay, the runner's hooks) and declares
what each episode must supply; it inherits from nothing else. Similar episodes therefore have copies of
their binding files, and the copies are intended. Shared code is library
functions only, which an episode calls explicitly with its own pieces. There is
no table of bindings and no base class for bindings.

Each episode folder holds exactly these files (plus `__init__.py`, its child
episode folders and `tests/`): `goal.py`, `task.py`, `credit.py`,
`yield_estimator.py`, `episode.py` (ties it together), and a `messages/` folder
with `read_from_parent.py`, `msg_to_child.py`, `read_from_child.py`,
`internal_summary.py` and `final_to_parent.py`. Every function an episode needs
fits into one of these files. In the carry-over, old-runner machinery is
not needed and is not carried; every episode function must end up somewhere in
the scheme — in the episode file it serves, or as a parameterized library
function in `episode_support/` that the episode calls. None is dropped. An episode with no children has no
`msg_to_child.py` or `read_from_child.py`.

How records are passed faithfully between episodes — receipts and custody:
which records a parent passed to a child, what a child returned, what an
action produced, and the check that an episode reads only records it actually
received or produced — is part of the system (the generic runner, like
`method_loop` and `episode_runtime`), not part of any episode definition and not
a per-axis library. Episodes only name the records they pass and read through
the runner. The same holds for every tracking, tracing and replay device:
recording decisions and model calls, units and their outcomes, commissions,
child returns, reports and progress, the run journal, and resume. These are
part of the system and work automatically for any episode that follows the
system; episodes contain no recording or replay code.

How the system fails and stops (owner's rules, 2026-11-19):

- A parent knows how to call its child; that is what writing its
  `msg_to_child.py` and prompt is for. If a commission is wrong — a selection
  the child does not declare, a record the parent does not hold, any error in
  the prompt construction — it fails. There is no fallback, no extra check,
  no autofix, no feedback path and no cleanup for it: the run fails with its
  error message. Nothing is added to the system to catch or repair a wrong
  commission, and no link-time check of one episode's names against another's.
- Stopping belongs to the episode's yield estimator alone. Every unit's credit
  change goes to the estimator and the estimator decides when the episode
  stops. The system has no concept of observed or unobserved units, and no
  other stopping rule. Whether a lookup, wait or check earns credit is that
  episode's own credit and settings.
- Library functions never write to the Store or its tables directly. Anything
  they read or write goes through custody: the scoped store the system hands
  the episode, or an operation that has custody built in.
- `store.db` (the old Store's raw SQLite connection) is not part of the
  structure. Nothing is written against it, wrapped around it, or given back to
  the custody store as a compatibility layer. Old code that used it is
  rewritten: records come in through the custody reader, results go out through
  the scoped store, a function's own tables are declared work tables, and what
  cannot be expressed gets a system operation with custody built in. No stub or
  `NotImplementedError` stands in for behaviour that was not rewritten.
- `yield_estimator.py` reads what `read_from_parent.py` produced, never the raw
  assignment; `read_from_parent.py` is the only place an assignment is read.
- A child declares every field it can return; the parent selects which of them
  it wants in `msg_to_child.py`; credit and finding are always returned.
- Controlled messaging overrides everything else in this file. What passes
  between episodes (`msg_to_child`, `final_to_parent`, what `read_from_child`
  shows a parent's model) is controlled data only: numbers, booleans, values of a
  fixed vocabulary and record references. There are no open fields: every
  field has a controlled answer set that code can validate (a number in a range,
  a count, a boolean, a value from a fixed vocabulary, a record reference, or an
  annotation: a gene, function or product ID or name, a controlled name that
  comes from a looked-up list; an annotation is a real data field, not free
  text), and one field holds one thing. Evidence is spread over such fields, never put into
  one field, and never written as a paragraph, which would give prompt injection
  a way in. The messages are small
  and chosen by the sender for the receiver's next decision; credit is the
  progress and productivity signal. A requirement elsewhere in this file that
  would need free text to pass between episodes is met by keeping the record in
  the episode that wrote it and passing its reference.

The episode tree was articulated so each episode could be tuned on its own. The
owner decided on 2026-11-18 that each episode's own files at commit `97308b94c`
(the episode trees `root/<axis>/<role>_evidence/**` only) are carried over as
the source of that episode's intention: the files return to that episode's
folder and only their old-runner machinery is replaced by the new runner and
library functions. The old shared root (files directly under `root/`,
`root/library`, `root/scientific_process` and the duplicate top-level trees at
that commit) is never restored and never read as a guide.

# No version names; one version of everything

Nothing in this code is named after a version: no `_v2` on an identifier, string
constant, schema or record-kind name, `version` field value, function, file, folder or
fixture; no `legacy_`, `old_`, `previous_` or `deprecated_` copies kept beside the live
one. Code is versioned only by git commits. In a given episode folder there is exactly
one version of every file and every function, so nothing can be confused with an older
shape. An old version is dead: delete it at once (see the next section) and let the
survivor take the plain name. Names of outside tools, databases and file formats keep
the outside world's own version (a BLAST+ release, an Rfam release, NCBI database
format 5): that is a fact about the outside, not our versioning. Fix a violation by
reading the code, deciding per name which version is live, and applying that decision
everywhere the name is used; never by a blind pattern rename. A new name that follows
an existing wrong pattern spreads it: follow this rule, not the pattern.

# Removing unwanted code

When something is no longer wanted, delete it directly. Not wanting it is the
judgement: nothing about it is preserved. Do not trace its dependants first,
keep backward compatibility, add shims or aliases, wait until nothing imports
it, or run tests or tools to decide whether it may go. The breakage that
follows is the useful signal: each break is either rebuilt on the wanted design
or was only serving the unwanted thing and is deleted with it. In a
replacement, delete the old path before porting onto the new one, so hidden
dependencies fail immediately instead of passing silently. Never restore
deleted code to make something pass.

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

For experimental_activity_evidence (A105) and sample_context_evidence (A108),
interpreting applicable evidence includes selecting its
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
`investigation_finding`: evidence for an annotation, giving what type of
evidence it is and how strong it is, as controlled features read from the
grading (subscoring) sheet by code, such as the number of assays, the
statistical deviation or noise, and the signal. They are numbers, counts and
fixed-vocabulary values, never prose. The sheet stays a record of the episode
that graded it; the parent receives the features and the sheet's reference.
Do not manufacture target support to obtain credit.

A selected tool or reasoning unit that executes and returns must enter its
original iterator with its existing progress measurement, including an invalid,
failed or unavailable result. Rejection before a unit is acquired creates no
executed action or observation. Preserve the original action identity; do not
omit a returned invalid outcome from the iterator or invent progress for it.

# Evidence-axis bookkeeping

To build another evidence axis (A102 to A110) the way A101 was built, follow [the evidence-axis build SOP](docs/sop/evidence_axis_build_sop.md).

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
