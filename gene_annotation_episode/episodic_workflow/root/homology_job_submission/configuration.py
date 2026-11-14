"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
from gene_annotation_episode.local_jobs import LocalJobPolicy
from types import SimpleNamespace
ROLES = ('job_launch',)

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
    self._role_credit_bindings = {'job_launch': json.loads(json.dumps(credit_binding, allow_nan=False))}
    if statistics is not None:
        from gene_annotation_episode.episodic_workflow.root.execution_recording import HomologyStatistics
        if type(statistics) is not HomologyStatistics:
            raise TypeError('typed_homology_statistics_binding_required')
    self.statistics = statistics
    self.native_event_provider = None
