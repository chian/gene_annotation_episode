"""Admit the recursive monitor's requested progress into the original receipt index."""
from gene_annotation_episode.episodic_workflow.root.a102.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a102.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a102.method_loop.durable import content_digest
from .progress_records import _unique

def receive_progress(context, form, schema, operation_key, provider):
    if not isinstance(context.episode_id, str) or not context.episode_id or (not isinstance(operation_key, str)) or (not operation_key):
        raise ContractError('progress_delivery_identity_required')
    references = []

    def declared_reference(reference, namespace):
        if namespace == 'episode_progress':
            provider.read_progress(reference, context.scope)
            references.append(reference)
        return True
    validate_form(form, schema, declared_reference)
    references = _unique(references)
    signature = content_digest({'form': plain(form), 'schema': plain(schema), 'scope': plain(context.scope)})
    return provider._receive_progress(context.episode_id, references, signature, operation_key)
