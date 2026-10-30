# Reuse successful schema checks during tool-library construction

Implementation repair, 2026-10-25. This does not change the permanent episode
design, the scientific tool scope, a scoring formula or continuation behavior.

The actual composed MSA test exposed repeated validation of identical tool input
schemas. Its retained diagnostic-004 profile recorded 781 Draft202012Validator
check_schema calls occupying 24.454 seconds of a 29.617-second instrumented
interval. The major callers were scientific_tool_library._catalog/_profiles
and resource_tool_information._contract. This was CPU work during construction,
not a native job, network wait, selected episode action or yield observation.

Those three consumers now call tool_schema_validation.check_tool_schema. The
helper caches only successful syntax validation under the complete canonical
JSON schema contents, with a bounded 512-entry LRU. A nested mutation becomes a
different key. Invalid checks still raise the original SchemaError and are not
cached. Each consumer continues its original type, name, instruction, resource,
route and current-contract checks. Actual invocation arguments still undergo
their original validation. No file custody or resource availability is cached.

The helper is included in the scientific construction implementation pin. Old
run definitions and observations are not rewritten. There are no method_loop,
controller, credit or episode-menu changes.

Verification: six focused cache/consumer checks and the existing child-tool
information, actual retrieval and resource-selection suites passed together:
33 tests in 50.37 seconds. The three real consumers share one check for repeated
identical schemas; changed valid and invalid nested schemas are rechecked;
invalid arguments and resource/instruction conflicts remain rejected. The
current complete Workflow test is a separate verification responsibility.
