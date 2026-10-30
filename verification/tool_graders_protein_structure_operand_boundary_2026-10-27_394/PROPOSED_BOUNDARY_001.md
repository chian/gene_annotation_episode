# Protein operand and received-authority coding boundary, 394

2026-10-27. **Proposal for root approval, not implemented ports.** This lane
changed no production/test code, prompts, inventory, tally or earlier packet.
It ran no tests, native scientific operations, models, network calls or services.
Only this 394 packet is owned here. Its scope is original operands and actual
received authority for the protein structure route, not a general audit.

Authority: the entire immutable attachment at
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
was read; SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
AGENTS.md and the relevant episode, time, practical, TASK/STEERING and grader
directions were read. All of 380/SHARED_CONTRACT_001 and CONSUMER_TRACE_001,
addenda 002–004/006, capture 005 and worker 007 were read. Later 008 and 009
are incorporated below. After the implementation study, the immutable objective
and all sixteen principles were reread verbatim, then the relevant 380 operand,
return, issue, dispatch and original-authority contracts were reread.

## 1. Current implementation versus this proposal

The existing scientific child already executes selected `sequence.align` through
`WorkflowServices.execute_tool` and the bounded Store-free sequence worker.
`execution.estimate` for that tool calls the same `_alignment_arguments` reader.
Both currently accept registered sequence material without the proposed protein
descriptor check. `ScientificProcessEpisodes.execute` currently forwards
`permitted_record_refs` only for `result.blast.hsp`.

The ordinary alignment publisher retains the full native JSON and grading
artifact, immutable source/observation identities, ordered deduplicated operand
references, and its original `tool_operations` row. Runtime retains the matching
selected action/outcome. These records can prove an original alignment; a
matching sequence length or Store-visible observation cannot replace that proof.

A/B/C/D1 now supply concrete scientific types, deterministic readers/calculations,
native execution envelopes and four exact projection fact schemas. Their
validators do not authenticate a receiving episode. C's worker already checks
the original extraction map/sequence bytes, re-extracts using the original
selection, and only then explicitly rebinds the detached sequence to fixed or
moving. C's received-transform worker check explicitly assumes D has proved the
grant before commissioning. Keep that division.

The original source/reference publisher, original-result lookup, received-return
adapter, operand adapter and shared admission wiring are still required. D391's
reported 51 tests establish its own projection boundary, not these missing
authority paths. This lane did not rerun those tests.

## 2. Ownership and exact dependency values

The proposed coding lane owns only:

- `gene_annotation_episode/protein_structure_operands.py`;
- `gene_annotation_episode/native_protein_structure_returns.py`;
- new focused tests for those two modules and a new executed verification packet.

Root owns all existing shared consumer edits and the new protein result host /
publication modules. D392 owns capture and retained-byte lookup. D393 owns the
Store-free result worker. D391's pure projections and the four source schemas
remain unchanged. A owns shared science/descriptor types and B owns recorded
component validation/calculation; this lane does not clone their definitions.

Dependencies are specific values, not whole workloads:

| Supplier | Exact value/port required here | Use |
| --- | --- | --- |
| A | `StructureSequenceDescriptor`, `AlignmentDescriptor`, `SavedSheetDescriptor`, `DeclaredTransform`, `AlignmentSnapshot`, `FileIdentity`, `StructuredIssue` and their existing validators | Closed shape and within-record relationships. |
| A | `validate_alignment_snapshot`, `rebind_structure_sequence`, existing sequence/map types | Healthy retained traceback and the one allowed operation-local role substitution. Rebinding never precedes exact original map validation. |
| B | `validate_recorded_protein_structure_components(sheet, components=...)` | Authenticate already recorded arithmetic without fitting, SVD or replacing components. |
| C | `validate_protein_structure_request`, `validate_protein_structure_requested_job`, `required_input_files`, `validate_input_associations`, `InputFile`, `ScientificRequest`, `CompareRequest`, `Software` | Exact selected native request and required role/file multiset. |
| D391 | `protein_structure_fact_sources` and validators for projection results/failures | Exactly four typed return sources; no arbitrary findings or new source schema. |
| D392 | `retained_protein_structure_file(store, FileIdentity)` and `decode_protein_structure_json(bytes, canonical_bytes=...)` | Retained Store path, actual digest/length and strict JSON; never producer reads. |
| Root result host | The three metadata/receipt ports in section 3 | Actual original result receipt, qualified files, published selected facts and family ownership. |
| Existing runtime | `EpisodeReturnRecords`, `EpisodeReceipts.read_manifest/known`, `runtime_actions`, `tool_operations`, `runtime_report_attempts`, `runtime_forms`, original saved contexts | Original action and frozen delivery proof. |

No runtime scorer, scheduler, monitoring policy, model, acquisition or aligner is
a dependency of the two proposed modules.

## 3. Required root result-host interface

Keep the durable result receipt's private layout owned by root. Supply this
small **Python-only, detached read view** of its authenticated existing records.
This is not a new Store record/reference type, fact source or episode message.
All listed keys are required; only explicit nullable fields may be null.

```python
ProteinFactGroups = {
    "execution_protein_structure_projections": list[ProjectionResult],
    "execution_protein_structure_saved_sheets": list[SavedSheetDescriptor],
    "execution_protein_structure_sequences": list[StructureSequenceDescriptor],
    "execution_protein_structure_failures": list[ProteinFailureReturn],
}

ProteinResultAuthorityRecord = {
    "custody": ResultCustody,
    "selector": ProteinResultSelector,
    "request": ScientificRequest,
    "software": Software,
    "native_file": FileIdentity | None,
    "sequence_file": FileIdentity | None,
    "residue_map_file": FileIdentity | None,
    "sheet_file": FileIdentity | None,
    "original_components_file": FileIdentity | None,
    "components_file": FileIdentity | None,
    "facts": ProteinFactGroups,
}

# Proposed methods on root's NativeProteinStructureResults:
def read_result_authority(self, custody: ResultCustody, *, scope: dict
) -> ProteinResultAuthorityRecord: ...

def own_fact_groups(self, context: BindingContext, *, verify_artifacts: bool
) -> ProteinFactGroups: ...

def owns_reference(self, reference: str) -> bool: ...
```

`read_result_authority` is metadata/receipt authentication. It must locate the
exact result episode and operation named by custody, rather than choose the
first source-index entry. It proves all of these relationships:

1. Current run, saved result episode/path/request, original parent commission,
   scope, complete original assignment/selector and report contract agree.
   `custody.original_request_sha256` is `execution_contracts.digest` of that
   results child's full original request, not the scientific request alone.
2. The original `execution.results.collect({})` action actually completed and its
   runtime result agrees with the immutable result receipt and publication.
   Status, a written intent, a worker output file, or a pending action is not a
   completed result. Runtime's separately validated `pending_work_after_action`
   addition may be excluded only as that existing exact wrapper field.
3. The original target/handoff, capture's qualified run plan and retained bundle
   identify the same selected native attempt/request/software. Revalidation uses
   saved target/receipt data, not current liveness or producer files.
4. The source record has its normal immutable Store identity and exact publisher
   payload. Each returned file identity is the file actually captured or retained
   by that original result operation, with its declared role/format. No scanning
   of another source's auxiliaries supplies an omitted identity.
5. `facts` is the per-action selected publication, unchanged from that receipt.
   It contains only descriptors/projections/failures actually published there.
   Frozen episode facts/forms are checked separately by the returns adapter.

The read view exposes **qualified scientific outputs only**. Under 380/008,
a C-valid but B-invalid native comparison may have a diagnostic native file,
but has null qualified sheet/components here and cannot supply comparison
numbers. A saved sheet retained for diagnosis with an absent or inconsistent
baseline also has null qualified sheet/components here. Diagnostic files stay
in the root receipt/capture, not in an executable saved-sheet grant. Extraction
files are non-null only when the actual captured native/sequence/map relationship
was qualified; a missing `sequence.txt` is not reconstructed into a grant.

For a saved recalculation, `request`/`software` remain those of the original
native result; `selector` and `custody` identify the later selected calculation.
`sheet_file`/`original_components_file` retain the original immutable pair;
`components_file` identifies the later calculation. Any repeated original
saved-sheet descriptor retains its original custody. These distinct identities
are needed to reject a later transform claimed under only an earlier descriptor.

`own_fact_groups` reads only this episode's selected original result actions.
With `verify_artifacts=False`, loss of retained bytes does not erase historical
descriptor delivery; byte-consuming operations will report the specific loss.
With `True`, all actual selected numerical output artifacts required by the form
are checked. It never calculates or publishes a result again.

`owns_reference` is a classification/denial input, not an authorization verdict.
It recognizes protein source records, their original generated reference records,
captured artifacts and later prepared/calculation/table artifacts using compact
published metadata. It must also recognize foreign-run/sibling protein material
so that missing authority cannot fall through to generic Store visibility.
Do not open a native result or numerical sheet just to classify a reference.
The ordinary source tag plus the root's recorded per-action file identities are
sufficient. Independent explicit delivery of identical content may still prove
access; merely finding another source containing the same bytes does not.

The exact naming of these three root methods and this read view is an approval
item. They are a concrete dependency proposal, not a claim that the result host
already provides them.

## 4. Normal Store publication and lookup requirements

The extraction publisher must use the existing reference schema unchanged:

```python
payload = {
    "reference_type": "protein",
    "source_ref": original_source_ref,
    "accession": "structure_sequence_" + digest(original_structure_sequence),
    "label": "Structure-derived protein sequence",
    "sequence_ref": sequence_file["artifact_ref"],
    "molecule": "protein",
    "length": original_structure_sequence["sequence_length"],
    "term_refs": [],
    "context_refs": [],
    "anchor": None,
}
record = store.put("reference", payload, origin="tool")
```

Here `digest` is `execution_contracts.digest`, over the exact original complete
StructureSequence. The sequence bytes are uppercase ASCII with no header or
newline. The map bytes are `execution_contracts.canonical(sequence).encode("utf-8")`
with no newline. Both artifacts must already be actual captured bytes.
`Store.put` supplies the domain identity using **domain** canonicalization; do
not replace that identity algorithm. Store IDs accept their existing 24–64 hex
suffixes, while artifact SHA-256 identities remain full 64 hex digits.

Do not use `origin="extracted"`: `Store._validate_record` reserves that origin
for an exact source anchor and a null sequence/length. Do not add a product,
new reference kind, target footprint, surrogate source, or source-schema field.
`subject_length` uses the actual sequence artifact's size; `subject_molecule`
returns protein; `subject_unit` returns aa. The ordinary self-map describes
sequence indices and cannot stand in for the structure residue map.

Root can use this exact ordinary source payload, matching the established
native-family pattern, without a schema extension:

```python
{
    "provider": "episode.execution_result",
    "accession": "native_protein_structure_" + digest(bundle["identity"]),
    "uri": None,
    "artifact_ref": capture["bundle_file"]["artifact_ref"],
    "text_ref": None,
    "request_ref": None,
    "version": "native_protein_structure_bundle_v1",
    "retrieved_at": bundle["finished_at"],
    "auxiliary_artifact_refs": ordered_unique_actual_captured_and_prepared_refs,
}
```

The auxiliary list contains actual observed capture bytes, including preserved
mismatches for diagnosis, and already retained worker outputs where present.
Capture retains the role/match status; list membership alone grants no use.
Publish this source before a reference or descriptor that points back to it.
Never put the new reference/descriptor, current ResultCustody, future return,
or a hash of those cyclic values in its payload. Original scientific worker
outputs do not contain their own future result custody and can be retained
before this source. Saved recalculation does not mutate that original source.

Source payload identity is root-owned. If root chooses a different ordinary
accession/auxiliary ordering, it must expose one exact publisher/validator helper
to the result host; the operand lane must not guess it or accept several loose
alternatives. The proposed payload above needs root approval.

The original-result lookup must retain the source-to-receipt association outside
the source payload. Multiple collections of one native source are possible;
`ResultCustody` pins the producing result episode/action/request and the exact
descriptor's allowed uses. A source-only lookup must not choose an arbitrary
receipt as authority. The source's immutable provider/version identifies the
protein family even when no valid admitted descriptor can be found.

## 5. Proposed returns adapter ports and authority algorithm

```python
SequenceUse = Literal["sequence_align", "structure_correspondence"]
SavedSheetUse = Literal["recalculate", "select_projection", "use_transform"]

def requested_sources(schema: dict) -> tuple[str, ...]: ...

class NativeProteinStructureReturns(EpisodeReturnRecords):
    def __init__(self, owner: ExecutionEpisodes): ...
    def authenticate(self, context: BindingContext, *, allow_unsaved=False
    ) -> BindingContext: ...
    def received_context(self, context: BindingContext) -> list[dict]: ...
    def received_facts(self, context: BindingContext, schema: dict
    ) -> ProteinFactGroups: ...
    def validate_received_report(self, context: BindingContext, form: dict,
        schema: dict) -> None: ...
    def record_admission(self, context: BindingContext, form: dict,
        schema: dict, operation_key: str) -> list[str]: ...
    def resolve_received(self, context: BindingContext, reference: str,
        namespace: str | None) -> bool | None: ...
    def retained_reference_access(self, context: BindingContext, reference: str,
        namespace: str | None) -> bool | None: ...
    def received_sequence_descriptors(self, context: BindingContext,
        reference_ref: str) -> list[StructureSequenceDescriptor]: ...
    def authenticate_received_sequence(self, context: BindingContext,
        descriptor: StructureSequenceDescriptor, *, required_use: SequenceUse
    ) -> ProteinResultAuthorityRecord: ...
    def authenticate_received_saved_sheet(self, context: BindingContext,
        descriptor: SavedSheetDescriptor, *, required_use: SavedSheetUse
    ) -> ProteinResultAuthorityRecord: ...
    def authenticate_received_alignment(self, context: BindingContext,
        alignment: AlignmentDescriptor) -> None: ...
    def received_transform_projections(self, context: BindingContext,
        transform: DeclaredTransform) -> list[ProjectionResult]: ...
```

`received_facts` returns only requested keys, so its concrete return type is the
corresponding partial keyed view of ProteinFactGroups; absent requested facts
are empty arrays. `received_context` is exactly a list of
`{"fact_source": source_name, "facts": detached_rows}`. It is host intermediate
data, not model-facing JSON or an instruction template.

All source names come from D391's exact four-source dictionary. Source-key order
and row order are stable; duplicate identical rows are deduplicated preserving
first actual delivery order, without combining different grants. No successful
authority verdict is retained across synchronous form checks, turns or reopen.
Any use of the existing form-validation frame is scoped to that single check.

### Frozen context and original forms

Reuse `EpisodeReturnRecords.authenticate/context/_attempt/_admission_index` for
saved identity, successful immediate-child return and original action checks.
Add the role/path equality and full original commission/scope/purpose/schema /
frozen-form comparisons used by NativeRNAStructureReturns._attempt. A redelivery
must match its original child and selected schema/purpose, then the original
frozen facts; it does not establish a new scientific result.

Do **not** copy NativeRNAStructureReturns._received_selected_value alone: its
ancestor decision cutoff is insufficient to prove actual receipt time. Reuse
the stricter semantics present in RNA comparison operands:

1. At every link, the saved request's `message.knowledge_inheritance` equals
   `EpisodeReceipts.read_manifest` exactly and names the immediate saved parent.
   Reject cycles and path disagreement.
2. The current scientific episode may use its actually completed own work and
   actual successful returns. An assigned launch/resource/results input is
   constrained to its frozen initial knowledge/assignment. Unsaved construction
   is accepted only for an exact just-built child with the original parent,
   matching manifest and no existing own actions/form; it is not execution proof.
3. On ascent, require the saved `received_report_prefix`; do not invent one for
   historical NULL manifests. Restrict each ancestor attempt to an exact entry
   containing decision_index, delivery_ref, child_episode_id, contract_sha256 and
   form_sha256. Also require its index to precede that child commission.
4. Require the actual reference operands in the corresponding frozen semantic
   receipt selection. `known()` is necessary but not sufficient: its recursively
   expanded source references cannot stand in for a typed descriptor value.
5. For every successful form, validate the exact original schema and original
   source facts; require the entire descriptor/projection value, including
   custody and allowed uses, to be one of those actually delivered. A forwarded
   form recursively proves its own earlier received values. A direct sibling
   report and an unreceived later ancestor report provide no authority.

### Descriptors, grants and actual reference delivery

Sequence descriptors qualify only from the sequences source or an explicitly
returned `descriptor` selected field in a **values** extraction projection.
Match the whole descriptor against the original host publication, then require
the requested allowed use. A descriptor hidden inside an unread artifact table
does not become a received sequence descriptor by source/table traversal.

For a sequence descriptor, its exact explicit operand-reference set is:
reference_ref; sequence_file.artifact_ref; residue_map_file.artifact_ref;
structure_file.artifact_ref; custody.handoff_ref; custody.source_ref; and
custody.bundle_artifact_ref. These are operation operands, not delivered hidden
measurements. For a saved-sheet descriptor, use its custody's three references
and sheet_file/original_components_file artifact references. Grant no other
source/bundle auxiliary.

380/009 now fixes `return_saved_sheet=true` to exactly
`["recalculate", "select_projection", "use_transform"]`, in that order; false
returns no descriptor. This is an explicit original selector choice. It does
not prove transform availability or numerical receipt. Enforce the requested
use at each downstream operation.

For an ordinary ProjectionResult, custody and components-file locators are
validated against the root receipt but are **not added as generic read grants**.
An artifact delivery adds only the exact table artifact with
`allowed_use="read_exact_selected_table"`; its descriptor is not numerical
delivery. Failure custody/IDs also do not expose underlying artifacts.
The actual original source may be returned under the existing generic
execution_result_refs source, but source-only delivery grants no descriptors or
auxiliary bytes. This adds no fifth protein source schema.

`record_admission` returns exactly the grantable Store references above, after
validating the saved successful report attempt and supplied form/schema equality.
Do not call `Store._refs` recursively on an arbitrary protein projection to
compute grants. Numeric/provenance strings and calculation/receipt keys are not
Store references. `resolve_received` returns None only for an unrelated family;
it returns False for owned material lacking the exact proof, before any generic
resolver fallback. Do not treat a positive identifier lookup as knowledge of
its unseen numerical data.

### Original alignment receipt proof

`authenticate_received_alignment` proves one of two paths, not a fabricated
child-return record for own work:

- The observation is an actual completed own `sequence.align` action in the
  current episode, or in a frozen ancestor prefix before commissioning. Match
  exact `run_id:episode_id:decision_index` operation key, selected tool/arguments,
  operation_ref, saved ToolRegistry outcome and runtime outcome. The original
  observation/source must be in that outcome's actual record_refs and receipt
  prefix. Only the existing validated pending-work wrapper may differ.
- The observation reference was explicit in a successful original typed form.
  Use declared reference fields or the exact frozen recorded reference source;
  then prove the sending child's authority recursively back to that original
  completed alignment. A source-only form or arbitrary Store reference in a
  body does not prove receipt of the observation. At ancestor boundaries apply
  the saved received-report digest prefix, including delayed returns.

The original producer can be a separate child that actually returned its
observation through these immediate boundaries. Direct access to that child's
Store rows is not the proof. The exact original selected operation must be
`sequence.align`; the broader legacy helper accepting `reads.align` is not the
protein contract. Original-operation fallback for a legacy source missing
operand_refs must still match this exact operation and observation, not any
matching row in the run.

## 6. Proposed operand ports and consumers

Keep 380's four required public signatures unchanged:

```python
def authenticate_structure_sequence_reference(store, context, reference_ref, *, returns
) -> StructureSequenceDescriptor: ...
def authenticate_selected_alignment(store, context, alignment, *, fixed, moving,
    orientation, returns) -> AlignmentSnapshot: ...
def resolve_comparison_operands(store, context, request, *, returns
) -> ResolvedComparisonOperands: ...
def validate_saved_structure_sheet_operand(store, context, descriptor, *, returns
) -> ProteinStructureSheet: ...
```

Add these small explicit host ports to avoid private-method coupling:

```python
def is_protein_structure_sequence_operand(store, reference_ref: str) -> bool: ...

def authenticate_received_structure_transform(store, context,
    transform: DeclaredTransform, *, returns) -> ProteinStructureComponents: ...

def validate_protein_structure_job_inputs(store, context, assignment: dict, *, returns
) -> list[str]: ...

def validate_protein_structure_selected_inputs(store, context,
    selector: ProteinResultSelector, *, handoff_ref: str, returns) -> list[str]: ...

ResolvedComparisonOperands = {
    "request": CompareRequest,
    "input_files": list[InputFile],
    "selected_references": list[str],
}
```

All these functions are read-only. They return detached validated values or a
structured operand error. They cannot stage files, acquire data, fit, align,
invoke a model, start a process/job, choose inputs/resources or change credit.

### Sequence preflight

The classifier reads immutable record provenance, never label/accession prefix,
displayed sequence or a caller flag. A reference whose actual source is the
protein result family enters the protected path even if its original extraction
receipt or admitted descriptor is absent. Full original extraction provenance
is then established by the result-host lookup. A protein-family reference from
the wrong original operation fails; it never becomes an ordinary reference.
Ordinary references keep their existing behavior. The service fails closed for
protein-family operands when the protein authority binding is absent.

The additional derivative-classification choice is listed in section 10: a
feature or product must not be a shortcut around an original structure reference
requirement. Classification can inspect only its actual immutable sequence
ancestry, without creating grants by traversing that ancestry.

`authenticate_structure_sequence_reference` obtains actually received candidate
descriptors for this exact reference and requires `sequence_align`. If several
valid original deliveries authorize the same immutable reference, select the
first in deterministic actual delivery/prefix order solely as an authority
witness. Never combine their allowed uses or scientific values. Every candidate
actually used must match the original publication/receipt; conflicting original
identities reject. No eligible candidate gives `sequence_not_received`.

Then verify the exact normal reference payload from section 4, source identity,
original request/selection, formats, molecule, sequence length and artifact
identities. Read the original qualified ExtractionNative and the actual retained
structure/sequence/map files. Require byte-exact canonical map equality with
that original native.sequence, exact ASCII sequence equality, and agreement of
all original selection fields. File/selection equality is type-sensitive.
Authentication does not repair missing files or regenerate a missing sequence.
Keep original roles; this preflight does not rebind or align.

### Selected original alignment

Authenticate both explicitly supplied sequence descriptors for
`structure_correspondence`, independently of whether sequence_align was granted
to this receiver. Compare exact descriptor/reference identities with the
orientation-selected query and reference. The returns adapter establishes actual
own/received observation authority; this adapter then validates the immutable
observation, source and reference payloads and exact original operation args.

Require provider `biopython.alignment`, source.artifact_ref == native_file,
one subject and one source-subject, exact ordered-deduplicated operand_refs or
the exact original-operation legacy proof, dependencies, native lengths and
recorded mode/protein model. Find exactly one original grading auxiliary with
the tool-grading media type/schema, provider and native artifact identity;
require its identity == grading_file. Preserve the outer original scores object
unchanged. Validate the full native/sheet using A's existing snapshot validator;
do not align or build a replacement grading artifact.

Decode old alignment/grading JSON strictly but do not require the new protein
canonical encoding: ToolRegistry originally used `domain.canonical`. FileIdentity
authenticates the original bytes. New protein map/sheet/component JSON uses
`execution_contracts.canonical`. Never silently reserialize old artifacts into a
different claimed identity.

Return exactly `{descriptor, native_result, pairwise_sheet}`. Healthy native
no-alignment remains a valid zero correspondence. Partial/corrupt traceback is
`invalid_traceback`, not zero. C/A consume the full snapshot and original maps
to check all columns, symbols, gaps and outside-local-alignment positions.
Their existing re-extraction occurs before their explicit detached role rebind.

### Comparison and native-job inputs

`resolve_comparison_operands` validates CompareRequest and authorizes its exact
selected original files. Explicit-map mode requires its explicit retained map,
not an inferred alignment. Retained-alignment mode uses the preceding proof.
Supplied metadata files must be explicit received inputs; a source-envelope
receipt cannot supply arbitrary semantics sidecars. A received transform uses
the next subsection. Supplied transforms retain their supplied identity and do
not require an invented prior fitted result.

Build InputFile entries in `C.required_input_files(request)` order with input_id
`input_<i>`, staged_relative_path `inputs/input_<i>` and `path` equal to the
verified absolute Store path from D392. Do not copy/stage files here. Return only
the exact explicit Store reference set used by the selected request, including
the authenticated descriptor/alignment authority operands, in stable deduplicated
order. Do not expand source auxiliary lists.

Root's 380/009 decision permits identical original paths iff full FileIdentity
agrees, while every input_id/staged_relative_path remains unique. C already
stages each entry separately. Different chains/models in one structure file
therefore need no host copying phase. Nonidentical overlapping paths and one
path claiming conflicting identities remain invalid.

`validate_protein_structure_job_inputs` returns [] for assignments without the
actual `requested_job.native_protein_structure`. For protein jobs it uses C's
exact requested-job validator, enforces known explicit input authority and
validates compare operands before reservation. Match the supplied role/file
multiset, input identities and absolute retained paths; do not silently rewrite
selected job inputs. Inspect/extract authorize only C's explicit original
structure/metadata roles. The host can use the resolved port when constructing
a request, but validation of an already selected request preserves its order.

### Saved sheet and received transform

`validate_saved_structure_sheet_operand` is the common original-sheet custody
and bytes validator; it does not authorize a scientific invocation. Its caller
must first enforce the particular allowed use through the returns adapter.
It requires the received descriptor's exact original publication, qualified
sheet/original-components identities, actual canonical retained bytes and a
non-null baseline. The separate original-components file must exactly equal
native_baseline, with original parameters == sheet.native_request. Use B's
recorded validator; no SVD, refit or calculation. Check original mode and native
request associations. Missing bytes remain retained_artifact_missing, rather
than retroactively erasing a valid original descriptor receipt.

`validate_protein_structure_selected_inputs` validates the original results
selector/anchor. For `retained_sheet_only`, require received saved descriptor,
`recalculate`, new explicit parameters, exact original handoff association and
the original sheet pair above. If those parameters contain a received transform,
authenticate that additional transform too before D393 receives the plan.
Return only the selected reference set. Complete acquisition uses the original
qualified target/request; it adds no saved-input grant.

`authenticate_received_structure_transform` requires origin=received_fitted and
an exact non-null received_from record. Check the saved descriptor with
`use_transform`, then locate the **calculation_custody** original action (possibly
a later saved recalculation), exact components_file and calculation_id. Require
the corresponding recorded components to validate against the original sheet,
transform.state=identifiable_fit, exact proper R/t and exact fixed/moving
selections. Do not transpose, repair, refit or replace recorded components.

Separately require one actually received transform ProjectionResult containing
both rotation and translation from that same calculation/custody. Do not combine
R from one result with t from another. For values delivery, both present cells
must equal the original components and declared transform exactly. For artifact
delivery, require the received exact selected-table grant, authenticate only
that table's FileIdentity/rows and original projection membership, then compare
the same selected values. Reading this authorized operand table does not claim
that its unseen values were previously delivered as numerical knowledge or
create credit. A saved descriptor, components locator, calculation identifier,
source handle, or a different transform projection is insufficient.

Return the already recorded ProteinStructureComponents unchanged. The host
passes only the exact received_transform_sheet/components files to C. For a
saved recalculation, D393 still makes the one explicitly selected calculation;
authority validation itself makes none.

## 7. Failures and state/credit behavior

Use one proposed `ProteinStructureOperandError(ContractError)` carrying an A
StructuredIssue, with `str(error) == issue["code"]` and
`detail={"protein_structure_issue": issue}`. Construct the issue with A's
existing `issue` helper. This adds no IssueCode, free-text finding or scientific
confidence field. Internal EpisodeReturnRecords errors are mapped deliberately,
not exposed as arbitrary science issue strings.

| Condition | Existing code / fields |
| --- | --- |
| Missing descriptor/sequence use or no actual frozen delivery | sequence_not_received; authority / descriptor |
| Observation not actually owned/received | alignment_not_received; authority / alignment |
| Wrong original commission, run/path/prefix, selector, custody or frozen form | original_commission_mismatch; authority / receipt or request |
| Altered immutable reference/source payload | conflicting_identity; authority / descriptor or file_identity |
| Actual retained bytes absent | retained_artifact_missing; input / file_identity with applicable role |
| Actual digest/length differs | input_digest_mismatch; input / file_identity with applicable role |
| Different original map/sequence/selection | sequence_artifact_mismatch; sequence / sequence or residue_map |
| Wrong alignment operands/orientation/native source association | alignment_operand_mismatch; correspondence / alignment |
| Invalid native traceback/sheet | invalid_traceback; correspondence / traceback |
| Saved descriptor not received or requested use absent | saved_sheet_not_received; authority / descriptor |
| Transform projection/values/calculation do not match | invalid_transform; authority / rotation or translation |
| Well-formed request lacks the selected available field | selected_field_unavailable; projection / projection_fields |
| Malformed closed shape, wrong format or path | invalid_schema, unsupported_format, invalid_output_path respectively |

All unused role/position/atom/correspondence fields are explicitly null. These
boundaries return no fake numerical rows. At pre-dispatch/commission the existing
invalid feedback outcome has no completed own-action observation, no native
measurement and no forecast. Within an already selected result collect, root
converts an operand error to the existing D391 ProteinFailureReturn with the
actual custody when available and exact projection_id when applicable, preserving
other valid captured/projection data. Do not make a missing retained input cause
reacquisition, a new job or a retry.

No turn or observation is added for any check, parse validation, internal lookup,
descriptor construction or report construction. Original and saved calculations
retain their own existing result action; saved work earns no fresh acquisition
credit. Original forecasts, completed action gains and closed histories remain
unchanged. Root continues to use the existing validated practical endpoint and
immediate exact-zero future band for a completed original assignment, including
explicit requested unavailability; status alone is not completion.

## 8. Named root/shared edits

| Existing consumer | Exact change |
| --- | --- |
| `WorkflowServices` | Add required `authenticate_structure_alignment_operands(context, arguments) -> {query: descriptor|null, reference: descriptor|null}`. Validate both operands independently; null means truly ordinary. Obtain the bound protein returns owner from the existing execution binding; missing owner on a protected operand fails. |
| `ScientificProcessEpisodes.execute` | Inside its existing ValueError feedback path, immediately after exact selected-tool schema validation and before execute_tool, call that service for sequence.align. For execution.estimate with tool=sequence.align call it on arguments.arguments. No schema/algorithm/gap/settings or root-catalog change. |
| `ExecutionEpisodes.prepare_assignment` | For launch/resource requests, run the exact protein job-input validator before reservation. For results selections, validate selected saved/transform operands from the choosing parent's context. Preserve resource decision and original input values. |
| `ExecutionEpisodes._check_parent_inputs`, `initial_references` | Revalidate the original protein request against the frozen child context on construction/reconstruction; admit only the validator's selected reference set. Never use source traversal as descriptor authority. |
| `ExecutionEpisodes.__init__`, reconstruction/as_record and existing service factory | Instantiate root's actual protein result host and proposed returns adapter from the saved bound configuration. No protein-private execution loop. |
| `ExecutionEpisodes._selector`, results dispatch/preparation | Validate the exact D selector and actual target. Before D393 saved-sheet calculation, require recalculate and any received-transform grant. Pass qualified actual file identities only; 008 diagnostics cannot stand in for them. |
| `ExecutionEpisodes.fact_sources/facts`, `received_report_sources/received_report_facts` | Merge exactly D391's four schemas and original own/received facts. Avoid duplicate source keys; preserve caller's arbitrary top-level field names. |
| `ExecutionEpisodes.validate_received_report`, `received_form_references` | Invoke exact original return validation/admission; add only the explicit returned grant set. Generic result source handling is not descriptor admission. |
| `ExecutionEpisodes.resolve_received_reference` and `resolve` | Run protein family denial/permission checks before generic Store/reference fallback in both paths. Recognize protected sources/references/retained artifacts and semantic locator keys without treating locator existence as data receipt. |
| `ExecutionEpisodes._received` and final source-family fallback | Include native_protein_structure_bundle_v1 among specialized native-result source versions that cannot be parsed as generic byte-window results or accepted by generic result fallback. |
| `EpisodeReceipts.receive` | Add native_protein_structure_bundle_v1 to the protected episode.execution_result versions. Source receipt alone must not enqueue bundle/input/auxiliary refs. Explicit authenticated descriptor operands still enter the ordinary receipt mechanism. |
| `communication._compile_closed_schema` | Register only the four exact top-level D391 schemas. D391 currently omits x-source in report_schema; compare against a detached copy with precisely the selected x-source added by the existing fact-form expansion boundary. Do not modify D391 schemas or allow arbitrary $ref/$id. |
| `communication._validate_form_semantics` | If semantic traversal of these self-contained resources is added, resolve only local references within the exact registered resource. D391/A reference types currently use patterns rather than semantic format annotations; family return validation must explicitly authenticate them. Traversal alone is not authority. |
| Root protein results completion/proof consumers | Original requested delivery, actual completed action, partial failures and saved calculation retain the current practical endpoint semantics. Do not alter controller/scientific credit. |

ToolRegistry `_alignment_arguments`, `_estimate_native`, `_prepare_alignment_async`,
`_align_one`, sequence_ops.align_pair and the ordinary sequence worker need no
algorithm or public-contract edit. They are acceptance-test consumers of the
new **earlier** child-context preflight. A hook inside `_sequence` alone lacks
that receiving context and does not satisfy the boundary.

## 9. Verification cases for the coding assignment

Run future tests through local_jobs at 20 GiB RAM, 4 GiB scratch, no wall budget,
zero swap, immutable executed-source snapshots; retain failures. This proposal
did not run them. Unit fixtures must use real saved runtime/Store records for
the authority being asserted, not a descriptor-only fake owner.

1. Real extraction -> actual typed return -> new selected scientific child ->
   sequence.align -> retained native/sheet -> selected compare launch -> result
   typed return. Cover local/global, both orientations and same-file two-chain
   inputs. Trace one completed own action per selected operation.
2. Both direct sequence.align and nested execution.estimate reject missing,
   wrong-use, stale, sibling, altered original request/form or post-commission
   descriptor before `_alignment_arguments`, `_sequence`, native runner or
   statistics recovery runs. Instrument these consumers to fail if reached.
   One protected operand with one ordinary operand still validates independently.
3. Ordinary DNA/RNA/protein references and ordinary estimate operands retain
   existing behavior. A structure-like label/accession on an ordinary source
   does not trigger classification; changing a protected label does not evade it.
4. Same sequence/length with different reference, source, map, chain, model,
   TER segment, insertion code, basis, symbol/variant/CA choice or semantics
   declaration fails. Exact native original map survives role rebind; every
   field except the declared operation-local role stays identical.
5. Full run/path/scope/assignment/knowledge-manifest checks; immutable form/facts
   and original commission changes reject. Delayed report with an earlier
   decision index but absent frozen report digest is rejected. Missing historical
   prefix is explicit failure. Multiple ancestor boundaries and redelivery use
   their respective original prefix. A sibling result received through the
   actual parent before the next child is valid; direct sibling visibility is not.
6. Own completed alignment versus actual child-delivered observation are tested
   separately. Wrong original_operation_key, reads.align substitution, missing
   ToolRegistry row, incomplete runtime action, modified outcome or forged
   source/observation hashes fail. A source-only return does not carry observation
   authority. Correct legacy source without operand_refs needs its exact original
   sequence.align action.
7. Exactly one original full grading artifact, exact provider/native identity,
   full sheet equality, native lengths/mode and original traceback are checked.
   Genuine no-alignment remains zero; a corrupt aligned traceback is invalid.
   Native symbols outside local traceback come from the original sequence files.
8. Missing retained file and changed bytes/length remain distinct and do not
   trigger capture/producer/network/launch/aligner calls. Validate replay after
   deleting producer directories. Source and descriptor authority is not erased
   merely because a file is later lost.
9. Recalculate only from actual received saved descriptor and exact original
   sheet/baseline pair; changed parameters create separate components. Patch
   calculator/SVD/native calls to fail during receipt/operand checks. D393 alone
   performs the explicitly selected calculation. Test both 008 diagnostic-only
   cases and false/true return_saved_sheet with exact 009 use order.
10. Received transform requires one matching delivered R/t projection, exact
    later calculation custody when applicable, identifiable_fit and exact
    selections. Saved descriptor alone, aggregate-only/R-only return, wrong
    calculation, sibling/later transform, mismatched table bytes or a reflected /
    transposed matrix rejects. Selected exact-table use works while numerical
    knowledge/credit remains distinct from its descriptor receipt.
11. No recursive grant from source, source auxiliaries, provenance components,
    raw result custody, failure locators, selected coordinate identities or an
    artifact table's hidden descriptor. Own source-only and old expanded
    receipt cases are denied at both shared resolver paths. Independently
    explicitly delivered identical artifact content remains independently valid.
12. Actual enclosing parent form uses arbitrary field names and exact four
    registered schemas, including multiple self-contained resources. Reject
    changed schema/source, extra fields, floats/bools as counts, nonfinite values
    and nonexistent original references. Do not change literature form behavior.
13. Partial scientific failures preserve other requested facts; completion uses
    original assignment delivery and exact-zero practical semantics. No extra
    forecast/action/credit, no reprice of original baseline, no root science
    exposure and no new three-slot/episode/monitor itinerary are introduced.

Hand-checkable retained example for the final integration: original fit over
four unchanged noncollinear points gives R=I, t=0; a held-out fifth site differs
by 2 Angstrom, so the selected one-site distance is 2, SSE is 4 and RMSD is 2
with denominator 1. Recalculation over all five gives RMSD sqrt(4/5), preserving
the original baseline. This is the existing synthetic 380 example, not a new
execution result from this planning lane.

## 10. Decisions and remaining approval items

Root resolved and permanently recorded two issues during this trace in 380/009:
identical original input paths require identical full FileIdentity, and the
saved-sheet boolean grants exactly the three ordered retained-data uses. Root
reported a retained failing same-file/two-chain counterexample and a C repair;
this lane did not execute or verify root's C tests.

The remaining genuine root decisions are:

1. Approve the three concrete original-result host ports/read view in section 3
   and one exact ordinary source payload/helper in section 4. The host's durable
   receipt/index layout remains private; these exact required values cannot be
   replaced with source presence or a loose dictionary of artifacts.
2. Approve protection of immutable feature/product ancestry in the classifier.
   ToolRegistry can read a feature through subject_ref and products have actual
   parent_refs. Proposed rule: a derivative of a protected structure reference
   needs its own exact descriptor; the current contract publishes descriptors
   only for original references, so unsupported derivatives fail
   sequence_not_received. Ordinary ancestry stays unchanged. This closes a
   wrapper bypass without inventing derivative structure maps or a new mode.
3. Approve the deterministic first-valid-received authority-witness rule when
   the public four-argument aligner names a reference with several independently
   valid original descriptor deliveries. No scientific value/use union or
   arbitrary source receipt is selected; exact explicit descriptors still govern
   compare requests. Alternatively require unique eligible original descriptor
   and return conflicting_identity. The public aligner has no descriptor argument.

The compiler's x-source normalization and explicit host identity checks are
implementation obligations, not new scientific schema choices. No unresolved
service credential or scientific algorithm blocks this boundary. Coding is
withheld here as assigned until root approves the boundaries; no task completion
or inventory credit is claimed by the existence of this proposal.
