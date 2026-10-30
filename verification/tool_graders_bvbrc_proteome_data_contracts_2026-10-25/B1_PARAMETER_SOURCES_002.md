# Additive B1 original-parameter source handoff

Worker166 found a real input-contract omission. OriginalTask supplies only a
submission source reference, whereas effective parameters have a SourceEvidence
with content binding and pointer. If the selected parameter_source is effective,
the old signature cannot construct a source-bound submitted snapshot. Do not
invent its digest/pointer or attach submitted values to the effective source.

Extend only this B1 signature, before its implementation is completed:

```python
def index_original_inputs(original_task: dict, *, parameter_source: dict,
    source_contract: dict, additional_parameter_sources: list[dict] | None = None
) -> dict: ...
```

Every additional element is the existing closed ParameterSource shape. It
supplies a source-bound location, not additional parameter values. Values still
come from the supplied OriginalTask. No schema/output shape changes are needed.
The actual adapter must validate these locations against acquired records.

The selected parameter_source determines the order/reference mapping. Additional
sources never choose a different mapping or substitute parameter values. Accept
at most one distinct source for each kind, allowing exact duplicate descriptions
to collapse; conflicting supplied locations are explicit invalid inputs.

Retain submitted/effective threshold snapshots separately when their actual
source fields are available. The effective SourceEvidence already in OriginalTask
may supply its own exact source location. A missing submitted location remains
an explicit original_parameters requirement with parameter_source_conflict;
preserve any valid selected index and source-bound snapshot in a partial result.
Do not invent an empty snapshot or put values under a false SourceField. No
effective parameter snapshot exists when OriginalTask has no such observation.

Both selected and additional submitted fields must name the exact existing
submission_source_ref; effective fields must agree with the exact effective
SourceEvidence. The functions do no Store lookup or new acquisition. Existing
host custody remains separate. All other B1 interfaces and frozen data shapes
remain as accepted in B1_FREEZE_001.md.
