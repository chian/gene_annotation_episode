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

class HomologyResourceProgress:
    def credit_view(self, context, receiver_selection):
        source = self._legacy(context)
        if source is None:
            raise ValueError('explicit_role_credit_binding_required:' + context.role)
        return self.homology.implementation_for(source.path[-1][0]).credit_view(source)

    def decision_context(self, context):
        statistics = self.homology.statistics
        if statistics is None or self.resource_estimator is None:
            return {'resource_tool_estimates': []}
        from gene_annotation_episode.episodic_workflow.root.execution_expectations import capture_execution_scopes
        source = self._legacy(context)
        if source is not None:
            assignment = self.homology.assignment(source)
            execution_class = statistics.execution_class(self.homology.jobs, self.homology.jobs._row(assignment['job_ref']))
            captured = capture_execution_scopes(statistics.history_path, [execution_class], assigned_execution_class_ref=execution_class.ref)
            estimates = self.resource_estimator.estimate(captured, job_ref=assignment['job_ref'], sample=self.homology.latest_sample(source))
        else:
            job = plain(context.assignment).get('job_request', {})
            if 'existing_job_ref' in job:
                row = self.homology.jobs._row(job['existing_job_ref'])
                self.homology._query(self.store, plain(context.scope), row['query_ref'])
                execution_class = statistics.execution_class(self.homology.jobs, row)
                captured = capture_execution_scopes(statistics.history_path, [execution_class], assigned_execution_class_ref=execution_class.ref)
                return {'resource_tool_estimates': self.resource_estimator.estimate(captured, job_ref=row['job_ref'])}
            if 'query_ref' not in job or 'cpu' not in job:
                return {'resource_tool_estimates': []}
            from gene_annotation_episode.materials import artifact_path
            query = self.homology._query(self.store, plain(context.scope), job['query_ref'])
            sequence = artifact_path(self.store, query['sequence_ref']).read_text()
            execution_class = statistics.execution_class_for_query(self.homology.jobs, query_fasta='>query\n' + sequence + '\n', cpu=job['cpu'], search_mode=job.get('search_mode', 'native_defaults'))
            captured = capture_execution_scopes(statistics.history_path, [execution_class])
            estimates = self.resource_estimator.estimate_context(captured)
        return {'resource_tool_estimates': estimates}
