"""Private report_delivery responsibility with original returned-value semantics."""
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

class ResourceAcquisitionReportDelivery:
    def facts(self, context, completion_snapshot):
        if context.role != 'results':
            raise ValueError('fixed_resource_context_required')
        values = {'execution_handoff': None, 'execution_handoffs': []}
        adapters = [self._adapter(context.assignment)]
        for adapter in adapters:
            facts = adapter.facts(context, completion_snapshot)
            for key, value in facts.items():
                if key == 'execution_handoffs':
                    values[key].extend(value)
                    continue
                if key == 'execution_handoff':
                    continue
                if value is not None:
                    values[key] = value
                else:
                    values.setdefault(key, None)
        identities = {(item['resource_selection']['capability_binding_ref'], item['execution_handle']): item for item in values['execution_handoffs']}
        values['execution_handoffs'] = [identities[key] for key in sorted(identities)]
        values['execution_handoff'] = values['execution_handoffs'][0] if len(identities) == 1 else None
        return values

