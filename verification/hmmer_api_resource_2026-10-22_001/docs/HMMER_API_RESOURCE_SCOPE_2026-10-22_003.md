# Explicit actual-registry setup input

This new clarification follows adopted scopes 001/002. Full consumer inspection
found that `actual_tool_catalog_v1` supplies descriptions only, while caller
setup constructs the API progress provider before composition. Supplying only
descriptions cannot bind that provider to the actual HTTP client/importers.

Root additionally owns isolated changes in `episode_application_services.py`
and the factory-input dispatch in `runtime.Workflow.__init__`. The new explicit
`episode_service_inputs="actual_tool_registry_v1"` supplies both a detached
`tool_catalog` and the existing actual `tool_registry` object. Its saved service
binding is `episode_application_services_v3`, with this exact input name.
Inputs None and actual_tool_catalog_v1 retain their original arguments and saved
versions. Neither ordinary tools nor worker creation changes.

`assembled_case_services_v2` is an opt-in saved configuration with the existing
v1 fields plus the required `public_search_registry` descriptor. Its factory
requests the new registry input. Configuration v1 retains its strict original
field set, input version and setup call. No API resource is installed for v1.
API setup consumes the actual registry, source-custody/importer operations and
client binding; it does not reconstruct a second ToolRegistry or infer client
configuration from descriptions.

Root's `bind_public_search_ports(store, tool_registry, *, registry)` in
`resource_service_setup.py` validates actual registry/client identity, then
constructs P's operations and no-network publisher. Both setup and
`WorkflowServices.public_search_ports` use that helper. Separate instances
share the same Store, actual client, immutable registry and authoritative job
records. They do not acquire new scientific ownership.

B confirmed the reader constructor omitted from proposal 001:
`ApiSearchInformationReader(store, *, run_id, ports)`.
`HmmerServiceResourceAdapter(services, store, journal, *, ports)` exposes that
reader as `.information` at journal.run_id. The remaining constructors stay as
fixed in 001/002. P supplies `describe_hmmer_client_binding(client)` and
`hmmer_client_binding_sha256(client)` from public_search_operations.py. They
derive actual source/client operands without HTTP.

Saved root/child reconstruction continues through the existing fixed-case
factory, input descriptor, implementation pin and before-transport comparisons.
The new input is explicit saved caller state; no private worker, inferred
factory, pending numerical rule or runtime approval gate is introduced.
This entire increment remains isolated from configured_development_002.
