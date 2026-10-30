# Independent episodic investigations

The user accepted this design as the direction to implement and adjust on
2026-10-21. It supersedes the earlier blocking-tree proposal. Acceptance is not
evidence of implemented behavior; the implementation boundary is stated below.

## Unit of composition: problem-solving process intelligences

The central unit is an intelligence carrying out an iterative problem-solving
process. A parent invokes another such intelligence to address a scoped problem,
receives information through its requested form, and uses that information in
its next decisions. The child interprets outcomes, revises its approach and can
invoke further problem-solving processes. An episode is a decision point that
iterates; a primitive operation remains a tool call within that process.

The information library is a collection of problem-solving processes. Retrieval
helps construct the child's decision problem. When an investigation wants to
work on something, the library supplies relevant ways of working on it. That
process information fills a common mother episode template to construct the
child on demand, with a small relevant set of alternatives on each turn. The
parent need not hand-design a separate episode implementation for every kind of
problem. Tool and resource instructions can support a process, but a collection
of those instructions alone does not supply this composition.

The implementation boundaries follow that distinction:

| Owner | Responsibility |
| --- | --- |
| Common episode template | Shared iterative machinery, identity, controlled communication, durable execution and the configured continuation interface. |
| Library process information | Composable annotation-focus and thought-pattern information for the scientific child's decision problem; actual tools are retrieved separately for the assigned investigation. |
| Assigning parent | The requested job, scope, constraints, supplied context and typed information it needs returned. |
| Constructed child intelligence | Repeated choices within that decision problem, interpretation of actual outcomes and revision of its approach. |
| Primitive execution and state adapters | Actual selected operations, source custody, recorded facts and validation against bound capabilities. |

Caller-owned resources, numerical bindings and parent constraints retain their
existing owners. Library retrieval supplies process information; it does not
make the child's decisions or introduce another autonomous workflow layer.
Permitted child relationships limit alternatives without prescribing which
children run, in what order, or how many times. The literature hierarchy below
is an intentional example of this narrowing.

Implementing particular literature processes and implementing library-driven
construction from the common template are separate responsibilities. Existing
handwritten episode bindings and retrievable manuals alone establish neither a
process-definition library nor the on-demand constructor. The later scientific
three-slot implementation and outstanding construction boundaries are described in
[TOOL_KNOWLEDGE.md](TOOL_KNOWLEDGE.md).

For bioinformatics construction, the parent combines an annotation-credit focus,
a thought pattern and a retrieved set of actual tools. The tool retriever uses
the parent's desired investigation to select multiple operations from the actual
tool map. Tool sets and composed scientific episodes are not predefined library
entries. A/P options supply reusable components, rather than complete episode
designs. The literature relationships below are a separate design responsibility;
they do not supply or explain these scientific slots.

## Episode branching

```text
Scientific investigation: which uncertainty matters next?
├─ Scoped scientific investigation: how can this question be resolved? ↺
├─ Literature investigation: what published evidence answers this question?
│  └─ Strategy: which search approach is productive?
│     └─ Search: which returned sources deserve examination?
│        └─ Page: where and how should this source be examined?
│           ├─ Table investigation
│           ├─ Ordered reading
│           └─ Targeted passage investigation
├─ Launch: which execution approach is productive?
│  ├─ API/service: how can this work run through this service?
│  ├─ Local compute: how can this work run on this machine?
│  └─ HPC: how can this work run through this environment and queue?
├─ Monitor: what further progress information is useful?
│  └─ Monitor: what further information is needed from dependent work? ↺
└─ Results acquisition: how can the requested results be obtained?
```

Every node is an iterative decision point. Scoped scientific investigations have
the same branching options recursively, with a narrower question and context.
These are available choices, not a prescribed sequence. Literature and
bioinformatics can motivate each other in either direction. Tool categories and
retrieval can narrow context without compulsory extra episode levels.

## Independent execution and ownership

A scientific episode can commission work and continue deciding while that work
executes, including computational jobs and child episodes. Scientific ownership
remains with the assigning parent even when launch helpers establish execution
elsewhere. Process placement does not change the goal or reporting relationship.

A durable commission identifies parent, goal/scope, requested return form and
field meanings, supplied inputs/versions, constraints, selected resource and a
semantic execution handle. Internal audit identities stay distinct from
parent-facing semantic handles.

Launch chooses an approach where the scientific parent leaves that choice open.
Resource-specific launch children receive the selected work and software/resource
information; their outcomes inform launch's next decisions. Infrastructure
executes selections without choosing resources or substituting work. Process
creation establishes neither scientific progress nor successful completion.

Implement independence in shared method_loop and its durable binding, not a
private agent loop inside a tool or tasks sharing the mutable nesting stack.

## Controlled communication

Parents define forms before commissioning children. Recorded facts come from
actual records. Interpretations use declared fields and allowed values. Validate
meaningful references and field relationships. Retain actionable failures and
valid partial work. No extra FAST composer or unrestricted summaries.

A monitoring episode closes and returns its requested progress update while the
scientific investigation may remain open. A scientific investigation returns its
scientific result through its original form at closure. Monitoring can return
requested committed intermediate findings through constrained fields, but not
private reasoning, unrestricted summaries or uncommitted intentions. Scientific
integration remains the receiving scientific episode's decision.

## Recursive monitoring

A monitor obtains exposed information about its target and can commission deeper
monitoring when its request needs information about dependent work:

```text
Scientific parent
└─ Monitor investigation X
   └─ Monitor X's child Y
      └─ Monitor Y's dependent job
```

Each monitor iterates and returns its own parent-defined form at closure. Deeper
updates pass upward through these forms. Requests do not automatically traverse
all descendants. A monitor may have sufficient information, need one dependency,
or estimate little yield from further observation. Its controller governs
continuation.

Example requested fields: semantic execution handle; state enumeration;
observation timestamp; elapsed measurement and its meaning; requested progress
measurements or committed-record references; dependent handles/states; result
availability; constrained failure code and affected references. These are
examples, not a compulsory universal form. Preserve observation time and
provenance; old observations are not new samples.

## Yield-informed waiting

Waiting is an explicit episode-selected action while the episode stays open.
It can await a specified report/event, any event from a selected set of
commissions, or a chosen reconsideration time. Persist its condition, start,
actual duration and wake reason. Waiting is distinct from episode termination.

The wait-yield estimate uses known pending work, previous returned progress,
relevant timing expectations and the episode's own history to assess useful
information/progress expected over a proposed wait. Unknown expectations stay
unknown. The episode chooses whether and what to await; runtime executes it.
There is no fixed polling cadence or automatic decision to keep waiting.

Continuation estimation also receives relevant outstanding-work information:
available continuation includes waiting. A quiet interval alone is not proof of
exhaustion. Scientific yield, monitoring yield and duration expectations remain
separate; this design introduces no master hypervolume or gain/time scalar.

## Accounting and continuation

Actual work, recorded state, received information and credit describe the same
contribution. Starting work earns no anticipated scientific credit. Retain
separate scientific investigation progress, annotation-support softened
hypervolume, monitoring information and technical duration learning. Intermediate
and final returns of the same contribution do not earn duplicate credit. Child
scores are not added to parent scores instead of projecting received information.

A commissioned child remains pending until its result returns. Its internal turns
do not become parent turns. A selected wait has one completed-own-action
observation when it returns, with zero gain for passing time alone. A returning
child separately completes its previously commissioned action. A report arrival
can complete both an outstanding child action and a selected wait; their
observations must not credit the same contribution twice. Completion ordering
and controller stopping at this boundary must be explicit and tested, without
silently changing the numerical rule.

Only the configured estimator/controller governs numerical continuation. No turn
caps, forced child closure, scientific approval gates, unrequested retries, fixed
work timeouts, artificial yield smoothing or upward score clamps.

Global learning shares typed run statistics, not scientific findings or another
episode's yield history. Timing information earns monitoring credit under the
bound scheme and updates future duration expectations. Preserve original
expectation snapshots and closed credit histories.

The scientific three-slot mother retains its original annotation focus,
thought pattern and selected actual tool set. process.revise prepares a different
thought pattern and/or retrieved tool set for a
new child; the existing child action commissions that separate episode. Each
episode keeps its existing local credit and yield history. Explicit revision
provenance identifies which parent prepared the alternative. When higher steering
needs these results, the intervening parents request and forward the typed
scientific_process_results source. It copies existing per-episode quantities;
there is no referral score or new attribution formula. Scientific information
still receives credit through the existing projection of what the parent
actually receives. Exact interfaces and verification scope are in
[FIXED_PROCESS_BOUNDARIES.md](FIXED_PROCESS_BOUNDARIES.md).

## Parent yielding with active descendants

A parent can close with pending-work handles in its requested form. Yielding
does not automatically cancel children. Later returns remain durable, without
rewriting the closed parent's observations. An active ancestor can commission
monitoring or follow-up using returned handles.

Root yielding with outstanding work is termination with pending work, not
successful completion. No implicit supervisor resumes scientific decisions.
Further work requires an explicit caller/user decision. This accepted starting
treatment can be adjusted from observed behavior and user direction.

## Durability and resources

Persist commissions, handles, forms, waits, returns and observation order.
Recovery uses existing execution identities and pending decisions; it does not
resubmit because a parent process restarted. Archive closed history and release
it from active memory, retaining durable references and still-needed live state.
Do not recursively retain closed trees or load archives for status.

Parents receive outstanding-work and resource-commitment information alongside
duration expectations. They choose what additional work is worthwhile. Retrieve
software/resource knowledge as needed. Keep selected local limits at 20 GiB RAM
and 4 GiB scratch, with no wall-time budget. Do not invent concurrency quotas or
an autonomous scientific scheduler. External/API and HPC bindings must identify
actual availability/authentication; unverified deployments are not claimed.

## Implementation boundary and verification

At acceptance, Workflow remains annotation → recursive improvement plus flat
job_launch/job_monitor/job_results. Existing child execution blocks its immediate
parent. The detached adapter supports configured local phmmer. The retrievable
instruction library is implemented, but execution-tool schemas still enumerate
enabled tools. See TOOL_KNOWLEDGE.md.

Build the independent-execution/return foundation in shared method_loop, then
connect yield-informed waiting, recursive monitoring, resource launch and
literature specialization. This is implementation ordering, not an episode
itinerary. Trace ownership, selected work, durable state, communication, credit,
controller observations and closure across each changed path.

Verify independent parent/child decisions, controlled typed returns, one
observation per actual completed action, selected zero-gain waits, pending-aware
estimates, recursive monitor forms, recovery, surviving descendants, unchanged
closed histories and archive release. Then demonstrate configured-model work on
the fixed one-gene annotation question with useful scientific evidence. Scripted
fixtures and operational success alone do not prove the goal. Preserve the
original investigation_009 code pin and state.

### First implementation increment

Shared method_loop now provides ChildEpisodeUnit.start_async and independent
child contexts with immutable ownership metadata. Parent and sibling nesting
stacks are separate; children still run the ordinary Episode loop and their
own configured controllers. Independent delivery shares the existing async
closed-result projection/admission path. Parent closure and cancelled readiness
waits do not cancel child tasks. Where an archive is supplied, completed child
trace and result are held through disk references before parent collection.

Seven focused engineering tests establish independent parent/two-child work,
controlled typed returns, survival of a parent yielding, no retrospective parent
observations, closed-source release, cancellation-safe readiness waiting and
rejection of a mismatched owner or unrestricted report, and nested independent
execution with immediate-parent-only collection. They also verify that pending
child delivery callbacks do not retain a yielded parent's source/history.
Synthetic work and
controllers are used; these are not configured-model or scientific claims.

This primitive uses tasks within one live Python event loop. It is not yet wired
into the scientific Workflow's commissioning decisions and does not survive
process/event-loop exit. Durable independent processes, the completion inbox,
wait action/estimator integration, recursive monitoring and specialized branches
remain implementation work. A readiness await alone is not the designed
episode-selected, estimated and journaled wait action.

### Contract-scoped implementation checkpoint

The development contracts and workload boundaries are in IMPLEMENTATION_PLAN.md.
Shared method_loop now also has pending dispatch, closed-child collection,
restored ownership contexts and a durable subprocess/inbox/event binding. The
application has separate commission-intent, admission, completion-order,
reconstruction, specialist-composition and wait-input modules. Literature,
recursive monitoring and resource launch/results have specialized bindings using
the same Episode loop. Focused checks include real detached fixture processes,
typed recursive monitor returns and actual tiny local homology execution; model
choices and credit units in these fixtures are scripted.

At that module checkpoint the assembled detached scientific path was not
established: Workflow's selected child path still acquired TimedChildUnit
synchronously. The frozen commission/completion modules needed source/return integration, including
replay and controller stop ordering. Wait support reaches decision and
completed-action context, but a default pending-aware numerical model is not
implemented by merely supplying those inputs. Configured-model scientific
demonstration and actual API/HPC deployment remain unverified. The goal stays
active.

### Detached application integration checkpoint

The common Workflow now commissions selected children through frozen durable
intents and DeferredUnit, admits original closed typed returns transactionally,
and replays ordered completion slots through the same method_loop controller.
Explicit caller reconstruction and new known configured roots use this path;
saved markerless legacy runs retain their original semantics. New worker hosts
receive their semantic handle separately from their episode identity. Requested
pending handles are available as controlled closing facts, and root summaries
distinguish yielding with pending work.

Four real subprocess consumer cases establish parent work while a child is live,
selected wait followed by original return/follow-up, surviving descendants with
unchanged closed history, restart identity/order and stopping after a wait before
return admission. Two further subprocess cases establish failure/feedback recovery
without an observation and acknowledgment recovery when replay immediately
stops. Source-state metadata points to existing records; it duplicates no action
history or scientific state. Configured-entrypoint checks verify saved binding
publication and capability rejection before transport; they perform no inference.

These engineering checks do not establish meaningful pending-aware numerical
estimation, the complete detached specialist/job-progress assembly or a new
configured-model scientific investigation. The default rank estimator still does
not use its supplied pending context. C9 resource byte identities and C1 semantic
record identities now use separate pins through their conversion boundary; 23
focused checks include actual Workflow intent production without dispatch. The full goal and
investigation_009's preserved pin/state remain unchanged.

### Native monitoring and caller reconstruction checkpoint

Physical homology jobs now have a distinct JobStatusV1 progress representation,
including original native states, measured service-wall duration, output
availability/writer closure, and retained selected log windows with source
custody. A selected observation replays its original saved snapshot. A worker
exposes only its actual assigned job relationship; episode and native lifecycle
states remain distinct.

Caller-owned specialist setup now reaches root and fixed-case child hosts
through one saved factory/definition contract. Actual descriptors, role credit
definitions and the native progress-provider configuration are compared before
transport. New runs receive own progress outcomes and typed forms in one durable
first-receipt order; saved runs lacking that mode keep their original selection.
Monitoring credit is an explicit component using only the supplied received
facts and baseline, with caller-selected units and no automatic installation.

A real engineering consumer ran three durable workers plus one tiny native
phmmer job. A monitor commissioned a deeper monitor for an exposed assigned job,
received its original typed form, and returned while the target episode stayed
live. Tests check repeated-fact zero gain, original completion observations,
log/time custody, surviving descendants and unchanged closed histories. The
providers and controllers were scripted fixtures. This does not establish
configured-model science, a numerical pending/wait model, production operational
credit, native-job event notification, or API/HPC deployment. The remaining
contracts and exact coding ownership are in NEXT_PARALLEL_BATCH.md.
