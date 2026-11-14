"""A106 intervention AppService operations in its existing episode loop.

This module records calls and qualifies their handoffs and acquisitions. Service
implementations supply individual native operations; neither layer owns a model
loop, polling schedule, retry decision or scientific interpretation.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path

from .acquisition import AcquisitionError, SourceSnapshot
from .api_error_feedback import api_error_feedback, api_error_response
from .communication import plain
from .domain import ContractError, identity, validate_schema
from .execution_contracts import (canonical, checked,
    digest, validate_api_assignment, validate_target)
from .practical_execution_records import validate_completion_proof
from .practical_execution_state import _immutable, _read


PROVIDER = 'episode.api_service_handoff'
VERSION = 'api_service_execution_v1'
HANDOFF_VERSION = 'api_service_handoff_v1'
EVENT_FIELDS = {'kind', 'state', 'native_handle', 'handoff_ready',
                'result_available', 'facts', 'failure_code'}
STATES = {'submitted', 'running', 'completed', 'failed', 'unknown'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _outcome(key, result=None, *, refs=(), status='completed', code=None, **feedback):
    return {'status': status, 'operation_ref': identity('api_operation', {'key': key}),
        'record_refs': list(refs), 'changed_record_refs': list(refs), 'result': result,
        'feedback': None if code is None else {'category': 'provider', 'code': code, **feedback}}


class APIServiceExecution:
    """A106 selected intervention AppService operations and original receipts."""

    def __init__(self, store, *, run_id, directory, configuration, tool_registry,
                 handoff_unit, acquired_record_unit, received_input_reader=None, credit_projector=None, decision_summary=None, report_facts=None, completion_projector=None, publication_completion=None, application_return_owner=None, context_reader=None, operation_catalog=None, support_receipts=None, support_report_validator=None):
        from .api_services import build_service
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('explicit_api_execution_run_required')
        for unit in (handoff_unit, acquired_record_unit):
            if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
                raise ValueError('explicit_positive_operational_credit_units_required')
        self.store, self.run_id = store, run_id
        if received_input_reader is not None and not callable(received_input_reader):
            raise ValueError('api_received_input_reader_must_be_callable')
        self.received_input_reader = received_input_reader
        if support_receipts is not None and not callable(support_receipts):
            raise ValueError("api_support_receipts_must_be_callable")
        self._support_receipts = support_receipts
        if support_report_validator is not None and not callable(support_report_validator):
            raise ValueError("api_support_report_validator_must_be_callable")
        self._support_report_validator = support_report_validator
        if operation_catalog is not None and not callable(operation_catalog):
            raise ValueError("api_operation_catalog_must_be_callable")
        self._operation_catalog = operation_catalog
        if context_reader is not None and not callable(context_reader):
            raise ValueError("api_context_reader_must_be_callable")
        self._context_reader = context_reader
        if credit_projector is not None and not callable(credit_projector):
            raise ValueError("api_credit_projector_must_be_callable")
        self._credit_projector = credit_projector
        if decision_summary is not None and not callable(decision_summary):
            raise ValueError("api_decision_summary_must_be_callable")
        self._decision_summary = decision_summary
        if report_facts is not None and not callable(report_facts):
            raise ValueError("api_report_facts_must_be_callable")
        self._report_facts_projector = report_facts
        if completion_projector is not None and not callable(completion_projector):
            raise ValueError("api_completion_projector_must_be_callable")
        self._completion_projector = completion_projector
        if publication_completion is not None and not callable(publication_completion):
            raise ValueError("api_publication_completion_must_be_callable")
        self._publication_completion_projector = publication_completion
        self.directory = Path(directory)/'api-service-execution'/digest(run_id)
        self.configuration = json.loads(canonical(configuration))
        self.tools, self.clients = tool_registry, tool_registry.clients
        self.handoff_unit, self.acquired_record_unit = handoff_unit, acquired_record_unit
        from .api_selected_effects import SelectedAPIEffects
        self.selected_effects = SelectedAPIEffects(directory, run_id=run_id)
        if not self.configuration or tool_registry.store is not store:
            raise ValueError('actual_api_services_and_tool_registry_required')
        self.services = {}
        for resource_id, config in self.configuration.items():
            if config.get('kind') != 'api':
                raise ValueError('unsupported_api_resource_configuration')
            self.services[resource_id] = build_service(config.get('service'), config, tool_registry)
        from .bvbrc_appservice_host import BVBRCAppServiceHost
        self.appservice = BVBRCAppServiceHost(self)
        from .library.bvbrc_application_return_access import BVBRCApplicationReturns
        self.application_returns = BVBRCApplicationReturns(self, owner=application_return_owner)

    def assignment_schema(self, resource_id):
        if resource_id not in self.configuration:
            raise ValueError('api_resource_not_bound')
        from .execution_contracts import API_SERVICE_ASSIGNMENT_SCHEMA
        schema = deepcopy(API_SERVICE_ASSIGNMENT_SCHEMA)
        schema['properties']['service'] = {'const': self.services[resource_id].service}
        schema['properties']['request'] = deepcopy(self.services[resource_id].request_schema)
        schema['properties']['resource_id'] = {'type': 'string', 'const': resource_id}
        return schema

    def validate_assignment(self, assignment, *, scope=None):
        assignment = validate_api_assignment(plain(assignment))
        resource_id = assignment['resource_id']
        schema = self.assignment_schema(resource_id)
        checked(assignment, schema, 'api_service_assignment_conflict')
        service = self.services[resource_id]
        service.validate_request(assignment['request'], plain(scope) if scope is not None else None)
        for key, value in assignment['constraints'].items():
            if key == 'allowed_resource_ids':
                valid = isinstance(value, list) and resource_id in value
            elif key == 'allowed_kinds':
                valid = isinstance(value, list) and 'api' in value
            elif key == 'kind':
                valid = value == 'api'
            elif key in {'resource_id', 'service', 'request', 'endpoint'}:
                valid = value == assignment[key]
            else:
                valid = False
            if not valid:
                raise ValueError('api_service_constraint_conflict:'+key)
        return assignment

    def capabilities(self, resource_id):
        return self.services[resource_id].capabilities()

    def operation_contracts(self, resource_id, role):
        """Actual configured service contracts; no query or target is fabricated."""
        if resource_id not in self.configuration:
            raise ValueError('api_resource_not_bound')
        if role not in {'launch_api', 'results'}:
            raise ValueError('api_execution_role_required')
        service = self.services[resource_id]
        from .bvbrc_appservice_tool_info import bvbrc_appservice_tool_contracts
        return [{key: deepcopy(row[key]) for key in ('name', 'description', 'input_schema', 'instructions')}
            for row in bvbrc_appservice_tool_contracts(resource_id=resource_id)
            if any(route['resource_role'] == role for route in row['invocation_route']['routes'])]
    def is_handoff_source(self, reference):
        try:
            from .bvbrc_appservice_records import PROVIDER as APPSERVICE_PROVIDER
            if self.store.get(reference).get('provider') == APPSERVICE_PROVIDER:
                self.appservice.read_handoff(reference)
                return True
            return False
        except (ValueError, KeyError, OSError, TypeError):
            return False

    def _context(self, context, *, verify_artifacts=True,
                 _completed_appservice_download=False):
        reader = getattr(self, '_context_reader', None)
        if reader is not None:
            return reader(self, context, verify_artifacts=verify_artifacts,
                _completed_appservice_download=_completed_appservice_download)
        from .library.standalone_api_context import standalone_api_context
        return standalone_api_context(self, context, verify_artifacts=verify_artifacts,
            _completed_appservice_download=_completed_appservice_download)

    def validate_result_selector(self, target, selector):
        self.validate_assignment(target['assignment'], scope=target['scope'])
        schema = self.services[target['resource_id']].selector_schema
        value = checked(selector, schema, 'invalid_api_service_result_selector')
        self.services[target['resource_id']].result_catalog(target['assignment']['request'], value)
        return value

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

    def initialize(self, context):
        self._context(context)
        self.appservice.validate_assignment(context)
        self._manifest(context)
        return {'assignment': plain(context.assignment), 'scope': plain(context.scope)}

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

    def catalog(self, context):
        catalog = getattr(self, '_operation_catalog', None)
        if catalog is not None:
            return catalog(self, context)
        from .library.standalone_api_catalog import standalone_api_catalog
        return standalone_api_catalog(self, context)

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

    def _native_handle(self, target):
        return self._read_handoff(target['handle'], target['scope'])['event']['native_handle']

    def _submission_snapshot(self, target):
        body = self.appservice.read_handoff(target['handle'], target['scope'])
        return self._load_snapshot(body['snapshot'])

    async def execute(self, context, name, arguments, operation_key):
        try:
            arguments = plain(arguments)
            if (name == 'api.bvbrc_appservice.download' and type(arguments) is dict
                    and 'max_bytes' not in arguments):
                cached = self.appservice.legacy_cached_download(context, name, arguments, operation_key)
                if cached is not None:
                    return cached
            self.initialize(context)
            assignment, service, target = self._context(context)
            entry = next((row for row in self.catalog(context) if row['name'] == name), None)
            if entry is None:
                raise ValueError('api_operation_not_available')
            validate_schema(arguments, entry['input_schema'])
            self._selected(context, name, arguments, operation_key)
        except (ValueError, ContractError, KeyError, TypeError) as error:
            return _outcome(operation_key, status='invalid', code=str(error),
                **api_error_feedback(error))
        directory = self._manifest(context)/'actions'/digest(operation_key)
        directory.mkdir(exist_ok=True)
        # Acquire outside the event loop: a concurrent recovery must not block
        # the coroutine that owns the selected request and will release the lock.
        with (directory/'.lock').open('a') as lock:
            await asyncio.to_thread(fcntl.flock, lock, fcntl.LOCK_EX)
            try:
                return await self._execute_locked(context, assignment, service, target,
                    name, arguments, operation_key, directory)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    async def _execute_locked(self, context, assignment, service, target, name, arguments, key, directory):
        return await self.appservice.execute_locked(context, assignment, service, target,
            name, arguments, key, directory)

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        value = json.loads(raw)
        if raw != canonical(value).encode('utf-8') or reference != 'artifact_'+hashlib.sha256(raw).hexdigest():
            raise ValueError('api_service_artifact_identity_conflict')
        return value

    def _original_context(self, manifest):
        from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
        return BindingContext(self.run_id, manifest['episode_id'], manifest['role'],
            ((manifest['role'], 'original'),), manifest['scope'], manifest['assignment'], {})

    def _read_handoff(self, reference, scope, *, verify_artifacts=True):
        return self.appservice.read_handoff(reference, scope)

    def scope(self, handoff_ref):
        return self.appservice.read_handoff(handoff_ref)['scope']

    def read_target(self, handoff_ref, scope, *, verify_artifacts=True,
                    _completed_appservice_download=False):
        return self.appservice.read_target(handoff_ref, scope,
            **({'_completed_download': True} if _completed_appservice_download else {}))

    def _observation(self, target, event, snapshot, provenance=()):
        facts = deepcopy(event['facts'])
        if snapshot is not None and (event['state'] == 'failed' or event['failure_code']):
            facts['error_response'] = api_error_response(snapshot)
        return {'observed_at': snapshot.retrieved_at if snapshot is not None else _now(),
            'state': event['state'], 'returncode': None, 'failure_code': event['failure_code'],
            'result_available': event['result_available'], 'measurements': [], 'outputs': [], 'logs': [],
            'provenance_refs': [target['handle'], *provenance],
            'native': {'service': target['assignment']['service'], 'kind': event['kind'],
                'handle': event['native_handle'], 'facts': facts}}

    def observe_target(self, target, *, operation_key, native_operation=None,
                       observation_context=None):
        target = validate_target(plain(target))
        from .bvbrc_appservice_monitor import AppServiceMonitor
        return AppServiceMonitor(self).observe(target, operation_key=operation_key,
            native_operation=native_operation, observation_context=observation_context)

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

    def read_result(self, reference, scope, *, episode_id=None, operation_key=None,
                    verify_artifacts=True):
        return self.appservice.publications.read(reference, scope, episode_id=episode_id)

    def result_identity(self, reference, scope):
        body = self.read_result(reference, scope)
        return self.appservice.publications.result_identity(body)

    def facts(self, context, completion_snapshot):
        return self.appservice.facts(context)

    def credit_view(self, context, receiver_selection):
        projector = getattr(self, '_credit_projector', None)
        if projector is not None:
            return projector(self, context, receiver_selection)
        from .library.standalone_api_credit import standalone_api_credit
        return standalone_api_credit(self, context, receiver_selection)

    def _completion(self, context):
        return self.appservice.completion(context)

    def completion_for_action(self, context, operation_key):
        proof = self._completion(context)
        return proof if proof is not None and proof['operation_key'] == operation_key else None

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
            return proof == self._completion(context)
        except (ValueError, ContractError, KeyError, TypeError, OSError):
            return False

    def resolve(self, context, reference, namespace):
        if context.run_id == self.run_id:
            from .library.bvbrc_application_facts import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                private_resolver = getattr(self.application_returns, 'resolve', None)
                if callable(private_resolver):
                    return private_resolver(context, reference, namespace)
                return (self.application_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.application_returns.resolve_received(context, reference, namespace))
            resolved = self.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if context.run_id != self.run_id or namespace not in {None, 'source', 'execution_handoff', 'execution_result'}:
            return False
        try:
            if namespace != 'execution_result':
                self.read_target(reference, context.scope)
                return True
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            pass
        try:
            self.read_result(reference, context.scope)
            return namespace != 'execution_handoff' and (namespace != 'source' or
                self.store.get(reference)['record_type'] == 'source')
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            return False

    def decision_context(self, context, current_view=None):
        summary = getattr(self, '_decision_summary', None)
        if summary is not None:
            return summary(self, context, current_view)
        from .library.standalone_api_summary import standalone_api_summary
        return standalone_api_summary(self, context, current_view)

__all__ = ['APIServiceExecution', 'PROVIDER', 'VERSION']
