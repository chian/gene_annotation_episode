"""Private A102 API api operations."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, _outcome, checked, launch_operation_catalog, native_result_operation_catalog, plain

class APIApiOperations:

    def catalog(self, context):
        if self.native_protein_structure_results.applies(context):
            from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_results import operation_catalog as protein_result_catalog
            self._selector(plain(context.assignment), self._target(context))
            return protein_result_catalog()
        return self._delegate(context).catalog(context)

    async def execute(self, context, tool_name, arguments, operation_key):
        self._check_parent_inputs(context)
        return await self._delegate(context).execute(context, tool_name, arguments, operation_key)

