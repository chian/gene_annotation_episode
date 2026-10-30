# Requested-field order after durable canonical storage

Actual-host worker202 found a root common-contract defect before a final
FastqUtils integration freeze. `make_requested_schema` preserved field order
in both object properties and its required array. `validate_requested_form`
reconstructed that order from object-key iteration. Durable canonical JSON
sorts object keys while retaining array order, so a valid non-alphabetical form
failed after normal storage. Root independently reproduced both the valid
pre-storage form and the post-canonical failure before editing.

The validator now uses the exact required array, checks string names, no
duplicates and complete equality of its field set with the property keys,
then reconstructs the form and performs the same full canonical-schema equality
check. No original schema, selection, scientific number, typed communication
grammar, source validator, journal or continuation behavior changes.

Six focused cases cover the actual canonical serialization round trip and
missing, duplicated, extraneous, non-string or absent declared order. The
original C86/B75/A37 receipts remain facts for their original dependency hashes.
Because common source is part of the scientific implementation closure, this
fix necessarily changes the current provider pin. Final combined verification
must run against the new actual pin; it must not relabel earlier receipts.
