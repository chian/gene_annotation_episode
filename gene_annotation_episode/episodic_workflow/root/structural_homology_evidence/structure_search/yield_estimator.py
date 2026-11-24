"""Continuation: the completion controller (``CompletionYieldController``) through
``structure_search_child.completion_controller``: continue until the credit reaches the commission's finite target; the
target (``read_from_parent``) is the sum of the units still obtainable under the commission's ``until``: the model (unless one
is passed or a job is resumed), the estimate and the launch (unless a handoff is passed back), and for ``extracted`` the job
known ended and the graded result. At the target the remaining credit is exactly zero and the controller stops the episode at
once. A model source that has no model, a job that failed at the service or a monitor that keeps showing running leaves the
target unreached: the controller then winds the episode down by units that earn nothing. The cost is ``settings['cost']``
times the smallest credit unit of the commission; ``settings['parameters']`` are the estimator's."""
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    completion_controller)


def yield_controller(initial_credit, settings, parent_input):
    return completion_controller('structure_search', initial_credit, settings, parent_input)
