"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
from gene_annotation_episode.local_jobs import LocalJobPolicy
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import _binding
from types import MappingProxyType
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.homology_job_submission.episode import LegacyHomologySubmissionEpisodes
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.homology_job_monitoring.episode import LegacyHomologyMonitoringEpisodes
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.homology_result_acquisition.episode import LegacyHomologyAcquisitionEpisodes
from gene_annotation_episode.episodic_workflow.root.homology_job_submission.episode import HomologySubmissionEpisodes
from gene_annotation_episode.episodic_workflow.root.homology_job_monitoring.episode import HomologyMonitoringEpisodes
from gene_annotation_episode.episodic_workflow.root.homology_result_acquisition.episode import HomologyAcquisitionEpisodes
from gene_annotation_episode.episodic_workflow.root.library import homology_custody
from gene_annotation_episode.episodic_workflow.root.library import homology_custody_configuration
from gene_annotation_episode.episodic_workflow.root.library import homology_native_events
from gene_annotation_episode.episodic_workflow.root.library import homology_received_records

class HomologyEpisodes:
    """Configured custody and six fixed job implementations for two explicit parents."""
    roles = ('job_launch', 'job_monitor', 'job_results')
    jobs = homology_custody_configuration.jobs
    parser_policy = homology_custody_configuration.parser_policy
    _job_credit_calculator = homology_custody_configuration._job_credit_calculator
    monitoring_projector = homology_custody_configuration.monitoring_projector
    _role_credit_bindings = homology_custody_configuration._role_credit_bindings
    statistics = homology_custody_configuration.statistics
    native_event_provider = homology_custody_configuration.native_event_provider

    def __init__(self, jobs: HomologyJobs, *, parser_policy: LocalJobPolicy, credit_projector, credit_binding, monitoring_projector, monitoring_binding, statistics=None):
        self._custody = SimpleNamespace()
        if type(jobs) is not HomologyJobs or type(parser_policy) is not LocalJobPolicy:
            raise TypeError('explicit_homology_resources_required')
        if not callable(credit_projector) or not isinstance(credit_binding, dict) or (not credit_binding):
            raise ValueError('explicit_operational_credit_binding_required')
        self.jobs, self.parser_policy, self._job_credit_calculator = (jobs, parser_policy, credit_projector)
        if not callable(monitoring_projector) or not isinstance(monitoring_binding, dict) or (not monitoring_binding):
            raise ValueError('explicit_monitoring_credit_binding_required')
        self.monitoring_projector = monitoring_projector
        self._role_credit_bindings = {'job_launch': json.loads(json.dumps(credit_binding, allow_nan=False)), 'job_monitor': json.loads(json.dumps(monitoring_binding, allow_nan=False)), 'job_results': json.loads(json.dumps(credit_binding, allow_nan=False))}
        if statistics is not None:
            from gene_annotation_episode.episodic_workflow.root.execution_recording import HomologyStatistics
            if type(statistics) is not HomologyStatistics:
                raise TypeError('typed_homology_statistics_binding_required')
        self.statistics = statistics
        self.native_event_provider = None
        self._implementations = MappingProxyType({'job_launch': HomologySubmissionEpisodes(jobs, parser_policy=parser_policy, credit_projector=credit_projector, credit_binding=credit_binding, monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding, statistics=statistics), 'job_monitor': HomologyMonitoringEpisodes(jobs, parser_policy=parser_policy, credit_projector=credit_projector, credit_binding=credit_binding, monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding, statistics=statistics), 'job_results': HomologyAcquisitionEpisodes(jobs, parser_policy=parser_policy, credit_projector=credit_projector, credit_binding=credit_binding, monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding, statistics=statistics)})
        self._standalone_implementations = MappingProxyType({'job_launch': LegacyHomologySubmissionEpisodes(jobs, parser_policy=parser_policy, credit_projector=credit_projector, credit_binding=credit_binding, monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding, statistics=statistics), 'job_monitor': LegacyHomologyMonitoringEpisodes(jobs, parser_policy=parser_policy, credit_projector=credit_projector, credit_binding=credit_binding, monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding, statistics=statistics), 'job_results': LegacyHomologyAcquisitionEpisodes(jobs, parser_policy=parser_policy, credit_projector=credit_projector, credit_binding=credit_binding, monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding, statistics=statistics)})
        for implementation in (*self._implementations.values(), *self._standalone_implementations.values()):
            implementation._custody = self._custody

    def as_record(self):
        return {'version': 'root_homology_episode_family_v2', 'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config, 'parser_policy': self.parser_policy.to_dict(), 'job_credit_calculator': _binding(self._job_credit_calculator), 'monitoring_projector': _binding(self.monitoring_projector), 'role_credit_bindings': deepcopy(self._role_credit_bindings), 'monitoring_projector_parameters': self.monitoring_projector.as_record() if callable(getattr(self.monitoring_projector, 'as_record', None)) else None, 'statistics': None if self.statistics is None else self.statistics.as_record(), 'private_implementations': {role: self.implementation_for(role).as_record() for role in self.roles}, 'standalone_improvement_implementations': {role: self._standalone_implementation_for(role).as_record() for role in self.roles}}
    recover_native_events = homology_native_events.recover_native_events
    recover_statistics = homology_native_events.recover_statistics
    bind_job_native_events = homology_native_events.bind_job_native_events
    _query = staticmethod(homology_custody._query)
    prospective_execution_classes = homology_custody.prospective_execution_classes
    prospective_execution_options = homology_custody.prospective_execution_options
    assignment = staticmethod(homology_custody.assignment)
    working_state = homology_custody.working_state
    resolve = homology_custody.resolve
    latest_sample = homology_custody.latest_sample
    recorded_sample = staticmethod(homology_custody.recorded_sample)
    latest_checked_status = homology_custody.latest_checked_status
    received_timing_records = homology_received_records.received_timing_records

    def implementation_for(self, role):
        expected = {'job_launch': HomologySubmissionEpisodes, 'job_monitor': HomologyMonitoringEpisodes, 'job_results': HomologyAcquisitionEpisodes}
        if role not in expected:
            raise ValueError('unknown_job_episode_role')
        implementation = self._implementations[role]
        if type(implementation) is not expected[role] or implementation.jobs is not self.jobs:
            raise TypeError('fixed_homology_implementation_required')
        return implementation

    def _standalone_implementation_for(self, role):
        expected = {'job_launch': LegacyHomologySubmissionEpisodes, 'job_monitor': LegacyHomologyMonitoringEpisodes, 'job_results': LegacyHomologyAcquisitionEpisodes}
        if role not in expected:
            raise ValueError('unknown_job_episode_role')
        implementation = self._standalone_implementations[role]
        if type(implementation) is not expected[role] or implementation._custody is not self._custody or implementation.jobs is not self.jobs:
            raise TypeError('fixed_homology_implementation_required')
        return implementation

    def implementation_for_path(self, path, *, child_role=None):
        """Select the fixed child of its actual original annotation/improvement parent."""
        minimum = 2 if child_role is None else 1
        if not isinstance(path, (tuple, list)) or len(path) < minimum or any((not isinstance(item, (tuple, list)) or len(item) != 2 for item in path)):
            raise ValueError('fixed_homology_parent_path_required')
        parent_path = path[:-1] if child_role is None else path
        if parent_path[0][0] not in ('annotation', 'improvement') or any((item[0] != 'improvement' for item in parent_path[1:])):
            raise ValueError('fixed_homology_parent_path_required')
        parent = parent_path[-1][0]
        role = path[-1][0] if child_role is None else child_role
        if parent == 'annotation':
            return self.implementation_for(role)
        if parent == 'improvement':
            return self._standalone_implementation_for(role)
        raise ValueError('fixed_homology_parent_path_required')

    def with_native_events(self, provider):
        view = homology_native_events.with_native_events(self, provider)
        view._implementations = MappingProxyType({role: self.implementation_for(role).with_native_events(provider) for role in self.roles})
        view._standalone_implementations = MappingProxyType({role: self._standalone_implementation_for(role).with_native_events(provider) for role in self.roles})
        for implementation in (*view._implementations.values(), *view._standalone_implementations.values()):
            implementation._custody = view._custody
        return view

    def describe(self, *, parent_path=None):
        implementations = {role: self.implementation_for(role) if parent_path is None else self.implementation_for_path(parent_path, child_role=role) for role in self.roles}
        return {role: {'report_facts': implementation.fact_sources(role), 'responsibility': implementation.instructions(role)} for role, implementation in implementations.items()}

    def commission_schemas(self, scientific_child, *, parent_path=None):
        return [schema for role in self.roles for schema in (self.implementation_for(role) if parent_path is None else self.implementation_for_path(parent_path, child_role=role)).commission_schemas(scientific_child)]
