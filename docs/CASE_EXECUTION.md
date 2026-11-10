# Running the fixed one-gene investigation

`gene_annotation_episode.case_execution` prepares a fixed case and delegates
execution to the existing `run_workflow`. It has no separate episode loop,
annotation algorithm, prescribed child sequence, continuation rule or scorer.

The retained earlier preparation is:

```
cases/gene_001/runs/investigation_001/case-launch.json
```

It binds the sole original ybhP gene in the canonical Store, an immutable evidence
inventory, the cached reference corpus, native registry, explicit shared execution
history, models and caller resource limits. `cases/gene_001/execution.toml` supplies
20 GiB RAM, 4 GiB scratch, one allocated native CPU and no work timeout. Native
resource availability is evaluated by the owning launch/tool path; an unavailable
optional executable or statistical history does not prevent other scientific work.

That retained `investigation_001` manifest records the earlier
`single_query_phmmer_jobs_v1` registry. The current immutable-allocation interface
uses v2 registries and does not silently migrate the retained preparation. New
execution needs an unused run directory. `/path/to/new_case_run` below is an
illustrative directory placeholder, not an already prepared or executed run.

## Preparation and inputs

```bash
.venv/bin/python -m gene_annotation_episode.case_execution prepare \
  --case-dir cases/gene_001 \
  --run-dir /path/to/new_case_run \
  --config cases/gene_001/execution.toml
```

Preparation checks the fixed input identity, registers a deterministic caller
evidence index, creates the native registry and initializes the explicitly named
shared history when new. It submits no job, starts no model inference and creates
no assessment/annotation. Missing optional evidence references are reported in
the index while valid references survive. Source assertions remain source data.

An optional `--focus-file /path/to/focus.txt` supplies a caller-owned scientific
assignment, appended to the fixed case question. `prepare_case_run(...,
focus=...)` exposes the same input. Preparation records the exact focus and full
goal in `case-launch.json`; execution and resume use that saved assignment even
if the original focus file is removed. Repreparing with a different explicit
focus returns `prepared_case_scientific_focus_conflict`. Omitting it reuses the
saved assignment. Focus does not alter the fixed target, scoring parameters,
resource limits or numerical continuation rule.

`cases/gene_001/runs/investigation_003` is prepared with
`cases/gene_001/coordination-focus.txt` and the provisional
`scientific_child: interpretation_accounts` binding. It is now running as
`run_3c2467f1f9d04a828efe396ac1dfa276`; its initial scientific credit
2.8764033528067054 is inherited from recorded work. Its saved factory digest is
`d844aa1dedb0b53e45cb040bb834133fc390ae8bf2100adc5c7d6b754c7b71fc`.
The assignment asks the parent to coordinate iterative child investigations;
it leaves questions, methods, order and commissions to the episode. At parent
decision 1 the configured model selected a child investigation of the membrane
fractionation evidence with a closed typed-reference form. The child has recorded
source-linked assessments and five local interpretation-account revisions.
It subsequently yielded after 58 completed actions, returned its typed form,
and the parent used that exact form in decision 2 to revise the annotation.
Decision 3 selected a new iterative functional-transfer investigation. These
actual selections establish scientific child/parent steering; native job-role
selection by the configured models remains unverified. Investigation_002 was externally interrupted for this implementation reload,
with all 120 completed action rows and 120 controller observations verified
unchanged against its saved upgrade checkpoint. It remains resumable;
interruption is not numerical saturation or scientific completion.

The case harness group passed eight checks in 31.56 seconds after this addition,
including actual CLI preparation, saved-focus custody and resume after removal
of the focus file. Independent source review found no concrete defect in that
input path. The execution checks use scripted decisions, not model inference.

The prepared actual index contains 21 source references and 20 retained native
comparisons. It includes the full retained article XML, PubMed abstracts and
queries, UniProt/Gene summaries, genomic neighborhood bytes, family/structure
records, native measurements and transport failures. A retained HTTP 404 body is
a transport response, not a successfully acquired supplementary dataset. Original
bytes and known provenance are preserved without generated scientific summaries.

On execution/resume, the committed Store target, problem and sequence digest are
authoritative. Original staging filenames and mutable case-status labels do not
replace those records. Resuming does not require the original input file once its
immutable material is committed. The evidence inventory is an initial-input
snapshot, not a live annotation table or a credit contribution.

## Explicit policy binding

The first configured-model case used a policy source snapshot with explicit
parameters in `cases/gene_001/runs/investigation_002/parameters.json`.
The live central policy module and its fixed-case setup were later removed when
continuation binding moved to each episode owner. The historical case retains its
saved source and settings. It retains the existing
scientific projection and numerical estimator, with provisional operational units
defined over actual recorded facts. See
[scientific credit bindings](SCIENTIFIC_CREDIT_BINDING.md) for exact meanings and limits.
The harness continues to require an explicit caller implementation instead of
silently borrowing a fixture policy.

For newly loaded factory source, parameters explicitly select
`"scientific_child":"annotation_accounts"` or
`"scientific_child":"interpretation_accounts"`. The latter admits recorded
episode-owned interpretation accounts into the same evidence projection while
leaving task credit annotation-only. A parent sees this configured child binding
before commissioning and defines its own requested typed report.
Investigation_002's original four-section saved factory/parameters remain its
resume authority; the selector is not retroactively inserted into that interrupted
run. Investigation_003 explicitly selected `interpretation_accounts` at preparation
and uses its own saved five-section factory/parameters.

A policy module exports:

```python
def create_policy(parameters):
    return PolicyBindings(
        project_task_credit=...,
        project_scientific_child_credit=...,
        project_job_credit=...,
        project_monitoring_credit=...,
        controller_factory=...,
        task_credit_definition=...,
        scientific_child_credit_definition=...,
        job_credit_definition=...,
        monitoring_credit_definition=...,
        controller_definition=...,
    )
```

These are executable caller functions and nonempty JSON configuration definitions,
not approval flags. The factory constructs policy from the supplied parameters;
it must not perform annotation or submit work outside the episode runtime.
The task projector receives `(store, scope)`. Each scientific improvement child's
projector receives `(store, scope, *, assignment, episode_id, run_id)`. Its
assignment is the original immutable commission: goal, scope, parent report
purpose, closed schema and initial interpretation values. This permits local
credit for a source-linked sub-investigation without requiring that child to
revise the parent annotation. The concrete case's provisional numeric policy is
recorded in its explicit parameters; these interfaces do not select it implicitly.

The job projector receives the Store and named `role`, `assignment`, `episode_id`
and `run_id`. Monitoring has its own projector with the same signature, separate
from launch/extraction credit. The controller factory receives `(path, initial_credit)`
and returns the configured controller. All four credit bindings have separate definitions.
The runtime never adds a scientific or operational child's local score to its
parent's score; the parent projects its own recorded goal progress after the
child action. Nested scientific children use their own original commissions.

The harness independently installs the versioned resource/tool duration
forecaster. Before each new annotation/improvement decision, its explicit
`planning_roles` binding derives proposed execution classes from actual eligible
in-scope protein records and the caller-bound resources. The parent receives
duration/resource expectations before choosing work. No order, translation,
staging or submission occurs during this lookup. If no eligible protein is
available, classes and forecasts are empty; subsequent actual acquisitions can
make one available on a later decision.

The parent selects CPU with the launch query. The durable order and immutable
assignment retain it; the launch child's argument-free `homology.configure`
checks/applies that selection. A repair commission naming an existing job
preserves its original query and CPU. The optional requested `job_cpu` fact
reports assigned CPU threads, not measured consumption.

Estimates are planning inputs, not another credit contribution or controller.
Timing information earns monitoring credit and updates execution expectations;
scientific information earns scientific credit. Jobs are not preclassified as
exclusively timing or scientific. The separate monitoring policy can use
`MonitoringInformationCredit(information_unit=...)`, whose parameters are also
recorded in the job binding; this does not select a production information unit
or time-aware continuation formula.

Projectors are read-only calculations over recorded progress. A local policy's
eligible contributions and denominator belong to its fixed commission and policy;
they must not expand when a child returns additional labels or form fields.
Projection does not acquire evidence, generate an interpretation or fill a form.

Each child's initial credit is recorded before its work. Later local raw changes,
its model context and any requested `x-source: credit` form field use that same
local projector. The existing form admission remains responsible for what crosses
to the parent. No additional report composer, unrestricted field or shared
scientific-learning channel is introduced. Closed facts and completed-action
scores remain frozen on interruption/replay. No scoring choice is implied by
providing this interface.

The scientific adapter can supply both scientific projectors:
`ScientificEvidenceCredit(CreditPolicy.from_record(parameters['scientific']))`.
Its `as_record()` supplies their matching definitions; operational projectors and
the controller remain separately defined. No production factory or scientific
parameter set is selected by this example. The case-entry/resume integration
check uses this actual adapter with synthetic evidence and nondefault explicit
parameters. It passed in 5.14 seconds, preserving the score, parameters and two
own-action observations across interruption and a changed original policy file.
This proves the harness can retain that binding; it is not a configured-model
investigation.

On a child return, the runtime first records that child's actual contributions in
the parent's own action outcome, then projects the parent's credit. This ordering
also applies when the parent is itself a scientific child. A crash between those
steps leaves a recoverable outcome with no score yet; resume projects it without
repeating the child, changing its frozen form or adding an extra observation.

A scientific projector can opt into an ordinary `episode.credit` detail read by
exposing `read_details` with its projection arguments plus `details_limit` and
`details_offset`. Both the catalog and execution select the current episode's
projector. A local projector without this capability cannot accidentally expose
the root/default policy's details.

The parent can also request the optional recorded `episode_yield` fact through
its existing typed form. It copies the actual closing local controller forecast
and decision without diagnostics or private history. This does not choose any
scientific/job score, rate or scheduling policy. See
[EPISODE_YIELD_REPORTS.md](EPISODE_YIELD_REPORTS.md).

Job scoring must use recorded goal-relevant contributions and the original
expectation context associated with each action, not rescore earlier actions
from a later global mean. The decision's statistical input is retained in
`runtime_model_calls.request.context.execution_expectations`. Shared progress,
transport events and later accuracy information are not extra completed actions.

Once a policy has been defined, this interface executes it:

```bash
.venv/bin/python -m gene_annotation_episode.case_execution run \
  --run-dir /path/to/new_case_run \
  --policy /path/to/explicit_policy.py \
  --parameters /path/to/parameters.json
```

The example paths above are placeholders; the concrete case binding is recorded
at the paths given above. The
harness snapshots that entry source, its digest, parameters and effective declared
definitions. Active callables retain their globals; the dynamic import cache does
not retain closed policy state. Imported dependencies are not a complete captured
Python environment and must retain their declared implementation compatibility.

Unused default policies are absent: custom runs record null `credit_policy` and
`controller`, plus their actual binding definitions. Those definitions appear in
model context. Passing default-controller/default-credit settings to a different
custom implementation is a configuration error rather than silently ignoring them.

## Expectations and recovery

The caller-owned homology expectation binding records explicit planning episode
types in `episode_execution_expectation_binding_v3`. Prospective and assigned
classes use the same constructor with actual query bytes, selected CPU and frozen
resources. New launch commissions require CPU rather than receiving a downstream
default. Once reserved, the original native statistical class remains its
authority. A different query size, CPU allocation, database, implementation or
duration measure does not silently inherit another class's numerical estimate.
These reads do not poll a running job or expose scientific findings through
global history. Each decision retains its actual snapshot on replay.

Expected total duration is the exact-class/current-condition empirical mean of
successful complete durations. Failure/censoring support remains visible;
missing history supplies unknown duration, not zero or a launch restriction.
Observed extrema are historical ranges, not calibrated prediction intervals.
Resource limits are not measured consumption, local service wall time is not
separately measured queue wait, and an overrun does not imply zero remaining time.

```bash
.venv/bin/python -m gene_annotation_episode.case_execution run \
  --run-dir /path/to/new_case_run --resume
```

Resume restores the policy source/parameters, resource bindings, original selected
actions and archived reports. It does not replace a completed child's score or
restart an already yielded run. The source snapshot is the policy entry module;
the runtime's existing compatibility requirements still apply to its dependencies.

## Evidence limits

Case-harness checks use the real Store and shared method_loop with explicit fixture
policies and scripted decisions. They cover preparation without launches, partial
input references, absent defaults, unavailable resources/history, interruption and
policy/input custody on resume. The latest correction also checks prospective
forecasts from an existing protein, an initially empty inventory followed by an
explicit translation action and refreshed forecasts, and immutable parent-selected
CPU through assignment, native command, statistics and requested form.

The focused six-file group passed **40 tests** in 96.59 seconds:
`test_case_execution.py`, `test_homology_jobs.py`, `test_assigned_expectations.py`,
`test_homology_episode_runtime.py`, `test_resource_estimation_contract.py` and
`test_episode_timing_learning.py`. The tiny native cases use actual phmmer with
one reference and fixture decisions/controllers. They include actual timing
information reaching monitoring credit, the requested form, updated parent
expectations and a later scripted choice. They do not demonstrate biological
reasoning, a selected production scientific score or a configured-model investigation.

The configured connection separately returned structured responses from
`gpt-6-luna` with `none` effort and `gpt-6-sol` with `medium` effort. The provider
checks the server's reported model/effort against those requests. Those two
transport checks are recorded in `model-role-verification.json`; they are not an
episodic scientific run or a completed annotation.
