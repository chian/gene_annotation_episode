"""Shared exact configured execution-owner lookup; no task choice."""

def _execution(services, *, context=None, owner=None):
    registry = getattr(getattr(services, "workflow", None), "episode_bindings", None)
    if registry is None or "results" not in registry.roles:
        return None
    binding = registry.for_context_role("results", path=getattr(context, "path", None), owner=owner)
    api = getattr(binding, "api_execution", None)
    if api is None or not any(value.service == "bvbrc_appservice" for value in api.services.values()):
        return None
    return binding
