"""Private report_fields responsibility with original returned-value semantics."""
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

class APIResourceReportFields:
    def fact_sources(self, role):
        if role != 'launch_api':
            raise ValueError('fixed_resource_role_required')
        values = {'execution_handoff': {'type': ['object', 'null'], 'meaning': 'The latest original usable received or own selected check when exactly one physical execution is known; null for zero or several identities. No new receiving check occurs at closure.', 'report_schema': {**_nullable(HANDOFF_SCHEMA), 'x-source': 'execution_handoff'}}, 'execution_handoffs': {'type': 'array', 'meaning': 'For each distinct registry and execution handle, the available usable check with latest original checked_at, in identity order. This records available facts without selecting a resource or rechecking it.', 'report_schema': {**_array(HANDOFF_SCHEMA), 'x-source': 'execution_handoffs'}}}
        for adapter in self.adapters.values():
            for name, definition in adapter.fact_sources('launch_api').items():
                if name in values and values[name] != definition:
                    raise ValueError('resource_fact_definition_conflict:' + name)
                values[name] = definition
        return values

