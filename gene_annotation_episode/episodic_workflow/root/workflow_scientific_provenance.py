"""Preserved root host ports defined by WorkflowScientificProvenance."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from .communication import plain
from .receiving_context import BindingContext

class WorkflowScientificProvenance:

    def _scientific_provenance(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('scientific_provenance_receiver_identity_mismatch')
        provenance = self.workflow.scientific_provenance
        if provenance is None:
            raise ValueError('scientific_process_provenance_unavailable')
        return provenance

    def scientific_preparation(self, context, preparation_ref, *, owner='self'):
        provenance = self._scientific_provenance(context)
        reader = getattr(self.workflow.scientific_process_binding, 'read_scientific_preparation', None)
        if reader is not None:
            return reader(provenance, context, preparation_ref, owner=owner)
        return provenance.preparation(context, preparation_ref, owner=owner)

    def scientific_parent_preparation(self, context, preparation_ref):
        return self.scientific_preparation(context, preparation_ref, owner='parent')

    def scientific_received_results(self, context):
        return self._scientific_provenance(context).received_results(context)

    def scientific_frozen_results(self, context):
        return self._scientific_provenance(context).frozen_results(context)

    def scientific_closed_request(self, context: BindingContext) -> dict | None:
        """Read one completed invocation, without creating work or loading its tree."""
        workflow = self.workflow
        journal = workflow.journal
        if context.run_id != workflow.run_id or journal.run_id != workflow.run_id or context.role != 'scientific_process' or (EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_closed_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if row['run_id'] != context.run_id or row['episode_id'] != context.episode_id or json.loads(row['path']) != plain(context.path):
            raise ValueError('scientific_closed_request_identity_mismatch')
        if row['state'] != 'yielded' or row['completion'] is None or row['archive'] is None:
            return None
        closing = journal.row('runtime_forms', context.episode_id)
        if closing is None or closing['form'] is None:
            return None
        if closing['run_id'] != context.run_id or closing['episode_id'] != context.episode_id:
            raise ValueError('scientific_closed_request_identity_mismatch')
        completion, archive, form, request = (json.loads(value) for value in (row['completion'], row['archive'], closing['form'], row['request']))
        if not isinstance(completion, dict) or not completion or (not isinstance(archive, dict)) or (not archive) or (not isinstance(form, dict)) or (not isinstance(request, dict)):
            raise ValueError('scientific_closed_request_invalid')
        return request

    def scientific_parent_invocation(self, context):
        return self._scientific_provenance(context).parent_invocation(context)

    def scientific_reference(self, context, reference, namespace):
        return self._scientific_provenance(context).resolve(context, reference, namespace, credit_metadata=self.workflow.source_controller_credit(context))

