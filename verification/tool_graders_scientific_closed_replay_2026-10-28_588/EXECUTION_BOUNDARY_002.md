# Preserve the existing check before new execution

Additive implementation clarification to001, agreed before the worker's edit.
Restoring a historical closed request must not authorize new work under its old
implementation identity. The prior full mechanics comparison enforced that
restriction, and the restoration repair must preserve it.

Add `ScientificProcessEpisodes.validate_execution_context(context) -> None`:
validate the ordinary context and require its full mechanics binding to equal
the current `as_record()` before an unsaved model/action/child dispatch or a
direct scientific execute. Call it only at the identified actual dispatch
boundaries. Exact saved decisions/actions continue to replay without a current
implementation hash. Reads and validation of the authoritative closed request
remain possible through001's restoration ports.

This retains execution identity checks. It does not add a controller condition,
scientific gate, automatic cancellation, turn cap, or permission flow. Verify
that an attempted unsaved dispatch with the historical binding fails before any
model/tool/native work, while original recorded dispatch replay remains exact.
Report the changed caller methods and bounded verification separately.
