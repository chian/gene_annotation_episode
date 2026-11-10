# Minimal information for parent steering

Status: proposed plan, 2026-11-04. This document specifies the information
contract; it does not implement it or change an existing workflow.

The parent needs to choose its next action. Detailed diagnosis belongs with the
episode handling the failing operation; the durable archive retains the full
record. Escalation should transmit the facts that change the parent's decision.

User clarification, 2026-11-05: episodes iterate by credit yield, with a yield
estimator for each action. An open information record is metadata, not an
independent reason to continue or wait. This plan must not introduce a
recipient-based continuation gate, a task-complete stop action, or another
completion policy. Diagnose repeated unproductive waiting through its recorded
marginal credit, action-specific estimate, presentation and action selection.
Information routing remains relevant context, but it does not replace those
mechanisms. Earlier suggestions to add separate waiting/completion gates are
withdrawn.

## Recommended design in brief

Use one current decision brief per child assignment, backed by durable records.
The default brief contains only the changed outcome or blocker, its consequence
for the assigned deliverable, relevant execution or retained-result status, and
the actual available next operations. Give it a scoped detail handle. The
parent chooses the operation; the brief supplies the facts needed to choose.

Select each fact with this question: could omitting it change which next action
is valid, what work would be duplicated, or how a returned result can be used?
If yes, include it. Otherwise retain it behind the detail lookup. Apply the same
rule to successful returns, partial results, failures, and standing tool
instructions. Do not truncate away a necessary uncertainty to make a brief fit
an arbitrary length.

An update is warranted when the child supplies a usable requested result,
cannot proceed without a parent-controlled decision, terminates, or changes a
previously reported fact that affects the parent's choice. A recoverable local
error stays with the child. Where the parent needs to track active assignments,
show their handle and current status without adding the child's progress log.

For a successful return, the brief gives the requested value or finding, its
question and scope, and a limitation only if it affects its use. For a failure,
it gives the observed cause, consequence, and whether execution and result
availability are known. Details such as raw source text, traceback, full record
inventory, and earlier attempts remain accessible through a requested section.

Build the contract and cause capture first, then durable delivery and scoped
lookup, then the actual model rendering. Validate the delivered information and
the parent's resulting decisions in full workflows. The existing continuation
policy and pending-child lifecycle require their own explicit resolution;
message design alone cannot deliver to a parent that has already closed.

## Observed gap

`independent_execution.open_commission` wraps an unclassified exception as
`execution_failed` and preserves a flat list of partial record references.
`method_loop.durable_worker` archives the exception. The parent renderer's
`_feedback` deliberately removes the private host diagnostic address.

There is also a transport issue. `decision_context.py` already defines versioned
bootstrap/update frames, but `providers._presentation` reconstructs the current
state and sends a complete text rendering for text-rendered roles. Its
`TEXT_INSTRUCTIONS` explicitly describe complete information on each request.
Those requests use a continuing model conversation. Replacing a record in host
state does not remove earlier messages from that conversation. Context economy
must therefore be verified at the actual provider boundary, including fixed
instructions, repeated text, and requested detail replies.

## Default parent report

Maintain one current, versioned report for the affected child/task. Its visible
content answers five questions:

| Parent question | Information supplied |
| --- | --- |
| Which work needs attention? | Existing child/task handle, lifecycle state, and failing stage. Reuse the assigned question reference. |
| What happened? | Specific observed failure code and one factual explanation, including whether local recovery failed. Mark an unknown cause explicitly. |
| What executed and survived? | Whether the attempted action executed or its effect is unknown; any still-live attempt; the relevant saved checkpoint/result and its availability. Distinguish saved work from an admitted typed return. |
| Which next actions are possible? | Applicable operations from the parent's actual catalog, with prerequisites or missing inputs only where they affect the choice. The parent selects the action. |
| Where can necessary detail be obtained? | An opaque, scoped operational handle and an executable detail-query operand. |

Fields are conditional on decision relevance, rather than an expanding list of
empty fields. A recorded retry outcome or recurrence count is useful when it
changes the recovery choice; it does not impose a retry or usage budget.

Lead with the unresolved parent decision: for example, "recover unfinished
analysis," "resolve a return-contract mismatch," or "supply a missing input."
This labels the decision the facts require; it does not choose the recovery
action for the parent. If the cause is unknown, show what is known and the
available diagnostic lookup rather than guessing a remedy.

Keep the report identity, revision and observation provenance in the structured
transport. All visible state must describe the same attempt and committed
observation; do not combine one attempt's failure with another attempt's saved
return. Capability eligibility must be checked again at action dispatch. A
changed prerequisite produces refreshed feedback, not an action based on stale
status. Question identity and scientific revision lineage remain separate from
these operational report revisions.

Use the same report for successful completion, partial completion and failure.
For an admitted result, show the requested result, its question/scope, and any
limitation that changes its use. Reference the existing typed return rather than
copying it into a second evidence representation. If nothing requires a parent
decision, ordinary child progress does not create another parent message.

For a running child awaiting a parent-controlled decision, the brief also states
what remains active and which work actually depends on that decision. Distinguish
an optional request for stronger evidence from a dependency that prevents the
assigned deliverable. An available operation is not itself a request to execute
it. Show a required parent decision only when the durable state establishes one.

## Separate states that lead to different decisions

Keep execution, saved work, and parent admission as separate recorded facts.
Do not collapse them into a single success/failure flag.

| Recorded situation | Information needed for steering |
| --- | --- |
| Child continues after a local error | Current assignment remains active. Escalate only a dependency or decision outside the child's control. |
| Child terminated before returning | Observed cause, execution effect, surviving jobs, and relevant committed work. A saved publication alone does not enable `redeliver_report`. |
| Child completed but delivery failed | Saved return availability, rejected field/reason, and an executable delivery handle. Reuse saved facts through the existing redelivery operation when its prerequisites hold. |
| Child completed with missing requested evidence | Which requested component is missing and why: unexamined, unavailable, unresolved, or measured absence. An empty return is not proof that no useful records exist. |
| Action effect or job liveness is uncertain | Explicit uncertainty and an available status/reconciliation lookup. Do not advertise a rerun as safe on the basis of missing acknowledgment. |
| Requested result was admitted | The result and decision-relevant scope/limitations, linked to its authoritative typed return. |

Available operations describe capabilities, not a recovery policy. The host
supplies verified prerequisites and missing inputs; the episode chooses among
the operations it actually has. No new retry, resume, cancellation or resource
allocation capability is implied by the report.

A valid unresolved scientific result can be a completed deliverable. Missing
context should be a result limitation, with any optional information need marked
as such, when the assigned contract permits that answer. Do not turn every
missing value into a blocked child or a mandatory demand on the parent.

An open information need must not imply an incoming response. For a decision that
depends on another actor, expose the actual recipient's existence, whether work
has been assigned, and an actual event handle when there is one. Keep missing
caller input, an unassigned request and active response-producing work distinct.
This is truthful capability/status presentation, not a new stopping rule or an
automatic commission.

## Information stays at the level that can act on it

1. **Local feedback:** give the child the precise operation error, relevant
   argument/receipt requirements, and execution-effect status. Ordinary
   recoverable tool errors stay local while the child continues its assignment.
2. **Parent escalation:** publish the compact report when the child terminates,
   needs a parent-controlled input/capability decision, or has a result/contract
   state requiring parent action. A running child with a local error remains
   distinguishable from a terminal child. Resource or environment facts appear
   only when necessary to steer; the report grants no extra resources.
3. **Details on request:** extend the existing `request_context` mechanism with a
   scoped operational view. The parent selects cause, attempted recovery,
   retained-work inventory, or a diagnostic excerpt. This is a proposed reader,
   not an assertion that the current catalog already exposes diagnostics.

The opaque handle resolves through the runtime's ownership and visibility rules;
private filesystem paths stay private. Diagnostic text is operational data,
separate from scientific evidence and scientific credit. The detail response is
limited to the requested subject and section, with explicit continuations when
needed. Reading details does not execute or retry work.

Apply this rule at every parent/child boundary. A specialist handles its own
subtree's errors and escalates only the effect on its assigned deliverable plus
the decision needed from its immediate parent. The root receives an axis-level
consequence when it must act, with a drill-down handle; it does not receive each
descendant's incident report. An external blocker includes the missing input or
capability and which boundary can supply it, when known.

Commit an escalation before exposing its notification through the parent's
wait/decision path. A waiting parent must be able to receive a child failure or
request for a parent-controlled dependency without waiting for a successful
return. Record which report revision was delivered; repeated notifications of
that revision do not append repeated content. Restoration recovers undelivered
current issues from durable state. The new report channel emits no notification
for routine child progress. Existing wait-event selection and its effect on
continuation remain a separate policy boundary; filtering report notifications
must not silently change those observations or introduce a new stopping rule.

## Keep context proportional to the decision

- Replace a child's earlier report with its current revision in the rendered
  state. Keep the current issue available until its disposition is resolved.
- Coalesce repeated occurrences into the same issue with changed facts and,
  where relevant, a recurrence count. Preserve all occurrences in the archive.
- Show semantically labeled recovery checkpoints, not every created record ID.
  Retain the complete inventory behind the detail handle. Independent failures
  requiring different decisions remain distinguishable.
- Include a failure explanation once, even if it appears in both feedback and
  the last-action outcome. Do not append old diagnostic excerpts to every prompt.
- Update the current report when decision-relevant facts change. Repeated
  unchanged observations do not become new prompt content. Show resolution once
  it is evidenced, then retain only any consequence still relevant to the task.
  On conversation restoration, reconstruct current issues and usable results
  from durable state; do not replay every earlier incident into the prompt.
- Show the parent's own operations and each available child's purpose, required
  inputs, relevant return contract and operational availability. Retrieve detailed
  child-operation catalogs and other return schemas when a decision needs them;
  do not preload every specialist's low-level population instructions into the
  parent. Preserve executable lookup operands and honest capability boundaries.
- Keep full source bodies, schemas, tracebacks and chronological attempt logs
  outside the default report. Existing scientific return contracts remain the
  authoritative route for evidence and numerical cells.

The small report must preserve uncertainty about effects and liveness. An unknown
action outcome must never become “safe to rerun”; a live job must not be mistaken
for absent work. Missing diagnostic detail must not become a negative biological
finding. No new stopping rule, timeout, automatic fallback or score policy is
introduced by this information contract.

## Implementation boundaries

### Delivery into the model conversation

Use the existing decision-frame mechanism instead of creating a second history:

1. At bootstrap, supply the assignment, the parent's own action interface,
   relevant child summaries, and current unresolved steering reports.
2. On update, render only changed reports and other changed decision fields,
   with explicit replacements or removals. Do not expand an update back into
   the complete task, child catalog, or prior report inventory. Keep rendering
   instructions consistent with those replacement semantics.
3. For a lookup, return only the requested section. Keep the full reply in the
   durable exchange record; carry forward its relevant consequence and handle
   when rebuilding current state, rather than replaying diagnostic excerpts.
   Preserve outstanding requests and the fact that a lookup was answered.
4. After conversation loss or existing provider compaction, reconstruct the
   compact current snapshot from durable records. Include unresolved decisions,
   valid result references and established task constraints. Explicitly retire
   superseded operational reports without discarding scientific uncertainty.

Earlier messages remain historical until the provider compacts or replaces its
conversation. Do not claim that a host-side replacement has physically removed
them. Inspect both supplied messages and available compaction records. This
plan changes information selection and presentation; it introduces no periodic
restart, context-size stopping threshold or workflow termination policy.

Detailed specialist instructions belong behind the scoped lookup from the
first parent bootstrap. The current provider fixes developer instructions for
each conversation, so changing the renderer alone cannot remove catalogs that
were embedded in those instructions. Apply the new instruction construction to
new conversations; preserve the identity and record of existing runs.

Proposed short parent guidance:

> Use each child's current report to decide what work is needed next. Match any
> saved result to the assigned question and its admission state. Choose among
> the supplied operations using their stated prerequisites. Request operational
> detail when a missing fact changes that choice. A newer report replaces the
> older state for that child; diagnostic information does not supply scientific
> evidence or authorize additional compute resources.

### Code ownership

| Existing location | Planned responsibility |
| --- | --- |
| Failure-producing adapters and `providers.py` | Capture a known cause and whether the attempted action executed, without inferring facts from a generic exception. |
| `independent_execution.py`, `method_loop/durable_worker.py`, `method_loop/durable.py` | Preserve cause, lifecycle and committed-work references across process boundaries. Version any changed durable contract and retain readable historical records. |
| `runtime.py` and the existing composition/context lookup interface | Assemble the current operational report; enforce visibility; expose section-specific detail queries and valid operation operands. |
| `decision_context.py`, `composition_information.py`, `providers.py` | Preserve versioned update semantics through text rendering and scoped lookup replies; reconstruct compact state after restoration; keep detailed specialist catalogs out of fixed parent instructions. |
| `scientific_process_prompt.py` and applicable role renderers | Present each current report once; keep specialist manuals and detailed inventories available on demand. Inspect actual provider inputs, not just the intermediate state. |
| Existing typed return and admission paths | Remain authoritative for scientific evidence, numerical possession and report redelivery. An operational report cannot bypass them. |

Checkpoint selection follows the assigned question, explicit revision lineage,
record type and availability. Recency alone does not establish relevance or
scientific superiority. If competing scopes or publications cannot be reconciled
from those facts, show that ambiguity and provide the corresponding handles;
the presentation layer must not invent the missing interpretation.

## Build sequence

1. **Capture and transport:** introduce a versioned operational status record.
   Capture known causes where they occur, preserve them through the durable
   wrapper, and retain the existing diagnostic archive. Use explicit adapters
   for known failures and honest unknowns for unclassified ones; no additional
   LLM call is needed to invent a cause or summarize a traceback.
2. **Recovery inventory:** derive current usable checkpoints from committed
   records, publication revisions and receipt state. Preserve the original
   question, valid reference access, action effects and live execution identity.
   Keep the large inventory durable and expose only relevant checkpoint handles
   by default. Preserve current custody and typed-return admission boundaries.
3. **Scoped lookup and rendering:** add the operational detail view to the
   existing context-request interface; render the compact report once in the
   actual parent prompt and send subsequent changes as updates. Adjust fixed
   instructions and text-frame rendering together. Retain the distinction
   between recovering an unfinished investigation and `redeliver_report` for a completed child whose
   saved return can be represented again.
4. **Full-workflow validation:** observe actual failures and parent decisions in
   complete workflows, one at a time. Inspect the delivered prompt, selected
   recovery action, its prerequisites, and the final return. Do not substitute
   targeted checks, scripted parent choices or evaluator hints.

Implement the shared information contract and delivery path once, then supply
role-specific views from existing result contracts. Extend the same mechanism to
scientific axes and compute children; their brief may need a live job handle or resource fact
where the literature brief does not. Keep those differences in the producing
adapter, rather than adding every role's fields to every parent's prompt.

## Completion condition

From the default report, the parent can identify the affected assignment,
understand the observed failure and its uncertainty, distinguish executed/live
work from unexecuted work, locate a relevant preserved result, and select a valid
next action. It requests detail only when that decision needs it.

Full traces must demonstrate this for model-response failure, unavailable
input/receipt, tool or service failure with partial work, and completed-child
return-delivery failure, as well as successful admitted results. The displayed
facts must agree with durable state and the actual action effects. Repeated
failures must not accumulate raw logs or
record inventories in the default context, and no recovery summary may bypass
scientific fact admission. Record operationally successful steering separately
from eventual biological correctness and successful numerical delivery.

Evaluate context economy against the actual delivered prompt: one current report
per relevant child, no duplicated feedback, no growing attempt inventory, and
no specialist catalog included without a current need. Compare the decisions
the parent could justify with the compact report and with the full retained
record. A missing fact that changes the valid next action is a failed design;
extra detail that cannot affect that decision belongs behind the lookup.
Measure prompt size as an observation, not as a new token or stopping budget.
Include unchanged updates, a resolved failure, a stale action prerequisite, and
conversation restoration in the trace audit. An unchanged report must not be
resent; resolved issues must not reappear as current failures; an obsolete
prerequisite must not authorize work; restoration must retain the information
needed for the same next decision. Track fixed-instruction size, newly supplied
text and repeated report content separately, because a small new message alone
does not establish a small accumulated model context.

The completed system must let the parent distinguish “continue live work,”
“recover from saved work,” “repair delivery,” and “obtain missing information”
from the supplied facts and available operations. These are validation outcomes,
not scripted model choices or additional runtime actions.
