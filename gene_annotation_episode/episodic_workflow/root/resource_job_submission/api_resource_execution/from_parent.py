"""Private from_parent responsibility with original configured behavior."""
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

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, plain

from gene_annotation_episode.episodic_workflow.root.episode_bindings import reference_in_context

from gene_annotation_episode.episodic_workflow.root.library.homology_result_coverage import recorded_coverage

from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import recorded_forecasts

from gene_annotation_episode.episodic_workflow.root.resource_records import ROLES, RESOURCE_ROLES, LAUNCH_VERSION, RESULTS_VERSION, FAILURE_CODES, ALLOCATION_SCHEMA, SELECTION_SCHEMA, INPUT_VERSION_SCHEMA, CAPABILITY_SCHEMA, FAILURE_SCHEMA, RECEIVER_SCHEMA, HANDOFF_SCHEMA, LAUNCH_SCHEMA, RESULTS_SCHEMA, _string, _reference, _array, _nullable, _validate

from gene_annotation_episode.episodic_workflow.root.library.resource_information import ResourceInformation

from gene_annotation_episode.launch_instructions import validate_selection

from gene_annotation_episode.local_resources import LocalResources
from gene_annotation_episode.episodic_workflow.root.resource_records import obj
from gene_annotation_episode.episodic_workflow.root.library.resource_outcomes import _failure, _outcome, _availability_failure

class APIResourceParentAssignment:
    def assignment_schema(self, role):
        if role != 'launch_api':
            raise ValueError('fixed_resource_role_required')
        self.credit_kind('launch_api')
        return deepcopy(LAUNCH_SCHEMA)

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        if role != 'launch_api':
            raise ValueError('fixed_resource_role_required')
        selected = plain(selection)
        schema = self.assignment_schema('launch_api')
        selected = {key: selected[key] for key in schema['properties'] if key in selected}
        selected = _validate(selected, schema)
        if parent.role == 'launch' and False:
            raise ValueError('resource_child_role_not_owned_by_launch')
        if parent.role == 'launch':
            inherited = plain(parent.assignment)
            inherited.pop('adapter_assignment', None)
            for key in LAUNCH_SCHEMA['properties']:
                if key == 'launch_instructions':
                    self._require_launch_child_instruction_pins(inherited.get(key), selected.get(key))
                    continue
                if key != 'resource_selection' and selected[key] != inherited[key]:
                    raise ValueError('resource_assignment_conflict')
            if inherited['resource_selection'] is not None and selected['resource_selection'] != inherited['resource_selection']:
                raise ValueError('resource_selection_conflict')
        if selected['resource_selection'] is None:
            raise ValueError('explicit_resource_selection_required')
        capability = next((value for value in self.capabilities() if value['resource_id'] == selected['resource_selection']['resource_id']), None)
        if capability is None or capability['kind'] != {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}['launch_api'] or (not self._permitted(selected, capability)):
            raise ValueError('resource_selection_conflict')
        return self._adapter(selected).prepare_assignment(parent, 'launch_api', selected, scope, operation_key)
