"""Deterministic acquisition/publication inside the existing results episode.

This is an operation binding, not an episode or a private investigation loop.
The original selected action and its immutable receipt qualify every return.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError
from .execution_contracts import canonical, digest, obj
from .form_reference_validation import _binding_key, form_validation_value
from .infernal_native_result_views import (FAMILY_SOURCES, IDENTIFIER_NAMESPACES,
    row_schema, validate_native_infernal_result_selector)
from .local_jobs import LocalJobPolicy
from .native_infernal_acquisition import (ORIGIN, capture_local_bundle,
    is_native_infernal_target, publish_original_source, original_source_payload)
from .native_infernal_result_publication import (prepare_native_infernal_grading,
    publish_selected_native_infernal_rows)
from .practical_execution_state import _immutable, _read


VERSION = 'native_infernal_acquired_result_v1'


def operation_catalog():
    return [{'name': 'execution.results.status', 'description':
        'Observe the original native attempt once; this does not acquire numerical results.',
        'input_schema': obj({})},
        {'name': 'execution.results.collect', 'description':
        'Capture the original sealed Infernal bundle and complete files, populate deterministic numerical '
        'sheets, and return exactly the assigned native rows and metrics. No new search or retry.',
        'input_schema': obj({})}]


class NativeInfernalResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.directory = owner.directory/'native-infernal-result-index'

    def applies(self, context):
        return context.role == 'results' and is_native_infernal_target(self.owner._target(context))

    def _directory(self, context):
        return self.owner._result_directory(context)/'native-infernal-actions'

    def _action_directory(self, context, operation_key):
        directory = self._directory(context)/digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _validate_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key',
            'tool_name', 'arguments', 'target', 'observation', 'capture', 'prepared',
            'source_ref', 'record_refs', 'rows', 'failures', 'complete'}
        if (not isinstance(body, dict) or set(body) != fields or body['version'] != VERSION
                or body['run_id'] != self.owner.run_id):
            raise ContractError('native_infernal_result_receipt_invalid')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(
            body['assignment']['handoff_ref'], body['scope'])
        if target != body['target'] or not is_native_infernal_target(target):
            raise ContractError('native_infernal_result_original_target_conflict')
        selector = validate_native_infernal_result_selector(body['assignment']['selector'],
            program=target['assignment']['requested_job']['native_infernal']['program'])
        row = self.owner._selected_result_action(body['episode_id'], body['operation_key'],
            body['tool_name'], body['arguments'])
        if body['tool_name'] not in {entry['name'] for entry in operation_catalog()} or body['arguments'] != {}:
            raise ContractError('native_infernal_result_original_operation_conflict')
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (self.owner.run_id, body['episode_id'])).fetchone()
        if episode is None:
            raise ContractError('native_infernal_result_original_episode_missing')
        message = json.loads(episode['request'])['message']
        if (message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope']
                or json.loads(episode['path'])[-1][0] != 'results'):
            raise ContractError('native_infernal_result_original_assignment_conflict')
        directory = (self.owner.directory/'execution-results'/digest([self.owner.run_id, body['episode_id']])/
            'native-infernal-actions'/digest(body['operation_key']))
        if not (directory/'receipt.json').exists() or _read(directory/'receipt.json') != body:
            raise ContractError('native_infernal_result_original_receipt_conflict')
        if body['capture'] is not None and _read(directory/'capture'/'capture.json') != body['capture']:
            raise ContractError('native_infernal_result_capture_receipt_conflict')
        if body['prepared'] is not None and _read(directory/'grading'/'native-infernal-grading'/
                'prepared.json') != body['prepared']:
            raise ContractError('native_infernal_result_prepared_receipt_conflict')
        if row['result'] is not None:
            outcome = json.loads(row['result'])
            if (outcome.get('status') != 'completed' or outcome.get('result') != body
                    or outcome.get('record_refs') != body['record_refs']):
                raise ContractError('native_infernal_result_saved_outcome_conflict')
        if body['source_ref'] is not None:
            source = self.store.get(body['source_ref'])
            if (source.get('provider') != 'episode.execution_result'
                    or source.get('origin') != 'tool' or source.get('version') != 'native_infernal_bundle_v1'
                    or source['artifact_ref'] != body['capture']['bundle_artifact_ref']
                    or body['source_ref'] not in body['record_refs']):
                raise ContractError('native_infernal_result_original_source_conflict')
            bundle = json.loads(self.store.get_artifact(source['artifact_ref']))
            if (bundle['requested_job'] != target['assignment']['requested_job']
                    or bundle['identity']['run_id'] != self.owner.run_id
                    or bundle['identity']['execution_id'] != target['execution_id']
                    or bundle['identity']['resource_id'] != target['resource_id']):
                raise ContractError('native_infernal_result_original_bundle_conflict')
            expected_source = original_source_payload(bundle=bundle, capture=body['capture'], prepared=body['prepared'])
            if {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != expected_source:
                raise ContractError('native_infernal_result_source_content_conflict')
            prepared = body['prepared']
            if prepared is not None and prepared['source_grading_artifact_ref'] not in source['auxiliary_artifact_refs']:
                raise ContractError('native_infernal_result_grading_custody_conflict')
            if prepared is not None:
                publication = _read(directory/'publication.json')
                if publication['record_refs'] != body['record_refs'] or publication['rows'] != body['rows']:
                    raise ContractError('native_infernal_result_publication_receipt_conflict')
            for projected in body['rows']:
                from .domain import validate_schema
                validate_schema(projected, row_schema(selector['projection']['family']))
                if projected['source_ref'] != source['id']:
                    raise ContractError('native_infernal_result_row_source_conflict')
                reference = projected['observation_ref']
                if reference is None:
                    continue
                observation = self.store.get(reference)
                if (reference not in body['record_refs'] or observation.get('origin') != 'tool'
                        or observation.get('source_ref') != source['id']
                        or observation.get('subject_refs') != [projected['subject_ref']]
                        or observation.get('source_subject_refs') != projected['reference_refs']
                        or observation.get('native_infernal', {}).get('record_key') != projected['record_key']
                        or observation['native_infernal'].get('bundle_artifact_ref') != source['artifact_ref']):
                    raise ContractError('native_infernal_result_row_observation_conflict')
                values = {value['name']: value['value']['value'] for value in observation['measurements']}
                if any(values.get(value['name']) != value['value'] for value in projected['measurements']):
                    raise ContractError('native_infernal_result_row_measurement_conflict')
        elif body['record_refs'] or body['rows']:
            raise ContractError('native_infernal_result_source_required')
        complete = False
        if body['source_ref'] is not None and body['prepared'] is not None:
            complete = (body['capture']['complete'] and bundle['returncode'] == 0
                and not bundle['failures'] and body['prepared']['numerical_complete']
                and not any(row['status'] == 'invalid' for row in body['rows'])
                and body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0)
        if type(body['complete']) is not bool or body['complete'] != complete:
            raise ContractError('native_infernal_result_completion_conflict')
        return body

    def _index(self, body):
        for reference in body['record_refs']:
            directory = self.directory/digest(reference)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory/(digest(body['operation_key'])+'.json'), {
                'run_id': body['run_id'], 'episode_id': body['episode_id'],
                'operation_key': body['operation_key']})

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        selector = validate_native_infernal_result_selector(plain(context.assignment)['selector'],
            program=target['assignment']['requested_job']['native_infernal']['program'])
        directory = self._action_directory(context, operation_key)
        intent = {'target': target, 'assignment': plain(context.assignment), 'operation_key': operation_key,
            'tool_name': tool_name, 'arguments': arguments, 'scope': plain(context.scope)}
        _immutable(directory/'intent.json', intent)
        if (directory/'receipt.json').exists():
            body = self._validate_body(_read(directory/'receipt.json'), context.scope)
        else:
            if self.completion(context) is not None:
                raise ContractError('execution_results_assignment_already_completed')
            if not (directory/'observation.json').exists():
                observation = self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(directory/'observation.json', observation)
            observation = _read(directory/'observation.json')
            body = {'version': VERSION, 'run_id': context.run_id, 'episode_id': context.episode_id,
                'scope': plain(context.scope), 'assignment': plain(context.assignment),
                'operation_key': operation_key, 'tool_name': tool_name, 'arguments': arguments,
                'target': target, 'observation': observation, 'capture': None, 'prepared': None,
                'source_ref': None, 'record_refs': [], 'rows': [], 'failures': [], 'complete': False}
            if tool_name == 'execution.results.collect':
                capture = capture_local_bundle(self.store, target=target, directory=directory/'capture')
                body['capture'] = capture
                body['failures'].extend(capture['failures'])
                if capture['bundle_validated']:
                    bundle = json.loads(self.store.get_artifact(capture['bundle_artifact_ref']))
                    configuration = self.owner.resources[target['resource_id']]
                    policy = LocalJobPolicy(**configuration['policy'])
                    try:
                        prepared = prepare_native_infernal_grading(self.store, bundle=bundle,
                            bundle_artifact_ref=capture['bundle_artifact_ref'], artifacts=capture['artifacts'],
                            directory=directory/'grading', policy=policy, selector=selector)
                    except (ValueError, OSError) as error:
                        prepared = None
                        body['failures'].append({'stage': 'grading', 'code': str(error)
                            if isinstance(error, ValueError) else 'native_infernal_grading_unavailable', 'record_key': None})
                    body['prepared'] = prepared
                    source = publish_original_source(self.store, bundle=bundle, capture=capture, prepared=prepared)
                    body['source_ref'], body['record_refs'] = source, [source]
                    if prepared is not None:
                        if (directory/'publication.json').exists():
                            publication = _read(directory/'publication.json')
                        else:
                            publication = publish_selected_native_infernal_rows(self.store, source_ref=source, bundle=bundle,
                                prepared=prepared, scope=plain(context.scope), selector=selector)
                            _immutable(directory/'publication.json', publication)
                        body.update(record_refs=publication['record_refs'], rows=publication['rows'])
                        body['failures'].extend(publication['failures'])
                        body['complete'] = (capture['complete'] and bundle['returncode'] == 0
                            and not bundle['failures'] and prepared['numerical_complete']
                            and not any(row['status'] == 'invalid' for row in publication['rows'])
                            and observation['state'] == 'completed' and observation['returncode'] == 0)
            _immutable(directory/'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'],
            'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}

    def read_result(self, reference, scope, *, assignment=None):
        self.store.get(reference)
        directory = self.directory/digest(reference)
        if directory.exists():
            for path in sorted(directory.glob('*.json')):
                pointer = _read(path)
                if pointer.get('run_id') != self.owner.run_id:
                    raise ContractError('native_infernal_result_index_run_conflict')
                receipt = (self.owner.directory/'execution-results'/digest([self.owner.run_id, pointer['episode_id']])/
                    'native-infernal-actions'/digest(pointer['operation_key'])/'receipt.json')
                body = self._validate_body(_read(receipt), scope)
                if assignment is not None and body['assignment'] != plain(assignment):
                    continue
                if reference not in body['record_refs']:
                    raise ContractError('native_infernal_result_index_reference_conflict')
                return body
        raise ContractError('not_a_native_infernal_acquired_result')

    def _own_bodies(self, context):
        def load():
            directory = self._directory(context)
            bodies = [] if not directory.exists() else [_read(path) for path in directory.glob('*/receipt.json')]
            validated = []
            for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
                if (body['run_id'] != context.run_id or body['episode_id'] != context.episode_id
                        or body['assignment'] != plain(context.assignment) or body['scope'] != plain(context.scope)):
                    raise ContractError('native_infernal_result_owner_context_conflict')
                validated.append(self._validate_body(body, context.scope))
            return {'bodies': validated}
        # One synchronous form can mention each row in several reference
        # fields. Validate its original receipts once in that form's existing
        # frame; nothing survives the boundary or another selected action.
        yield from form_validation_value(('native_infernal_own_bodies', id(self),
            _binding_key(context)), load)['bodies']

    def facts(self, context):
        bodies = list(self._own_bodies(context))
        # A complete capture of a failed attempt is still useful custody, but
        # ORIGIN's successful-attempt qualification must not describe it.
        successful_capture = any(body['capture'] is not None and body['capture']['complete']
            and body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0
            and body['capture']['bundle_validated']
            and (lambda bundle: bundle['returncode'] == 0 and not bundle['failures'])(
                json.loads(self.store.get_artifact(body['capture']['bundle_artifact_ref'])))
            for body in bodies)
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [],
            'execution_result_refs': sorted({ref for body in bodies for ref in body['record_refs']}),
            'execution_infernal_result_refs': sorted({ref for body in bodies for ref in body['record_refs']}),
            'execution_result_origin': deepcopy(ORIGIN) if successful_capture else None,
            'execution_completed': any(body['complete'] for body in bodies),
            **{source: [] for source in FAMILY_SOURCES.values()}}
        fields = context.request.get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested = {field.get('x-source') for field in fields.values()}
        seen = set()
        for body in bodies:
            family = body['assignment']['selector']['projection']['family']
            source = FAMILY_SOURCES[family]
            if source not in requested:
                continue
            for row in body['rows']:
                key = row['source_ref'], row['record_key']
                if key not in seen:
                    result[source].append(row)
                    seen.add(key)
        return result

    def credit_view(self, context, receiver_selection):
        selection = plain(receiver_selection)
        known, initial = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        if not initial <= known:
            raise ContractError('native_infernal_initial_references_must_be_known')
        # A stable observation/source identity survives page and metric choices.
        # This retains the existing acquisition-unit scheme, not a new scientific score.
        acquired = {self.result_identity(ref, context.scope)
            for ref in set(self.facts(context)['execution_result_refs']) & known}
        inherited = set()
        for reference in initial:
            try:
                inherited.add(self.result_identity(reference, context.scope))
            except (ValueError, KeyError, OSError):
                pass
        count = len(acquired-inherited)
        value = self.owner.acquired_record_unit*count
        return {'credit': value, 'operational_credit': value, 'new_handoff_count': 0,
            'new_acquired_record_count': count, 'operational_credit_binding': {
                'version': VERSION, 'handoff_unit': self.owner.handoff_unit,
                'acquired_record_unit': self.owner.acquired_record_unit,
                'scientific_credit': False, 'monitoring_credit': False}}

    def result_identity(self, reference, scope):
        body = self.read_result(reference, scope)
        original = body['source_ref']
        bundle = body['capture']['bundle_artifact_ref']
        cache = {original: {'record_type': 'source', 'bundle_artifact_ref': bundle}}
        publication = set(body['record_refs'])
        visiting = set()
        def record(ref):
            if ref in cache:
                return cache[ref]
            if ref in visiting:
                raise ContractError('native_infernal_result_reference_cycle')
            visiting.add(ref)
            result = {key: normalize(value) for key, value in self.store.get(ref).items()
                if key not in {'id', 'origin'}}
            visiting.remove(ref)
            cache[ref] = result
            return result
        def normalize(value):
            if isinstance(value, str) and value in publication:
                return record(value)
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value
        return digest({'bundle_artifact_ref': bundle, 'record': record(reference)})

    def completion(self, context):
        for body in self._own_bodies(context):
            if not body['complete']:
                continue
            # Runtime must have completed the actual selected own action first.
            row = self.owner._selected_result_action(context.episode_id, body['operation_key'],
                body['tool_name'], body['arguments'])
            if row['result'] is None:
                continue
            return {'version': 'practical_completion_v1', 'run_id': context.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                'endpoint': 'usable_handoff', 'operation_key': body['operation_key'],
                'receipt_sha256': digest(body), 'validation_keys': ['original_native_attempt',
                    'complete_sealed_bundle_acquisition', 'requested_native_numerical_projection']}
        return None

    def resolve(self, context, reference, namespace):
        # Scientific receivers use their authenticated immediate-child forms.
        # An index/source in the Store must not expose unrequested sibling rows.
        if not self.applies(context):
            return False
        if namespace in IDENTIFIER_NAMESPACES:
            try:
                field = {'native_infernal_row': 'record_key',
                    'native_infernal_sequence_name': 'sequence_name',
                    'native_infernal_model_name': 'model_name'}[namespace]
                return any(row[field] == reference
                    for body in self._own_bodies(context) for row in body['rows'])
            except (ValueError, KeyError, OSError, TypeError):
                return False
        if namespace not in {None, 'source', 'execution_result'}:
            return False
        try:
            return (any(reference in body['record_refs'] for body in self._own_bodies(context))
                and (namespace != 'source' or self.store.get(reference)['record_type'] == 'source'))
        except (ValueError, KeyError, OSError, TypeError):
            return False


__all__ = ['NativeInfernalResults', 'operation_catalog', 'VERSION']
