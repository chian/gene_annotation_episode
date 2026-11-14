"""Instruction-led Launch roles using the ordinary episode tool-action loop.

The command executor supplies transport and immutable factual receipts. The LLM
chooses shell code, scripts, environment, recovery and subsequent actions.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a102.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a102.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.a102.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a102.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a102.practical_execution_records import ASSIGNMENT_SCHEMA, assess_validations, validate_assignment
from gene_annotation_episode.episodic_workflow.root.a102.practical_execution_state import PracticalState
from gene_annotation_episode.episodic_workflow.root.a102.terminal_execution import TerminalExecution, digest
VERSION = 'terminal_execution_episode_v1'
ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}

def operation_catalog(kind):
    """General execution capability, identical for every resource."""
    if kind not in {'local', 'hpc'}:
        raise ValueError('execution_resource_kind_invalid')
    return [{'name': 'exec_command', 'description': 'Execute the shell command you write on the assigned resource. Use normal shell/file tools to inspect files, author scripts, prepare an environment, run software, or submit/observe the actual job as needed. Returns its actual output and saved action receipt. workdir and env apply to this command; select them explicitly on each action.', 'input_schema': {'type': 'object', 'properties': {'cmd': {'anyOf': [{'type': 'string', 'minLength': 1}, {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]}, 'workdir': {'type': 'string', 'minLength': 1}, 'target': {'type': 'string', 'enum': ['resource', 'coordinator'], 'description': 'Assigned resource (default), or local coordinator run directory for input-file work.'}, 'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}}, 'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}]
