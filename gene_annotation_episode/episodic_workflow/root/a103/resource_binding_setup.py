"""Construct the caller's declared root and scientific A103 resource portfolio."""
from __future__ import annotations


def create_resource_bindings(*args, **configuration):
    from .resource_work_submission.episode import ResourceEpisode as Launch
    from .resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as API
    from .resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as Local
    from .resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as HPC
    from .resource_result_acquisition.episode import ResourceEpisode as Results
    from .scientific_process.episode import create_resource_bindings as scientific_resources
    return (Launch(*args, **configuration), API(*args, **configuration),
            Local(*args, **configuration), HPC(*args, **configuration),
            Results(*args, **configuration), *scientific_resources(*args, **configuration))
