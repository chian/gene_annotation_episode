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
from gene_annotation_episode.episodic_workflow.root.library.resource_message import _Message
from gene_annotation_episode.episodic_workflow.root.resource_episodes import ResourceEpisodes
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_family import HomologyEpisodes
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import _result_progress
from gene_annotation_episode.episodic_workflow.root.library.homology_resource_assignment import HomologyResourceAssignment
from gene_annotation_episode.episodic_workflow.root.library.homology_resource_operations import HomologyResourceOperations
from gene_annotation_episode.episodic_workflow.root.library.homology_resource_custody import HomologyResourceCustody
from gene_annotation_episode.episodic_workflow.root.library.homology_resource_returns import HomologyResourceReturns
from gene_annotation_episode.episodic_workflow.root.library.homology_resource_progress import HomologyResourceProgress

class HomologyResourceAdapter(HomologyResourceAssignment, HomologyResourceOperations, HomologyResourceCustody, HomologyResourceReturns, HomologyResourceProgress):
    def __init__(self, homology_episodes, store, journal, resource_estimator=None):
        if type(homology_episodes) is not HomologyEpisodes:
            raise TypeError('explicit_homology_episode_binding_required')
        self.homology = homology_episodes
        self.store, self.journal = (store, journal)
        self.information = ResourceInformation(store, run_id=journal.run_id, jobs=homology_episodes.jobs)
        self.resource_estimator = resource_estimator
        statistics = homology_episodes.statistics
        self.resource_id = statistics.resource_id if statistics is not None else 'registry-local:' + homology_episodes.jobs.config['registry_ref']
        provider = getattr(homology_episodes, 'native_event_provider', None)
        if provider is not None and provider.resource_id != self.resource_id:
            raise ValueError('native_event_resource_binding_mismatch')
        self.record_selection = None

    def bind_record_selection(self, callback):
        self.record_selection = callback

    def as_record(self):
        return {'version': 'root_homology_resource_adapter_v1', 'resource_id': self.resource_id, 'resource_identity_kind': 'physical_binding' if self.homology.statistics else 'logical_registry', 'homology': self.homology.as_record(), 'resource_estimator': None if self.resource_estimator is None else self.resource_estimator.as_record()}
