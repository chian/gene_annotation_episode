"""Private scientific catalogue authorization and dispatch for A108."""
from __future__ import annotations
from ..library.scientific_catalog_operations import retrieve_tools

class ScientificLibraryOperations:

    async def execute_catalog_operation(self, workflow, source, name, arguments, operation_key, retriever_catalog, *, validator_type, validation_error, library_executor=None):
        if not workflow.scientific_library_available(source):
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': 'tool_not_available_to_episode'}}
        if name == 'process.tools':
            return await retrieve_tools(workflow, source, arguments, operation_key, retriever_catalog, validator_type=validator_type, validation_error=validation_error)
        if library_executor is not None:
            return library_executor()
        return workflow.services.execute_scientific_library(workflow.binding_context(source), name, arguments)
