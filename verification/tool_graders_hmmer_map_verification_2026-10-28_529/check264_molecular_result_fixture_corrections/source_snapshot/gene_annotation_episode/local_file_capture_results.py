"""Selected local file custody within the existing results episode.

The retained stream has an exact byte identity. Neither the path, the job's
termination nor pinning an inode establishes a producing execution or an atomic
source version. Per-file Store commits survive later sibling failures.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .communication import plain
from .domain import identity
from .episode_bindings import BindingContext
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, checked, digest, obj
from .genomic_overlap_result_receipts import immutable, read_control
from .materials import source_for_artifact
from .native_file_capture import (
    NativeFileCaptureError, _identity, _label, _metadata, _path, capture_native_file, retained_native_file,
)
from .practical_execution_operations import confined


SELECTOR_VERSION = 'local_file_source_selector_v1'
RECEIPT_VERSION = 'execution_file_source_information_v1'
FILE_VERSION = 'execution_file_capture_v1'
FILE_PROVIDER = 'episode.execution_file'
RESULT_PROVIDER = 'episode.execution_result'
_TABLE = 'runtime_execution_file_captures'
_ACTIONS = 'runtime_execution_file_capture_admissions'
_TEXT = {'type': 'string', 'minLength': 1}
SELECTOR_SCHEMA = obj({'version': {'const': SELECTOR_VERSION}, 'files': {
    'type': 'array', 'minItems': 1, 'uniqueItems': True,
    'items': obj({'path': deepcopy(_TEXT), 'format': deepcopy(_TEXT)})}})
ORIGIN = {'content_location': 'current_resource_filesystem',
    'attempt_output_version': 'unverified',
    'read_consistency': 'pinned_regular_file_stream_not_atomic_snapshot',
    'writer_closure': 'not_established'}
SOURCE_REFS_SCHEMA = {'type': 'array', 'uniqueItems': True, 'items': {
    'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
    'x-source': 'execution_file_source_refs'}
_FAILURE_SCHEMA = {**obj({'code': deepcopy(_TEXT)}), 'type': ['object', 'null']}
OUTCOME_SCHEMA = obj({'version': {'type': 'string', 'const': 'execution_file_source_outcome_v1'},
    'operation': {'type': 'string', 'enum': ['execution.results.collect', 'execution.results.status']},
    'job': obj({'state': deepcopy(_TEXT), 'returncode': {'type': ['integer', 'null']},
        'failure_code': {'type': ['string', 'null']}}),
    'files': {'type': 'array', 'items': obj({'path': deepcopy(_TEXT), 'format': deepcopy(_TEXT),
        'source_ref': {'type': ['string', 'null'], 'format': 'reference',
            'x-reference-namespace': 'source'},
        'availability': {'type': 'string', 'enum': ['retained', 'unavailable', 'not_acquired']},
        'size_bytes': {'type': ['integer', 'null'], 'minimum': 0}, 'failure': deepcopy(_FAILURE_SCHEMA)})},
    'provenance': obj({key: {'type': 'string', 'const': value} for key, value in ORIGIN.items()}),
    'failure': deepcopy(_FAILURE_SCHEMA)})
OUTCOMES_SCHEMA = {'type': 'array', 'items': OUTCOME_SCHEMA,
    'x-source': 'execution_file_capture_outcomes'}


def _require(condition, code):
    if not condition:
        raise ValueError('execution_file_capture_' + code)


def is_file_source_selector(value):
    return isinstance(value, dict) and value.get('version') == SELECTOR_VERSION


def whole_file_bridge(store, file):
    """Freeze the exact digest already used by legacy complete byte windows."""
    raw_digest, encoded_digest, size = hashlib.sha256(), hashlib.sha256(b'"'), 0
    # Every nonfinal block has a multiple-of-three length: concatenated base64
    # is the encoding of the complete stream, including its final padding.
    with retained_native_file(store, file).open('rb') as stream:
        pending = b''
        while block := stream.read(3 * 262144):
            raw_digest.update(block)
            size += len(block)
            block = pending + block
            complete = len(block) // 3 * 3
            encoded_digest.update(base64.b64encode(block[:complete]))
            pending = block[complete:]
        encoded_digest.update(base64.b64encode(pending))
    encoded_digest.update(b'"')
    _require(size == file['size_bytes'] and raw_digest.hexdigest() == file['sha256'],
        'retained_bridge_identity_conflict')
    return {'offset': 0, 'returned_bytes': size, 'size_bytes': size,
        'bytes_base64_sha256': encoded_digest.hexdigest()}


def full_window_key(target, window):
    if window['offset'] != 0 or window['returned_bytes'] != window['size_bytes']:
        return None
    return (target['resource_id'], target['execution_id'], str(Path(window['path'])),
        window['size_bytes'], digest(window['bytes_base64']))


class LocalFileSourceResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.records = EpisodeReturnRecords(self.store, owner.run_id,
            failure_prefix='execution_file_capture_')
        with self.store.transaction():
            self.store.db.execute(f'''CREATE TABLE IF NOT EXISTS {_TABLE} (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                path TEXT NOT NULL, receipt TEXT NOT NULL, source_ref TEXT,
                PRIMARY KEY(run_id,episode_id,operation_key,path))''')
            self.store.db.execute(f'''CREATE TABLE IF NOT EXISTS {_ACTIONS} (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                admission TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,operation_key))''')

    def applies(self, context):
        return context.role == 'results' and is_file_source_selector(
            plain(context.assignment).get('selector'))

    def selector(self, assignment, target, *, validate_paths=True):
        value = checked(assignment['selector'], SELECTOR_SCHEMA,
            'execution_file_capture_invalid_selector')
        _require(target['resource_kind'] == 'local', 'local_resource_required')
        _require(set(target['assignment']['requested_job']) == {'argv', 'environment'},
            'generic_original_job_required')
        configuration = self.owner.resources[target['resource_id']]
        _require(configuration['kind'] == 'local', 'local_resource_required')
        seen = set()
        for row in value['files']:
            _require(_label(row['format']), 'invalid_selected_format')
            path = (confined(row['path'], target['assignment']['workspace'])
                if validate_paths else Path(row['path']))
            if validate_paths:
                confined(str(path), configuration['workspace'])
                _path(str(path.parent), absolute=True)
                _path(path.name, absolute=False)
            _require(str(path) not in seen, 'duplicate_selected_path')
            seen.add(str(path))
        return value

    def admit(self, context, assignment, target, *, validate_paths=True):
        self.records.authenticate(context, allow_unsaved=True)
        _require(assignment['handoff_ref'] in
            self.owner._selection(context)['known_record_refs'], 'handoff_not_received')
        self.store.validate_scope(plain(context.scope))
        self.store.validate_scope(target['scope'], parent_scope=plain(context.scope))
        return self.selector(assignment, target, validate_paths=validate_paths)

    def _paths(self, context, key):
        directory = self.owner._result_directory(context)
        return directory / (digest(key) + '.file-source.intent.json'), directory / (
            digest(key) + '.file-source.observation.json'), directory / (
            digest(key) + '.file-source.receipt.json')

    def _saved(self, context, key, path):
        row = self.store.db.execute(f'SELECT receipt,source_ref FROM {_TABLE} '
            'WHERE run_id=? AND episode_id=? AND operation_key=? AND path=?',
            (context.run_id, context.episode_id, key, path)).fetchone()
        return None if row is None else json.loads(row['receipt'])

    def _admission(self, context, target, key, *, initialize=False):
        row = self.store.db.execute(f'SELECT admission FROM {_ACTIONS} WHERE '
            'run_id=? AND episode_id=? AND operation_key=?',
            (context.run_id, context.episode_id, key)).fetchone()
        if row is None:
            _require(initialize, 'original_admission_missing')
            with self.store.transaction():
                # Another legitimate resume can have committed after our
                # optimistic read. Recheck under SQLite's writer ownership.
                current = self.store.db.execute(f'SELECT 1 FROM {_ACTIONS} WHERE '
                    'run_id=? AND episode_id=? AND operation_key=?',
                    (context.run_id, context.episode_id, key)).fetchone()
                if current is not None:
                    return self._admission(context, target, key)
                selector = self.admit(context, plain(context.assignment), target)
                value = {'context': context.as_record(), 'target': target, 'selector': selector,
                    'resolved_paths': {file['path']: str(confined(file['path'],
                        target['assignment']['workspace'])) for file in selector['files']}}
                self.store.db.execute(f'INSERT INTO {_ACTIONS} VALUES(?,?,?,?)',
                    (context.run_id, context.episode_id, key, canonical(value)))
            return value
        value = json.loads(row['admission'])
        _require(value['context'] == context.as_record() and value['target'] == target
            and value['selector'] == self.selector(plain(context.assignment), target, validate_paths=False)
            and set(value['resolved_paths']) == {file['path'] for file in value['selector']['files']},
            'original_admission_conflict')
        for resolved in value['resolved_paths'].values():
            path = Path(resolved)
            _path(str(path.parent), absolute=True)
            _path(path.name, absolute=False)
        return value

    def _public_outcome(self, context, body, reference):
        row = self.owner._selected_result_action(context.episode_id, body['operation_key'],
            body['tool_name'], {})
        if row['result'] is None:
            return  # The original selected action can still be uncommitted.
        value = json.loads(row['result'])
        _require(type(value) is dict, 'public_outcome_conflict')
        if 'pending_work_after_action' in value:
            from .waiting import validate_pending
            validate_pending(value.pop('pending_work_after_action'))
        _require(canonical(value) == canonical(self.outcome(body, reference)), 'public_outcome_conflict')

    @staticmethod
    def public_view(body):
        retained = {row['selection']['path']: row for row in body['captured_files']}
        files = []
        for selection in body['assignment']['selector']['files']:
            row = retained.get(selection['path'])
            available = row is not None and row['file'] is not None
            files.append({'path': selection['path'], 'format': selection['format'],
                'source_ref': row['source_ref'] if available else None,
                'availability': 'retained' if available else 'unavailable' if row is not None else 'not_acquired',
                'size_bytes': row['file']['size_bytes'] if available else None,
                'failure': row['failure'] if row is not None else None})
        observation = body['observation']
        value = {'version': 'execution_file_source_outcome_v1', 'operation': body['tool_name'],
            'job': {field: observation.get(field) for field in ('state', 'returncode', 'failure_code')},
            'files': files, 'provenance': deepcopy(ORIGIN), 'failure': body['failure']}
        return checked(value, OUTCOME_SCHEMA, 'execution_file_capture_public_projection_invalid')

    @staticmethod
    def outcome(body, reference):
        refs = [reference, *[row['source_ref'] for row in body['captured_files']
            if row['source_ref'] is not None]]
        return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': LocalFileSourceResults.public_view(body), 'feedback': None}

    def _validate_file(self, value, scope, *, verify_artifact=False):
        _require(type(value) is dict and set(value) == {'version', 'context', 'target',
            'operation_key', 'selection', 'observation', 'resolved_path', 'origin', 'file',
            'whole_file_bridge', 'failure', 'source_ref', 'source_payload'}, 'file_receipt_shape')
        context = BindingContext(**value['context'])
        self.records.authenticate(context)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        self.owner._selected_result_action(context.episode_id, value['operation_key'],
            'execution.results.collect', {})
        target = self.owner.job_progress_provider.targets.read_target(
            plain(context.assignment)['handoff_ref'], context.scope)
        _require(target == value['target'] and value['origin'] == ORIGIN
            and value['version'] == FILE_VERSION, 'original_file_context_conflict')
        selected = self.selector(plain(context.assignment), target, validate_paths=False)
        _require(value['selection'] in selected['files'], 'original_file_selection_conflict')
        admission = self._admission(context, target, value['operation_key'])
        _require(value['resolved_path'] == admission['resolved_paths'][value['selection']['path']],
            'original_file_access_conflict')
        saved = self._saved(context, value['operation_key'], value['selection']['path'])
        _require(saved == value, 'original_file_receipt_conflict')
        intent, observation, _ = self._paths(context, value['operation_key'])
        _require(read_control(intent) == {'context': context.as_record(), 'target': target,
            'operation_key': value['operation_key'], 'tool_name': 'execution.results.collect',
            'arguments': {}} and read_control(observation) == value['observation'],
            'original_file_intent_conflict')
        native = value['observation'].get('native', {})
        _require(native.get('terminal') is True and native.get('quiescent') is True,
            'original_observation_not_quiescent')
        _, _, wrapper_path = self._paths(context, value['operation_key'])
        wrapper = read_control(wrapper_path)
        action = self.owner._selected_result_action(context.episode_id, value['operation_key'],
            'execution.results.collect', {})
        if action['result'] is not None:
            _require(wrapper is not None and value in wrapper['captured_files'],
                'committed_file_wrapper_missing')
            artifact = 'artifact_' + hashlib.sha256(canonical(wrapper).encode()).hexdigest()
            payload = self._wrapper_payload(context, wrapper, artifact)
            reference = identity('source', {'origin': 'tool', 'record': payload})
            self._public_outcome(context, wrapper, reference)
        if value['file'] is not None:
            file = _identity(value['file'])
            _require(value['failure'] is None and file['format'] == value['selection']['format']
                and type(value['source_ref']) is str and value['source_payload'] is not None,
                'successful_file_relationship_conflict')
            metadata = _metadata(self.store, file['artifact_ref'])
            _require(metadata['sha256'] == file['sha256']
                and metadata['size'] == file['size_bytes'], 'retained_metadata_conflict')
            if verify_artifact:
                retained_native_file(self.store, file)
            bridge = value['whole_file_bridge']
            _require(type(bridge) is dict and set(bridge) == {
                'offset', 'returned_bytes', 'size_bytes', 'bytes_base64_sha256'}
                and type(bridge['bytes_base64_sha256']) is str
                and re.fullmatch(r'[0-9a-f]{64}', bridge['bytes_base64_sha256']) is not None
                and type(bridge['offset']) is int and bridge['offset'] == 0
                and type(bridge['returned_bytes']) is int and type(bridge['size_bytes']) is int
                and bridge['returned_bytes'] == bridge['size_bytes'] == value['file']['size_bytes'],
                'bridge_metadata_conflict')
            source = self.store.get(value['source_ref'])
            payload = value['source_payload']
            _require(source == {**payload, 'id': value['source_ref'],
                'record_type': 'source', 'origin': 'tool'}
                and value['source_ref'] == identity('source', {'origin': 'tool', 'record': payload})
                and payload['artifact_ref'] == value['file']['artifact_ref']
                and payload['provider'] == FILE_PROVIDER
                and payload['parent_source_refs'] == [plain(context.assignment)['handoff_ref']]
                and self.store.get_artifact(payload['request_ref']) == canonical(
                    {k: v for k, v in value.items() if k not in {'source_ref', 'source_payload'}}).encode(),
                'source_identity_conflict')
        else:
            _require(value['source_ref'] is None and value['source_payload'] is None
                and value['whole_file_bridge'] is None
                and value['failure'] == {'code': 'capture_file_unavailable'},
                'unavailable_file_relationship_conflict')
        return value

    def read_source(self, reference, scope, *, verify_artifact=False):
        source = self.store.get(reference)
        if source.get('provider') != FILE_PROVIDER:
            return None
        rows = self.store.db.execute(f'SELECT receipt FROM {_TABLE} WHERE run_id=? AND source_ref=?',
            (self.owner.run_id, reference)).fetchall()
        _require(len(rows) == 1, 'source_receipt_missing')
        return self._validate_file(json.loads(rows[0]['receipt']), scope,
            verify_artifact=verify_artifact)

    def _capture(self, context, target, selection, key, observation, admission):
        previous = self._saved(context, key, selection['path'])
        if previous is not None:
            return self._validate_file(previous, context.scope, verify_artifact=True)
        value = {'version': FILE_VERSION, 'context': context.as_record(), 'target': target,
            'operation_key': key, 'selection': selection, 'observation': observation,
            'resolved_path': admission['resolved_paths'][selection['path']],
            'origin': deepcopy(ORIGIN), 'file': None, 'whole_file_bridge': None, 'failure': None}
        # There is no all-files transaction around this commit. A later file's
        # failure cannot roll back an already authenticated successful sibling.
        with self.store.transaction():
            previous = self._saved(context, key, selection['path'])
            if previous is not None:
                return self._validate_file(previous, context.scope, verify_artifact=True)
            path = Path(value['resolved_path'])
            try:
                file = capture_native_file(self.store, directory=str(path.parent),
                    relative_path=path.name, format=selection['format'])
            except NativeFileCaptureError as error:
                if error.code != 'capture_file_unavailable':
                    raise
                value['failure'] = {'code': error.code}
            else:
                value['file'] = file
                value['whole_file_bridge'] = whole_file_bridge(self.store, file)
            source = None if value['file'] is None else source_for_artifact(self.store,
                value['file']['artifact_ref'], provider=FILE_PROVIDER, request=value,
                parent_source_refs=[plain(context.assignment)['handoff_ref']])
            value.update(source_ref=None if source is None else source['id'], source_payload=(
                None if source is None else {k: v for k, v in source.items()
                    if k not in {'id', 'record_type', 'origin'}}))
            self.store.db.execute(f'INSERT INTO {_TABLE} VALUES(?,?,?,?,?,?)',
                (context.run_id, context.episode_id, key, selection['path'], canonical(value), value['source_ref']))
        return value

    def _wrapper_payload(self, context, body, artifact):
        return {'provider': RESULT_PROVIDER, 'accession': 'execution_file_capture_' + digest([
            context.run_id, context.episode_id, body['operation_key']]), 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': RECEIPT_VERSION, 'retrieved_at': body['observation']['observed_at']}

    def _publish(self, context, body):
        artifact = self.store.artifact(canonical(body), 'application/json')
        source = self.store.put('source', self._wrapper_payload(context, body, artifact), origin='tool')
        return source['id']

    def read_wrapper(self, reference, scope, *, verify_artifact=False):
        source = self.store.get(reference)
        if source.get('provider') != RESULT_PROVIDER or source.get('version') != RECEIPT_VERSION:
            return None
        raw = self.store.get_artifact(source['artifact_ref'])
        body = json.loads(raw)
        _require(type(body) is dict and set(body) == {'version', 'context', 'assignment',
            'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'windows',
            'captured_files', 'failure'} and body['version'] == RECEIPT_VERSION,
            'wrapper_shape_conflict')
        context = BindingContext(**body['context'])
        self.records.authenticate(context)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        self.owner._selected_result_action(context.episode_id, body['operation_key'], body['tool_name'], {})
        target = self.owner.job_progress_provider.targets.read_target(
            plain(context.assignment)['handoff_ref'], context.scope)
        self.selector(plain(context.assignment), target, validate_paths=False)
        admission = self._admission(context, target, body['operation_key'])
        _, _, receipt = self._paths(context, body['operation_key'])
        _require(read_control(receipt) == body and body['target'] == target
            and body['assignment'] == plain(context.assignment) and body['windows'] == [],
            'wrapper_receipt_conflict')
        native = body['observation'].get('native', {})
        if body['tool_name'] == 'execution.results.collect' and native.get('terminal') is True and native.get('quiescent') is True:
            _require(body['failure'] is None and [row['selection'] for row in body['captured_files']]
                == admission['selector']['files'], 'wrapper_file_population_conflict')
        else:
            _require(body['captured_files'] == [] and body['failure'] == (
                None if body['tool_name'] == 'execution.results.status' else {
                    'code': 'execution_file_capture_original_execution_not_quiescent'}),
                'wrapper_unavailable_relationship_conflict')
        payload = self._wrapper_payload(context, body, source['artifact_ref'])
        _require(source == {**payload, 'id': reference, 'record_type': 'source', 'origin': 'tool'}
            and reference == identity('source', {'origin': 'tool', 'record': payload})
            and raw == canonical(body).encode(),
            'wrapper_source_conflict')
        for file in body['captured_files']:
            self._validate_file(file, scope, verify_artifact=verify_artifact)
        self._public_outcome(context, body, reference)
        return body

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.records.authenticate(context)
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        _require(tool_name in {'execution.results.status', 'execution.results.collect'} and arguments == {},
            'operation_conflict')
        # Only these local custody transitions are serialized. This is not an
        # episode lease or scheduler. File commits remain independent below.
        with self.store.transaction():
            intent_path, observation_path, receipt_path = self._paths(context, operation_key)
            immutable(intent_path, {'context': context.as_record(), 'target': target,
                'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments})
            body = read_control(receipt_path)
            admission = self._admission(context, target, operation_key, initialize=True)
        selector = admission['selector']
        if body is None:
            with self.store.transaction():
                observation = read_control(observation_path)
                if observation is None:
                    observation = self.owner.job_progress_provider.targets.observe_target(target,
                        operation_key=operation_key)
                    immutable(observation_path, observation)
            files, failure = [], None
            if tool_name == 'execution.results.collect':
                native = observation.get('native', {})
                if native.get('terminal') is True and native.get('quiescent') is True:
                    for selection in selector['files']:
                        files.append(self._capture(context, target, selection, operation_key, observation, admission))
                else:
                    failure = {'code': 'execution_file_capture_original_execution_not_quiescent'}
            body = {'version': RECEIPT_VERSION, 'context': context.as_record(),
                'assignment': plain(context.assignment), 'operation_key': operation_key,
                'tool_name': tool_name, 'arguments': {}, 'target': target, 'observation': observation,
                'windows': [], 'captured_files': files, 'failure': failure}
        with self.store.transaction():
            immutable(receipt_path, body)
            reference = self._publish(context, body)
        self.read_wrapper(reference, context.scope, verify_artifact=True)
        return self.outcome(body, reference)

    def complete(self, context, bodies):
        selected = self.selector(plain(context.assignment), self.owner._target(context), validate_paths=False)
        delivered = set()
        for body in bodies:
            if body.get('version') != RECEIPT_VERSION or body['assignment'] != plain(context.assignment):
                continue
            native = body['observation'].get('native', {})
            if native.get('terminal') is not True or native.get('quiescent') is not True:
                continue
            for row in body['captured_files']:
                if row['source_ref'] is not None:
                    self.read_source(row['source_ref'], context.scope)
                    delivered.add((row['selection']['path'], row['selection']['format']))
        return all((row['path'], row['format']) in delivered for row in selected['files'])

    def source_key(self, reference, scope):
        value = self.read_source(reference, scope)
        if value is None:
            return None
        file, target = value['file'], value['target']
        return (target['resource_id'], target['execution_id'],
            value['resolved_path'], file['size_bytes'],
            value['whole_file_bridge']['bytes_base64_sha256'])

    @staticmethod
    def _source_fields(schema, source='execution_file_source_refs'):
        return [name for name, node in plain(schema).get('properties', {}).items()
            if node.get('x-source') == source]

    def _received_returns(self, context, source):
        self.records.authenticate(context)
        rows = self.store.db.execute('SELECT decision_index,contract FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (context.run_id, context.episode_id))
        for row in rows:
            schema = json.loads(row['contract']).get('measurements', {}).get('schema', {})
            fields = self._source_fields(schema, source)
            if not fields:
                continue
            child, form, original_schema = self.records._attempt(context, row['decision_index'])
            _require(self._source_fields(original_schema, source) == fields, 'original_return_fields_conflict')
            yield child, form, original_schema, fields

    def received_sources(self, context):
        references = set()
        for _, form, original_schema, fields in self._received_returns(context, 'execution_file_source_refs'):
            for name in fields:
                node = original_schema['properties'][name]
                _require(node.get('type') == 'array'
                    and node.get('items', {}).get('x-reference-namespace') == 'source',
                    'typed_source_return_required')
                for reference in form[name]:
                    _require(self.read_source(reference, context.scope) is not None,
                        'received_capture_source_required')
                    references.add(reference)
        return sorted(references)

    def outcomes_for_context(self, context):
        if not self.applies(context):
            return self.received_outcomes(context) if context.role in {'annotation', 'scientific_process'} else []
        self.records.authenticate(context)
        values = {}
        for row in self.store.db.execute('SELECT decision_index,action,result FROM runtime_actions '
                'WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index',
                (context.run_id, context.episode_id)):
            action = json.loads(row['action'])
            if action.get('kind') != 'tool' or action.get('tool') not in {
                    'execution.results.collect', 'execution.results.status'}:
                continue
            outcome = json.loads(row['result'])
            if not isinstance(outcome, dict) or outcome.get('status') != 'completed':
                continue
            key = f'{context.run_id}:{context.episode_id}:{row["decision_index"]}'
            body = read_control(self._paths(context, key)[2])
            _require(body is not None, 'original_wrapper_missing')
            artifact = 'artifact_' + hashlib.sha256(canonical(body).encode()).hexdigest()
            reference = identity('source', {'origin': 'tool',
                'record': self._wrapper_payload(context, body, artifact)})
            body = self.read_wrapper(reference, context.scope)
            value = self.public_view(body)
            values.setdefault(canonical(value), value)
        return list(values.values())

    def received_outcomes(self, context):
        values = {}
        for child, form, _, fields in self._received_returns(context, 'execution_file_capture_outcomes'):
            expected = self.outcomes_for_context(child)
            for name in fields:
                _require(self.records._equal(form[name], expected), 'received_outcome_facts_conflict')
                for value in expected:
                    values.setdefault(canonical(value), value)
        return list(values.values())

    def admit_return(self, context, form, schema, operation_key):
        fields = self._source_fields(schema)
        outcomes = self._source_fields(schema, 'execution_file_capture_outcomes')
        if not fields and not outcomes:
            return []
        index = self.records._admission_index(context, operation_key)
        child, original, original_schema = self.records._attempt(context, index)
        _require(self.records._equal(original, form) and self.records._equal(original_schema, schema),
            'original_return_conflict')
        references = []
        for name in fields:
            node = original_schema['properties'][name]
            _require(node.get('type') == 'array'
                and node.get('items', {}).get('x-reference-namespace') == 'source',
                'typed_source_return_required')
            for reference in original[name]:
                _require(self.read_source(reference, context.scope) is not None,
                    'received_capture_source_required')
                if reference not in references:
                    references.append(reference)
        if outcomes:
            expected = self.outcomes_for_context(child)
            for name in outcomes:
                _require(self.records._equal(original[name], expected), 'received_outcome_facts_conflict')
                for value in expected:
                    for file in value['files']:
                        reference = file['source_ref']
                        if reference is not None:
                            _require(self.read_source(reference, context.scope) is not None,
                                'received_capture_source_required')
                            if reference not in references:
                                references.append(reference)
        return references

    def validate_received_report(self, context, form, schema):
        fields = self._source_fields(schema)
        if fields and context.role in {'annotation', 'scientific_process'}:
            expected = self.received_sources(context)
            _require(all(self.records._equal(form[name], expected) for name in fields),
                'received_source_facts_conflict')
        outcomes = self._source_fields(schema, 'execution_file_capture_outcomes')
        if outcomes and context.role in {'annotation', 'scientific_process'}:
            expected = self.received_outcomes(context)
            _require(all(self.records._equal(form[name], expected) for name in outcomes),
                'received_outcome_facts_conflict')

    def acquisition_counts(self, context, selection, results):
        """Count acquired information, with complete-file equivalence both ways.

        Only retained control/legacy-window metadata is read here. Partial
        windows are never joined into a supposedly atomic full-file version.
        """
        known = list(dict.fromkeys(selection['known_record_refs']))
        initial = set(selection['initial_known_record_refs'])
        captures = {}
        for reference in known:
            if self.store.get(reference).get('provider') == FILE_PROVIDER:
                captures[reference] = self.source_key(reference, context.scope)
        if not captures and not any(body.get('captured_files') for body in results.values()):
            return None  # Preserve the legacy-only projector exactly.

        def window_bundle(body):
            return (body['target']['resource_id'], body['target']['execution_id'], tuple(sorted(
                (row['path'], row['offset'], row['returned_bytes'], digest(row['bytes_base64']))
                for row in body['windows'])))

        def captured_keys(body):
            return [self.source_key(row['source_ref'], context.scope)
                for row in body.get('captured_files', []) if row['source_ref'] is not None]

        seen_windows, seen_files = set(), set()
        for reference in known:
            if reference not in initial:
                continue
            if reference in captures:
                seen_files.add(captures[reference])
            body = results.get(reference)
            if body is not None:
                seen_files.update(captured_keys(body))
                if body['windows']:
                    seen_windows.add(window_bundle(body))
                    seen_files.update(key for row in body['windows']
                        if (key := full_window_key(body['target'], row)) is not None)
        windows_count, files_count = 0, 0
        for reference in known:
            if reference in initial:
                continue
            if reference in captures:
                key = captures[reference]
                files_count += int(key not in seen_files)
                seen_files.add(key)
            body = results.get(reference)
            if body is None:
                continue
            for key in captured_keys(body):
                files_count += int(key not in seen_files)
                seen_files.add(key)
            if body['windows']:
                contribution = window_bundle(body)
                keys = [full_window_key(body['target'], row) for row in body['windows']]
                covered = all(key is not None and key in seen_files for key in keys)
                windows_count += int(contribution not in seen_windows and not covered)
                seen_windows.add(contribution)
                seen_files.update(key for key in keys if key is not None)
        return windows_count, files_count


__all__ = ['LocalFileSourceResults', 'SELECTOR_SCHEMA', 'SELECTOR_VERSION',
    'RECEIPT_VERSION', 'FILE_PROVIDER', 'is_file_source_selector', 'full_window_key',
    'SOURCE_REFS_SCHEMA', 'OUTCOMES_SCHEMA']
