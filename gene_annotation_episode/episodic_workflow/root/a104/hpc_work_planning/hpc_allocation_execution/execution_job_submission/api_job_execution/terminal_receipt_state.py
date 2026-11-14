"""Instruction-led Launch roles using the ordinary episode tool-action loop.

The command executor supplies transport and immutable factual receipts. The LLM
chooses shell code, scripts, environment, recovery and subsequent actions.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a104.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import ASSIGNMENT_SCHEMA, assess_validations, validate_assignment
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import PracticalState
from gene_annotation_episode.episodic_workflow.root.a104.library.native_terminal_transport import TerminalExecution, digest
VERSION = 'terminal_execution_episode_v1'
ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}

def operation_catalog(kind):
    """General execution capability, identical for every resource."""
    if kind not in {'local', 'hpc'}:
        raise ValueError('execution_resource_kind_invalid')
    return [{'name': 'exec_command', 'description': 'Execute the shell command you write on the assigned resource. Use normal shell/file tools to inspect files, author scripts, prepare an environment, run software, or submit/observe the actual job as needed. Returns its actual output and saved action receipt. workdir and env apply to this command; select them explicitly on each action.', 'input_schema': {'type': 'object', 'properties': {'cmd': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]}, 'workdir': {'type': 'string', 'minLength': 1}, 'target': {'type': 'string', 'enum': ['resource', 'coordinator'], 'description': 'Assigned resource (default), or local coordinator run directory for input-file work.'}, 'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}}, 'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}]

class TerminalExecutionBehavior:

    def __init__(self, services, *, directory, resources, store=None, initial_information=None):
        self.services, self.directory, self.store = (services, Path(directory), store)
        self.resources = json.loads(json.dumps(plain(resources), allow_nan=False))
        if not self.resources or not set(self.resources) <= {'local', 'hpc'}:
            raise ValueError('explicit_execution_resources_required')
        self.initial_information = plain(initial_information or {})
        if not set(self.initial_information) <= set(self.resources):
            raise ValueError('initial_inventory_resource_not_bound')
        self._states = {}

    def _operations(self, kind):
        from gene_annotation_episode.episodic_workflow.root.a104.terminal_scientific_evidence import terminal_artifact_paths
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
            from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store, context.run_id).resolve(context, reference, namespace)
        return namespace == 'practical_receipt' and reference in {digest(row) for row in self.state(context).receipts()}
