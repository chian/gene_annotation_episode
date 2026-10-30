# Additive operation-schema port for the native invocation owner

This is an implementation interface addition, not a goal or scope change.
The root reviewed 001, 002 and 003 and the core validator implementation.

The native tool-information and requested-job schemas need the same exact
program/mode parameter authority as the pure Operation validator. The core
owner therefore exports one additional pure function:

```python
sequence_masking_operation_schema(*, program: str, mode: str) -> dict
```

It returns an independent JSON Schema object for the already specified closed
Operation for that exact program/mode, including the matching format/style
alternatives and all required nullable requested_parameters. Generate parameter
fields and bounds from the core PARAMETERS authority already used by the
validator; do not define a second parameter table in the native compiler or tool
information. Unknown program/mode is a ContractError. The native owner imports
this function when composing its Job and per-operation input schemas and still
calls validate_sequence_masking_record for typed and cross-field validation.
This function describes the internal operation/response contract. It is not a
model-facing context dump, numerical transformation or separate scoring sheet.

Existing public pure functions and all data shapes from001+002+003 stay unchanged.
The core owner's focused checks cover representative valid/null parameter values,
wrong program/mode, extra keys and unchanged schema results after caller mutation.
