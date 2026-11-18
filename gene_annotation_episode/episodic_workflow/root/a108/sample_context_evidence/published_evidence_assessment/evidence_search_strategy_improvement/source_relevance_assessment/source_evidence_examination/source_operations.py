from __future__ import annotations
'source operations for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_contracts import ContractError, Mapping, _A108_ACCESS_TOOLS, _a108_population_catalog, _required_grading_logic, deepcopy, identity, inspect, obj, plain, source_location_inputs, validate_schema

class LiteratureOperations:

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'reason', 'child', 'redeliver_report')

    def catalog(self, context):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = [{'name': name, **entry} for name, entry in available.items()] if isinstance(available, Mapping) else list(available)
        allowed = set(_A108_ACCESS_TOOLS)
        result = []
        for entry in entries:
            if entry['name'] not in allowed:
                continue
            entry = deepcopy(plain(entry))
            if entry['name'] == 'public.ncbi.search':
                entry['input_schema']['properties']['database'] = {'enum': ['pubmed', 'protein', 'nuccore', 'taxonomy', 'biosample', 'bioproject']}
            if entry['name'] == 'execution.estimate':
                branches = [branch for branch in entry['input_schema'].get('anyOf', ()) if branch.get('properties', {}).get('tool', {}).get('const') in {'source.xlsx.sheets', 'source.xlsx.rows'}]
                if not branches:
                    continue
                entry['input_schema'] = {'anyOf': branches}
            result.append(entry)
        populations = _a108_population_catalog()
        if self._contract_information_profile is not None:
            from gene_annotation_episode.episodic_workflow.root.a108.composition_information import CONTRACT_ARGUMENT_TRANSPORT
            populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
        result.extend(populations)
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        if tool_name in {'literature.a108_grading.populate', 'literature.a108.aggregate'}:
            from gene_annotation_episode.episodic_workflow.root.a108.literature_contract_error import ExperimentalContractError
            repository = self._a108_grading_repository() if tool_name == 'literature.a108_grading.populate' else self._a108_aggregation_repository()
            try:
                materialized = self._materialize_text_arguments(context, arguments, repository)
                return repository.populate(context, materialized, operation_key)
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), 'field': getattr(error, 'field', None), **({'detail': deepcopy(error.detail)} if getattr(error, 'detail', None) is not None else {})}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.references'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        if tool_name == 'state.query' and outcome.get('status') in {'completed', 'partial'}:
            try:
                for record in outcome.get('result', {}).get('records', ()):
                    self._a108_grading_repository().authorize_record_access(context, record)
                    self._a108_aggregation_repository().authorize_record_access(context, record)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        return outcome

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment('literature_page', context.assignment, context.scope, context=context)
        entries = {entry['name']: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ContractError('tool_not_available_to_literature_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        page = assignment
        if page:
            selected = arguments['arguments'] if tool_name == 'execution.estimate' else arguments
            source_ref = selected.get('source_ref')
            if tool_name == 'source.archive.extract':
                member = self._require(arguments['member_ref'], context.scope, 'archive_member')
                source_ref = member['source_ref']
            if source_ref is not None and (not self._within_source(source_ref, page['source_ref'], context.scope)):
                raise ContractError('literature_reading_outside_assigned_source')
            if tool_name in {'literature.a108_grading.populate', 'literature.a108.aggregate'}:

                def sources(value):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key in {'source_ref', 'metadata_source_ref', 'sheet_ref', 'covariance_source_ref', 'model_source_ref'} and isinstance(child, str):
                                yield child
                            else:
                                yield from sources(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from sources(child)
                if any((not self._within_source(ref, page['source_ref'], context.scope) for ref in set(sources(arguments)))):
                    raise ContractError('literature_reading_outside_assigned_source')
        for repository in (self._a108_grading_repository(), self._a108_aggregation_repository()):
            if isinstance(arguments.get('source_ref'), str) and (tool_name.startswith('source.') or tool_name in {'image.view', 'material.from_source'}):
                representation = arguments.get('representation', 'original' if tool_name == 'source.sequence.references' else 'text')
                repository.authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            elif tool_name == 'state.query' and 'refs' in arguments:
                for ref in arguments['refs']:
                    repository.authorize_record_access(context, self.services.read_record(ref))
        return arguments

    def _materialize_text_arguments(self, context, arguments, repository):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_assay_inputs import materialize_text_witness_inputs

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation})
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': repository.store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)
