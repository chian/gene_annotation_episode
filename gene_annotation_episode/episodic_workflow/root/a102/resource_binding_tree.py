"""Actual A102 service resource portfolio, preserving both original parent contexts."""
def create_resource_bindings(*args, **configuration):
    from .resource_work_submission.episode import ResourceEpisode as Private0
    from .resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as Private1
    from .resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as Private2
    from .resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as Private3
    from .resource_result_acquisition.episode import ResourceEpisode as Private4
    from .structural_homology_evidence.resource_work_submission.episode import ResourceEpisode as Private5
    from .structural_homology_evidence.resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as Private6
    from .structural_homology_evidence.resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as Private7
    from .structural_homology_evidence.resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as Private8
    from .structural_homology_evidence.resource_result_acquisition.episode import ResourceEpisode as Private9
    return (
        Private0(*args, **configuration),
        Private1(*args, **configuration),
        Private2(*args, **configuration),
        Private3(*args, **configuration),
        Private4(*args, **configuration),
        Private5(*args, **configuration),
        Private6(*args, **configuration),
        Private7(*args, **configuration),
        Private8(*args, **configuration),
        Private9(*args, **configuration),
    )
