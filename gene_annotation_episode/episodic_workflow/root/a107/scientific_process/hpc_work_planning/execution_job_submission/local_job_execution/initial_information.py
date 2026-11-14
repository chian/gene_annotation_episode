"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.presentation import (
    resource_information, received_api_information)

def initial_information(context, catalog):
    readers = catalog.readers('scientific_process/hpc_work_planning/execution_job_submission/local_job_execution', context)
    value = resource_information(readers)
    value.update(received_api_information(context, readers))
    return value
