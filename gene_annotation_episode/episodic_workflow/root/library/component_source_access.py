"""Authenticate the original source-reader action's received-input binding."""
from gene_annotation_episode.episodic_workflow.root.communication import plain
from ..episode_return_records import EpisodeReturnRecords


def source_received_inputs(tools, name, arguments, scope, operation_key, selected):
    """Bind an original source-reader action across frozen/plain scope views.

    This passes only its existing receipt set. Explicit subsets stay selected;
    an unbound action, a different invocation or an unauthenticated context
    acquires no extra source access. No record, evidence or credit is created.
    """
    if selected is not None or name not in {'source.locate', 'source.sequence.scan',
            'source.sequence.references', 'source.experimental.records'}:
        return selected
    invocation = tools._current_invocation.get()
    if invocation is None or operation_key is None or invocation[2:] != (name, arguments, operation_key):
        return None
    context = invocation[0]
    try:
        if tools.store.validate_scope(scope) != plain(context.scope):
            return None
        exists = tools.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_episodes'").fetchone()
        if exists is None:
            return ()
        EpisodeReturnRecords(tools.store, context.run_id,
            failure_prefix='component_source_').authenticate(context)
    except (ValueError, KeyError, TypeError):
        return ()  # Prevent the generic fallback from binding an invalid host context.
    return tuple(context.received_record_refs)


