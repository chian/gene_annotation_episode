"""Record of the actual private homology binding and its configuration."""
from gene_annotation_episode.episodic_workflow.root.library.homology_episode_contracts import _binding

def as_record(self):
    return {'version': 'root_legacy_private_homology_v1', 'commissioning_parent': 'improvement', 'binding_path': 'legacy_annotation/homology_job_monitoring', 'binding_id': 'job_monitor', 'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config, 'parser_policy': self.parser_policy.to_dict(), 'credit_binding': self.binding_for('job_monitor'), 'credit_calculator': _binding(self.monitoring_projector if 'job_monitor' == 'job_monitor' else self._job_credit_calculator), 'statistics': None if self.statistics is None else self.statistics.as_record()}
