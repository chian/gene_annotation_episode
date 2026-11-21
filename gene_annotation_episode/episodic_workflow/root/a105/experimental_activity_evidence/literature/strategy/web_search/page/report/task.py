"""The task: the leaf extraction of a source in document order, window after window, for ONE experiment type. Each window's
extraction is the library's (``literature_leaf_extraction``), called with this episode's pieces: the text is called the
window (``TEXT``) and has no reading sentence of its own. Unit k is asked, with the text of the k-th window
(``messages/internal_summary.py``), to fill the answer form of the commissioned experiment type with its identity block,
quote-only; code validates every quote (found once in the window), finds its span and holds the immutable leaf record of
that window; ``extract`` is the one action. The experiment ref is ``kind:source:offset-end`` of the window, so each
window's record is its own. The windows are the page's remaining prose chunks in document order (``windows`` of the
commission); each is read once and removed from the input list (``input_list``), never re-read. The leaf grades and judges nothing: the page groups the leaf records of its chunk, table and
report children into graders."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_call, extraction_request, leaf_record)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'window'   # what the model is told it reads, and the context key of the text


def decide(summary, feedback, ctx):
    """The extraction of the first unread window (``input_list``); a read window is consumed and never offered again.
    With every window read the input list is empty and the episode's yield estimator ends it, so a decision asked for
    with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return extraction_request(summary['experiment_type'], summary['window'], feedback, summary['already_stated_fields'],
                              summary['not_yet_stated_fields'], text=TEXT)


def action(response, summary, records, ctx):
    return extraction_call(response, summary['experiment_type'], summary['window'], source_ref=summary['source_ref'],
                           offset=summary['offset'], limit=summary['limit'],
                           assertion_ref=summary['proposed_annotation_ref'])


def extract(arguments, ctx):
    """Hold the record (of the commissioned experiment type) the answer makes for this window; return its ref."""
    record_ref = ctx.store.artifact(canonical(leaf_record(arguments)), 'application/json')
    return {'status': 'completed', 'record_ref': record_ref}


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
