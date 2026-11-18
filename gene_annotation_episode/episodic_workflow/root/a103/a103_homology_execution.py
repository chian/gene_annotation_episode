"""A103 BLAST launch, grader-return and root wait projections."""
from __future__ import annotations

import hashlib
import json
from .communication import plain
from .execution_contracts import canonical, checked, obj

TEXT = {'type': 'string', 'minLength': 1}
# A BLAST launch may request a graded database result while leaving the child
# free to select its search program and, unless constrained, its database.
# The original query operand is a required result identity, not a prewritten
# service command.  A submitted RID is an intermediate handoff; the grader is
# available after the separately selected results acquisition.
BLAST_GRADED_REQUEST_VERSION = 'blast_database_grader_return_request_v1'
BLAST_GRADED_REQUEST_SCHEMA = obj({
    'version': {'const': BLAST_GRADED_REQUEST_VERSION},
    'resource_id': TEXT,
    'return_type': {'const': 'blast_database_sheet_v1'},
    'query_subject_ref': TEXT,
    'database': TEXT,
}, ['version', 'resource_id', 'return_type', 'query_subject_ref'])
BLAST_GRADED_RETURN_SOURCE = 'ncbi_blast_database_grader_result'
BLAST_GRADED_RETURN_SCHEMA = {'type': 'array', 'items': obj({
    'result_ref': {'type': 'string', 'format': 'reference',
                   'x-reference-namespace': 'execution_result'},
    'grading_artifact_ref': {'type': 'string', 'format': 'reference',
                             'x-reference-namespace': 'artifact'},
    'sheet_schema': {'const': 'blast_database_sheet_v1'},
}), 'x-source': BLAST_GRADED_RETURN_SOURCE}

class A103HomologyExecution:
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
        from .tool_grading_artifacts import source_tool_grading_entries
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

    def _blast_scientific_owner(self, origin_episode_id):
        """Recover the annotation and axis assigned above one original launch."""
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, origin_episode_id)).fetchone()
        if row is None:
            raise ValueError('blast_original_launch_episode_unavailable')
        path = json.loads(row['path'])
        for length in range(len(path), 0, -1):
            if path[length - 1][0] != 'gene_context_evidence':
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

    @staticmethod
    def _blast_axis_summaries(jobs):
        """Keep root scheduling input at annotation/axis level."""
        grouped = {}
        for job in jobs:
            key = (job['proposed_annotation_ref'], job['evidence_axis'], job['subject_ref'])
            grouped.setdefault(key, []).append(job)
        summaries = []
        for annotation, axis, subject in sorted(grouped,
                key=lambda key: tuple('' if value is None else value for value in key)):
            rows = grouped[(annotation, axis, subject)]
            active = [row for row in rows if not row['result_received']
                and row['native_state'] not in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}]
            actionable = min(active, key=lambda row: (
                row['native_state'] != 'READY', row['observed_at'], row['handoff_ref'])) if active else None
            summaries.append({'proposed_annotation_ref': annotation, 'evidence_axis': axis,
                'subject_ref': subject, 'original_job_count': len(rows),
                'waiting_count': sum(row['native_state'] in {'accepted', 'WAITING'} for row in active),
                'ready_count': sum(row['native_state'] == 'READY' for row in active),
                'result_received_count': sum(row['result_received'] for row in rows),
                'failed_or_unknown_count': sum(row['native_state'] in
                    {'FAILED', 'UNKNOWN', 'failed', 'unknown'} for row in rows),
                'actionable_handoff_ref': None if actionable is None else actionable['handoff_ref'],
                'status_observed_at': None if actionable is None else actionable['observed_at'],
                'forecast_as_of': None if actionable is None else actionable['forecast_as_of'],
                'latest_progress_failure_code': (None if actionable is None else
                    actionable['latest_progress_failure_code']),
                'estimated_remaining_seconds': (None if actionable is None else
                    (actionable['wait_forecast'] or {}).get('estimated_remaining_seconds'))})
        return summaries

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

    @staticmethod
    def _blast_reference_source():
        return {'type': 'array', 'meaning':
            'Native paired BLAST source, observation and reference records actually returned through this boundary. '
            'References alone do not deliver unrequested numerical rows.',
            'report_schema': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
                'x-source': 'execution_blast_pairwise_result_refs'}}

