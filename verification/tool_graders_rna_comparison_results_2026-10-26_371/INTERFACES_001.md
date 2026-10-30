# Workload E authority and selected-result interfaces

These are the fixed 362 addendum007/008 ports, with ancestor-return proof from
010 and shared constructor transaction preservation from011. This packet does
not define another episode, native job, scoring formula or prompt template.

## Original operands

`gene_annotation_episode.rna_structure_comparison_operands` exports:

```python
authenticate_received_rna_operand(context, descriptor, *, returns) -> dict
authenticate_received_rna_failure(context, failure, *, returns) -> dict
validate_rna_comparison_selected_inputs(store, context, selector, *,
    anchor_handoff_ref, returns) -> list[str]
resolve_rna_comparison_operands(store, context, selector, *,
    anchor_handoff_ref, returns) -> dict
```

`returns` is the existing bound `NativeRNAStructureReturns`. Each saved or
failure member is authenticated independently against its original selected
completed action, native receipt and actual eligible frozen form. The saved
descriptor is exactly the unchanged original descriptor. A failure is the
entire original fixed-ordinal failure row. Source handles alone are not proof
of receipt of either value.

The current parent's actual successful received form can authorize a new
commission. A commissioned results child uses its original initial knowledge.
Every lineage manifest must equal its saved request. At an ancestor boundary,
the original attempt identity and parsed contract/form digests must occur in
that child's original frozen received-report prefix. An absent legacy prefix
raises `rna_comparison_operand_prefix_proof_unavailable`; a late receipt cannot
be reconstructed from its earlier commission index. No new receipt registry or
scientific source is created by these checks.

`NativeRNAStructureReturns.authenticate_received_saved_input` is the extracted
original authority proof. Its public original `resolve_saved_rna_input` still
requires a results assignment's handoff and single saved_input to equal the
selected original descriptor. E adds the stronger new comparison prefix proof
after the shared original proof; it does not relax the old route.

Selected reference order is membership order, explicit correspondence source
order, then the routing anchor, deduplicated in that order. The anchor is an
independently received original native RNA handoff. It is not an inferred
baseline. Alias members have no additional original operand or receipt.

Resolution returns exactly:

```text
version: rna_structure_comparison_resolved_operands_v1
data: {non_alias_member_id: {original_sheet, original_bundle_software,
                           received_failure}}
original_receipts: {saved_or_received_failure_member_id: original_receipt}
selected_references: [ordered_unique_reference]
```

Only the selected original sheets and the original retained bundle's software
object are opened. Original producer locations and auxiliary outputs are not
consulted. `RNAComparisonInputError.issue` is exactly the input-stage issue
from008, with retained_sheet_missing or retained_sheet_digest_mismatch and the
selected member ID. The original cause is chained internally. It never becomes
a received native-failure member or an all-null scientific operand.

## Existing results role adapter

`NativeRNAStructureComparisonResults(owner)` is bound as
`owner.rna_structure_comparison_results`. It consumes
`owner.native_rna_structure_returns` and the actual D publication implementation.

```python
applies(context) -> bool
async execute(context, target, tool_name, arguments, operation_key) -> dict
facts(context, *, verify_artifacts=True) -> dict
read_result(context, result) -> dict
read_receipt_key(key, scope, *, assignment=None) -> dict
resolve(context, reference, namespace) -> bool
retained_reference_access(context, reference, namespace) -> bool | None
credit_view(context, receiver_selection) -> dict
completion(context) -> dict | None
```

`operation_catalog()` contains only execution.results.status and
execution.results.collect, both with an exact empty argument object. Status
checks the selected retained inputs and records its result without B/D or
native observation. Collect calls D with exact20GiB RAM,4GiB scratch and no wall
limit. It never changes the caller's resource or retries unresolved work.

Immutable intent, status/custody detail, grading and receipt use the exact
008 directory. The result receipt has the exact008 field set; the exported
`VERSION` is rna_structure_comparison_result_receipt_v1. D's prepared record and
worker chain remain separate. The index stores only original run, episode and
operation pointers. `result_receipt_key(body)` derives the receipt identifier
from those three original fields.

On reading or replay, the adapter authenticates original context, assignment,
scope, commission, selected action, immutable intent/receipt and actual outcome.
The own-action `read_result` additionally requires the caller's exact episode
and assignment. Original lookup by `read_receipt_key` is a scope-checked port;
it does not itself grant received-value authority. A completed outcome may add
only the host's existing validated pending_work_after_action envelope.

Every successful calculation is revalidated through actual D against newly
authenticated original inputs and the original expected receipt key. An
authority verdict is not cached. A recorded input-custody failure replays as
that original failed collection even if its input bytes are later restored.
Status and custody failures contain no invented projections or input digests.

The completed action returns `record_refs=[]`, `changed_record_refs=[]`, the
actual receipt and feedback null. Facts provide only the selected requested
comparison projections, plus the exact basic results fields from008. Repeated
identical scientific rows do not become new facts. No old individual-structure
facts or saved-input descriptors are synthesized from a comparison.

## Typed returns and reference boundaries

`RNAStructureComparisonReturns(owner)` is bound as
`owner.rna_structure_comparison_returns`. It reuses EpisodeReturnRecords and
the existing original-commission/frozen-form checks. It supplies the fixed
received_context, received_facts, validate_received_report, record_admission
and resolve_received ports. `requested_sources(schema)` recognizes only
execution_rna_structure_comparison_projections, whose exact schema comes from C.

Results facts equal actual selected receipts. Annotation/scientific-process
forwarding requires the actual received form. Altered values, qualifications,
original forms and namespace substitutions cannot pass an earlier cached
reference check. Admission returns[]: comparison identifiers are not Store
references and do not enter EpisodeReceipts.receive.

Both modules export `IDENTIFIER_NAMESPACES` as
`("rna_comparison_receipt", "rna_comparison_calculation")`. Exact namespace
dispatch precedes the retained-reference guard in the shared host. Identifiers
resolve only against own/received rows. The internal sheet, components,
projections, worker input/request/start/receipt/log/output artifacts are denied
by default. The guard reads fixed custody metadata to identify them, not
scientific payloads or source trees. An independent explicit initial operand,
own completed action or authenticated original immediate-child reference form
can still authorize identical content-addressed bytes.

## Credit and practical completion

`credit_view` keeps the existing caller's units and returns exact zero new
operational credit, native acquisition count and handoff count. It changes no
prior native receipt or credit. Scientific and monitoring binding flags are
false; E invents no alternative score.

Completion requires a valid actual completed collect action and D's complete
requested delivery. It returns the ordinary practical_completion_v1 proof with
the original assignment/receipt digests, usable_handoff endpoint and exactly:

```text
selected_original_operand_authority
retained_operand_custody
requested_comparison_projection_or_explicit_unavailability
```

The existing estimator/controller owns immediate exact-zero future expectation
and continuation. Full shared Workflow dispatch, one observation per own action,
parent closure and prompt presentation are separately verified by root/372;
these adapter ports do not establish that full-tool claim on their own.

## Additive final namespace correction (362 addenda012/013)

After E check008 and shared372 check005 finished, the results adapter's
retained-reference guard was corrected at lines295,299,302–303,309. The exact
allowed `execution_handoff` set is the routing anchor plus each selected saved
descriptor's independently authenticated original handoff. The existing full
selected-input proof still runs before access is granted. In a comparison
context, an `execution_handoff` reference outside that set returns False before
the shared host's generic native-handoff fallback. Ordinary selected sources,
failure sources, sheets and bundles do not gain that namespace. This does not
change the selected initial references or any calculation, requested projection,
credit or completion meaning.

Final results-module SHA256:
`2e1a4dfe2ac409018dc87073ea7897399b30904f8d7140a12adcf754304a5bcc`.
Earlier checks retain their original sources. The final focused E check009 and
shared372 namespace check007 identify their actual final-source evidence in
their immutable execution receipts.
