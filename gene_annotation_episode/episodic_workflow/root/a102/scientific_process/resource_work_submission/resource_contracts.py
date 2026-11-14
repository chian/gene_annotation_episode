"""A102 resource launch binding for structural evidence operations.

``ResourceEpisode(services, resource_adapters=...)`` implements C7. Adapters
are explicit A102 caller bindings.

The persisted ``resource_launch_assignment_v1`` wraps C9 LaunchAssignmentV1
losslessly and adds ``adapter_assignment`` only after a resource is selected.
That field holds the existing immutable job assignment; it is not a selectable
replacement for the scientific parent's job, inputs, constraints or allocation.
``resource_results_assignment_v1`` carries handoff and requested_data_selector.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a102.communication import ReportBoundaryError, plain
from gene_annotation_episode.episodic_workflow.root.a102.domain import obj
from gene_annotation_episode.episodic_workflow.root.a102.episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.a102.resource_records import ROLES, RESOURCE_ROLES, LAUNCH_VERSION, RESULTS_VERSION, FAILURE_CODES, ALLOCATION_SCHEMA, SELECTION_SCHEMA, INPUT_VERSION_SCHEMA, CAPABILITY_SCHEMA, FAILURE_SCHEMA, RECEIVER_SCHEMA, HANDOFF_SCHEMA, LAUNCH_SCHEMA, RESULTS_SCHEMA, _string, _reference, _array, _nullable, _validate
from gene_annotation_episode.episodic_workflow.root.a102.launch_instructions import validate_selection
from gene_annotation_episode.episodic_workflow.root.a102.local_resources import LocalResources

def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references), 'diagnostic_ref': None, 'partial_record_refs': []}

def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs), 'changed_record_refs': [], 'result': value, 'feedback': failure}

def _availability_failure(capability):
    return {'unavailable': 'resource_unavailable', 'authentication_required': 'resource_authentication_required', 'unknown': 'resource_availability_unknown'}.get(capability['availability'])
from pathlib import Path
_AXIS_DIRECTORY = Path(__file__).resolve().parents[2]

def _binding_source_bytes():
    return b''.join((p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py'))))
