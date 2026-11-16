"""Predefined improvement parent."""
from importlib import import_module
from .task import LegacyImprovementTask
from .instructions import instructions
from .from_parent import assemble_request, validate_path
from .credit import credit_projector, credit_binding, credit_view
from .to_child_homology_job_submission import assemble_improvement_homology_job_submission_request
from .to_child_homology_job_monitoring import assemble_improvement_homology_monitor_request
from .to_child_homology_result_acquisition import assemble_improvement_homology_result_acquisition_request
from .from_child_homology_job_submission import receive_improvement_homology_job_submission_report
from .from_child_homology_job_monitoring import receive_improvement_homology_monitor_report
from .from_child_homology_result_acquisition import receive_improvement_homology_result_acquisition_report


class LegacyImprovementEpisode:
    binding_path = 'legacy_improvement'
    roles = ('improvement',)
    decision_source_type = LegacyImprovementTask
    instruction_composer = staticmethod(instructions)
    validate_path = staticmethod(validate_path)
    assemble_request = staticmethod(assemble_request)
    credit_projector = staticmethod(credit_projector)
    credit_binding = staticmethod(credit_binding)
    credit_view = staticmethod(credit_view)
    yield_controller = staticmethod(import_module(__package__ + '.yield_estimator').yield_controller)

    @staticmethod
    def child_request_assembler(role):
        if role == 'job_launch':
            return assemble_improvement_homology_job_submission_request
        if role == 'job_monitor':
            return assemble_improvement_homology_monitor_request
        if role == 'job_results':
            return assemble_improvement_homology_result_acquisition_request
        raise ValueError('unknown_job_episode_role')

    @staticmethod
    def child_report_receiver(role):
        if role == 'job_launch':
            return receive_improvement_homology_job_submission_report
        if role == 'job_monitor':
            return receive_improvement_homology_monitor_report
        if role == 'job_results':
            return receive_improvement_homology_result_acquisition_report
        raise ValueError('unknown_job_episode_role')

    @staticmethod
    def as_record():
        return {'version': 'legacy_improvement_episode_v1', 'binding_id': 'legacy_improvement', 'role': 'improvement',
                'owner_class': 'gene_annotation_episode.episodic_workflow.root.a103.legacy_improvement.episode.LegacyImprovementEpisode',
                'task_class': 'gene_annotation_episode.episodic_workflow.root.a103.legacy_improvement.task.LegacyImprovementTask'}
