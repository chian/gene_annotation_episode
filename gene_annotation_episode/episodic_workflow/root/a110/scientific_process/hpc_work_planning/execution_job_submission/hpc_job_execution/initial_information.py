"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_initial_information.presentation import (
    resource_information)

def initial_information(context, catalog):
    readers = catalog.readers('scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution', context)
    value = resource_information(readers)
    return value
