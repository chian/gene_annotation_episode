"""Explicit construction for the legacy runtime job interface."""

def create_homology_bindings(*args, **configuration):
    from gene_annotation_episode.episodic_workflow.root.a104.homology_job_submission.episode import HomologyEpisode as Private0
    from gene_annotation_episode.episodic_workflow.root.a104.homology_job_monitoring.episode import HomologyEpisode as Private1
    from gene_annotation_episode.episodic_workflow.root.a104.homology_result_acquisition.episode import HomologyEpisode as Private2
    return {binding.roles[0]: binding for binding in (
        Private0(*args, **configuration), Private1(*args, **configuration), Private2(*args, **configuration))}


def create_homology_family(jobs, *, parser_policy, credit_projector, credit_binding,
                           monitoring_projector, monitoring_binding, statistics=None):
    """Caller opt-in to original three-role resources and private child owners."""
    from .homology_binding_family import HomologyBindingFamily
    return HomologyBindingFamily(jobs, parser_policy=parser_policy,
        credit_projector=credit_projector, credit_binding=credit_binding,
        monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding,
        statistics=statistics)


def restore_homology_family(descriptor, jobs, *, parser_policy, credit_projector,
                            credit_binding, monitoring_projector, monitoring_binding,
                            statistics=None):
    """Restore only the exact v4 record against actual caller-owned resources."""
    from .homology_family_restore import restore_homology_family as restore
    return restore(descriptor, jobs, parser_policy=parser_policy,
        credit_projector=credit_projector, credit_binding=credit_binding,
        monitoring_projector=monitoring_projector, monitoring_binding=monitoring_binding,
        statistics=statistics)
