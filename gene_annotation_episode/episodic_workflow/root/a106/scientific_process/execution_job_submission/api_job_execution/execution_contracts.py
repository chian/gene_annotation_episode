"""Private A106 AppService launch and selected intervention result binding."""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical, checked, digest, obj
from gene_annotation_episode.episodic_workflow.root.a106.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a106.practical_execution_records import validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.a106.resource_records import INPUT_VERSION_SCHEMA
VERSION = 'execution_episode_v1'
LAUNCH_VERSION = 'execution_launch_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'
ROLES = ('launch', 'launch_api', 'results')
KINDS = {'api': 'api'}
ROLE_KINDS = {'launch_api': 'api'}
TEXT = {'type': 'string', 'minLength': 1}
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})

def launch_operation_catalog():
    return [{'name': 'execution.capabilities', 'description': 'Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection.', 'input_schema': obj({})}]

def _outcome(result=None, *, references=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references), 'changed_record_refs': list(references), 'result': result, 'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}
from pathlib import Path
_AXIS_DIRECTORY = Path(__file__).resolve().parents[3]

def _binding_source_bytes():
    return b''.join((p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py'))))
