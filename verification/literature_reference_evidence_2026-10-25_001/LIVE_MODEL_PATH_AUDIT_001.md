# Read-only audit: configured model execution for source literature

2026-10-25. Scope: application/provider/configuration inspection only. No source
paper or retained paper packet was opened. No server, catalog request, model,
scientific workflow, controller or external service was started. Only this new
owned audit document was written. CLI version/help were inspected; they do not
prove account or model availability. No credentials were inspected or printed.

## Established executable path

The existing public callable is `gene_annotation_episode.runtime.run_workflow`
(runtime.py:3771), with `provider=None` for the real configured transport. It can
receive `episode_binding_factories=(partial(LiteratureEpisodes,
rate_population=True),)` and actual `initial_known_record_refs`. Set the parent's
scientific goal/scope explicitly. The existing optional
`annotation_child_roles=('literature',)` restricts the annotation parent's declared
child alternatives to the actual literature entry; it does not impose a child
sequence or choose an action. The literature child's ordinary assignment and
closed return form remain its parent's selected commission.

Leave `controller_factory` and `project_credit` unset to bind the existing
standard-default scientific/controller implementation rather than a test fake.
The standard path supplies ScientificFindingProgress, receipt knowledge and an
ordinary YieldController; it also supplies its supported durable reconstruction.
Use `build_tools(store, configuration)` rather than a custom unregistered tool
facade, so the actual reconstruction configuration is recorded. This is a
callable path, not an existing turnkey literature-specific CLI subcommand.

The simple CLI `gene-episode run --workspace ...` invokes run_workflow but does
not enable the new experimental population profile. It is insufficient by itself
for this goal. A small caller using the public callable is required. The fixed
case preparation path adds local native jobs and custom policy machinery; those
are unnecessary for a source-only literature demonstration.

## Actual current default configuration

`gene_annotation_episode/defaults.toml` and runtime's effective configuration
were read. Current packaged values are:

- connection command: `codex app-server --stdio`;
- REASONING: `gpt-6-sol`, effort `medium`;
- FAST: `gpt-6-luna`, effort `none`;
- decide and child interpretation route to REASONING;
- controller: cost0.001, window_size8, subsample_size4, uncertainty_alpha0.05;
- scientific finding_unit1, loss_preview_size24, explicit initially known refs;
- restoration preview_size24;
- local job limits20GiB memory and4GiB scratch, without wall-time budget.

These are observed existing defaults, not newly selected model recommendations
or permission to substitute a model. Explicit caller configuration is used in
full; saved runs retain their original model/controller bindings. ModelConnection
checks the server-selected model and effort against the requested values.

Local executable verification: `command -v codex` returned
`/usr/local/bin/codex`; `codex --version` returned `codex-cli 0.163.0`.
`codex app-server --help` confirms `--stdio` is supported as an alias for
`--listen stdio://`. The `.venv/bin/python` interpreter exists. No service was
started by these help/version checks. The app-server initialize/model-list and
actual model turn remain unverified until the parent performs a real invocation.
No official-documentation fallback was needed to establish these local facts.

## Real transport and text presentation

providers.py was read in complete portions. `_SessionConnection.__aenter__`
starts the configured subprocess and performs initialize/initialized. `_session`
starts an ephemeral thread per episode/role, disables native execution/research
features, supplies the workflow's structured-output contract and rejects model /
effort substitution. Models return the selected action; Workflow executes it.
`complete` records the original context/schema and actual rendered text, sends
turn/start, retains public response/events, rejects model-side tool requests and
parses finite structured JSON. No report-composer model is inserted.

The experimental literature marker selects the source TASK/STEERING renderer
through the existing bootstrap/update/lookup/reconstruction path. Current
LiteratureEpisodes supplies that marker to its own roles when rate_population
is enabled. Facts use the ordinary typed source namespaces and exact saved
numerical/reference validation. Source custody checks use the actual episode's
received refs and scope. A source existing globally is not authorization.

A presentation gap remains for the proposed complete parent/child live run:
public run_workflow always builds `annotation/root` (runtime.py:4131), and exposes
neither root_role nor an initial root literature assignment. That root lacks a
published-scientific or experimental-literature marker, so `_presentation` falls
back to JSON. Its literature child gets TEXT TASK/STEERING, but this does not
prove the parent side meets the adopted every-prompt requirement. Do not claim a
fully compliant live parent/child run from the child renderer alone.

Existing extension point: EpisodeBindingRegistry.initial_decision_context
(episode_bindings.py:198) invokes explicitly bound callbacks for every role;
DecisionSource.call supplies their fields before a new model call
(runtime.py:821). An explicit caller-configured source-parent TASK/marker could
use this hook without another episode/private loop. It must preserve the parent's
own assignment and typed receiving meanings, rather than infer task from a fact
source or import child/private history. This audit did not implement that option.

## Continuation and scientific-credit limit

YieldController and its continuation consumer were inspected. The only numerical
stop is an available projected marginal upper bound <= configured cost. Window8
is minimum information for fitting, not eight turns, a source-completion rule or
a cap. Do not use FixtureController, fixed action counts, artificial completion
credit or a hidden zero-history shortcut for the live demonstration.

Default ScientificFindingProgress credits received, current, retained typed TARGET
assessments through FindingIdentity/FindingValidity. Source sheets, numerical
operand references and context/source metadata alone earn zero under it. A
source-only demonstration may therefore have zero scientific credit while
retaining useful source results. The live run must report this honestly and let
the unchanged configured controller own continuation. This audit does not infer
a replacement progress unit, source-count bonus, target-transfer assessment or
new annotation score. Source outputs must not be relabeled target findings merely
to stop sooner or manufacture progress.

## Durable binding, restart and isolation

`application_execution_binding.py`, `episode_composition.py` and
`independent_execution.py` were read completely, as were the public run/restore
functions. With owned ModelConnection, new standard-default runs automatically
publish the known durable application reconstruction before work. Known
LiteratureEpisodes descriptors/configuration, including the opt-in profile, are
restored from saved settings and compared by implementation hash. Parent-selected
scope/form/knowledge receipt manifests and source/version digests are checked
when a detached child is opened through the shared method_loop worker.

The independent implementation hash includes EVERY Python source file under
`gene_annotation_episode` and `method_loop`, not just this literature branch.
Concurrent tool-grader edits can therefore invalidate a child or resume in the
shared checkout. The parent should execute from an isolated pinned snapshot of
the actual packages and necessary package assets, with an explicit import path,
using a fresh separate Store/run directory. Preserve the original target inputs
and saved investigation; do not open another scientific parent against its live
shared Store. A pin must remain unchanged while its root or descendants are live.

Resume requires the same Store/problem/directory, model/controller/projector
identities and definitions, initial known refs, binding descriptors and immutable
goal. Do not repair a running pin in place or replay historical scores with new
code. A provider restart opens a new transport audit directory but reuses saved
selected actions/results/receipts. A yielded closed run is inspection on resume,
not a fresh epoch. Survival/restart must be demonstrated with actual handles and
committed evidence, not a descriptor or a state-file existence check.

## Parent decisions or remaining actual inputs

No user permission question is required merely to use the authorized configured
path. Still needed before a real demonstration: the exact actual source assignment
and typed requested form; the parent presentation correction or an explicitly
reported limited demonstration; an isolated stable code/data/run setup; and an
actual transport/model call to establish available account/model behavior.
Keep the current default model/controller values unless the actual caller/user
has supplied different authorized configuration. The root's source investigation
and later biological target correspondence remain separate.

Inspection sources: cli.py; providers.py; defaults.toml; public_configuration.py;
tool_configuration.py; runtime.py public configuration/run/restore, Workflow
assembly and initial decision-context consumers; default_scientific_binding.py;
investigation_progress.py; numerical.py continuation/controller consumers;
episode_bindings.py initial-information/received-fact hooks; literature_episodes.py;
episode_composition.py; application_execution_binding.py; independent_execution.py;
existing scripted literature integration caller setup. Initial batched output
truncations were repaired with complete relevant sequential file/function reads.
No source-packet reset or primary-paper review is claimed by this technical audit.

## Concrete caller shape (not executed)

The existing synchronous shell entry is `.venv/bin/python CALLER.py`; that caller
can use `asyncio.run(main())`. After registering the actual immutable target and
source records in its isolated Store, the existing relevant call is exactly:

```python
from functools import partial
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tool_configuration import build_tools

tools = build_tools(store, configuration)
summary = await run_workflow(
    store, tools,
    provider=None,
    provider_config=configuration,
    run_dir=run_directory,
    resume=False,
    goal=source_investigation_goal,
    initial_known_record_refs=actual_source_references,
    episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
    annotation_child_roles=('literature',),
)
```

No replacement model/controller or progress callable belongs in that invocation.
For resume, use the same directory and `resume=True`, without replacing original
knowledge/goal/binding settings. The actual public root loop is
`root = workflow.build('annotation', 'root', settings['goal'], scope)` followed by
`record = await root.run_async(workflow.context)` and
`await root.build_result(record)`. Literature children use this same shared loop
through their actual selected commission. The root presentation gap above must
still be addressed before treating this shape as a complete compliant run.
