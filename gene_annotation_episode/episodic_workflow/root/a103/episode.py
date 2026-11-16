"""Predefined annotation parent."""
from importlib import import_module
from gene_annotation_episode.episodic_workflow.root.a103.task import LegacyAnnotationTask
from gene_annotation_episode.episodic_workflow.root.a103.instructions import instructions
from gene_annotation_episode.episodic_workflow.root.a103.from_parent import assemble_request, validate_path
from gene_annotation_episode.episodic_workflow.root.a103.credit import credit_projector, credit_binding, credit_view
from gene_annotation_episode.episodic_workflow.root.a103.to_child_homology_job_submission import assemble_annotation_homology_job_submission_request
from gene_annotation_episode.episodic_workflow.root.a103.to_child_homology_job_monitoring import assemble_annotation_homology_monitor_request
from gene_annotation_episode.episodic_workflow.root.a103.to_child_homology_result_acquisition import assemble_annotation_homology_result_acquisition_request
from gene_annotation_episode.episodic_workflow.root.a103.from_child_homology_job_submission import receive_annotation_homology_job_submission_report
from gene_annotation_episode.episodic_workflow.root.a103.from_child_homology_job_monitoring import receive_annotation_homology_monitor_report
from gene_annotation_episode.episodic_workflow.root.a103.from_child_homology_result_acquisition import receive_annotation_homology_result_acquisition_report


class LegacyAnnotationEpisode:
    binding_path = 'legacy_annotation'
    roles = ('annotation',)
    decision_source_type = LegacyAnnotationTask
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
            return assemble_annotation_homology_job_submission_request
        if role == 'job_monitor':
            return assemble_annotation_homology_monitor_request
        if role == 'job_results':
            return assemble_annotation_homology_result_acquisition_request
        raise ValueError('unknown_job_episode_role')

    @staticmethod
    def child_report_receiver(role):
        if role == 'job_launch':
            return receive_annotation_homology_job_submission_report
        if role == 'job_monitor':
            return receive_annotation_homology_monitor_report
        if role == 'job_results':
            return receive_annotation_homology_result_acquisition_report
        raise ValueError('unknown_job_episode_role')

    @staticmethod
    def as_record():
        return {'version': 'legacy_annotation_episode_v1', 'binding_id': 'legacy_annotation', 'role': 'annotation',
                'owner_class': 'gene_annotation_episode.episodic_workflow.root.a103.episode.LegacyAnnotationEpisode',
                'task_class': 'gene_annotation_episode.episodic_workflow.root.a103.task.LegacyAnnotationTask'}
