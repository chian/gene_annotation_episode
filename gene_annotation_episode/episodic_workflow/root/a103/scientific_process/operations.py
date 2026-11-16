"""Private A103 scientific operations."""
from __future__ import annotations
from .contracts import ContractError, INSTRUCTION_VERSION, _COMMON_TOOLS, _REVISION_ARGUMENTS, _object, deepcopy, identity, inspect, plain, scientific_digest, scientific_invocation_ref, selection_fields, validate_child_selection, validate_revision_origin, validate_schema, validate_selection

class ScientificOperations:

    def _information_catalog(self, scope):
        callback = getattr(self.services, 'tool_information_catalog', self.services.tool_catalog)
        return callback(scope)

    def _closed_tool_resolution(self, context, selection):
        """Read only an authenticated closed invocation's original frozen contracts."""
        original = self.restore_closed_process(context)
        if original is None:
            return None
        if scientific_digest(selection) != scientific_digest(original['selection']):
            raise ContractError('scientific_filled_identity_mismatch')
        return self.tool_library.resolve_invocations(selection['child_tool_info'])

    def _tool_resolution_for(self, selection, scope, *, context=None):
        if context is not None:
            if plain(scope) != plain(context.scope):
                raise ContractError('scientific_filled_identity_mismatch')
            closed = self._closed_tool_resolution(context, selection)
            if closed is not None:
                return closed
        return self.tool_library.resolve_invocations(selection['child_tool_info'], self._information_catalog(scope))

    def _tool_resolution(self, context, selection):
        entries = self._tool_resolution_for(selection, context.scope, context=context)
        if any((entry['name'] in {*_COMMON_TOOLS, 'process.revise'} for entry in entries)):
            raise ContractError('scientific_primitive_uses_common_tool_name')
        return entries

    def catalog(self, context):
        selection = self._original_selection(context)
        resolved = self._tool_resolution(context, selection)
        direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
        if self._closed_tool_resolution(context, selection) is not None:
            resolved = direct
        else:
            resolved = self.tool_library.resolve_invocations([{'name': row['name'], 'resources': row['resources']} for row in direct], self.services.tool_catalog(context.scope))
        entries = [{key: deepcopy(value) for key, value in row.items() if key not in {'instructions', 'invocation_route'}} for row in plain(resolved)]
        description = "Prepare a pinned thought pattern and selected actual tools for a new child using the original scientific support and library. Return its selection for a separately selected episode_child commission with the child's job, scope, constraints and typed form. Copy result.selection and revision_origin into that assignment; request scientific_process_results in the form when process provenance and existing closed results are needed. Changes no current process, starts no child and records no biological observation. Supply the actual tool names returned by process.tools for the desired alternative investigation."
        axis = self.library.resolve(selection[selection_fields(selection)[0]])
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            description = "Prepare a different thought pattern and/or selected actual tools for a new child investigating the same evidence axis. Return its selection for a separately selected episode_child commission with the child's job, scope, constraints and typed return form. Copy result.selection and revision_origin into that assignment. Changes no current process, starts no child and records no biological observation. Select the actual tool/resource choices returned by process.tools for the desired investigation."
        entries.append({'name': 'process.revise', 'description': description, 'input_schema': deepcopy(_REVISION_ARGUMENTS)})
        if getattr(self.services, 'workflow', None) is not None and self.tool_library.supports_tool_info:
            from gene_annotation_episode.episodic_workflow.root.a103.execution_planning import catalog
            entries.extend(catalog())
        return entries

    def common_tool_names(self, context):
        return (*_COMMON_TOOLS, *(entry['name'] for entry in self.catalog(context)))

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
            from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.tool_policy import validate_tool_name
            validate_tool_name(tool_name)
            arguments = _object(arguments, 'scientific_arguments_invalid')
            validate_schema(arguments, entries[tool_name]['input_schema'])
            if tool_name == 'process.execution':
                from gene_annotation_episode.episodic_workflow.root.a103.execution_planning import read
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
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope, operation_key=operation_key, **{'permitted_record_refs': context.received_record_refs} if tool_name.startswith('context.') or tool_name in {'reference.neighborhood', 'result.blast.hsp', 'source.locate'} else {})
        return await outcome if inspect.isawaitable(outcome) else outcome
