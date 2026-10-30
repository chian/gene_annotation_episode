# HMMER checked-proof receipt and publication custody clarification

This permanent clarification records the concrete B implementation within
adopted scopes 001/002. Root approved the separate deterministic checked-proof
receipt identity before implementation. It introduces no replacement physical
job, mutable job status, operation alias, score, episode, polling or retry policy.
All implementation and fixture verification remain in the isolated API checkout.

## Checked receipt identity and proof custody

The semantic execution handle remains the original `provider_job`. A successful
selected status check produces the unchanged `execution_handoff_v1`, whose
`check_record_refs` contains exactly one deterministic audit identity:

```python
proof_version = 'api_search_handoff_information_v1'
preimage = [proof_version, run_id, episode_id, operation_key, status_receipt_ref]
canonical_bytes = json.dumps(preimage, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode('utf-8')
check_reference = 'handoff_receipt_' + sha256(canonical_bytes).hexdigest()
```

The full 64-character digest is retained. `handoff_receipt` is the existing
typed report namespace. This identity names the checked proof relation; it is
not a source ID or another submission identity. Its containing proof source is
content-addressed independently by ordinary `Store.put('source', ..., origin=
'tool')`. That source's ID is added to actual `record_refs` and
`resource_information_refs` only after its body has been retained. It is never
embedded in its own body, avoiding a content-address cycle.

The source provider is `episode.api_search_handoff`, source/body version is
`api_search_handoff_information_v1`, and its body has exactly:

```text
version, run_id, episode_id, operation_key, scope, assignment_sha256,
registry_ref, job_ref, request_sha256, status_receipt_ref,
execution_handoff, outcome
```

The source accession is `api_handoff_` plus full SHA256 of the same canonical
encoding of `[run_id, episode_id, operation_key]`. Its original retrieval time
equals the selected status receipt's `observed_at`; `artifact_ref` and
`text_ref` name the exact canonical JSON bytes; URI and request reference are
null; `operand_refs` contains the actual original request subject.

The reader validates source content address and bytes, original run/episode
assignment digest and scope, actual selected check action and operation key,
original bound registry/order/request, input versions, physical handle,
receiving contracts, original provider status receipt, UTC check time and the
audit derivation. Body outcome equals the completed receipt outcome exactly,
including the entire original receipt and original `provider_operation_refs`.
If a runtime outcome is already committed, the reader also checks the retained
source-bearing outcome against it. Replaying the selected check returns that
outcome and performs no HTTP. A parent receiver qualifies the received source
against its own original API job, input versions and explicit constraints.

## Publication selector and outcome boundary

`PublicSearchResultPublisher.publish(receipt_ref, *, scope, operation_key)`
receives the actual Store scope. Its output remains exactly `{result,
record_refs}` with scope 001/002 result fields. P's immutable publication source
records the single captured page selector:

```json
{"version":"public_search_result_selector_v1","provider":"hmmer",
 "first_page":1,"last_page":1,"page_size":50}
```

The integers above illustrate the captured page and actual captured page size;
they are not defaults chosen by B. B independently qualifies that captured page
and size against the parent's `requested_data_selector`. It checks the actual
selected acquisition action/key, publication content address and canonical
bytes, registry/order/request, acquisition receipt, original retained snapshot,
native source request/transport/body bytes, actual record types and source
relationships, native hit/domain array ordinals, and actual outcome references.
Only this results episode's own completed/partial acquisition publications
supply operational result witnesses.

B wraps the exact publisher output with `status='completed'` when the saved
projection failure array is empty, otherwise `status='partial'`;
`changed_record_refs` contains the actual published references. Feedback is
null for complete publication, otherwise exactly `{code:'partial_projection',
projection_failures: saved_failure_array}`. It does not import extra data or
reinterpret a partial publication as scientific completion. All original valid
records remain visible. Ordinary direct public search/collect tools keep their
existing outcome contract.

## In-progress delivery and transaction boundary

A same-key `ProviderOperationInProgress` raised by the submit port becomes a
failed adapter delivery with result `{job_ref, operation_key}` and restricted
feedback code `submission_in_progress`, affected original job, null diagnostic,
and empty partial-record references. It fabricates no provider operation
receipt, does not terminate the still-owned operation, does not earn a completed
action observation, and authorizes no POST. Provider atomic claims/captured
receipts remain authoritative. The caller can select the existing explicit
recovery operation later.

The adapter rejects awaited provider work while a Store transaction is open.
Provider receipt capture, no-network result publication, proof publication and
later runtime outcome recording occur through separate actual transactions.
Closure/report/credit reads do not call HTTP. Repeated checked receipts for the
same `(registry_ref, provider_job)` and repeated canonical result references do
not create additional operational contributions. Monitoring projection remains
C's separate existing-unit channel.
