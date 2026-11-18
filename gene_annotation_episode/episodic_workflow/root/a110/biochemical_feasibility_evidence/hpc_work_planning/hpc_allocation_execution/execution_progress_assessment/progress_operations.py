"""ProgressOperations"""
from __future__ import annotations
from copy import deepcopy
import inspect
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, REF, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import native_observation_options
from .contracts import _FIELDS

class ProgressOperations:

    def catalog(self, context):
        self._role(context.role)
        properties = {'requested_fields': deepcopy(_FIELDS)}
        describe = getattr(self.services, 'describe_progress_target', None)
        descriptor = describe(context.assignment['target_handle'], context.scope) if describe is not None else None
        selected_schema = (descriptor or {}).get('selected_observation_schema')
        if selected_schema is not None:
            if selected_schema.get('type') != 'object' or selected_schema.get('additionalProperties') is not False or set(selected_schema.get('properties', {})) != {'native_operation'} or (selected_schema.get('required') != ['native_operation']):
                raise ContractError('progress_selected_observation_schema_invalid')
            properties.update(deepcopy(selected_schema['properties']))
        return [{'name': 'progress.observe', 'description': 'Observe selected exposed fields of your assigned target. Retain the original observation identity when facts are unchanged. This operation never traverses dependent work.', 'input_schema': obj(properties)}, {'name': 'progress.read', 'description': 'Read an already delivered exact progress observation.', 'input_schema': obj({'progress_ref': REF})}, {'name': 'progress.log', 'description': 'Read one exact retained log window from an already delivered progress observation, preserving source/artifact byte custody.', 'input_schema': obj({'progress_ref': REF, 'log_index': {'type': 'integer', 'minimum': 0}})}]

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            assignment = self._assignment(context.assignment, context.scope)
            entries = {item['name']: item for item in self.catalog(context)}
            if tool_name not in entries:
                raise ContractError('tool_not_available_to_monitor_role')
            arguments = plain(arguments)
            validate_schema(arguments, entries[tool_name]['input_schema'])
            if tool_name == 'progress.observe':
                if not set(arguments['requested_fields']) <= set(assignment['requested_fields']):
                    raise ContractError('monitor_observation_expands_requested_fields')
                snapshot = self.services.observe_progress(assignment['target_handle'], arguments['requested_fields'], context.scope, permitted_committed_record_types=assignment['permitted_committed_record_types'], operation_key=operation_key, **native_observation_options(arguments['native_operation'], context) if 'native_operation' in arguments else {})
                if inspect.isawaitable(snapshot):
                    snapshot = await snapshot
            else:
                snapshot = self._snapshot(context, arguments['progress_ref'])
            if tool_name == 'progress.log':
                if arguments['log_index'] >= len(snapshot['log_windows']):
                    raise ContractError('monitor_log_window_unavailable')
                window = snapshot['log_windows'][arguments['log_index']]
                source = self.services.read_record(window['source_ref'])
                representation = next((name for name, key in (('original', 'artifact_ref'), ('text', 'text_ref'), ('stdout', 'stdout_ref'), ('stderr', 'stderr_ref')) if source.get(key) == window['artifact_ref']), None)
                if representation is None:
                    raise ContractError('progress_log_source_artifact_mismatch')
                if window['start_byte'] == window['end_byte']:
                    result = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': {'source_ref': window['source_ref'], 'artifact_ref': window['artifact_ref'], 'start': window['start_byte'], 'end': window['end_byte'], 'text': ''}}
                else:
                    result = self.services.execute_tool('source.read', {'source_ref': window['source_ref'], 'representation': representation, 'offset': window['start_byte'], 'limit': window['end_byte'] - window['start_byte']}, scope=context.scope, operation_key=operation_key)
                    if inspect.isawaitable(result):
                        result = await result
                return {**plain(result), 'progress_refs': [snapshot['progress_ref']]}
            committed = [ref for ref in snapshot['committed_record_refs'] if self.services.read_record(ref)['record_type'] in assignment['permitted_committed_record_types']]
            return {'status': 'completed', 'operation_ref': identity('operation', {'key': operation_key, 'name': tool_name, 'arguments': arguments}), 'record_refs': committed, 'changed_record_refs': [], 'progress_refs': [snapshot['progress_ref']], 'result': snapshot}
        except ContractError as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'progress_refs': [], 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **({'detail': error.detail} if error.detail else {})}}
