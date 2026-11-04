"""Received source-qualified API duration facts and optional typed union view.

The reader owns no score, transport, statistical refresh or continuation rule.
The optional wrapper reuses the existing native information unit exactly.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import math

from .communication import REFERENCE_FORMATS, ReportBoundaryError, plain
from .domain import canonical, identity
from .hmmer_resource_information import json_value, utc
from .native_timing_information import NativeTimingInformation, validate_native_measurements
from .api_timing_records import DURATION_MEASURE, OBSERVATION_UNIT, reported_result_identity

PROVIDER = 'episode.hmmer_reported_timing'
SOURCE_VERSION = 'api_reported_timing_source_v1'

API_MEASUREMENT_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['receipt_ref', 'job_ref', 'duration_measure', 'observation_unit', 'elapsed_seconds', 'observed_at'],
    'properties': {
        'receipt_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
        'job_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'resource_execution'},
        'duration_measure': {'type': 'string', 'const': DURATION_MEASURE},
        'observation_unit': {'type': 'string', 'const': OBSERVATION_UNIT},
        'elapsed_seconds': {'type': 'number', 'minimum': 0},
        'observed_at': {'type': 'string', 'format': 'identifier',
            'x-reference-namespace': 'api_timing_observation_timestamp'}}}


def _fact(reference, witness):
    return {'receipt_ref': reference, **{key: witness[key] for key in
        ('job_ref', 'duration_measure', 'observation_unit', 'elapsed_seconds', 'observed_at')}}


class ApiReportedTimingFactReader:
    def __init__(self, ledger, *, ports):
        from .api_timing_records import ApiTimingLedger
        from .public_search_operations import PublicSearchPorts
        if (type(ledger) is not ApiTimingLedger or not isinstance(ports, PublicSearchPorts)
                or ports.operations.store is not ledger.store
                or ports.result_publisher.store is not ledger.store
                or getattr(ports.operations, 'timing', None) is not ledger
                or json_value(ports.registry) != ledger.as_record()['registry']
                or ports.registry['resource_id'] != ledger.binding.resource_id):
            raise ValueError('api_timing_reader_binding_mismatch')
        self.ledger, self.ports = ledger, ports
        self.store = ledger.store
        self._record = {'version': 'api_reported_timing_fact_reader_v1', 'ledger': ledger.as_record()}

    def as_record(self):
        return deepcopy(self._record)

    def _witness(self, witness, *, scope):
        """Requalify the first ledger fact using only actual public custody ports."""
        from .provider_jobs import validate_remote_identity
        if witness != self.ledger.read_measurement(witness['measurement_ref']):
            raise ValueError('api_timing_witness_conflict')
        operations = self.ports.operations
        inspected = operations.inspect(witness['job_ref'])
        order, request = inspected['order'], inspected['request']
        original_scope = operations.open_scope(witness['job_ref'])['scope']
        if not self.store.scope_contains(self.store.validate_scope(plain(scope)), original_scope):
            raise ValueError('api_timing_source_outside_scope')
        receipt = operations.read_operation(witness['acquisition_receipt_ref'])
        snapshot = operations.read_snapshot(witness['acquisition_receipt_ref'])
        native = json.loads(snapshot.content)
        validate_remote_identity(native, request, witness['remote_id'], result=True)
        stats = native['result']['stats']
        database = stats.get('database') if type(stats) is dict else None
        if isinstance(database, dict):
            database = database.get('id')
        if (receipt['operation'] != 'result' or receipt['outcome'] != 'completed'
                or receipt['failure'] is not None or native['status'] != 'SUCCESS'
                or receipt['job_ref'] != witness['job_ref']
                or receipt['registry_ref'] != witness['registry_ref']
                or receipt['remote_id'] != witness['remote_id']
                or witness['registry_ref'] != self.ports.registry['registry_ref']
                or witness['resource_id'] != self.ports.registry['resource_id']
                or receipt['request_sha256'] != order['request_sha256']
                or witness['request_sha256'] != order['request_sha256']
                or receipt['snapshot_ref'] != witness['snapshot_ref']
                or snapshot.sha256 != witness['entity_sha256']
                or receipt['observed_at'] != witness['observed_at']
                or witness['field_path'] != '$.result.stats.elapsed'
                or witness['duration_measure'] != DURATION_MEASURE
                or witness['observation_unit'] != OBSERVATION_UNIT
                or witness['semantics_version'] != 'hmmer_reported_elapsed_source_v1'
                or witness['measurement_ref'] != reported_result_identity(witness['registry_ref'], witness['remote_id'])['measurement_ref']
                or type(stats) is not dict
                or any(stats.get(key) != actual for key, actual in
                    (('id', witness['remote_id']), ('algo', request['algorithm'])))
                or database != request['database']
                or type(stats.get('elapsed')) not in (int, float)
                or not math.isfinite(stats['elapsed']) or stats['elapsed'] < 0
                or stats['elapsed'] != witness['elapsed_seconds']):
            raise ValueError('api_timing_source_custody_conflict')
        utc(witness['observed_at'])
        return original_scope, request['subject_ref']

    def read_source(self, reference, *, scope):
        source = self.store.get(reference)
        if source.get('record_type') != 'source' or source.get('provider') != PROVIDER:
            return None
        try:
            body = json.loads(self.store.get_artifact(source['artifact_ref']))
            if (type(body) is not dict or set(body) != {'version', 'run_id', 'scope', 'subject_ref', 'witness'}
                    or body['version'] != SOURCE_VERSION or body['run_id'] != self._record['ledger']['run_id']):
                raise ValueError('api_timing_source_body_conflict')
            original_scope, subject = self._witness(body['witness'], scope=scope)
            payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
            expected = {'provider': PROVIDER, 'accession': body['witness']['measurement_ref'],
                'uri': None, 'artifact_ref': source['artifact_ref'], 'text_ref': None, 'request_ref': None,
                'version': SOURCE_VERSION, 'retrieved_at': body['witness']['observed_at'], 'operand_refs': [subject]}
            if (payload != expected or source.get('origin') != 'tool'
                    or reference != identity('source', {'origin': 'tool', 'record': payload})
                    or body['scope'] != original_scope or body['subject_ref'] != subject
                    or self.store.get_artifact(source['artifact_ref']) != canonical(body).encode()):
                raise ValueError('api_timing_source_identity_conflict')
            return body
        except (KeyError, TypeError) as error:
            raise ValueError('api_timing_source_body_conflict') from error

    def publish(self, measurement_ref):
        witness = self.ledger.read_measurement(measurement_ref)
        original = self.ports.operations.open_scope(witness['job_ref'])['scope']
        scope, subject = self._witness(witness, scope=original)
        body = {'version': SOURCE_VERSION, 'run_id': self._record['ledger']['run_id'],
            'scope': scope, 'subject_ref': subject, 'witness': witness}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(body), 'application/json')
            source = self.store.put('source', {'provider': PROVIDER, 'accession': measurement_ref,
                'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
                'version': SOURCE_VERSION, 'retrieved_at': witness['observed_at'], 'operand_refs': [subject]}, origin='tool')
            self.read_source(source['id'], scope=scope)
        return source['id']

    def read_details(self, store, scope, *, known_record_refs, initial_known_record_refs,
                     details_limit, details_offset):
        if store is not self.store:
            raise ValueError('api_timing_reader_store_mismatch')
        if (details_limit is not None and (type(details_limit) is not int or details_limit < 0)
                or type(details_offset) is not int or details_offset < 0):
            raise ValueError('api_timing_details_require_nonnegative_page')
        store.validate_scope(scope)
        def key(body):
            witness = body['witness']
            return OBSERVATION_UNIT, witness['registry_ref'], witness['remote_id']
        def received(ref):
            try:
                return self.read_source(ref, scope=scope)
            except ValueError as error:
                if str(error) != 'api_timing_source_outside_scope':
                    raise
                return None
        seen = {key(body) for ref in initial_known_record_refs if (body := received(ref)) is not None}
        facts, identities = [], []
        for ref in known_record_refs:
            body = received(ref)
            if body is None or key(body) in seen:
                continue
            seen.add(key(body))
            witness = body['witness']
            facts.append(_fact(ref, witness))
            identities.append({'kind': OBSERVATION_UNIT, 'registry_ref': witness['registry_ref'], 'remote_id': witness['remote_id']})
        stop = None if details_limit is None else details_offset + details_limit
        rows = facts[details_offset:stop]
        return {'version': 'api_reported_timing_facts_v1', 'new_information_identities': identities,
            'reported_result_count': len(facts), 'api_execution_measurements': rows,
            'next_offset': details_offset+len(rows) if details_offset+len(rows) < len(facts) else None}

    def resolve(self, scope, reference, namespace, *, known_record_refs):
        if namespace not in {'api_timing_observation_timestamp', 'resource_execution', 'source'}:
            return False
        for ref in known_record_refs:
            try:
                body = self.read_source(ref, scope=scope)
            except ValueError as error:
                if str(error) != 'api_timing_source_outside_scope':
                    raise
                continue
            if body is None:
                continue
            if reference == {'source': ref, 'resource_execution': body['witness']['job_ref'],
                    'api_timing_observation_timestamp': body['witness']['observed_at']}[namespace]:
                return True
        return False

    def validate_report(self, store, value, *, schema):
        if store is not self.store:
            raise ValueError('api_timing_reader_store_mismatch')
        def visit(node, declared):
            if isinstance(node, Mapping):
                properties = declared.get('properties', {})
                for name, field in properties.items():
                    if (field.get('format') in REFERENCE_FORMATS and field.get('x-reference-namespace') == 'source'
                            and node.get(name) is not None):
                        source = store.get(node[name])
                        if source.get('provider') != PROVIDER:
                            if node.get('duration_measure') == DURATION_MEASURE:
                                raise ReportBoundaryError('API timing source is not qualified', code='api_timing_fact_mismatch')
                            continue
                        body = self.read_source(node[name], scope=json.loads(store.get_artifact(source['artifact_ref']))['scope'])
                        actual = _fact(node[name], body['witness'])
                        if any(node[key] != actual[key] for key in node.keys() & actual.keys()):
                            raise ReportBoundaryError('API timing fields differ from their source', code='api_timing_fact_mismatch')
                for name, child in node.items():
                    if name in properties:
                        visit(child, properties[name])
            elif isinstance(node, (list, tuple)) and 'items' in declared:
                for child in node:
                    visit(child, declared['items'])
        visit(value, schema)


class ReceivedExecutionTimingInformation:
    def __init__(self, native, api):
        if type(native) is not NativeTimingInformation or type(api) is not ApiReportedTimingFactReader:
            raise TypeError('typed_received_timing_components_required')
        if native.information_unit != api.ledger.binding.monitoring_information_unit:
            raise ValueError('api_timing_information_unit_mismatch')
        self.native, self.api = native, api
        self.information_unit = native.information_unit

    def as_record(self):
        return {'version': 'received_execution_timing_information_v1', 'information_unit': self.information_unit,
            'native_duration_facts': self.native.as_record(), 'api_reported_duration_facts': self.api.as_record(),
            'contribution': 'existing_unit_per_new_typed_received_duration_fact',
            'baseline': 'union_of_original_inherited_native_and_api_duration_identities',
            'scientific_credit': False, 'controller_effect': 'preserve_existing_controller_scalar_paths'}

    def read_details(self, store, scope, *, known_execution_refs, initial_execution_refs,
                     known_record_refs, initial_known_record_refs, details_limit, details_offset):
        native = self.native.read_details(store, scope, known_execution_refs=known_execution_refs,
            initial_execution_refs=initial_execution_refs, details_limit=details_limit, details_offset=details_offset)
        api = self.api.read_details(store, scope, known_record_refs=known_record_refs,
            initial_known_record_refs=initial_known_record_refs, details_limit=details_limit, details_offset=details_offset)
        # Each component already subtracts its original baseline and deduplicates
        # its semantic identity. Their declared kinds are disjoint typed sets.
        count = native['measured_attempt_count'] + len({(row['kind'], row['registry_ref'], row['remote_id'])
            for row in api['new_information_identities']})
        credit = self.information_unit * count
        if not math.isfinite(credit):
            raise ValueError('finite_monitoring_information_credit_required')
        return {'credit': credit, 'monitoring_information_credit': credit,
            'monitoring_information_binding': self.as_record(),
            'measured_attempt_count': native['measured_attempt_count'], 'reported_result_count': api['reported_result_count'],
            'native_receipt_count': native['receipt_count'], 'api_receipt_count': api['reported_result_count'],
            'native_execution_measurements': native['native_execution_measurements'],
            'api_execution_measurements': api['api_execution_measurements'],
            'native_next_offset': native['next_offset'], 'api_next_offset': api['next_offset']}

    def __call__(self, store, scope, **knowledge):
        return self.read_details(store, scope, details_limit=0, details_offset=0, **knowledge)

    def report_sources(self):
        result = self.native.report_sources()
        result['monitoring_information_credit'] = {'type': 'number', 'meaning':
            'One caller-bound monitoring-information unit per new typed received duration identity in the union of native physical phase attempts and logical provider-job reported results, after the original inherited baseline. Repeated delivery earns none. Scientific and operational controller scalars retain their original meanings.'}
        result['api_execution_measurements'] = {'type': 'array', 'meaning':
            'Original source-qualified provider-reported search seconds, once per newly received logical provider job after the inherited baseline. Physical attempts, retry history, queue wait and turnaround are unknown.',
            'report_schema': {'type': 'array', 'items': deepcopy(API_MEASUREMENT_SCHEMA), 'x-source': 'api_execution_measurements'}}
        return result

    def validate_report(self, store, value, *, schema):
        validate_native_measurements(store, value, schema=schema)
        self.api.validate_report(store, value, schema=schema)


__all__ = ['ApiReportedTimingFactReader', 'ReceivedExecutionTimingInformation', 'API_MEASUREMENT_SCHEMA']
