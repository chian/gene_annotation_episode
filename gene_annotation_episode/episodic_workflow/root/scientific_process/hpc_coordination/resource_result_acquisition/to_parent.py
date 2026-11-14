"""Private to_parent responsibility with original returned-value semantics."""
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

class ResourceAcquisitionParentReport:
    def validate_report(self, context, form, original_schema):
        if context.role != 'results':
            raise ValueError('fixed_resource_context_required')
        adapters = (self._adapter(context.assignment),)
        for adapter in adapters:
            adapter.validate_report(context, form, original_schema)
        facts = self.facts(context, {})

        def visit(value, schema):
            if schema.get('x-source') in {'execution_handoff', 'execution_handoffs'}:
                if plain(value) != facts[schema['x-source']]:
                    raise ReportBoundaryError('Resource handoff differs from selected recorded check', code='resource_handoff_fact_mismatch')
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in schema.get('properties', {}):
                        visit(child, schema['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in schema:
                for child in value:
                    visit(child, schema['items'])
        visit(form, original_schema)
