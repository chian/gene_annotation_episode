"""The task: one action, ``extract``, on the next chunk of the assigned source's text. The leaf is commissioned with its
chunks (``spans``, each a byte window of the page's source in the page's representation); each is its own unit. The model is
asked, with the chunk, to fill the perturbation form (the library's ``literature_leaf_extraction``: quotations only, every
quotation found once in the chunk). ``action`` checks the answer (an answer that is not in the form, or a quotation that is not
in the chunk exactly once, is rejected before any unit exists and ``decide`` asks again with the reason). The unit,
``extract``, saves the perturbation sheet through the population route over the custody-scoped store; a refusal of the route
is the unit's ``invalid`` outcome and enters the iterator. A chunk that has been extracted is consumed (nano-graphrag's
processed chunk, ``input_list`` in ``messages/internal_summary.py``) and is never offered again. The leaf has no reasoning
commit, no access tool, no other population and no other task kind; what it computes it computes from the one chunk."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_leaf_extraction import (
    extraction_call, extraction_request, perturbation_extraction)

from .goal import GOAL, ROLE

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'chunk'   # what the model is told it reads, and the context key of the text


def decide(summary, feedback, ctx):
    """The extraction of the first unread chunk (``input_list``); a chunk extracted is consumed, so with the list empty the
    yield estimator has ended the episode and a decision asked for is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return extraction_request(summary['chunk'], feedback, text=TEXT)


def action(response, summary, records, ctx):
    return extraction_call(response, summary['chunk'], page=summary['page'], offset=summary['offset'],
                           scope=summary['scope'], assignment=summary['literature_assignment'],
                           proposed_annotation_ref=summary['proposed_annotation_ref'])


def extract(arguments, ctx):
    """Save the perturbation sheet of the answer; return the route's outcome."""
    return perturbation_extraction(arguments, ctx, ROLE, GOAL)


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
