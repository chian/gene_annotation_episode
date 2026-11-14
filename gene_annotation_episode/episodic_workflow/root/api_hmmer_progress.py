"""Original HMMER operational credit, report and completion proof predicates."""
from __future__ import annotations
import json
import math
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.practical_execution_records import validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.api_hmmer_protocol import PROVIDER, VERSION


class HMMERAPIProgress:
    def _own_results(self, context):
        return [json.loads(row['result']) for row in self.store.db.execute('SELECT result FROM api_execution_actions '
            'WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY rowid',
            (self.run_id, context.episode_id))]

    def facts(self, context, completion_snapshot):
        self.initialize(context)
        handoffs, results = [], []
        for outcome in self._own_results(context):
            if outcome['status'] not in {'completed', 'partial'}:
                continue
            for reference in outcome['record_refs']:
                record = self.store.get(reference)
                if record.get('provider') == PROVIDER:
                    self.read_target(reference, context.scope)
                    handoffs.append(reference)
                elif context.role == 'results':
                    results.append(reference)
        return {'execution_handoff_refs': list(dict.fromkeys(handoffs)),
            'execution_result_refs': list(dict.fromkeys(results)),
            'execution_completed': self._completion(context) is not None}

    def credit_view(self, context, receiver_selection):
        facts = self.facts(context, {})
        selection = plain(receiver_selection)
        if not {'known_record_refs', 'initial_known_record_refs'} <= set(selection):
            raise ValueError('api_credit_requires_received_record_selection')
        known, initial = set(selection['known_record_refs']), set(selection['initial_known_record_refs'])
        if not initial <= known:
            raise ValueError('api_credit_initial_references_must_be_known')
        def handoff_identity(reference):
            target = self.read_target(reference, context.scope)
            return target['resource_id'], target['execution_id']
        inherited, inherited_records = set(), set()
        for reference in initial:
            try:
                inherited.add(handoff_identity(reference))
            except (ValueError, ContractError, KeyError):
                pass
            try:
                inherited_records.add(self.result_identity(reference, context.scope))
            except (ValueError, ContractError, KeyError):
                pass
        acquired_records = {self.result_identity(reference, context.scope) for reference in
            set(facts['execution_result_refs']) & known}
        acquired = len(acquired_records-inherited_records)
        handoffs = {handoff_identity(reference) for reference in set(facts['execution_handoff_refs']) & known}
        count = len(handoffs-inherited)
        credit = self.handoff_unit*count + self.acquired_record_unit*acquired
        if not math.isfinite(credit):
            raise ValueError('finite_operational_credit_required')
        return {'credit': credit, 'operational_credit': credit, 'new_handoff_count': count,
            'new_acquired_record_count': acquired, 'operational_credit_binding': {
                'version': VERSION, 'handoff_unit': self.handoff_unit,
                'acquired_record_unit': self.acquired_record_unit,
                'qualification': 'received_qualified_original_api_handoffs_and_own_canonical_result_records',
                'scientific_credit': False, 'monitoring_credit': False}}

    def decision_context(self, context, current_view=None):
        self.initialize(context)
        if context.role == 'results':
            return {'api_execution_assignment': plain(context.assignment),
                'api_execution_target': self.read_target(context.assignment['handoff_ref'], context.scope),
                'api_execution_completion': self._completion(context)}
        prepared = self.store.db.execute('SELECT request FROM api_execution_preparations WHERE run_id=? '
            'AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        try:
            job = self.tools.remote_searches.describe(self._job(context.episode_id)['id'])
        except ValueError:
            job = None
        return {'api_execution_assignment': plain(context.assignment),
            'api_execution_prepared_request': json.loads(prepared['request']) if prepared else None,
            'api_execution_job': job, 'api_execution_completion': self._completion(context)}

    def resolve(self, context, reference, namespace):
        if context.run_id != self.run_id:
            return False
        if namespace not in {None, 'source', 'execution_handoff', 'execution_result'}:
            return False
        try:
            if namespace != 'execution_result':
                self.read_target(reference, context.scope)
                return True
        except (ValueError, ContractError, KeyError, OSError, TypeError):
            pass
        if namespace in {None, 'source', 'execution_result'}:
            try:
                self.read_result(reference, context.scope)
                return namespace != 'source' or self.store.get(reference).get('record_type') == 'source'
            except (ValueError, ContractError, KeyError, OSError, TypeError):
                return False
        return False

    def validate_report(self, context, form, schema):
        validate_form(form, schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in schema.get('properties', {}).items():
            if node.get('x-source') in facts and form[name] != facts[node['x-source']]:
                raise ValueError('api_report_disagrees_with_recorded_facts')

    def _completion(self, context):
        if context.run_id != self.run_id:
            raise ValueError('api_completion_run_identity_conflict')
        if context.role == 'results':
            return self._results_completion(context)
        if context.role != 'launch_api':
            return None
        for outcome in reversed(self._own_results(context)):
            receipt = (outcome.get('result') or {}).get('receipt')
            if outcome['status'] == 'completed' and receipt is not None:
                reference = outcome['result']['handoff_ref']
                self.read_target(reference, context.scope)
                return {'version': 'practical_completion_v1', 'run_id': self.run_id,
                    'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment),
                    'endpoint': 'usable_handoff', 'operation_key': receipt['operation_key'],
                    'receipt_sha256': digest(receipt), 'validation_keys': ['usable_handoff']}
        return None

    def _results_completion(self, context):
        assignment = plain(context.assignment)
        if assignment.get('version') != 'execution_results_assignment_v1':
            return None
        target = self.read_target(assignment['handoff_ref'], context.scope)
        for row in self.store.db.execute("SELECT * FROM api_execution_actions WHERE run_id=? AND episode_id=? "
                "AND name='api.hmmer.result' AND result IS NOT NULL ORDER BY rowid DESC",
                (self.run_id, context.episode_id)):
            outcome = json.loads(row['result'])
            if outcome['status'] != 'completed':
                continue
            receipt = (outcome.get('result') or {}).get('acquisition_receipt')
            if receipt is None:
                continue
            if (receipt['version'] != 'api_result_acquisition_receipt_v1'
                    or receipt['run_id'] != self.run_id or receipt['episode_id'] != context.episode_id
                    or receipt['tool_name'] != 'api.hmmer.result' or receipt['arguments'] != {}
                    or receipt['validation_keys'] != ['requested_result_page']
                    or receipt['assignment_sha256'] != digest(assignment)
                    or receipt['selector'] != assignment['selector']
                    or receipt['selector_sha256'] != digest(assignment['selector'])
                    or receipt['handoff_ref'] != target['handle']
                    or receipt['operation_key'] != row['operation_key']
                    or receipt['record_refs'] != outcome['record_refs']
                    or receipt['source_ref'] != outcome['result']['source_ref']):
                raise ValueError('api_result_completion_identity_conflict')
            selected = self._selected(context, row['name'], json.loads(row['arguments']), row['operation_key'])
            if selected['result'] is not None:
                actual = json.loads(selected['result'])
                if (actual.get('status') != 'completed' or actual.get('record_refs') != outcome['record_refs']
                        or canonical(actual.get('result')) != canonical(outcome.get('result'))):
                    raise ValueError('api_result_completion_runtime_outcome_conflict')
            original = self._load_snapshot(row['snapshot'])
            if original.sha256 != receipt['snapshot_sha256']:
                raise ValueError('api_result_completion_source_conflict')
            source = self.store.get(receipt['source_ref'])
            request = self._artifact_json(source['request_ref'])['request']
            selector = assignment['selector']
            if (self.store.get_artifact(source['artifact_ref']) != original.content
                    or request['job_id'] != target['execution_id']
                    or request['page'] != selector['page']
                    or request['page_size'] != selector.get('page_size', target['assignment']['page_size'])):
                raise ValueError('api_result_completion_requested_page_conflict')
            return {'version': 'practical_completion_v1', 'run_id': self.run_id,
                'episode_id': context.episode_id, 'assignment_sha256': digest(assignment),
                'endpoint': 'usable_handoff', 'operation_key': row['operation_key'],
                'receipt_sha256': digest(receipt), 'validation_keys': ['requested_result_page']}
        return None

    def completion_for_action(self, context, key):
        proof = self._completion(context)
        return proof if proof is not None and proof['operation_key'] == key else None

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
            actual = self._completion(context)
            return actual is not None and proof == actual
        except (ValueError, ContractError, TypeError, KeyError, OSError):
            return False
