"""Continuation: the completion controller over the leaf's credit (the share of the asked fields the held records of the
table newly state), target 1.0; it stops the Episode when the forecast of the credit still to come is at or below its cost.
Not the forecast controller: see chunk/yield_estimator.py (a refused first extraction never ends the Episode). The
owner's one more stopping condition: when no item remains on the leaf's input list, stop. The list is the one
commissioned window, and the extraction of it consumes it, so the Episode stops after its extraction
(``ListBoundCompletionYieldController``: the completion controller, unchanged, plus that condition)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_leaf_list_stop import (
    ListBoundCompletionYieldController)

TARGET = 1.0
ITEMS = 1        # the input list: the one window [offset, offset + limit] of the commission


def yield_controller(initial_credit, settings, parent_input):
    return ListBoundCompletionYieldController('table', initial_credit, settings['cost'], TARGET,
                                              settings['parameters'], items=ITEMS)


def items_remaining(summary):
    """The texts still on the input list: a text leaves it when an extraction of it had every form accepted (or named no
    method); while a form is refused it stays, and the further attempt is a unit the estimator sees."""
    return len(summary['input_list'])
