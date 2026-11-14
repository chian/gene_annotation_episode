"""Original API facts, operational credit and authenticated completion interfaces.

Scientific interpretations still belong to their original provider return owners.
"""
from __future__ import annotations

import math

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .practical_execution_records import validate_completion_proof
from .api_service_operations import PROVIDER


VERSION = 'api_service_execution_v1'


class APIExecutionProgress:
    def facts(self, context, completion_snapshot):
        if self._legacy_context(context):
            return {**self._legacy_binding().facts(context, completion_snapshot), 'execution_blast_hsps': []}
        self.initialize(context)
        if self.appservice.owns_context(context):
            return self.appservice.facts(context)
        handoffs, results = [], []
        for _, outcome in self._own_outcomes(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            for reference in outcome['record_refs']:
                if self.store.get(reference).get('provider') == PROVIDER:
                    self.read_target(reference, context.scope)
                    handoffs.append(reference)
                elif context.role == 'results':
                    self.read_result(reference, context.scope)
                    results.append(reference)
        from gene_annotation_episode.episodic_workflow.root.library.blast_result_views import blast_hsp_facts
        fields = (context.request.get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {})
        requested_hsps = any(field.get('x-source') == 'execution_blast_hsps' for field in fields.values())
        hsp_facts = blast_hsp_facts(self.store, results) if context.role == 'results' and requested_hsps else []
        bvbrc_facts = self.bvbrc_data.facts(context,
            (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}))
        minhash_facts = self.minhash.facts(context,
            (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}))
        rfam_schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        rfam_facts = (self.rfam_returns.facts(context, rfam_schema)
            if any(service.service == 'rfam_batch' for service in self.services.values()) else {})
        uniprot_facts = (self.uniprot_returns.facts(context, rfam_schema)
            if any(service.service == 'uniprot' for service in self.services.values()) else {})
        enrichr_facts = (self.enrichr_returns.facts(context, rfam_schema)
            if any(service.service == 'enrichr' for service in self.services.values()) else {})
        addgene_facts = {}
        if any(service.service == 'sequence_support' for service in self.services.values()):
            closing = completion_snapshot is not None and completion_snapshot.get('completion') is not None
            addgene_facts = (self.addgene_returns.facts_for_closure(context, rfam_schema) if closing else
                self.addgene_returns.facts(context, rfam_schema))
        return {'execution_handoff_refs': sorted(set(handoffs)), 'execution_result_refs': sorted(set(results)),
            **bvbrc_facts, **minhash_facts, **rfam_facts, **uniprot_facts, **enrichr_facts, **addgene_facts,
            'execution_blast_hsps': hsp_facts,
            'execution_completed': self._completion(context) is not None}

    def credit_view(self, context, receiver_selection):
        if self._legacy_context(context):
            return self._legacy_binding().credit_view(context, receiver_selection)
        facts = self.facts(context, {})
        selection = plain(receiver_selection)
        known, initial = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        if not initial <= known:
            raise ValueError('api_initial_references_must_be_known')
        old_handoffs, old_results = set(), set()
        for reference in initial:
            try:
                target = self.read_target(reference, context.scope)
                old_handoffs.add((target['resource_id'], target['execution_id']))
            except (ValueError, ContractError, KeyError, OSError):
                pass
            try:
                old_results.add(self.result_identity(reference, context.scope))
            except (ValueError, ContractError, KeyError, OSError):
                pass
        handoffs = set()
        for reference in set(facts['execution_handoff_refs']) & known:
            target = self.read_target(reference, context.scope)
            handoffs.add((target['resource_id'], target['execution_id']))
        results = {self.result_identity(ref, context.scope) for ref in set(facts['execution_result_refs']) & known}
        new_handoffs, new_results = len(handoffs-old_handoffs), len(results-old_results)
        value = self.handoff_unit*new_handoffs+self.acquired_record_unit*new_results
        if not math.isfinite(value):
            raise ValueError('finite_operational_credit_required')
        return {'credit': value, 'operational_credit': value, 'new_handoff_count': new_handoffs,
            'new_acquired_record_count': new_results, 'operational_credit_binding': {
                'version': VERSION, 'handoff_unit': self.handoff_unit,
                'acquired_record_unit': self.acquired_record_unit, 'scientific_credit': False,
                'monitoring_credit': False}}

    def _completion(self, context):
        if self.appservice.owns_context(context):
            return self.appservice.completion(context)
        for directory, outcome in reversed(list(self._own_outcomes(context))):
            if outcome['status'] != 'completed':
                continue
            if context.role == 'launch_api':
                receipt = (outcome.get('result') or {}).get('receipt')
                if receipt is None:
                    continue
                self.read_target(outcome['result']['handoff_ref'], context.scope)
                keys = ['usable_handoff']
            else:
                receipt = (outcome.get('result') or {}).get('acquisition_receipt')
                if receipt is None or not outcome['record_refs']:
                    continue
                acquired = self.read_result(outcome['record_refs'][0], context.scope)
                if acquired['target']['assignment'].get('service') == 'rfam_batch':
                    qualified = self.rfam_returns.read(outcome['record_refs'][0], context.scope,
                                                       episode_id=context.episode_id)
                    if context.assignment['selector']['projection'] is not None and qualified['projection'] is None:
                        continue
                from .bvbrc_data_host import is_bvbrc_request
                if is_bvbrc_request(acquired.get('service_request')):
                    from gene_annotation_episode.episodic_workflow.root.library.bvbrc_data_publication import requested_projection_failures
                    qualified = self.read_bvbrc_result(acquired['source_ref'], context=context)
                    failures = requested_projection_failures(qualified['grading'], input_results=qualified['input_results'])
                    if failures:
                        continue
                keys = ['requested_service_result']
            return {'version': 'practical_completion_v1', 'run_id': self.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'],
                'receipt_sha256': digest(receipt), 'validation_keys': keys}
        return None

    def completion_for_action(self, context, operation_key):
        if self._legacy_context(context):
            return self._legacy_binding().completion_for_action(context, operation_key)
        proof = self._completion(context)
        return proof if proof is not None and proof['operation_key'] == operation_key else None

    def verify_completion(self, context, proof):
        if self._legacy_context(context):
            return self._legacy_binding().verify_completion(context, proof)
        try:
            proof = validate_completion_proof(plain(proof))
            return proof == self._completion(context)
        except (ValueError, ContractError, KeyError, TypeError, OSError):
            return False

    def decision_context(self, context, current_view=None):
        if self._legacy_context(context):
            return self._legacy_binding().decision_context(context, current_view)
        self.initialize(context)
        assignment, service, target = self._context(context)
        latest = {}
        for row in self._events(context.episode_id):
            latest[row['name']] = {'state': row['event']['state'],
                'kind': row['event']['kind'], 'facts': row['event']['facts'],
                'failure_code': row['event']['failure_code']}
        return {'api_service': service.service,
            'api_request': assignment['request'],
            'api_received_progress': latest,
            'api_execution_completed': self._completion(context) is not None}

