"""Private resource_selection responsibility with original configured behavior."""
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

class HPCResourceResourceSelection:
    def capabilities(self, context=None):
        if context is not None and context.role != 'launch_hpc':
            raise ValueError('fixed_resource_context_required')
        'Include unbound declarations accurately, but never offer their tools.'
        values = {}
        for capability in self.services.capabilities():
            value = _validate(capability, CAPABILITY_SCHEMA)
            if value['resource_id'] not in self.adapters:
                value['tool_names'] = []
            values[value['resource_id']] = value
        for adapter in self.adapters.values():
            value = _validate(adapter.capability(), CAPABILITY_SCHEMA)
            if value['resource_id'] != adapter.resource_id:
                raise ValueError('resource_capability_identity_mismatch')
            if context is not None and True and (context.assignment.get('resource_selection', {}).get('resource_id') == adapter.resource_id):
                bound = {tool['name'] for tool in adapter.catalog(context)}
                if not set(value['tool_names']) <= bound:
                    raise ValueError('resource_capability_tool_not_bound')
            values[value['resource_id']] = value
        return tuple(values.values())

