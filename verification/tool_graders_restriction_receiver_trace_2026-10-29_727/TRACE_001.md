# Restriction receiver and authority trace727

2026-10-29. Read-only source evidence under the final727 section of725 CONTRACT_001.
The original user attachment is authoritative. This is neither a replacement goal
nor a production consumer contract. Only this TRACE and SOURCE_PINS_001.json were
written. No application imports, tests, native/719 work, network/model calls,
installations, other agents, production edits or inventory changes occurred.
Host Python was used only for standard-library metadata/source inspection.

## Actual boundary finding

**The child's own context validates its complete closing form at admission. The
parent's context receives the admitted requested facts afterward.** Restriction
identifiers cannot use a blanket resolver or be treated as Store record IDs.

| Boundary | Actual source path | Context and information |
| --- | --- | --- |
| Interpretation update | DecisionSource.apply_response; communication.interpretation_schema | Recorded x-source fields are absent from the model-authored update. Remaining declared references use that episode's resolver. |
| Candidate closure | DecisionSource.finish; Workflow.facts; form_with_facts | Build requested facts deterministically, save literal facts/form in runtime_forms, then release. finish explicitly calls this a candidate, not an admitted parent report. It does not run a separate report-composition model or add an observation. |
| Ordinary blocking admission | Workflow.child's contract_binding, admitted_report/report | Both resolver and semantic validator close over the CHILD BindingContext, saved at construction. contract.admit validates references and relationships before save_attempt records the accepted form. |
| Detached admission | Workflow.returned_request; next_return; episode_admission._admit_form/_admit_return | Reconstruct CHILD BindingContext from the original commission. Compare x-source values with child's runtime_forms, then original TypedReportContract.admit. The parent receipt callback receives the admitted form afterward in the same admission transaction. |
| Redelivery | Workflow.redeliver | Reconstruct original CHILD context. Read frozen facts and existing interpretation fields; require revised interpretations to have identical original meanings. No new child work, native call or719 calculation. |
| Parent receipt | Workflow._receive_form | source here is PARENT. Only after successful attempt recording does it index requested Store handles and call binding received_form_references under the parent's context. |
| Parent decision | EpisodeView._model_inputs; DecisionSource.next | method_loop admits only actual direct-child ParentReport objects belonging to that parent. Runtime supplies their exact requested values as child_reports. Typed form values do not depend on every value also being a Store receipt. |
| Parent text | scientific_process_prompt._steering; alignment_report_presentation | Existing renderer presents supplied admitted child values as tables. Alignment presentation leaves unrelated values intact. This inspection does not approve a new restriction-specific TASK/STEERING template or implement pending draft002. |

TypedReportContract.admit first runs communication.validate_form with the bound
resolver and then the semantic validator. Workflow.validate_report invokes
validate_received_report on the same context and finally the role's specialist.
ScientificProcessEpisodes.validate_report runs validate_form again with
ScientificProcessEpisodes.resolve. A restriction addition must therefore work in
BOTH resolver entry points. Admission is not a parent-wide catalog lookup.

## Exact restriction_enzyme gap

723 row.name is format=identifier with x-reference-namespace=restriction_enzyme.
communication.REFERENCE_FORMATS includes identifier; its semantic walker calls
the actual resolver for every non-null such value, including applicable union
branches. Valid syntax or a successful pure723 projection grants no authority.

Currently ScientificProcessEpisodes.resolve handles only scientific provenance
namespaces, then delegates to reference_in_context. WorkflowServices checks
received-reference hooks, native events and Store scope. Workflow.resolver also
checks received-reference hooks before specialist resolution and a generic Store
fallback. No restriction namespace implementation exists in these inspected pins.
Ordinary enzyme names are not Store records, so the current real boundary rejects
them as unknown_reference.

The required narrow resolver must accept an exact enzyme name only from an
**authenticated selected own-operation catalog available to the CHILD**, or, for
a later RECEIVED-context query, the names that actually crossed in requested,
admitted enzyme_rows. The former joins to725's original captured catalog/native
source and authoritative operation row; another episode's row, a current Bio
catalog, a similar motif or supplied JSON is insufficient. The latter grants
only the received name and requested row fields, never the rest of that catalog.
A source handle without received enzyme_rows does not mean every enzyme name
became the parent's requested knowledge.

Unknown names in this namespace need authoritative False. Adding only a False
branch to ScientificProcessEpisodes.resolve is insufficient: Workflow.resolver
continues to generic Store fallback after a False specialist result. The existing
registry resolve_received_reference tri-state port can intercept this namespace
before fallback in BOTH Workflow.resolver and WorkflowServices.reference_in_context;
return None for other namespaces. A root-owned explicit equivalent interception
is also possible. Do not return True for all names or loosen identifier grammar.

The smallest immediate child-to-parent form delivery does not need a new
received-source array: method_loop already carries the exact admitted typed form.
If the parent must subsequently resolve or forward received names, implement a
narrow reader of its original admitted forms, with episode/run/contract/frozen
identity checks and captured inheritance cutoffs. Do not merge received child
operations into723 all_own_completed_results. Arbitrary recursive forwarding or
new interpretation questions are separate explicit contracts, not implied by723.

## Requested fields, source custody and a receipt caveat

723 selects one source array, restriction_mapping_results. Its const policy is
all_own_completed_results or matching_sequence with exact sequence_ref. Mandatory
identity/meaning fields are selection_policy, sequence_ref, namespace, topology,
data_status, coordinate_unit and population_scope. Optional requested fields are
operational/source metadata, population components, enzyme rows, coordinates,
recognition events and issue codes. Rows preserve source order/multiplicity.
There is no row subset, hidden first-N selection or annotation-confidence score.

For example, a form requesting mandatory fields plus enzyme name/search state
makes those values available to the parent. It does not supply unrequested motif,
positions, population counters, raw dictionary JSON or software diagnostics.
Source/native bytes do not cross because validation inspected them internally.

Workflow._references_in indexes a schema-declared reference/identifier/accession
only when record_lookup returns an actual matching Store record, then applies
Store.reference_subset. It deliberately does not load source/artifact bodies.
Consequently sequence_ref is a receipt candidate, requested source_ref and
input_source_ref are candidates, but EcoRI is not a Store-handle receipt. Parent
form knowledge remains available even when no catalog-name receipt exists.

**Current generic traversal needs an explicit restriction custody decision.**
EpisodeReceipts.receive follows Store._refs on a received source, including
artifact_ref, text_ref, auxiliary_artifact_refs, parent_source_refs and operand_refs.
Its custody-only exclusion currently names selected episode.execution_result
bundle versions, not725's episode.restriction_result or episode.restriction_input.
Thus if a parent requests a restriction source_ref, generic traversal would mark
all these dependent handles received although no artifact bytes are loaded. This
is broader than the requested form fields and must not be described as source
contents actually read. A restriction received hook alone cannot undo traversal.
Root should define an exact provider/version custody-only exception through the
existing receipt mechanism, or another equally narrow actual mechanism, before
claiming only requested artifact access. Preserve all other source semantics.

## Existing original-return and receipt proof

EpisodeReturnRecords.authenticate checks run, EpisodeRef path identity, original
scope/assignment and exact saved runtime_episodes request. context reconstructs
that saved context. _attempt authenticates the parent, original successful
runtime_report_attempt, immediate child's exact context, original contract,
selected runtime action (or saved redelivery selection), child role/path and
literal x-source arrays against child's frozen runtime_forms. _admission_index
parses the exact run:parent:index:typed_form operation key. These are reusable
existing proof pieces; JSON equality alone is not an admission or job receipt.

Detached C4 additionally joins the original commission/return IDs, selected
pending action, active parent and exact original contract. Form attempt,
received references, completed original action and cumulative parent credit are
one Store transaction. Replayed runtime_return_admissions return their saved
admission/credit/controller input and do not call receipt or projection callbacks
again. A closed parent receives no retrospective completed action. completed_unit
restores its original slot and report without repeating child work.

Receipt inheritance has TWO distinct snapshots: through_receipt_index for Store
handles and received_report_prefix with original attempt identities plus
contract/form digests. EpisodeReceipts.bind freezes both at child construction;
a later-arriving earlier-decision child report is not automatically inherited.
A new received-form reader must respect that captured typed-report prefix, not
infer receipt from a smaller commission decision index. Existing
ScientificProcessProvenance._received_results reads this episode's successful
requested process-result attempts; it is not a restriction result or permission
to return the child's private results. No new ledger is required by this trace.

## Frozen facts and replay

ScientificProcessEpisodes currently registers process results and alignment site
sources only. facts validates the original scientific assignment, projects its
process result and requested alignment own-action pages. It has no restriction
source/reader. validate_report validates references, then compares requested
alignment facts with literal frozen arrays; process-result fields likewise use
their original closing source. Workflow.facts returns existing runtime_forms
immediately rather than rebuilding a closed result.

Root's restriction connection should follow that path: validate723 selectors in
_invocation; register723 fact sources; page authenticated own action records;
project723 requested fields once; save runtime_forms through existing finish;
validate exact frozen source with validate_frozen_restriction_return on admission
and redelivery. Frozen validation must not call own_action_results,719, Bio or a
native worker. Namespace authentication may read retained original authority,
without refreshing native/catalog data or deriving numbers. If root uses frozen
requested names for closed-context resolution, tie them to the authenticated
original frozen source rather than broad current catalog membership. Keep source
validation distinct from another scientific measurement or controller action.

## Smallest proposed root-owned ports

These are source-only recommendations for the subsequent root contract, not
implemented signatures or a capability claim.

| Port/component | Required semantics |
| --- | --- |
| RestrictionMappingActionRecords(EpisodeReturnRecords).own_action_results(context, *, selection, after_decision_index, limit) | Authenticate original scientific owner and requested723 selector. Page only this episode's actual completed/partial restriction tool actions by original decision index; no inherited/sibling actions. Join exact runtime_actions to tool_operations using run:episode:index; validate operation identity, name/arguments/scope and exact saved result, allowing only the existing pending_work_after_action runtime augmentation. Authenticate725 published source via its loader and726 authoritative row; return723's exact action shape. |
| restriction_mapping_own_action_results service | Forward the above bounded page. A single source needs no generalized scientific schema interpreter. Page size/cursor is host enumeration of saved rows, not an episode itinerary or new selected action. |
| RestrictionMappingActionRecords.frozen_facts(context, *, sources) and restriction_mapping_frozen_facts service | Authenticate context; read only requested literal restriction_mapping_results array from runtime_forms, preserving absent versus []. No live action reconstruction or calculation. |
| restriction_mapping_reference(context, reference, namespace) | Exact namespace authority described above; unknown names False; unrelated namespace None at the registry interception. Own catalog versus requested received form names remain separate inputs. No unrestricted parent catalog grant. |
| Selected-operation authorization | ScientificProcessEpisodes.execute must pass the actual received refs for both aliases into the actual Tools binding, as it already does for selected result.blast.hsp/source.locate. Native mode requires selected sequence handle known before selection; saved mode requires selected prior result source before selection.721 still owns exact sequence/mapping witness;725/726 still own original input/job/publication. |
| Fingerprint and selector consumers | Register723 in fact_sources, _invocation, facts and validate_report. Include actual new proof/return dependencies in mechanics source identity; preserve original closed-request restoration and old observations. Do not expose aliases/catalog text while draft002 feedback remains unresolved. |

723 action record fields are exactly decision_index,operation_ref,tool_name,
work_mode,operation_status,sequence_ref,namespace,input_source_ref,source_ref,
native_artifact_ref,mapping_artifact_ref,mapping,failure_code. Mapping joins its
selected_sequence to sequence_ref/namespace/input_source_ref. Null mapping means
specific unavailable failure, not zero counts.725 raw file byte SHA differs from
MappingResult.native_sha256's canonical NativeResult digest. Copy719 numerical
values and723 fields; never add another count/coordinate calculator.

## Shared _received_before relocation

The production/test name scan found one implementation and one production call:
AlignmentSiteActionRecords._received_before and its result.blast.hsp input check
in _record. No other _received_before definition or call was found. All direct
EpisodeReturnRecords subclasses were enumerated; none overrides this name.

Moving this method verbatim under the SAME name into EpisodeReturnRecords is
source-semantically safe: the base already supplies db,run_id,_require; the
alignment instance preserves failure_prefix=alignment_site_return_. Its current
caller and errors retain ordinary inheritance. Do not change these meanings:

* A bound lineage is required; an unbound manifest and lineage cycle raise the
  same failure-prefix codes.
* A same-episode initial receipt is available immediately. decision_input uses
  source_index <= selected decision; own_action/child_form/report_redelivery use
  source_index < selected decision. A same-index tool result cannot authorize
  its own input.
* Ancestor receipts qualify only within each original through_receipt_index.
  Later parent receipts are not inherited retroactively.
* Context.received_record_refs is not a substitute for this original receipt
  history. The helper proves handle delivery, not source-byte reading or typed
  report-name knowledge.

Existing tests/test_alignment_site_action_records.py contains the receipt-kind/
index matrix, before/after inherited-prefix cases and missing-history rejection
(lines311–355); these were READ, not run. The helper can support restriction
native-sequence/saved-source preselection proof, with the restriction subclass's
own prefix. It cannot replace original action/source/job authentication.

ScientificProcessEpisodes' current mechanics fingerprint includes the alignment
module but not EpisodeReturnRecords. Relocation changes the alignment file hash;
include the shared proof dependency in the subsequent restriction binding and
preserve the accepted closed-process restoration. No base _attempt/authenticate/
_equality semantics need changing. Existing nonalignment subclasses gain an
unused inherited method; their executed paths otherwise remain untouched.

## Remaining verification and status

Root must verify actual Tools dispatch/publication/action proof, restriction
namespace resolution in both child and receiver paths, requested-field custody,
closed/replayed/redelivered equality without fresh science, sibling/forged/late
receipt rejection, native/saved authorization, and original one-action/controller
accounting. A source trace cannot establish any of those integrated capabilities.
Use existing retained results for these checks where possible; do not repeat
successful native work to repair assertions. Supporting operation results add
no restriction confidence score or new W05 aggregation.

The two fixed WORK_STATUS rows182/183 remain unfinished, with draft002 awaiting
running feedback and actual host/episode binding pending. Historical152 component
checks are tracker evidence, not727 execution or full-boundary proof. Whole-tool,
connected-operation and scientific-scoring-group increments from727 are zero.
All original R1–R7 remain open. Root retains ownership of the subsequent precise
consumer implementation contract.
