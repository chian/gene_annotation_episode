# Explicit API timing ledger Store ownership, scope019

This additive cross-owner clarification follows unchanged016–018 before A/C
coding dispatch. B's statistics/configuration formats and owned files do not
change. A ledger cannot check matching Store ownership from a path-less
constructor, so its runtime constructor is fixed to the actual owner:

```python
ApiTimingLedger(*, store: Store, run_id: str, registry: dict,
                binding: ApiTimingBinding, statistics: ApiReportedStatistics)
```

C passes the actual same Store object already supplied to its caller factory and
ProviderJobOperations. A retains that owner as ledger.store and checks object
identity when installing/using the ProviderJobOperations timing hook. A also
persists the canonical absolute Store.path identity in the immutable ledger
binding. Reconstruction can create a new Store object at the same exact saved
path, then creates matching ledger/operations against that same new object;
a different workspace cannot adopt an existing ledger/run/registry binding.
No Store is created by the ledger. An orphan timing marker never supplies
provider authority: actual order/scope/receipts still validate through operations.

The exact ApiTimingLedger.as_record() output is:

```python
{
    'version': 'api_timing_ledger_v1',
    'run_id': str,
    'store_path': absolute_canonical_path,
    'registry': original_validated_public_search_registry_v1,
    'binding': ApiTimingBindingRecordV1,
}
```

The registry is an owned plain JSON copy of the actual registry, never a client
substitute. The binding is exactly016's closed caller configuration. The ledger
binding_ref is api_timing_binding_ followed by SHA256 of this canonical record.
A retains immutable copies; exposed record dictionaries cannot mutate its
binding. Equality/CAS checks include the complete record. Existing API public
port/order/claim/receipt formats do not change.

C's ApiReportedTimingFactReader(ledger, *, ports) verifies actual matching
Store/registry/resource/ledger ownership. Its exact as_record() output is:

```python
{
    'version': 'api_reported_timing_fact_reader_v1',
    'ledger': ledger.as_record(),
}
```

C uses this actual output in the already declared optional union-information
binding. No independent unit, score, controller or execution decision is added.
Root/factory/worker reconstruction must preserve the same config and Store path
before work. These checks validate existing ownership rather than create a
runtime approval step. Native-only setup remains unchanged.
