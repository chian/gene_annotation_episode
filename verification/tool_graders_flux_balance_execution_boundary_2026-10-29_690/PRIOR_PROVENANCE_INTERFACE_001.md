# FBA prior-provenance boundary proposal, 690/001

Source-only proposal for root's next implementation contract. This is not a
goal or scope amendment and grants no runtime authority. No application import,
test, native invocation, download or production edit was performed by690.
The eight producer roles remain unchanged. Root owns adoption;689 has released
the reader at `b3badf2ff361133fb36a1146d0ac0d9754e3df63406290cfe8bd50c070016c62`.

## Demonstrated source gap

`flux_balance_readers._bind` accepts a File only if it equals one of
`files.values()`. `parse_fba_capture` builds that registry solely from eight
native payloads. `_selected_request` calls `_record` before checking the raw
requested-job digest. Consequently a legitimate previously received File in
`model_input.acquisition_receipt_file` or a requested bound's `source` fails
binding even when its original selection and native output are otherwise valid.
`flux_balance_contracts._bundle_relationships` also requires every typed File
to appear in `retained_files`. None of those checks supplies Store/episode
authority; adding arbitrary caller files to the registry would not supply it.

## Exact proposed parser input

```python
parse_fba_capture(payloads: dict, *, expected: dict,
                  prior_sources: list[dict] | None = None) -> dict
```

`payloads` remains exactly `FBAArtifactPayloads` with eight roles. `expected`
remains `FBAAttemptIdentity`. `prior_sources` is a non-JSON bytes boundary:

```text
PriorSourcePayload = {file: File, bytes: bytes}
prior_sources = [PriorSourcePayload] or None
```

Every row is closed. None and [] mean no supplied prior bytes. There is no
filesystem path, source authority flag, ninth role, schema-inference callback,
native solve, acquisition or Store access in this input. The host contract below
is a separate port. A prior file can have multiple selected uses.

Only literal typed File values at these original selected-request paths are
eligible external inputs:

1. `/requested_job/native_flux_balance/model_input/acquisition_receipt_file`.
2. `/requested_job/native_flux_balance/constraints/<i>/lower/source/file`.
3. `/requested_job/native_flux_balance/constraints/<i>/upper/source/file`.

Null fields add nothing. The objective has only kind/reaction_id; solver options
are numbers/null. Neither currently introduces an additional prior File field.
Software FilePin paths are execution pins and never enter this source registry.
Opaque evidence dictionaries cannot declare input authority. Do not scan them
for dictionaries that happen to resemble a File.

Validate the original envelope/attempt and compute
`execution_contracts.digest(raw['requested_job'])` against the expected digest
before allowing any prior input into address binding. Do not change the raw
object or require the retained-address validator to accept producer role-shaped
addresses before ordinary binding. Existing role-address fixtures remain valid.
Derive the external allowlist from the exact original fields above. An external
input cannot enlarge it. A mismatch of original attempt/digest remains a conflict
even when every extra file is valid.

For an eligible supplied row, validate the shared File shape, exact equality to
the selected File (including artifact_ref and format), immutable bytes type,
SHA256 and length. Validate reference uniqueness and reject conflicting aliases.
If it coincides with a native-role File, it cannot replace that role's identity,
format or bytes. A redundant same-identity row is unnecessary and must not
introduce a second retained-file identity. Different Files sharing an artifact
reference remain an explicit conflict, consistent with the existing registry.

For a bound SourceLocation, validate its original pointer using the existing
RFC6901 grammar. Empty pointer addresses the complete retained file, including
a non-JSON file. A nonempty prior pointer requires supplied finite JSON decoded
with duplicate keys/nonfinite tokens rejected and the exact pointer resolving.
Do not guess XML, CSV or other address grammars from a filename. An acquisition
receipt File without a SourceLocation needs byte-identity validation; its arbitrary
payload is not parsed as an authenticated provider protocol.

Add only verified, selected prior Files to the address registry and
`ParsedFBABundle.retained_files`; preserve exact selected SourceLocations and
File objects through binding. Shared sheet/calculator schemas and arithmetic do
not change. Native-role files keep their original role lookup. Prior identities
need a separate internal lookup rather than invented role names.

### Explicit partial and failure behavior

Use existing Issue codes and exact original locators. Missing supplied bytes
for a selected prior File produce `artifact_missing`; malformed rows/pointers
produce `schema_invalid`; wrong bytes/identity or conflicting aliases produce
`artifact_identity_conflict`. Unselected extra rows cannot become retained
scientific operands; report a located schema error. Native-role data independent
of the invalid source survives. Never substitute zeros, replace a prior source
with the selected-request artifact, insert a local path, or silently omit the
original source from selected-request bytes.

Under the present closed bundle contract, an unresolved required source cannot
appear as a verified retained File. Preserve exact selected-request bytes in
the acquired native artifacts and qualify request association/application as
unavailable rather than certifying the complete original delivery. Existing
`_selected_request` failure behavior may therefore leave `original_request_file`
null and constraint/objective application unknown while independent snapshots
and numerical checks survive. This is a qualification of the usable bound
record, not a statement that the originally selected source never existed.
If root elects finer independent request-field recovery, it needs a separate
explicit shape decision; do not erase provenance to fake that recovery.

For original model custody, when the original selected
`model_input.artifact_ref` is nonnull, compare it with the retained
`original_model.artifact_ref` as well as the already required selected SHA,
size and format. It is the same bytes under Store's content-addressed identity.
Null remains null for existing supplied-byte/native fixtures; the parser cannot
invent a Store identity for that original selection. The real episode host below
requires received input authority separately.

## Exact proposed host-only input binding

Reuse the existing launch `immutable_input_versions` array; it already admits
typed `{reference, version, content_sha256}` rows and remains in the original
launch assignment. No provenance metadata is added to or rewritten inside the
selected FBARequestedJob. The resource child obtains the exact original launch
selection through its authenticated parent commission, as `_check_parent_inputs`
already does for NMF. Results obtain it through the original source-action and
handoff proof, not through a current unrelated selection.

```python
bind_flux_balance_job_inputs(store, context, assignment, *,
    input_versions: list[dict], reference_access) -> dict  # FBAInputBinding
validate_flux_balance_input_binding(store, value: dict, *,
    context, assignment, input_versions: list[dict], reference_access) -> dict
```

Both functions perform metadata/record authority checks only, no solver call,
scientific decoding or new receipt grant. Their proposed closed output is:

```text
FBAInputBinding = {
  version: 'flux_balance_input_binding_v1',
  run_id: str, episode_id: str, request_sha256: hex64,
  assignment_sha256: hex64, scope: existing validated Scope,
  inheritance_manifest: existing EpisodeReceipts manifest,
  input_versions: [existing InputVersion],
  model: FBAReceivedFile,
  prior_sources: [FBAReceivedFile]
}
FBAReceivedFile = {
  file: File, path: absolute Store-derived path,
  uses: [FBAInputUse], witnesses: [FBAInputWitness]
}
FBAInputUse = {
  request_pointer: JSON Pointer to the original selected File or model_input,
  source_pointer: JSON Pointer|null
}
FBAInputWitness = {
  reference: existing artifact/source reference,
  record_sha256: hex64,
  artifact_field: null|'artifact_ref'|'text_ref'|'request_ref'|'stdout_ref'|'stderr_ref',
  input_version: existing InputVersion
}
```

Here request_sha256 is `digest(context.request)`, assignment_sha256 is
`digest(assignment)`; the requested-job digest remains in FBAAttemptIdentity.
The model has one use at `/native_flux_balance/model_input` relative to the
selected requested job. Prior `request_pointer` values use the same relative
base, e.g. `/native_flux_balance/constraints/0/lower/source/file`; the parser's
locators above additionally include its retained envelope `/requested_job`.
`source_pointer` is the original bound-source pointer or null for a bare File.

Authenticate BindingContext/episode/scope and frozen receipt inheritance using
the same complete lineage checks as `expression_nmf_operands._received_context`.
Do not copy that private helper as a new scoring or receipt implementation;
extract a narrowly shared received-input authority helper or use the existing
EpisodeReturnRecords/EpisodeReceipts primitives directly under one owner.

Each witness must be explicitly present in original input_versions and actually
received under that authenticated frozen prefix. Enforce existing protected
reference access and scope. A direct artifact witness has null artifact_field
and must equal File.artifact_ref. A source witness names an actual Store source
record and exactly one of its declared artifact fields whose value equals that
File.artifact_ref. Its digest is over the exact saved Store record, preserving
provider, origin, accession, request_ref and other original relationships.
Source metadata can be frozen as existing canonical control bytes for replay;
it never becomes a new native role or model-facing information.

Require at least one valid explicitly selected witness for every file. Do not
search all Store source records for a convenient owner. A received source grants
only the exact selected file/field use here, not all linked artifacts or its
parent's receipts. A direct received artifact establishes byte custody only;
it does not establish a provider acquisition or successful native operation.
Where provider-specific receipt meaning is claimed, retain and use that existing
provider's validator separately. A File labelled a receipt cannot create one.

Use native_file_capture._metadata for exact Store identity/size and the canonical
Store artifact path, and retained_native_file when reading bytes. For the model,
selected FilePin.path must equal that canonical received path. Preserve its
original_loader_selection/repository_identifier as supplied; no local path is
substituted for acquisition identity. The local producer consumes the actual
retained model file; it does not perform repository acquisition.

This binding is frozen before selected launch and is revalidated against the
same original context/selection at start and result capture. It is internal
transport, not decision prompt content. The bounded result worker receives only
the selected retained File/path list with this binding's identity. It verifies
bytes and constructs the parser's `{file,bytes}` rows. The parser never accepts
the binding as proof of authority and never grants references to a parent.

## Necessary focused cases

Reuse the existing73 reader cases; do not rerun native solves. Add external
acquisition receipt, two bounds sharing one external JSON source, escaped JSON
Pointer, exact null/empty source cases, missing prior bytes, wrong SHA/size,
unselected extras, duplicate/conflicting aliases, native-role collision, absent
pointer target, nonempty pointer into non-JSON, original digest mismatch,
nonnull model artifact-ref mismatch, and unchanged caller bytes. Verify each
valid result uses the existing sheet and calculator and saved-only recalculation.
Host cases separately prove received artifact, received selected source-field
witness, forged/unreceived/out-of-scope/protected witness, unrelated source
field, changed metadata, changed original input_versions and no receipt grant.

No case in this proposal has been executed by690. Root's later adopted contract
and the assigned owners' actual evidence determine implementation status.
