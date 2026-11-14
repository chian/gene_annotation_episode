"""Private original A104 LocalExecution service native_tool_actions."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import assess_validations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.library.native_terminal_transport import digest
from .native_tool_contracts import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import validate_schema

class LocalExecutionNativeToolActions:

    def catalog(self, context):
        return operation_catalog(self._assignment(context)['resource_kind'])

    async def execute(self, context, tool_name, arguments, operation_key):
        arguments = plain(arguments)
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_tool_not_available')
            validate_schema(arguments, catalog[tool_name]['input_schema'])
            operations = self._operations(context.assignment['resource_kind'])
            operations.validate_action(plain(context.assignment), tool_name, arguments)
        except (ValueError, TypeError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
        state = self.state(context)
        intent = state.begin(operation_key, tool_name, arguments)
        if intent['state'] == 'completed':
            receipt = intent['receipt']
        else:
            try:
                outcome, _ = await operations.execute(state, tool_name, arguments, operation_key)
            except (ValueError, TypeError, OSError, AcquisitionError) as error:
                outcome = {'facts': {}, 'native_outcome': {'failure': {'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
            from gene_annotation_episode.episodic_workflow.root.a104.terminal_scientific_evidence import finalize_scientific_command
            outcome = finalize_scientific_command(plain(context.assignment), arguments, outcome)
            before = state.context()
            after = deepcopy(before)
            if arguments.get('target', 'resource') == 'resource' and Path(arguments['workdir']).is_relative_to(context.assignment['workspace']):
                after.update({'cwd': arguments['workdir'], 'environment': arguments['env']})
            after['revision'] += int(any((after[name] != before[name] for name in ('cwd', 'environment'))))
            validations = assess_validations(plain(context.assignment), outcome, after, tool_name=tool_name)
            receipt = state.finish(operation_key, outcome, validations, context_after=after)
        references = []
        if self.store is not None:
            from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
            references.append(PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt))
        return {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'operation_ref': digest(operation_key), 'result': receipt}
