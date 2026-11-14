"""Root-owned child_delivery.py"""
from __future__ import annotations
from .task_action_units import ActionLeaf
from gene_annotation_episode.episodic_workflow.root.method_loop.archive import ArchivedRecord
from .receiving_context import BindingContext
from .workflow_values import EPISODE_BRANCH_LIFECYCLE
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeRecord
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeRequest
from collections.abc import Mapping
from pathlib import Path
from .episode_admission import ReceiverBindingV1
from .task_values import Record
from .workflow_values import ReportAcquisitionLeaf
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportDeliveryError
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportRedelivery
from .workflow_values import ReturnedActionUnit
from .workflow_values import TypedReportContract
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import UnitRef
from .episode_journal import WorkflowError
from .task_action_contracts import _decode_recorded_action_response
from .task_values import _json
from .task_action_contracts import _object
from .task_values import _plain
from .episode_admission import admit_return
import json
from .episode_admission import load_return_admission
from contextlib import nullcontext
from .boundary_validation import parse_json_object
from .communication import validate_form
from .episode_contract_information import validate_saved_fact_form

class ChildDelivery:

    def pending_delivery(self, source, delivery_ref=None):
        if self.episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE:
            return None
        rows = self.store.db.execute("SELECT a.* FROM runtime_report_attempts a JOIN runtime_actions work ON work.run_id=a.run_id AND work.episode_id=a.parent_episode_id AND work.decision_index=a.decision_index WHERE a.run_id=? AND a.parent_episode_id=? AND a.failure IS NOT NULL AND (work.result IS NULL OR json_extract(work.result,'$.status')='pending') ORDER BY a.decision_index", (self.run_id, source.episode_id)).fetchall()
        for original in rows:
            if delivery_ref is None or original['delivery_ref'] == delivery_ref:
                return original
        return None

    def delivery_resolution_inputs(self, source, delivery_ref, context):
        original = self.pending_delivery(source, delivery_ref)
        if original is None:
            raise WorkflowError('delivery_resolution_requires_owned_unfinished_child')
        latest = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND delivery_ref=? ORDER BY decision_index DESC LIMIT 1', (self.run_id, source.episode_id, delivery_ref)).fetchone()
        pending = {'delivery_ref': delivery_ref, 'original_decision_index': original['decision_index'], 'original_contract': json.loads(original['contract']), 'latest_contract': json.loads(latest['contract']), 'failure': None if latest['failure'] is None else json.loads(latest['failure'])}
        schema = _object({'selection': {'anyOf': [_object({'kind': {'type': 'string', 'const': 'redeliver_report'}, 'delivery_ref': {'type': 'string', 'const': delivery_ref}, 'purpose': {'type': 'string'}, 'schema_json': {'type': 'string'}})]}, 'report_update': source.interpret_schema})
        return ({**context, 'pending_child_delivery': pending, 'tools': [], 'job_episode_options': []}, schema)

    async def resolve_pending_deliveries(self, source, view, *, only_delivery_ref=None):
        original = self.pending_delivery(source, only_delivery_ref)
        if original is None:
            return
        delivery_ref = original['delivery_ref']
        source._delivery_resolution_ref = delivery_ref
        try:
            while True:
                result = await source.next(view, delivery_ref=delivery_ref)
                if not isinstance(result, ReportRedelivery):
                    raise WorkflowError('delivery_resolution_requires_report_operation')
                latest = self.store.db.execute('SELECT failure FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND delivery_ref=? ORDER BY decision_index DESC LIMIT 1', (self.run_id, source.episode_id, delivery_ref)).fetchone()
                if latest is not None and latest['failure'] is None:
                    return
        finally:
            source._delivery_resolution_ref = None

    async def next_branch_return(self, source, view):
        """Complete existing owned work while selection is numerically yielded.

        Keep the same active parent and receipt boundary. Durable notifications
        release execution until a return exists; they are not episode actions.
        This does not recreate an exited parent process or reopen closed history.
        """
        while True:
            with self.execution_backend._connect() as events:
                cursor = events.execute('SELECT coalesce(max(cursor),0) FROM events').fetchone()[0]
            slot = self.completions.slot(source.episode_id, view.units_consumed)
            if slot is not None:
                return self.completed_unit(source, slot)
            source.restore_checkpoint()
            slot = self.next_return(source)
            if slot is not None:
                return self.completed_unit(source, slot)
            await self.resolve_pending_deliveries(source, view)
            slot = self.completions.slot(source.episode_id, view.units_consumed)
            if slot is not None:
                return self.completed_unit(source, slot)
            pending = self.commissions.pending(source.episode_id)['items']
            if not pending:
                return None
            conditions = [item.get('suspension') for item in pending]
            state = source._execution_context._suspension
            state.update({'kind': 'owned_child_return', 'handles': [item['handle'] for item in pending]} if all((condition is not None for condition in conditions)) else None)
            try:
                await self.execution_backend.wait_events({'version': 'event_condition_v1', 'events': [{'handle': item['handle'], 'event': event, 'after_cursor': cursor} for item in pending for event in ('returned', 'state_changed')], 'reconsider_at': None})
            finally:
                state.update(None)

    def returned_request(self, spec):
        child, recorded = (spec['child'], spec['child']['request'])
        message, scope = (recorded['message'], child['scope'])
        role, schema = (child['role'], recorded['report_contract']['measurements']['schema'])
        declaration = message.get('report_contract_declaration')
        if declaration is not None:
            validate_saved_fact_form(child_role=role, submitted_schema_json=declaration['submitted_schema_json'], expanded_schema=schema, declaration=declaration)
        assignment = message.get('job_assignment')
        context = BindingContext(spec['run_id'], child['episode_id'], role, child['path'], scope, message.get('episode_assignment', {}), recorded)

        def validate(value):
            self.validate_report(value, scope, assignment=assignment, grain=role, schema=schema, context=context)
        contract = TypedReportContract(recorded['report_contract']['decision'], schema, self.resolver(scope, assignment=assignment, grain=role, context=context), validate)
        if contract.as_record() != recorded['report_contract']:
            raise WorkflowError('original_return_contract_changed')
        return EpisodeRequest(EpisodeGoal.from_record(recorded['goal']), Record(message), contract)

    def next_return(self, source, *, only_handle=None):
        self.settle_unclaimed_child_failures(source)
        for pending in self.commissions.pending(source.episode_id)['items']:
            self.execution_backend.supervise_receiver(pending['handle'])
        cursor = 0
        while True:
            page = self.execution_backend.return_page(source.episode_id, cursor, 16)
            for item in page['items']:
                if only_handle is not None and item['handle'] != only_handle:
                    continue
                status = self.execution_backend.status(item['handle'])
                if status['acknowledgment_id'] is not None:
                    continue
                spec = self.execution_backend.load_commission(item['handle'])
                action = self.store.db.execute("SELECT decision_index FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(result,'$.pending_handle')=?", (self.run_id, source.episode_id, item['handle'])).fetchone()
                if action is None:
                    installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_return_admissions'").fetchone()
                    saved = self.store.db.execute('SELECT admission FROM runtime_return_admissions WHERE run_id=? AND return_id=?', (self.run_id, item['return_id'])).fetchone() if installed else None
                    if saved is None:
                        raise WorkflowError('return_has_no_original_pending_action')
                    admission = load_return_admission(self.store, self.run_id, item['return_id'])
                    observed = self.store.db.execute("SELECT 1 FROM runtime_observations WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?", (self.run_id, source.episode_id, admission['original_decision_index'])).fetchone()
                    if observed is not None or admission['state'] == 'receiver_closed':
                        self.execution_backend.acknowledge(item['handle'], item['return_id'], admission['admission_id'])
                    continue
                index = action[0]
                request = self.returned_request(spec)
                returned = self.execution_backend.load_return(item['handle'], item['return_id'])
                receiver = ReceiverBindingV1(self.store, self.journal, index, request.report_contract, lambda form: None, lambda form: self.receive_form(source, form, request.report_contract.schema, index), lambda: self.source_credit_view(source)['credit'], lambda original_index, credit: self.controller_value(source, original_index, credit), defer_failed_delivery=self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE)
                slot = None
                with self.store.transaction():
                    parent_open = self.journal.row('runtime_episodes', source.episode_id)['state'] == 'active'
                    with self.journal.measure('runtime_actions', source.episode_id, index) if parent_open else nullcontext():
                        admission = admit_return(spec, returned, receiver)
                    if admission['controller_input'] is not None:
                        original_action = self.journal.row('runtime_actions', source.episode_id, index)
                        outcome = json.loads(original_action['result'])
                        outcome['pending_work_after_action'] = self.pending_work(source)
                        self.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index, 'action': original_action['action'], 'credit': original_action['credit'], 'result': _json(outcome)})
                        slot = self.completions.stage(source.episode_id, index, label=spec['child']['key'], kind='child_return', controller_input=Record(admission['controller_input']), child_return={'handle': item['handle'], 'return_id': item['return_id'], 'admission_id': admission['admission_id']})
                    if admission['state'] == 'delivery_pending':
                        source.feedback = admission['delivery_failure']
                        source.checkpoint()
                    elif admission['state'] != 'receiver_closed':
                        recorded = self.journal.row('runtime_actions', source.episode_id, index)
                        source.last_outcome, source.last_outcome_index = (json.loads(recorded['result']), index)
                        if source.last_outcome.get('feedback') is not None:
                            source.feedback = source.last_outcome['feedback']
                        source.checkpoint()
                if admission['state'] == 'receiver_closed':
                    self.execution_backend.acknowledge(item['handle'], item['return_id'], admission['admission_id'])
                if admission['state'] == 'receiver_closed':
                    continue
                if slot is not None:
                    return slot
                source.feedback = admission['delivery_failure']
            if not page['items']:
                return None
            cursor = page['next_cursor']

    def archive_reference(self, descriptor):
        return ArchivedRecord(self.archive.path / descriptor['file'], descriptor['sha256'], descriptor['index_sha256'])

    def publish_outcome(self, source, index):
        if self.execution_handle is None or self.progress_provider is None:
            return
        row = self.journal.row('runtime_actions', source.episode_id, index)
        result = json.loads(row['result'])
        dependency = getattr(self.progress_provider.job_provider, 'dependency_from_outcome', None)
        if dependency is not None and result.get('status') in {'completed', 'partial'}:
            key = f'{self.run_id}:{source.episode_id}:{index}'
            relationship = dependency(self.binding_context(source), result, operation_key=key)
            if relationship is not None:
                self.progress_provider.expose(self.execution_handle, operation_key=key + ':physical_target', dependencies=[relationship])
        references = result.get('record_refs', [])
        if references:
            self.progress_provider.expose(self.execution_handle, operation_key=f'{self.run_id}:{source.episode_id}:{index}:committed_outcome', committed_record_refs=references)
        self.progress_provider.flush_notifications()

    def expose_assigned_job(self, source):
        if self.execution_handle is None or self.progress_provider is None:
            return
        provider = self.progress_provider.job_provider
        dependency = getattr(provider, 'dependency', None)
        if dependency is None:
            return
        spec = self.execution_backend.load_commission(self.execution_handle)
        if spec['child']['episode_id'] != source.episode_id:
            return
        operation_key = spec['operation_key'] + ':assigned_job'
        with self.store.transaction():
            relationship = dependency(spec, operation_key=operation_key)
            if relationship is not None:
                self.progress_provider.expose(self.execution_handle, operation_key=operation_key, dependencies=[relationship])
        if not self.store.db.in_transaction:
            self.progress_provider.flush_notifications()

    def completed_unit(self, source, slot):
        index = slot['original_decision_index']
        action = self.journal.row('runtime_actions', source.episode_id, index)
        source.last_outcome, source.last_outcome_index = (json.loads(action['result']), index)
        if slot['kind'] == 'own_action':
            if json.loads(action['action']).get('kind') == 'redeliver_report':
                attempt = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                contract = self.saved_delivery_contract(attempt['child_episode_id'], json.loads(attempt['contract']))
                report = contract.admit(json.loads(attempt['form']), audit_identifiers=())
                return ReportAcquisitionLeaf(slot, extract=lambda value: Record(value['controller_input']), result=lambda _, value: value, label=slot['label'], decision_index=index, report_delivery=ReportRedelivery(attempt['child_episode_id'], report=report))
            return ActionLeaf(slot, extract=lambda value: Record(value['controller_input']), result=lambda _, value: value, label=slot['label'], decision_index=index)
        reference = slot['child_return']
        spec = self.execution_backend.load_commission(reference['handle'])
        returned = self.execution_backend.load_return(reference['handle'], reference['return_id'])
        admission = load_return_admission(self.store, self.run_id, reference['return_id'])
        if admission['state'] == 'execution_failed':
            source.feedback = admission['delivery_failure']
            return ActionLeaf(slot, extract=lambda value: Record(value['controller_input']), result=lambda _, value: value, label=slot['label'], decision_index=index)
        request = self.returned_request(spec)
        child, completion = (spec['child'], returned['completion'])
        record = EpisodeRecord(child['role'], child['key'], completion['units_consumed'], completion['ended_by'], (), None, request, path=tuple((tuple(part) for part in child['path'])), end_reason=completion['end_reason'], episode_ref=EpisodeRef(self.run_id, child['path']), archived_record=self.archive_reference(returned['episode_archive']))
        result = Record(self.archive_reference(returned['result_archive']).load())

        def report(*_):
            if admission['report'] is None:
                failure = self.store.db.execute('SELECT failure FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                raise ReportDeliveryError(Record(json.loads(failure[0])))
            return admission['report']
        delivery_contract = request.report_contract if 'delivery_contract' not in admission else self.saved_delivery_contract(child['episode_id'], admission['delivery_contract'])
        return ReturnedActionUnit(slot['label'], record, result, request, lambda *_: Record(slot['controller_input']), report, decision_index=index, delivery_contract=lambda: delivery_contract)

    def _closed_child_commission(self, source, selection, index):
        """Replay one wholly closed in-process commission from its real archives.

        This is not admission for another child. The original action, observed
        input, successful return and both closed records must agree before any
        assignment preparation, initialization or receipt delivery is skipped.
        """
        if self.execution_binding is not None or self.receipts is None or self.native_timing_information is not None or (selection.get('kind') != 'episode_child'):
            return None

        def require(condition, code):
            if not condition:
                raise WorkflowError('closed_commission_' + code)

        def same(left, right):
            return _json(left) == _json(right)

        def archived(row):
            descriptor = json.loads(row['archive'])
            require(type(descriptor) is dict and set(descriptor) == {'file', 'sha256', 'index_sha256'} and (type(descriptor['file']) is str) and (Path(descriptor['file']).name == descriptor['file']) and descriptor['file'].endswith('.json') and all((type(descriptor[key]) is str and len(descriptor[key]) == 64 and all((char in '0123456789abcdef' for char in descriptor[key])) for key in ('sha256', 'index_sha256'))), 'archive_invalid')
            reference = self.archive_reference(descriptor)
            try:
                value = reference.load()
            except (OSError, ValueError) as error:
                raise WorkflowError('closed_commission_archive_invalid') from error
            completion = json.loads(row['completion'])
            path = json.loads(row['path'])
            request = json.loads(row['request'])
            episode_ref = EpisodeRef(self.run_id, path)
            require(type(completion) is dict and set(completion) == {'ended_by', 'actions'} and (type(completion['actions']) is int) and (completion['actions'] >= 0) and (type(value) is dict) and (type(value.get('units')) is list) and (type(value.get('units_consumed')) is int) and (value['units_consumed'] == len(value['units']) == completion['actions']) and (value.get('ended_by') == completion['ended_by']) and same(value.get('request'), request) and same(value.get('goal'), request['goal']) and same(value.get('path'), path) and same(value.get('episode_ref'), episode_ref.as_record()) and (value.get('episode_id') == episode_ref.episode_id == row['episode_id']) and (value.get('run_id') == self.run_id == row['run_id']) and (value.get('scope_level') == path[-1][0]) and (value.get('scope_key') == path[-1][1]), 'archive_conflict')
            return (reference, value)
        with self.store.read_snapshot():
            parent = self.journal.row('runtime_episodes', source.episode_id)
            if parent is None or parent['state'] != 'yielded' or parent['completion'] is None or (parent['archive'] is None):
                return None
            require(type(index) is int and index >= 0, 'action_index_invalid')
            action = self.journal.row('runtime_actions', source.episode_id, index)
            require(action is not None, 'original_action_required')
            require(same(json.loads(action['action']), selection), 'selection_conflict')
            if action['result'] is None:
                return None
            outcome = json.loads(action['result'])
            if type(outcome) is not dict or outcome.get('status') != 'completed':
                return None
            call = self.journal.row('runtime_model_calls', source.episode_id, index)
            require(call is not None and call['purpose'] == 'decision' and (call['response'] is not None), 'original_call_required')
            try:
                original_call = json.loads(call['request'])
                response = _decode_recorded_action_response(json.loads(call['response']), original_call['schema'], recorded_selection=selection)
            except (ValueError, KeyError, TypeError) as error:
                raise WorkflowError('closed_commission_call_conflict') from error
            require(same(response.get('selection'), selection), 'call_conflict')
            role = selection['role']
            require(role in self.grains and role in self.episode_bindings.roles, 'role_conflict')
            identity = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path)
            child_row = self.journal.row('runtime_episodes', identity.episode_id)
            require(child_row is not None, 'original_child_required')
            if child_row['state'] != 'yielded' or child_row['completion'] is None or child_row['archive'] is None:
                return None
            specialist = self.specialist(source)
            allowed = self.available_child_roles(source) if self.annotation_child_roles is not None else specialist.allowed_children(self.binding_context(source), self.services.capabilities()) if specialist is not None else self.episode_bindings.entry_roles
            require(role in allowed, 'role_not_available')
            scope = self.store.validate_scope(selection['scope'], parent_scope=source.scope)
            from .episode_return_records import EpisodeReturnRecords
            records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='closed_commission_')
            context = self.binding_context(source)
            records.authenticate(context)
            attempt = self.store.db.execute('SELECT failure FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
            if attempt is not None and attempt['failure'] is not None:
                return None
            child, form, schema = records._attempt(context, index)
            require(child.episode_id == identity.episode_id and child.role == role and same(child.scope, scope), 'child_identity_conflict')
            assignment = _plain(child.assignment)
            if role == 'scientific_process':
                from .scientific_process_records import selector_selection
                binding = self.scientific_process_binding
                require(binding is not None and binding.restore_closed_process(child) is not None, 'scientific_request_conflict')
                binding.validate_context(child)
                selected_assignment = {**assignment, 'selection': selector_selection(assignment['selection'])}
                require(same(selection['assignment'], assignment) or same(selection['assignment'], selected_assignment), 'assignment_conflict')
            compiled, declaration = self.expanded_contract_form(source, selection, index, role)
            request_value = _plain(child.request)
            require(same(compiled, schema) and same(request_value['message'].get('report_contract_declaration'), declaration) and same(request_value['message'].get('initial_report'), parse_json_object(self.child_initial_report_input(source, selection, role))) and (request_value['report_contract']['decision'] == selection['purpose']) and same(EpisodeGoal.child(source.request.goal, objective=selection['goal'], result_contract=schema).as_record(), request_value['goal']), 'request_conflict')
            for current in (context, child):
                require(same(current.request['message'].get('knowledge_inheritance'), self.receipts.manifest(current.episode_id)), 'inheritance_conflict')
            references = records.recorded_admission_references(context, form, schema, index)
            if references is None:
                return None
            projected, unsupported = ([], [])

            def reference_projection(reference, namespace):
                if namespace == 'hpc_model' and child.role in {'hpc', 'hpc_prediction', 'hpc_execution'}:
                    owner = self.episode_bindings.for_path(child.path)
                    return owner.frozen_reference(child, reference, namespace)
                if namespace == 'restriction_enzyme' and child.role == 'scientific_process':
                    from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_references import RestrictionMappingReferences
                    return RestrictionMappingReferences(self.store, self.run_id).frozen_reference(child, reference, namespace)
                if isinstance(namespace, str) and namespace.startswith('native_hmmer_preparation_'):
                    from .native_hmmer_preparation_returns import IDENTIFIER_NAMESPACES
                    if namespace in IDENTIFIER_NAMESPACES:
                        owner = self.episode_bindings.for_role('results') if 'results' in self.episode_bindings.roles else None
                        reader = getattr(owner, 'native_hmmer_preparation_returns', None)
                        return False if reader is None else reader.frozen_reference(child, reference, namespace)
                if namespace == 'bvbrc_minhash_genome':
                    owner = self.episode_bindings.for_role('results') if 'results' in self.episode_bindings.roles else None
                    execution = getattr(owner, 'api_execution', None)
                    reader = getattr(execution, 'minhash', None)
                    return False if reader is None else reader.frozen_reference(child, reference, namespace)
                from gene_annotation_episode.domain import RECORD_SCHEMAS
                if reference not in references:
                    return False
                record = self.store.get(reference)
                if not isinstance(record, Mapping) or record.get('id') != reference or (not isinstance(record.get('record_type'), str)):
                    return False
                kind = record['record_type']
                scoped = reference in self.store.reference_subset([reference], scope)
                if not scoped and kind == 'artifact' and (namespace == 'artifact') and (child.role == 'results'):
                    owner = self.episode_bindings.for_role('results') if 'results' in self.episode_bindings.roles else None
                    execution = getattr(owner, 'api_execution', None)
                    reader = getattr(execution, 'addgene_returns', None)
                    scoped = reader is not None and reader.resolve_own(child, reference, namespace) is True
                if not scoped:
                    return False
                execution_alias = {'execution_result': {'source', 'artifact'}, 'execution_handoff': {'source'}}.get(namespace)
                if namespace in RECORD_SCHEMAS and namespace != kind or (execution_alias is not None and kind not in execution_alias) or (namespace == 'subject' and kind not in {'input', 'feature', 'product', 'read_subject'}):
                    return False
                if kind == 'collection_member' or (namespace not in {None, 'record', kind} and execution_alias is None and (not (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'}))):
                    unsupported.append(reference)
                projected.append(reference)
                return True
            try:
                validate_form(form, schema, reference_projection)
            except (ValueError, KeyError, TypeError) as error:
                raise WorkflowError('closed_commission_reference_projection_conflict') from error
            if unsupported:
                return None
            receiver_evidence = None
            if set(references) != set(projected):
                require(set(projected) <= set(references), 'reference_projection_conflict')
                saved = self.store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                receiver_evidence = json.loads(saved['data']).get('current_completion_evidence') if saved is not None else None
                require(isinstance(receiver_evidence, dict) and receiver_evidence.get('run_id') == self.run_id and (receiver_evidence.get('episode_id') == source.episode_id) and (receiver_evidence.get('original_decision_index') == index) and (receiver_evidence.get('action_kind') == 'episode_child') and (type(receiver_evidence.get('received_record_refs')) is list) and (set(receiver_evidence['received_record_refs']) == set(references)), 'receiver_attribution_evidence_conflict')
                for reference in set(references) - set(projected):
                    record = self.store.get(reference)
                    require(record.get('origin') == 'tool' and reference_projection(reference, record['record_type']), 'receiver_attribution_reference_conflict')
            require(set(references) == set(projected), 'reference_projection_conflict')
            require(type(outcome.get('changed_record_refs')) is list and set(outcome['changed_record_refs']) <= set(references), 'changed_references_conflict')
            frozen = self.journal.row('runtime_forms', child.episode_id)
            require(frozen is not None and same(json.loads(frozen['form']), form), 'frozen_form_conflict')
            _, parent_archive = archived(parent)
            child_reference, child_archive = archived(child_row)
            observed = list(self.store.db.execute("SELECT unit_index,observation FROM runtime_observations WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?", (self.run_id, source.episode_id, index)))
            require(len(observed) == 1, 'original_observation_required')
            sequence = observed[0]['unit_index']
            require(type(sequence) is int and 0 <= sequence < len(parent_archive['units']), 'observation_index_conflict')
            unit = parent_archive['units'][sequence]
            unit_ref = UnitRef(EpisodeRef(self.run_id, source.path).episode_id, sequence)
            require(receiver_evidence is None or same(receiver_evidence.get('unit_ref'), unit_ref.as_record()), 'receiver_attribution_unit_conflict')
            require(same(unit.get('unit_ref'), unit_ref.as_record()) and unit.get('unit_id') == unit_ref.unit_id and (unit.get('unit_label') == f'child_{index}') and same(unit.get('child'), child_archive) and same(unit.get('child_result'), {'form': form}) and same(json.loads(observed[0]['observation']), {'label': unit['unit_label'], 'credit': unit['controller_input'], 'step': unit['controller_step'], 'unit_ref': unit['unit_ref'], 'decision_index': index}), 'observation_conflict')
            controller_input = unit['controller_input']
            from .episode_journal import decode_credit
            from .numerical import validate_task_credit
            require(type(controller_input) is dict, 'credit_conflict')
            validate_task_credit(controller_input.get('credit'))
            require(controller_input['credit'] == decode_credit(action['credit']) and type(controller_input.get('estimation_action_index', index)) is int and (controller_input.get('estimation_action_index', index) == index), 'credit_conflict')
            expected_update = dict(record_id=child.episode_id, goal=request_value['goal'], completion={key: child_archive[key] for key in ('ended_by', 'end_reason', 'units_consumed')}, controller_input=controller_input, report=form, report_contract=request_value['report_contract'], delivery_failures=[])
            require(same(unit.get('episode_update'), expected_update), 'delivered_report_conflict')

            def admitted(value):
                require(same(value, form), 'form_conflict')
                return references
            contract = TypedReportContract(selection['purpose'], schema, lambda *_: False, recorded_admission=admitted)
            require(same(contract.as_record(), request_value['report_contract']), 'contract_conflict')
            request = EpisodeRequest(EpisodeGoal.from_record(request_value['goal']), Record(request_value['message']), contract)
            record = EpisodeRecord(role, f'child_{index}', child_archive['units_consumed'], child_archive['ended_by'], (), child_archive['controller_state'], request, path=child.path, end_reason=child_archive['end_reason'], episode_ref=EpisodeRef(self.run_id, child.path), archived_record=child_reference)
            source.last_outcome, source.last_outcome_index = (outcome, index)
            return ReturnedActionUnit(unit['unit_label'], record, Record({'form': form}), request, lambda *_: Record(controller_input), lambda *_: form, decision_index=index)
