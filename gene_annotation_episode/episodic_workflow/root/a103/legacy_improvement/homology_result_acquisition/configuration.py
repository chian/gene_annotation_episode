from __future__ import annotations
from .contracts import HomologyJobs, LocalJobPolicy, json

class AcquisitionConfiguration:

    def __init__(self, jobs: HomologyJobs, *, parser_policy: LocalJobPolicy, credit_projector, credit_binding, monitoring_projector, monitoring_binding, statistics=None):
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
            from gene_annotation_episode.episodic_workflow.root.a103.execution_recording import HomologyStatistics
            if type(statistics) is not HomologyStatistics:
                raise TypeError('typed_homology_statistics_binding_required')
        self.statistics = statistics
        self.native_event_provider = None
