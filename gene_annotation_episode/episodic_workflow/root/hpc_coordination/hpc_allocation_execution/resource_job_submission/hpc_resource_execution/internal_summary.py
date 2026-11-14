"""Private internal_summary responsibility with original configured behavior."""
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

class HPCResourceInternalSummary:
    def decision_context(self, context, current_view):
        if context.role != 'launch_hpc':
            raise ValueError('fixed_resource_context_required')
        values = {'role': 'launch_hpc', 'assignment': plain(context.assignment), 'resource_capabilities': list(self.capabilities())}
        adapters = [self._adapter(context.assignment)]
        estimates = []
        for adapter in adapters:
            callback = getattr(adapter, 'decision_context', None)
            if callback is not None:
                estimates.extend(callback(context).get('resource_tool_estimates', []))
        values['resource_tool_estimates'] = estimates
        return values
