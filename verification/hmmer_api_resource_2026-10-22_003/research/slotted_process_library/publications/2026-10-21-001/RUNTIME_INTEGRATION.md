# Runtime construction from the three slots

**Current correction (2026-10-21):** the active construction contract is one
pinned A option, one pinned P option, and `tools: [<actual callable name>, ...]` in
`scientific_process_selection_v2`. `process.tools({investigation})` retrieves
relevant names and their real catalog records from the complete caller-provided
tool map; the parent passes `result.tools` into the tools slot. `process.revise`
prepares a separately commissioned child with `{thought_ref, tools}`. There are
no complete episode entries or selected T bundles. This implementation is in
progress and is not verified by this documentation change. See the
[current source table and exact contract](CURRENT_SLOT_SOURCES.md).

Everything below is the retained earlier integration account, including its
single `tool_ref`, explicit T-operation mappings and historical test evidence.
Those interfaces are superseded; their passing tests do not validate the
current correction. Literature episode relationships are separate from this
bioinformatics mix-and-match construction change.

The curation task and its fixed L1–L6 checklist remain complete as recorded. The
initial implementation is recorded in [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md),
with retained SL1–SL5 items. The later fixed-process/provenance correction is
scoped and verified by [FP0–FP7](../../docs/FIXED_PROCESS_BOUNDARIES.md). The
library data remains the same 42 separately addressable entries and 208
option/source relationships. The [all-case register](CASE_COVERAGE.md) still
accounts for all 142 groups.

`ScientificProcessLibrary.freeze(run_directory / "scientific-process-library", source=source_directory)` creates an immutable run snapshot. It pins the source index, entry bodies and per-option provenance rows independently of the research manifest. It retains compact headers in memory; body/source retrieval reads selected files. Reopening uses that snapshot even if the original research directory has changed or disappeared. Reads and reconstruction detect snapshot drift.

`process.search`, `process.entry` and `process.sources` are ordinary selected retrieval tools. Their output is instruction provenance with empty scientific record-reference arrays. Source case identifiers never become target observations or credit receipts.

The caller explicitly maps a pinned T reference and operation pointer, such as `/capability_operations/0`, to actual callable names and optional argument restrictions. The pointer has meaning only within that exact pinned T body. Suggested repository callables and prose inputs/outputs do not enable operations. Missing callables remain visibly unbound. Several operation-specific restrictions on one callable are alternatives within its actual API constraint.

`prepare_scientific_binding(run_directory=..., source_directory=..., mappings=..., child_roles=...)` returns a normal binding descriptor. The caller registers it alongside its actual literature/resource/monitor bindings. Its child roles must include `scientific_process` itself and name actual registered roles. It starts no model or work. Fixed-case callers can explicitly supply `PolicyBindings.execution_planning_roles` to bind prospective duration information to their choosing roles; historical profiles retain their original default.

The parent selects role `scientific_process` and supplies:

```text
assignment = {
  selection: {version, annotation_ref, thought_ref, tool_ref},
  evidence_refs: [actual in-scope Store references],
  constraints: {...},
  context: {...}
}
```

An alternative-approach assignment additionally carries the explicit
`revision_origin` returned by its parent's completed `process.revise` operation.
Omitting that marker remains valid for ordinary children, even when their P/T
differs from their parent's. The relationship is never inferred from a change
of selection.

Each selected reference includes its version, library identity, slot, option ID and entry digest. The existing commission fields separately carry the job, scope, purpose, exact typed report schema and parent-initialized interpretation values. The mother validates and pins these operands; it does not choose their contents or install an A entry's illustrative values into the report form.

All A/P/T combinations use one recursive Python episode role. The decision context contains the selected annotation distinctions, thought alternatives/result contingencies, tool operations/availability and original parent assignment. The ordinary shared loop owns iteration and the caller's existing projector/controller owns credit/continuation. The literature tree keeps its separate seven roles and permitted relationships.

The v2 mother keeps its original A/P/T throughout the episode. Its ordinary
choices remain iterative within that process. An explicit own
`process.revise({thought_ref, tool_ref})` prepares `result.selection` and a
sibling `revision_origin` for a separately selected `episode_child` action.
Preparation starts no child and changes no current selection or history. The
existing child action supplies its own goal, scope, constraints and original
typed return form. Commissioning and reconstruction authenticate the copied
origin against that actual parent's completed preparation.

Parents can request the closed `scientific_process_results` fact source under
their chosen field name. Each row records the original selection, parent
invocation and explicit revision preparation, together with copies of the
episode's existing initial credit, closing credit, binding identity and closing
yield. These are existing values, not referral or attribution scores. A parent
forwards only rows it actually received through requested forms. A grandchild's
result reaches higher steering only through the intervening forms. Scientific
credit still projects received scientific information once; local child scores
and turns are not added to parent histories. Reads, preparation and result
formatting publish no scientific records. Inherited evidence stays initial
information. Exact current interfaces and implementation checklist are in
[FIXED_PROCESS_BOUNDARIES.md](../../docs/FIXED_PROCESS_BOUNDARIES.md).

The saved descriptor pins the library, literal caller mappings and mother implementation. The original filled request survives normal construction and independent worker reconstruction. Common helper augmentation is filtered through the binding's final tool whitelist, and dispatch validates that same narrowed catalog.

Scientific-library discovery is exposed to episodes that can commission the scientific constructor. The literature episodes receive no A/P/T selection or extra scientific-library menu; their permitted child relationships remain unchanged. Direct dispatch respects the same boundary and the binding's permitted action types.

Engineering tests cover shared-loop iteration, typed return, revision/restart, source-independent reconstruction, pre-provider identity rejection, schema transport and caller timing roles. Their decisions, score units and stopping counts are fixtures. Production resource/credit/continuation composition, a numerical wait-gain model and configured-model scientific demonstration remain open in the [full implementation checklist](../../docs/IMPLEMENTATION_CHECKLIST.md). Passing these tests does not establish those behaviors.

## Historical SL1–SL5 engineering checks

The counts and subprocess details below describe the earlier in-place revision
checkpoint. Its [verification artifact](integration_verification.json) remains
unchanged. They do not verify the v2 revision/provenance behavior above; the
[FP verification record](../../docs/fixed_process_verification.json) provides
separate connected and real-worker evidence for that behavior.

The eight new test modules contain **153 passing feature checks**: library 33,
tool contexts 38, mother 24, runtime 7, reconstruction 13, fixed-case forecasts 16,
schema transport 21 and detached execution 1. The last combined runtime/schema/
detached run passed all 29 checks. The direct permission-dispatch check was
also rerun after its added assertions and passed.

The broader regression run initially passed 58 checks and failed one direct-call
history fixture because pending_work was absent. Fresh direct calls now capture
authoritative pending work; saved contexts remain unchanged. The failed check
and affected receipt/wait-input suites subsequently passed all 24 checks.
The earlier runtime module passed its 35 existing cases in the mixed run; its
single reported failure was a new fixture's incorrect inherited-reference
expectation, corrected and passing in the subsequent runtime suite.

The real subprocess test verifies parent and child PIDs differ, selected parent
work overlaps the gated child, a selected wait wakes on return, the original
filled request/descriptor/mappings survive source deletion, and the child uses
an earlier result before revising P/T. Its parent receives only the original
typed form. Parent deltas are [1,0,1,0], child deltas [1,0,0], with exactly seven
observations and released live worker state. No library/revision outcome creates
Store observations or assessments. This also exposed and verified the shared
receipt-prefix transaction repair described in the plan.
