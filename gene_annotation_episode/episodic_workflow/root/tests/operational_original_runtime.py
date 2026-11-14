"""Root-owned action_execution.py"""
from __future__ import annotations

__package__ = 'gene_annotation_episode.episodic_workflow.root'
from .task_action_units import ActionLeaf
from .composition_information import CONTRACT_INFORMATION_OPERATIONS
from gene_annotation_episode.domain import ContractError
from jsonschema import Draft202012Validator
from .workflow_values import EPISODE_BRANCH_LIFECYCLE
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from .task_values import Record
from .communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportDeliveryError
from .workflow_values import TimedChildUnit
from .workflow_values import TypedReportContract
from jsonschema import ValidationError
from .episode_journal import WorkflowError
from .task_values import _digest
from .task_values import _json
from .composition_information import metadata_catalog as composition_catalog
import inspect
from .communication import interpretation_schema
import json
from gene_annotation_episode.tool_knowledge import catalog as knowledge_catalog
from gene_annotation_episode.launch_instructions import catalog as launch_instruction_catalog
from contextlib import nullcontext
from .boundary_validation import parse_json_object
from .native_timing_information import read_measurement
from .composition_information import restricted_root
from .communication import validate_form


class OriginalActionExecution:

    def selected(self, source, selection, index):
        if selection['kind'] in {'child', 'job_child', 'episode_child'}:
            if source.path[-1][0] == 'scientific_process':
                saved = self.journal.row('runtime_actions', source.episode_id, index)
                if saved is None or saved['result'] is None:
                    self.scientific_binding(source).validate_execution_context(self.binding_context(source))
            old = self.journal.row('runtime_actions', source.episode_id, index) if self.annotation_child_roles is not None else None
            original = old is not None and json.loads(old['action']) == selection
            self.validate_child_choice(source, selection.get('role', 'improvement'), selection=selection, original=original)
        common_action = 'child' if selection['kind'] in {'child', 'job_child', 'episode_child'} else selection['kind']
        resolving = selection['kind'] == 'redeliver_report' and selection.get('delivery_ref') == source._delivery_resolution_ref and (self.pending_delivery(source, selection.get('delivery_ref')) is not None)
        if not resolving and (not self.permits_common_action(source, common_action)):
            raise ValueError('action_not_available_to_episode')
        if restricted_root(self, source) and selection['kind'] == 'tool':
            recorded = self.journal.row('runtime_actions', source.episode_id, index)
            replay = recorded is not None and recorded['result'] is not None and (json.loads(recorded['action']) == selection)
            if not replay and selection.get('tool') not in {item['name'] for item in self.catalog(source.scope, source=source)}:
                raise ValueError('action_not_available_to_episode')
        closed = self._closed_child_commission(source, selection, index)
        if closed is not None:
            return closed
        if self.execution_binding is None and selection['kind'] in {'child', 'job_child', 'episode_child'}:
            original = self.journal.row('runtime_actions', source.episode_id, index)
            if original is not None and original['result'] is not None:
                outcome = json.loads(original['result'])
                if outcome.get('status') == 'failed' and outcome.get('feedback', {}).get('category') == 'child_execution':
                    if json.loads(original['action']) != selection or original['credit'] is None:
                        raise WorkflowError('original_child_failure_replay_conflict')

                    def failed_result(_):
                        source.last_outcome, source.last_outcome_index = (outcome, index)
                        source.feedback = outcome['feedback']
                        return self.controller_value(source, index, original['credit'])
                    return ActionLeaf(selection, extract=failed_result, result=lambda _, result: result, label=f'child_{index}', decision_index=index)
        if selection['kind'] == 'wait':
            original = self.journal.row('runtime_actions', source.episode_id, index)
            recorded = original is not None and json.loads(original['action']) == selection
            if not recorded:
                self.validate_wait_selection(source, selection['condition'])
        if selection['kind'] == 'child' and self.has_scientific_binding:
            raise ValueError('scientific_child_requires_filled_process')
        if selection['kind'] == 'redeliver_report':
            return self.redeliver(source, selection, index)
        if selection['kind'] not in {'child', 'job_child', 'episode_child'}:
            if self.execution_binding is not None or self.inprocess_replay is not None:
                old = self.journal.row('runtime_actions', source.episode_id, index)
                if old is not None and json.loads(old['action']) != selection:
                    raise WorkflowError('reconstructed selected work changed')
                if old is None:
                    self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': None, 'credit': None})
            return ActionLeaf(selection, extract=lambda action: source.execute(action, index), result=lambda action, result: result, label=f"{selection['kind']}:{index}", decision_index=index)
        if self.execution_binding is not None:
            old = self.journal.row('runtime_actions', source.episode_id, index)
            if old is not None:
                if json.loads(old['action']) != selection:
                    raise WorkflowError('reconstructed selected work changed')
                result = json.loads(old['result']) if old['result'] is not None else {}
                handle = result.get('pending_handle')
                if handle is not None:
                    original = next((spec for spec in self.commissions.recover_selected(source.episode_id) if spec['handle'] == handle), None)
                    if original is None:
                        raise WorkflowError('pending_commission_intent_unavailable')
                    return self.deferred_unit(source, index, original)
        scope = self.store.validate_scope(selection['scope'], parent_scope=source.scope)
        role = selection.get('role', 'improvement')
        episode_assignment = None
        scientific_process = None
        root_binding_selection = self.binding_selection_for_child(source, role, selection, index) if selection['kind'] == 'episode_child' else None
        selected_owner = None if root_binding_selection is None else root_binding_selection['binding']['owner']
        schema, report_declaration = self.expanded_contract_form(source, selection, index, role, owner=selected_owner)
        if selection['kind'] == 'episode_child':
            binding = self.episode_bindings.for_child(source.path, role, owner=selected_owner)
            required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(self.binding_context(source), role)
            sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
            for fact_source in required:
                if sources.count(fact_source) != 1:
                    raise ContractError('child_return_requires_' + fact_source)
        hpc_launch = role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'} or (role == 'launch_hpc' and any((part[0] == 'hpc' for part in source.path)))
        if hpc_launch and (not any((node.get('x-source') == 'execution_handoff_refs' for node in schema.get('properties', {}).values()))):
            raise ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
        initial = parse_json_object(self.child_initial_report_input(source, selection, role))
        if selection['kind'] == 'episode_child':
            validate_form(initial, interpretation_schema(schema), lambda *_: True)
        else:
            validate_form(initial, interpretation_schema(schema), self.resolver(scope, grain=role))
            self.validate_report(initial, scope, grain=role, schema=interpretation_schema(schema))
        if selection['kind'] == 'episode_child':
            specialist = self.specialist(source)
            allowed = self.available_child_roles(source) if self.annotation_child_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
            if role not in allowed:
                raise ValueError('child_role_not_available_to_parent')
            binding = self.episode_bindings.for_child(source.path, role, owner=selected_owner)
            self.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
            if binding is (self.episode_bindings.for_role('scientific_process', owner=selected_owner) if 'scientific_process' in self.episode_bindings.roles else None):
                closed = {}
                recorded = self.journal.row('runtime_actions', source.episode_id, index)
                if recorded is not None and recorded['result'] is not None and (_json(json.loads(recorded['action'])) == _json(selection)) and (json.loads(recorded['result']).get('status') == 'completed'):
                    from .episode_return_records import EpisodeReturnRecords
                    child_id = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path).episode_id
                    if self.journal.row('runtime_episodes', child_id) is not None:
                        records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='scientific_closed_')
                        candidate = records.context(child_id)
                        read_closed = getattr(self.services, 'scientific_closed_request', None)
                        if callable(read_closed) and read_closed(candidate) is not None:
                            closed['closed_context'] = candidate
                prepared = binding.prepare_invocation(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}', invocation={'objective': selection['goal'], 'purpose': selection['purpose'], 'report_schema': schema, 'initial_report': initial}, **closed)
                episode_assignment = prepared['assignment']
                scientific_process = prepared['scientific_process']
            else:
                episode_assignment = binding.prepare_assignment(self.binding_context(source), role, selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}')
        assignment = self.job_episodes.assign(self.store, role, selection, scope, operation_key=f'{self.run_id}:{source.episode_id}:{index}') if selection['kind'] == 'job_child' else None
        contract_binding = {}

        def validator(value):
            self.validate_report(value, scope, assignment=assignment, grain=role, schema=schema, context=contract_binding['context'])

        def resolve(reference, namespace=None):
            return contract_binding['resolver'](reference, namespace)

        def recorded_admission(value):
            if self.receipts is None or self.is_job_source(source):
                return None
            from .episode_return_records import EpisodeReturnRecords
            return EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_admission_').recorded_admission_references(self.binding_context(source), value, schema, index)
        contract = TypedReportContract(selection['purpose'], schema, resolve, validator, recorded_admission=recorded_admission)
        with self.store.transaction():
            old = self.journal.row('runtime_actions', source.episode_id, index)
            if old is None:
                self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': None, 'credit': None})
            elif json.loads(old['action']) != selection:
                raise WorkflowError('reconstructed selected work changed')
            child = self.build(role, f'child_{index}', selection['goal'], scope, parent=source.request.goal, parent_path=source.path, contract=contract, initial=initial, job_assignment=assignment, episode_assignment=episode_assignment, scientific_process=scientific_process, root_binding_selection=root_binding_selection, **{'report_contract_declaration': report_declaration} if report_declaration is not None else {})
            contract_binding['context'] = self.binding_context(child.source)
            contract_binding['resolver'] = self.resolver(scope, assignment=assignment, grain=role, context=contract_binding['context'])
            allow_suspension = self.permits_common_action(child.source, 'wait')
            if self.execution_binding is not None:
                return self.commission_child(source, child, selection, index)

        def admitted_report(result, request):
            delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
            owned = self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
            action = self.journal.row('runtime_actions', source.episode_id, index)
            frozen_index = None if action['result'] is None else json.loads(action['result']).get('delivery_resolution_index')
            saved = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
            if saved is not None:
                if saved['failure'] is not None:
                    raise ReportDeliveryError(Record(json.loads(saved['failure'])))
                admitted = json.loads(saved['form'])
            else:
                try:
                    admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
                except ReportBoundaryError as error:
                    feedback = self.delivery_feedback(delivery_ref, error)
                    self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
                    raise ReportDeliveryError(Record(feedback)) from error
                self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
            delivery_index = index if saved is None else saved['decision_index']
            delivery_schema = schema if saved is None else json.loads(saved['contract'])['measurements']['schema']
            references = self.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
            return (admitted, references)

        def credit(result, completion, request):
            old = self.journal.row('runtime_actions', source.episode_id, index)
            if old['result'] is None:
                facts = self.facts(child.source)
                if self.receipts is not None or self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE:
                    _, returned = admitted_report(result, request)
                    changed = set(facts['changed_record_refs'])
                    facts = {'committed_record_refs': returned, 'changed_record_refs': [ref for ref in returned if ref in changed]}
                outcome = {'status': 'completed', 'record_refs': facts['committed_record_refs'], 'changed_record_refs': facts['changed_record_refs']}
                original_delivery = self.store.db.execute('SELECT MAX(decision_index) FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND delivery_ref=?', (self.run_id, source.episode_id, 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24])).fetchone()[0]
                outcome['delivery_resolution_index'] = original_delivery
                from .episode_source_failure import child_completion_status
                outcome['child_completion'] = child_completion_status(self.store, self.run_id, child.source.episode_id, completion.as_record(), delivery='admitted')
                if self.wait_inputs_version == 'wait_inputs_binding_v2' or self.completed_action_inputs_version is not None:
                    outcome['pending_work_after_action'] = self.pending_work(source)
                self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': None})
                old = self.journal.row('runtime_actions', source.episode_id, index)
            value = old['credit']
            if value is None:
                value = self.source_credit_view(source)['credit']
                self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': old['action'], 'result': old['result'], 'credit': value})
            source.last_outcome, source.last_outcome_index = (json.loads(old['result']), index)
            source.checkpoint()
            return self.controller_value(source, index, value)

        async def report(result, completion, request):
            if self.receipts is not None or self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE:
                try:
                    return admitted_report(result, request)[0]
                except ReportDeliveryError as error:
                    source.feedback = error.feedback.as_record()
                    await self.resolve_pending_deliveries(source, source._selection_view, only_delivery_ref=source.feedback['delivery_ref'])
                    return admitted_report(result, request)[0]
            delivery_ref = 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
            try:
                admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
            except ReportBoundaryError as error:
                feedback = self.delivery_feedback(delivery_ref, error)
                self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
                raise ReportDeliveryError(Record(feedback)) from error
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
            self.receive_form(source, admitted, schema, index)
            return admitted
        scheduled = 'delay_seconds' in selection
        if scheduled:
            self.journal.schedule_child(source.episode_id, index, selection, child.source.episode_id)

        async def resolved_credit(result, completion, request):
            try:
                admitted_report(result, request)
            except ReportDeliveryError as error:
                source.feedback = error.feedback.as_record()
                await self.resolve_pending_deliveries(source, source._selection_view, only_delivery_ref=source.feedback['delivery_ref'])
                admitted_report(result, request)
            value = credit(result, completion, request)
            original = self.journal.row('runtime_actions', source.episode_id, index)
            resolved_index = json.loads(original['result']).get('delivery_resolution_index')
            if resolved_index is not None:
                source.calls = max(source.calls, resolved_index + 1)
            return value

        def delivery_contract():
            action = self.journal.row('runtime_actions', source.episode_id, index)
            resolved_index = None if action['result'] is None else json.loads(action['result']).get('delivery_resolution_index')
            latest = self.store.db.execute('SELECT contract FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if resolved_index is not None else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (self.run_id, source.episode_id, resolved_index if resolved_index is not None else 'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24])).fetchone()
            return contract if latest is None else self.saved_delivery_contract(child.source.episode_id, json.loads(latest['contract']))
        owned = self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE

        def failed_child(error):
            outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'category': 'child_execution', 'exception_type': type(error).__name__}}
            from .communication import ReportBoundaryError
            if isinstance(error, ReportBoundaryError):
                outcome['feedback']['report_boundary'] = dict(error.diagnostic)
            self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': None})
            value = self.source_credit_view(source)['credit']
            self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': value})
            source.last_outcome, source.last_outcome_index = (outcome, index)
            source.feedback = outcome['feedback']
            return self.controller_value(source, index, value)
        return TimedChildUnit(child, resolved_credit if owned else credit, report, self.journal, source.episode_id, index, scheduled=scheduled, delivery_contract=delivery_contract if owned else None, receive_failure=failed_child, allow_suspension=allow_suspension)


def original_admit_return(workflow, source, child, index, schema, contract, result, request):
    delivery_ref = 'delivery_' + _digest({'run': workflow.run_id, 'parent': source.episode_id, 'index': index})[:24]
    owned = workflow.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
    action = workflow.journal.row('runtime_actions', source.episode_id, index)
    frozen_index = None if action['result'] is None else json.loads(action['result']).get('delivery_resolution_index')
    saved = workflow.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND ' + ('decision_index=?' if frozen_index is not None or not owned else 'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'), (workflow.run_id, source.episode_id, frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
    if saved is not None:
        if saved['failure'] is not None:
            raise ReportDeliveryError(Record(json.loads(saved['failure'])))
        admitted = json.loads(saved['form'])
    else:
        try:
            admitted = contract.admit(result.as_record()['form'], audit_identifiers=(child.source.episode_id, request.goal.goal_id)).as_record()
        except ReportBoundaryError as error:
            feedback = workflow.delivery_feedback(delivery_ref, error)
            workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, failure=feedback)
            raise ReportDeliveryError(Record(feedback)) from error
        workflow.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id, contract, form=admitted)
    delivery_index = index if saved is None else saved['decision_index']
    delivery_schema = schema if saved is None else json.loads(saved['contract'])['measurements']['schema']
    references = workflow.receive_form(source, admitted, delivery_schema, delivery_index, redelivery=delivery_index != index)
    return (admitted, references)

