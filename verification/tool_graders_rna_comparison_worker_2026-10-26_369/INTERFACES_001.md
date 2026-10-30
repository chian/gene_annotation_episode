# Workload D: frozen retained worker and publication interfaces

This implements the exact D/E boundary from 362/CONTRACT_ADDENDUM_007.md.
The complete scientific contract is PLAN_001 plus addenda 001–007. A supplies
closed inputs and the reader, B supplies numerical calculations, C supplies
the explicitly selected compact returns. D owns calculation execution and
retained-byte correspondence. E owns original received-input authority and
actual selected-action/commission identity. D does not authenticate or grant
authority and does not import E.

## Public imports and signatures

`gene_annotation_episode.rna_structure_comparison_worker`:

```python
comparison_input_digests(selector: dict, data: dict) -> list[dict]
comparison_calculation_key(selector: dict, data: dict) -> str
run_rna_comparison_worker(plan: dict) -> dict
```

`gene_annotation_episode.rna_structure_comparison_publication`:

```python
prepare_rna_comparison_grading(store, *, selector: dict, operands: dict,
    result_receipt_key: str, directory: Path, policy: LocalJobPolicy) -> dict

validate_prepared_rna_comparison(store, prepared: dict, *, selector: dict,
    operands: dict, result_receipt_key: str) -> dict

publish_selected_rna_comparison_rows(store, *, selector: dict, prepared: dict,
    operands: dict, result_receipt_key: str) -> list[dict]
```

The two pure identity helpers are also imported/reexported by publication.
Validation returns exactly `{sheet, components, projection_rows}`. Sheet and
components are nullable only for a verified retained preparation failure.
Publication invokes the same validation and returns its exact projection rows.
All supplied dictionaries remain unchanged.

## Inputs and identities

`operands` is exactly the addendum007 ResolvedOperands object:

```text
version: rna_structure_comparison_resolved_operands_v1
data: {non_alias_member_id: {original_sheet, original_bundle_software,
                           received_failure}, ...}
original_receipts: {saved_or_received_failure_member_id: original_receipt, ...}
selected_references: [ordered_unique_existing_reference, ...]
```

E must authenticate every original before this call and on later return
validation. D checks exact non-alias data membership, scientific associations,
saved sheet bytes, original receipt key correspondence and original receipt
membership. D preserves selected references as supplied in the immutable
intent; it does not retrieve, authorize or recursively expand them. Input data
contains no aliases, extra records or producer-path fields.

Value identities use `execution_contracts.digest`, while persisted JSON bytes
use `canonical(value) + "\n"`. A saved descriptor's sheet_sha256 hashes the
actual canonical newline-terminated original sheet bytes. Selected input rows
contain exactly `{member_id, kind, input_sha256}` in question membership order,
including declared absences and excluding aliases. Each input_sha256 is the
value digest of the complete corresponding ResolvedOperandData.

`comparison_calculation_key` is `rna_comparison_calculation:` plus the digest
of exactly `{selected_input_digests, question, parameters, calculator_version}`.
Projection selection is excluded. The full selector still binds the original
intent and prepared record. Changing only projections preserves the sheet,
components and calculation identity; it creates distinct requested returns.
This does not invoke native RNA or acquire any input.

E supplies `rna_comparison_receipt:` plus its actual selected collect-action
identity digest. D checks format and equality throughout the retained request,
output and projection chain. A supplied key is not evidence of authority.

## One bounded calculation

The exact worker plan and success manifest are addendum007's closed shapes,
exported as PLAN_VERSION/PLAN_FIELDS and RESULT_VERSION/RESULT_FIELDS. The
worker reads only directory/input-data.json with its explicit absolute path,
actual SHA256 and byte count. It rejects noncanonical, duplicate-key, nonfinite,
malformed, missing, substituted or extra data. The worker has no Store handle,
original receipt bodies, original producer directory or acquisition operation.

The worker calls A's reader, B's full calculator and C's explicit projector,
writing immutable sheet.json, components.json, projections.json and finally
worker-result.json. Its executable port is:

```text
<selected interpreter> -B -m gene_annotation_episode.rna_structure_comparison_worker <absolute plan.json>
```

Preparation accepts only LocalJobPolicy with memory_bytes=21474836480,
scratch_bytes=4294967296 and wall_seconds=None. It uses existing run_local_job
with a small owned cwd and explicit TMPDIR/TMP/TEMP, XDG_CACHE_HOME,
PIP_CACHE_DIR, PYTHONDONTWRITEBYTECODE and PYTHONPATH. The actual command,
environment, policy, verified cgroup facts, return code and log artifacts stay
retained. No scheduler, native RNA, network, HPC or episode loop is introduced.

## Retention, replay and failures

PreparedComparison is exactly the 18-field addendum007 object, exported as
PREPARED_VERSION/PREPARED_FIELDS. It contains both original receipt keys and
ordered selected input digests, the full selector digest, actual input byte
hash, current receipt/calculation identity, sheet/components/projection
artifact links, full selected rows, scientific issues, a separate nullable
preparation_failure and delivery_complete.

Preparation retains intent.json, input-data.json, input-custody.json, plan.json,
worker-started.json, worker stdout/stderr, execution-receipt.json,
worker-receipt.json and prepared.json. Each JSON record is immutable. Store
artifacts retain these records and all available worker output bytes, including
malformed output used as diagnostic evidence. The original execution exception
and stderr stay internal; public failures use exactly `{code, member_id,
artifact_role}` from addendum007. Scientific ComparisonIssue enums are unchanged.

An exclusive preparation lock covers the single worker launch. A completed
preparation validates and replays the saved prepared record from Store even if
its local output files were removed. A completed execution receipt can finish
the interrupted preparation without launching a replacement; a final retained
worker receipt can also recover a missing prepared.json. An existing start
without an execution receipt raises `rna_comparison_preparation_incomplete`.
It never silently retries, overwrites history or treats process interruption as
scientific completion.

Validation verifies all retained artifact bytes and links, reconstructs the
expected sheet from the canonical input-data representation actually used by
the worker, recomputes every B component and reconstructs every exact C return.
Canonical comparison rejects a changed/rehashed number, selection, model,
correspondence, identity or artifact association. The host uses the canonical
data representation so provenance path order agrees with the worker regardless
of caller dictionary insertion order.

Valid partial sheet/components/projections remain retained if a later output
or worker step fails. Missing or corrupt input bytes have distinct preparation
failure codes and never become native-failure population entries. Missing or
invalid outputs give calculation_output_invalid; nonzero/failed execution gives
calculation_worker_failed. A valid scientific incompatibility is a completed
calculation with qualified unavailable requested values. Artifact loss or
alteration after a completed preparation fails validation without rewriting
the saved result or rerunning work.

Full input_paths remain in retained A/B artifacts. Every compact returned cell
uses C's addendum006 schema. Two structures are returned only when their exact
members and fields are selected. An aggregate scan has no implicit structures,
member list or unselected provenance paths.

## Receiving integration responsibilities

E must prove original frozen received-form authority, correct scope, exact
original failure ordinal and all selected descriptor/software associations;
derive the current result receipt key from the actual collect action; repeat
the authority proof when reading a result; and use these exact D ports. Root/E
own action completion, registered typed parent delivery, zero new native
acquisition identities, one observation per completed action and practical
completion. D does not assign credit, infer a baseline from an anchor, grant
references or approve prompt wording.
