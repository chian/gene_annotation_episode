# Approved boundary refinements and typed sequence ancestry

2026-10-27. Additive to PROPOSED_BOUNDARY_001.md; read this note with that
proposal. No production/test code is implemented by this packet.

Root reviewed the complete proposal and approved:

- the exact three root-host port names and detached read view in section 3;
- deterministic first eligible actually received original descriptor as an
  authority witness, without grant union;
- feature/product ancestry protection restricted to the actual typed immutable
  links below;
- the proposed ordinary source provider, accession, version and timestamp,
  with the exact auxiliary ordering/exclusions below.

These decisions resolve section 10's three approval items. There is no remaining
scientific or authority-policy decision blocking the two proposed modules.
Root will expose its exact source-payload publisher/validator helper; its private
module/helper name is a root implementation dependency, not permission to infer
a different payload. Root owns shared host edits. Fresh coding contexts will own
the two new modules separately, with nonoverlapping test files assigned by root.
This planning lane remains read-only outside its 394 packet.

## 1. Exact original source auxiliary ordering

Section 4's source payload is approved, with this definition of
`ordered_unique_actual_captured_and_prepared_refs` replacing its broader prose:

1. Observed capture file artifact references in original manifest order, then
2. the original result-worker `native_result_file`, `sheet_file`, and
   `components_file` artifact references, in precisely that order, for each
   identity that was actually retained.

Deduplicate by exact artifact reference, preserving its first occurrence.
Missing files create no auxiliary entry. Preserve actual observed mismatching
capture files for diagnosis, using their observed identities, not their absent
claimed bytes. Exclude host result-worker plans, host execution receipts, host
logs/control artifacts, every projection, custody object and descriptor. This
exclusion concerns the host result worker; it does not erase declared original
C manifest files, which remain captured native provenance in manifest order.
Saved recalculation never mutates this original source payload.

The source still has the section 4 exact provider/accession/version/time fields;
its main artifact is the actual captured bundle. Later calculation and table
identities are available through the result-host receipt metadata, not appended
to the original source. An auxiliary entry is no grant to read or use it.
380/008's diagnostic-only restrictions remain unchanged.

## 2. Why feature and product records are relevant here

These are the existing constructors and consumers; no new derivative mode is
proposed:

| Existing path | Actual immutable relationship |
| --- | --- |
| `domain.RECORD_SCHEMAS['feature']` at domain.py:249 | One `subject_ref`, plus segments/strand. |
| `domain.RECORD_SCHEMAS['product']` at domain.py:251 | Nonempty `parent_refs`, its own `sequence_ref`, and optional native mapping. |
| `ToolRegistry._derive` at tools.py:2046; records at tools.py:2137 | `sequence.view`, `sequence.translate` and `genes.predict` create a feature whose subject is the selected subject, then a product whose parent is that feature. `sequence.view` is the concrete protein-capable wrapper route. |
| `Store.commit_reasoning` at state.py:1794 and sections at state.py:1815 | `structural_proposals` create reasoning-origin features through Store.put; these also have the exact selected subject_ref. No product is constructed by this reasoning section. |
| `Store.put` at state.py:1502 | Immutable identity includes origin and complete stored payload. Feature/product payloads carry their typed links. |
| `Store._validate_record` at state.py:925 | Feature parent and every product parent must be input/feature/product/reference/read_subject. Coordinate and native mapping checks remain existing Store responsibilities. |
| `ToolRegistry._sequence` at tools.py:321 | A feature reads its subject recursively and slices/strands it. A product reads its own sequence artifact directly, so checking only `_sequence`'s read recursion would miss its parents. |
| `ToolRegistry._alignment_arguments` at tools.py:789 | Reads both actual operand sequences; `_estimate_native` at 796 and `_prepare_alignment_async` at 810 both call it. |

`Store.sequence_mapping` validates or returns a nucleotide/amino-acid symbol
mapping. It neither carries original extraction authority nor supplies a
structure-residue descriptor. Do not use a matching mapping, a matching sequence,
or empty genomic footprint as a substitute for the original descriptor.

## 3. Exact classifier traversal

The existing proposed public port remains:

```python
def is_protein_structure_sequence_operand(store, reference_ref: str) -> bool: ...
```

This is a metadata classifier for the required existing preflight and existing
reference-resolution guards. It is not a generic provenance crawler or a new
runtime decision/action. Its only record edges are:

```text
feature.subject_ref                 -> sequence subject
product.parent_refs[i]               -> sequence subject, in stored array order
reference.source_ref                -> terminal source
```

Here a sequence subject must be one of `input`, `read_subject`, `feature`,
`product`, or `reference`. Inputs and read subjects are terminal ordinary
subjects. At a reference's terminal source, classify the protein family using
the actual immutable source payload's `provider == 'episode.execution_result'`
and `version == 'native_protein_structure_bundle_v1'`. That family marker is a
reason to require authentication, not proof that an extraction succeeded. A
wrong operation, missing original receipt or fake reference under that family
must never become an ordinary reference.

For each visited feature/product/reference/source, require the existing record
kind and its ordinary immutable Store identity: strip only id/record_type/origin
and compare `domain.identity(kind, {'origin': origin, 'record': payload})` with
the stored id. The existing `alignment_site_native.immutable_record` implements
this identity rule and can be reused with deliberate protein error translation.
Validate the typed link shapes using the existing record schema; do not invoke
Store._validate_record, which would read sequence bytes and recursively perform
unrelated Store validation. Do not require native `origin='tool'` for a feature:
reasoning-origin features are valid existing constructors and need this check
too. The original protected source/reference origin and full payload are proved
later by the operand authenticator.

Use an iterative depth-first traversal with per-call active/completed sets and
memoized protected/ordinary results. Visit the single feature edge and all
product parents in their original order; combine only the classification with
logical OR after validating every typed parent. A repeated completed parent in
a DAG is valid. An active ancestor encountered again is a cycle and fails;
never return ordinary because a cycle was skipped. No arbitrary recursion-depth
limit, persistent cache or scientific selection is introduced.

Missing required links, missing linked Store records, wrong target kinds and
identity conflicts fail before dispatch. A malformed closed link shape uses
`invalid_schema` at authority/descriptor. An actual missing record, wrong kind,
cycle or immutable-identity contradiction uses `conflicting_identity` at
authority/descriptor. Other issue fields remain null, as in proposal section 7.
These states cannot be converted to `False`/ordinary. A normal unrelated input
or ordinary reference, including normal derivatives whose complete parent DAG
is ordinary, returns False and follows existing tool validation unchanged.

Do not traverse context_refs, mapping_source_ref, mapping.path, footprints,
source parents/operand_refs/auxiliaries, observation dependencies, descriptors,
artifact contents, or arbitrary fields ending in `_ref`/`_refs`. Do not reverse
search Store for another record containing the same sequence bytes. Source
classification needs no native result, coordinates, map or numerical sheet.
Ordinary independently supplied material is not protected merely because its
bytes happen to equal a protected extraction.

## 4. Exactly where the unchanged descriptor is supplied

`ScientificProcessEpisodes.execute` supplies its current BindingContext and the
already schema-validated four original alignment arguments to the approved
`WorkflowServices.authenticate_structure_alignment_operands` port. This occurs
inside the existing invalid-feedback try block, before `execute_tool`, for both
selected sequence.align and the nested alignment arguments of execution.estimate.
The service classifies query and reference independently.

For an original protected reference, the unchanged StructureSequenceDescriptor
is obtained only from an actual typed received descriptor in that context's
frozen ancestry/report prefix. The parent supplies the exact original operand
references in the child's existing evidence_refs; their presence alone does not
supply the descriptor. The receiving child must inherit actual descriptor
delivery through the existing frozen knowledge manifest. The port returns the
first eligible actual received descriptor as an authority witness, requiring
`descriptor.reference_ref == the actual alignment argument` and sequence_align.
It does not synthesize an extra tool argument, descriptor, receipt or action.

For a protected feature/product argument, the original ancestor's descriptor
does **not** identify that argument. Current 380 reference publication and
StructureSequenceDescriptor validators cover the original `reference:*`, not
`feature:*` or `product:*`; no eligible exact descriptor exists for a wrapper.
Therefore the current contract rejects that protected wrapper with
sequence_not_received before ToolRegistry, including after an otherwise valid
original descriptor was delivered. This is deliberate unsupported derivative
use, not an invented derivative residue map. To use the current structure
route, the selected alignment must name the original published reference and
the child must receive its unchanged original descriptor. Neither a byte-identical
full-length wrapper nor a cropped wrapper can substitute its id into the
descriptor. No automatic input replacement occurs.

The same classifier result is used in the already proposed
NativeProteinStructureReturns.retained_reference_access / existing shared
reference-resolution fallbacks: protected wrappers cannot get an affirmative
sequence-use grant from generic Store visibility or recursively expanded old
receipts. Return False for a protected wrapper there; return None for an
ordinary family so existing behavior proceeds. Classification adds no received
references and never treats traversal as authorization. There is no added hook
inside ToolRegistry._sequence, no new generic source-scanning gate, and no change
to sequence.view/translation/gene-prediction algorithms or their constructors.

For protein comparison, the selecting caller already supplies the exact
unchanged fixed/moving StructureSequenceDescriptors in RetainedAlignmentInput.
They must match the original reference operands of the actual selected
sequence.align operation. `structure_correspondence` is checked independently
of sequence_align. Role rebinding remains only C/A's existing detached
single-to-fixed/moving step, after original map and sequence bytes agree.

## 5. Concrete additional verification cases

These cases augment proposal section 9; none was executed by this planning lane.

| Actual fixture | Required result |
| --- | --- |
| Original ordinary input; feature from that input; nested product/feature DAG with only ordinary parents | Classifier False; original alignment/estimate behavior preserved. |
| Actual `_derive('sequence.view', ...)` product whose parent feature names an unreceived protected extraction | Classifier True; sequence_not_received before `_alignment_arguments`, native worker or statistics recovery. |
| Reasoning structural_proposals feature over the same protected reference | Same denial, independent of feature origin. |
| Full-length wrapper and cropped wrapper after valid original descriptor delivery | Both denied as unsupported exact operand ids; original reference argument with that unchanged descriptor succeeds. |
| Product with one ordinary and one protected parent, or nested product/feature chain | Protected even though `_sequence` would read the product artifact directly. |
| DAG reusing the same completed ancestor through two parents | No false cycle; same classification. |
| Injected cycle, deleted parent/source, wrong linked kind, changed immutable payload, malformed parent_refs | Specific structured failure; no generic ordinary fallback. Use retained corrupted fixtures where Store's normal constructors reject such states. |
| Ordinary reference with equal sequence bytes, or unrelated context/source auxiliary pointing at protected material | Remains ordinary; no reverse artifact or generic provenance traversal. |
| Wrapper passed in query versus reference, and each inside execution.estimate | Same preflight in all four cases, with original arguments unmodified. |

## 6. Exact seam for separate fresh coding assignments

Root subsequently fixed these names and ownership boundaries:

```text
gene_annotation_episode/protein_structure_authority.py    root-owned
gene_annotation_episode/native_protein_structure_returns.py    returns lane
gene_annotation_episode/protein_structure_operands.py          operands lane
```

The root-owned `protein_structure_authority.py` contains only the detached
host read-view TypedDicts from proposal section 3 and
`ProteinStructureOperandError` with proposal section 7's exact issue/detail
shape. Both new modules import those definitions there. It owns no runtime
lookup, receipt proof, resolver, acquisition, science execution or decision.
This supersedes any implication that the error class belongs exclusively to
the operands module.

The actual existing-owner attributes are:

```python
owner.native_protein_structure_results
owner.native_protein_structure_returns
```

The first supplies the three approved host read ports. The second supplies the
approved received-authority ports to the operand functions via their existing
`returns=` argument. The returns module must not import the operands module.
Returns authenticates original actions, contexts, frozen deliveries and grant
identities using the host ports and existing runtime records; operands consumes
those authenticated values and validates the exact retained scientific bytes.
Shared root resolver wiring can call the operand classifier and the returns
ports in sequence without creating a returns-to-operands import. If a wrapper
has already been classified by that wiring, the wrapper denial described in
section 4 is applied there, rather than importing the classifier into returns.
No shared implementation file is assigned to both fresh coding lanes.

## 7. Reset and implementation handoff

After the additional constructor/consumer read, the immutable objective and
entire sixteen-principle block were reread verbatim. Then 380's original
descriptor/publication, alignment, operand ports, four fact sources, selected
projection/selector, dispatch and receipt contracts were reread, together with
008 and 009. No scientific execution or test result is claimed.

Implementers should read PROPOSED_BOUNDARY_001.md followed by this additive note.
Approved contracts are ready for root's fresh-context assignments. Remaining
work is implementation, consumer wiring and the listed verification, not another
authority policy choice. This packet earns no inventory/completion credit for
the unfinished integrated protein capability.
