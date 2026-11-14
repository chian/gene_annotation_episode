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
from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import (recorded_estimate, recorded_forecasts, validate_recorded_estimates,
    report_source as resource_report_source)


from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import obj, reference, CHECKED_STATUS_SCHEMA, RESULT_PROGRESS_SCHEMA, _result_progress, _binding

def _query(store, scope, query_ref):
    from gene_annotation_episode.episodic_workflow.root.library.homology_query import protein_query
    return protein_query(store,scope,query_ref,error_code='job_query_must_be_protein_of_assigned_target')

def prospective_execution_classes(self, store, scope):
    """Caller-resource configurations for actual eligible protein records.

    Reading this inventory does not translate a sequence, choose work,
    create an order, or launch anything. It is recomputed for later
    decisions so newly acquired protein records can become visible.
    """
    return list({value['execution_class'].ref: value['execution_class']
                 for value in self.prospective_execution_options(store, scope)}.values())

def prospective_execution_options(self, store, scope):
    """Local selectable operands and their statistical class, never a choice.

    Query identity stays in the episode's local configuration inventory;
    it is not added to shared run statistics or credited as a finding.
    """
    if self.statistics is None:
        return []
    options = []
    offset = 0
    while True:
        page = store.query_records('subject', scope=scope, offset=offset, limit=100)
        for candidate in page['records']:
            try:
                query = self._query(store, scope, candidate['id'])
                symbols = artifact_path(store, query['sequence_ref']).read_text()
            except (ValueError, KeyError, OSError, ContractError):
                continue
            for cpu in range(1, self.jobs.config['max_cpu']+1):
                for mode in self.jobs.search_modes:
                    execution_class = self.statistics.execution_class_for_query(self.jobs,
                        query_fasta='>query\n'+symbols+'\n', cpu=cpu, search_mode=mode)
                    options.append({'query_ref': query['id'], 'cpu': cpu,
                        'search_mode': mode, 'execution_class': execution_class})
        if page['next_offset'] is None:
            return options
        offset = page['next_offset']

def assignment(source):
    return source.request.message.as_record()['job_assignment']

def working_state(self, source):
    # No implicit live poll, scientific state dump or private child history.
    return {'role': source.path[-1][0], 'assignment': self.assignment(source)}

def resolve(self, store, scope, value, namespace, *, assignment=None):
    if assignment is not None and namespace=='subject' and value==assignment.get('query_ref'):
        # In a native-result contract this is the bound algorithm operand,
        # which may be an external protein reference. It does not become
        # an original annotation target or authorize another subject.
        try:
            self._query(store,scope,value)
        except (ValueError,KeyError,ContractError):
            return False
        return True
    if assignment is not None and (
            namespace in {None, 'homology_job'} and value == assignment['job_ref']
            or namespace in {None, 'job_sample'}
            and self.recorded_sample(store, value, assignment) is not None):
        # This exact assignment and returned sample were already admitted
        # and recorded. A later registry outage cannot change their identity.
        try:
            self._query(store, scope, assignment['query_ref'])
        except (ValueError, KeyError, ContractError):
            return False
        return True
    if namespace in {'job_execution_estimate', 'execution_class', 'execution_expectation', 'execution_proposal'}:
        estimate = recorded_estimate(store, value, assignment['job_ref'] if assignment else None,
                                     namespace=namespace)
        if estimate is None:
            return False
        if estimate['job_ref'] is None or assignment is None and namespace != 'job_execution_estimate':
            # Typed statistical configuration references carry no job
            # identity. Check the actual in-scope resource configuration;
            # retain the recorded snapshot even after history advances.
            try:
                return estimate['execution_class_ref'] in {
                    execution_class.ref for execution_class in self.prospective_execution_classes(store, scope)}
            except (ValueError, KeyError, OSError, ContractError):
                return False
        try:
            query_ref = (assignment['query_ref'] if assignment is not None
                and estimate['job_ref'] == assignment['job_ref']
                else self.jobs._row(estimate['job_ref'])['query_ref'])
            self._query(store, scope, query_ref)
        except (ValueError, KeyError, ContractError, sqlite3.Error):
            return False
        return True
    try:
        if not self.jobs.resolve(value, namespace):
            return False
        if value == self.jobs.config['registry_ref']:
            return True
        if self.jobs.resolve(value, 'homology_job'):
            job_ref = value
        elif self.jobs.resolve(value, 'job_sample'):
            job_ref = self.jobs.db.execute('SELECT job_ref FROM samples WHERE sample_ref=?', (value,)).fetchone()[0]
        else:
            row = self.jobs.db.execute('SELECT job_ref FROM handoffs WHERE receipt_ref=?', (value,)).fetchone()
            if row is None:
                return False
            job_ref = row[0]
        if assignment is not None and job_ref != assignment['job_ref']:
            return False
        self._query(store, scope, self.jobs._row(job_ref)['query_ref'])
    except (ValueError, KeyError, ContractError, sqlite3.Error):
        return False
    return True

def latest_sample(self, source, *, include_inherited=False):
    row = source.workflow.store.db.execute('''SELECT json_extract(result,'$.result')
        FROM runtime_actions WHERE run_id=? AND episode_id=?
        AND json_extract(result,'$.operational_sample_ref') IS NOT NULL
        ORDER BY decision_index DESC LIMIT 1''', (source.workflow.run_id, source.episode_id)).fetchone()
    if row is not None:
        return json.loads(row[0])
    prior = self.assignment(source).get('prior_samples', []) if include_inherited else []
    return deepcopy(prior[-1]) if prior else None

def recorded_sample(store, sample_ref, assignment):
    for sample in assignment.get('prior_samples', []):
        if sample['sample_ref'] == sample_ref and sample['job_ref'] == assignment['job_ref']:
            return deepcopy(sample)
    row = store.db.execute('''SELECT json_extract(result,'$.result') FROM runtime_actions
        WHERE json_extract(result,'$.operational_sample_ref')=?
        AND json_extract(result,'$.result.job_ref')=?
        AND json_extract(result,'$.status')='completed' LIMIT 1''',
        (sample_ref, assignment['job_ref'])).fetchone()
    return json.loads(row[0]) if row is not None else None

def latest_checked_status(self, source):
    assignment = self.assignment(source)
    row = source.workflow.store.db.execute('''SELECT json_extract(result,'$.result.sample'),
        json_extract(result,'$.result.checked_at_unix_seconds') FROM runtime_actions
        WHERE run_id=? AND episode_id=?
        AND json_extract(action,'$.tool')='homology.check_handoff'
        AND json_extract(result,'$.status')='completed'
        AND json_extract(result,'$.result.sample.job_ref')=?
        AND json_extract(result,'$.result.sample.registry_ref')=?
        ORDER BY decision_index DESC LIMIT 1''', (source.workflow.run_id, source.episode_id,
            assignment['job_ref'], self.jobs.config['registry_ref'])).fetchone()
    return ({'checked_at_unix_seconds': row[1], **json.loads(row[0])}
            if row is not None else None)

