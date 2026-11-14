"""Private execution_result_acquisition BLAST result grading responsibility."""
from __future__ import annotations
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical, checked, obj
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_return_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA

class BlastResultGrading:

    def _blast_target_requirement(self, target, scope):
        """Rebuild the original BLAST return check from its launch request."""
        if target['resource_kind'] != 'api' or target['assignment'].get('service') != 'ncbi_blast':
            return None
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, target['origin_episode_id'])).fetchone()
        if row is None:
            raise ValueError('blast_grader_original_launch_missing')
        path = json.loads(row['path'])
        if len(path) < 2 or path[-2][0] != 'launch':
            raise ValueError('blast_grader_original_launch_path_invalid')
        parent = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?',
            (self.run_id, canonical(path[:-1]))).fetchone()
        if parent is None:
            raise ValueError('blast_grader_original_parent_missing')
        launch = self._launch(json.loads(parent['request'])['message']['episode_assignment'], scope=scope)
        request = launch['requests'].get(target['resource_id'])
        if request is None or request.get('version') != BLAST_GRADED_REQUEST_VERSION:
            return None
        selected = target['assignment']
        if selected.get('service') != 'ncbi_blast':
            raise ValueError('blast_grader_selected_service_conflict')
        subject_ref = request['query_subject_ref']
        self.tool_registry._check_sequence_operand(subject_ref, plain(scope))
        required_sequence = self.tool_registry._sequence(subject_ref,
            molecule_model=self.store.subject_molecule(subject_ref))
        required = {'return_type': request['return_type'], 'query_subject_ref': subject_ref,
                    'query_length': len(required_sequence),
                    'query_sha256': hashlib.sha256(required_sequence.encode()).hexdigest(),
                    'database': request.get('database')}
        prepared = self.api_execution.services[target['resource_id']].prepare(
            'api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != required['query_sha256']:
            raise ValueError('blast_grader_selected_query_conflict')
        if required['database'] is not None and selected['request']['database'] != required['database']:
            raise ValueError('blast_grader_selected_database_conflict')
        handoff = self.api_execution._read_handoff(target['handle'], plain(scope))
        subject_ref = target['assignment']['request']['subject_ref']
        sequence = self.tool_registry._sequence(subject_ref,
            molecule_model=self.store.subject_molecule(subject_ref))
        expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
        if handoff['snapshot']['request'].get('query_sha256') != expected:
            raise ValueError('blast_grader_submitted_query_conflict')
        return required

    def _blast_grader_rows(self, context, result_refs, required):
        """Return only original retained database-grader results that meet the request."""
        from gene_annotation_episode.episodic_workflow.root.a101.tool_grading_artifacts import source_tool_grading_entries
        rows = []
        for reference in result_refs:
            body = self.api_execution.read_result(reference, context.scope)
            if body['target']['assignment'].get('service') != 'ncbi_blast':
                continue
            if body['target']['handle'] != plain(context.assignment)['handoff_ref']:
                raise ValueError('blast_grader_result_handoff_conflict')
            source = self.store.get(body['source_ref'])
            graders = source_tool_grading_entries(self.store, source['id'])
            if len(graders) != 1:
                raise ValueError('blast_grader_result_required')
            grading = graders[0]['grading']
            sheet = grading.get('sheet')
            if grading.get('failure') is not None or not isinstance(sheet, dict) or sheet.get('schema') != required['return_type']:
                raise ValueError('blast_grader_result_type_conflict')
            normalized = sheet.get('normalized_result') or {}
            query, search = normalized.get('query') or {}, normalized.get('search') or {}
            request = search.get('request') or {}
            if (normalized.get('mode') != 'database' or normalized.get('resource') != 'api'
                    or query.get('length') != required['query_length']
                    or request.get('sequence_sha256') != required['query_sha256']
                    or request.get('subject_ref') != body['service_request']['subject_ref']
                    or request.get('database') != body['service_request']['database']):
                raise ValueError('blast_grader_result_query_conflict')
            database = search.get('database')
            if not isinstance(database, str) or not database:
                raise ValueError('blast_grader_native_database_missing')
            if required['database'] is not None and database != required['database']:
                raise ValueError('blast_grader_result_database_conflict')
            rows.append({'result_ref': reference, 'grading_artifact_ref': graders[0]['artifact_ref'],
                         'sheet_schema': sheet['schema']})
        return rows
