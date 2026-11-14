"""Private scientific_process/execution_job_submission BLAST received context responsibility."""
from __future__ import annotations
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical, checked, obj
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_return_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_axis_summaries import _blast_axis_summaries

class BlastReceivedContext:
    _blast_axis_summaries = staticmethod(_blast_axis_summaries)


    def _blast_scientific_owner(self, origin_episode_id):
        """Recover the annotation and axis assigned above one original launch."""
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, origin_episode_id)).fetchone()
        if row is None:
            raise ValueError('blast_original_launch_episode_unavailable')
        path = json.loads(row['path'])
        for length in range(len(path), 0, -1):
            if path[length - 1][0] != 'scientific_process':
                continue
            owner = self.store.db.execute('SELECT request FROM runtime_episodes '
                'WHERE run_id=? AND json(path)=json(?)',
                (self.run_id, json.dumps(path[:length]))).fetchone()
            if owner is None:
                raise ValueError('blast_scientific_owner_unavailable')
            assignment = json.loads(owner['request'])['message']['episode_assignment']
            return {'proposed_annotation_ref': assignment.get('proposed_annotation_ref'),
                    'evidence_axis': assignment['selection']['evidence_axis']['option_id']}
        return {'proposed_annotation_ref': None, 'evidence_axis': None}
