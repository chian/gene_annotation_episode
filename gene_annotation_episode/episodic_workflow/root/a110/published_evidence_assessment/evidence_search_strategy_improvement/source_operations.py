"""Private A110 source operations."""
from __future__ import annotations
from .contracts import ContractError, Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _population_catalog, deepcopy, identity, inspect, plain, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_population import populate

class LiteratureSourceOperations:

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
        populations = _population_catalog()
        if self._contract_information_profile is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.composition_information import CONTRACT_ARGUMENT_TRANSPORT
            populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
        result.extend(populations)
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        if tool_name in {'literature.reaction.populate', 'literature.reaction.source.populate'}:
            from gene_annotation_episode.episodic_workflow.root.a110.literature_contract_error import ExperimentalContractError
            try:
                if tool_name == 'literature.reaction.source.populate':
                    from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_source_selection import populate_source
                    repo = self.literature_reaction_repository()
                    return populate_source(repo, context, self._materialize_text_arguments(context, arguments, repo), operation_key)
                repo = self.literature_reaction_repository()
                arguments = self._materialize_text_arguments(context, arguments, repo)
                return populate(repo, context, arguments, operation_key)
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), 'field': getattr(error, 'field', None), **({'detail': deepcopy(error.detail)} if getattr(error, 'detail', None) is not None else {})}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        outcome = await outcome if inspect.isawaitable(outcome) else outcome
        return outcome

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment('literature_strategy', context.assignment, context.scope, context=context)
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
                from gene_annotation_episode.episodic_workflow.root.a110.component_axis_source_access import rejection_detail
                raise ContractError('literature_reading_outside_assigned_source', detail=rejection_detail(getattr(self.services, 'workflow', None), context, page['source_ref'], [source_ref]))
            if tool_name in {'literature.reaction.populate', 'literature.reaction.source.populate'}:

                def sources(value):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key == 'metadata_source_ref' and isinstance(child, str):
                                yield child
                                continue
                            if key in {'source_ref', 'sheet_ref', 'data_source_ref', 'reaction_source_ref'} and isinstance(child, str):
                                yield child
                            else:
                                yield from sources(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from sources(child)
                blocked = next((ref for ref in set(sources(arguments)) if not self._within_source(ref, page['source_ref'], context.scope)), None)
                if blocked is not None:
                    from gene_annotation_episode.episodic_workflow.root.a110.component_axis_source_access import rejection_detail
                    raise ContractError('literature_reading_outside_assigned_source', detail=rejection_detail(getattr(self.services, 'workflow', None), context, page['source_ref'], [blocked]))
        return arguments

    def _materialize_text_arguments(self, context, arguments, repository):
        from gene_annotation_episode.episodic_workflow.root.a110.library.literature_assay_inputs import materialize_text_witness_inputs

        def read_source(ref, representation):
            source = repository._source(context, ref)
            self._tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation})
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': repository.store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)
