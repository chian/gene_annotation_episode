"""Continuation: the completion controller (``CompletionYieldController``) through the shared
``bvbrc_job_child.completion_controller``: continue until the credit reaches the commission's finite target; the cost is
``settings['cost']`` times the smallest credit unit of the commission, ``settings['parameters']`` are the estimator's."""
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    completion_controller)


def yield_controller(initial_credit, settings, parent_input):
    return completion_controller('bvbrc_msa', initial_credit, settings, parent_input)
