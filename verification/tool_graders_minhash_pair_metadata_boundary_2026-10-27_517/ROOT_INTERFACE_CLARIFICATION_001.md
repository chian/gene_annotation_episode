# Root-reviewed MinHash coding interfaces

This additive implementation clarification does not change the user goal. Read
the complete final CONTRACT.md in this directory and the original attachment.
Root inspected the complete existing grader, the projector through its component
validation, and the service request/selection definitions before this handoff.

## Existing saved-data validation

`calculate_minhash_components` currently calls `parse_minhash_result` on the
sheet's retained `native_result` to validate saved cells and their associations.
That is pure validation of supplied saved data, not acquisition or a rerun of
MinHash. Preserve it. The proposal's stronger parser-disabled recalculation
assertion is not compatible with the existing implementation and is not a goal
requirement. Saved-mode publication must not independently re-extract a response
or fetch anything; the existing calculator's internal saved-data validation may
run. Ordinary publication/read/replay still bypasses the parser and full
calculator, returning the original retained artifacts.

## Exact pure contract ports

The new `bvbrc_minhash_contracts.py` owns these ports:

```python
minhash_result_selector_schema() -> dict
validate_minhash_result_selector(value) -> dict
validate_minhash_pair_metadata(value, *, request) -> list[dict]
validate_minhash_publication_inputs(value, *, request, selector) -> dict
```

The schema port returns a detached closed JSON schema accepting legacy `{}` or
the exact V2 selector in CONTRACT.md. All validators return detached copies,
preserve original ordering and duplicate entries, and do not normalize/coerce
values. They perform no I/O, source lookup, parser call or numerical calculation.
`request` is the existing **service request** with `mode`, `query`, `max_pvalue`,
`max_distance`, `max_hits`, `include_reference`, `include_representative`,
`bacterial`, `viral`; it is not the RPC method/params envelope. Existing service
request validation remains authoritative for the native invocation. These ports
check the input shape and exact metadata query association necessary here.

Errors are `ValueError` with one of these stable code strings:

- `minhash_result_selector_invalid`
- `minhash_pair_metadata_invalid`
- `minhash_metadata_query_conflict`
- `minhash_publication_inputs_conflict`

Host input binding owns the more specific source/custody/pointer failures in
CONTRACT.md. Pure validation cannot establish possession or truth from a source
ID, JSON pointer or supplied digest. Its role is closed shape, exact copied
value relationships, null/present relationships, field-evidence multiplicity and
pair-metadata-index relationships. Duplicate pair candidates remain intact for
the existing calculator's ambiguity handling.

The publication envelope and each binding have exactly the keys in the final
CONTRACT.md, including `pair_metadata_index`, `artifact_ref` and
`artifact_sha256`. Each binding corresponds to one nonnull field on that exact
supplied list occurrence. Preserve the original common sheet and component
schema names. Do not import service or host modules into the pure contract
module, or introduce a circular service/view dependency.

## Exact common numerical helper

The existing `bvbrc_minhash_grader.py` owns:

```python
calculate_minhash_shared_hash_fraction(shared_hashes, compared_union_hashes,
    *, row_identity_available: bool) -> float | None
```

Return the existing Python division result only when the identity flag is exactly
True, both counts are non-boolean integers, `0 <= shared <= union`, and union is
positive. Otherwise return None. Preserve rounding and underflow behavior; the
existing full calculator continues to own the associated diagnostic records.
The helper performs no parsing, I/O, lookup or other calculation. The full
calculator and the projector's consistency validation must call this same
helper. Projection copies the saved value after validation; it does not replace
it with a newly produced value or invoke the full calculator.

The grader also owns one finite `MINHASH_DIAGNOSTIC_CODES` collection matching
its actual existing issue codes for later typed diagnostic returns. Do not
invent new scientific diagnostics, alter distance/binomial calculations, or
change the existing sheet/component output shape for this refactor.

## First independent coding workload

Fresh workload A exclusively owns the new contracts module, the existing grader,
new `tests/test_bvbrc_minhash_contracts.py`, and
`tests/test_bvbrc_minhash_grader.py`. It writes focused tests and retains before
snapshots/diffs. It does not edit the service, host, views, execution dispatch,
prompts or tool information, and does not launch its own scientific test job.
Root coordinates frozen verification. The view owner will later call the exact
common helper above; A is not expected to finish that separate owned consumer.

Other workloads can code against these frozen data shapes and signatures; they
need not wait for A's implementation to define their interfaces. Root will
assign their exclusive files after reviewing the complete affected execution
and custody paths. No whole MinHash integration is complete when A finishes.

Tests must preserve legacy calculation outputs and include bad native counts,
zero denominator, absent identity, rounded fractions, exact 2/3, unchanged
distance/p-value results, valid/null/k-only metadata, wrong query, duplicate
metadata candidates, exact per-field bindings, wrong list indices and malformed
closed shapes. Numerical imports/tests execute only in the root-owned frozen
native_lifecycle/local_jobs environment under the user's resource constraints.
