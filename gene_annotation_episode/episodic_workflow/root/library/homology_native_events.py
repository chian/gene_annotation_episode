"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
from copy import copy, deepcopy
import json
import math
import sqlite3
import subprocess
from collections.abc import Mapping
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import REFERENCE_FORMATS, ReportBoundaryError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
from gene_annotation_episode.episodic_workflow.root.library.homology_job_contracts import HANDOFF_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.homology_job_status_contracts import SAMPLE_SCHEMA, STATUS_SCHEMA
from gene_annotation_episode.episodic_workflow.root.homology_results import HomologyResults
from gene_annotation_episode.episodic_workflow.root.library.native_phmmer_inputs import NativePhmmerInput
from gene_annotation_episode.episodic_workflow.root.library.homology_result_coverage import recorded_coverage
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.library.monitoring_credit import EXECUTION_OBSERVATION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import recorded_estimate, recorded_forecasts, validate_recorded_estimates, report_source as resource_report_source
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import obj, reference, CHECKED_STATUS_SCHEMA, RESULT_PROGRESS_SCHEMA, _result_progress, _binding

def with_native_events(self, provider):
    """A host-local view; the caller's binding/descriptor stays unchanged."""
    from gene_annotation_episode.episodic_workflow.root.native_events import NativeEventProvider
    if type(provider) is not NativeEventProvider:
        raise TypeError('typed_native_event_provider_required')
    if self.statistics is not None and self.statistics.resource_id != provider.resource_id:
        raise ValueError('native_event_resource_identity_conflict')
    view = copy(self)
    view._custody = copy(self._custody)
    view.native_event_provider = provider
    return view

def recover_native_events(self):
    summary = {}
    if self.native_event_provider is not None:
        for value in self.jobs.recover_native_events(native_event_provider=self.native_event_provider):
            summary[value['state']] = summary.get(value['state'], 0) + 1
    return summary

def bind_job_native_events(self, source, job_ref):
    provider = self.native_event_provider
    if provider is None:
        return None
    if source.workflow.run_id != provider.run_id:
        raise ValueError('native_event_run_identity_conflict')
    original = self.jobs.native_event_binding(job_ref)
    if original is None and (self.jobs._handle(job_ref).path.exists() or self.jobs._row(job_ref)['submission_requested']):
        return None
    return provider.for_job(owner_episode_id=source.episode_id, job_ref=job_ref, registry_ref=self.jobs.config['registry_ref'], original_binding=original)

def recover_statistics(self):
    summary = {}
    if self.statistics is not None:
        for value in self.jobs.recover_statistics():
            summary[value['state']] = summary.get(value['state'], 0) + 1
    return summary
