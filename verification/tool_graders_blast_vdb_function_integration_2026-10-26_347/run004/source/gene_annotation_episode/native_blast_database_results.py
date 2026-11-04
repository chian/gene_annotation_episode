"""Selected original-attempt acquisition, numerical views and practical endpoint."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .acquisition import AcquisitionError
from .communication import plain
from .domain import ContractError, validate_schema
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest, obj
from .form_reference_validation import _binding_key, form_validation_value
from .local_jobs import LocalJobPolicy
from .native_blast_database_acquisition import (capture_native_blast_database_bundle,
    is_native_blast_database_target, _source_payload, _validate_capture)
from .native_blast_database_result_publication import (prepare_native_blast_database_grading,
    publish_selected_native_blast_database_rows, validate_native_blast_database_publication,
    _failure, _json, _json_artifact, _exception_diagnostic, _local_job_failure,
    saved_function_input_descriptor)
from .native_blast_database_result_views import (native_blast_database_fact_sources,
    validate_native_blast_database_result_selector, FUNCTION_SELECTOR, SAVED_INPUT_SOURCE,
    saved_function_descriptor, _SAVED_INPUT_SCHEMA)
from .practical_execution_state import _immutable, _read

VERSION = 'native_blast_database_result_receipt_v1'
FUNCTION_VERSION = 'native_blast_database_result_receipt_vdb_function_v1'
IDENTIFIER_NAMESPACES = ('native_blast_database_row', 'native_blast_database_artifact_key',
    'native_blast_database_search_pointer', 'native_blast_database_entity_key')
ACQUISITION_SOURCE = 'execution_blast_database_acquisition'
REFERENCE_SOURCE = 'execution_blast_database_result_refs'
FAILURE_SOURCE = 'execution_blast_database_failures'


def operation_catalog():
    return [{'name': 'execution.results.status', 'description': 'Observe the exact original database attempt once.', 'input_schema': obj({})},
        {'name': 'execution.results.collect', 'description': 'Execute the assigned input mode: capture the original database bundle, or calculate the selected VDB model from an exact received saved sheet; return its frozen numerical view.', 'input_schema': obj({})}]


def _saved_failure(error):
    message = str(error)
    if 'frozen_artifact' in message or message == 'artifact_digest_mismatch':
        return _failure('worker', 'native_blast_database_frozen_artifact_changed', 'frozen_value_changed')
    if 'sheet_invalid' in message or 'sheet_schema' in message:
        return _failure('population', 'native_blast_database_sheet_invalid', 'metadata_shape_invalid')
    if message.startswith('blast_vdb_function_') and ('model' in message or 'prior' in message):
        return _failure('calculation', 'native_blast_database_calculation_failed', 'calculator_contract_invalid')
    return _failure('authority', 'native_blast_database_return_unauthorized', 'scope_or_receipt_conflict')


def schema_references(value, schema):
    """Walk only fields declared as reference/identifier by the exact row schema."""
    if value is None:
        return
    for choice in ('oneOf', 'anyOf'):
        if choice in schema:
            for branch in schema[choice]:
                try:
                    validate_schema(value, branch)
                except ValueError:
                    continue
                yield from schema_references(value, branch)
                break
            return
    if schema.get('format') in {'reference', 'identifier'} and isinstance(value, str):
        yield value, schema.get('x-reference-namespace'), schema['format']
    if isinstance(value, dict):
        for key, child in value.items():
            if key in schema.get('properties', {}):
                yield from schema_references(child, schema['properties'][key])
    elif isinstance(value, list) and isinstance(schema.get('items'), dict):
        for child in value:
            yield from schema_references(child, schema['items'])


def empty_facts():
    result = {key: [] for key in native_blast_database_fact_sources()}
    result[ACQUISITION_SOURCE] = {k: False for k in ('acquisition_complete', 'projection_complete', 'native_execution_successful', 'complete')}
    return result


class NativeBLASTDatabaseResults:
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.directory = owner.directory / 'native-blast-database-result-index'
        self.original_records = EpisodeReturnRecords(self.store, owner.run_id, failure_prefix='native_blast_database_result_')

    def applies(self, context):
        return context.role == 'results' and is_native_blast_database_target(self.owner._target(context))

    def _directory(self, context):
        return self.owner._result_directory(context) / 'native-blast-database-actions'

    def _action_directory(self, context, operation_key):
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _validate_body(self, body, scope, *, _seen=()):
        expected = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments',
            'target', 'observation', 'capture', 'preparation', 'publication', 'record_refs', 'failures', 'diagnostic_artifact_refs', 'complete'}
        function_mode = type(body) is dict and body.get('version') == FUNCTION_VERSION
        if function_mode:
            expected.update(('calculation_input', 'reused_result_receipt'))
        if type(body) is not dict or set(body) != expected or body['version'] not in (VERSION, FUNCTION_VERSION) or body['run_id'] != self.owner.run_id:
            raise ContractError('native_blast_database_result_receipt_invalid')
        context = self.original_records.context(body['episode_id'])
        if (context.role != 'results' or plain(context.assignment) != body['assignment']
                or plain(context.scope) != body['scope']):
            raise ContractError('native_blast_database_original_assignment_conflict')
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], body['scope'])
        if target != body['target'] or not is_native_blast_database_target(target):
            raise ContractError('native_blast_database_original_target_conflict')
        selector = validate_native_blast_database_result_selector(body['assignment']['selector'],
            program=target['assignment']['requested_job']['native_blast_database']['program'])
        if function_mode != (selector['version'] == FUNCTION_SELECTOR):
            raise ContractError('native_blast_database_result_receipt_invalid')
        saved_mode = function_mode and selector['calculation_input']['mode'] == 'saved_function_sheet'
        if function_mode and (body['calculation_input'] != selector['calculation_input']
                or body['reused_result_receipt'] != selector['calculation_input'].get('original_result_receipt')):
            raise ContractError('native_blast_database_return_unauthorized')
        if saved_mode:
            if body['observation'] is not None or body['capture'] is not None:
                raise ContractError('native_blast_database_saved_capture_conflict')
            if body['publication'] is not None or body['preparation'] is not None or body['record_refs']:
                original = self._read_saved_function_input(saved_function_descriptor(body['calculation_input']), scope, _seen=_seen)
                if original['target'] != target:
                    raise ContractError('native_blast_database_return_unauthorized')
                self.owner.native_blast_database_returns.resolve_saved_function_input(context,
                    saved_function_descriptor(body['calculation_input']))
        action = self.owner._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        if body['arguments'] != {} or body['tool_name'] not in {r['name'] for r in operation_catalog()}:
            raise ContractError('native_blast_database_original_operation_conflict')
        directory = self._action_directory(context, body['operation_key'])
        if _read(directory / 'receipt.json') != body:
            raise ContractError('native_blast_database_original_receipt_conflict')
        intent = {key: body[key] for key in ('target', 'assignment', 'operation_key', 'tool_name', 'arguments', 'scope')}
        if _read(directory / 'intent.json') != intent or (not saved_mode and _read(directory / 'observation.json') != body['observation']):
            raise ContractError('native_blast_database_original_action_conflict')
        if action['result'] is not None:
            outcome = json.loads(action['result'])
            if (outcome.get('status') != 'completed' or outcome.get('result') != body
                    or outcome.get('record_refs') != body['record_refs']):
                raise ContractError('native_blast_database_saved_outcome_conflict')
        for ref in body['diagnostic_artifact_refs']:
            _json(self.store, ref)
        complete = False
        if body['capture'] is not None:
            capture = _validate_capture(self.store, body['capture'], target=target, operation_key=body['operation_key'], directory=directory / 'capture')
            if _read(directory / 'capture' / 'capture.json') != capture:
                raise ContractError('native_blast_database_original_capture_conflict')
        if body['publication'] is not None:
            if (body['preparation'] is None or _read(directory / 'grading' / 'preparation.json') != body['preparation']
                    or _read(directory / 'publication' / 'publication.json') != body['publication']):
                raise ContractError('native_blast_database_original_preparation_conflict')
            publication = validate_native_blast_database_publication(self.store, context=context, publication=body['publication'])
            if (publication['record_refs'] != body['record_refs'] or publication['failures'] != body['failures']
                    or _json(self.store, publication['preparation_artifact_ref']) != body['preparation']):
                raise ContractError('native_blast_database_original_publication_conflict')
            complete = publication['complete']
        elif body['record_refs']:
            if body['capture'] is None or body['capture']['status'] not in {'complete', 'partial'}:
                raise ContractError('native_blast_database_source_without_capture')
            bundle = _json(self.store, body['capture']['bundle_artifact_ref'])
            from .domain import identity
            payload = _source_payload(bundle, body['capture'])
            expected_ref = identity('source', {'origin': 'tool', 'record': payload})
            source = self.store.get(expected_ref)
            if body['record_refs'] != [expected_ref] or {k: v for k, v in source.items()
                    if k not in {'id', 'record_type', 'origin'}} != payload:
                raise ContractError('native_blast_database_original_source_conflict')
        if body['tool_name'] == 'execution.results.status' and any(body[k] for k in
                ('capture', 'preparation', 'publication', 'record_refs', 'failures', 'diagnostic_artifact_refs')):
            raise ContractError('native_blast_database_status_content_conflict')
        if type(body['complete']) is not bool or body['complete'] != complete:
            raise ContractError('native_blast_database_completion_conflict')
        validate_schema(body['failures'], native_blast_database_fact_sources()[FAILURE_SOURCE]['report_schema'])
        return body

    def _index(self, body):
        for ref in body['record_refs']:
            directory = self.directory / digest(ref); directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body['operation_key']) + '.json'),
                {key: body[key] for key in ('run_id', 'episode_id', 'operation_key')})

    async def execute(self, context, target, tool_name, arguments, operation_key):
        self.original_records.authenticate(context)
        if not self.applies(context) or target != self.owner._target(context):
            raise ContractError('native_blast_database_original_results_owner_required')
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        if arguments != {} or tool_name not in {r['name'] for r in operation_catalog()}:
            raise ContractError('native_blast_database_result_operation_invalid')
        selector = self.owner._selector(plain(context.assignment), target)
        directory = self._action_directory(context, operation_key)
        intent = dict(target=target, assignment=plain(context.assignment), scope=plain(context.scope),
            operation_key=operation_key, tool_name=tool_name, arguments=arguments)
        _immutable(directory / 'intent.json', intent)
        if (directory / 'receipt.json').exists():
            body = self._validate_body(_read(directory / 'receipt.json'), context.scope)
        else:
            if self.completion(context) is not None:
                raise ContractError('execution_results_assignment_already_completed')
            function_mode = selector['version'] == FUNCTION_SELECTOR
            saved_mode = function_mode and selector['calculation_input']['mode'] == 'saved_function_sheet'
            if not saved_mode and not (directory / 'observation.json').exists():
                _immutable(directory / 'observation.json', self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key))
            body = dict(version=FUNCTION_VERSION if function_mode else VERSION, run_id=context.run_id, episode_id=context.episode_id, **intent,
                observation=None if saved_mode else _read(directory / 'observation.json'), capture=None, preparation=None, publication=None,
                record_refs=[], failures=[], diagnostic_artifact_refs=[], complete=False)
            if function_mode:
                body.update(calculation_input=deepcopy(selector['calculation_input']),
                    reused_result_receipt=deepcopy(selector['calculation_input'].get('original_result_receipt')))
            if saved_mode and tool_name == 'execution.results.collect':
                try:
                    descriptor = saved_function_descriptor(selector['calculation_input'])
                    original = self.owner.native_blast_database_returns.resolve_saved_function_input(context, descriptor)
                    if original['target'] != target:
                        raise ContractError('native_blast_database_return_unauthorized')
                    prepared = prepare_native_blast_database_grading(self.store, context=context, target=target,
                        capture=None, selector=selector, directory=directory / 'grading',
                        policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None), original_body=original)
                    body['preparation'] = prepared
                    publication = publish_selected_native_blast_database_rows(self.store, context=context,
                        preparation=prepared, selector=selector, directory=directory / 'publication')
                    body.update(publication=publication, record_refs=publication['record_refs'],
                        failures=publication['failures'], complete=publication['complete'])
                except (AcquisitionError, ValueError, KeyError, TypeError, OSError) as error:
                    failure = _local_job_failure(error) if isinstance(error, AcquisitionError) else _saved_failure(error)
                    body['failures'].append(failure)
                    body['diagnostic_artifact_refs'].append(_json_artifact(self.store,
                        {'schema': 'native_blast_database_diagnostics_v1', 'failures': [failure], 'metadata_issues': [],
                         'errors': [_exception_diagnostic(error)], 'calculation_input': selector['calculation_input']}))
            elif tool_name == 'execution.results.collect':
                capture = capture_native_blast_database_bundle(self.store, target=target,
                    reader=self.owner.job_progress_provider.targets, operation_key=operation_key, directory=directory / 'capture')
                body['capture'] = capture
                if capture['status'] in {'complete', 'partial'}:
                    bundle = _json(self.store, capture['bundle_artifact_ref'])
                    source = self.store.put('source', _source_payload(bundle, capture), origin='tool')['id']
                    body['record_refs'] = [source]
                    try:
                        prepared = prepare_native_blast_database_grading(self.store, context=context, target=target,
                            capture=capture, selector=selector, directory=directory / 'grading',
                            policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None))
                        body['preparation'] = prepared
                        publication = publish_selected_native_blast_database_rows(self.store, context=context,
                            preparation=prepared, selector=selector, directory=directory / 'publication')
                        body.update(publication=publication, record_refs=publication['record_refs'],
                            failures=publication['failures'], complete=publication['complete'])
                    except (AcquisitionError, ValueError, KeyError, TypeError, OSError) as error:
                        invalid_contract = str(error) == 'native_blast_database_calculator_contract_invalid'
                        failure = _local_job_failure(error) if isinstance(error, AcquisitionError) else _failure('calculation' if invalid_contract else 'worker',
                            'native_blast_database_calculation_failed' if invalid_contract else 'native_blast_database_worker_failed',
                            'calculator_contract_invalid' if invalid_contract else 'implementation_failure')
                        body['failures'].append(failure)
                        body['diagnostic_artifact_refs'].append(_json_artifact(self.store,
                            {'schema': 'native_blast_database_diagnostics_v1', 'failures': [failure], 'metadata_issues': [],
                             'errors': [_exception_diagnostic(error)]}))
                        for name in ('invalid-request.json', 'invalid-request-diagnostics.json', 'implementation-receipt.json'):
                            path = directory / 'grading' / name
                            if path.exists():
                                from .materials import artifact_file
                                body['diagnostic_artifact_refs'].append(artifact_file(self.store, path, 'application/json'))
                else:
                    body['failures'] = [_failure('capture', 'native_blast_database_capture_incomplete',
                        'attempt_identity_conflict' if row['code'] == 'attempt_mismatch' else 'artifact_bytes_unavailable',
                        artifact_key=row['artifact_key'], pointer='/capture/failures/' + str(i)) for i, row in enumerate(capture['failures'])]
            _immutable(directory / 'receipt.json', body)
            self._validate_body(body, context.scope)
        self._index(body)
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'],
            'result': body, 'feedback': None}

    def _own_bodies(self, context):
        def load():
            directory = self._directory(context)
            bodies = [] if not directory.exists() else [_read(p) for p in directory.glob('*/receipt.json')]
            result = []
            for body in sorted(bodies, key=lambda b: int(b['operation_key'].rsplit(':', 1)[1])):
                if body['episode_id'] != context.episode_id:
                    raise ContractError('native_blast_database_receipt_owner_conflict')
                result.append(self._validate_body(body, context.scope))
            return result
        yield from form_validation_value((self, 'own', _binding_key(context)), load)

    def read_result(self, reference, scope, *, assignment=None):
        for path in sorted((self.directory / digest(reference)).glob('*.json')):
            pointer = _read(path)
            if pointer['run_id'] != self.owner.run_id:
                raise ContractError('native_blast_database_index_run_conflict')
            context = self.original_records.context(pointer['episode_id'])
            if assignment is not None and plain(context.assignment) != plain(assignment):
                continue
            body = self._validate_body(_read(self._action_directory(context, pointer['operation_key']) / 'receipt.json'), scope)
            if reference not in body['record_refs']:
                raise ContractError('native_blast_database_index_reference_conflict')
            return body
        raise ContractError('not_a_native_blast_database_acquired_result')

    def _read_saved_function_input(self, descriptor, scope, *, _seen=()):
        validate_schema(descriptor, _SAVED_INPUT_SCHEMA)
        address = descriptor['original_result_receipt']
        key = (address['run_id'], address['episode_id'], address['operation_key'])
        if key in _seen or address['run_id'] != self.owner.run_id:
            raise ContractError('native_blast_database_return_unauthorized')
        context = self.original_records.context(address['episode_id'])
        path = self._directory(context) / digest(address['operation_key']) / 'receipt.json'
        if not path.is_file():
            raise ContractError('native_blast_database_return_unauthorized')
        body = _read(path)
        if (digest(body) != address['receipt_sha256'] or body.get('version') != FUNCTION_VERSION
                or body.get('run_id') != address['run_id'] or body.get('episode_id') != address['episode_id']
                or body.get('operation_key') != address['operation_key'] or address['source_ref'] not in body.get('record_refs', [])):
            raise ContractError('native_blast_database_return_unauthorized')
        body = self._validate_body(body, scope, _seen=(*_seen, key))
        action = self.owner._selected_result_action(context.episode_id, body['operation_key'], body['tool_name'], body['arguments'])
        if action['result'] is None or saved_function_input_descriptor(self.store, body) != descriptor:
            raise ContractError('native_blast_database_return_unauthorized')
        return deepcopy(body)

    def read_saved_function_input(self, descriptor: dict, scope: dict) -> dict:
        """Read one exact durable receipt and its finite authenticated chain."""
        return self._read_saved_function_input(descriptor, scope)

    def facts(self, context):
        result, seen = empty_facts(), {}
        fields = plain(context.request).get('report_contract', {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested = {node.get('x-source') for node in fields.values()}
        bodies = list(self._own_bodies(context))
        for body in bodies:
            for ref in body['record_refs']:
                if ref not in result[REFERENCE_SOURCE]:
                    result[REFERENCE_SOURCE].append(ref)
            result[FAILURE_SOURCE].extend(deepcopy(body['failures']))
            publication = body['publication']
            if publication is None:
                continue
            if SAVED_INPUT_SOURCE in requested and body['version'] == FUNCTION_VERSION:
                try:
                    descriptor = saved_function_input_descriptor(self.store, body)
                except ContractError as error:
                    if str(error) not in {'native_blast_database_saved_function_input_unavailable', 'native_blast_database_sheet_invalid'}:
                        raise
                else:
                    if descriptor not in result[SAVED_INPUT_SOURCE]:
                        result[SAVED_INPUT_SOURCE].append(descriptor)
            result[ACQUISITION_SOURCE] = {k: publication[k] for k in result[ACQUISITION_SOURCE]}
            for family, rows in publication['rows_by_family'].items():
                source = 'execution_blast_database_' + family + '_rows'
                if source not in requested:
                    continue
                for row in rows:
                    key = row['calculation_id'], row['record_key']
                    if key not in seen.setdefault(source, set()):
                        result[source].append(deepcopy(row)); seen[source].add(key)
        return {**result, 'execution_handoff_refs': [], 'execution_result_refs': result[REFERENCE_SOURCE],
            'execution_completed': any(b['complete'] for b in bodies), 'execution_result_origin': None}

    def resolve(self, context, reference, namespace):
        if not self.applies(context):
            return False
        if namespace not in (*IDENTIFIER_NAMESPACES, None, 'source', 'execution_result', 'subject'):
            return False
        descriptors = native_blast_database_fact_sources()
        for body in self._own_bodies(context):
            if namespace not in IDENTIFIER_NAMESPACES and reference in body['record_refs']:
                kind = self.store.get(reference)['record_type']
                return kind == 'source' if namespace == 'source' else kind in {'input', 'feature', 'product', 'read_subject'} if namespace == 'subject' else True
            if body['publication'] is None:
                continue
            if body['version'] == FUNCTION_VERSION:
                try:
                    descriptor = saved_function_input_descriptor(self.store, body)
                except ContractError as error:
                    if str(error) not in {'native_blast_database_saved_function_input_unavailable', 'native_blast_database_sheet_invalid'}:
                        raise
                else:
                    schema = descriptors[SAVED_INPUT_SOURCE]['report_schema']
                    if any(ref == reference and ns == namespace for ref, ns, _ in schema_references([descriptor], schema)):
                        return True
            for family, rows in body['publication']['rows_by_family'].items():
                schema = descriptors['execution_blast_database_' + family + '_rows']['report_schema']
                if any(ref == reference and ns == namespace for ref, ns, _ in schema_references(rows, schema)):
                    return True
        return False

    def credit_view(self, context, receiver_selection):
        selection = plain(receiver_selection)
        known, inherited = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        if not inherited <= known:
            raise ContractError('native_blast_database_initial_references_must_be_known')
        acquired = {self.result_identity(ref, context.scope) for ref in set(self.facts(context)[REFERENCE_SOURCE]) & known}
        inherited_identities = set()
        for reference in inherited:
            try:
                inherited_identities.add(self.result_identity(reference, context.scope))
            except (ValueError, KeyError, OSError):
                pass
        count = len(acquired - inherited_identities)
        value = self.owner.acquired_record_unit * count
        return dict(credit=value, operational_credit=value, new_handoff_count=0, new_acquired_record_count=count,
            operational_credit_binding=dict(version=VERSION, handoff_unit=self.owner.handoff_unit,
                acquired_record_unit=self.owner.acquired_record_unit, scientific_credit=False, monitoring_credit=False))

    def result_identity(self, reference, scope):
        body = self.read_result(reference, scope)
        while body.get('calculation_input', {}).get('mode') == 'saved_function_sheet':
            body = self.read_saved_function_input(saved_function_descriptor(body['calculation_input']), scope)
        bundle = _json(self.store, body['capture']['bundle_artifact_ref'])
        record = self.store.get(reference)
        if record['record_type'] == 'source':
            contribution = {'record_type': 'source'}
        elif record.get('native_blast_database') is not None:
            contribution = {k: deepcopy(v) for k, v in record.items()
                if k not in {'id', 'origin', 'source_ref', 'dependencies'}}
            contribution['dependencies'] = [r for r in record['dependencies'] if r != record['source_ref']]
        else:
            raise ContractError('native_blast_database_acquired_contribution_invalid')
        return digest({'attempt_identity': bundle['identity'], 'contribution': contribution})

    def completion(self, context):
        for body in self._own_bodies(context):
            if body['complete'] and self.owner._selected_result_action(context.episode_id, body['operation_key'],
                    body['tool_name'], body['arguments'])['result'] is not None:
                return dict(version='practical_completion_v1', run_id=context.run_id, episode_id=context.episode_id,
                    assignment_sha256=digest(context.assignment), endpoint='usable_handoff', operation_key=body['operation_key'],
                    receipt_sha256=digest(body), validation_keys=['original_native_attempt',
                        'authenticated_saved_function_sheet' if body.get('calculation_input', {}).get('mode') == 'saved_function_sheet' else 'complete_sealed_bundle_acquisition',
                        'requested_native_numerical_projection'])
        return None


__all__ = ['NativeBLASTDatabaseResults', 'operation_catalog']
