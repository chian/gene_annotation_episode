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
from gene_annotation_episode.episodic_workflow.root.library.resource_custody import ResourceCustody

class ResourceEpisodes(ResourceCustody):
    def __init__(self, services, *, resource_adapters=(), contract_information_profile=None):
        self.services = services
        from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_INFORMATION_PROFILE
        if contract_information_profile not in (None, CONTRACT_INFORMATION_PROFILE):
            raise ValueError('unsupported_resource_contract_information_profile')
        self._contract_information_profile = contract_information_profile
        self.adapters = {}
        required = ('capability', 'as_record', 'prepare_assignment', 'catalog', 'execute', 'fact_sources', 'facts', 'resolve', 'validate_report', 'credit_view')
        for adapter in resource_adapters:
            if not isinstance(adapter.resource_id, str) or not adapter.resource_id or any((not callable(getattr(adapter, name, None)) for name in required)):
                raise TypeError('explicit_resource_adapter_required')
            if adapter.resource_id in self.adapters:
                raise ValueError('duplicate_resource_id')
            bind_selection = getattr(adapter, 'bind_record_selection', None)
            if bind_selection is not None:
                bind_selection(getattr(services, 'record_selection', None))
            self.adapters[adapter.resource_id] = adapter

    def configuration(self):
        return {'resource_adapters': [adapter.as_record() for adapter in self.adapters.values()],
                **({'contract_information_profile': self._contract_information_profile}
                   if self._contract_information_profile is not None else {})}

    def as_record(self):
        return {'version': 'root_resource_custody_v1', 'configuration': self.configuration()}
