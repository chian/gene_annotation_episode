"""Original selected-API file, snapshot and action custody, without transport.

These methods require the real owning API execution host and Store. This module
neither constructs that host nor grants publication or commissioning authority.
"""
from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
import hashlib
import json

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.immutable_json_records import _immutable, _read


EVENT_FIELDS = {'kind', 'state', 'native_handle', 'handoff_ready',
                'result_available', 'facts', 'failure_code'}
STATES = {'submitted', 'running', 'completed', 'failed', 'unknown'}


class APIServiceCustody:
    def _episode_directory(self, episode_id):
        return self.directory/'episodes'/digest(episode_id)

    def _manifest(self, context, *, create=True):
        directory = self._episode_directory(context.episode_id)
        body = {'run_id': self.run_id, 'episode_id': context.episode_id, 'role': context.role,
            'assignment': plain(context.assignment), 'scope': plain(context.scope)}
        path = directory/'assignment.json'
        if create:
            directory.mkdir(parents=True, exist_ok=True)
            (directory/'actions').mkdir(exist_ok=True)
            _immutable(path, body)
        if not path.exists() or _read(path) != body:
            raise ValueError('api_original_assignment_conflict')
        return directory

    def _selected(self, context, name, arguments, key):
        prefix = f'{self.run_id}:{context.episode_id}:'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('api_selected_action_identity_required')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? '
            'AND episode_id=? AND decision_index=?', (self.run_id, context.episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('api_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('api_selected_action_conflict')
        return row

    def _snapshot(self, snapshot):
        fields = asdict(snapshot)
        fields.pop('content')
        fields['content_ref'] = self.store.artifact(snapshot.content, snapshot.media_type)
        return json.loads(canonical(fields))

    def _load_snapshot(self, metadata):
        fields = deepcopy(metadata)
        fields['content'] = self.store.get_artifact(fields.pop('content_ref'))
        return SourceSnapshot(**fields)

    def _event(self, value):
        value = json.loads(canonical(value))
        if (set(value) != EVENT_FIELDS or value['kind'] not in {'response', 'job', 'preparation', 'metadata'}
                or value['state'] not in STATES or type(value['handoff_ready']) is not bool
                or type(value['result_available']) is not bool or not isinstance(value['facts'], dict)
                or value['native_handle'] is not None and not isinstance(value['native_handle'], dict)
                or value['failure_code'] is not None and not isinstance(value['failure_code'], str)):
            raise ValueError('invalid_api_service_native_event')
        if value['handoff_ready'] and value['state'] not in {'submitted', 'running', 'completed'}:
            raise ValueError('api_service_unusable_handoff_state')
        return value

    def _action_paths(self, episode_id):
        directory = self._episode_directory(episode_id)/'actions'
        # Directory names are hashes, not chronology. The immutable selected
        # operation key carries the episode's actual numerical decision index.
        return sorted(directory.glob('*/intent.json'),
            key=lambda path: int(_read(path)['operation_key'].rsplit(':', 1)[-1])) if directory.exists() else []

    def _events(self, episode_id):
        result = []
        for path in self._action_paths(episode_id):
            event_path = path.parent/'event.json'
            if event_path.exists():
                intent = _read(path)
                result.append({'name': intent['name'], 'prepared': intent['prepared'],
                    'event': _read(event_path), 'operation_key': intent['operation_key']})
        return sorted(result, key=lambda row: int(row['operation_key'].rsplit(':', 1)[-1]))

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        value = json.loads(raw)
        if raw != canonical(value).encode('utf-8') or reference != 'artifact_'+hashlib.sha256(raw).hexdigest():
            raise ValueError('api_service_artifact_identity_conflict')
        return value

    def _own_outcomes(self, context):
        for path in self._action_paths(context.episode_id):
            outcome_path = path.parent/'outcome.json'
            if outcome_path.exists():
                yield path.parent, _read(outcome_path)

    def _index_result(self, context, directory, outcome):
        for reference in outcome.get('record_refs', []):
            index = self.directory/'result-index'/digest(reference)
            index.mkdir(parents=True, exist_ok=True)
            _immutable(index/(directory.name+'.json'), {'episode_id': context.episode_id,
                'operation_key': _read(directory/'intent.json')['operation_key']})

