"""Private A103 literature source operations."""
from __future__ import annotations
from .source_contracts import ContractError, Mapping, _ACCESS_TOOLS, _ACQUISITION_TOOLS, deepcopy, identity, inspect, plain, source_location_inputs, validate_schema

class SourceOperations:

    def catalog(self, context):
        self._role('literature')
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
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])} for entry in result]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': plain(arguments)}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
        authorization = {'permitted_record_refs': tuple(context.received_record_refs)} if tool_name in {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'} else {}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **authorization)
        return await outcome if inspect.isawaitable(outcome) else outcome

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment('literature', context.assignment, context.scope, context=context)
        entries = {entry['name']: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ContractError('tool_not_available_to_a103_literature_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        return arguments
