"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_initial_information.presentation import (
    resource_information)

def initial_information(context, catalog):
    readers = catalog.readers('hpc_work_planning/hpc_resource_prediction', context)
    value = resource_information(readers)
    return value
