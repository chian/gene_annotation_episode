# API forecast source correction before integration, scope017

This permanent clarification follows unchanged adopted016 (SHA256
7cdeaf90e81b6e66aa7b697e0ceeaaf20a1095b4e1a293d09ed83cb915c09d42).
B inspected the actual communication consumer and identified that the proposed
native/API schema union is invalid: validate_closed_schema does not accept
oneOf/anyOf and its form traversal requires each declared closed object shape.
No union implementation or generic communication change is adopted. This fixes
that exact shared handoff before A/C integration is dispatched. Original goal,
active science, existing schemas/numerics and prior records stay unchanged.

## Exact producer/consumer replacements

1. Native ESTIMATE_SCHEMA, report_source(), estimate_context(),
   recorded_forecasts() and their default v2 saved definition/output keep their
   existing native meanings. The native phase enum must remain the original
   four phases; do not accidentally expand it via the new backend-map entry.
   Remote input to the native path must not produce a remote-shaped row under
   a native schema. Native facts and original hashes stay unchanged.
2. B adds the separate closed API_REPORT_ESTIMATE_SCHEMA exactly as016 defines
   the API row, and function reported_report_source(). Its returned source
   report_schema is exactly an array of API_REPORT_ESTIMATE_SCHEMA with
   x-source api_reported_execution_forecasts. No JSON schema union is used.
3. ResourceToolEstimator.with_reported_results() returns the actual opt-in
   estimator class. Its as_record() is exactly
   {version:resource_tool_duration_estimator_v3,
    method:exact_class_current_condition_successful_duration_mean,
    reported_result_method:exact_exposed_configuration_current_condition_reported_duration_mean_v1}.
   Default as_record/from_record v2 behavior remains exact. The new explicit
   estimate_reported_context(context) returns only closed API rows; it is
   unavailable on a non-opted-in instance. estimate_context remains native.
   This is the same empirical-mean support component, not a new controller.
4. C calls estimate_reported_context only for the assigned API normalized
   request and supplies its rows in api_reported_execution_forecasts.
   resource_tool_estimates remains native-only. C exposes the new exact
   requested source api_reported_execution_forecasts using B's
   reported_report_source(); typed fact validation uses the original journal.
   api_reported_execution_expectations remains the separate original capture
   list and api_execution_options the local operand-to-class/proposal mapping.
   These fields do not enter waiting_support, WaitInputs, commission native
   expectation_snapshot_refs or any numerical pending-turnaround calculation.
5. B owns recorded_api_forecasts(store, *, run_id, episode_id), which mirrors
   the existing latest-completed-own-action/original-at-selection journal
   semantics for api_reported_execution_forecasts only. It computes no fresh
   forecast. B additively recognizes this field's runtime_actions.result and
   runtime_model_calls.request.context paths in recorded_estimate for the
   existing declared forecast reference namespaces, without changing native
   recorded_forecasts defaults. Existing factual schema validation compares
   all supplied API fields with their actual original row.
6. C owns all resulting decision/complete-action/form/facts/resolver/replay
   routing in the files already assigned by016. No communication.py,
   generation_schema.py, waiting/controller or shared-loop change is planned.
   Native-only caller/form/source definitions and values remain exact.

## Unsupported configurations and unknown information

B execution_class(request) and capture_start(request) raise
ValueError(unsupported_statistics_configuration) for nonempty taxonomy filters.
B capture(request) returns the existing capture envelope with
status unavailable, code unsupported_statistics_configuration,
execution_classes empty and snapshots empty. The scientific/API operation is
still permitted. No taxonomy identity/digest/proxy enters shared statistics.
C preserves this explicit disposition instead of treating empty output as a
known zero-duration class.

A may retain a local qualified reported-duration witness with null start_context
and null matched intent when no compatible class/start context could be made.
The original immutable order/request still determines the unsupported reason;
A may revalidate that technical configuration through B without recapturing
history or making another HTTP call. It must not invent a valid typed start
context or coerce unknown condition to unspecified. Such facts can inform the
one existing monitoring-information projection, while numerical export remains
unavailable/not-applicable with the actual recorded reason.

Tests must exercise separate closed source validation through the actual form
validator, old native source/serialized-output equality, API forecast reference
resolution from its original journal, and explicit exclusion from pending-wait
inputs. This amendment changes no owned file boundary and no score/unit.
