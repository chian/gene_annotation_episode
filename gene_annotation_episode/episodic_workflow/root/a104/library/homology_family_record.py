"""Exact original v4 family descriptor; no singleton field projection."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.message_contracts import _binding

def original_family_record(owner):
    return {'version': 'homology_episode_bindings_v4', 'registry_directory': str(owner.jobs.directory), 'registry_configuration': owner.jobs.config, 'parser_policy': owner.parser_policy.to_dict(), 'job_credit_calculator': _binding(owner._job_credit_calculator), 'monitoring_projector': _binding(owner.monitoring_projector), 'role_credit_bindings': deepcopy(owner._role_credit_bindings), 'monitoring_projector_parameters': owner.monitoring_projector.as_record() if callable(getattr(owner.monitoring_projector, 'as_record', None)) else None, 'statistics': None if owner.statistics is None else owner.statistics.as_record()}
