# Projection failures and saved replay: additive boundary closure 005

This closes the concrete P/I seam found by actual publication integration.
Earlier contracts and verification receipts remain historical. It does not
change native measurements, formulas, the shared N/C/D schema asset, generic
AppService schemas, episode ownership, observations or credit.

## Meaning and processing order

1. Project requested native measurements, calculated measurements/ratios,
   populations and memberships. Retain their projection failures.
2. Freeze one metadata-selection input containing original sheet/component
   requirements and diagnostics, explicitly supplied original failure inputs,
   and failures from step 1.
3. All requested requirement and qualification fields select from that same
   frozen input. Their own cardinality/availability failures enter the final
   complete requirements/diagnostics and overall request status. They do not
   become new inputs to sibling metadata fields.
4. Build request status from all requested-field outcomes.

Field insertion order and JSON serialization order cannot change those meanings.
Excessive source matches remain retained and invalid, never truncated. Genuine
source requirements can equal generated records; that is not grounds to reject
the source or erase its original occurrence. Existing final-array deduplication
does not establish which records existed before projection.

## Lossless original failure context

P owns a strict ordinary function:

```python
validate_projection_failure_context(value: object) -> dict
```

It validates and returns a detached JSON object with exactly these keys:

```json
{
  "retained_requirements": [],
  "retained_diagnostics": [],
  "failure_status": null
}
```

The arrays contain the original `RequirementV1` and `DiagnosticV1` records
supplied to projection, before projection generated further records.
`failure_status` is exactly null, `partial` or `invalid`, preserving the original
explicit failure input rather than inferring it from final status. Validate
finite JSON, exact keys and array/member shapes with the existing shape helpers.
This is input custody, not a new scoring language or a scientific grader.

The ordinary current `consume_bundle` constructs both sheet and calculations
and supplies the empty context above. Its exported signature and
`ProviderResultV1` remain unchanged. A caller constructing a nullable/failed
projection must retain the exact original context at that construction step.
It cannot reconstruct it later by subtracting generated failures from final
deduplicated arrays. No reserved-source namespace or collision prohibition is
introduced to conceal that loss.

P extends the saved-validation signature with the required keyword:

```python
validate_saved_comparative_systems_projection(
    sheet, components, *, facts, status, missing_requirements, diagnostics,
    requested_form, parameters, original_task, bundle,
    failure_context: dict,
) -> None
```

Validation checks original-context record identities against the original
parameters/bundle as well as final record identities. It reprojects saved
values using that original context and compares every final fact, status,
requirement and diagnostic exactly. It does not parse, extract, calculate,
acquire or invoke a provider. Components without a sheet remain invalid.
An explicit non-null failure status remains valid only where an original
sheet/calculation is unavailable, as in the existing projection contract.

## I publication codec and consumers

I extends only its own publication codec and its named consumers:

```python
encode_comparative_publication_result(
    result: dict, *, failure_context: dict,
) -> dict

decode_comparative_publication_result(
    adapter: dict, *, sheet: dict | None, components: dict,
) -> tuple[dict, dict]  # (ProviderResultV1, original failure context)
```

The saved `components_content` wrapper is now explicitly versioned
`bvbrc_comparative_systems_published_components_v2`, with exactly:

```json
{
  "version": "bvbrc_comparative_systems_published_components_v2",
  "calculations": null,
  "missing_requirements": [],
  "diagnostics": [],
  "failure_context": {
    "retained_requirements": [],
    "retained_diagnostics": [],
    "failure_status": null
  }
}
```

`calculations` remains C's original object or null. Final native arrays remain
complete and retain their distinct meaning from the original failure inputs.
The existing content digest authenticates the entire wrapper. Generic summary
mapping stays as specified in 003. The sheet still has its own content binding.
The earlier candidate v1 wrapper remains a historical artifact; it is not
silently interpreted as carrying a failure context it never stored.

Actual consumers are `AppServicePublications._grade`, its authenticated read
path, and `bvbrc_comparative_systems_returns._saved_facts`. They pass the decoded
context to P's saved validator. Ordinary current provider publication passes
the empty context explicitly. If a production failure branch cannot construct
or retain that context, report the exact branch as unfinished rather than
inventing a context from its final arrays or bypassing P validation.

No ProviderResultV1, N/D/C data definition, generic AppService schema, root
runtime or existing other-provider contract changes. P owns its five modules
and two tests; I owns its codec, actual consumers and tests, as previously
assigned. Root owns this closure and final source freeze/application.

## Required verification

- A missing requested qualification and a zero-cardinality requirement field
  use the same original metadata snapshot regardless of field order.
- Genuine excess source matches remain visible and invalidate the request.
- Original requirements/diagnostics exactly equal to generated records survive
  the distinct original-context store and replay correctly.
- Both-null and sheet-present/components-null cases round-trip with exact
  original failure status and all final arrays; no invented available facts.
- Changed/omitted context, invalid context fields and altered original-record
  identity fail validation/authentication where applicable.
- Saved replay succeeds with native parsing, extraction, scientific calculation,
  acquisition and provider construction forbidden.
- Actual I publication and typed-return consumers use the new context port.

P's 111-test result predates this correction and remains a historical result.
Final P/I source pins and verification must include this agreed change.
