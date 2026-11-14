"""Preserved root host ports defined by WorkflowReferenceAccess."""
from __future__ import annotations
from .communication import plain

class WorkflowReferenceAccess:

    def reference_in_scope(self, reference, scope, namespace):
        store = self.workflow.store
        from gene_annotation_episode.enrichr_reference_privacy import enrichr_reference_restriction
        restriction = enrichr_reference_restriction(store, None, reference, namespace, private_only=True)
        if restriction is not None:
            return restriction
        from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
        restriction = molecular_reference_restriction(store, None, reference, namespace, private_only=True)
        if restriction is not None:
            return restriction
        if namespace in {'execution_handle', 'execution'}:
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        if not store.reference_subset([reference], plain(scope)):
            provider = getattr(self.workflow, 'progress_provider', None)
            return bool(provider is not None and provider.resolve(reference, plain(scope), namespace))
        kind = store.get(reference)['record_type']
        return not namespace or namespace == kind or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})

    def reference_in_context(self, context, reference, namespace):
        if context.run_id != self.workflow.run_id:
            raise ValueError('context_reference_receiver_identity_mismatch')
        molecular = self._molecular_reference_access(context, reference, namespace)
        if molecular is not None:
            return molecular
        protein = self.protein_structure_reference_access(context, reference, namespace)
        if protein is not None:
            return protein
        received = self.workflow.episode_bindings.resolve_received_reference(context, reference, namespace)
        if received is not None:
            return received
        native = getattr(self.workflow, 'native_event_information', None)
        if native is not None and native.resolve(context, reference, namespace):
            return True
        if namespace == 'native_event_target':
            return False
        return self.reference_in_scope(reference, context.scope, namespace)

