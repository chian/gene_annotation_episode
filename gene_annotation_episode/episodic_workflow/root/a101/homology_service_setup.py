"""Explicit construction for the legacy runtime job interface."""

def create_homology_bindings(*args, **configuration):
    from gene_annotation_episode.episodic_workflow.root.a101.homology_job_submission.episode import HomologyEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a101.homology_job_monitoring.episode import HomologyEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a101.homology_result_acquisition.episode import HomologyEpisode as Private2
    return {binding.roles[0]: binding for binding in (
        Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration))}
