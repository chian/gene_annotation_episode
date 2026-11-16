"""Private scientific tool selection."""
from __future__ import annotations
from .scientific_contracts import ContractError, INSTRUCTION_VERSION, _COMMON_TOOLS, _REVISION_ARGUMENTS, deepcopy, plain, scientific_digest, selection_fields

class ScientificToolSelection:

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
            from .execution_planning import catalog
            entries.extend(catalog())
        return entries

    def create_tool_retriever(self, store, *, run_id, provider, configuration):
        from gene_annotation_episode.episodic_workflow.root.a101.scientific_tool_retrieval import ScientificToolRetriever
        return ScientificToolRetriever(store, run_id=run_id, provider=provider, library=self.tool_library, configuration=configuration)

    def common_tool_names(self, context):
        return (*_COMMON_TOOLS, *(entry['name'] for entry in self.catalog(context)))
