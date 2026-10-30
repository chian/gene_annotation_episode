# Fixed scientific processes, revision provenance and existing yields

The user's latest direction is settled: retain existing per-episode credit and
local yield histories, and record where episodes came from so their parents can
steer. Do not introduce referral scores, original-approach exclusion scores,
normalized productivity or another attribution policy. A revised P/T belongs to
a different episode. `process.revise` prepares that selection; the existing
`episode_child` action launches it with its own job, scope and original form.
Ordinary action choices remain iterative within an episode's fixed A/P/T.

The user distinguished alternative-approach children from ordinary task parts.
A higher parent needs to see the actual relationship and recorded results rather
than receive an undifferentiated aggregate. Typed forms remain the only upward
communication boundary. Nothing here changes scientific projections, numeric
estimators, local costs, observations or the continuation rule.

Two initial coding assignments were interrupted when the user clarified this
communication requirement. Two fresh read-only investigations then traced the
actual commission, source-fact, admission, receipt and controller consumers.
The revised contract below preceded fresh, exclusive coding assignments.
FP0–FP7 now has the bounded engineering evidence recorded in
[fixed_process_verification.json](fixed_process_verification.json), including
nested original forms, separate local histories, authenticated revision-child
restoration and an actual scripted-provider worker. CE0–CE3 remains separately
verified at its historical checkpoint. No configured-model scientific behavior
is established by this correction.

## Original request and preparation records

Option refs, selections and filled-process records keep their existing exact
wire shapes. Keep the old validate_revision parser solely for historical record
inspection. The new binding is scientific_process_episodes_v2; its implementation
pin covers the mother, setup, records, reports and provenance modules. Existing
full-descriptor/code comparisons reject v1 reconstruction under changed code.
Old histories and snapshots are not migrated, reset or repriced.

Every new scientific-profile annotation/scientific_process request gains the
semantic message.scientific_invocation_ref. The pure record helper

    scientific_invocation_ref(run_id, path) -> str

uses the validated stable run and logical path, returning
scientific_invocation_<24 lowercase hex> via the existing domain identity
encoding. It identifies an invocation for both blocking and detached work; it
is not an execution handle. The build path computes it before publication and
preserves it in the exact original request. The worker reconstructs the same
value; original-request equality remains mandatory. Markerless non-library
profiles do not gain this field. Parent forms never expose raw episode/goal IDs.

ScientificAssignment keeps selection/evidence_refs/constraints/context and gains
one OPTIONAL field. Omission leaves ordinary assignments unchanged:

    revision_origin = {
      version: scientific_process_revision_origin_v1,
      parent_invocation_ref: scientific_invocation_<24 hex>,
      preparation_operation_ref: operation_<24 hex>
    }

Presence records a selected alternative approach, not merely different P/T.
Never infer this relationship from the most recent preparation or a P/T change.
The same preparation may support more than one explicitly selected commission.

process.revise keeps exact input {thought_ref, tool_ref}. Its completed ordinary
ToolOutcome has empty record_refs/changed_record_refs, the existing operation_ref,
and these two data fields:

    result = {
      version: scientific_process_child_selection_v1,
      parent_selection_sha256: sha256(original current A/P/T selection),
      selection: ScientificSelectionV1
    }
    revision_origin = ScientificRevisionOriginV1

revision_origin.preparation_operation_ref equals that operation_ref; its parent
reference is this actual invocation. Preserve original A/library, validate the
new P/T and expose caller tool availability without substitution. This operation
changes no current frame/controller/history and launches no child. The caller
copies result.selection and revision_origin into a later scientific child
assignment. Biological information is returned through the child's other fields.

Before filling a revision child's request, validate its origin against ONE actual
completed preparation owned by the commissioning episode. Check original tool,
arguments, operation key/identity, successful result, empty scientific refs,
original selection digest, A/library and exact proposed selection. Missing,
failed, foreign or mismatched preparations are explicit input errors. Revalidate
the same original relationship on worker/build restoration. No new ledger or C1
envelope field is needed: assignment_sha256 and the original request/C1 digest
already pin it.

## Exact host service ports

Remove Workflow.scientific_selection and its WorkflowServices/protocol forwarding;
that method only folded old in-place mutations. No active-selection service
replaces it. The mother resolves its original validated assignment directly.
Fresh scientific frames retain selection and initial_selection_sha256 and omit
revision/revision_decision_index.

New narrow ports, with detached finite JSON outputs:

    services.scientific_preparation(context, preparation_ref, *, owner="self")
      -> {
        operation_ref, owner_invocation_ref, owner_selection,
        arguments: {thought_ref, tool_ref},
        proposal: ScientificChildSelectionV1,
        revision_origin: ScientificRevisionOriginV1
      }

    services.scientific_received_results(context) -> [ScientificProcessResultV1]
    services.scientific_parent_invocation(context) -> invocation_ref | None
    services.scientific_reference(context, reference, namespace) -> bool

For preparation, owner is exactly self or parent. prepare_invocation uses self;
child validate_context uses parent. Authenticate context run/path/episode and its
original saved request wherever present; self requires a saved owner. A newly
built child can lack its own row, but its parent must exist and agree with its
original goal relationship and scope. Parent mode selects only the actual
immediate parent, not a supplied episode identity. It returns the one preparation
and its owning original selection, not a parent history/model context.

The producer is a new read-only ScientificProcessProvenance(store, journal,
*, library) in scientific_process_provenance.py, with matching methods
preparation, received_results, parent_invocation and resolve. resolve additionally
accepts credit_metadata=None for the current actual binding definition supplied
by the host; it must not project credit. Construction/reads create no tables,
write no records, poll no backend, read no archives or call models/controllers.
Use one read snapshot and project only required JSON positions in SQLite.

Namespaces: scientific_invocation, scientific_preparation,
scientific_process_library, scientific_option_digest, scientific_credit_binding.
Invocation/preparation visibility comes from the original request, actual own
preparations and admitted process-result fields; never grant arbitrary descendant
history access. Library/entry identities resolve against the pinned library.
Binding refs resolve against the actual caller metadata or already received rows.
Root Workflow.resolver and the mother's separate resolve/validate_report paths
must all honor these namespaces. Unknown values remain unavailable.

## One typed result source, no extra score

A new pure scientific_process_reports.py supplies:

    report_sources(library) -> {scientific_process_results: source definition}
    validate_process_result(value, *, library=None) -> detached dict
    build_process_result(context, completion_snapshot) -> dict | None
    merge_process_results(own_result, received_results) -> [dict]
    credit_binding_ref(metadata) -> semantic reference | None

The requested top-level source scientific_process_results is a closed array of:

    ScientificProcessResultV1 = {
      version: scientific_process_result_v1,
      invocation_ref: scientific_invocation reference,
      parent_invocation_ref: scientific_invocation reference | null,
      origin_kind: ordinary_child | approach_revision,
      preparation_operation_ref: scientific_preparation reference | null,
      selection: ScientificSelectionV1,
      initial_credit: finite number,
      credit: finite number,
      credit_kind: scientific | monitoring | operational | null,
      credit_binding_ref: scientific_credit_binding reference | null,
      completed_actions: nonnegative integer,
      episode_yield: existing closed episode_yield value | null
    }

ordinary_child means no explicit revision marker; it does not claim that every
unmarked job is scientifically a decomposition. For a revision row, the parent
and preparation match its original assignment. Both credit fields are COPIES:
initial_credit is the original runtime_episodes baseline; credit is the same
closing scalar already exposed by the existing credit fact. No new progress
delta, child-score addition, weight, exclusion, counterfactual or normalization.
Use the existing episode_yield schema/projection, including signed/unavailable
bands and custom-controller null. Binding metadata remains internal finite JSON;
its semantic reference is domain.identity(scientific_credit_binding, metadata).
Unknown kind/binding are both null, not invented units.

The source schema uses closed objects and enum codes, with semantic identifier
formats for library/entry digests and references for invocation/preparation/binding
handles. Raw pattern-based option schemas and unrestricted binding dictionaries
cannot enter forms. Per-slot option ID enums come from the actual pinned library.
Full-record validation also checks option namespace/body identity and meaningful
origin/binding relationships. No audit IDs appear in the row.

The host extends the existing specialist completion_snapshot with:

    initial_credit, credit, controller_credit, episode_yield,
    parent_invocation_ref

Existing completion/own_action_count fields remain. controller_credit is the
actual source_controller_credit metadata or None. Credit and episode_yield are
reused from the SAME existing closure projection, not recomputed for reporting.
Without actual completion, build_process_result returns None; it cannot invent a
closing result. No final-yield refit is allowed.

Mother.fact_sources exposes the new source. Mother.facts builds its own result
only at closure and merges rows actually received through successful original
child forms. Merge is stable with the own row first; identical invocation rows
deduplicate, conflicting bodies fail. Do not recursively inspect descendants.
The producer reads only fields whose original admitted contract declares this
x-source, from runtime_report_attempts; it ignores unrequested/private child facts,
failed attempts and unrelated field names. A form cannot forge this source from
unrestricted prose. Existing source-fact validation and frozen runtime_forms
remain authoritative on admission, redelivery and replay.

An ancestor receives a grandchild row only through intervening requested forms.
The revised-process instructions/preparation describe the source needed for this
steering communication; they do not append undeclared fields to an existing form.
The parent chooses its field name and scientific fields as before. Existing
redelivery can request frozen recorded facts when appropriate. Metadata references
are not Store scientific evidence; no new receipt credit or observation follows
from formatting/forwarding the result rows.

## Exclusive implementation workloads and handoffs

| Part | Exclusive files | Concrete output |
| --- | --- | --- |
| FP1 mother/records | scientific_process_episodes.py, scientific_process_records.py, tests/test_scientific_process_episodes.py | Fixed v2 A/P/T; optional authenticated origin and copyable preparation; semantic invocation helper/validators; new service/report consumers; no in-place mutation. |
| FP2 host | Coordinator: runtime.py, episode_services.py, episode_bindings.py; independent_execution.py only if traced restoration needs a forwarder | Remove old fold; construct original semantic refs; install read-only provenance ports; route reference validation; supply existing closure operands; preserve commission/admission/credit/controller semantics. |
| FP3 connected tests | tests/test_scientific_process_runtime.py, tests/test_scientific_process_reconstruction.py | Actual prepare -> separately selected revision child; stable original selections; nested requested records and distinct actual local yields, source-independent reconstruction, interruption/replay and v1 rejection. |
| FP4 detached tests | tests/scientific_process_worker_fixture.py, tests/test_scientific_process_detached.py | Real worker fixed process/preparation, exact origin/request/form, parent overlap/wait and one projected parent return observation, source deletion/archive/release. |
| FP5 record | Coordinator: plan/design/status/checklist and separate verification record | Precise current semantics/evidence; preserve historical catalog and SL/RI/CE verification bytes. |
| FP6 provenance producer | New scientific_process_provenance.py and tests/test_scientific_process_provenance.py | Read-only exact original preparation/relationship and received-result lookup; scoped semantic reference resolution. |
| FP7 typed results | New scientific_process_reports.py and tests/test_scientific_process_reports.py | Closed source schema, pure record validation/build/merge, copied existing baseline/credit/yield and pinned binding identity. |

Three fresh coding agents first own FP1, FP6 and FP7; the coordinator owns FP2.
Their input/output shapes above are fixed, so they code against fixtures in
parallel. FP3 and FP4 coding can follow as slots become available, not because
nested runtime episodes force serial development. Keep Scenario/prepared_child
helper APIs stable: schema/detached tests import them. Only connected execution
requires all implementations together. Freeze source bytes during real-worker
verification; no two owners edit one production or test file.

## Retained correction checklist

- [x] FP0: actual boundary trace and shared contracts before coding. The user-added
  provenance/steering amendment above supersedes the interrupted first contract.
- [x] FP1: v2 fixed mother, authenticated revision preparation and original origin.
- [x] FP2: host consumers and exact saved request/closure operands.
- [x] FP3: connected nested distinct histories, upward facts and reconstruction.
- [x] FP4: actual detached fixed-process/typed-return evidence.
- [x] FP5: current records and full retained checklist updated precisely.
- [x] FP6: read-only provenance producer and scoped relationship validation.
- [x] FP7: closed result facts copying existing per-episode quantities.

Tests must distinguish child local credit/forecast from its parent's actual
received delta, preserving one observation per completed own action. Preparation
creates no scientific contribution; a commission remains pending until returned.
Test ordinary children with changed P/T but no revision marker; foreign/failed/
forged proposals; repeated preparation use; received/unrequested/grandchild rows;
unknown binding; signed yields; forged body conflicts; failed/closed receivers;
exact saved replay and source-independent worker reconstruction. Numerical units,
bands and stops in engineering fixtures are not production policy adoption.

The full A–I/LIB/TIME/CREDIT/CASE/SCIENCE/VERIFY list is unchanged. Pending/wait
numerical models, physical native events, production composition, separate
literature-library work, configured-model science and complete verification
remain open. No competing scientific root runs in investigation_009's workspace.

## Verification checkpoint

The mother suite passed 39 cases. The provenance producer passed 33 cases in its
full-file run and two subsequently added edge cases separately. The pure result
suite passed 42 cases. The final connected/reconstruction group passed 29 cases,
including requested and unrequested lineage, metadata-only returns, ordinary
changed selections, interruption and v1/origin rejection. Root's adjacent
library/tool-context/schema/forecast group passed 108 cases; existing scientific
credit/yield regressions passed 17. These groups overlap other recorded runs and
are not summed. The initial metadata-only fixture failure and its correction are
retained in the verification record.

The actual worker test passed with different parent/worker processes, deleted
research source, original P01/T01 across three child decisions, a completed
preparation and the requested result row. Parent completion order remained
[1,2,0,3] with raw gains [1,0,1,0]; child gains remained [1,0,0]. Preparation
created no third episode. Archives and live-state retirement were verified. This
uses a scripted provider and custom fixture controller, whose existing closing
yield is null. The nested connected cases separately exercise actual
YieldController histories and copied signed closing bands; the production
factory reconstruction checks execute no episode or inference.
