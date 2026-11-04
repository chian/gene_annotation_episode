"""HMMER service operations within the existing resource Episode binding.

Iteration, waiting and continuation belong to shared method_loop. This adapter
executes one selected operation and records the original receiving proof; it
never chooses another job, resource or retry.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .communication import ReportBoundaryError, plain
from .episode_bindings import BindingContext
from .domain import ContractError
from .hmmer_resource_information import (ApiSearchInformationReader, INTERFACES, STATES,
    contains_page, digest, json_value, proof_receipt_ref, selector, utc)
from .public_search_operations import ProviderOperationInProgress, PublicSearchPorts
from .resource_records import HANDOFF_SCHEMA, LAUNCH_SCHEMA, RESULTS_SCHEMA, RESULTS_VERSION, _validate


def _obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _ref(namespace=None, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
        'x-reference-namespace': namespace}


def _outcome(result=None, failure=None):
    return {'status': 'failed' if failure else 'completed', 'record_refs': [],
        'changed_record_refs': [], 'result': result, 'feedback': failure}


def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references), 'diagnostic_ref': None, 'partial_record_refs': []}


class HmmerServiceResourceAdapter:
    def __init__(self, services, store, journal, *, ports: PublicSearchPorts,
                 timing=None, resource_estimator=None):
        if (not isinstance(ports, PublicSearchPorts) or journal.store is not store
                or getattr(ports.result_publisher, 'store', None) is not store):
            raise TypeError('explicit_hmmer_resource_ports_required')
        self.services, self.store, self.journal, self.ports = services, store, journal, ports
        self.information = ApiSearchInformationReader(store, run_id=journal.run_id, ports=ports)
        self.registry = json_value(ports.registry)
        self.resource_id = self.registry['resource_id']
        self.record_selection = None
        self.timing, self.resource_estimator = timing, resource_estimator
        self.timing_reader = None
        if timing is not None:
            from .api_timing_information import ApiReportedTimingFactReader
            from .resource_estimation import ResourceToolEstimator
            if (timing.store is not store or timing.as_record()['run_id'] != journal.run_id
                    or type(resource_estimator) is not ResourceToolEstimator
                    or resource_estimator.as_record() != ResourceToolEstimator.with_reported_results().as_record()):
                raise ValueError('api_timing_adapter_binding_mismatch')
            self.timing_reader = ApiReportedTimingFactReader(timing, ports=ports)

    def bind_record_selection(self, callback):
        self.record_selection = callback

    def as_record(self):
        value = {'version': 'hmmer_service_resource_adapter_v1', 'resource_id': self.resource_id,
            'registry': json_value(self.registry),
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        if self.timing is not None:
            value.update(version='hmmer_service_resource_adapter_v2',
                timing=self.timing.as_record(), resource_estimator=self.resource_estimator.as_record())
        return value

    def capability(self):
        return {'resource_id': self.resource_id, 'kind': 'api', 'availability': 'unknown',
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'provenance_refs': [self.registry['registry_ref']], 'knowledge_entry_ids': [],
            'tool_names': ['api_search.inspect', 'api_search.submit', 'api_search.recover_submission', 'api_search.check_handoff']}

    def _selection(self):
        return self.information.selection()

    @staticmethod
    def _assigned_context(parent, role, value, scope):
        return BindingContext(parent.run_id, parent.episode_id, role,
            (*parent.path[:-1], (role, parent.path[-1][1])), scope, value, plain(parent.request))

    def prepare_assignment(self, context, role, launch_assignment, scope, operation_key):
        value = json_value(launch_assignment)
        if role == 'results':
            _validate({key: value[key] for key in RESULTS_SCHEMA['properties']}, RESULTS_SCHEMA)
            child = self._assigned_context(context, role, value, scope)
            inspected, _ = self.information.qualify_results(child)
            value['adapter_assignment'] = inspected['order']
            return value
        if role != 'launch_api':
            raise ValueError('hmmer_resource_requires_api_role')
        _validate({key: value[key] for key in LAUNCH_SCHEMA['properties']}, LAUNCH_SCHEMA)
        child = self._assigned_context(context, role, value, scope)
        self.information.qualify_launch(child)
        request, fasta = self.information.request_for_assignment(child)
        job = value['job_request']
        if 'existing_job_ref' in job:
            order = self.ports.operations.open_order(job['existing_job_ref'])
        else:
            order = self.ports.operations.order(operation_key=operation_key, provider='hmmer',
                scope=self.store.validate_scope(plain(scope)),
                subject_ref=request['subject_ref'], query_fasta=fasta, algorithm=request['algorithm'],
                database=request['database'], parameters=request['parameters'], page_size=request['page_size'])
        if order['request_sha256'] != digest(request):
            raise ValueError('resource_assignment_conflict')
        value['adapter_assignment'] = order
        return value

    def _order(self, context):
        if not self.information.owns(context):
            raise ValueError('resource_assignment_conflict')
        assignment = plain(context.assignment)
        if context.role == 'results':
            inspected, _ = self.information.qualify_results(context)
            return inspected['order']
        self.information.qualify_launch(context)
        order = assignment.get('adapter_assignment')
        if order is None or self.ports.operations.open_order(order['job_ref']) != order:
            raise ValueError('resource_assignment_conflict')
        return order

    def catalog(self, context):
        if not self.information.owns(context):
            return []
        if context.role == 'results':
            return [{'name': 'api_search.acquire', 'description':
                'Acquire one assigned HMMER result page. Preserve the original job; scientific integration stays with the parent.',
                'input_schema': _obj({'page': {'type': 'integer', 'minimum': 1}})},
                {'name': 'api_search.coverage', 'description':
                    'Read saved acquisition coverage; no HTTP or extraction.', 'input_schema': _obj({})}]
        return [{'name': name, 'description': description, 'input_schema': schema} for name, description, schema in (
            ('api_search.inspect', 'Read the actual assigned request, saved identity and operation references without HTTP.', _obj({})),
            ('api_search.submit', 'Attempt exactly the assigned submission; retry_of explicitly names a proven not-sent predecessor.',
                _obj({'retry_of': _ref('provider_operation', nullable=True)})),
            ('api_search.recover_submission', 'Recover the original saved response and UUID without another POST.', _obj({})),
            ('api_search.check_handoff', 'Observe the original job once and check its bound monitor/results receivers without fetching pending results.', _obj({})))]

    def _operation_outcome(self, receipt):
        result = _outcome(json_value(receipt), receipt['failure'] if receipt['outcome'] == 'failed' else None)
        result['provider_operation_refs'] = [receipt['receipt_ref']]
        return result

    @staticmethod
    def _in_progress(error):
        # No terminal provider receipt exists for the still-owned operation.
        return _outcome({'job_ref': error.job_ref, 'operation_key': error.operation_key},
            _failure('submission_in_progress', [error.job_ref]))

    async def execute(self, context, tool_name, arguments, operation_key):
        entries = {entry['name']: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ValueError('tool_not_owned_by_resource_role')
        arguments = _validate(arguments, entries[tool_name]['input_schema'])
        if self.store.db.in_transaction:
            raise ValueError('api_operation_requires_committed_store')
        if tool_name == 'api_search.check_handoff':
            replay = self.information.selected_handoff(context, operation_key)
            if replay is not None:
                return replay
        try:
            order = self._order(context)
        except (ValueError, KeyError) as error:
            code = ('resource_selection_conflict' if str(error) in {
                'resource_selection_conflict', 'unsupported_api_constraints', 'explicit_resource_selection_required'}
                else 'resource_assignment_conflict')
            return _outcome(failure=_failure(code))
        if tool_name == 'api_search.inspect':
            return _outcome(self.ports.operations.inspect(order['job_ref']))
        if tool_name == 'api_search.submit':
            try:
                receipt = await self.ports.operations.submit_once(order['job_ref'],
                    operation_key=operation_key, retry_of=arguments['retry_of'])
            except ProviderOperationInProgress as error:
                # The original action still owns its unfinished receipt. This
                # delivery neither terminates that operation nor invents one.
                return self._in_progress(error)
            return self._operation_outcome(receipt)
        if tool_name == 'api_search.recover_submission':
            return self._operation_outcome(self.ports.operations.recover_submission(order['job_ref'], operation_key=operation_key))
        if tool_name == 'api_search.check_handoff':
            return await self._check(context, order['job_ref'], operation_key)
        if tool_name == 'api_search.coverage':
            return _outcome(self.coverage(context))
        selected = selector(plain(context.assignment)['requested_data_selector'])
        if not contains_page(selected, arguments['page'], selected['page_size']):
            return _outcome(failure=_failure('requested_data_selector_conflict', [order['job_ref']]))
        try:
            receipt = await self.ports.operations.result_once(order['job_ref'], operation_key=operation_key,
                page=arguments['page'], page_size=selected['page_size'])
        except ProviderOperationInProgress as error:
            return self._in_progress(error)
        if receipt['outcome'] != 'completed':
            return self._operation_outcome(receipt)
        timing = self._receive_timing(receipt)
        try:
            published = json_value(self.ports.result_publisher.publish(receipt['receipt_ref'],
                scope=plain(context.scope), operation_key=operation_key))
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
            if self.timing is None:
                raise
            return {**self._operation_outcome(receipt), 'status': 'failed',
                'feedback': _failure(str(error) if isinstance(error, ContractError)
                    else 'result_publication_failed', [order['job_ref']]), **timing}
        failures = published['result']['projection_failures']
        return {'status': 'partial' if failures else 'completed', **published,
            'changed_record_refs': list(published['record_refs']),
            'feedback': {'code': 'partial_projection', 'projection_failures': failures} if failures else None,
            'provider_operation_refs': [receipt['receipt_ref']], **timing}

    def _receive_timing(self, receipt):
        if self.timing is None:
            return {}
        from .api_timing_records import timing_disposition as disposition
        try:
            value = self.timing.receive_result(self.ports.operations, receipt['receipt_ref'])
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error):
            value = disposition('unavailable', 'timing_custody_unavailable')
        refs = []
        if value.get('measurement_ref') is not None:
            try:
                reference = self.timing_reader.publish(value['measurement_ref'])
                refs.append(reference)
                value = {**value, 'source_ref': reference}
            except (ValueError, KeyError, TypeError, OSError, sqlite3.Error):
                value = {**value, 'state': 'unavailable', 'code': 'timing_source_publication_unavailable'}
        return {'api_timing_disposition': value, 'api_timing_refs': refs}

    async def _check(self, context, job_ref, operation_key):
        try:
            receipt = await self.ports.operations.status_once(job_ref, operation_key=operation_key)
        except ProviderOperationInProgress as error:
            return self._in_progress(error)
        if (receipt['outcome'] != 'completed' or receipt['state'] not in STATES or receipt['remote_id'] is None):
            result = self._operation_outcome(receipt)
            result['status'] = 'failed'
            result['feedback'] = _failure('receiving_interface_unavailable', [job_ref])
            return result
        utc(receipt['observed_at'])
        assignment = plain(context.assignment)
        versions = (assignment['handoff']['submitted_input_versions'] if context.role == 'results'
            else assignment['immutable_input_versions'])
        handoff = {'version': 'execution_handoff_v1', 'execution_handle': job_ref,
            'resource_selection': self._selection(), 'submitted_input_versions': versions,
            **{name: {'provider_id': self.resource_id, 'target_handle': job_ref, 'contract_ref': contract}
                for name, contract in INTERFACES.items()},
            'checked_at': receipt['observed_at'],
            'check_record_refs': [proof_receipt_ref(context.run_id, context.episode_id, operation_key, receipt['receipt_ref'])],
            'state': 'usable', 'failure': None}
        outcome = {**self._operation_outcome(receipt), 'execution_handoff': handoff}
        return self.information.publish_handoff(context, outcome, operation_key)

    async def check_handoff(self, context, handoff, operation_key):
        replay = self.information.selected_handoff(context, operation_key)
        if replay is not None:
            return replay
        self.information.references_for_handoff(handoff, scope=plain(context.scope))
        inspected = self.information.validate_handoff(handoff, scope=plain(context.scope))
        qualified = self.information.qualify_launch(context)
        if (qualified['request_sha256'] != inspected['order']['request_sha256']
                or handoff['submitted_input_versions'] != qualified['immutable_input_versions']):
            raise ValueError('resource_assignment_conflict')
        return await self._check(context, handoff['execution_handle'], operation_key)

    def _known(self, context):
        refs = []
        if self.record_selection is not None:
            selected = self.record_selection(context)
            if selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id:
                raise ValueError('api_information_identity_conflict')
            refs.extend(selected['known_record_refs'])
        for row in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
                (context.run_id, context.episode_id)):
            refs.extend(json.loads(row[0]).get('resource_information_refs', []))
        return list(dict.fromkeys(refs))

    def execution_handoffs(self, context):
        if not self.information.owns(context):
            return []
        qualified = self.information.qualify_launch(context) if context.role != 'results' else None
        candidates = {}
        for reference in self._known(context):
            proof = self.information.read_handoff_source(reference, scope=plain(context.scope))
            if proof is None:
                continue
            if qualified is not None:
                self.information.qualify_handoff(context, qualified, proof)
            handoff = proof['execution_handoff']
            if context.role == 'results' and handoff['execution_handle'] != context.assignment['handoff']['execution_handle']:
                continue
            key = (proof['registry_ref'], proof['job_ref'])
            if key not in candidates or utc(handoff['checked_at']) > utc(candidates[key]['checked_at']):
                candidates[key] = handoff
        return [deepcopy(candidates[key]) for key in sorted(candidates)]

    def received_form_references(self, context, form, schema, operation_key):
        references = []
        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else ([] if value is None else [value])
                for handoff in values:
                    if handoff['resource_selection']['resource_id'] == self.resource_id:
                        references.extend(self.information.references_for_handoff(handoff, scope=plain(context.scope)))
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in declared:
                for child in value:
                    visit(child, declared['items'])
        visit(form, schema)
        return sorted(set(references))

    def initial_references(self, context):
        if context.role != 'results' or not self.information.owns(context):
            return []
        return self.information.references_for_handoff(plain(context.assignment)['handoff'], scope=plain(context.scope))

    def coverage(self, context):
        inspected, selected = self.information.qualify_results(context)
        pages, counts, refs, failures = set(), set(), [], 0
        for row in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND json_extract(action,'$.tool')='api_search.acquire' AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
                (context.run_id, context.episode_id)):
            result = json.loads(row[0])['result']
            if not contains_page(selected, result['page'], result['page_size']):
                raise ValueError('requested_data_selector_conflict')
            pages.add(result['page'])
            if result['page_count'] is not None:
                counts.add(result['page_count'])
            refs.append(result['publication_ref'])
            failures += len(result['projection_failures'])
        if not refs:
            return None
        self.information.own_result_rows(context)
        page_count = next(iter(counts)) if len(counts) == 1 else None
        upper = selected['last_page'] if page_count is None else min(selected['last_page'] or page_count, page_count)
        complete = None if upper is None else all(page in pages for page in range(selected['first_page'], upper + 1))
        return {'job_ref': inspected['order']['job_ref'], 'request_sha256': inspected['order']['request_sha256'],
            'selector': selected, 'acquired_pages': sorted(pages), 'page_count': page_count,
            'all_requested_pages_acquired': complete, 'projection_failure_count': failures,
            'publication_refs': list(dict.fromkeys(refs))}

    def fact_sources(self, role):
        from .hmmer_resource_information import SELECTOR_SCHEMA
        coverage = _obj({'job_ref': _ref('resource_execution'), 'request_sha256': _ref('api_request_digest'),
            'selector': deepcopy(SELECTOR_SCHEMA), 'acquired_pages': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}},
            'page_count': {'type': ['integer', 'null'], 'minimum': 0},
            'all_requested_pages_acquired': {'type': ['boolean', 'null']},
            'projection_failure_count': {'type': 'integer', 'minimum': 0},
            'publication_refs': {'type': 'array', 'items': _ref('source')}})
        # Parent forms require explicit semantic types, also for selector consts.
        coverage['properties']['selector']['properties']['version']['type'] = 'string'
        coverage['properties']['selector']['properties']['provider']['type'] = 'string'
        failure = _obj({'code': {'type': 'string', 'enum': [
            'prerequisite_missing', 'spacing_required', 'http_failure', 'connection_failed', 'request_timeout',
            'client_failure', 'response_invalid', 'remote_identity_conflict', 'submission_uncertain',
            'retry_not_authorized', 'submission_in_progress', 'result_readiness_unknown', 'result_not_ready',
            'remote_job_failed', 'request_conflict', 'unknown_job', 'operation_conflict', 'input_unavailable',
            'storage_failure', 'unsupported_provider']},
            'native_code': {**_ref('api_failure_code', nullable=True), 'format': 'identifier'},
            'phase': {'type': 'string', 'enum': ['local_request', 'local_preflight', 'submission', 'status', 'result', 'recovery', 'storage']},
            'submission_outcome': {'type': ['string', 'null'], 'enum': ['not_sent', 'remote_handle_returned', 'unknown', None]},
            'prerequisite': {'type': ['string', 'null'], 'enum': ['ncbi_contact', 'provider_access_dir', 'installed_client', None]},
            'retry_after_seconds': {'type': ['number', 'null'], 'minimum': 0},
            'http_status': {'type': ['integer', 'null'], 'minimum': 100, 'maximum': 599},
            'diagnostic_ref': _ref(None, nullable=True), 'response_snapshot_ref': _ref(None, nullable=True),
            'affected_refs': {'type': 'array', 'items': _ref()}, 'partial_record_refs': {'type': 'array', 'items': _ref()}})
        return {name: {'type': ['object', 'null'], 'meaning': meaning,
            'report_schema': {**shape, 'type': ['object', 'null'], 'x-source': name}}
            for name, shape, meaning in (
                ('api_failure', failure, 'The latest actual selected provider failure; no fresh operation at closure.'),
                ('api_result_coverage', coverage, 'Saved assigned-page acquisition and projection coverage, not scientific completion.'))}

    def facts(self, context, completion_snapshot):
        handoffs = self.execution_handoffs(context)
        failure = None
        if self.information.owns(context):
            row = self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND json_type(result,'$.provider_operation_refs')='array' ORDER BY decision_index DESC LIMIT 1",
                (context.run_id, context.episode_id)).fetchone()
            if row is not None:
                outcome = json.loads(row[0])
                references = outcome['provider_operation_refs']
                if references:
                    failure = self.ports.operations.read_operation(references[-1])['failure']
        return {'execution_handoffs': handoffs, 'execution_handoff': handoffs[0] if len(handoffs) == 1 else None,
            'api_failure': failure, 'api_result_coverage': self.coverage(context)
                if context.role == 'results' and self.information.owns(context) else None}

    def resolve(self, context, reference, namespace):
        if not self.information.owns(context):
            return False
        if namespace == 'resource_binding':
            return reference == self.resource_id
        if namespace == 'execution_registry':
            return reference == self.registry['registry_ref']
        if namespace == 'resource_interface':
            return reference in INTERFACES.values()
        if namespace in {'resource_execution', 'provider_job', 'execution_handle'}:
            try:
                inspected = self.ports.operations.inspect(reference)
                self.information._validate_order(inspected['order'], inspected['request'], plain(context.scope))
                return context.role == 'launch' or inspected['order'] == self._order(context)
            except (ValueError, KeyError, ContractError):
                return False
        handoffs = self.execution_handoffs(context)
        if context.role == 'results':
            handoffs.append(plain(context.assignment)['handoff'])
        if namespace == 'handoff_receipt':
            return any(reference in value['check_record_refs'] for value in handoffs)
        if namespace == 'resource_check_timestamp':
            return any(reference == value['checked_at'] for value in handoffs)
        if namespace in {'resource_input_version', 'resource_input_digest'}:
            field = 'version' if namespace == 'resource_input_version' else 'content_sha256'
            return any(reference == item[field] for value in handoffs for item in value['submitted_input_versions'])
        if namespace in {'provider_operation', 'api_request_digest', 'api_failure_code'}:
            for row in self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL',
                    (context.run_id, context.episode_id)):
                outcome = json.loads(row[0])
                for receipt_ref in outcome.get('provider_operation_refs', []):
                    receipt = self.ports.operations.read_operation(receipt_ref)
                    values = {'provider_operation': receipt_ref, 'api_request_digest': receipt['request_sha256'],
                        'api_failure_code': (receipt.get('failure') or {}).get('native_code')}
                    if reference == values[namespace]:
                        return True
        return False

    def validate_report(self, context, form, original_schema):
        if not self.information.owns(context):
            return
        facts = self.facts(context, {})
        for name, declared in original_schema.get('properties', {}).items():
            source = declared.get('x-source')
            if source in {'api_failure', 'api_result_coverage'} and plain(form[name]) != facts[source]:
                raise ReportBoundaryError('API recorded facts differ from selected work', code='api_recorded_fact_mismatch', field=name)

    def credit_view(self, context, receiver_selection):
        return self.services.bound_role_credit(context, receiver_selection)

    def decision_context(self, context):
        if self.timing is None or context.role not in {'launch', 'launch_api'} or not self.information.owns(context):
            return {'resource_tool_estimates': []}
        from .api_timing_records import timing_disposition as disposition
        values = {'resource_tool_estimates': [], 'api_reported_execution_expectations': [],
            'api_reported_execution_forecasts': [], 'api_execution_options': [],
            'api_timing_export_recovery': None, 'api_timing_planning_disposition': None}
        try:
            self.information.qualify_launch(context)
            request, _ = self.information.request_for_assignment(context)
            capture = self.timing.statistics.capture(request)
            values['api_reported_execution_expectations'] = [capture]
            forecasts = self.resource_estimator.estimate_reported_context(capture)
            values['api_reported_execution_forecasts'] = forecasts
            values['api_execution_options'] = [{'version': 'api_execution_option_v1', 'provider': 'hmmer',
                **{key: request[key] for key in ('subject_ref', 'algorithm', 'database', 'parameters')},
                'execution_class_ref': item['execution_class_ref'], 'proposal_ref': item['proposal_ref']}
                for item in forecasts if item['execution_class_ref'] is not None and item['proposal_ref'] is not None]
            values['api_timing_planning_disposition'] = disposition(
                'available' if capture['status'] == 'available' else 'unavailable',
                None if capture['status'] == 'available' else capture['code'])
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error):
            values['api_timing_planning_disposition'] = disposition('unavailable', 'timing_binding_unavailable')
        try:
            values['api_timing_export_recovery'] = self.timing.retry_exports()
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error):
            pass
        return values


__all__ = ['HmmerServiceResourceAdapter']
