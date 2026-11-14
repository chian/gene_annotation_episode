"""Scientific tool retrieval reused by the private head and standalone binding protocol.

The standalone dispatcher retains supplied bindings that do not declare the new
private catalogue callback. It selects no arbitrary private episode implementation.
"""
from __future__ import annotations

async def retrieve_tools(workflow, source, arguments, operation_key, retriever_catalog, *, validator_type, validation_error):
    try:
        validator_type(retriever_catalog[0]['input_schema']).validate(arguments)
        tools = workflow.scientific_process_binding.tool_library
        available = workflow.services.tool_information_catalog(source.scope) if tools.supports_tool_info else workflow.services.tool_catalog(source.scope)
        if not tools.supports_tool_info:
            tools.resolve([entry['name'] for entry in tools.catalog()], available)
        if workflow.scientific_tool_retriever is not None:
            return await workflow.scientific_tool_retriever.retrieve(arguments['investigation'], episode_id=source.episode_id, operation_key=operation_key, available_catalog=available)
        result = tools.retrieve_literal_test(arguments['investigation'], available_catalog=available)
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result, 'feedback': None}
    except (ValueError, validation_error) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': str(error)}}

async def execute_standalone_catalog_operation(workflow, source, name, arguments, operation_key, retriever_catalog, *, validator_type, validation_error, library_executor=None):
    if not workflow.scientific_library_available(source):
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': 'tool_not_available_to_episode'}}
    if name == 'process.tools':
        return await retrieve_tools(workflow, source, arguments, operation_key, retriever_catalog, validator_type=validator_type, validation_error=validation_error)
    if library_executor is not None:
        return library_executor()
    return workflow.services.execute_scientific_library(workflow.binding_context(source), name, arguments)
