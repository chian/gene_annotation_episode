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

class ResourceCustody:
    def contract_information_profile(self, context):
        return self._contract_information_profile if context.role == 'launch' else None

    @staticmethod
    def _permitted(assignment, capability):
        constraints = assignment.get('constraints', {})
        selection = assignment.get('resource_selection')
        return (selection is None or (capability['resource_id'] == selection['resource_id'] and capability['kind'] == selection['kind'])) and ('allowed_resource_ids' not in constraints or capability['resource_id'] in constraints['allowed_resource_ids']) and ('allowed_kinds' not in constraints or capability['kind'] in constraints['allowed_kinds']) and ('resource_id' not in constraints or capability['resource_id'] == constraints['resource_id']) and ('kind' not in constraints or capability['kind'] == constraints['kind'])

    def _adapter(self, assignment):
        selection = assignment['handoff']['resource_selection'] if assignment.get('version') == RESULTS_VERSION else assignment.get('resource_selection')
        if selection is None or selection['resource_id'] not in self.adapters:
            raise ValueError('resource_not_bound')
        return self.adapters[selection['resource_id']]

    @staticmethod
    def _require_launch_child_instruction_pins(parent_selection, child_selection):
        """The resource launch parent owns the instruction pins it supplied."""
        parent_selection = validate_selection(parent_selection)
        child_selection = validate_selection(child_selection)
        if parent_selection is None:
            return
        if child_selection is None or child_selection['library_id'] != parent_selection['library_id']:
            raise ValueError('launch_instruction_inheritance_conflict')
        retained = {(row['entry_id'], row['section_id'], row['sha256']) for row in child_selection['sections']}
        if any(((row['entry_id'], row['section_id'], row['sha256']) not in retained for row in parent_selection['sections'])):
            raise ValueError('launch_instruction_inheritance_conflict')

    def received_form_references(self, context, form, schema, operation_key):
        references = []

        def visit(value, declared):
            source = declared.get('x-source')
            if source in {'execution_handoff', 'execution_handoffs'}:
                values = value if source == 'execution_handoffs' else [] if value is None else [value]
                for handoff in values:
                    adapter = self._adapter({'version': RESULTS_VERSION, 'handoff': handoff})
                    callback = getattr(adapter, 'received_form_references', None)
                    if callback is None:
                        raise ValueError('resource_information_handoff_proof_missing')
                    references.extend(callback(context, handoff, {'x-source': 'execution_handoff'}, operation_key))
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in declared:
                for child in value:
                    visit(child, declared['items'])
        visit(form, schema)
        return sorted(set(references))

    def initial_references(self, context):
        if context.role != 'results':
            return []
        callback = getattr(self._adapter(context.assignment), 'initial_references', None)
        return [] if callback is None else callback(context)
