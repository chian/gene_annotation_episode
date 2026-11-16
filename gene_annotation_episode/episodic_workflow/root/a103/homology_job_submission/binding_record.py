from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.homology_job_submission.contracts import _binding, deepcopy

class SubmissionBindingRecord:

    def as_record(self):
        return {'binding_id': 'legacy_annotation/homology_job_submission', 'version': 'homology_episode_bindings_v5', 'commissioning_parent': 'legacy_annotation', 'owner_class': type(self).__module__ + '.' + type(self).__qualname__, 'task_class': self.decision_source_type.__module__ + '.' + self.decision_source_type.__qualname__, 'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config, 'parser_policy': self.parser_policy.to_dict(), 'job_credit_calculator': _binding(self._job_credit_calculator), 'monitoring_projector': _binding(self.monitoring_projector), 'role_credit_bindings': deepcopy(self._role_credit_bindings), 'monitoring_projector_parameters': self.monitoring_projector.as_record() if callable(getattr(self.monitoring_projector, 'as_record', None)) else None, 'statistics': None if self.statistics is None else self.statistics.as_record()}
