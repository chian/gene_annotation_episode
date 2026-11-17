"""Root-owned episode_construction.py"""
from __future__ import annotations
from .episode_contract_information import ContractInformationError
from .task import AnnotationTask as DecisionSource
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeRequest
from .workflow_values import FeedbackEpisode
from .task_values import Record
from .episode_journal import WorkflowError
from .task_values import _json
from .task_values import _plain
from .reference_selection import _references_in
import inspect
from .communication import interpretation_schema
import json
from contextlib import nullcontext
from .communication import validate_form
from .episode_contract_information import validate_saved_fact_form

class EpisodeConstruction:

    def build(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None, root_binding_selection=None):
        arguments = dict(parent=parent, parent_path=parent_path, contract=contract, initial=initial,
            job_assignment=job_assignment, episode_assignment=episode_assignment,
            scientific_process=scientific_process, report_contract_declaration=report_contract_declaration)
        if not self.episode_bindings.private_owners:
            if root_binding_selection is not None:
                raise ValueError('root_binding_owner_not_registered')
            return self._build(name, key, goal_text, scope, **arguments)
        path = (*parent_path, (name, key))
        with self.binding_construction(path, scope, root_binding_selection) as selected:
            return self._build(name, key, goal_text, scope, root_binding_selection=selected, **arguments)

    def _build(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None, job_assignment=None, episode_assignment=None, scientific_process=None, report_contract_declaration=None, root_binding_selection=None):
        path = (*parent_path, (name, key))
        goal = EpisodeGoal.root(objective=goal_text, result_contract={'role': name}) if parent is None else EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema)
        message = {'scope': scope, 'initial_report': initial or {}}
        if root_binding_selection is not None:
            message['root_binding_selection'] = _plain(root_binding_selection)
        if self.inprocess_completion_order is not None:
            message['inprocess_completion_order'] = {'version': self.inprocess_completion_order}
        if report_contract_declaration is not None:
            if contract is None:
                raise ContractInformationError('report_contract_required_for_declaration')
            validate_saved_fact_form(child_role=name, submitted_schema_json=report_contract_declaration['submitted_schema_json'], expanded_schema=contract.schema, declaration=report_contract_declaration)
            message['report_contract_declaration'] = _plain(report_contract_declaration)
        if job_assignment is not None:
            message['job_assignment'] = job_assignment
        if episode_assignment is not None:
            self.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
            message['episode_assignment'] = _plain(episode_assignment)
        if scientific_process is not None:
            message['scientific_process'] = _plain(scientific_process)
        identity = Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
        if self.has_scientific_binding and name in {'annotation', 'scientific_process'}:
            from .scientific_process_records import scientific_invocation_ref
            message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
        if self.receipts is not None:
            parent_id = Episode.identity(self.context, self.grains[parent_path[-1][0]], parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None
            message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
        request = EpisodeRequest(goal, Record(message), contract)
        self._construction_request(path, request)
        source_type = self.task_source_for_path(path)
        source = source_type(self, path, request, scope)
        self.contract_information_profile(source)
        if name == 'scientific_process':
            restored = self.scientific_binding(source).restore_closed_process(self.binding_context(source))
            if restored is not None:
                message['scientific_process'] = restored
                request = EpisodeRequest(goal, Record(message), contract)
                self._construction_request(path, request)
                source = source_type(self, path, request, scope)
        row = self.journal.row('runtime_episodes', identity.episode_id)
        restore_active = getattr(self.scientific_binding(source), 'restore_saved_process', None)
        if name == 'scientific_process' and callable(restore_active) and (row is not None) and (row['state'] == 'active') and (row['completion'] is None) and (row['archive'] is None):
            restored = restore_active(self.binding_context(source), original_request=json.loads(row['request']))
            if restored is not None:
                message['scientific_process'] = restored
                request = EpisodeRequest(goal, Record(message), contract)
                self._construction_request(path, request)
                source = source_type(self, path, request, scope)
        if row is not None and json.loads(row['request']) != _plain(request.as_record()):
            raise WorkflowError('reconstructed immutable assignment differs')
        if name == 'scientific_process':
            self.scientific_binding(source).validate_context(self.binding_context(source))
        elif scientific_process is not None:
            raise ValueError('scientific_process_role_mismatch')
        specialist = self.specialist(source)
        initialize = getattr(specialist, 'initialize', None)
        if initialize is not None:
            initialize(self.binding_context(source))
        with self.store.transaction():
            if self.receipts is not None and (not parent_path):
                self.receipts.receive(identity.episode_id, [*scope['subject_refs'], *self.initial_known_record_refs], kind='initial')
            if self.receipts is not None and contract is not None and (not self.is_job_source(source)):
                initial_refs = _references_in({}, self.store.get, forms=[(message['initial_report'], interpretation_schema(contract.schema))], reference_subset=lambda refs: self.store.reference_subset(refs, scope))
                self.receipts.receive(identity.episode_id, initial_refs, kind='initial')
            if self.receipts is not None and (not self.is_job_source(source)):
                initial_refs = self.episode_bindings.initial_references(self.binding_context(source))
                self.receipts.receive(identity.episode_id, initial_refs, kind='initial')
            if row is None:
                self.journal.save('runtime_episodes', {'episode_id': identity.episode_id, 'path': _json(path), 'request': _json(request.as_record()), 'initial_credit': 0.0, 'state': 'active', 'completion': None, 'archive': None})
                self.receive_tool_attributions(source, None, kind='initial')
                from .episode_journal import encode_credit
                self.store.db.execute('UPDATE runtime_episodes SET initial_credit=? WHERE run_id=? AND episode_id=?', (encode_credit(self.source_credit_view(source)['credit']), self.run_id, identity.episode_id))
            if contract is not None and self.specialist(source) is not None:
                initial_schema = interpretation_schema(contract.schema)
                admitted = validate_form(message['initial_report'], initial_schema, self.resolver(scope, source=source))
                self.validate_report(admitted, scope, grain=name, schema=initial_schema, source=source)
        self.expose_assigned_job(source)

        def on_unit(item, contribution, view):
            if view.episode_update is not None and view.episode_update.delivery_failures:
                source.feedback = view.episode_update.delivery_failures[-1].as_record()
            data = {'label': view.unit_label, 'credit': _plain(view.controller_input), 'step': _plain(view.controller_step), 'unit_ref': view.unit_ref.as_record(), 'decision_index': item.decision_index}
            if self.execution_binding is not None:
                self.completions.confirm_observed(identity.episode_id, view.unit_ref.unit_index, data)
                slot = self.completions.slot(identity.episode_id, view.unit_ref.unit_index)
                if slot['child_return'] is not None:
                    returned = slot['child_return']
                    self.execution_backend.acknowledge(returned['handle'], returned['return_id'], returned['admission_id'])
                else:
                    action = self.journal.row('runtime_actions', identity.episode_id, item.decision_index)
                    outcome = json.loads(action['result'])
                    if json.loads(action['action']).get('kind') in {'job_child', 'episode_child'} and outcome.get('status') == 'failed' and outcome.get('execution_handle'):
                        spec = self.execution_backend.load_commission(outcome['execution_handle'])
                        self.execution_backend.acknowledge_failed_dispatch(outcome['execution_handle'], parent_episode_id=identity.episode_id, operation_key=spec['operation_key'], observation=data)
                self.publish_outcome(source, item.decision_index)
                return
            with self.store.transaction() if self.inprocess_replay is not None else nullcontext():
                old = self.journal.row('runtime_observations', identity.episode_id, view.unit_ref.unit_index)
                if old and json.loads(old['observation']) != data:
                    raise WorkflowError('reconstructed controller observation differs')
                if not old:
                    self.journal.save('runtime_observations', {'episode_id': identity.episode_id, 'unit_index': view.unit_ref.unit_index, 'observation': _json(data)})
                if self.inprocess_replay is not None:
                    self.inprocess_replay.capture(source)
                    source.checkpoint()

        def on_close(record):
            old = self.journal.row('runtime_episodes', identity.episode_id)
            if self.inprocess_replay is not None and old['state'] == 'yielded':
                if json.loads(old['completion']) != {'ended_by': record.ended_by, 'actions': record.units_consumed} or json.loads(old['archive']) != self.archive.store(record).descriptor():
                    raise WorkflowError('inprocess_closed_history_replay_differs')
                return
            if old['state'] == 'active':
                pending = self.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(action,'$.kind') IN ('job_child','episode_child') AND (result IS NULL OR json_extract(result,'$.status')='pending') LIMIT 1", (self.run_id, identity.episode_id)).fetchone()
                unobserved = self.store.db.execute('SELECT 1 FROM runtime_completion_slots s LEFT JOIN runtime_observations o ON o.run_id=s.run_id AND o.episode_id=s.episode_id AND o.unit_index=s.sequence WHERE s.run_id=? AND s.episode_id=? AND o.unit_index IS NULL LIMIT 1', (self.run_id, identity.episode_id)).fetchone()
                unobserved_action = self.store.db.execute("SELECT 1 FROM runtime_actions a WHERE a.run_id=? AND a.episode_id=? AND a.credit IS NOT NULL AND NOT EXISTS (SELECT 1 FROM runtime_observations o WHERE o.run_id=a.run_id AND o.episode_id=a.episode_id AND json_extract(o.observation,'$.decision_index')=a.decision_index) LIMIT 1", (self.run_id, identity.episode_id)).fetchone()
                if pending is not None or unobserved is not None or unobserved_action is not None:
                    raise WorkflowError('episode_cannot_close_with_unaccounted_owned_work')
            self.journal.save('runtime_episodes', {**{key: old[key] for key in ('episode_id', 'path', 'request', 'initial_credit')}, 'state': 'yielded', 'completion': _json({'ended_by': record.ended_by, 'actions': record.units_consumed}), 'archive': _json(self.archive.store(record).descriptor())})
        return FeedbackEpisode(self.grains[name], key, source, request, source.finish, on_unit=on_unit, on_close=on_close, archive_record=self.archive.store)

    async def release(self, episode_id):
        callback = getattr(self.provider, 'release', None)
        if callback:
            value = callback(episode_id)
            if inspect.isawaitable(value):
                await value
