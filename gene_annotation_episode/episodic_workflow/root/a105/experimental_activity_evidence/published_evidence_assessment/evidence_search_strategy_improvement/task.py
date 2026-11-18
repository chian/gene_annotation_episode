from __future__ import annotations
'Private task responsibility for literature_strategy.'
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_contracts import Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _population_catalog, deepcopy, identity, inspect, plain, source_location_inputs
from gene_annotation_episode.domain import ContractError

class LiteratureOperations:

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'reason', 'child', 'redeliver_report')

    def catalog(self, context):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = [{'name': name, **entry} for name, entry in available.items()] if isinstance(available, Mapping) else list(available)
        allowed = set(_ACCESS_TOOLS)
        allowed.update(_ACQUISITION_TOOLS)
        result = []
        for entry in entries:
            if entry['name'] not in allowed:
                continue
            entry = deepcopy(plain(entry))
            if entry['name'] == 'public.ncbi.search':
                entry['input_schema']['properties']['database'] = {'enum': ['pubmed']}
            if entry['name'] == 'execution.estimate':
                branches = [branch for branch in entry['input_schema'].get('anyOf', ()) if branch.get('properties', {}).get('tool', {}).get('const') in {'source.xlsx.sheets', 'source.xlsx.rows'}]
                if not branches:
                    continue
                entry['input_schema'] = {'anyOf': branches}
            result.append(entry)
        if self.rate_population:
            populations = _population_catalog(assay_grading_population=self._enabled('assay_grading_population', context), ratio_source_population=self.ratio_source_population, controlled_response_population=self.controlled_response_population, gel_population=self.gel_population, completion_time_population=self.completion_time_population, active_site_population=self.active_site_population, parent_depletion_population=self.parent_depletion_population, stoichiometric_balance_population=self.stoichiometric_balance_population, product_partition_population=self.product_partition_population, compiled_assay_population=self.compiled_assay_population, channel_population=self.channel_population, ion_discrimination_population=self.ion_discrimination_population)
            if self._contract_information_profile is not None:
                from gene_annotation_episode.episodic_workflow.root.a105.composition_information import CONTRACT_ARGUMENT_TRANSPORT
                populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
            result.extend(populations)
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        if tool_name in {'literature.concentration_window.populate', 'literature.measurement_comparison.populate', 'literature.product_coupling.populate', 'literature.measurement_validation.populate', 'literature.ion_discrimination.populate', 'literature.channel.populate', 'literature.assay.components.populate', 'literature.calibration.recovery.populate', 'literature.rate.observations.populate', 'literature.rate.replicates.populate', 'literature.rate.populate', 'literature.rate.source.populate', 'literature.quantity.populate', 'literature.assay.populate', 'literature.ratio.populate', 'literature.ratio.source.populate', 'literature.binding.populate', 'literature.binding.model.populate', 'literature.transport.response.populate', 'literature.figure.populate', 'literature.amount.populate', 'literature.completion_time.populate', 'literature.active_site.populate', 'literature.product_partition.populate', 'literature.optical.populate', 'literature.kinetic.populate', 'literature.kinetic.model.populate', 'literature.binding.interaction.populate', 'literature.binding.interaction.model.populate', 'literature.controlled_response.source_v3.populate', 'literature.gel.populate', 'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate', 'literature.assay_grading.populate', 'literature.a105.aggregate'}:
            from gene_annotation_episode.episodic_workflow.root.a105.literature_contract_error import ExperimentalContractError
            try:
                if tool_name == 'literature.figure.populate' and arguments.get('version') == 'literature_figure_endpoint_signal_population_v1':
                    repo = self._endpoint_signal_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo, operation_key), operation_key)
                if tool_name == 'literature.kinetic.populate' and arguments.get('version') == 'literature_kinetic_summary_precision_population_v1':
                    repo = self._summary_precision_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo, operation_key), operation_key)
                repo = {'literature.concentration_window.populate': self._concentration_window_repository, 'literature.measurement_comparison.populate': self._measurement_comparison_repository, 'literature.product_coupling.populate': self._product_coupling_repository, 'literature.measurement_validation.populate': self._measurement_validation_repository, 'literature.ion_discrimination.populate': self._ion_discrimination_repository, 'literature.channel.populate': self._channel_repository, 'literature.assay.components.populate': self._compiled_assay_repository, 'literature.rate.populate': self.literature_rate_repository, 'literature.calibration.recovery.populate': self.literature_calibration_recovery_repository, 'literature.rate.observations.populate': self.literature_rate_observation_repository, 'literature.rate.replicates.populate': self.literature_rate_replicate_repository, 'literature.rate.source.populate': self.literature_rate_repository, 'literature.quantity.populate': self.literature_quantity_repository, 'literature.assay.populate': self.literature_assay_repository, 'literature.amount.populate': self.literature_amount_repository, 'literature.completion_time.populate': self._completion_time_repository, 'literature.active_site.populate': self._active_site_repository, 'literature.parent_depletion.populate': self._parent_depletion_repository, 'literature.stoichiometric_balance.populate': self._stoichiometric_balance_repository, 'literature.assay_grading.populate': self._assay_grading_repository, 'literature.a105.aggregate': self._a105_aggregation_repository, 'literature.product_partition.populate': self._product_partition_repository, 'literature.optical.populate': self.literature_optical_repository, 'literature.kinetic.populate': self.literature_kinetic_repository, 'literature.kinetic.model.populate': self._kinetic_model_repository, 'literature.binding.interaction.populate': self.literature_binding_interaction_repository, 'literature.binding.interaction.model.populate': self._binding_interaction_model_repository, 'literature.ratio.populate': self.literature_ratio_repository, 'literature.ratio.source.populate': self._ratio_source_repository, 'literature.controlled_response.source_v3.populate': self._controlled_response_repository, 'literature.gel.populate': self._gel_repository, 'literature.binding.populate': self.literature_binding_repository, 'literature.binding.model.populate': self.literature_binding_model_repository, 'literature.transport.response.populate': self.literature_transport_repository, 'literature.figure.populate': self.literature_figure_repository}[tool_name]()
                arguments = self._materialize_text_arguments(context, arguments, repo, operation_key)
                if tool_name == 'literature.controlled_response.source_v3.populate':
                    return repo.populate_v3(context, arguments, operation_key)
                return repo.populate_native(context, arguments, operation_key) if tool_name == 'literature.rate.source.populate' else repo.populate(context, arguments, operation_key)
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), 'field': getattr(error, 'field', None), **({'detail': deepcopy(error.detail)} if getattr(error, 'detail', None) is not None and (isinstance(error, ExperimentalContractError) and error.code == 'source_quote_mismatch' or (isinstance(error, ContractError) and str(error) == 'representation_error')) else {})}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        if self.rate_population and tool_name == 'state.query' and (outcome.get('status') in {'completed', 'partial'}):
            try:
                for record in outcome.get('result', {}).get('records', ()):
                    self._endpoint_signal_repository().authorize_record_access(context, record)
                    self._summary_precision_repository().authorize_record_access(context, record)
                    self._measurement_comparison_repository().authorize_record_access(context, record)
                    self._concentration_window_repository().authorize_record_access(context, record)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        return outcome
from gene_annotation_episode.episodic_workflow.root.a105.runtime import Draft202012Validator, EventTargetError, FACT_MEANINGS, FACT_SOURCES, Mapping, Record, ReportRedelivery, SourceEnd, ValidationError, _decode_recorded_action_response, _json, _plain, _references_in, _wait_target_feedback, form_with_facts, inspect, json, nullcontext, observes_action_outcome, schema_failure_diagnostic, validate_form
from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionFailure
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.episode_contract_information import ContractInformationError
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.episode_journal import WorkflowError
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.task_state import LiteratureTaskState
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.task_decision import LiteratureTaskDecision
from .task_instructions import instructions as compose_private_instructions

class LiteratureTask(LiteratureTaskState, LiteratureTaskDecision):
    instruction_composer = staticmethod(compose_private_instructions)

    async def next(self, view, *, delivery_ref=None):
        if delivery_ref is None:
            self._selection_view = view
            closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
            if closed is not None and closed['state'] == 'yielded' and (closed['completion'] is not None):
                completion = _original_runtime.json.loads(closed['completion'])
                if completion['ended_by'] == 'source_failed' and view.units_consumed == completion['actions']:
                    return _original_runtime.SourceEnd('source_failed')
        if self.workflow.inprocess_replay is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.inprocess_replay.unit(self, view.units_consumed)
            if ready is not None:
                return ready
            self.restore_checkpoint()
            self._inprocess_replay_ready = True
            with self.workflow.store.transaction():
                self.workflow.inprocess_replay.capture(self)
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, _original_runtime.json.loads(action['action']), index)
        if self.workflow.execution_binding is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            self.restore_checkpoint()
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, _original_runtime.json.loads(action['action']), index)
            ready = self.workflow.next_return(self)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            await self.workflow.resolve_pending_deliveries(self, view)
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
        while True:
            original_call = self.workflow.journal.row('runtime_model_calls', self.episode_id, self.calls)
            if delivery_ref is None and original_call is None and (self._execution_context is not None):
                ready = self._execution_context._ready_owned_child(self.path)
                if ready is not None:
                    return ready
            original_request = _original_runtime.json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None or 'contract_information' in original_request or 'literature_numerical_contracts' in original_request):
                context, schema = (original_request['context'], original_request['schema'])
            else:
                with self.workflow.store.read_snapshot():
                    state = self.workflow.working_state(self)
                    row = self.workflow.journal.db.execute("SELECT CASE\n                        WHEN json_extract(action,'$.kind')='tool'\n                         AND json_extract(action,'$.tool')='image.view'\n                         AND json_extract(result,'$.status')='completed'\n                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END\n                        FROM runtime_actions WHERE run_id=? AND episode_id=?\n                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1", (self.workflow.run_id, self.episode_id)).fetchone()
                    visual_evidence = _original_runtime.json.loads(row[0]) if row and row[0] is not None else []
                    subset = getattr(self.workflow.store, 'reference_subset', None)
                    presented_outcome = self.workflow.local_outcome_preview(self.last_outcome, decision_index=self.last_outcome_index)
                    presented_feedback = self.feedback
                    if isinstance(self.last_outcome, _original_runtime.Mapping) and self.feedback is self.last_outcome.get('feedback') and isinstance(presented_outcome, _original_runtime.Mapping):
                        presented_feedback = presented_outcome.get('feedback')
                    credit_view = self.workflow.source_credit_view(self)
                    forms = [(self.report_values, self.interpret_schema)]
                    forms.extend(((report.as_record(), _original_runtime._plain(report.contract.measurements['schema'])) for report in view.child_reports))
                    controller_state = _original_runtime._plain(view.controller_state)
                    basis = _original_runtime._references_in({'working_state': state, 'last_local_outcome': presented_outcome, 'visual_evidence': visual_evidence}, self.workflow.store.get, forms=forms, reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
                    context = view.model_inputs({'goal': self.request.goal.as_record(), 'scope': self.scope, 'working_state': state, 'visible_record_refs': basis, 'current_credit': credit_view['credit'], 'current_evidence_vector': credit_view.get('axis_components'), **({'investigation_progress': {key: credit_view[key] for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages') if key in credit_view}} if self.workflow.receipt_projection(self) else {}), 'credit_binding': self.workflow.source_credit_binding(self), 'time_accounting': self.workflow.journal.elapsed_view(self.episode_id), 'pending_work': self.workflow.pending_work(self), 'last_local_outcome': presented_outcome, 'feedback': presented_feedback, 'visual_evidence': visual_evidence, 'report_deliveries': self.workflow.delivery_status(self.episode_id), 'controller': controller_state, 'controller_binding': self.workflow.controller_binding, 'tools': self.workflow.catalog(self.scope, source=self), 'tool_knowledge': self.workflow.knowledge.context(), 'job_episode_options': self.workflow.job_episode_options(self), 'available_report_facts': {name: {'type': 'number' if name == 'credit' else 'reference_array', 'meaning': _original_runtime.FACT_MEANINGS[name]} for name in sorted(_original_runtime.FACT_SOURCES)} | self.workflow.extra_report_sources(self), 'requested_report_purpose': self.request.report_contract.decision if self.request.report_contract else None, 'requested_form': self.request.report_contract.schema if self.request.report_contract else None, 'current_report_update': self.report_values, 'current_report_basis_refs': self.report_basis, 'report_lifecycle': 'Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment.'}, reports=view.child_reports)
                    if self.workflow.is_scientific_source(self):
                        context.update(self.workflow.annotation_context(self.scope, source=self))
                    if 'monitoring_information_credit' in credit_view:
                        context.update({key: credit_view[key] for key in ('monitoring_information_credit', 'monitoring_information_binding')})
                    specialist = self.workflow.specialist(self)
                    if specialist is not None:
                        context.update(specialist.decision_context(self.workflow.binding_context(self), view))
                    context['_completed_work_axis_results'] = {key: credit_view[key] for key in ('a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet', 'target_sheets', 'tool_attachments', 'source_contributions') if key in credit_view}
                    contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
                    if callable(contract_catalog):
                        context['available_report_facts'] = contract_catalog(context)
                schema = self.workflow.action_schema(self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(self, delivery_ref, context)
            if delivery_ref is not None and context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref:
                raise _original_runtime.WorkflowError('restored_delivery_resolution_identity_conflict')
            from gene_annotation_episode.episodic_workflow.root.provider_errors import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from gene_annotation_episode.episodic_workflow.root.a105.episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id, self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source', 'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                if delivery_ref is not None:
                    raise
                return _original_runtime.SourceEnd('source_failed')
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None else _original_runtime.nullcontext():
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit

    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = self.workflow.journal.row('runtime_model_calls', self.episode_id, index) if original is None and self.workflow.decision_exchanges is not None else None
            saved = {} if call is None else _original_runtime.json.loads(call['request'])
            response = _original_runtime._decode_recorded_action_response(response, schema, recorded_selection=None if original is None else _original_runtime.json.loads(original['action']), exchanges=() if original is not None or self.workflow.decision_exchanges is None else self.workflow.decision_exchanges.rows(self.episode_id, index), exchange_schema=saved.get('contract_information', {}).get('exchange_schema'))
            selection = response['selection']
            if self._delivery_resolution_ref is not None:
                _original_runtime.Draft202012Validator(schema).validate(response)
                if response['report_update'] != self.report_values:
                    raise ValueError('delivery_resolution_must_preserve_current_interpretation')
            if self.workflow.permits_common_action(self, 'reason') and isinstance(selection, _original_runtime.Mapping) and (selection.get('kind') == 'reason'):
                envelope = self.workflow.reasoning_action_schema(self, {'type': 'object'})
                _original_runtime.Draft202012Validator(envelope).validate(selection)
                payload = selection['commit']
                commit_schema = self.workflow.store.reasoning_schema()
                if set(commit_schema.get('required', commit_schema['properties'])) <= set(payload) <= set(commit_schema['properties']) and all((value == [] for value in payload.values())) and (selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                    binding = self.workflow.specialist(self)
                    has_task_content = getattr(binding, 'reasoning_has_task_content', None)
                    if has_task_content is None or not has_task_content(self.workflow.binding_context(self), selection):
                        raise ValueError('empty_reasoning_commit')
            else:
                _original_runtime.Draft202012Validator(schema['properties']['selection']).validate(selection)
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
                unit = self.workflow.selected(self, selection, index)
        except _original_runtime.EventTargetError as error:
            self.feedback = _original_runtime._wait_target_feedback(error, status='invalid')
            self.record_effect(index, 'rejected')
            return None
        except (ValueError, KeyError, TypeError, _original_runtime.ValidationError) as error:
            self.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': _original_runtime.schema_failure_diagnostic(error) if isinstance(error, _original_runtime.ValidationError) else str(error)}
            if isinstance(error, _original_runtime.ContractInformationError):
                self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
                if error.code == 'closed_top_level_form_required':
                    self.feedback['repair'] = 'schema_json must encode a JSON Schema object with the explicit top-level field "type": "object" and a properties object. Keep the intended properties, declare every field in required, and set additionalProperties to false. A properties object alone does not declare the required outer type.'
                if isinstance(error.__cause__, _original_runtime.ReportBoundaryError):
                    self.feedback['schema_reason'] = str(error.__cause__)
            if isinstance(error, _original_runtime.ContractError) and str(error) == 'component_native_return_channels_required':
                self.feedback['contract_error'] = {'code': str(error), 'field': error.detail['field']}
                self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
                self.feedback['repair'] = error.detail['repair']
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = _original_runtime.validate_form(response['report_update'], self.interpret_schema, resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope, assignment=self.request.message.as_record().get('job_assignment'), grain='literature_strategy', schema=self.interpret_schema, source=self)
            self.report_values = admitted
            self.report_basis = [ref for ref in actual_context['visible_record_refs'] if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {'status': 'invalid', 'category': 'report_format', 'detail': getattr(error, 'diagnostic', {'code': 'invalid_report_update'})}
        if isinstance(unit, _original_runtime.ReportRedelivery):
            self.feedback = None if unit.failure is None else unit.failure.as_record()
        self.record_effect(index, 'redelivery' if isinstance(unit, _original_runtime.ReportRedelivery) else 'selected')
        return unit

    async def execute(self, selection, index):
        journal = self.workflow.journal
        old = journal.row('runtime_actions', self.episode_id, index)
        if old and _original_runtime.json.loads(old['action']) != selection:
            raise _original_runtime.WorkflowError('reconstructed selected work changed')
        if old and old['result'] is not None:
            result, credit = (_original_runtime.json.loads(old['result']), old['credit'])
        else:
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _original_runtime._json(selection), 'result': None, 'credit': None})
            key = f'{self.workflow.run_id}:{self.episode_id}:{index}'
            with journal.measure('runtime_actions', self.episode_id, index):
                if selection['kind'] == 'reason':
                    payload = selection['commit']
                    account_context = {'account_invocation': (self.workflow.run_id, self.episode_id)} if payload.get('interpretation_accounts') else {}
                    specialist = self.workflow.specialist(self)
                    execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                    result = execute_reasoning(self.workflow.binding_context(self), selection, key) if execute_reasoning is not None else None
                    if result is None:
                        result = self.workflow.store.commit_reasoning(payload, self.scope, key, **account_context)
                else:
                    result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
                if _original_runtime.inspect.isawaitable(result):
                    result = await result
            result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
            with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
                journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _original_runtime._json(selection), 'result': _original_runtime._json(result), 'credit': None})
                self.last_outcome, self.last_outcome_index = (result, index)
                if result['status'] not in ('completed', 'partial'):
                    self.feedback = result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')}
                self.checkpoint()
            credit = None
        observed_outcome = _original_runtime.observes_action_outcome(selection['kind'], result['status'])
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
            self.workflow.receive_native_outcome(self, result, index)
            if credit is None and observed_outcome:
                self.workflow.receive_outcome(self, selection, result, index)
        if credit is None and observed_outcome:
            result = await self.workflow.automatic_score_updates(self, index, result)
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else _original_runtime.nullcontext():
            if credit is None and observed_outcome:
                credit_view = self.workflow.source_credit_view(self)
                credit = credit_view['credit']
                if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                    self.workflow.retain_shared_grading_results(self, result, credit_view)
                journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _original_runtime._json(selection), 'result': _original_runtime._json(result), 'credit': credit})
            if self.workflow.execution_binding is not None and observed_outcome:
                self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=self.workflow.controller_value(self, index, credit), child_return=None)
                self.last_outcome, self.last_outcome_index = (result, index)
                self.checkpoint()
        self.last_outcome = result
        self.last_outcome_index = index
        if not observed_outcome:
            raise _original_runtime.ActionFailure(result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')})
        return self.workflow.controller_value(self, index, credit)

    async def finish(self, record):
        if self.request.report_contract is None:
            result = {'credit': self.workflow.source_credit_view(self)['credit'], 'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return _original_runtime.Record(result)
        saved = self.workflow.journal.row('runtime_forms', self.episode_id)
        if saved and saved['form'] is not None:
            form = _original_runtime.json.loads(saved['form'])
        else:
            facts = self.workflow.facts(self, completion_record=record)
            form = _original_runtime.form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save('runtime_forms', {'episode_id': self.episode_id, 'facts': _original_runtime._json({**facts, 'interpretations': self.report_values}), 'form': _original_runtime._json(form)})
        await self.workflow.release(self.episode_id)
        return _original_runtime.Record({'form': form})
from gene_annotation_episode.episodic_workflow.root.a105 import runtime as _original_runtime
