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

class APIResourceOperations:
    def catalog(self, context):
        if context.role != 'launch_api':
            raise ValueError('fixed_resource_context_required')
        tools = [{'name': 'resource.capabilities', 'description': 'Read actual capability availability and configured resource information; this does not select or submit work.', 'input_schema': obj({})}]
        tools.extend(self._adapter(context.assignment).catalog(context))
        return tools

    async def execute(self, context, tool_name, arguments, operation_key):
        if context.role != 'launch_api':
            raise ValueError('fixed_resource_context_required')
        catalog = {item['name']: item for item in self.catalog(context)}
        if tool_name not in catalog:
            raise ValueError('tool_not_owned_by_resource_role')
        arguments = _validate(arguments, catalog[tool_name]['input_schema'])
        if tool_name == 'resource.capabilities':
            return _outcome({'capabilities': list(self.capabilities())})
        if tool_name == 'resource.inspect':
            reference = arguments['resource_id']
            capability = next((value for value in self.capabilities() if value['resource_id'] == reference), None)
            if capability is None:
                return _outcome(failure=_failure('resource_not_bound', [reference]))
            code = _availability_failure(capability)
            if code is None and reference not in self.adapters:
                code = 'resource_not_bound'
            return _outcome({'capability': capability}, _failure(code, [reference]) if code else None)
        if tool_name == 'resource.check_handoff':
            handoff = arguments['handoff']
            try:
                adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                callback = getattr(adapter, 'check_handoff', None)
                if callback is None:
                    return _outcome(failure=_failure('receiving_interface_unavailable'))
                value = callback(context, handoff, operation_key)
                return await value if inspect.isawaitable(value) else value
            except (ValueError, KeyError, OSError, sqlite3.Error) as error:
                if str(error) == 'resource_information_identity_conflict':
                    raise
                return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
        adapter = self._adapter(context.assignment)
        return await adapter.execute(context, tool_name, arguments, operation_key)
