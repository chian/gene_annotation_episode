"""The task: the leaf extraction of ONE byte window of a source that holds a table, for ONE experiment type. The leaf
extraction is the library's (``literature_leaf_extraction``), called with this episode's pieces: the text is called the
table (``TEXT``) and the model is told how a table states a value (``READING``). The model is asked once per unit, with
the table's text, to fill the answer form of the commissioned experiment type with its identity block, quote-only; code
validates every quote (found once in the table), finds its span and holds the immutable leaf record; ``extract`` is the
one action. The leaf grades and judges nothing: the page groups the leaf records of its chunk, table and report children
into graders.

The selection is a byte window only. A sheet selection (an XLSX sheet's rows) has no text rendering in the A105 tools
(``source.xlsx.*`` has no A105 implementation), so it is not offered. The experiment ref is ``kind:source:offset-end`` of
the window. The window is the leaf's one input unit (``input_list``): it is extracted once and then consumed
(nano-graphrag's selected table region), never offered for a re-extraction."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_call, extraction_request, leaf_record)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'table'   # what the model is told it reads, and the context key of the text
READING = (
    '\nThe table states a value in a cell: the value belongs to the row and the column the cell is in, so read each value '
    'with its row label and its column heading, and take its unit from the cell or, when the cell has none, from the '
    'heading of its column. A quote is a span of the table text exactly as written; when the value alone occurs more than '
    'once, extend the quote along its row until it occurs once.')


def decide(summary, feedback, ctx):
    """The extraction of the table while it is unread (``input_list``); once it has been extracted the table region is
    consumed and is never offered again: the input list is empty and the episode's yield estimator ends it, so a
    decision asked for with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return extraction_request(summary['experiment_type'], summary['table'], feedback, summary['already_stated_fields'],
                              summary['not_yet_stated_fields'], text=TEXT, reading=READING)


def action(response, summary, records, ctx):
    return extraction_call(response, summary['experiment_type'], summary['table'], source_ref=summary['source_ref'],
                           offset=summary['offset'], limit=summary['limit'],
                           assertion_ref=summary['proposed_annotation_ref'])


def extract(arguments, ctx):
    """Hold the record (of the commissioned experiment type) the answer makes; return its ref."""
    record_ref = ctx.store.artifact(canonical(leaf_record(arguments)), 'application/json')
    return {'status': 'completed', 'record_ref': record_ref}


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
