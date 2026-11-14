"""A107 BLAST launch, grader-return and root wait projections."""
from __future__ import annotations
from .library.blast_pairwise_return_schema import blast_pairwise_reference_source
from .library.received_blast_job_information import blast_scientific_owner, blast_axis_summaries
import hashlib
import json
from .communication import plain
from .execution_contracts import canonical, checked, obj
TEXT = {'type': 'string', 'minLength': 1}
BLAST_GRADED_REQUEST_VERSION = 'blast_database_grader_return_request_v1'
BLAST_GRADED_REQUEST_SCHEMA = obj({'version': {'const': BLAST_GRADED_REQUEST_VERSION}, 'resource_id': TEXT, 'return_type': {'const': 'blast_database_sheet_v1'}, 'query_subject_ref': TEXT, 'database': TEXT}, ['version', 'resource_id', 'return_type', 'query_subject_ref'])
BLAST_GRADED_RETURN_SOURCE = 'ncbi_blast_database_grader_result'
BLAST_GRADED_RETURN_SCHEMA = {'type': 'array', 'items': obj({'result_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'grading_artifact_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'artifact'}, 'sheet_schema': {'const': 'blast_database_sheet_v1'}}), 'x-source': BLAST_GRADED_RETURN_SOURCE}

class A107BlastExecution:

    def _blast_launch_requirement(self, request, resource_id, scope):
        """Bind this launch's query and optional database from its parent request."""
        checked(request, BLAST_GRADED_REQUEST_SCHEMA, 'blast_database_grader_return_request_invalid')
        if request['resource_id'] != resource_id:
            raise ValueError('blast_database_grader_resource_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        return {'return_type': request['return_type'], 'query_subject_ref': subject_ref, 'query_length': len(sequence), 'query_sha256': hashlib.sha256(sequence.encode()).hexdigest(), 'database': request.get('database')}

    def _validate_blast_launch_selection(self, launch, selected, scope):
        """Apply only this BLAST request's stated query/database constraints."""
        resource_id = selected['resource_id']
        if resource_id not in launch['requests'] or not self._permitted(launch, resource_id):
            raise ValueError('execution_resource_selection_conflict')
        request = launch['requests'][resource_id]
        if request.get('version') != BLAST_GRADED_REQUEST_VERSION:
            return
        required = self._blast_launch_requirement(request, resource_id, scope)
        if selected.get('service') != 'ncbi_blast':
            raise ValueError('blast_grader_selected_service_conflict')
        prepared = self.api_execution.services[resource_id].prepare('api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != required['query_sha256']:
            raise ValueError('blast_grader_selected_query_conflict')
        if required['database'] is not None and selected['request']['database'] != required['database']:
            raise ValueError('blast_grader_selected_database_conflict')
    _blast_scientific_owner = blast_scientific_owner
    _blast_axis_summaries = staticmethod(blast_axis_summaries)

    def annotation_axis_yield_context(self, context, credit):
        if context.role != 'annotation' or self.api_execution is None or (not any((service.service == 'ncbi_blast' for service in self.api_execution.services.values()))):
            return {}
        arms = credit.get('arms', [])
        unresolved = []
        for job in self.api_execution.received_blast_jobs(context, self.job_progress_provider):
            job.update(self._blast_scientific_owner(job['origin_episode_id']))
            if job['result_received'] or job['native_state'] in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}:
                continue
            matches = [arm for arm in arms if arm['proposed_annotation_ref'] == job['proposed_annotation_ref'] and arm['axis'] == job['evidence_axis'] and (arm['subject_ref'] == job['subject_ref'])]
            if len(matches) != 1:
                raise ValueError('blast_pending_job_requires_one_annotation_axis_arm')
            unresolved.append({**{name: matches[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}, 'handoff_ref': job['handoff_ref'], 'native_state': job['native_state']})
        return {'unresolved_annotation_axis_credit': unresolved}
    _blast_reference_source = staticmethod(blast_pairwise_reference_source)
