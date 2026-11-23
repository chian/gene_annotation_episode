"""Continuation: the completion controller over the leaf's credit (half the share of the commission's windows read plus
half the share of the asked fields the held records newly state, ``credit.credit``), target 1.0; it stops the Episode when
the forecast of the credit still to come is at or below its cost. Each new window earns its share of the coverage, so the
Episode reads on while windows remain. Not the forecast controller: see chunk/yield_estimator.py (a refused first
extraction never ends the Episode). The owner's one more stopping condition: when no item remains on the leaf's input
list, stop. The list is the commissioned windows (``read_from_parent``'s ``windows``), each extraction consumes one, so
the Episode stops at the latest after the extraction of the last window (``ListBoundCompletionYieldController``: the
completion controller, unchanged, plus that condition)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_leaf_list_stop import (
    ListBoundCompletionYieldController)

TARGET = 1.0


def yield_controller(initial_credit, settings, parent_input):
    return ListBoundCompletionYieldController('report', initial_credit, settings['cost'], TARGET,
                                              settings['parameters'], items=len(parent_input['windows']))


def items_remaining(summary):
    """The texts still on the input list: a text leaves it when an extraction of it had every form accepted (or named no
    method); while a form is refused it stays, and the further attempt is a unit the estimator sees."""
    return len(summary['input_list'])
