"""Private A102 literature_search source operations."""
from __future__ import annotations
from .source_contracts import ContractError, Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _population_catalog, deepcopy, identity, inspect, plain, source_location_inputs, validate_schema

class SourceSourceOperations:

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
        if self.structure_population:
            populations = _population_catalog()
            if self._contract_information_profile is not None:
                from gene_annotation_episode.episodic_workflow.root.a102.composition_information import CONTRACT_ARGUMENT_TRANSPORT
                populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
            result.extend(populations)
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        if tool_name == 'literature.structure.populate':
            from gene_annotation_episode.episodic_workflow.root.a102.literature_contract_error import ExperimentalContractError
            repository = self.literature_structure_repository()
            try:
                materialized = self._materialize_text_arguments(context, arguments, repository)
                return repository.populate(context, materialized, operation_key)
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': getattr(error, 'code', str(error))}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        return outcome

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope, context=context)
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
                raise ContractError('literature_reading_outside_assigned_source')
            if tool_name == 'literature.structure.populate':

                def source_refs(value):
                    if isinstance(value, Mapping):
                        for key, child in value.items():
                            if key in {'source_ref', 'coordinate_source_ref', 'validation_source_ref', 'metadata_source_ref', 'model_source_ref'} and isinstance(child, str):
                                yield child
                            else:
                                yield from source_refs(child)
                    elif isinstance(value, (list, tuple)):
                        for child in value:
                            yield from source_refs(child)
                if any((not self._within_source(ref, page['source_ref'], context.scope) for ref in set(source_refs(arguments)))):
                    raise ContractError('literature_reading_outside_assigned_source')
        return arguments

    def _materialize_text_arguments(self, context, arguments, repository):
        from gene_annotation_episode.episodic_workflow.root.a102.library.literature_assay_inputs import materialize_text_witness_inputs

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation})
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': repository.store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)
