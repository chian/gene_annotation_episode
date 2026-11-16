"""Selected AppService operations in the existing API episode executor.

This host connects actual episode custody, one selected service invocation and
immutable receipts. It does not select a next operation or calculate science.
"""
from __future__ import annotations

import json
from copy import deepcopy

from .api_selected_call import perform_selected_call
from .api_selected_effects import EffectConflict
from .api_services import event as native_event
from .library.bvbrc_appservice_contracts import download_request, validate_contract
from .bvbrc_appservice_custody import AppServiceCustody, _references
from .bvbrc_appservice_inputs import AppServiceInputs
from .bvbrc_appservice_records import AppServiceRecords, PROVIDER, provisional_receipt_ref
from .library.bvbrc_appservice_receipt_values import build_appservice_receipt, confirm_appservice_effects
from .communication import plain
from .domain import ContractError, identity
from .execution_contracts import canonical, digest, validate_target
from .practical_execution_state import _immutable, _read


SERVICE = 'bvbrc_appservice'
SUPPORT_SOURCE = 'bvbrc_appservice_support_refs'


def _common(record):
    return record['value'] if record['contract'] == 'CommonReceipt' else record['value']['receipt']


def _diagnostic(code, *, phase='publication', refs=()):
    return {'code': code, 'phase': phase, 'path': '', 'severity': 'error',
        'evidence_refs': list(refs)}


class BVBRCAppServiceHost:
    def __init__(self, execution):
        self.api, self.store, self.run_id = execution, execution.store, execution.run_id
        self.records = AppServiceRecords(execution)
        self.custody = AppServiceCustody(self.store, self.run_id,
            read_original_handoff=self.original_handoff)
        self.inputs = AppServiceInputs(execution, records=self.records, custody=self.custody,
            read_acquisition=self.read_acquisition)
        from .bvbrc_appservice_publication import AppServicePublications
        self.publications = AppServicePublications(self)

    def owns_context(self, context):
        assignment = plain(context.assignment)
        return ((context.role == 'launch_api' and assignment.get('service') == SERVICE)
            or (context.role == 'results' and assignment.get('selector', {}).get('version')
                == 'bvbrc_appservice_result_selector_v1'))

    def validate_assignment(self, context):
        self.custody.authenticate(context, allow_unsaved=True)
        self.custody.original_job_context(context)
        self.custody.initial_references(context)

    def initial_references(self, context):
        return self.custody.initial_references(context)

    def bind_inputs(self, context, name, arguments, *, operation_key):
        return self.inputs.bind_inputs(context, name, arguments, operation_key=operation_key)

    def read_handoff(self, reference, scope=None, *, require_completed=True):
        record = self.records.read(reference, require_completed=require_completed)
        if record['contract'] != 'TaskHandoff':
            raise ValueError('appservice_original_task_handoff_required')
        value, common = record['value'], record['value']['receipt']
        context = self.custody.context(common['origin']['episode_id'])
        if scope is not None:
            self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        original_context = self.custody.original_job_context(context)
        task = value['original_task']
        if (context.role != 'launch_api' or canonical(original_context) != canonical(value['original_job_owner'])
                or common['origin']['name'] != 'api.bvbrc_appservice.submit'
                or common['status'] != 'ok' or common['purpose'] != 'handoff'
                or task['submission_receipt_ref'] != reference
                or task['submission_operation_key'] != common['origin']['operation_key']
                or task['resource_id'] != context.assignment['resource_id']):
            raise ValueError('appservice_original_handoff_conflict')
        effect = self.api.selected_effects.read(value['effect_receipt_ref'], original_job_owner=original_context)
        if (effect['state'] != 'confirmed' or effect['descriptor']['kind'] != 'appservice_submit'
                or effect['operation_key'] != common['origin']['operation_key']
                or effect['confirmation_source_ref'] != task['submission_source_ref']
                or effect['native_effect_identifiers'].get('task_id') != task['task_id']):
            raise ValueError('appservice_original_submission_unconfirmed')
        directory = self.api._manifest(context, create=False) / 'actions' / digest(common['origin']['operation_key'])
        selected_event = self.api._event(_read(directory / 'event.json'))
        if (not selected_event['handoff_ready'] or selected_event['state'] != value['state']
                or selected_event['native_handle'] != {'task_id': task['task_id']}):
            raise ValueError('appservice_original_handoff_event_conflict')
        response = _read(directory / 'call_response.json')
        # This is a read-only compatibility projection, not another stored
        # receipt or an inference from the first mutation in the episode.
        return {'version': value['version'], 'run_id': self.run_id,
            'episode_id': context.episode_id, 'assignment': plain(context.assignment),
            'scope': plain(context.scope), 'event': selected_event, 'snapshot': response['snapshot'],
            'receipt': {**deepcopy(common['origin']), 'tool_name': common['origin']['name'],
                'state': value['state'], 'receipt_ref': reference},
            'task_handoff': value, 'origin_context': context}

    def original_handoff(self, reference):
        body = self.read_handoff(reference)
        return {'reference': reference, 'origin_context': body['origin_context'],
            'original_job_owner': body['task_handoff']['original_job_owner']}

    def read_target(self, reference, scope):
        body = self.read_handoff(reference, scope)
        return validate_target({'version': 'execution_target_v1', 'handle': reference,
            'run_id': self.run_id, 'resource_id': body['assignment']['resource_id'], 'resource_kind': 'api',
            'execution_id': body['task_handoff']['original_task']['task_id'],
            'request_sha256': digest(body['assignment']), 'origin_episode_id': body['episode_id'],
            'assignment': body['assignment'], 'scope': body['scope']})

    def _native_refs(self, directory, binding):
        refs = [] if binding is None else [binding['source_ref']]
        definition = directory / 'definition_inputs.json'
        if definition.exists():
            refs.extend(_read(definition)['source_refs'])
        return list(dict.fromkeys(refs))

    def _own_receipts(self, context):
        if not self.owns_context(context):
            return []
        # Workflow computes initial facts before persisting the child. The
        # custody helper still requires its exact saved parent model selection.
        self.custody.authenticate(context, allow_unsaved=True)
        rows = []
        for _, outcome in self.api._own_outcomes(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            result = outcome.get('result') or {}
            reference = result.get('handoff_ref') or result.get('support_receipt_ref')
            if reference is not None:
                rows.append(self.records.read(reference))
        return rows

    def facts(self, context):
        rows = self._own_receipts(context)
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        facts = {'execution_handoff_refs': [r['source_ref'] for r in rows if r['contract'] == 'TaskHandoff'],
            SUPPORT_SOURCE: [r['source_ref'] for r in rows if r['contract'] != 'TaskHandoff'],
            'execution_result_refs': self.publications.own_results(context), 'execution_blast_hsps': [],
            'execution_completed': self.completion(context) is not None}
        for returns in (self.api.homology_returns, self.api.phylogeny_returns,
                self.api.alignment_returns, self.api.genome_alignment_returns, self.api.proteome_returns,
                self.api.comparative_systems_returns, self.api.fastqutils_returns, self.api.application_returns):
            supplied = returns.facts(context, schema)
            if set(facts).intersection(supplied):
                raise ValueError('appservice_own_fact_source_conflict')
            facts.update(supplied)
        return facts

    def completion(self, context):
        if context.role == 'results':
            return self.publications.completion(context)
        if context.role != 'launch_api':
            return None
        for record in reversed(self._own_receipts(context)):
            if record['contract'] != 'TaskHandoff':
                continue
            common = record['value']['receipt']
            self.read_handoff(record['source_ref'], context.scope)
            return {'version': 'practical_completion_v1', 'run_id': self.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                'endpoint': 'usable_handoff', 'operation_key': common['origin']['operation_key'],
                'receipt_sha256': digest(common), 'validation_keys': ['usable_handoff']}
        return None

    def resolve(self, context, reference, namespace):
        try:
            provider = self.store.get(reference).get('provider')
        except (ValueError, KeyError, OSError, TypeError):
            # Other bindings can resolve identifiers that are not Store rows.
            return None
        if self.publications.is_provider(provider):
            try:
                if namespace == 'execution_result':
                    self.publications.read(reference, context.scope)
                elif namespace in {None, 'source'}:
                    self.publications.read_content_source(reference, context.scope)
                else:
                    return False
                self.custody.possession(context, reference)
                return True
            except (ValueError, ContractError, KeyError, OSError, TypeError):
                return False
        if provider != PROVIDER:
            return None
        try:
            if context.role == 'monitor' and namespace in {'execution_handle', 'execution'}:
                from .bvbrc_appservice_monitor import AppServiceMonitor
                return AppServiceMonitor(self.api).resolve_target(context, reference)
            record = self.records.read(reference)
            self.custody.possession(context, reference)
            if namespace == 'execution_handoff':
                return record['contract'] == 'TaskHandoff'
            if namespace == 'execution_result':
                return False
            return namespace in {None, 'source', 'bvbrc_appservice_support'}
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            return False

    def received_support_refs(self, context):
        self.custody.authenticate(context, allow_unsaved=True)
        rows = self.store.db.execute('SELECT decision_index FROM runtime_report_attempts '
            'WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL '
            'ORDER BY decision_index', (self.run_id, context.episode_id)).fetchall()
        result = []
        for row in rows:
            _, form, schema = self.custody._attempt(context, row['decision_index'])
            for reference, namespace in _references(form, schema):
                if namespace not in {None, 'source', 'bvbrc_appservice_support'}:
                    continue
                if self.store.get(reference).get('provider') != PROVIDER:
                    continue
                record = self.records.read(reference)
                self.custody.possession(context, reference)
                if record['contract'] != 'TaskHandoff' and reference not in result:
                    result.append(reference)
        return result

    def validate_received_report(self, context, form, schema):
        names = [name for name, node in plain(schema).get('properties', {}).items()
            if node.get('x-source') == SUPPORT_SOURCE]
        if names:
            expected = (self.facts(context)[SUPPORT_SOURCE] if self.owns_context(context)
                else self.received_support_refs(context))
            if any(canonical(form[name]) != canonical(expected) for name in names):
                raise ValueError('appservice_received_support_refs_conflict')

    def publish_acquisition(self, context, prepared, event, snapshot, *, common_receipt, operation_key):
        return self.publications.publish(context, prepared, event, snapshot,
            common_receipt=common_receipt, operation_key=operation_key)

    def read_acquisition(self, reference):
        record = self.records.read(reference)
        if record['contract'] != 'AcquisitionReceipt':
            raise ValueError('appservice_acquisition_receipt_required')
        return record['value']


__all__ = ['BVBRCAppServiceHost', 'SUPPORT_SOURCE']
