# Additive C retained-record failure and caller contract

2026-10-25. This closes the one ambiguity in EXTRACTION_CONTRACT_001.md without changing permanent002, any A/B-consumed value, or a production file. Root requested explicit per-record recovery. Source expectations in001 remain source expectations throughout; no recipe, path, invocation-mode or producer-source expectation proves deployment or same-run bytes.

The proposed helper signature remains:

```python
validate_genome_alignment_retained_records(original_task: dict, *,
    retained_records: tuple[dict, ...],
    supplied_bytes: dict[str, bytes]) -> tuple[dict, ...]
```

It returns detached copies of all provided records if they pass. It performs no Store access and does not authenticate episode possession. On a one-record call it either returns `(validated_record,)` or raises a finite error. It does not drop a record silently, return arbitrary dictionaries, mutate its inputs, or claim authenticity from its name.

Both top-level C callers use the following required sequence:

1. Validate the overall Python types, closed RetainedRecord shapes, existing typed receipt schemas, explicit original-task shape and the bytes-map key/value types before semantic extraction. Unsupported discriminator, missing/extra field or wrong Python type is a caller contract error: raise `ValueError("bvbrc_genome_alignment_argument_invalid")` (or the documented existing narrower original-task contract code). A typed record may not use a fabricated alternative receipt schema.
2. Validate each retained record independently by calling the helper with a **one-element tuple**. Catch only the finite data-dependent errors listed below, record the affected record's requirement/diagnostic, and continue with other records. Never call the helper once on the entire tuple and discard everything on the first failure. Unexpected exceptions are programming errors and must not be converted to missing science.
3. Resolve cross-record relationships only among the individually accepted records. Detect duplicate receipt references before selecting any candidate. Exact repeated receipt/content representations may be deduplicated for extraction while all supplied references remain in the retained host inputs. If one source reference names different typed values or receipt content, mark that reference's entire conflicting group unusable; do not choose the first/last. Unrelated references remain usable.
4. Conflicting multiple native invocation candidates produce a conflicting invocation only; valid original genome occurrences, candidate FASTA records, native artifacts and independent manifest associations survive. A bad optional metadata claim cannot erase a valid independently extracted native fact.
5. Return `InputExtraction`/`AssociationResult` with `status="partial"`, retained valid fields, and complete reports when any local gap/conflict remains. `value=null` is reserved for an uninterpretable original task/application/input, as001 states. Result status and report sets are deterministic and preserve all local missing distinctions.

Finite semantic errors caught per record (exact `bvbrc_genome_alignment_` prefix):

| Error suffix | Exact condition | Requirement |
| --- | --- | --- |
| `content_missing` | The envelope or required snapshot content reference has no supplied bytes | input_metadata/input_bytes/output_bytes according to the absent record's actual role |
| `content_digest_conflict` | Supplied bytes disagree with declared SHA256/byte_count, or one receipt-content reference has contradictory byte identity | same kind as missing bytes; conflict state |
| `metadata_record_unverified` | Envelope bytes are not valid unique-key finite canonical JSON, encoded envelope differs from the provided typed record after only the documented self-reference removal, or selected native operands cannot substantiate the declared record meaning | input_metadata / relevant role |
| `metadata_task_conflict` | Actual receipt task/handoff/request/resource or original selected call disagrees with the original task | original_task / null |
| `invocation_missing` | Actual stdout is absent, unavailable, transport-incomplete/windowed, undecodable or lacks a complete supported command group | input_metadata / genome_alignment_invocation |
| `invocation_conflict` | Multiple incompatible command groups, cardinality/token/retrieval-event conflict or unsupported unambiguous reconstruction | input_metadata / genome_alignment_invocation |
| `artifact_task_conflict` | Actual acquisition/manifest object association belongs to another original task or fails exact handoff/object/source relationship | task_manifest / actual artifact role |
| `artifact_version_unverified` | Object relationship and bytes are present, but no original-producer byte identity exists | byte_version_evidence / actual artifact role; qualification, not deletion |

The helper handles receipt structure/bytes/task-selected-call checks; log parsing and artifact/manifest semantic checks occur in the appropriate extractor/binder stage. The last four semantic codes can therefore arise after a retained record was accepted structurally. Known host custody exceptions happen before the provider call and remain the host's existing structured failures; C does not suppress or counterfeit them.

Diagnostic `path` identifies `/retained_records/i` and, when relevant, its concrete nested field. `evidence_refs` includes only actual affected source references. Requirement IDs include that source/occurrence identity; the entire input/extraction report preserves separate requirements for two different failing sources even when their reason codes match.

`artifact_version_unverified` is nonfatal to a validated native manifest object association and native measurements on acquired bytes. It remains fatal to a claim requiring exact original producer bytes, such as a same-run source/member join or an internal-interval export relation. Unknown version is never upgraded by a typed assertion.

## Exact original binding-pointer clarification

Generic `validate_request` checks an InputBinding's `parameter_pointer` against the original request and its inline/path operand. It does **not** resolve every `MemberFact.member_pointer`. Therefore C must not imply that generic validation alone certifies a member join.

For current GenomeAlignment occurrences, permit a unique original `inline_parameter` or `supplied_link` binding whose parameter pointer resolves to the exact original scalar `/genome_ids/i`, or a unique original `inline_parameter` binding at `/genome_ids` whose entire inline array exactly equals the submitted ordered array. The group-binding identity then applies to each explicit array occurrence; equal duplicate genome strings do not merge occurrences. If a scalar and a group binding both match, report ambiguity rather than picking one. `members` is not needed to invent a scalar relationship. If a future use relies on `MemberFact.member_pointer`, it needs an explicit documented base object and actual pointer/evidence equality; this current contract does not guess that base.

This additive clarification supersedes001's loose reference to resolving a member pointer via `validate_request`. It changes no requested or output value shape.
