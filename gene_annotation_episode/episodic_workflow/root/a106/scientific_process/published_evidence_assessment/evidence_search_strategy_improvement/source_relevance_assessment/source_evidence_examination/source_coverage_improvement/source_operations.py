"""Private A106 literature_ordered source operations."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_contracts import ContractError, Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _population_catalog, _required_grading_logic, deepcopy, identity, inspect, obj, plain, source_location_inputs, validate_schema

class LiteratureOperations:

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def reasoning_action_schema(self, context, commit_schema):
        repository = self._required_grading_repository(context)
        leads = context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads'
        if repository is None and (not leads):
            return None
        schema = obj({'kind': {'const': 'reason'}, 'commit': deepcopy(commit_schema)}) if repository is None else _required_grading_logic(repository).action_schema(commit_schema, source_location_inputs(repository.population_schema()))
        if leads:
            from gene_annotation_episode.episodic_workflow.root.a106.library.literature_commission_contracts import lead_schema
            schema['properties']['source_lead'] = lead_schema()
        return source_location_inputs(schema)

    def reasoning_has_task_content(self, context, selection):
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.goal import commissioned_task
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_commission_contracts import lead_schema
        if 'source_lead' not in selection:
            return False
        task, _ = commissioned_task(context)
        if task['kind'] != 'verified_source_leads':
            return False
        validate_schema(plain(selection['source_lead']), source_location_inputs(lead_schema()))
        return True

    def execute_reasoning(self, context, selection, operation_key):
        repository = self._required_grading_repository(context)
        if 'source_lead' in selection:
            from gene_annotation_episode.episodic_workflow.root.a106.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.credit import validate_lead
            from gene_annotation_episode.episodic_workflow.root.a106.literature_contract_error import ExperimentalContractError
            store = self.services.workflow.store
            try:
                witness = selection['source_lead']['witness']
                self._tool_arguments(context, 'source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'], 'offset': witness['start'], 'limit': witness['end'] - witness['start']})
                with store.transaction():
                    native = {key: value for key, value in plain(selection).items() if key != 'source_lead'}
                    account_context = {'account_invocation': (context.run_id, context.episode_id)} if native['commit'].get('interpretation_accounts') else {}
                    result = store.commit_reasoning(native['commit'], plain(context.scope), operation_key, **account_context) if repository is None else _required_grading_logic(repository).execute(context, native, operation_key, repository, authorize_source_access=lambda ref, representation: self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation}))
                    if result['status'] not in ('completed', 'partial'):
                        return result
                    return {**result, 'literature_source_lead': validate_lead(store, context, selection['source_lead'], result)}
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}
        if repository is None:
            return None
        return _required_grading_logic(repository).execute(context, selection, operation_key, repository, authorize_source_access=lambda ref, representation: self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation}))

    def catalog(self, context):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = [{'name': name, **entry} for name, entry in available.items()] if isinstance(available, Mapping) else list(available)
        allowed = set(_ACCESS_TOOLS)
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
        populations = _population_catalog(ratio_source_population=self.ratio_source_population, controlled_response_population=self.controlled_response_population, gel_population=self.gel_population, completion_time_population=self.completion_time_population, active_site_population=self.active_site_population, parent_depletion_population=self.parent_depletion_population, stoichiometric_balance_population=self.stoichiometric_balance_population, product_partition_population=self.product_partition_population, compiled_assay_population=self.compiled_assay_population, channel_population=self.channel_population, ion_discrimination_population=self.ion_discrimination_population)
        if self._contract_information_profile is not None:
            from gene_annotation_episode.episodic_workflow.root.a106.composition_information import CONTRACT_ARGUMENT_TRANSPORT
            populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
        result.extend(populations)
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        if tool_name == 'literature.intervention_analysis.contract':
            try:
                value = prepare_analysis_contract(self.services, arguments, context=context)
            except ContractError as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': value, 'feedback': None}
        if tool_name in {'literature.concentration_window.populate', 'literature.measurement_comparison.populate', 'literature.product_coupling.populate', 'literature.measurement_validation.populate', 'literature.ion_discrimination.populate', 'literature.channel.populate', 'literature.assay.components.populate', 'literature.calibration.recovery.populate', 'literature.rate.observations.populate', 'literature.rate.replicates.populate', 'literature.rate.populate', 'literature.rate.source.populate', 'literature.quantity.populate', 'literature.assay.populate', 'literature.ratio.populate', 'literature.ratio.source.populate', 'literature.binding.populate', 'literature.binding.model.populate', 'literature.transport.response.populate', 'literature.perturbation.populate', 'literature.figure.populate', 'literature.amount.populate', 'literature.completion_time.populate', 'literature.active_site.populate', 'literature.product_partition.populate', 'literature.optical.populate', 'literature.kinetic.populate', 'literature.kinetic.model.populate', 'literature.binding.interaction.populate', 'literature.binding.interaction.model.populate', 'literature.controlled_response.source_v3.populate', 'literature.gel.populate', 'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate', 'literature.intervention_grading.populate', 'literature.a106.finalize'}:
            from gene_annotation_episode.episodic_workflow.root.a106.literature_contract_error import ExperimentalContractError
            try:
                if tool_name == 'literature.figure.populate' and arguments.get('version') == 'literature_figure_endpoint_signal_population_v1':
                    repo = self._endpoint_signal_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                if tool_name == 'literature.kinetic.populate' and arguments.get('version') == 'literature_kinetic_summary_precision_population_v1':
                    repo = self._summary_precision_repository()
                    return repo.populate(context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                repo = {'literature.concentration_window.populate': self._concentration_window_repository, 'literature.measurement_comparison.populate': self._measurement_comparison_repository, 'literature.product_coupling.populate': self._product_coupling_repository, 'literature.measurement_validation.populate': self._measurement_validation_repository, 'literature.ion_discrimination.populate': self._ion_discrimination_repository, 'literature.channel.populate': self._channel_repository, 'literature.assay.components.populate': self._compiled_assay_repository, 'literature.rate.populate': lambda: self._a106_repository('rate'), 'literature.calibration.recovery.populate': lambda: self._a106_repository('calibration_recovery'), 'literature.rate.observations.populate': lambda: self._a106_repository('rate_observation'), 'literature.rate.replicates.populate': lambda: self._a106_repository('rate_replicate'), 'literature.rate.source.populate': lambda: self._a106_repository('rate'), 'literature.quantity.populate': lambda: self._a106_repository('quantity'), 'literature.assay.populate': lambda: self._a106_repository('assay'), 'literature.amount.populate': lambda: self._a106_repository('amount'), 'literature.completion_time.populate': self._completion_time_repository, 'literature.active_site.populate': self._active_site_repository, 'literature.parent_depletion.populate': self._parent_depletion_repository, 'literature.stoichiometric_balance.populate': self._stoichiometric_balance_repository, 'literature.intervention_grading.populate': self._intervention_grading_repository, 'literature.a106.finalize': self._a106_subscore_repository, 'literature.product_partition.populate': self._product_partition_repository, 'literature.optical.populate': lambda: self._a106_repository('optical'), 'literature.kinetic.populate': lambda: self._a106_repository('kinetic'), 'literature.kinetic.model.populate': self._kinetic_model_repository, 'literature.binding.interaction.populate': lambda: self._a106_repository('binding_interaction'), 'literature.binding.interaction.model.populate': self._binding_interaction_model_repository, 'literature.ratio.populate': lambda: self._a106_repository('ratio'), 'literature.ratio.source.populate': self._ratio_source_repository, 'literature.controlled_response.source_v3.populate': self._controlled_response_repository, 'literature.gel.populate': self._gel_repository, 'literature.binding.populate': lambda: self._a106_repository('binding'), 'literature.binding.model.populate': lambda: self._a106_repository('binding_model'), 'literature.transport.response.populate': lambda: self._a106_repository('transport'), 'literature.perturbation.populate': lambda: self._a106_repository('perturbation'), 'literature.figure.populate': lambda: self._a106_repository('figure')}[tool_name]()
                arguments = self._materialize_text_arguments(context, arguments, repo)
                if tool_name == 'literature.controlled_response.source_v3.populate':
                    return repo.populate_v3(context, arguments, operation_key)
                return repo.populate_native(context, arguments, operation_key) if tool_name == 'literature.rate.source.populate' else repo.populate(context, arguments, operation_key)
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), 'field': getattr(error, 'field', None), **({'detail': deepcopy(error.detail)} if getattr(error, 'detail', None) is not None and (isinstance(error, ExperimentalContractError) and error.code == 'source_quote_mismatch' or (isinstance(error, ContractError) and str(error) in {'representation_error', 'a106_revision_question_mismatch', 'a106_existing_assessment_requires_null_missing_reason'}) or (isinstance(error, ContractError) and tool_name == 'literature.intervention_grading.populate' and (str(error) == 'assay_grading_anchored_support_required' or (str(error) == 'intervention_latest_revision_required' and bool(error.detail))))) else {})}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        if tool_name == 'state.query' and outcome.get('status') in {'completed', 'partial'}:
            try:
                for record in outcome.get('result', {}).get('records', ()):
                    self._endpoint_signal_repository().authorize_record_access(context, record)
                    self._summary_precision_repository().authorize_record_access(context, record)
                    self._measurement_comparison_repository().authorize_record_access(context, record)
                    self._concentration_window_repository().authorize_record_access(context, record)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        return outcome

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment('literature_ordered', context.assignment, context.scope, context=context)
        entries = {entry['name']: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ContractError('tool_not_available_to_literature_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        page = assignment.get('page')
        if page:
            selected_arguments = arguments['arguments'] if tool_name == 'execution.estimate' else arguments
            source_ref = selected_arguments.get('source_ref')
            if tool_name == 'source.archive.extract':
                member = self._require(arguments['member_ref'], context.scope, 'archive_member')
                source_ref = member['source_ref']
            if source_ref is not None and (not self._within_source(source_ref, page['source_ref'], context.scope)):
                raise ContractError('literature_reading_outside_assigned_source', detail=None)
            if tool_name in {'literature.concentration_window.populate', 'literature.measurement_comparison.populate', 'literature.product_coupling.populate', 'literature.measurement_validation.populate', 'literature.ion_discrimination.populate', 'literature.channel.populate', 'literature.assay.components.populate', 'literature.calibration.recovery.populate', 'literature.rate.observations.populate', 'literature.rate.replicates.populate', 'literature.rate.source.populate', 'literature.assay.populate', 'literature.ratio.populate', 'literature.ratio.source.populate', 'literature.binding.populate', 'literature.binding.model.populate', 'literature.transport.response.populate', 'literature.perturbation.populate', 'literature.figure.populate', 'literature.amount.populate', 'literature.completion_time.populate', 'literature.active_site.populate', 'literature.product_partition.populate', 'literature.optical.populate', 'literature.kinetic.populate', 'literature.kinetic.model.populate', 'literature.binding.interaction.populate', 'literature.binding.interaction.model.populate', 'literature.controlled_response.source_v3.populate', 'literature.gel.populate', 'literature.parent_depletion.populate', 'literature.stoichiometric_balance.populate', 'literature.intervention_grading.populate', 'literature.a106.finalize'}:

                def sources(value):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key == 'metadata_source_ref' and isinstance(child, str):
                                yield child
                                continue
                            if (key == 'sheet_ref' and tool_name in {'literature.intervention_grading.populate', 'literature.a106.finalize', 'literature.measurement_validation.populate', 'literature.assay.components.populate', 'literature.ion_discrimination.populate'} or (key == 'original_source_ref' and tool_name == 'literature.binding.interaction.populate') or key in {'source_ref', 'covariance_source_ref', 'activity_covariance_source_ref', 'model_source_ref', 'km_sheet_ref', 'data_source_ref', 'coordinate_source_ref', 'validation_source_ref'}) and isinstance(child, str):
                                yield child
                            elif key == 'covariance_source_refs' and tool_name == 'literature.measurement_comparison.populate':
                                yield from child
                            else:
                                yield from sources(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from sources(child)
                    elif isinstance(value, str) and (value in arguments.get('visual_source_refs', ()) or value in arguments.get('covariance_source_refs', ())):
                        yield value
                blocked = next((ref for ref in set(sources(arguments)) if not self._within_source(ref, page['source_ref'], context.scope)), None)
                if blocked is not None:
                    raise ContractError('literature_reading_outside_assigned_source', detail=None)
        repo = self._endpoint_signal_repository()
        if tool_name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}:
            representation = 'original' if tool_name in {'source.sequence.references', 'source.experimental.records'} else arguments.get('representation', 'text')
            repo.authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            self._summary_precision_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            self._measurement_comparison_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            self._concentration_window_repository().authorize_source_access(context, arguments['source_ref'], representation, tool_name)
        elif tool_name == 'state.query' and 'refs' in arguments:
            for ref in arguments['refs']:
                repo.authorize_record_access(context, self.services.read_record(ref))
                self._summary_precision_repository().authorize_record_access(context, self.services.read_record(ref))
                self._measurement_comparison_repository().authorize_record_access(context, self.services.read_record(ref))
                self._concentration_window_repository().authorize_record_access(context, self.services.read_record(ref))
        return arguments

    def _materialize_text_arguments(self, context, arguments, repository):
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_assay_inputs import materialize_text_witness_inputs

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation})
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': repository.store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)


from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a106.library.intervention_execution_lookup import _execution

CONTRACT_OPERATION = "literature.intervention_analysis.contract"

def prepare_analysis_contract(services, arguments, *, context=None):
    from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_adapters import selected_adapter
    binding = _execution(services, context=context)
    service = None if binding is None else binding.api_execution.services.get(arguments["resource_id"])
    if service is None or service.service != "bvbrc_appservice":
        raise ContractError("intervention_analysis_execution_unbound")
    parameters = arguments["parameters"]
    adapter_id = {"TnSeq":"bvbrc_tnseq", "RNASeq":"bvbrc_rnaseq"}.get(parameters.get("application_id"))
    selection = dict(adapter_id=adapter_id, adapter_version="1", parameters=parameters)
    selected = selected_adapter(service, selection)
    if selected is None:
        raise ContractError("intervention_analysis_adapter_unbound")
    implementation, digest = selected
    try:
        parameters = implementation.validate_parameters(parameters)
        schema = implementation.requested_form_schema(arguments["fields"])
    except ValueError as error:
        raise ContractError(str(error)) from error
    documents = {row["document_id"] for row in parameters["documents"]}
    if any(row["selection"]["document_id"] not in documents for row in arguments["fields"]):
        raise ContractError("intervention_analysis_selected_document_unbound")
    return dict(resource_id=arguments["resource_id"], adapter=deepcopy(selection), requested_schema=schema,
        adapter_implementation_sha256=digest, parent_report_source="bvbrc_application_outcomes",
        service_availability="not_observed")
