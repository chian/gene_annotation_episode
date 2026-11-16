"""Private scientific scientific operations."""
from __future__ import annotations
from .scientific_contracts import ContractError, _object, identity, inspect, scientific_digest, scientific_invocation_ref, selection_fields, validate_child_selection, validate_revision_origin, validate_schema, validate_selection

class ScientificOperations:

    async def execute(self, context, tool_name, arguments, operation_key):
        self.validate_execution_context(context)
        selection = validate_selection(context.assignment['selection'])
        try:
            if not isinstance(operation_key, str) or not operation_key:
                raise ContractError('operation_key_required')
            entries = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in entries:
                raise ContractError('scientific_operation_unavailable')
            axis = self.library.resolve(selection[selection_fields(selection)[0]])
            arguments = _object(arguments, 'scientific_arguments_invalid')
            validate_schema(arguments, entries[tool_name]['input_schema'])
            if tool_name == 'process.execution':
                from .execution_planning import read
                return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': read(self, context, arguments)}
            if tool_name in {'material.from_source', 'material.parse', 'material.read', 'source.read', 'source.locate'}:
                self.services.authenticate_source_byte_operands(context, tool_name, arguments)
            if tool_name == 'process.revise':
                proposed = self._proposed_selection(selection, arguments, context.scope)
                self._tool_resolution(context, proposed)
                child_selection = validate_child_selection({'version': 'scientific_process_child_selection_v1', 'parent_selection_sha256': scientific_digest(selection), 'selection': proposed})
                operation_ref = identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': arguments})
                origin = validate_revision_origin({'version': 'scientific_process_revision_origin_v1', 'parent_invocation_ref': scientific_invocation_ref(context.run_id, context.path), 'preparation_operation_ref': operation_ref})
                return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [], 'result': child_selection, 'revision_origin': origin, 'feedback': None}
        except ValueError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name}), 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **{'permitted_record_refs': context.received_record_refs} if tool_name == 'source.locate' else {})
        return await outcome if inspect.isawaitable(outcome) else outcome
