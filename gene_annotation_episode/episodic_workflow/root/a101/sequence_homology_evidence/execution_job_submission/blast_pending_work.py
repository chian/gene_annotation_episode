"""Private sequence_homology_evidence/execution_job_submission BLAST pending work responsibility."""
from __future__ import annotations
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical, checked, obj
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_return_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA

class BlastPendingWork:

    def annotation_axis_yield_context(self, context, credit):
        if (context.role != 'annotation' or self.api_execution is None
                or not any(service.service == 'ncbi_blast'
                    for service in self.api_execution.services.values())):
            return {}
        arms = credit.get('arms', [])
        unresolved = []
        for job in self.api_execution.received_blast_jobs(context, self.job_progress_provider):
            job.update(self._blast_scientific_owner(job['origin_episode_id']))
            if job['result_received'] or job['native_state'] in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}:
                continue
            matches = [arm for arm in arms
                if arm['proposed_annotation_ref'] == job['proposed_annotation_ref']
                and arm['axis'] == job['evidence_axis']
                and arm['subject_ref'] == job['subject_ref']]
            if len(matches) != 1:
                raise ValueError('blast_pending_job_requires_one_annotation_axis_arm')
            unresolved.append({**{name: matches[0][name] for name in
                ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')},
                'handoff_ref': job['handoff_ref'], 'native_state': job['native_state']})
        return {'unresolved_annotation_axis_credit': unresolved}
