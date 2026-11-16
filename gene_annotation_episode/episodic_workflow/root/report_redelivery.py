"""Root-owned report_redelivery.py"""
from __future__ import annotations
from .receiving_context import BindingContext
from .episode_admission import ReceiverBindingV1
from .task_values import Record
from .workflow_values import ReportAcquisitionLeaf
from .communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportRedelivery
from .workflow_values import TypedReportContract
from .episode_journal import WorkflowError
from .task_values import _json
from .communication import form_with_facts
from .communication import interpretation_schema
import json
from .episode_admission import resolve_return_delivery

class ReportRedelivery:

    @staticmethod
    def delivery_feedback(delivery_ref, error):
        diagnostic = error.diagnostic
        feedback = {'kind': 'report_delivery_failure', 'delivery_ref': delivery_ref, 'reason': diagnostic['code'], 'field': diagnostic.get('field')}
        if diagnostic['code'] == 'literature_reaction_projection_version_mismatch':
            from .literature_reaction_storage import reaction_return_view_requirements
            feedback.update(reaction_return_view_requirements())
        return feedback

    def save_attempt(self, parent_id, index, delivery_ref, child_id, contract, *, form=None, failure=None, report_contract_declaration=None):
        values = {'parent_episode_id': parent_id, 'decision_index': index, 'delivery_ref': delivery_ref, 'child_episode_id': child_id, 'contract': _json(contract.as_record()), 'form': None if form is None else _json(form), 'failure': None if failure is None else _json(failure), 'report_contract_declaration': None if report_contract_declaration is None else _json(report_contract_declaration)}
        old = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, parent_id, index)).fetchone()
        if old is not None:
            if any((old[key] != value for key, value in values.items())):
                raise WorkflowError('reconstructed report delivery differs from its recorded attempt')
        else:
            self.journal.save('runtime_report_attempts', values)

    def delivery_status(self, parent_id):
        rows = self.store.db.execute('SELECT a.delivery_ref,a.failure,a.timing_receipts FROM runtime_report_attempts a WHERE a.run_id=? AND a.parent_episode_id=? AND a.decision_index=(SELECT MAX(b.decision_index) FROM runtime_report_attempts b WHERE b.run_id=a.run_id AND b.delivery_ref=a.delivery_ref) ORDER BY a.decision_index', (self.run_id, parent_id)).fetchall()
        return [{'delivery_ref': row['delivery_ref'], 'status': 'pending' if row['failure'] else 'delivered', **({'timing_receipt_issues': json.loads(row['timing_receipts'])['issues']} if row['timing_receipts'] is not None and json.loads(row['timing_receipts'])['issues'] else {})} for row in rows]

    def saved_delivery_contract(self, child_id, saved):
        child = self.journal.row('runtime_episodes', child_id)
        request, path = (json.loads(child['request']), json.loads(child['path']))
        scope, role = (request['message']['scope'], path[-1][0])
        assignment = request['message'].get('job_assignment')
        context = BindingContext(self.run_id, child_id, role, path, scope, request['message'].get('episode_assignment', {}), request)
        schema = saved['measurements']['schema']
        contract = TypedReportContract(saved['decision'], schema, self.resolver(scope, assignment=assignment, grain=role, context=context), lambda value: self.validate_report(value, scope, assignment=assignment, grain=role, schema=schema, context=context))
        if contract.as_record() != saved:
            raise WorkflowError('recorded_delivery_contract_changed')
        return contract

    def redeliver(self, source, selection, index):
        prior = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND delivery_ref=? ORDER BY decision_index LIMIT 1', (self.run_id, source.episode_id, selection['delivery_ref'])).fetchone()
        if prior is None:
            raise ValueError('unknown_report_delivery_for_parent')
        child_id = prior['child_episode_id']
        child_row = self.journal.row('runtime_episodes', child_id)
        request = json.loads(child_row['request'])
        scope = request['message']['scope']
        role = json.loads(child_row['path'])[-1][0]
        assignment = request['message'].get('job_assignment')
        binding_context = BindingContext(self.run_id, child_id, role, json.loads(child_row['path']), scope, request['message'].get('episode_assignment', {}), request)
        schema, declaration = self.expanded_contract_form(source, selection, index, role, original_child=False)
        validator = lambda value: self.validate_report(value, scope, assignment=assignment, grain=role, schema=schema, context=binding_context)
        contract = TypedReportContract(selection['purpose'], schema, self.resolver(scope, assignment=assignment, grain=role, context=binding_context), validator)
        saved = self.journal.row('runtime_forms', child_id)
        facts = json.loads(saved['facts'])
        old_interpretations = facts.pop('interpretations')
        original_schema = request['report_contract']['measurements']['schema']
        original_fields = interpretation_schema(original_schema)['properties']
        try:
            requested = interpretation_schema(schema)['properties']
            for name, node in requested.items():
                if name not in old_interpretations or node != original_fields.get(name):
                    raise ReportBoundaryError('Saved child interpretation does not answer the revised field', code='recorded_interpretation_unavailable', field=name)
            values = {name: old_interpretations[name] for name in requested}
            candidate = form_with_facts(values, schema, facts)
            admitted = contract.admit(candidate, audit_identifiers=(child_id, request['goal']['goal_id']))
        except ReportBoundaryError as error:
            feedback = self.delivery_feedback(selection['delivery_ref'], error)
            self.save_attempt(source.episode_id, index, selection['delivery_ref'], child_id, contract, failure=feedback, report_contract_declaration=declaration)
            return ReportRedelivery(child_id, failure=Record(feedback))
        self.save_attempt(source.episode_id, index, selection['delivery_ref'], child_id, contract, form=admitted.as_record(), report_contract_declaration=declaration)
        pending = self.pending_delivery(source, selection['delivery_ref'])
        if pending is not None and self.execution_binding is not None:
            original_index = pending['decision_index']
            row = self.store.db.execute('SELECT admission FROM runtime_return_admissions WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?', (self.run_id, source.episode_id, original_index)).fetchone()
            if row is None:
                raise WorkflowError('pending_delivery_missing_original_admission')
            original = json.loads(row[0])
            spec = self.execution_backend.load_commission(original['handle'])
            returned = self.execution_backend.load_return(original['handle'], original['return_id'])
            original_request = self.returned_request(spec)
            receiver = ReceiverBindingV1(self.store, self.journal, original_index, original_request.report_contract, lambda form: None, lambda form: self.receive_form(source, form, schema, index, redelivery=True), lambda: self.source_credit_view(source)['credit'], lambda original_index, credit: self.controller_value(source, original_index, credit), defer_failed_delivery=True)
            resolve_return_delivery(spec, returned, receiver, repair_decision_index=index, delivery_contract=contract)
            action = self.journal.row('runtime_actions', source.episode_id, original_index)
            source.last_outcome, source.last_outcome_index = (json.loads(action['result']), original_index)
            source.feedback = None
        elif pending is not None:
            self.receive_form(source, admitted.as_record(), schema, index, redelivery=True)
        else:
            from .episode_report_acquisition import acquire_report_evidence
            controller_input = acquire_report_evidence(self, source, selection, index, original_attempt=prior, admitted=admitted, schema=schema)
            if controller_input is not None:
                return ReportAcquisitionLeaf(selection, extract=lambda _: controller_input, result=lambda _, value: value, label=f'redeliver_report:{index}', decision_index=index, report_delivery=ReportRedelivery(child_id, report=admitted))
        return ReportRedelivery(child_id, report=admitted)
