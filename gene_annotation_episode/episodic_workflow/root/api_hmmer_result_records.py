"""Original acquired HMMER result identity and selected publication custody."""
from __future__ import annotations
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.library.provider_jobs import validate_remote_identity


class HMMERResultRecords:
    def result_identity(self, reference, scope):
        """Exact typed acquired content, independent of repeated custody timestamps.

        The source keeps every original byte and retrieval. Credit normalizes
        references only within that same original page publication, so another
        receipt of identical content cannot manufacture a new acquisition.
        """
        body = self.read_result(reference, scope)
        source = self.store.get(body['source_ref'])
        page = body['assignment']['selector']
        target = body['target']
        page_identity = digest({'resource_id': target['resource_id'], 'execution_id': target['execution_id'],
            'page': page['page'], 'page_size': page.get('page_size', target['assignment']['page_size']),
            'raw_sha256': hashlib.sha256(self.store.get_artifact(source['artifact_ref'])).hexdigest()})
        publication = set(body['record_refs'])
        cache = {body['source_ref']: {'record_type': 'source', 'page_content_identity': page_identity}}
        visiting = set()
        def record_value(ref):
            if ref in cache:
                return cache[ref]
            if ref in visiting:
                raise ValueError('cyclic_api_acquired_record_identity')
            visiting.add(ref)
            record = self.store.get(ref)
            value = {key: normalize(value) for key, value in record.items() if key not in {'id', 'origin'}}
            visiting.remove(ref)
            cache[ref] = value
            return value
        def normalize(value):
            if isinstance(value, str) and value in publication:
                return record_value(value)
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value
        return digest({'page_content_identity': page_identity, 'record': record_value(reference)})

    def read_result(self, reference, scope):
        """Qualify actual acquired records for their receiving parent, without I/O."""
        self.store.get(reference)
        rows = self.store.db.execute("SELECT action.* FROM api_execution_actions action, "
            "json_each(action.result,'$.record_refs') returned WHERE action.run_id=? "
            "AND action.name='api.hmmer.result' AND returned.value=? ORDER BY action.rowid",
            (self.run_id, reference)).fetchall()
        for row in rows:
            outcome = json.loads(row['result'])
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            manifest = self.store.db.execute('SELECT assignment,scope FROM api_execution_episodes '
                'WHERE run_id=? AND episode_id=?', (self.run_id, row['episode_id'])).fetchone()
            assignment, original_scope = json.loads(manifest['assignment']), json.loads(manifest['scope'])
            self.store.validate_scope(original_scope, parent_scope=plain(scope))
            if assignment.get('version') != 'execution_results_assignment_v1':
                raise ValueError('api_result_original_assignment_conflict')
            target = self.read_target(assignment['handoff_ref'], original_scope)
            selector = assignment['selector']
            from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
            original_context = BindingContext(self.run_id, row['episode_id'], 'results', (('results', 'original'),),
                original_scope, assignment, {})
            selected = self._selected(original_context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if (actual.get('status') != outcome['status'] or actual.get('record_refs') != outcome['record_refs']
                        or canonical(actual.get('result')) != canonical(outcome.get('result'))):
                    raise ValueError('api_result_runtime_outcome_conflict')
            episode = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (self.run_id, row['episode_id'])).fetchone()
            message = json.loads(episode['request']).get('message', {}) if episode is not None else {}
            if (canonical(message.get('episode_assignment', message.get('assignment'))) != canonical(assignment)
                    or canonical(message.get('scope')) != canonical(original_scope)):
                raise ValueError('api_result_original_episode_conflict')
            publication = self.store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?',
                (row['operation_key']+':publication',)).fetchone()
            if publication is None or publication['name'] != 'internal.hmmer.result_publication':
                raise ValueError('api_result_original_publication_missing')
            published = json.loads(publication['result'])
            if (published['record_refs'] != outcome['record_refs'] or published['status'] != outcome['status']
                    or publication['scope'] != canonical(original_scope)):
                raise ValueError('api_result_original_publication_conflict')
            source_ref = published['result']['source_ref']
            source = self.store.get(source_ref)
            request = self._artifact_json(source['request_ref'])['request']
            snapshot = self._load_snapshot(row['snapshot'])
            body = self._read_handoff(target['handle'], original_scope)
            if (self.store.get_artifact(source['artifact_ref']) != snapshot.content
                    or request != {**body['request'], 'job_id': target['execution_id'], 'page': selector['page'],
                        'page_size': selector.get('page_size', target['assignment']['page_size'])}):
                raise ValueError('api_result_original_request_conflict')
            validate_remote_identity(json.loads(snapshot.content), body['request'], target['execution_id'], result=True)
            return {'version': 'api_acquired_result_information_v1', 'reference': reference,
                'run_id': self.run_id, 'episode_id': row['episode_id'], 'scope': original_scope,
                'assignment': assignment, 'target': target, 'source_ref': source_ref,
                'record_refs': list(outcome['record_refs']), 'status': outcome['status']}
        raise ValueError('not_an_api_acquired_result')

