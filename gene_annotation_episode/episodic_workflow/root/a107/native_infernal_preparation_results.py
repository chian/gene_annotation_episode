"""Selected preparation-result acquisition within the existing results episode.

Native execution, retained-file grading and requested projection have separate
contracts. This binding records one own action; it creates no biological
observation or annotation score and chooses no retry or resource.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import ContractError
from .execution_contracts import canonical, digest, obj
from .form_reference_validation import _binding_key, form_validation_value
from .infernal_preparation_result_views import (
    IDENTIFIER_NAMESPACES, preparation_fact_sources, validate_preparation_result_selector,
)
from .local_jobs import LocalJobPolicy
from .native_hmmer_acquisition import ORIGIN
from .native_infernal_preparation_acquisition import (
    capture_local_bundle, is_native_infernal_preparation_target,
    original_source_payload, publish_original_source,
)
from .native_infernal_preparation_result_publication import (
    prepare_native_infernal_preparation_grading, publish_selected_preparation_result,
    validate_prepared_grading, validate_publication,
)
from .native_infernal_preparation_failure_views import preparation_failure_facts
from .practical_execution_state import _immutable, _read


VERSION = 'native_infernal_preparation_acquired_result_v1'
PREFIX = 'execution_infernal_preparation_'


def operation_catalog():
    return [
        {'name': 'execution.results.status', 'description':
            'Observe the original preparation attempt once without acquiring or grading its outputs.',
         'input_schema': obj({})},
        {'name': 'execution.results.collect', 'description':
            'Retain the original preparation bundle and complete declared files; populate deterministic '
            'sheets and calculations and return only the assigned quantities, checks and artifacts. '
            'Generated samples remain generated samples. No new native execution or retry.',
         'input_schema': obj({})},
    ]


def _require(condition, code):
    if not condition:
        raise ContractError('native_infernal_preparation_result_' + code)


def _selector(assignment, target):
    job = target['assignment']['requested_job']['native_infernal_preparation']
    return validate_preparation_result_selector(assignment['selector'],
        program=job['program'], mode=job['mode'])


def _complete(body, bundle):
    # Missing/unknown numerical cells and failed diagnostic checks are valid
    # information. Completion is acquisition of the requested practical output,
    # never a scientific acceptance test of those values.
    population = body['population']
    return bool(bundle is not None and body['capture']['complete']
        and bundle['returncode'] == 0 and not bundle['failures']
        and body['prepared'] is not None and body['prepared']['graded']
        and population is not None and not population['missing_record_keys']
        and not population['missing_artifacts']
        and body['observation']['state'] == 'completed'
        and body['observation']['returncode'] == 0)


class NativeInfernalPreparationResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.directory = owner.directory / 'native-infernal-preparation-result-index'

    def applies(self, context):
        return (context.role == 'results'
            and is_native_infernal_preparation_target(self.owner._target(context)))

    def _directory(self, context):
        return self.owner._result_directory(context) / 'native-infernal-preparation-actions'

    def _saved_directory(self, episode_id, operation_key):
        return (self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id])
            / 'native-infernal-preparation-actions' / digest(operation_key))

    def _policy(self, target):
        return LocalJobPolicy(**self.owner.resources[target['resource_id']]['policy'])

    def _validate_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key',
            'tool_name', 'arguments', 'target', 'observation', 'capture', 'prepared',
            'source_ref', 'record_refs', 'rows', 'artifacts', 'population', 'failures', 'complete'}
        _require(isinstance(body, dict) and set(body) == fields and body['version'] == VERSION
            and body['run_id'] == self.owner.run_id, 'receipt_invalid')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(
            body['assignment']['handoff_ref'], body['scope'])
        _require(target == body['target'] and is_native_infernal_preparation_target(target),
            'original_target_conflict')
        selector = _selector(body['assignment'], target)
        _require(body['tool_name'] in {row['name'] for row in operation_catalog()}
            and body['arguments'] == {}, 'original_operation_conflict')
        selected = self.owner._selected_result_action(body['episode_id'], body['operation_key'],
            body['tool_name'], body['arguments'])
        episode = self.store.db.execute('SELECT request,path FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (self.owner.run_id, body['episode_id'])).fetchone()
        _require(episode is not None, 'original_episode_missing')
        message = json.loads(episode['request'])['message']
        _require(message.get('episode_assignment') == body['assignment']
            and message['scope'] == body['scope'] and json.loads(episode['path'])[-1][0] == 'results',
            'original_assignment_conflict')
        directory = self._saved_directory(body['episode_id'], body['operation_key'])
        _require(_read(directory / 'receipt.json') == body, 'original_receipt_conflict')
        _require(_read(directory / 'intent.json') == {key: body[key] for key in (
            'target', 'assignment', 'operation_key', 'tool_name', 'arguments', 'scope')},
            'original_intent_conflict')
        _require(_read(directory / 'observation.json') == body['observation'], 'observation_conflict')
        if selected['result'] is not None:
            outcome = json.loads(selected['result'])
            _require(outcome.get('status') == 'completed' and outcome.get('result') == body
                and outcome.get('record_refs') == body['record_refs'], 'saved_outcome_conflict')
        bundle = None
        if body['capture'] is not None:
            # Require the existing receipt before entering acquisition's replay
            # path. Validation never performs a first capture or native read.
            _require((directory / 'capture' / 'capture.json').is_file(), 'capture_receipt_missing')
            _require(capture_local_bundle(self.store, target=target, directory=directory / 'capture')
                == body['capture'], 'capture_receipt_conflict')
        if body['source_ref'] is not None:
            _require(body['capture'] is not None and body['capture']['bundle_validated'], 'source_capture_required')
            bundle = json.loads(self.store.get_artifact(body['capture']['bundle_artifact_ref']))
            source = self.store.get(body['source_ref'])
            expected = original_source_payload(bundle=bundle, capture=body['capture'], prepared=body['prepared'])
            _require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
                and {k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}} == expected,
                'source_content_conflict')
            _require(body['source_ref'] in body['record_refs'], 'source_reference_missing')
        else:
            _require(not body['record_refs'] and not body['rows'] and not body['artifacts']
                and body['population'] is None and body['prepared'] is None, 'source_required')
        if body['prepared'] is not None:
            validate_prepared_grading(self.store, body['prepared'], bundle=bundle, verify_files=True)
            if body['population'] is not None:
                publication = _read(directory / 'publication.json')
                validate_publication(self.store, publication, source_ref=body['source_ref'],
                    prepared=body['prepared'], selector=selector,
                    directory=directory / 'projection', policy=self._policy(target))
                _require(all(body[key] == publication[key] for key in (
                    'record_refs', 'rows', 'artifacts', 'population')), 'publication_receipt_conflict')
            else:
                _require(body['record_refs'] == [body['source_ref']] and not body['rows']
                    and not body['artifacts'], 'publication_required')
        elif body['source_ref'] is not None:
            _require(body['record_refs'] == [body['source_ref']] and not body['rows']
                and not body['artifacts'] and body['population'] is None, 'grading_required')
        _require(type(body['complete']) is bool and body['complete'] == _complete(body, bundle),
            'completion_conflict')
        return body

    def _index(self, body):
        for reference in body['record_refs']:
            directory = self.directory / digest(reference)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'), {
                'run_id': body['run_id'], 'episode_id': body['episode_id'],
                'operation_key': body['operation_key']})

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        _require(self.applies(context) and target == self.owner._target(context), 'original_target_conflict')
        _require(tool_name in {row['name'] for row in operation_catalog()} and arguments == {},
            'original_operation_conflict')
        selector = _selector(plain(context.assignment), target)
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        intent = {'target': target, 'assignment': plain(context.assignment), 'operation_key': operation_key,
            'tool_name': tool_name, 'arguments': arguments, 'scope': plain(context.scope)}
        _immutable(directory / 'intent.json', intent)
        if (directory / 'receipt.json').exists():
            body = self._validate_body(_read(directory / 'receipt.json'), context.scope)
        else:
            _require(self.completion(context) is None, 'assignment_already_completed')
            if not (directory / 'observation.json').exists():
                observation = self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                _immutable(directory / 'observation.json', observation)
            observation = _read(directory / 'observation.json')
            body = {'version': VERSION, 'run_id': context.run_id, 'episode_id': context.episode_id,
                **intent, 'observation': observation, 'capture': None, 'prepared': None,
                'source_ref': None, 'record_refs': [], 'rows': [], 'artifacts': [], 'population': None,
                'failures': [], 'complete': False}
            if tool_name == 'execution.results.collect':
                capture = capture_local_bundle(self.store, target=target, directory=directory / 'capture')
                body['capture'] = capture
                body['failures'].extend(capture['failures'])
                if capture['bundle_validated']:
                    bundle = json.loads(self.store.get_artifact(capture['bundle_artifact_ref']))
                    policy = self._policy(target)
                    try:
                        prepared = prepare_native_infernal_preparation_grading(self.store,
                            target=target, capture=capture, capture_directory=directory / 'capture',
                            directory=directory / 'grading', policy=policy)
                    except (ValueError, OSError) as error:
                        prepared = None
                        body['failures'].append({'stage': 'grading', 'code': str(error)
                            if isinstance(error, ValueError) else 'retained_grading_unavailable', 'record_key': None})
                    body['prepared'] = prepared
                    source = publish_original_source(self.store, bundle=bundle, capture=capture, prepared=prepared)
                    body['source_ref'], body['record_refs'] = source, [source]
                    if prepared is not None:
                        body['failures'].extend(prepared['failures'])
                    if prepared is not None:
                        try:
                            publication = publish_selected_preparation_result(self.store, source_ref=source,
                                prepared=prepared, selector=selector, directory=directory / 'projection', policy=policy)
                        except (ValueError, OSError) as error:
                            body['failures'].append({'stage': 'projection', 'code': str(error)
                                if isinstance(error, ValueError) else 'retained_projection_unavailable', 'record_key': None})
                        else:
                            _immutable(directory / 'publication.json', publication)
                            body.update({key: publication[key] for key in ('record_refs', 'rows', 'artifacts', 'population')})
                            body['failures'].extend(publication['failures'])
                    body['complete'] = _complete(body, bundle)
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'],
            'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}

    def read_result(self, reference, scope, assignment=None):
        directory = self.directory / digest(reference)
        for path in sorted(directory.glob('*.json')) if directory.exists() else ():
            row = _read(path)
            _require(row['run_id'] == self.owner.run_id, 'index_run_conflict')
            body = self._validate_body(_read(self._saved_directory(row['episode_id'],
                row['operation_key']) / 'receipt.json'), scope)
            if assignment is not None and body['assignment'] != plain(assignment):
                continue
            _require(reference in body['record_refs'], 'index_reference_conflict')
            return body
        raise ContractError('not_a_native_infernal_preparation_acquired_result')

    def _own_bodies(self, context):
        def load():
            directory = self._directory(context)
            bodies = [_read(path) for path in directory.glob('*/receipt.json')] if directory.exists() else []
            result = []
            for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
                _require(body['run_id'] == context.run_id and body['episode_id'] == context.episode_id
                    and body['assignment'] == plain(context.assignment) and body['scope'] == plain(context.scope),
                    'owner_context_conflict')
                result.append(self._validate_body(body, context.scope))
            return {'bodies': result}
        yield from form_validation_value(('native_infernal_preparation_own_bodies', id(self),
            _binding_key(context)), load)['bodies']

    def facts(self, context):
        bodies = list(self._own_bodies(context))
        references = list(dict.fromkeys(ref for body in bodies for ref in body['record_refs']))
        captured = any(body['capture'] is not None and body['capture']['complete']
            and body['capture']['bundle_validated'] and body['observation']['state'] == 'completed'
            and body['observation']['returncode'] == 0
            and (lambda bundle: bundle['returncode'] == 0 and not bundle['failures'])(
                json.loads(self.store.get_artifact(body['capture']['bundle_artifact_ref'])))
            for body in bodies)
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [],
            'execution_result_refs': references, PREFIX + 'result_refs': references,
            'execution_result_origin': deepcopy(ORIGIN) if captured else None,
            'execution_completed': any(body['complete'] for body in bodies),
            **{PREFIX + name: [] for name in ('rows', 'artifacts', 'population', 'failures')}}
        fields = context.request.get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested = {field.get('x-source') for field in fields.values()}
        for name in ('rows', 'artifacts', 'population', 'failures'):
            source, seen = PREFIX + name, set()
            if source not in requested:
                continue
            for body in bodies:
                if name == 'failures':
                    capture = body['capture']
                    bundle = (json.loads(self.store.get_artifact(capture['bundle_artifact_ref']))
                        if capture is not None and capture['bundle_validated'] else None)
                    values = preparation_failure_facts(body, bundle=bundle)
                else:
                    values = ([body[name]] if body[name] is not None else []) if name == 'population' else body[name]
                for value in values:
                    identity = canonical(value)
                    if identity not in seen:
                        result[source].append(deepcopy(value))
                        seen.add(identity)
        return result

    def result_identity(self, reference, scope):
        body = self.read_result(reference, scope)
        return body['capture']['bundle_artifact_ref']

    def retained_reference_access(self, context, reference, namespace):
        """Do not let original source custody authorize unrequested file data.

        Query only record metadata. The exact own-result and immediate-child
        forms authorize selected references. Independently supplied or actually
        delivered references retain their normal resolver; old source-expanded
        receipt membership alone is deliberately insufficient.
        """
        if context.role not in {'results', 'annotation', 'scientific_process'} or namespace not in {
                None, 'source', 'artifact', 'execution_result'}:
            return None
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        version = 'native_infernal_preparation_bundle_v1'
        if record['record_type'] == 'source':
            owns = record.get('provider') == 'episode.execution_result' and record.get('version') == version
        elif record['record_type'] == 'artifact':
            owns = self.store.db.execute("SELECT 1 FROM records r WHERE r.record_type='source' "
                "AND json_extract(r.data,'$.provider')='episode.execution_result' "
                "AND json_extract(r.data,'$.version')=? AND (json_extract(r.data,'$.artifact_ref')=? "
                "OR EXISTS (SELECT 1 FROM json_each(r.data,'$.auxiliary_artifact_refs') a WHERE a.value=?)) LIMIT 1",
                (version, reference, reference)).fetchone() is not None
        else:
            return None
        if not owns:
            return None
        if context.role in {'annotation', 'scientific_process'}:
            received = self.owner.native_infernal_preparation_returns.resolve_received_reference_metadata(
                context, reference, namespace)
            if received is not None:
                return received
        # Only the operation's explicit return references count here. Traversing
        # a returned source's metadata is the original leak this guard prevents.
        explicit = self.store.db.execute("SELECT a.decision_index,a.result FROM runtime_actions a "
            "JOIN json_each(a.result,'$.record_refs') refs WHERE a.run_id=? AND a.episode_id=? "
            "AND json_extract(a.result,'$.status') IN ('completed','partial') AND refs.value=?",
            (self.owner.run_id, context.episode_id, reference)).fetchall()
        for action in explicit:
            outcome = json.loads(action['result'])
            body = outcome.get('result')
            if (context.role != 'results' or not isinstance(body, dict)
                    or body.get('version') != VERSION):
                continue
            # Check the original compact operation, not its complete scientific
            # artifacts. Absence from explicit record_refs needs no byte reads.
            self.owner.native_infernal_preparation_returns.authenticate(context)
            key = f'{self.owner.run_id}:{context.episode_id}:{action["decision_index"]}'
            _require(body.get('run_id') == context.run_id
                and body.get('episode_id') == context.episode_id
                and body.get('scope') == plain(context.scope)
                and body.get('assignment') == plain(context.assignment)
                and body.get('operation_key') == key
                and body.get('record_refs') == outcome['record_refs'], 'owner_context_conflict')
            self.owner._selected_result_action(context.episode_id, key,
                body['tool_name'], body['arguments'])
            directory = self._saved_directory(context.episode_id, key)
            _require(_read(directory / 'receipt.json') == body, 'original_receipt_conflict')
            _require(_read(directory / 'intent.json') == {name: body[name] for name in (
                'target', 'assignment', 'operation_key', 'tool_name', 'arguments', 'scope')},
                'original_intent_conflict')
            return namespace in {None, 'execution_result', record['record_type']}
        if reference in self.store._refs(plain(context.assignment)):
            return None
        for subject in context.scope['subject_refs']:
            if reference in self.store._refs(self.store.get(subject)):
                return None
        return None if explicit else False

    def credit_view(self, context, receiver_selection):
        selection = plain(receiver_selection)
        known, initial = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        _require(initial <= known, 'initial_references_must_be_known')
        # Count the acquired original result once, never its number of files,
        # quantities or validation checks. Repeated selections of the same
        # bundle cannot earn another acquisition unit.
        acquired = {body['capture']['bundle_artifact_ref'] for body in self._own_bodies(context)
            if body['source_ref'] is not None and body['source_ref'] in known}
        inherited = set()
        for reference in initial:
            if self.store.get(reference).get('version') == 'native_infernal_preparation_bundle_v1':
                inherited.add(self.result_identity(reference, context.scope))
        count = len(acquired - inherited)
        value = self.owner.acquired_record_unit * count
        return {'credit': value, 'operational_credit': value, 'new_handoff_count': 0,
            'new_acquired_record_count': count, 'operational_credit_binding': {
                'version': VERSION, 'handoff_unit': self.owner.handoff_unit,
                'acquired_record_unit': self.owner.acquired_record_unit,
                'scientific_credit': False, 'monitoring_credit': False}}

    def completion(self, context):
        for body in self._own_bodies(context):
            if not body['complete']:
                continue
            selected = self.owner._selected_result_action(context.episode_id, body['operation_key'],
                body['tool_name'], body['arguments'])
            if selected['result'] is None:
                continue
            return {'version': 'practical_completion_v1', 'run_id': context.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                'endpoint': 'usable_handoff', 'operation_key': body['operation_key'],
                'receipt_sha256': digest(body), 'validation_keys': ['original_native_attempt',
                    'complete_sealed_bundle_acquisition', 'requested_preparation_projection']}
        return None

    def resolve(self, context, reference, namespace):
        if not self.applies(context):
            return False
        bodies = list(self._own_bodies(context))
        if namespace in IDENTIFIER_NAMESPACES:
            if namespace in {'native_infernal_preparation_failure_code', 'native_infernal_preparation_failure_record'}:
                field = 'code' if namespace.endswith('_code') else 'record_key'
                return any(row[field] == reference for row in self.facts(context)[PREFIX + 'failures'])
            if namespace == 'native_infernal_preparation_sha256':
                return any(row['sha256'] == reference for body in bodies for row in body['artifacts'])
            field = {'native_infernal_preparation_row': 'record_key',
                'native_infernal_preparation_name': 'name',
                'native_infernal_preparation_accession': 'accession'}[namespace]
            return (any(row[field] == reference for body in bodies for row in body['rows'])
                or field == 'record_key' and any(body['population'] is not None
                    and reference in body['population']['missing_record_keys'] for body in bodies))
        if namespace not in {None, 'source', 'artifact', 'execution_result'}:
            return False
        if not any(reference in body['record_refs'] for body in bodies):
            return False
        return namespace not in {'source', 'artifact'} or self.store.get(reference)['record_type'] == namespace


__all__ = ['NativeInfernalPreparationResults', 'operation_catalog', 'VERSION']
