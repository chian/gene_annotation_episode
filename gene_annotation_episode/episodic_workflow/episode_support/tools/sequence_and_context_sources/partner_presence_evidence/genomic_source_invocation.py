"""A107 original-action custody for genomic source acquisitions that read a received File/Source."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.episode_support.readers.partner_presence_evidence.received_inputs import ReceivedInputs


def authenticate_genomic_source_invocation(registry, name, arguments, scope, operation_key):
    """The current action's ``(ActionInvocation, ReceivedInputs)`` once its recorded decision selects it.

    The action bound by ``A107ToolRegistry.execute_async`` must be exactly this
    tool, arguments, operation key and scope, and the decision the episode
    recorded for this unit must select it (``ReceivedInputs.selected_action``).
    """
    invocation = registry._current_invocation.get()
    if invocation is None:
        raise ContractError('a107_genomic_source_current_invocation_required')
    context, reader, selected_name, selected_arguments, selected_key = invocation
    if (type(reader) is not ReceivedInputs or reader.invocation is not context or selected_name != name
            or canonical(selected_arguments) != canonical(arguments) or selected_key != operation_key
            or operation_key != context.operation_key
            or canonical(plain(context.scope)) != canonical(registry.store.validate_scope(scope))):
        raise ContractError('a107_genomic_source_selected_action_conflict')
    reader.selected_action()
    return context, reader
