"""The task: one action, ``extract``, on one chunk of a source's text.

The commission names the kind of experiment (``experiment_type``, a controlled value of the library's ``FORMS``). Code
picks, by that value, the extraction module and, through the record's own type, the grader; the model never picks either
and never calls the grader. The leaf extraction is the library's (``literature_leaf_extraction``), called with this
episode's pieces: the text is called the chunk (``TEXT``) and has no reading sentence of its own.

The chunk is the leaf's one input unit (``input_list``): it is extracted once and then consumed (nano-graphrag's
processed chunk), never offered for a re-extraction.

The model is asked once per unit, with the chunk, to fill the answer form of that kind with its identity block.
``action`` checks the answer (an answer that is not in the form, or a quote that is not in the chunk exactly once, is
rejected before any unit exists and ``decide`` asks again with the reason). The unit, ``extract``, turns the valid answer
into the record of that kind and holds it through the custody-scoped store; the leaf's output is that immutable record
(its ref) and nothing else. Grading and judging belong to the page's update. There is no model call after the
extraction."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_call, extraction_request, leaf_record)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'chunk'   # what the model is told it reads, and the context key of the text


def decide(summary, feedback, ctx):
    """The extraction of the chunk while it is unread (``input_list``); once it has been extracted the chunk is
    consumed and is never offered again: the input list is empty and the episode's yield estimator ends it, so a
    decision asked for with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return extraction_request(summary['experiment_type'], summary['chunk'], feedback, summary['already_stated_fields'],
                              summary['not_yet_stated_fields'], text=TEXT)


def action(response, summary, records, ctx):
    return extraction_call(response, summary['experiment_type'], summary['chunk'], source_ref=summary['source_ref'],
                           offset=summary['offset'], limit=summary['limit'],
                           assertion_ref=summary['proposed_annotation_ref'])


def extract(arguments, ctx):
    """Hold the record (of the commissioned experiment type) the answer makes; return its ref."""
    record_ref = ctx.store.artifact(canonical(leaf_record(arguments)), 'application/json')
    return {'status': 'completed', 'record_ref': record_ref}


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract`` (``decide`` always asks for an extraction)."""
    return list(TOOLS)
