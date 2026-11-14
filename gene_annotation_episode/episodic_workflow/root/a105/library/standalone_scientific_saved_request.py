"""Original standalone authenticated saved-request reader."""
from __future__ import annotations
from ..communication import plain
import json
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext

def scientific_saved_request(services, context: BindingContext, *, active_only=True) -> dict | None:
        """Read an existing request; yielded requests can finish their first form."""
        if type(active_only) is not bool:
            raise ValueError('scientific_saved_request_active_flag_invalid')
        workflow = services.workflow
        journal = workflow.journal
        if context.run_id != workflow.run_id or journal.run_id != workflow.run_id or context.role != 'scientific_process' or (EpisodeRef(context.run_id, context.path).episode_id != context.episode_id):
            raise ValueError('scientific_saved_request_identity_mismatch')
        row = journal.row('runtime_episodes', context.episode_id)
        if row is None:
            return None
        if row['run_id'] != context.run_id or row['episode_id'] != context.episode_id or json.loads(row['path']) != plain(context.path):
            raise ValueError('scientific_saved_request_identity_mismatch')
        if row['state'] == 'active':
            if row['completion'] is not None or row['archive'] is not None:
                return None
        elif not active_only and row['state'] == 'yielded':
            if row['completion'] is None or row['archive'] is None:
                return None
            completion, archive = (json.loads(value) for value in (row['completion'], row['archive']))
            if not isinstance(completion, dict) or not completion or (not isinstance(archive, dict)) or (not archive):
                raise ValueError('scientific_saved_request_invalid')
        else:
            return None
        request = json.loads(row['request'])
        if not isinstance(request, dict):
            raise ValueError('scientific_saved_request_invalid')
        return request
