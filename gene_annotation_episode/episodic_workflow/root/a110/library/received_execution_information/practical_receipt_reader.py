"""Exact own-axis practical receipt/state reads; no command execution binding."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.terminal_execution import TerminalExecution

from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import PracticalState

from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import assess_validations

from pathlib import Path

import json

from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}

from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import validate_assignment

from gene_annotation_episode.episodic_workflow.root.a110.terminal_execution import digest

class PracticalReceiptReader:

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

    def fact_sources(self, role):
        return {'practical_completed': {'type': 'boolean', 'meaning': 'Whether original requested endpoint predicates have a saved validated completion.'}, 'practical_receipt_digests': {'type': 'array', 'meaning': 'Host-recorded digests of the original selected command receipts.'}, 'practical_receipt_refs': {'type': 'array', 'meaning': 'Original selected command, actual result and earned operational credit sources.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'practical_receipt'}, 'x-source': 'practical_receipt_refs'}}}

    def resolve(self, context, reference, namespace):
        if self.store is not None and isinstance(reference, str) and reference.startswith('source_'):
            from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store, context.run_id).resolve(context, reference, namespace)
        return namespace == 'practical_receipt' and reference in {digest(row) for row in self.state(context).receipts()}
