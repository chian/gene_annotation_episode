# Authoritative provider-selection correction — 177/003

This additive correction supersedes the exact-only document-selection examples
in handoff001. It incorporates root's complete
`PREACQUISITION_SELECTION_HANDOFF_019.md`, which was read after root identified
the circular dependency. A future frozen results assignment cannot name the
source/artifact identities that its own later acquisition will create.

The immediate numerical A/B/C interfaces do not depend on acquisition and are
unchanged except for interface revision002. **D/F are not ready for assignment**
until their complete consuming contracts are specified against accepted176/178
and019 changes. This document records the mandatory selection requirements;
it is not an implementation of those downstream paths.

## 1. Both existing native selection variants must survive

`NativeDocumentSelectionV1` in the proposed ProviderParametersV2 means the
accepted019 closed union, not the pre019 exact-only schema:

```text
NativeDocumentSelectionV1 = NativeExactSelection | NativeRequirementSelection

NativeExactSelection = {
  document_id:string,
  source_ref:string,
  raw_artifact_ref:string,
  role:"proteome_native_projection",
  declared_format:HostDeclaredFormat,
  source_contract:NativeSourceContract
}

NativeRequirementSelection = {
  document_id:string,
  requirement_id:string,
  role:"proteome_native_projection",
  declared_format:HostDeclaredFormat,
  source_contract:NativeSourceContract
}
```

All listed fields required, additional properties forbidden. The requirement
variant has neither future identity field. Existing exact-source callers and
saved historical members remain compatible.

## 2. The new directional selector has the same disjoint choice

```text
DirectionalDocumentSelection = DirectionalExactSelection | DirectionalRequirementSelection

DirectionalExactSelection = {
  document_id:string,
  source_ref:string,
  raw_artifact_ref:string,
  role:"proteome_directional_report",
  report_key:string,
  declared_format:DirectionalDeclaredFormat
}

DirectionalRequirementSelection = {
  document_id:string,
  requirement_id:string,
  role:"proteome_directional_report",
  report_key:string,
  declared_format:DirectionalDeclaredFormat
}
```

`report_key` and `document_id` are predeclared logical labels, not invented
receipt identities or evidence of execution. Requirement ID must reference the
existing parent-declared ResultSelector requirement. Actual source identity is
resolved only from the uniquely matching authenticated bundle member. No
selection variant predicts hashes or source names, edits the assignment after
freezing, or borrows a different child's acquisition.

## 3. Host custody and saved replay

Use019's optional `ArtifactMember.requirement_ids`: unique nonempty strings
copied from the actual selected download operands, compared with the actual
receipt's array, and preserved by bundle construction. Historical absence is
valid but establishes no requirement membership. Do not synthesize this field
from filenames, requested labels or current artifact contents.

A requirement selector matches only actual members containing its requirement
ID. Zero matches is missing; more than one is ambiguous, including repeated
representations. Do not choose newest/first/largest/most complete. A unique match
then passes exact role, declared-format, original-task, range, completeness and
byte-digest checks. Detect duplicate actual source selection across both native
and directional logical document selections; do not count one report twice.

Preserve the existing `input_resolution` selection-index→actual-content→result
mapping. Add a reviewed directional selection kind in that mapping when D is
assigned; do not invent a redundant identity store. Validate every directional
ReaderResult source against its actual resolution content, format and logical
selection. Exact-source selectors also retain exact-identity checks. Primary
legacy source resolves from the actual selected primary document, never an
assumption that every selection contains `source_ref`.

Requirement-based saved-custody validation requires the actual authenticated
ArtifactBundle. Preserve019's optional bundle argument on
`validate_saved_projection`, require it for the requirement variant, and pass
the already authenticated/decoded bundle from the actual return binder. Check
bundle contract/hash/task, unique requirement membership, source content,
role/format and actual transfer completeness. This verification does not invoke
the scientific parser, constructor, calculator, downloader or network again.

Saved-sheet arithmetic remains possible without an acquisition bundle and
makes no custody claim by itself. Original-input and execution-occurrence joins
remain missing unless their distinct authentic evidence is supplied; neither
new requirement membership nor transport ownership establishes them.

## 4. Concrete downstream verification obligations

Freeze a genuine assignment with a directional requirement selector before
download; acquire through the existing actual host; publish the report through
reader/sheet/calculator and typed return. Then verify missing/ambiguous membership,
wrong role/format/task, member/receipt/operand disagreement, duplicate actual
source, incomplete bytes, wrong hash, nonzero range, saved-membership/resolution
tampering, v1 exact compatibility and replay without download/calculation.
These are future D/F obligations. A/B/C may proceed from saved ReaderResults
without this future deployment or host-custody work.
