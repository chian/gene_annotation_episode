"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_initial_information.presentation import (
    resource_information)

def initial_information(context, catalog):
    readers = catalog.readers('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', context)
    value = resource_information(readers)
    return value
