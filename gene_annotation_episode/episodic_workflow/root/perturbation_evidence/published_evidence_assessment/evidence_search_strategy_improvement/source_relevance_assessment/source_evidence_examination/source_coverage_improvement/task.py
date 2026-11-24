"""The task: one action, ``extract``, on the next window of the assigned source read in document order (nano-graphrag's
``ReportWindowSource``: the remaining text read in document order, each window once). The leaf is commissioned with its
windows in order (``spans``); unit k is asked, with the text of the k-th window, to fill the perturbation form (the library's
``literature_leaf_extraction``: quotations only, every quotation found once in the window). ``action`` checks the answer (an
answer that is not in the form, or a quotation that is not in the window exactly once, is rejected before any unit exists and
``decide`` asks again with the reason). The unit, ``extract``, saves the perturbation sheet through the population route over
the custody-scoped store; a refusal of the route is the unit's ``invalid`` outcome and enters the iterator. A window that has
been extracted is consumed (``input_list`` in ``messages/internal_summary.py``) and never offered again. The leaf has no
reading tool, no reasoning commit, no other population and no other task kind."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_leaf_extraction import (
    extraction_call, extraction_request, perturbation_extraction)

from .goal import GOAL, ROLE

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'window'   # what the model is told it reads, and the context key of the text


def decide(summary, feedback, ctx):
    """The extraction of the first unread window (``input_list``); a window extracted is consumed, so with the list empty
    the yield estimator has ended the episode and a decision asked for is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return extraction_request(summary['window'], feedback, text=TEXT)


def action(response, summary, records, ctx):
    return extraction_call(response, summary['window'], page=summary['page'], offset=summary['offset'],
                           scope=summary['scope'], assignment=summary['literature_assignment'],
                           proposed_annotation_ref=summary['proposed_annotation_ref'])


def extract(arguments, ctx):
    """Save the perturbation sheet of the answer; return the route's outcome."""
    return perturbation_extraction(arguments, ctx, ROLE, GOAL)


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
