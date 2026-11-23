"""Continuation: the commission is one extraction of one chunk, so it is finite. Its credit (the share of the
asked fields the extraction newly states) counts toward the target of all of them, and the estimator stops the
Episode when the forecast of the credit still to come is at or below its cost. The owner's one more stopping condition:
when no item remains on the leaf's input list, stop. The list is the one commissioned window, and the extraction of it
consumes it, so the Episode stops after its extraction (``ListBoundCompletionYieldController``: the completion
controller, unchanged, plus that condition)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_leaf_list_stop import (
    ListBoundCompletionYieldController)

TARGET = 1.0
ITEMS = 1        # the input list: the one window [offset, offset + limit] of the commission


def yield_controller(initial_credit, settings, parent_input):
    return ListBoundCompletionYieldController('chunk', initial_credit, settings['cost'], TARGET,
                                              settings['parameters'], items=ITEMS)


def items_remaining(summary):
    """The texts still on the input list: a text leaves it when an extraction of it had every form accepted (or named no
    method); while a form is refused it stays, and the further attempt is a unit the estimator sees."""
    return len(summary['input_list'])
