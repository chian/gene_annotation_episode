"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.presentation import (
    resource_information, received_api_information, scientific_blast_information, received_rna_information)

def initial_information(context, catalog):
    readers = catalog.readers('scientific_process', context)
    value = resource_information(readers)
    value.update(received_api_information(context, readers))
    value.update(scientific_blast_information(context, readers))
    value.update(received_rna_information(context, readers))
    return value
