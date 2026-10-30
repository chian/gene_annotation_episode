# Additive population, publication and reference boundaries

The goal attachment remains authoritative. This closes concrete implementation
interfaces discovered while consuming the accepted185 contract. It preserves
the185 files and shared115-definition schema. It does not claim an implemented
host binding, authenticated reference dataset or live service.

## Saved populations

C selects among explicitly saved, compatible view/population bindings and
saved reference sets. Native formula checks retain the native original
population. The earlier phrase about a different explicitly saved genome
subset does not define creating an arbitrary subset of one full view.
Do not add a subset type or substitute a denominator without selecting and
binding the matching numerator records. Arbitrary subset construction is
unsupported by the current closed contract; do not describe it as implemented.

## Requested count versus structural partial return

P's canonical requested-form renderer puts minItems=0 and maxItems equal to
the field's explicit expected_cardinality. The original exact cardinality and
availability requirement remain in x-bvbrc-comparative-systems metadata.
P returns status=ok only when every original selector meets those requirements.
Too many matches are ambiguous/incompatible, never truncated. Fewer matches
remain partial with the exact missing requirement. Wrong values, extra fields
and changed selector metadata are still invalid. This lets the existing host
validate the entire structural form even for a partial result; it does not
require bypassing that validation or weakening practical completion.

## Native provider records and generic publication records

ProviderResultV1 remains the exact P return. Its RequirementV1/DiagnosticV1
records do not have the existing generic AppService AcquisitionRequirement/
Diagnostic shapes. Passing them directly to AdapterResult is incorrect.

I owns a new module, bvbrc_comparative_systems_publication.py, in addition to its
previously named files. It supplies these deterministic storage conversions:

```python
def encode_comparative_publication_result(result: dict) -> dict: ...
def decode_comparative_publication_result(
    adapter: dict, *, sheet: dict | None, components: dict,
) -> dict: ...
```

Encoding validates the original ProviderResultV1, preserves its identity,
status, facts and sheet, and produces the normal host-facing result fields.
Its components value is this exact storage object:

```text
version: "bvbrc_comparative_systems_published_components_v1"
calculations: ComparativeSystemsComponentsV1 | null
missing_requirements: the original RequirementV1 array
diagnostics: the original DiagnosticV1 array
```

There are no other fields. The ordinary existing components_content binding
retains this object, including when calculations is null. The numerical sheet
still has its separate sheet_content binding. Other providers' storage remains
unchanged. No generic AppService schema or episode structure change is needed.

The host-facing missing_requirements map each original record as follows:

* requirement_id stays exact;
* role is required_input_role;
* source_refs stay exact;
* reason_code is code;
* kind is output_bytes for native-document/report roles, scientific_metadata
  for supplemental records/references/population/producer roles, and
  parser_binding for format incompatibility or an unavailable parser binding.

The native role and code remain retained in the storage object, so this generic
classification cannot erase their meaning. Define the complete finite role/code
mapping in ordinary functions and reject an unhandled value; no guessed string
heuristic or model interpretation is needed.

The host-facing diagnostics retain code and source_refs as evidence_refs.
Map decode to native_decode, association to association, and population,
calculation and projection to publication. path is the exact pointer
/diagnostics/{index} in the stored object. severity is error for an invalid
provider result, qualification otherwise. This publication classification is
not a numerical score or a replacement for the retained native diagnostic.

Decoding receives the authenticated generic saved adapter plus its two exact
content values. It validates the wrapper, reconstructs ProviderResultV1, and
verifies that encoding its native requirements/diagnostics exactly reproduces
the generic saved fields. The result goes to P's saved-projection validator
with the original numerical calculations object. No reparse, recalculation,
network or model call occurs. Preserve unknown/partial results and all native
diagnostic locations. Verify round trips for ok, partial and invalid results,
including null sheet/calculations and tampered native/generic metadata.

## Explicit source materialization

OriginalRequest.task_ref is OriginalTask.submission_receipt_ref;
request_source_ref is submission_source_ref. Native task_id remains checked
through artifact/task association. The fields are not interchangeable.

I authenticates the selected Data source using BVBRCDataHost.read, obtains its
already retained exact bytes, and passes the wrapper and byte map to P/D. Each
raw binding must equal an explicitly selected bundle supplied_contents binding
or supplied_scientific_metadata.content binding. The source, raw artifact,
digest and byte count must agree. SourceEvidence pointers and materialized
producer values likewise remain exact. No automatic discovery or acquisition
is added to this collection step.

No immutable Data snapshot or original remote-task group attestation format is
currently bound. Caller labels cannot establish either. D retains the requested
selection but derives unknown/unverified qualifications when proof is absent.
Single complete exact responses establish only their observed query population.

## Reference membership proof still required before I closure

ReferenceMembershipV1 parameter arrays do not authenticate themselves. For
basis=supplied_data_api, the concrete input must be selected qualified
pathway_ref/subsystem_ref records supplied through D, with exact source
locations, entity/map context and full-population qualifications. Independent
multivalued role ID/name arrays are never zipped. Unknown releases stay unknown.
Other basis values cannot silently authorize a fabricated native reference
format or a remote-service attestation.

P may implement native-only work independently. The remaining precise mapping
from these reference records to each requested membership must be closed before
I is assigned that portion; unresolved membership returns the existing missing
requirement. It is not counted as a completed reference-backed calculation or
production capability merely because C accepts a synthetic reference fixture.
