"""Private original-action binding for A110 flux-balance work."""
import json
from .domain import ContractError, canonical


class FluxBalanceOperationUnpublished(RuntimeError):
    """Keep an unfinished native action attached to its original attempt."""


def authenticate_flux_balance_invocation(registry, name, arguments, scope, operation_key):
    """A host context is necessary but its actual saved action is authoritative."""
    invocation = registry._current_invocation.get()
    if invocation is None:
        raise ContractError("molecular_tool_current_invocation_required")
    context, reader, selected_name, selected_arguments, selected_key = invocation
    from .communication import plain
    from .episode_return_records import EpisodeReturnRecords
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="molecular_tool_")
    records.authenticate(context)
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if isinstance(operation_key, str) and operation_key.startswith(prefix) else ""
    if (not suffix.isdecimal() or str(int(suffix)) != suffix or selected_name != name
            or canonical(selected_arguments) != canonical(arguments) or selected_key != operation_key
            or canonical(plain(context.scope)) != canonical(scope) or not callable(reader)):
        raise ContractError("molecular_tool_selected_action_conflict")
    row = registry.store.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
        "AND decision_index=?", (context.run_id, context.episode_id, int(suffix))).fetchone()
    if row is None or canonical(json.loads(row["action"])) != canonical(
            dict(kind="tool", tool=name, arguments=arguments)):
        raise ContractError("molecular_tool_selected_action_conflict")
    return context, reader


