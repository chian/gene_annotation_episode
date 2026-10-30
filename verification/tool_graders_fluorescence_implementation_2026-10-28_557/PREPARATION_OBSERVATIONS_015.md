# Preparation input indexing and retained native diagnostics

Additive clarifications to013–014, settled before implementation of these ports.

`validate_preparation_request(..., input_domains=...)` receives the ordered
domain list for `request.input.kind`: either original event input domains or
earlier preparation output domains. Its index is within that list. The producer
validates the kind, topology and absence of forward references; parser consumers
use the same split. No automatic reordering or new workflow owner is introduced.

Add exactly one field to ResolvedPreparation:

```
diagnostics: [{problem_code: PreparationProblem.code,
               exception_class: qualified native exception class}]
```

The class is a nonempty restricted Python qualified-identifier string, retained
only from a caught actual exception. Empty diagnostics means none observed.
Retain the applicable existing problem code and exact class, without invented
native codes or free error paragraphs. This stays in the already retained
parameters artifact. PreparationOutcome already contains those parameters;
do not duplicate diagnostics in it or add model-facing text.

FlowIO's native TEXT parser discards duplicate keys and removes dollar signs
before building its dictionary. For the strict preparation profile, a small
explicit observer of the unchanged TEXT passed to the original method may
retain ordered raw key/value tokens using the same delimiter/escape grammar.
The actual original FlowIO method still supplies decoder metadata. Compare the
normalized observed pairs with that actual result; reject duplicate relevant
keys and altered value tokens. This is metadata inspection, not a replacement
event-array decoder or numerical transform. Do not clone function bytecode,
replace function globals or change str.replace semantics. Existing encoded
reading remains unchanged. Verify escaped delimiters, duplicate selected keys
and literal dollar signs in values explicitly.
