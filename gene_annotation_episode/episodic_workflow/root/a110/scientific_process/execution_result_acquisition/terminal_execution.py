"""Instruction-led Launch roles using the ordinary episode tool-action loop.

The command executor supplies transport and immutable factual receipts. The LLM
chooses shell code, scripts, environment, recovery and subsequent actions.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a110.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.a110.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import ASSIGNMENT_SCHEMA, assess_validations, validate_assignment
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import PracticalState
from gene_annotation_episode.episodic_workflow.root.a110.terminal_execution import TerminalExecution, digest
VERSION = 'terminal_execution_episode_v1'
ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_operation_information import operation_catalog

class TerminalExecutionBehavior:

    def __init__(self, services, *, directory, resources, store=None, initial_information=None, flux_balance_input_reader=None):
        self.services, self.directory, self.store = (services, Path(directory), store)
        self.resources = json.loads(json.dumps(plain(resources), allow_nan=False))
        if not self.resources or not set(self.resources) <= {'local', 'hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information = plain(initial_information or {})
        if not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        self._states = {}

    def _operations(self, kind):
        from gene_annotation_episode.episodic_workflow.root.a110.terminal_scientific_evidence import terminal_artifact_paths
        return TerminalExecution(self.resources[kind], coordinator_workspace=self.directory, artifact_selector=terminal_artifact_paths)

    def _assignment(self, context):
        assignment = validate_assignment(plain(context.assignment))
        kind = ROLE_KINDS.get(context.role)
        if assignment['resource_kind'] != kind or kind not in self.resources:
            raise ValueError('execution_resource_assignment_mismatch')
        self._operations(kind).validate_assignment(assignment)
        return assignment

    def _state_directory(self, context):
        return self.directory / 'practical-execution' / digest({'run_id': context.run_id, 'episode_id': context.episode_id})

    def initialize(self, context):
        assignment = self._assignment(context)
        directory = self._state_directory(context)
        state = PracticalState(directory, context.run_id, context.episode_id, assignment, **{} if (directory / 'assignment.json').is_file() else {'initial_outcome': {'facts': {}}, 'initial_validations': assess_validations(assignment, {'facts': {}}, assignment['initial_context'])})
        self._states[context.episode_id] = state
        return state

    def state(self, context):
        return self._states.get(context.episode_id) or self.initialize(context)

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
            from gene_annotation_episode.episodic_workflow.root.a110.terminal_scientific_evidence import finalize_scientific_command
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
            from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
            references.append(PracticalReceiptInformation(self.store, context.run_id).publish(context, receipt))
        return {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'operation_ref': digest(operation_key), 'result': receipt}

    def completion_for_action(self, context, operation_key):
        proof = self.state(context).completion_proof()
        return proof if proof is not None and proof['operation_key'] == operation_key else None

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(self.state(context).verify_completion)

    def fact_sources(self, role):
        return {'practical_completed': {'type': 'boolean', 'meaning': 'Whether original requested endpoint predicates have a saved validated completion.'}, 'practical_receipt_digests': {'type': 'array', 'meaning': 'Host-recorded digests of the original selected command receipts.'}, 'practical_receipt_refs': {'type': 'array', 'meaning': 'Original selected command, actual result and earned operational credit sources.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'practical_receipt'}, 'x-source': 'practical_receipt_refs'}}}

    def facts(self, context, completion_snapshot):
        state = self.state(context)
        references = []
        if self.store is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
            information = PracticalReceiptInformation(self.store, context.run_id)
            references = [information.publish(context, receipt) for receipt in state.receipts()]
        return {'practical_completed': state.completion_proof() is not None, 'practical_receipt_digests': [digest(receipt) for receipt in state.receipts()], 'practical_receipt_refs': references}

    def resolve(self, context, reference, namespace):
        if self.store is not None and isinstance(reference, str) and reference.startswith('source_'):
            from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store, context.run_id).resolve(context, reference, namespace)
        return namespace == 'practical_receipt' and reference in {digest(row) for row in self.state(context).receipts()}

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        facts = self.facts(context, {})
        for name, node in original_schema.get('properties', {}).items():
            source = node.get('x-source')
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')

    def credit_view(self, context, receiver_selection):
        return self.state(context).credit_view()
