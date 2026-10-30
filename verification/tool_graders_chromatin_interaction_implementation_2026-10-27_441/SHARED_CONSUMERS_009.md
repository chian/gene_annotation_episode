# Chromatin shared consumer handoffs

Additive implementation clarification; original user goal unchanged. This makes
the concrete448/449/root dependencies explicit before their integration.

## Return traversal consumed by completed-action receipts

449 confirmed these existing-mechanism internal ports:

* `_commission(parent, child, *, construction=False) -> None`: authenticate the
  original immediate commission, including selected launch/resource ancestry
  and ordinary unsaved construction. No new commission is made.
* `_received(context, sources, *, allowed=None) -> (groups, origins, prefix)`:
  facts through exact successful forms, limited by the supplied frozen attempts
  when nonnull. `origins[canonical(saved_bundle)]` contains all exact origin
  dicts `{episode_id,operation_key}`. `prefix` is the complete existing
  `frozen_received_report_prefix_v1` dict, not merely its attempts list.

448's baseline reads those exact completed result actions. It does not scan an
episode for a favorable result or use current receipts in place of the frozen
prefix. This is the traversal required by447, not another authority mechanism.

## Root shared registration and pure information

Root owns `chromatin_interaction_execution_information.py` with these ports:

* `chromatin_result_selector_schema() -> dict`: exact independent C1
  ResultSelector schema, with its own local reference scope.
* `validate_chromatin_result_selector(selector, *, request) -> dict`: pure C1
  request/selector validation; selected populations must be declared, parameters
  must correspond to the original analysis modes, and projection kind must name
  an available analysis. Preserve parent population/key/page order. Saved mode
  validates the exact SavedSheetBundle shape; byte availability and received
  authority remain their separate owners. No native/data access or calculation.
* `describe_chromatin_result(target, *, selector) -> dict`: pure description of
  an already authenticated historical target and exact selected result. Uses
  existing target structure and actual callable parser/calculator/capture ports;
  no observations, producer/software access, TASK text or LLM judging prompt.

Root registers the actual C3 tool information and configured local request in
ExecutionEpisodes, calls450 supplied-input validation on choosing/construction
boundaries,449 on actual typed returns and saved operands, and448/host on selected
results work, operational credit and original practical completion. Provider
classification precedes generic Store reference fallback. New chromatin input
validation calls the composite received-reference resolver so another tool's
private output cannot become an input by merely existing in Store.

No concrete model TASK/STEERING template is approved by this integration.
Existing pending message work remains pending and must be shown for user feedback.
No tool count or full Workflow claim follows from writing these branches.
