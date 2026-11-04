"""Recorded HMMER assignment, handoff and acquisition qualification.

This reader never sends HTTP or refreshes a result. Provider records are read
only through the caller's public operations port. The ordinary Store owns the
immutable proof sources and their selected-action witnesses.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from .communication import plain
from .domain import ContractError, identity
from .episode_bindings import BindingContext
from .hmmer_request_preparation import ALLOCATION, CONSTRAINTS, prepare_hmmer_request, qualify_api_candidate
from .resource_records import HANDOFF_SCHEMA, LAUNCH_SCHEMA, LAUNCH_VERSION, RESULTS_SCHEMA, RESULTS_VERSION, _validate


PROVIDER = 'episode.api_search_handoff'
PUBLICATION_PROVIDER = 'episode.api_search_result_publication'
PROOF_VERSION = 'api_search_handoff_information_v1'
ROW_VERSION = 'api_search_result_publication_row_v1'
INTERFACES = {'monitoring': 'public_search.status.v1', 'results': 'public_search.results.v1'}
CHECK_TOOLS = {'api_search.check_handoff', 'resource.check_handoff'}
STATES = {'PENDING', 'RECEIVED', 'STARTED', 'RETRY', 'SUCCESS', 'FAILURE', 'REVOKED'}
SELECTOR_SCHEMA = {'type': 'object', 'properties': {
    'version': {'const': 'public_search_result_selector_v1'}, 'provider': {'const': 'hmmer'},
    'first_page': {'type': 'integer', 'minimum': 1},
    'last_page': {'type': ['integer', 'null'], 'minimum': 1},
    'page_size': {'type': 'integer', 'minimum': 1}},
    'required': ['version', 'provider', 'first_page', 'last_page', 'page_size'], 'additionalProperties': False}


def json_value(value):
    return json.loads(json.dumps(plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False))


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def utc(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('api_information_invalid_timestamp') from error
    return stamp


def selector(value):
    value = _validate(value, SELECTOR_SCHEMA)
    if value['last_page'] is not None and value['last_page'] < value['first_page']:
        raise ValueError('invalid_resource_selector')
    return value


def contains_page(selected, page, page_size):
    return (type(page) is int and type(page_size) is int and page_size == selected['page_size']
        and page >= selected['first_page'] and (selected['last_page'] is None or page <= selected['last_page']))


def proof_receipt_ref(run_id, episode_id, operation_key, status_receipt_ref):
    """Audit identity separate from its content-addressed containing source."""
    return 'handoff_receipt_' + digest([PROOF_VERSION, run_id, episode_id, operation_key, status_receipt_ref])


def api_selection(registry):
    return {'resource_id': registry['resource_id'], 'kind': 'api', 'allocation': dict(ALLOCATION),
        'capability_binding_ref': registry['registry_ref']}


class ApiSearchInformationReader:
    def __init__(self, store, *, run_id: str, ports):
        from .public_search_operations import PublicSearchPorts
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('api_information_run_required')
        if not isinstance(ports, PublicSearchPorts) or getattr(ports.operations, 'store', None) is not store:
            raise ValueError('api_information_identity_conflict')
        self.store, self.run_id, self.ports = store, run_id, ports
        self.registry = json_value(ports.registry)
        if self.registry.get('provider') != 'hmmer':
            raise ValueError('unsupported_provider')

    def as_record(self):
        return {'version': 'api_search_information_reader_v1', 'run_id': self.run_id,
            'registry_ref': self.registry['registry_ref']}

    def _context(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_information_identity_conflict')

    def selection(self):
        return api_selection(self.registry)

    def owns(self, context):
        assignment = plain(context.assignment)
        if assignment.get('version') == RESULTS_VERSION:
            selected = assignment.get('handoff', {}).get('resource_selection', {})
        else:
            selected = assignment.get('resource_selection')
            if selected is None:
                return context.role == 'launch' and assignment.get('job_request', {}).get('provider') == 'hmmer'
        return (isinstance(selected, dict) and selected.get('resource_id') == self.registry['resource_id']
            and selected.get('kind') == 'api' and selected.get('capability_binding_ref') == self.registry['registry_ref'])

    def _sequence(self, reference, scope):
        return self.ports.sequence_symbols(reference, scope=plain(scope))

    def _order_scope(self, job_ref, scope, *, exact=False):
        original = self.ports.operations.open_scope(job_ref)['scope']
        normalized = self.store.validate_scope(plain(scope))
        if ((exact and normalized != original)
                or not self.store.scope_contains(normalized, original)):
            raise ValueError('api_information_order_scope_conflict')
        return original

    def _versions(self, versions, scope):
        qualify_api_candidate(self.store, scope=scope, selection=self.selection(),
            constraints={}, immutable_input_versions=versions)

    def _constraints(self, constraints, selection):
        qualify_api_candidate(self.store, scope=None, selection=selection,
            constraints=constraints, immutable_input_versions=[])

    def request_for_assignment(self, context):
        """Read-only preparation; shared builder is the sole request normalizer."""
        self._context(context)
        job = plain(context.assignment)['job_request']
        if not isinstance(job, dict) or job.get('provider') != 'hmmer':
            raise ValueError('unsupported_api_job_request')
        if 'existing_job_ref' in job:
            if set(job) != {'provider', 'existing_job_ref'}:
                raise ValueError('unsupported_api_job_request')
            inspected = self.ports.operations.inspect(job['existing_job_ref'])
            self._order_scope(job['existing_job_ref'], context.scope, exact=True)
            self._validate_order(inspected['order'], inspected['request'], plain(context.scope))
            return json_value(inspected['request']), self.store.get_artifact(inspected['order']['query_fasta_ref']).decode('utf-8')
        allowed = {'provider', 'subject_ref', 'algorithm', 'database', 'parameters', 'page_size'}
        if set(job) - allowed or not {'provider', 'subject_ref', 'algorithm', 'database'} <= set(job):
            raise ValueError('unsupported_api_job_request')
        prepared = prepare_hmmer_request({key: value for key, value in job.items() if key != 'provider'},
            sequence_symbols=self.ports.sequence_symbols, scope=plain(context.scope))
        return json_value(prepared.request), prepared.query_fasta

    def _validate_order(self, order, request, scope):
        if (set(order) != {'version', 'registry_ref', 'job_ref', 'order_operation_key',
                'request_sha256', 'request_ref', 'query_fasta_ref'}
                or order['version'] != 'public_search_order_v1'
                or order['registry_ref'] != self.registry['registry_ref']
                or order['request_sha256'] != digest(request)
                or json.loads(self.store.get_artifact(order['request_ref'])) != request):
            raise ValueError('api_information_order_conflict')
        from .domain import parse_sequences
        from .provider_jobs import build_search_request, provider_job_reference
        original_scope = self._order_scope(order['job_ref'], scope)
        fasta = self.store.get_artifact(order['query_fasta_ref'])
        rebuilt, _ = build_search_request(subject_ref=request['subject_ref'], query_fasta=fasta.decode('utf-8'),
            algorithm=request['algorithm'], database=request['database'], parameters=request['parameters'],
            page_size=request['page_size'], provider='hmmer')
        if (rebuilt != request or order['job_ref'] != provider_job_reference(order['order_operation_key'], request)):
            raise ValueError('api_information_order_conflict')
        symbols = parse_sequences(self._sequence(request['subject_ref'], original_scope), format='raw', molecule='protein')[0].sequence
        if hashlib.sha256(symbols.encode()).hexdigest() != request['sequence_sha256']:
            raise ValueError('api_information_input_conflict')
        if hashlib.sha256(fasta).hexdigest() != request['query_sha256']:
            raise ValueError('api_information_input_conflict')

    def qualify_launch(self, context):
        self._context(context)
        assignment = plain(context.assignment)
        base = {key: assignment[key] for key in LAUNCH_SCHEMA['properties'] if key in assignment}
        _validate(base, LAUNCH_SCHEMA)
        if context.role not in {'launch', 'launch_api'} or not self.owns(context):
            raise ValueError('resource_assignment_conflict')
        chosen = self.selection()
        if assignment['resource_selection'] is not None and assignment['resource_selection'] != chosen:
            raise ValueError('resource_selection_conflict')
        if context.role == 'launch_api' and assignment['resource_selection'] is None:
            raise ValueError('explicit_resource_selection_required')
        self._constraints(assignment['constraints'], chosen)
        self._versions(assignment['immutable_input_versions'], plain(context.scope))
        request, _ = self.request_for_assignment(context)
        order = assignment.get('adapter_assignment')
        if order is not None:
            actual = self.ports.operations.open_order(order['job_ref'])
            if actual != order or order['request_sha256'] != digest(request):
                raise ValueError('api_information_assignment_conflict')
            self._validate_order(order, request, plain(context.scope))
            self._order_scope(order['job_ref'], context.scope, exact=context.role == 'launch_api')
        return {'version': 'qualified_api_launch_v1', 'run_id': self.run_id,
            'episode_id': context.episode_id, 'provider': 'hmmer', 'subject_ref': request['subject_ref'],
            'request_sha256': digest(request), 'existing_job_ref': assignment['job_request'].get('existing_job_ref'),
            'immutable_input_versions': assignment['immutable_input_versions'],
            'resource_selection': assignment['resource_selection'], 'constraints': assignment['constraints']}

    def qualify_handoff(self, context, qualified, proof):
        handoff = proof['execution_handoff']
        if (proof['run_id'] != context.run_id or proof['registry_ref'] != self.registry['registry_ref']
                or proof['request_sha256'] != qualified['request_sha256']
                or handoff['submitted_input_versions'] != qualified['immutable_input_versions']
                or qualified['existing_job_ref'] is not None and proof['job_ref'] != qualified['existing_job_ref']
                or qualified['resource_selection'] is not None and handoff['resource_selection'] != qualified['resource_selection']):
            raise ValueError('api_information_assignment_conflict')
        self._constraints(qualified['constraints'], handoff['resource_selection'])
        if proof['episode_id'] == context.episode_id and proof['assignment_sha256'] != digest(context.assignment):
            raise ValueError('api_information_assignment_conflict')

    def validate_handoff(self, handoff, *, scope):
        handoff = _validate(handoff, HANDOFF_SCHEMA)
        if (handoff['resource_selection'] != self.selection() or handoff['state'] != 'usable'
                or handoff['failure'] is not None or len(handoff['check_record_refs']) != 1):
            raise ValueError('invalid_resource_handoff')
        inspected = self.ports.operations.inspect(handoff['execution_handle'])
        self._validate_order(inspected['order'], inspected['request'], scope)
        self._versions(handoff['submitted_input_versions'], scope)
        utc(handoff['checked_at'])
        for field, contract in INTERFACES.items():
            if handoff[field] != {'provider_id': self.registry['resource_id'],
                    'target_handle': handoff['execution_handle'], 'contract_ref': contract}:
                raise ValueError('invalid_resource_handoff')
        return inspected

    def _selected(self, episode_id, operation_key):
        prefix = self.run_id + ':' + episode_id + ':'
        index = operation_key.removeprefix(prefix)
        if not operation_key.startswith(prefix) or not index.isdecimal() or str(int(index)) != index:
            raise ValueError('api_information_operation_conflict')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
            (self.run_id, episode_id, int(index))).fetchone()
        if row is None:
            raise ValueError('api_information_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') not in CHECK_TOOLS:
            raise ValueError('api_information_operation_conflict')
        if action['tool'] == 'api_search.check_handoff' and action.get('arguments') != {}:
            raise ValueError('api_information_operation_conflict')
        return row, action

    def _sources(self):
        return [json.loads(row[0]) for row in self.store.db.execute(
            "SELECT data FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=? ORDER BY id", (PROVIDER,))]

    def _body(self, source):
        return json.loads(self.store.get_artifact(source['artifact_ref']))

    def _accession(self, episode_id, operation_key):
        return 'api_handoff_' + digest([self.run_id, episode_id, operation_key])

    @staticmethod
    def with_reference(outcome, reference):
        value = deepcopy(outcome)
        for field in ('record_refs', 'resource_information_refs'):
            value[field] = list(dict.fromkeys([*value.get(field, []), reference]))
        return value

    def _validate_body(self, body, scope):
        fields = {'version', 'run_id', 'episode_id', 'operation_key', 'scope', 'assignment_sha256',
            'registry_ref', 'job_ref', 'request_sha256', 'status_receipt_ref', 'execution_handoff', 'outcome'}
        if (not isinstance(body, dict) or set(body) != fields or body['version'] != PROOF_VERSION
                or body['run_id'] != self.run_id or body['registry_ref'] != self.registry['registry_ref']
                or not isinstance(body['scope'], dict)):
            raise ValueError('api_information_malformed_proof')
        handoff = body['execution_handoff']
        inspected = self.validate_handoff(handoff, scope=scope)
        # The source retains its actual originating context. Visibility of the
        # job contribution follows the original assigned order scope, including
        # after a check by a containing parent and return to assigned results.
        self._order_scope(inspected['order']['job_ref'], body['scope'])
        if (body['job_ref'] != handoff['execution_handle']
                or body['request_sha256'] != inspected['order']['request_sha256']):
            raise ValueError('api_information_proof_identity_conflict')
        receipt = self.ports.operations.read_operation(body['status_receipt_ref'])
        if (receipt['operation'] != 'status' or receipt['outcome'] != 'completed'
                or receipt['operation_key'] != body['operation_key']
                or receipt['job_ref'] != body['job_ref'] or receipt['registry_ref'] != body['registry_ref']
                or receipt['request_sha256'] != body['request_sha256'] or receipt['state'] not in STATES
                or receipt['remote_id'] is None or receipt['failure'] is not None
                or receipt['observed_at'] != handoff['checked_at']):
            raise ValueError('api_information_check_receipt_conflict')
        expected = proof_receipt_ref(self.run_id, body['episode_id'], body['operation_key'], body['status_receipt_ref'])
        if handoff['check_record_refs'] != [expected]:
            raise ValueError('api_information_check_receipt_conflict')
        outcome = body['outcome']
        expected_outcome = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'result': receipt, 'feedback': None, 'provider_operation_refs': [body['status_receipt_ref']],
            'execution_handoff': handoff}
        if outcome != expected_outcome:
            raise ValueError('api_information_check_outcome_conflict')
        selected, action = self._selected(body['episode_id'], body['operation_key'])
        if action['tool'] == 'resource.check_handoff':
            original = action.get('arguments', {}).get('handoff')
            if not isinstance(original, dict) or set(action['arguments']) != {'handoff'}:
                raise ValueError('api_information_operation_conflict')
            if (original['execution_handle'] != body['job_ref'] or original['resource_selection'] != self.selection()
                    or original['submitted_input_versions'] != handoff['submitted_input_versions']):
                raise ValueError('api_information_assignment_conflict')
            self.references_for_handoff(original, scope=scope)
        episode = self.store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (self.run_id, body['episode_id'])).fetchone()
        if episode is None:
            raise ValueError('api_information_original_assignment_missing')
        request = json.loads(episode['request'])
        assignment = request['message'].get('episode_assignment', request['message'].get('assignment'))
        if assignment is None or digest(assignment) != body['assignment_sha256']:
            raise ValueError('api_information_assignment_conflict')
        path = json.loads(episode['path'])
        context = BindingContext(self.run_id, body['episode_id'], path[-1][0], path,
            request['message']['scope'], assignment, request)
        if plain(context.scope) != body['scope']:
            raise ValueError('api_information_assignment_conflict')
        if assignment['version'] == LAUNCH_VERSION:
            self.qualify_handoff(context, self.qualify_launch(context), body)
        else:
            self.qualify_results(context)
        return selected

    def read_handoff_source(self, reference, *, scope):
        source = self.store.get(reference)
        if source.get('record_type') != 'source' or source.get('provider') != PROVIDER:
            return None
        body = self._body(source)
        if body.get('registry_ref') != self.registry['registry_ref']:
            return None
        payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
        if (reference != identity('source', {'origin': 'tool', 'record': payload})
                or source.get('origin') != 'tool' or source['version'] != PROOF_VERSION
                or source['accession'] != self._accession(body['episode_id'], body['operation_key'])
                or source['text_ref'] != source['artifact_ref'] or source['request_ref'] is not None
                or source['uri'] is not None or source['retrieved_at'] != body['execution_handoff']['checked_at']
                or source.get('operand_refs') != [self.ports.operations.inspect(body['job_ref'])['request']['subject_ref']]
                or self.store.get_artifact(source['artifact_ref']) != json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()):
            raise ValueError('api_information_source_identity_conflict')
        selected = self._validate_body(body, plain(scope))
        if selected['result'] is not None:
            saved = json.loads(selected['result'])
            if any(saved.get(key) != value for key, value in self.with_reference(body['outcome'], reference).items()):
                raise ValueError('api_information_saved_outcome_conflict')
        return body

    def publish_handoff(self, context, outcome, operation_key):
        self._context(context)
        handoff, receipt = outcome['execution_handoff'], outcome['result']
        body = {'version': PROOF_VERSION, 'run_id': self.run_id, 'episode_id': context.episode_id,
            'operation_key': operation_key, 'scope': plain(context.scope), 'assignment_sha256': digest(context.assignment),
            'registry_ref': self.registry['registry_ref'], 'job_ref': handoff['execution_handle'],
            'request_sha256': receipt['request_sha256'], 'status_receipt_ref': receipt['receipt_ref'],
            'execution_handoff': json_value(handoff), 'outcome': json_value(outcome)}
        self._validate_body(body, plain(context.scope))
        with self.store.transaction():
            existing = [source for source in self._sources() if source.get('accession') == self._accession(context.episode_id, operation_key)]
            if existing:
                if len(existing) != 1 or self.read_handoff_source(existing[0]['id'], scope=plain(context.scope)) != body:
                    raise ValueError('api_information_operation_conflict')
                return self.with_reference(outcome, existing[0]['id'])
            artifact = self.store.artifact(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False), 'application/json')
            source = self.store.put('source', {'provider': PROVIDER,
                'accession': self._accession(context.episode_id, operation_key), 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': PROOF_VERSION,
                'retrieved_at': handoff['checked_at'],
                'operand_refs': [self.ports.operations.inspect(body['job_ref'])['request']['subject_ref']]}, origin='tool')
            return self.with_reference(outcome, source['id'])

    def selected_handoff(self, context, operation_key):
        for source in self._sources():
            if source.get('accession') == self._accession(context.episode_id, operation_key):
                body = self.read_handoff_source(source['id'], scope=plain(context.scope))
                if body['assignment_sha256'] != digest(context.assignment):
                    raise ValueError('api_information_operation_conflict')
                return self.with_reference(body['outcome'], source['id'])
        return None

    def references_for_handoff(self, handoff, *, scope):
        matches = []
        for source in self._sources():
            body = self._body(source)
            if body.get('run_id') == self.run_id and body.get('execution_handoff') == handoff:
                self.read_handoff_source(source['id'], scope=scope)
                matches.append(source['id'])
        if not matches:
            raise ValueError('api_information_handoff_proof_missing')
        return sorted(matches)

    def qualify_results(self, context):
        self._context(context)
        assignment = plain(context.assignment)
        base = {key: assignment[key] for key in RESULTS_SCHEMA['properties'] if key in assignment}
        _validate(base, RESULTS_SCHEMA)
        if context.role != 'results' or not self.owns(context):
            raise ValueError('resource_assignment_conflict')
        selected = selector(assignment['requested_data_selector'])
        inspected = self.validate_handoff(assignment['handoff'], scope=plain(context.scope))
        self._order_scope(inspected['order']['job_ref'], context.scope, exact=True)
        if assignment.get('adapter_assignment', inspected['order']) != inspected['order']:
            raise ValueError('api_information_assignment_conflict')
        self.references_for_handoff(assignment['handoff'], scope=plain(context.scope))
        return inspected, selected

    def own_result_rows(self, context):
        inspected, selected = self.qualify_results(context)
        rows = []
        actions = self.store.db.execute("SELECT decision_index,action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND json_extract(action,'$.tool')='api_search.acquire' AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
            (self.run_id, context.episode_id))
        for action_row in actions:
            action, outcome = json.loads(action_row['action']), json.loads(action_row['result'])
            result = outcome['result']
            page = action['arguments']['page']
            if not contains_page(selected, page, result['page_size']) or result['page'] != page:
                raise ValueError('requested_data_selector_conflict')
            source = self.store.get(result['publication_ref'])
            if source.get('provider') != PUBLICATION_PROVIDER or source.get('version') != 'api_search_result_publication_v1':
                raise ValueError('api_information_publication_conflict')
            body = self._body(source)
            operation_key = f'{context.run_id}:{context.episode_id}:{action_row["decision_index"]}'
            payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
            receipt = self.ports.operations.read_operation(body['acquisition_receipt_ref'])
            if (source['id'] != identity('source', {'origin': 'tool', 'record': payload})
                    or source.get('origin') != 'tool'
                    or self.store.get_artifact(source['artifact_ref']) != json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
                    or body['operation_key'] != operation_key or receipt['operation_key'] != operation_key
                    or action.get('kind') != 'tool' or set(action.get('arguments', {})) != {'page'}
                    or body['registry_ref'] != self.registry['registry_ref'] or body['job_ref'] != inspected['order']['job_ref']
                    or body['request_sha256'] != inspected['order']['request_sha256']
                    or body['publication_rows'] != result['publication_rows'] or body['source_ref'] != result['source_ref']
                    or body['subject_ref'] != inspected['request']['subject_ref']
                    or body['acquisition_receipt_ref'] != result['acquisition_receipt_ref']
                    or body['projection_failures'] != result['projection_failures'] or body['page_count'] != result['page_count']
                    or body['selector'] != {'version': 'public_search_result_selector_v1', 'provider': 'hmmer',
                        'first_page': page, 'last_page': page, 'page_size': selected['page_size']}
                    or body['page'] != page or body['page_size'] != selected['page_size']
                    or receipt['operation'] != 'result' or receipt['outcome'] != 'completed'
                    or receipt['registry_ref'] != body['registry_ref'] or receipt['job_ref'] != body['job_ref']
                    or receipt['request_sha256'] != body['request_sha256']
                    or source['retrieved_at'] != receipt['observed_at']
                    or source.get('parent_source_refs') != [body['source_ref']]
                    or source.get('text_ref') is not None or source.get('request_ref') is not None):
                raise ValueError('api_information_publication_conflict')
            raw_source = self.store.get(body['source_ref'])
            snapshot = self.ports.operations.read_snapshot(body['acquisition_receipt_ref'])
            raw_payload = {key: value for key, value in raw_source.items() if key not in {'id', 'record_type', 'origin'}}
            if (raw_source['id'] != identity('source', {'origin': 'external', 'record': raw_payload})
                    or raw_source.get('origin') != 'external' or raw_source.get('provider') != snapshot.service
                    or raw_source.get('uri') != snapshot.url or raw_source.get('retrieved_at') != snapshot.retrieved_at
                    or json.loads(self.store.get_artifact(raw_source['request_ref'])) != {
                        'request': snapshot.request, 'transport': snapshot.transport}
                    or self.store.get_artifact(raw_source['artifact_ref']) != snapshot.content
                    or snapshot.request['page'] != page or snapshot.request['page_size'] != selected['page_size']
                    or snapshot.transport['job_ref'] != body['job_ref']):
                raise ValueError('api_information_publication_conflict')
            hits = json.loads(snapshot.content)['result']['hits']
            for row in body['publication_rows']:
                expected = {'version', 'registry_ref', 'job_ref', 'request_sha256', 'publication_operation_key',
                    'acquisition_receipt_ref', 'source_ref', 'subject_ref', 'provider', 'page', 'page_size',
                    'hit_ordinal', 'domain_ordinal', 'record_ref', 'record_type'}
                if (set(row) != expected or row['version'] != ROW_VERSION or row['registry_ref'] != self.registry['registry_ref']
                        or row['job_ref'] != body['job_ref'] or row['request_sha256'] != body['request_sha256']
                        or row['publication_operation_key'] != body['operation_key']
                        or row['acquisition_receipt_ref'] != body['acquisition_receipt_ref']
                        or row['source_ref'] != body['source_ref'] or row['subject_ref'] != inspected['request']['subject_ref']
                        or row['provider'] != 'hmmer' or row['page'] != page or row['page_size'] != selected['page_size']
                        or type(row['hit_ordinal']) is not int or row['hit_ordinal'] < 0
                        or row['domain_ordinal'] is not None and (type(row['domain_ordinal']) is not int or row['domain_ordinal'] < 0)
                        or row['record_ref'] not in outcome['record_refs'] or row['record_type'] not in {'reference', 'observation'}
                        or self.store.get(row['record_ref'])['record_type'] != row['record_type']):
                    raise ValueError('api_information_publication_row_conflict')
                record = self.store.get(row['record_ref'])
                if (row['hit_ordinal'] >= len(hits) or record.get('source_ref') != body['source_ref']
                        or row['domain_ordinal'] is not None and row['domain_ordinal'] >= len(hits[row['hit_ordinal']].get('domains', []))
                        or row['record_type'] == 'reference' and row['domain_ordinal'] is not None
                        or row['record_type'] == 'observation' and record.get('subject_refs') != [body['subject_ref']]):
                    raise ValueError('api_information_publication_row_conflict')
                rows.append(json_value(row))
        return rows
