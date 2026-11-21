"""The task: one action, ``extract``, on one table region of a source's text.

The table region is the leaf's one input unit (``input_list``): it is extracted once and then consumed (nano-graphrag's
processed table region), never offered for a re-extraction. The model is asked once, with the region shown as segments with
their exact byte offsets, for the axis's extraction form: the typed commit of what the table reports with its grading (the
subscoring sheet saved in the same unit, and the cell rows of the grading components the parent requested) or the
source-grounded no-applicable-evidence declaration, and the source lead of the commission. The leaf has no access tool, no
population tool and no reasoning commit that assesses anything: its one unit is the library's ``extract``
(``literature_leaf_extraction``), called with this episode's pieces: the text is called the table (``TEXT``) and the goal is
this episode's. There is no model call after the extraction."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_leaf_extraction import (
    extract as extract_item, extraction_call, extraction_request)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'table'   # what the model is told it reads, and the context key of the text


def extract(arguments, ctx):
    """The unit: the graded typed commit of the table region, held through the custody-scoped store."""
    return extract_item(arguments, ctx)


TOOLS = {'extract': extract}


def decide(summary, feedback, ctx):
    return extraction_request(summary, feedback, ctx, goal=GOAL, text=TEXT)


def action(response, summary, records, ctx):
    return extraction_call(response, summary)


def offered_actions(summary, ctx):
    """The one action type offered: ``extract``."""
    return list(TOOLS)
