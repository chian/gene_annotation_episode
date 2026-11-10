# Runtime binding and current evidence

This reference describes runtime interfaces, typed reports, state custody and
recovery.

The replacement runtime composes the vendored `method_loop.Episode`,
`ChildEpisodeUnit`, `EpisodeTree` and `Grain`. The root annotation investigation
can select ordinary work, commit scientific reasoning based on existing evidence,
or commission a scoped iterative improvement. Improvement Episodes can commission
narrower improvements. There are no biological departments, compulsory stages,
branch quotas, model stop actions or application action limits.

`run_workflow(store, tools, *, provider=None, provider_config=None,
run_dir=None, resume=False, controller_settings=None, credit_policy=None,
controller_factory=None, project_credit=None, goal=None,
restoration_settings=None)` is asynchronous.
Production defaults use `providers.ModelConnection`, received-finding scientific
investigation progress, a separate `AnnotationSupportScore`, and
`numerical.YieldController`. `default_scientific_binding.bind_default_science`
assembles these settings before the one shared runtime executes the episode.
Configuration comes from packaged `defaults.toml`, with explicit caller
overrides selected before the run. The effective models, controller settings,
score definitions, immutable input and goal are recorded once. A resumed run
restores its original settings and initial known references; it cannot silently
substitute today's defaults. Custom injected numerical bindings are intended
for tests or callers retaining the same executable; their qualified names are
recorded, but arbitrary closure behavior cannot be proven unchanged.

`[scientific_progress]` configures `finding_unit`, `loss_preview_size`, and
`initial_known_record_refs`. The default unit of one is a provisional information
unit, not a calibrated biological value. Only distinct current retained typed
findings actually received by the episode contribute. Unchanged polling, raw
records and tool activity do not earn scientific progress. Callers declare any
existing information the episode should initially know; the default set is empty.
`[credit]` and the existing `credit_policy` API argument configure the separate
annotation-support hypervolume. Its scalar and evidence vector appear as
`annotation_score` and `annotation_evidence_vector`; they do not drive scientific
continuation. Explicit `project_credit` callers retain their selected scoring
binding, as do the pinned historical case runs. Resuming an older default run
requires its original implementation/binding rather than retroactively changing
its score meaning.

The effective caller-owned `[restoration].preview_size` is also persisted.
It controls the bounded metadata preview for a fresh provider conversation,
not scientific work, acceptance or continuation.

The default model choices are REASONING `gpt-6-sol`, medium effort, and FAST
`gpt-6-luna`, no reasoning. This binding uses REASONING for its scientific work;
there is no FAST report composer. The transport disables native model tools and
checks the actual server model and effort. Fixture tests below establish their
exercised engineering paths, not model scientific judgment.

## Action, communication and credit boundaries

Each existing reasoning response selects one action and supplies `report_update`
for the parent's requested interpretation fields. Report formatting is not an
acquisition. The same response can commit hypotheses, source-anchored extraction,
assessments and annotation revisions. The Store owns exact semantic validation,
alias resolution and partial-row preservation. The runtime validates the action
envelope separately so an independent valid row is not discarded because another
row is malformed. A completely empty reasoning request is feedback, not work.

Assessments explicitly select observed or inferred extent. Missing inferred target
footprint retains the scientific row and returns an informational notice through
the existing `last_local_outcome`; it does not reject the action or create a second
observation. The current projection exposes the same inactive assessment/field.
A direct/inferred contradiction is representation feedback for that row, preserving
independent valid contributions. See [STATE_API.md](STATE_API.md).

A completed or partially completed ordinary action creates one local controller
observation, including genuine zero gain. Failed, unavailable or invalid work
returns actionable feedback without inventing an action observation. Completed
child investigation is one parent action; nested operations do not become extra
parent turns. Credit is always projected from the same committed scientific
state, with actual signed changes. Refreshing a live shared score does not call
the parent's controller.

The ordinary `episode.credit` read exposes explicitly paged current source
operands and inactive dependencies through the same run-frozen policy and
scope as the Episode's scalar/vector projection. It changes no scientific
state and follows existing one-action accounting. Custom projectors must
declare detail support; no default scorer is substituted. Its exact interface,
state-basis meaning and limits are in [EPISODE_CREDIT.md](EPISODE_CREDIT.md).

The parent supplies `schema_json`, field meanings, purpose and an explicit initial
interpretation form when commissioning a child. The child receives that actual
purpose, requested form, latest admitted interpretation values and their recorded
basis. It also sees the current evidence vector from the same projection as its
scalar credit; the binding describes this as a progress proxy, not biological truth. The restricted recursive guard
prevents unrestricted strings/objects and checks actual semantic reference
membership. The Store owns scientific scope and original-coordinate containment.
Fact fields bind through registered top-level `x-source` selectors. Their declared
types must match the available recorded values before child work starts.
The optional `changed_annotation_refs` and `changed_assessment_refs` selectors
filter committed changes by actual semantic record type, so a parent can request
those revisions without receiving a mixed list or asking a model to invent the
new content-derived identifiers before publication.

The commissioning schema includes two optional examples: a fact-only form and
an interpretive form. The latter lets the child select actual assessment refs
and unresolved hypothesis refs, alongside recorded annotation changes and basis
facts. Assessment records retain the particular hypothesis, observation,
condition, assumption and evidence relation; no findings paragraph is introduced.
Both examples compile through the same closed-form guard. The parent still
chooses its contract, field meanings and explicit initial values. The examples
install no fields, scientific decision, required child or continuation rule.

No closure model call is made. The final form combines the last actual admitted
interpretation with requested recorded facts. A later tool result is not
presented as a new reasoning judgment. Optional fact selector
`observations_after_report_basis` means observations returned after the last
report interpretation's visible basis; it does **not** claim they lack an
assessment. A single reasoning commitment may itself extract and assess a new
observation. Parent contracts can request actual assessment/annotation references
and the basis facts needed to distinguish these cases.

Malformed model report updates preserve the prior admitted interpretation and
valid scientific action. They return representation feedback to the same
responsible Episode. They do not reject science or change its credit.

Schema-invalid action feedback identifies constraint paths and expected operands
without rendering the full catalog or model payload. Admission still uses the
original host schema. The exact proposal and contract remain journaled, and
existing specialized parameter diagnostics remain available.

## State, archives and recovery

Scientific records and runtime journals occupy the same SQLite Store, with
separate tables for assignments, selected actions, model calls, observations and
forms. Scientific work has a stable operation key. On interruption, reconstruction
reuses saved decisions and historical cumulative scores; committed tools or
reasoning publications are idempotently recovered if publication preceded their
runtime response journal. Saved controller observations cannot be counted twice.
An already yielded run returns its historical summary rather than rewriting it
from later changes in the Store. Yielding does not establish task completion.

Closed child traces are archived on disk using the shared archive implementation.
Controllers are removed at scope closure, provider processes/conversations are
retired, and the active parent keeps admitted forms rather than live descendant
trees. Interruption retires suspended parent providers too. Pending scientific
state and references remain durable. Selected query pages are passed through
exactly; this layer does not silently clip them.

A fresh provider conversation receives a bounded SQL-projected index of its own
prior decisions rather than every old full context and response. The ordinary
`episode.history` tool can read exact prior selections, saved outcomes and actual
admitted direct-child forms. It cannot read child-private decisions, old full
model contexts or native private reasoning. Automatic restoration adds no action
or observation. An explicitly selected successful history read is one ordinary
action, and an old failed outcome inside it retains that failure. The exact
actual provider input is journaled before dispatch. See
[BOUNDED_RESTORATION.md](BOUNDED_RESTORATION.md) for configuration, evidence and
limits; other current-input growth remains separate work.

The `decision_exchange_v1` protocol keeps exact `episode.history` outcome and
publication reads as ordinary actions. Its pending `request_context` lookups
cover metadata and selected inputs, with no completed-action observation.
They cannot retrieve the outcome through an input pointer. Exact recall never
executes a historical action or adds its historical credit again.

## Report-delivery recovery and verification

Automated tests use explicitly scripted providers and synthetic continuation
controllers; they do not establish model scientific reasoning quality. They
exercise recursive iteration, child-to-parent forms and subsequent decisions,
reasoning gains without another measurement, signed corrections, malformed-form
preservation, exact pages, failed-work accounting, scoped references, strict JSON,
configuration and interruption recovery. Separate integration tests use the actual
Store, local sequence-inspection adapter and credit projector, with scripted
reasoning. They verify existing-evidence interpretation commits and preservation
of independent valid rows; they do not claim a new biological discovery.

The previously reproduced defect was a parent requesting `last_outcome_refs`
with `maxItems: 0`: real child science finished, but its references could not fit
that form. The shared kernel now represents this as a completed child with typed
operational delivery failure. It preserves the child trace and independent credit,
admits no invalid scientific form, and contributes one parent observation.

The responsible parent receives `report_delivery_failure`, an opaque delivery
reference and a constrained reason/field. It can select `redeliver_report` with a
revised closed contract. The shared `Episode` loop processes `ReportRedelivery`
as communication repair, without acquiring work or advancing a controller.
The event updates the corresponding child edge's admitted report, retains prior
delivery failures, and records the revised contract. The child goal, scope,
science, original credit observation and history remain unchanged.

Redelivery projects the saved completion-time facts and the child's last actual
interpretation. It accepts no replacement interpretation values from the parent.
Reused interpretation fields must preserve their original declared meanings and
types. A requested interpretation that the completed work did not provide returns
`recorded_interpretation_unavailable`; another report composer does not invent it.
New scientific interpretation can instead be investigated in a subsequent owned
improvement using the available evidence. No fallback scientific fields or
deterministic clipping is used.

Saved delivery attempts and selected correction responses replay during recovery.
Tests interrupt both before and after correction, then verify the same science,
child trace, report and controller observation counts. Another test follows actual
parent feedback through an unavailable revised meaning, a compatible correction,
the admitted result and the parent's next scientific action. The synchronous
generic kernel path and the asynchronous runtime path are both exercised.

Numerical continuation remains authoritative. If the parent numerically yields
while delivery is still pending, the run reports `pending_report_deliveries`
explicitly. It does not call another model to bypass that stop or claim successful
delivery. Pure async scientific-tool protocols can be awaited through
`tools.execute_async`; synchronous local tools retain their existing path and
SQLite publication remains on its owning thread.

Recovery uses the full shared `run`/`run_async` parent trace. The generic
experimental single-unit stepping interface does not retain that prior trace and
explicitly cannot apply redelivery. The application entrypoint does not use it.
Frame-level `ReconstructionCursor` needs no special parser for form internals;
its opaque saved payload comparison remains unchanged. The application journals
and reconstructs the original selected communication events with the shared loop.
