"""Private execution_job_submission/api_job_execution BLAST request custody responsibility."""
from __future__ import annotations
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical, checked, obj
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_return_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA

class BlastRequestCustody:

    def _blast_launch_requirement(self, request, resource_id, scope):
        """Bind this launch's query and optional database from its parent request."""
        checked(request, BLAST_GRADED_REQUEST_SCHEMA,
                'blast_database_grader_return_request_invalid')
        if request['resource_id'] != resource_id:
            raise ValueError('blast_database_grader_resource_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        sequence = self.tool_registry._sequence(subject_ref,
            molecule_model=self.store.subject_molecule(subject_ref))
        return {'return_type': request['return_type'], 'query_subject_ref': subject_ref,
                'query_length': len(sequence),
                'query_sha256': hashlib.sha256(sequence.encode()).hexdigest(),
                'database': request.get('database')}

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
        prepared = self.api_execution.services[resource_id].prepare(
            'api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != required['query_sha256']:
            raise ValueError('blast_grader_selected_query_conflict')
        if required['database'] is not None and selected['request']['database'] != required['database']:
            raise ValueError('blast_grader_selected_database_conflict')

    def _validate_blast_api_parent_request(self, launch, selected, scope):
        """Bind this API child's selected search to its immediate parent goal."""
        resource_id = selected['resource_id']
        request = launch['requests'].get(resource_id)
        if request is None or request.get('version') != BLAST_GRADED_REQUEST_VERSION:
            return
        if selected.get('service') != 'ncbi_blast' or not self._permitted(launch, resource_id):
            raise ValueError('blast_grader_selected_service_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        sequence = self.tool_registry._sequence(subject_ref,
            molecule_model=self.store.subject_molecule(subject_ref))
        prepared = self.api_execution.services[resource_id].prepare(
            'api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != hashlib.sha256(sequence.encode()).hexdigest():
            raise ValueError('blast_grader_selected_query_conflict')
        if request.get('database') is not None and selected['request']['database'] != request['database']:
            raise ValueError('blast_grader_selected_database_conflict')
