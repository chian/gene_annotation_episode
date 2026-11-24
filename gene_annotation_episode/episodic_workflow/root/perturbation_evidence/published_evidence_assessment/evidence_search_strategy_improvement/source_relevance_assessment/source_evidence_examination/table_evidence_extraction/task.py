"""The task: one action, ``extract``, on ONE table region (a byte window of the page's source that holds a table). The model
is asked, with the table, to fill the perturbation form (the library's ``literature_leaf_extraction``: quotations only, every
quotation found once in the table; the model is told how a table states a value, ``READING``). ``action`` checks the answer
(an answer that is not in the form, or a quotation that is not in the table exactly once, is rejected before any unit exists
and ``decide`` asks again with the reason). The unit, ``extract``, saves the perturbation sheet through the population route
over the custody-scoped store; a refusal of the route is the unit's ``invalid`` outcome and enters the iterator. The region is
the leaf's one input unit (``input_list``): once extracted it is consumed (nano-graphrag's selected table region) and never
offered again. The selection is a byte window only: the leaf has no reading tool for a sheet's rows, no reasoning commit, no
other population and no other task kind."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_leaf_extraction import (
    extraction_call, extraction_request, perturbation_extraction)

from .goal import GOAL, ROLE

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'table'   # what the model is told it reads, and the context key of the text
READING = (
    '\nThe table states a value in a cell: the value belongs to the row and the column the cell is in, so read each value '
    'with its row label and its column heading, and take its unit from the cell or, when the cell has none, from the '
    'heading of its column. A quotation is a span of the table text exactly as written; when the value alone occurs more '
    'than once, extend the quotation along its row until it occurs once.')


def decide(summary, feedback, ctx):
    """The extraction of the table region while it is unread (``input_list``); once extracted it is consumed, the yield
    estimator ends the episode, and a decision asked for with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return extraction_request(summary['table'], feedback, text=TEXT, reading=READING)


def action(response, summary, records, ctx):
    return extraction_call(response, summary['table'], page=summary['page'], offset=summary['offset'],
                           scope=summary['scope'], assignment=summary['literature_assignment'],
                           proposed_annotation_ref=summary['proposed_annotation_ref'])


def extract(arguments, ctx):
    """Save the perturbation sheet of the answer; return the route's outcome."""
    return perturbation_extraction(arguments, ctx, ROLE, GOAL)


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
