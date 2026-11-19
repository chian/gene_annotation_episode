"""Received-record restriction for A107's source readers.

A source reader (``source.locate``, ``source.sequence.scan``,
``source.sequence.references``, ``source.experimental.records``) may read only
records the acting episode received. When the caller did not name the permitted
records itself, they are the ``received_record_refs`` of the current action's
``ActionInvocation`` (set by ``A107ToolRegistry.execute_async``).
"""

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain

_SOURCE_READERS = frozenset({"source.locate", "source.sequence.scan", "source.sequence.references",
                             "source.experimental.records"})


def source_received_inputs(tools, name, arguments, scope, operation_key, selected):
    """The records this reader may use: the caller's selection, else the acting episode's received records."""
    if selected is not None or name not in _SOURCE_READERS:
        return selected
    invocation = tools._current_invocation.get()
    if invocation is None or invocation[2:] != (name, arguments, operation_key):
        raise ValueError("a107_source_reader_requires_its_current_action")
    context = invocation[0]
    if tools.store.validate_scope(scope) != plain(context.scope):
        raise ValueError("a107_source_reader_scope_differs_from_its_action")
    return tuple(context.received_record_refs)
