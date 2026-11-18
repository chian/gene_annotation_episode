"""Private A107 Results target_custody"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_VERSION
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
import hashlib
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_REQUEST_VERSION, canonical, hashlib, json, plain

class ResultsTargetCustody:

    def _context_target(self, context, target):
        if context.role == 'launch':
            launch = self._launch(plain(context.assignment), scope=context.scope)
            selected = target['assignment']
            resource_id = target['resource_id']
            request = launch['requests'].get(resource_id)
            if request is not None and request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._validate_blast_launch_selection(launch, selected, context.scope)
                handoff = self.api_execution._read_handoff(target['handle'], plain(context.scope))
                subject_ref = selected['request']['subject_ref']
                sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
                expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
                if handoff['snapshot']['request'].get('query_sha256') != expected:
                    raise ValueError('blast_grader_submitted_query_conflict')
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target

    def _blast_target_requirement(self, target, scope):
        """Rebuild the original BLAST return check from its launch request."""
        if target['resource_kind'] != 'api' or target['assignment'].get('service') != 'ncbi_blast':
            return None
        row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, target['origin_episode_id'])).fetchone()
        if row is None:
            raise ValueError('blast_grader_original_launch_missing')
        path = json.loads(row['path'])
        if len(path) < 2 or path[-2][0] != 'launch':
            raise ValueError('blast_grader_original_launch_path_invalid')
        parent = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND path=?', (self.run_id, canonical(path[:-1]))).fetchone()
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
        required_sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        required = {'return_type': request['return_type'], 'query_subject_ref': subject_ref, 'query_length': len(required_sequence), 'query_sha256': hashlib.sha256(required_sequence.encode()).hexdigest(), 'database': request.get('database')}
        prepared = self.api_execution.services[target['resource_id']].prepare('api.blast.prepare', selected['request'], {}, scope=plain(scope), previous_events=[])
        if prepared['sequence_sha256'] != required['query_sha256']:
            raise ValueError('blast_grader_selected_query_conflict')
        if required['database'] is not None and selected['request']['database'] != required['database']:
            raise ValueError('blast_grader_selected_database_conflict')
        handoff = self.api_execution._read_handoff(target['handle'], plain(scope))
        subject_ref = target['assignment']['request']['subject_ref']
        sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
        expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
        if handoff['snapshot']['request'].get('query_sha256') != expected:
            raise ValueError('blast_grader_submitted_query_conflict')
        return required
