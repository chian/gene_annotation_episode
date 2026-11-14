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

from .acquisition import AcquisitionError
from .communication import REFERENCE_FORMATS, ReportBoundaryError
from .domain import ContractError
from .homology_jobs import HANDOFF_SCHEMA, SAMPLE_SCHEMA, STATUS_SCHEMA, HomologyJobs
from .homology_results import HomologyResults, NativePhmmerInput, recorded_coverage
from .local_jobs import LocalJobPolicy
from .materials import artifact_path
from .monitoring_credit import EXECUTION_OBSERVATION_SCHEMA
from .resource_estimation import (recorded_estimate, recorded_forecasts, validate_recorded_estimates,
    report_source as resource_report_source)


ROLES = ('job_launch', 'job_monitor', 'job_results')


def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def reference(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string',
            'format': 'reference', 'x-reference-namespace': namespace}


CHECKED_STATUS_SCHEMA = obj({'checked_at_unix_seconds': {'type': 'number', 'minimum': 0},
    **deepcopy(STATUS_SCHEMA['properties'])})


RESULT_PROGRESS_SCHEMA = obj({
    'snapshot_ref': reference('source'),
    'query_ref': reference('subject'),
    'execution_source_ref': reference('source'),
    'native_source_ref': reference('source'),
    'execution_context': {**obj({'job_ref': reference('homology_job'),
        'registry_ref': reference('execution_registry')}), 'type': ['object', 'null']},
    'status': {'type': 'string', 'enum': ['available', 'unavailable']},
    'parsed_row_count': {'type': ['integer', 'null'], 'minimum': 0},
    'acquired_row_count': {'type': ['integer', 'null'], 'minimum': 0},
    'acquired_ordinal_intervals': {'type': ['array', 'null'], 'items': {'type': 'array',
        'items': {'type': 'integer', 'minimum': 1}, 'minItems': 2, 'maxItems': 2}},
    'all_parsed_rows_acquired': {'type': ['boolean', 'null']},
    'parser_finished': {'type': ['boolean', 'null']},
    'native_error_count': {'type': ['integer', 'null'], 'minimum': 0},
    'parse_execution_failed': {'type': ['boolean', 'null']},
    'native_termination_seen': {'type': ['boolean', 'null']},
    'native_result_complete': {'type': ['boolean', 'null']},
})


def _result_progress(value):
    """Project actual coverage facts without passing an unrestricted error body."""
    return {key: (value['parse_execution_failure'] is not None
        if key == 'parse_execution_failed' else deepcopy(value[key]))
        for key in RESULT_PROGRESS_SCHEMA['properties']}


def _binding(callback):
    owner = callback if hasattr(callback, '__qualname__') else type(callback)
    return owner.__module__ + '.' + owner.__qualname__


class HomologyEpisodes:
    roles = ROLES

    def __init__(self, jobs: HomologyJobs, *, parser_policy: LocalJobPolicy,
                 credit_projector, credit_binding, monitoring_projector, monitoring_binding, statistics=None):
        if type(jobs) is not HomologyJobs or type(parser_policy) is not LocalJobPolicy:
            raise TypeError('explicit_homology_resources_required')
        if not callable(credit_projector) or not isinstance(credit_binding, dict) or not credit_binding:
            raise ValueError('explicit_operational_credit_binding_required')
        self.jobs, self.parser_policy, self._job_credit_calculator = jobs, parser_policy, credit_projector
        if not callable(monitoring_projector) or not isinstance(monitoring_binding, dict) or not monitoring_binding:
            raise ValueError('explicit_monitoring_credit_binding_required')
        self.monitoring_projector = monitoring_projector
        # The calculators are reusable functions. Each job episode owns its
        # binding and its selected role-specific invocation.
        self._role_credit_bindings = {
            'job_launch': json.loads(json.dumps(credit_binding, allow_nan=False)),
            'job_monitor': json.loads(json.dumps(monitoring_binding, allow_nan=False)),
            'job_results': json.loads(json.dumps(credit_binding, allow_nan=False)),
        }
        if statistics is not None:
            from .execution_recording import HomologyStatistics
            if type(statistics) is not HomologyStatistics:
                raise TypeError('typed_homology_statistics_binding_required')
        self.statistics = statistics
        self.native_event_provider = None

    def with_native_events(self, provider):
        """A host-local view; the caller's binding/descriptor stays unchanged."""
        from .native_events import NativeEventProvider
        if type(provider) is not NativeEventProvider:
            raise TypeError('typed_native_event_provider_required')
        if self.statistics is not None and self.statistics.resource_id != provider.resource_id:
            raise ValueError('native_event_resource_identity_conflict')
        view = copy(self)
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
        if original is None and (self.jobs._handle(job_ref).path.exists()
                or self.jobs._row(job_ref)['submission_requested']):
            # A new host setting cannot retrofit old work, including an
            # unconfirmed request whose original reservation is missing.
            return None
        return provider.for_job(owner_episode_id=source.episode_id, job_ref=job_ref,
            registry_ref=self.jobs.config['registry_ref'], original_binding=original)

    def as_record(self):
        return {'version': 'homology_episode_bindings_v4',
                'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config,
                'parser_policy': self.parser_policy.to_dict(),
                'job_credit_calculator': _binding(self._job_credit_calculator),
                'monitoring_projector': _binding(self.monitoring_projector),
                'role_credit_bindings': deepcopy(self._role_credit_bindings),
                'monitoring_projector_parameters': (self.monitoring_projector.as_record()
                    if callable(getattr(self.monitoring_projector, 'as_record', None)) else None),
                'statistics': None if self.statistics is None else self.statistics.as_record()}

    def recover_statistics(self):
        summary = {}
        if self.statistics is not None:
            # Startup needs dispositions, not an in-memory archive of closed
            # jobs. Each detailed receipt remains at its job-owned disk path.
            for value in self.jobs.recover_statistics():
                summary[value['state']] = summary.get(value['state'], 0) + 1
        return summary

    def instructions(self, role):
        responsibilities = {
            'job_launch': 'Establish the execution environment, prepare and submit the assigned detached job, and repair its usable monitoring handoff. Only your submit tool can launch this assigned job.',
            'job_monitor': 'Improve the requested understanding of the assigned job execution using actual observations. The job may continue after you yield. Repeated unchanged samples are not progress.',
            'job_results': 'Acquire and extract the requested native evidence, repair extraction problems where possible and return constrained result references. The parent owns scientific integration and annotation.'}
        return ('You own an iterative scoped job investigation in the shared method_loop. '
            + responsibilities[role] + ' Revise selected work from actual outcomes. '
            'Select one of your available ordinary tools. Only the configured yield controller '
            'owns continuation: no stop action, turn cap, forced sequence or work timeout. '
            'Use the parent-defined typed report form. Recorded execution facts come from '
            'declared x-source fields; do not invent them. Interpretive fields use only the '
            'parent-declared values and meanings. There is no separate report-composition call. '
            'Global execution expectations are statistical inputs, not scientific findings, '
            'task progress, another episode\'s yield history or instructions. '
            'Use episode.history for older own work; do not rerun work merely to see its output.'
            + (' monitoring_information_credit records execution information learned through your selected '
               'samples or handoff checks, independently of your current_credit binding. A completed '
               'duration remains timing information even when learned during launch or acquisition. '
               'The separate binding does not add itself to operational/scientific credit or choose continuation.'
               if self.has_information_channel(role) else ''))

    def fact_sources(self, role):
        if role not in ROLES:
            return {}
        handoff = {**deepcopy(HANDOFF_SCHEMA), 'type': ['object', 'null']}
        sample = {**deepcopy(SAMPLE_SCHEMA), 'type': ['object', 'null']}
        values = {
            'job_ref': (reference('homology_job'), 'The immutable assigned job, not an episode identity.'),
            'job_cpu': ({'type': 'integer', 'minimum': 1}, 'Assigned CPU threads selected by the parent and retained in the job; not measured consumption.'),
            'job_handoff': (handoff, 'A freshly functionally checked receiving-interface handoff, or null when unavailable.'),
            'job_handoff_state': ({'type': 'string', 'enum': ['usable', 'unavailable']}, 'Whether this closure established a usable receiving-interface handoff; no scientific completion claim.'),
            'job_handoff_failure': ({'type': ['string', 'null'], 'enum': [None,
                'job_not_submitted', 'submission_unconfirmed', 'native_handle_identity_mismatch',
                'receiving_interface_unavailable']}, 'The basic reason no usable handoff could be returned; null after a successful receiving-interface check.'),
            'job_sample': (sample, 'The last actual sample selected by this child, unchanged on replay; null if it selected none.')}
        if 'search_modes' in self.jobs.config:
            values['job_search_mode'] = ({'type': 'string', 'enum': list(self.jobs.search_modes)},
                'The immutable parent-selected search mode. Maximum sensitivity disables heuristic filters; it is not evidence of a specific function or a stronger significance threshold.')
        sources = {key: {'type': schema['type'], 'meaning': meaning,
                      'report_schema': {**schema, 'x-source': key}}
                for key, (schema, meaning) in values.items()}
        sources['resource_tool_estimates'] = resource_report_source()
        if role == 'job_launch':
            sources['job_checked_status'] = {
                'type': ['object', 'null'],
                'meaning': ('The status and timestamp of this child\'s last successful selected '
                    'homology.check_handoff action. This is the recorded check-time state, not a '
                    'fresh closure poll or a monitoring sample. Null if no selected check succeeded. '
                    'The parent decides what subsequent work this information warrants.'),
                'report_schema': {**deepcopy(CHECKED_STATUS_SCHEMA), 'type': ['object', 'null'],
                    'x-source': 'job_checked_status'}}
        if self.has_information_channel(role):
            sources['monitoring_findings'] = self.monitoring_projector.information_report_source()
            sources['monitoring_information_credit'] = {'type': 'number',
                'meaning': 'Monitoring information actually obtained by this episode; separate from operational/scientific score and duration estimates. It does not select the controller input.',
                'binding': self.monitoring_projector.as_record(),
                'report_schema': {'type': 'number', 'x-source': 'monitoring_information_credit'}}
        elif role == 'job_monitor' and callable(getattr(self.monitoring_projector, 'report_source', None)):
            sources['monitoring_findings'] = self.monitoring_projector.report_source()
        if role == 'job_results':
            sources['job_result_progress'] = {
                'type': ['object', 'null'],
                'meaning': ('Recorded acquisition coverage for the last native snapshot selected by this child. '
                    'Includes snapshot identity, native/parse completion, parsed/acquired row counts, '
                    'all_parsed_rows_acquired and explicit parse errors. A complete native result with '
                    'a finished error-free parser and zero parsed/acquired rows is a completed empty '
                    'search in the selected database, not evidence of a biological function. '
                    'Native ordinals are one-based; intervals are half-open. Acquiring a partial parsed prefix '
                    'is distinct from a complete native result. This is not scientific credit or completion. '
                    'Null when no snapshot was selected or its coverage could not be read.'),
                'report_schema': {**deepcopy(RESULT_PROGRESS_SCHEMA), 'type': ['object', 'null'],
                    'x-source': 'job_result_progress'}}
            sources['job_result_progress_failure'] = {
                'type': ['string', 'null'],
                'meaning': 'Basic coverage-read failure; null when no read failed. Native parse failures remain separate coverage facts.',
                'report_schema': {'type': ['string', 'null'], 'enum': [None,
                    'invalid_snapshot_or_scope', 'storage_failure', 'coverage_read_failed'],
                    'x-source': 'job_result_progress_failure'}}
        return sources

    def describe(self):
        return {role: {'report_facts': self.fact_sources(role), 'responsibility': self.instructions(role)}
                for role in ROLES}

    def commission_schemas(self, scientific_child):
        common = {key: deepcopy(value) for key, value in scientific_child['properties'].items()
                  if key != 'kind'}
        values = []
        for role in ROLES:
            operand = ({'query_ref': reference('subject'), 'cpu': {'type': 'integer', 'minimum': 1,
                'maximum': self.jobs.config['max_cpu'],
                'description': 'Select the CPU allocation for this query from the caller resources.'}} if role == 'job_launch'
                       else {'handoff': deepcopy(HANDOFF_SCHEMA)})
            if role == 'job_launch' and 'search_modes' in self.jobs.config:
                operand['search_mode'] = {'type': 'string', 'enum': list(self.jobs.search_modes),
                    'description': 'Parent selects the assigned search. native_defaults uses native heuristic filters; maximum_sensitivity disables all such filters (--max), at substantial runtime cost and possibly slight sensitivity improvement. It does not strengthen reported significance, establish homology or assign function. No duration transfer from another mode is assumed.'}
            if role == 'job_monitor':
                operand['prior_sample_refs'] = {'type': 'array', 'uniqueItems': True,
                    'items': reference('job_sample'),
                    'description': 'Actual prior samples the parent supplies as already-known execution information. Use [] when none is known. These are input facts, not new monitoring contributions or global history.'}
            commission = obj({'kind': {'type': 'string', 'const': 'job_child'},
                'role': {'type': 'string', 'const': role}, **common, **operand})
            commission['properties']['delay_seconds'] = {'type': 'number', 'minimum': 0,
                'description': 'Optional parent-chosen delay before this exact child starts. Choose from returned monitoring evidence and your yield estimate; no default cadence. The durable timer survives interruption/resume, does not select new work or add a controller observation. This one selected parent action waits and returns its child form; concurrent scheduling is later work.'}
            if role == 'job_monitor' or self.has_information_channel(role):
                if role != 'job_monitor':
                    commission['properties']['prior_sample_refs'] = {
                        'type': 'array', 'uniqueItems': True, 'items': reference('job_sample'),
                        'description': 'Optional actual prior samples already known to the parent for this assigned job. They seed execution knowledge without earning new information credit.'}
                commission['properties']['prior_checked_statuses'] = {
                    'type': 'array', 'uniqueItems': True, 'items': deepcopy(CHECKED_STATUS_SCHEMA),
                    'description': 'Optional already-known launch status facts received through the parent form. Each must exactly match a recorded successful selected handoff check of this assigned job and registry. They seed monitoring knowledge without becoming samples or new credit. Omission supplies none.'}
            values.append(commission)
            if role == 'job_launch':
                repair = deepcopy(commission)
                repair['properties'].pop('query_ref')
                repair['properties'].pop('cpu')
                repair['properties'].pop('search_mode', None)
                repair['properties']['existing_job_ref'] = {**reference('homology_job'),
                    'description': 'Commission a fresh iterative launch/repair investigation of this existing assigned job. It preserves its query, prepared inputs and native reservation; it does not create a replacement job.'}
                repair['required'] = [key for key in repair['required'] if key not in {'query_ref', 'cpu', 'search_mode'}] + ['existing_job_ref']
                values.append(repair)
        return values

    @staticmethod
    def _query(store, scope, query_ref):
        from .homology_query import protein_query
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

    def assign(self, store, role, selection, scope, *, operation_key):
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        if role == 'job_launch':
            if 'existing_job_ref' in selection:
                job = self.jobs._row(selection['existing_job_ref'])
                self._query(store, scope, job['query_ref'])
                assignment = {'job_ref': job['job_ref'], 'query_ref': job['query_ref'], 'cpu': job['cpu']}
            else:
                query = self._query(store, scope, selection['query_ref'])
                symbols = artifact_path(store, query['sequence_ref']).read_text()
                job_ref = self.jobs.order(query_ref=query['id'], query_fasta='>query\n'+symbols+'\n',
                                          cpu=selection['cpu'], operation_key=operation_key,
                                          search_mode=selection.get('search_mode'))
                assignment = {'job_ref': job_ref, 'query_ref': query['id'], 'cpu': selection['cpu']}
        else:
            handoff = deepcopy(selection['handoff'])
            job = self.jobs._row(handoff['job_ref'])
            self._query(store, scope, job['query_ref'])
            self.jobs.check_handoff(handoff)
            assignment = {'job_ref': handoff['job_ref'], 'query_ref': job['query_ref'], 'cpu': job['cpu'], 'handoff': handoff}
        if 'search_modes' in self.jobs.config:
            assignment['search_mode'] = self.jobs._row(assignment['job_ref'])['search_mode']
        if role == 'job_monitor' or self.has_information_channel(role):
            prior = []
            for sample_ref in selection.get('prior_sample_refs', []):
                row = self.jobs.db.execute('SELECT job_ref,body FROM samples WHERE sample_ref=?', (sample_ref,)).fetchone()
                if row is None or row['job_ref'] != assignment['job_ref']:
                    raise ValueError('prior_monitoring_sample_must_belong_to_assigned_job')
                prior.append(json.loads(row['body']))
            if role == 'job_monitor' or 'prior_sample_refs' in selection:
                assignment.update(prior_sample_refs=list(selection.get('prior_sample_refs', [])), prior_samples=prior)
            checked = deepcopy(selection.get('prior_checked_statuses', []))
            for value in checked:
                rows = store.db.execute('''SELECT json_extract(result,'$.result.sample')
                    FROM runtime_actions WHERE json_extract(action,'$.tool')='homology.check_handoff'
                    AND json_extract(result,'$.status')='completed'
                    AND json_extract(result,'$.result.checked_at_unix_seconds')=?
                    AND json_extract(result,'$.result.sample.job_ref')=?
                    AND json_extract(result,'$.result.sample.registry_ref')=?''',
                    (value['checked_at_unix_seconds'], assignment['job_ref'], self.jobs.config['registry_ref']))
                if not any(value == {'checked_at_unix_seconds': value['checked_at_unix_seconds'],
                                     **json.loads(row[0])} for row in rows):
                    raise ValueError('prior_checked_status_must_match_recorded_assigned_job_check')
            if 'prior_checked_statuses' in selection:
                assignment['prior_checked_statuses'] = checked
        return assignment

    @staticmethod
    def assignment(source):
        return source.request.message.as_record()['job_assignment']

    def working_state(self, source):
        # No implicit live poll, scientific state dump or private child history.
        return {'role': source.path[-1][0], 'assignment': self.assignment(source)}

    def _launch_credit(self, store, assignment, episode_id, run_id):
        return self._job_credit_calculator(store, role='job_launch', assignment=deepcopy(assignment),
            episode_id=episode_id, run_id=run_id)

    def _monitor_credit(self, store, assignment, episode_id, run_id):
        return self.monitoring_projector(store, role='job_monitor', assignment=deepcopy(assignment),
            episode_id=episode_id, run_id=run_id)

    def _results_credit(self, store, assignment, episode_id, run_id):
        return self._job_credit_calculator(store, role='job_results', assignment=deepcopy(assignment),
            episode_id=episode_id, run_id=run_id)

    def initial_credit(self, store, role, assignment, episode_id, run_id):
        bindings = {'job_launch': self._launch_credit,
            'job_monitor': self._monitor_credit, 'job_results': self._results_credit}
        if role not in bindings:
            raise ValueError('unknown_job_episode_role')
        value = bindings[role](store, assignment, episode_id, run_id)
        value = float(value['credit'] if isinstance(value, dict) else value)
        if not math.isfinite(value):
            raise ValueError('finite_operational_credit_required')
        return value

    def binding_for(self, role):
        if role not in self._role_credit_bindings:
            raise ValueError('unknown_job_episode_role')
        return deepcopy(self._role_credit_bindings[role])

    def credit_kind(self, role):
        """Declare the information kind of the existing controller projection."""
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        return 'monitoring' if role == 'job_monitor' else 'operational'

    def has_information_channel(self, role):
        return (getattr(self.monitoring_projector, 'include_handoff_checks', False)
                and role in getattr(self.monitoring_projector, 'information_roles', ())
                and callable(getattr(self.monitoring_projector, 'information_view', None)))

    def credit_view(self, source):
        role = source.path[-1][0]
        information = (self.monitoring_projector.information_view(source.workflow.store,
            assignment=self.assignment(source), episode_id=source.episode_id, run_id=source.workflow.run_id)
            if self.has_information_channel(role) else {})
        # Information kind determines its own projection. The caller's existing
        # scalar binding still determines this episode's controller input.
        value = (information['monitoring_information_credit'] if role == 'job_monitor' and information
            else self.initial_credit(source.workflow.store, role,
                self.assignment(source), source.episode_id, source.workflow.run_id))
        return {'credit': value, **information}

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

    def catalog(self, source):
        role = source.path[-1][0]
        empty = obj({})
        definitions = {
            'job_launch': [('homology.environment', empty),
                ('homology.configure', empty),
                ('homology.stage', empty), ('homology.submit', empty),
                ('homology.resume_start', empty), ('homology.check_handoff', empty)],
            'job_monitor': [('homology.sample', empty)],
            'job_results': [('homology.extract', {'type': 'object', 'properties': {
                'limit': {'type': 'integer', 'minimum': 0}, 'offset': {'type': 'integer', 'minimum': 0},
                'snapshot_ref': reference('source'), 'retry_from': reference('source')},
                'required': ['limit'], 'additionalProperties': False}),
                ('homology.coverage', obj({'snapshot_ref': reference('source')})),
                ('homology.errors', obj({'snapshot_ref': reference('source'),
                    'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 0}}))]}
        descriptions = {
            'homology.environment': 'Inspect preparation state and caller-owned resources for your assigned job.',
            'homology.configure': 'Apply and check the parent-selected CPU allocation and executable for the assigned job.',
            'homology.stage': 'Prepare or repair private snapshots; reuse unchanged inputs.',
            'homology.submit': 'Submit the assigned detached job once; a replay preserves its identity.',
            'homology.resume_start': 'Repair the existing submitted service startup without submitting another job.',
            'homology.check_handoff': 'Exercise a fresh receiver for status, elapsed time, progress and output availability.',
            'homology.sample': 'Record one actual typed job-state sample. Sample counts and unchanged polling are not progress.',
            'homology.extract': 'Extract a selected page of actual native measurements; explicit snapshot for later pages and retry_from for an explicit failed-attempt retry. Parent integrates scientific meaning.',
            'homology.coverage': 'Read recorded acquisition coverage and captured parser/native completeness for one assigned-job snapshot. This does not poll, parse or acquire new rows.',
            'homology.errors': 'Read a requested page of typed extraction failures without rerunning extraction.'}
        return [{'name': name, 'input_schema': schema, 'description': descriptions[name]}
                for name, schema in definitions[role]]

    async def execute(self, source, name, args, *, operation_key):
        result = await self._execute(source, name, args, operation_key=operation_key)
        if self.native_event_provider is not None and name in {'homology.submit', 'homology.resume_start'}:
            from method_loop.durable import DurableExecutionError
            job_ref = self.assignment(source)['job_ref']
            try:
                # Failure to establish this host's binding must not expose a
                # different run/resource's reservation as its own selection.
                self.bind_job_native_events(source, job_ref)
                result['native_event_targets'] = self.jobs.native_event_targets(job_ref)
            except (DurableExecutionError, sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
                result['native_event_targets'] = []
                storage = (isinstance(error, (sqlite3.Error, OSError)) or isinstance(error, DurableExecutionError)
                    and error.failure['code'] == 'storage_failure')
                result['native_event_target_failure'] = {
                    'code': 'native_event_storage_unavailable' if storage else 'native_event_identity_conflict',
                    'affected_refs': [job_ref]}
        if self.statistics is not None:
            try:
                exported = list(self.jobs.recover_statistics(self.assignment(source)['job_ref']))
            except (sqlite3.Error, OSError) as error:
                exported = [{'job_ref': self.assignment(source)['job_ref'], 'state': 'unavailable',
                    'code': 'statistics_registry_unavailable', 'exception_type': type(error).__name__}]
            result['execution_statistics_export'] = exported
        return result

    async def _execute(self, source, name, args, *, operation_key):
        if name not in {item['name'] for item in self.catalog(source)}:
            raise ValueError('tool_not_owned_by_job_role')
        assignment = self.assignment(source)
        job_ref = assignment['job_ref']
        try:
            row = self.jobs._row(job_ref)
            if row['cpu'] != assignment['cpu']:
                raise ValueError('job_assignment_cpu_mismatch')
            if row['search_mode'] != assignment.get('search_mode', 'native_defaults'):
                raise ValueError('job_assignment_search_mode_mismatch')
            if name == 'homology.environment':
                value = self.jobs.environment(job_ref)
            elif name == 'homology.configure':
                value = self.jobs.configure(job_ref, assignment['cpu'])
            elif name == 'homology.stage':
                value = self.jobs.stage(job_ref)
            elif name == 'homology.submit':
                value = self.jobs.submit(job_ref, statistics=self.statistics,
                    native_events=self.bind_job_native_events(source, job_ref))
            elif name == 'homology.resume_start':
                value = self.jobs.resume_start(job_ref,
                    native_events=self.bind_job_native_events(source, job_ref))
            elif name == 'homology.check_handoff':
                value = self.jobs.check_handoff(self.jobs.handoff(job_ref))
            elif name == 'homology.sample':
                value = self.jobs.sample(assignment['handoff'], operation_key=operation_key)
                return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                        'operational_sample_ref': value['sample_ref'], 'result': value, 'feedback': None}
            elif name == 'homology.coverage':
                value = recorded_coverage(source.workflow.store, args['snapshot_ref'],
                    query_ref=assignment['query_ref'], scope=source.scope,
                    execution_context={'job_ref': job_ref, 'registry_ref': self.jobs.config['registry_ref']})
            else:
                adapter = HomologyResults(source.workflow.store, policy=self.parser_policy)
                if name == 'homology.extract':
                    inputs = NativePhmmerInput.from_job(self.jobs, assignment['handoff'])
                    return await adapter.extract(inputs, scope=source.scope, **args, attempt_key=operation_key)
                value = adapter.errors(scope=source.scope, query_ref=assignment['query_ref'],
                    execution_context={'job_ref': job_ref, 'registry_ref': self.jobs.config['registry_ref']}, **args)
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                    'result': value, 'feedback': None}
        except (ValueError, KeyError, OSError, sqlite3.Error, subprocess.SubprocessError,
                ContractError, AcquisitionError) as error:
            # Failure is an actionable outcome, not a fabricated completed action.
            return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': (error.code if isinstance(error, AcquisitionError)
                                     else 'job_storage_failed' if isinstance(error, sqlite3.Error)
                                     else 'job_control_failed' if isinstance(error, subprocess.SubprocessError)
                                     else str(error) if isinstance(error, ValueError) else 'job_operation_failed'),
                    'exception_type': type(error).__name__, 'operation': name, 'job_ref': job_ref,
                    **({'phase': error.phase, **{key: error.operational[key]
                        for key in ('retryable', 'retry_same_prepared_job', 'local_resources')
                        if key in (error.operational or {})}}
                        if isinstance(error, AcquisitionError) else {})}}

    def latest_sample(self, source, *, include_inherited=False):
        row = source.workflow.store.db.execute('''SELECT json_extract(result,'$.result')
            FROM runtime_actions WHERE run_id=? AND episode_id=?
            AND json_extract(result,'$.operational_sample_ref') IS NOT NULL
            ORDER BY decision_index DESC LIMIT 1''', (source.workflow.run_id, source.episode_id)).fetchone()
        if row is not None:
            return json.loads(row[0])
        prior = self.assignment(source).get('prior_samples', []) if include_inherited else []
        return deepcopy(prior[-1]) if prior else None

    @staticmethod
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

    def facts(self, source, *, credit_view=None):
        assignment = self.assignment(source)
        # Functional communication validation is not a scientific review, a new
        # selected action or permission to override the continuation decision.
        try:
            handoff = self.jobs.handoff(assignment['job_ref'])
            self.jobs.check_handoff(handoff)
            failure = None
        except (sqlite3.Error, subprocess.SubprocessError):
            # The receiver itself is unavailable. Re-reading its registry to
            # classify that failure can fail again and lose the child's form.
            handoff, failure = None, 'receiving_interface_unavailable'
        except (ValueError, KeyError, OSError, AcquisitionError) as error:
            handoff = None
            try:
                row = self.jobs._row(assignment['job_ref'])
                handle = self.jobs.directory/assignment['job_ref']/'native.handle.json'
                unreadable = False
                try:
                    prepared = handle.is_file() and json.loads(handle.read_text()).get('stage') == 'prepared'
                except (OSError, ValueError, TypeError, AttributeError):
                    prepared, unreadable = False, True
                failure = ('receiving_interface_unavailable' if unreadable else
                    'submission_unconfirmed' if prepared else 'job_not_submitted' if not row['submission_requested'] else
                    'submission_unconfirmed' if not handle.is_file() else
                    'native_handle_identity_mismatch' if str(error) == 'native_handle_does_not_describe_registered_job'
                    else 'receiving_interface_unavailable')
            except (sqlite3.Error, ValueError, KeyError):
                failure = 'receiving_interface_unavailable'
        facts = {'job_ref': assignment['job_ref'], 'job_cpu': assignment['cpu'], 'job_handoff': handoff,
                'job_handoff_state': 'usable' if handoff else 'unavailable',
                'job_handoff_failure': failure, 'job_sample': self.latest_sample(source),
                'resource_tool_estimates': recorded_forecasts(source.workflow.store,
                    run_id=source.workflow.run_id, episode_id=source.episode_id)}
        if 'search_modes' in self.jobs.config:
            facts['job_search_mode'] = assignment['search_mode']
        if source.path[-1][0] == 'job_launch':
            facts['job_checked_status'] = self.latest_checked_status(source)
        if self.has_information_channel(source.path[-1][0]):
            information = self.credit_view(source) if credit_view is None else credit_view
            facts.update(monitoring_information_credit=information['monitoring_information_credit'],
                         monitoring_findings=information['monitoring_findings'])
        elif source.path[-1][0] == 'job_monitor' and callable(getattr(self.monitoring_projector, 'findings', None)):
            facts['monitoring_findings'] = self.monitoring_projector.findings(source.workflow.store,
                assignment=assignment, episode_id=source.episode_id, run_id=source.workflow.run_id)
        if source.path[-1][0] == 'job_results':
            facts.update(job_result_progress=None, job_result_progress_failure=None)
            selected = source.workflow.store.db.execute('''SELECT json_extract(result,'$.result.snapshot_ref')
                FROM runtime_actions WHERE run_id=? AND episode_id=?
                AND json_extract(action,'$.tool') IN ('homology.extract','homology.coverage')
                AND json_type(result,'$.result.snapshot_ref')='text'
                ORDER BY decision_index DESC LIMIT 1''',
                (source.workflow.run_id, source.episode_id)).fetchone()
            if selected is not None:
                try:
                    coverage = recorded_coverage(source.workflow.store, selected[0],
                        query_ref=assignment['query_ref'], scope=source.scope,
                        execution_context={'job_ref': assignment['job_ref'],
                            'registry_ref': self.jobs.config['registry_ref']})
                    facts['job_result_progress'] = _result_progress(coverage)
                except ContractError:
                    facts['job_result_progress_failure'] = 'invalid_snapshot_or_scope'
                except (OSError, sqlite3.Error):
                    facts['job_result_progress_failure'] = 'storage_failure'
                except (ValueError, KeyError, TypeError):
                    facts['job_result_progress_failure'] = 'coverage_read_failed'
        return facts

    def validate_report(self, value, assignment, *, role, store=None, schema=None):
        """Select the owning job episode's return binding explicitly."""
        bindings = {
            'job_launch': self._validate_launch_return,
            'job_monitor': self._validate_monitor_return,
            'job_results': self._validate_results_return,
        }
        if role not in bindings:
            raise ValueError('homology_return_role_required')
        bindings[role](value, assignment, store=store, schema=schema)

    def _validate_launch_return(self, value, assignment, *, store, schema):
        self._validate_role_return_sources('job_launch', schema)
        self._validate_recorded_return(value, assignment, store=store, schema=schema)

    def _validate_monitor_return(self, value, assignment, *, store, schema):
        self._validate_role_return_sources('job_monitor', schema)
        self._validate_recorded_return(value, assignment, store=store, schema=schema)

    def _validate_results_return(self, value, assignment, *, store, schema):
        self._validate_role_return_sources('job_results', schema)
        self._validate_recorded_return(value, assignment, store=store, schema=schema)

    def _validate_role_return_sources(self, role, schema):
        if schema is None:
            return
        allowed = self.fact_sources(role)
        for node in schema.get('properties', {}).values():
            source = node.get('x-source')
            if isinstance(source, str) and source.startswith(('job_', 'monitoring_')) and source not in allowed:
                raise ReportBoundaryError('Fact does not belong to this job episode',
                    code='homology_return_source_role_conflict')

    def _validate_recorded_return(self, value, assignment, *, store=None, schema=None):
        """References and native fact fields must describe their actual record.

        Parent-defined names/interpretations remain allowed. A declared native
        sample identity cannot be reused to smuggle different recorded values.
        This does not assess scientific suitability or decide continuation.
        """
        validate_recorded_estimates(store, value, schema=schema, job_ref=assignment['job_ref'])
        reference_namespaces = {'sample_ref': 'job_sample', 'job_ref': 'homology_job',
            'registry_ref': 'execution_registry'}
        def declares(actual, expected, keyword=None):
            # Recognize declared native meanings, not literal schema text.
            # Additional validation constraints and annotations cannot disable
            # provenance checks. Enum/type ordering is not semantic ordering.
            if isinstance(expected, Mapping):
                if not isinstance(actual, Mapping):
                    return False
                for key, child in expected.items():
                    if keyword != 'properties' and key not in {
                            'type', 'format', 'x-reference-namespace', 'enum', 'properties', 'items'}:
                        continue
                    if key == 'enum' and key not in actual and 'const' in actual:
                        if actual['const'] not in child:
                            return False
                    elif key not in actual or not declares(actual[key], child, key):
                        return False
                return True
            if keyword == 'enum':
                return isinstance(actual, list) and bool(actual) and all(item in expected for item in actual)
            if keyword == 'type':
                allowed = set(expected if isinstance(expected, list) else [expected])
                if 'number' in allowed:
                    allowed.add('integer')
                declared = actual if isinstance(actual, list) else [actual]
                return bool(declared) and all(item in allowed for item in declared)
            return actual == expected
        def known_identity(value, namespace):
            if namespace == 'homology_job' and value == assignment['job_ref']:
                return True
            if namespace == 'job_sample' and store is not None:
                if self.recorded_sample(store, value, assignment) is not None:
                    return True
            try:
                return self.jobs.resolve(value, namespace)
            except sqlite3.Error:
                return False
        def visit(node, declared):
            if isinstance(node, Mapping):
                properties = declared.get('properties', {}) if declared is not None else {}
                # This is the declared native execution-observation shape, not
                # a reservation of arbitrary parent-chosen field names.
                if declares(properties, EXECUTION_OBSERVATION_SCHEMA['properties'], 'properties'):
                    kind = node['observation_kind']
                    if kind == 'handoff_check':
                        if node.get('sample_ref') is not None or node.get('sampled_at_unix_seconds') is not None:
                            raise ReportBoundaryError('A checked status is not a sample', code='checked_status_identity_mismatch')
                        if store is None:
                            raise ReportBoundaryError('Selected checked-status record is unavailable',
                                                      code='checked_status_record_unavailable')
                        rows = store.db.execute('''SELECT json_extract(result,'$.result.sample')
                            FROM runtime_actions WHERE json_extract(action,'$.tool')='homology.check_handoff'
                            AND json_extract(result,'$.status')='completed'
                            AND json_extract(result,'$.result.checked_at_unix_seconds')=?
                            AND json_extract(result,'$.result.sample.job_ref')=?
                            AND json_extract(result,'$.result.sample.registry_ref')=?''',
                            (node.get('checked_at_unix_seconds'), assignment['job_ref'], self.jobs.config['registry_ref']))
                        if not any(all(node[key] == value for key, value in json.loads(row[0]).items())
                                   for row in rows):
                            raise ReportBoundaryError('Checked status differs from selected recorded work',
                                                      code='checked_status_fact_mismatch')
                    elif (node.get('sample_ref') is None or node.get('sampled_at_unix_seconds') is None
                          or node.get('checked_at_unix_seconds') is not None):
                        raise ReportBoundaryError('A sample needs its original sample identity',
                                                  code='sample_identity_mismatch')
                identities = {name: field.get('x-reference-namespace') for name, field in properties.items()
                    if field.get('format') in REFERENCE_FORMATS and node.get(name) is not None}
                if declared is None:
                    # Untyped direct consumers can establish identity from the
                    # registry, without reserving arbitrary parent field names.
                    identities = {name: namespace for name, namespace in reference_namespaces.items()
                        if node.get(name) is not None and known_identity(node[name], namespace)}
                for name, namespace in identities.items():
                    if namespace == 'homology_job' and node[name] != assignment['job_ref']:
                        raise ReportBoundaryError('Returned job differs from its assignment', code='job_identity_mismatch')
                    if namespace == 'execution_registry' and node[name] != self.jobs.config['registry_ref']:
                        raise ReportBoundaryError('Returned registry differs from its binding', code='registry_identity_mismatch')
                    if namespace != 'job_sample':
                        continue
                    actual = self.recorded_sample(store, node[name], assignment) if store is not None else None
                    if actual is None:
                        try:
                            row = self.jobs.db.execute('SELECT job_ref,body FROM samples WHERE sample_ref=?',
                                                      (node[name],)).fetchone()
                        except sqlite3.Error:
                            row = None
                        actual = json.loads(row['body']) if row is not None and row['job_ref'] == assignment['job_ref'] else None
                    if actual is None:
                        raise ReportBoundaryError('Sample does not belong to the assigned job', code='sample_identity_mismatch')
                    fields = [key for key in node.keys() & actual.keys()
                        if properties.get(key, {}).get('format') not in REFERENCE_FORMATS
                        or properties[key].get('x-reference-namespace') == reference_namespaces.get(key)]
                    if any(node[key] != actual[key] for key in fields):
                        raise ReportBoundaryError('Native sample fields differ from their recorded values', code='sample_fact_mismatch')
                for name, child in node.items():
                    visit(child, properties.get(name) if declared is not None else None)
            elif isinstance(node, (list, tuple)):
                for child in node:
                    visit(child, declared.get('items') if declared is not None else None)
        visit(value, schema)

    def received_timing_records(self, store, value, schema, scope):
        """Normalize requested, admitted timing facts to their physical receipt.

        Read only the original typed host measurement and immutable assignment
        at the selected check/sample boundary. No live poll, private reasoning,
        new statistic, child-score sum or biological interpretation participates.
        A missing provenance record is a reporting issue, never a form rejection.
        """
        from .execution_recording import NativeMeasurement
        from .native_timing_information import record_native_measurement
        references, issues = [], []

        def measured_status(status, source, path):
            if not isinstance(status, Mapping) or status.get('outcome') not in {'succeeded', 'failed'}:
                return
            if status.get('elapsed_seconds') is None:
                return
            code = None
            job = status['job_ref']
            try:
                if status['registry_ref'] != self.jobs.config['registry_ref']:
                    raise ValueError('received_status_registry_mismatch')
                checked = status.get('checked_at_unix_seconds')
                sample = status.get('sample_ref')
                row = store.db.execute('''SELECT exports.value, episodes.request, actions.result
                    FROM runtime_actions actions JOIN runtime_episodes episodes
                    ON episodes.run_id=actions.run_id AND episodes.episode_id=actions.episode_id
                    JOIN json_each(actions.result,'$.execution_statistics_export') exports
                    WHERE json_extract(exports.value,'$.job_ref')=?
                    AND json_type(exports.value,'$.measurement')='object'
                    AND json_extract(actions.result,'$.status')='completed'
                    AND ((? IS NOT NULL AND json_extract(actions.action,'$.tool')='homology.check_handoff'
                         AND json_extract(actions.result,'$.result.checked_at_unix_seconds')=?)
                      OR (? IS NOT NULL AND json_extract(actions.action,'$.tool')='homology.sample'
                          AND json_extract(actions.result,'$.operational_sample_ref')=?))
                    ORDER BY actions.rowid LIMIT 1''', (job, checked, checked, sample, sample)).fetchone()
                if row is None:
                    code = 'measurement_not_recorded'
                else:
                    exported, request, outcome = (json.loads(item) for item in row)
                    message = request['message']
                    carriers = ([message['job_assignment']] if 'job_assignment' in message else [])
                    resource = message.get('episode_assignment', {})
                    if 'adapter_assignment' in resource:
                        carriers.append(resource['adapter_assignment'])
                    if (not carriers or any(not isinstance(item, Mapping) for item in carriers)
                            or any(json.dumps(item, sort_keys=True, allow_nan=False)
                                != json.dumps(carriers[0], sort_keys=True, allow_nan=False)
                                for item in carriers[1:])):
                        raise ValueError('received_assignment_missing_or_conflicting')
                    assignment = carriers[0]
                    query_ref, cpu = assignment['query_ref'], assignment['cpu']
                    if assignment['job_ref'] != job or type(cpu) is not int:
                        raise ValueError('received_assignment_identity_mismatch')
                    handoff = assignment.get('handoff')
                    if handoff is not None and (handoff['job_ref'] != job
                            or handoff['registry_ref'] != status['registry_ref']):
                        raise ValueError('received_assignment_registry_mismatch')
                    # Both scopes and the immutable registry operands must
                    # agree with this action's saved assignment. The registry
                    # is a witness, never a fallback source of query identity.
                    self._query(store, store.validate_scope(message['scope']), query_ref)
                    query = self._query(store, scope, query_ref)
                    registered = self.jobs._row(job)
                    if (registered['query_ref'] != query_ref or registered['cpu'] != cpu
                            or registered['search_mode'] != assignment.get('search_mode', 'native_defaults')):
                        raise ValueError('received_assignment_job_mismatch')
                    from .homology_jobs import normalize_query_fasta
                    symbols = artifact_path(store, query['sequence_ref']).read_text()
                    if registered['query_fasta'] != normalize_query_fasta('>query\n'+symbols+'\n'):
                        raise ValueError('received_assignment_query_mismatch')
                    actual = outcome['result']['sample'] if checked is not None else outcome['result']
                    if (any(actual[key] != status[key] for key in STATUS_SCHEMA['properties'])
                            or checked is not None and sample is not None
                            or checked is None and (actual['sample_ref'] != sample
                                or actual['sampled_at_unix_seconds'] != status['sampled_at_unix_seconds'])):
                        raise ValueError('received_selected_status_mismatch')
                    measured = NativeMeasurement.from_record(exported['measurement'])
                    if (self.statistics is None
                            or measured.execution_class != self.statistics.execution_class(self.jobs, registered)
                            or exported['attempt_sha256'] != measured.statistic.attempt_sha256
                            or exported['class_ref'] != measured.execution_class.ref):
                        raise ValueError('received_measurement_assignment_mismatch')
                    if 'adapter_assignment' in resource:
                        selection = (resource['handoff']['resource_selection']
                            if 'handoff' in resource else resource['resource_selection'])
                        if (selection['capability_binding_ref'] != status['registry_ref']
                                or selection['allocation']['cpu'] != cpu
                                or selection['resource_id'] != measured.execution_class.resource_id):
                            raise ValueError('received_resource_assignment_mismatch')
                    expected_outcome = ('succeeded' if measured.statistic.outcome == 'succeeded'
                        else 'failed' if measured.statistic.outcome in {'failed', 'cancelled', 'resource_limit'}
                        else 'unknown')
                    if (measured.statistic.duration_kind != 'complete'
                            or measured.statistic.elapsed_seconds != status['elapsed_seconds']
                            or measured.execution_class.duration_measure != status['duration_measure']
                            or expected_outcome != status['outcome']):
                        code = 'measurement_status_mismatch'
                    else:
                        references.append(record_native_measurement(store, measured, operation='phmmer_search',
                            operands=[{'role': 'query', 'subject_ref': query_ref}]))
            except (ValueError, KeyError, TypeError, ContractError):
                code = 'measurement_record_invalid'
            except (OSError, sqlite3.Error):
                code = 'receipt_storage_unavailable'
            if code is not None:
                issues.append({'source': source, 'field': path, 'job_ref': job, 'code': code})

        def visit(node, declared, path):
            source = declared.get('x-source')
            if source in {'job_checked_status', 'job_sample'}:
                measured_status(node, source, path)
            elif source == 'monitoring_findings' and isinstance(node, (list, tuple)):
                for index, finding in enumerate(node):
                    measured_status(finding['sample'], source, path+[index, 'sample'])
            elif isinstance(node, Mapping):
                for key, child in node.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key], path+[key])
            elif isinstance(node, (list, tuple)) and 'items' in declared:
                for index, child in enumerate(node):
                    visit(child, declared['items'], path+[index])
        visit(value, schema, [])
        return {'version': 'received_job_timing_receipts_v1',
                'native_execution_refs': list(dict.fromkeys(references)), 'issues': issues}
