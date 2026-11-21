"""The task: the leaf extraction of a source in document order, window after window, for the sheet class of the claim. The
page has not read the source, so the commission names the sheet class (``sheet_class``), not an experiment type. Unit k is
asked, with the text of the k-th window (``messages/internal_summary.py``), to NAME the method that window reports, from the
experiment types of the class (each shown with its plain line) or ``none`` (the library's ``method_request`` and
``method_call``). The unit, ``extract``, then has the model fill the named type's form with its identity block, quote-only,
through the unit's recorded model (the library's ``extraction_arguments``); code validates every quote (found once in the
window), finds its span and holds the immutable leaf record of that window, which carries the type named. A window named
``none`` is done without a record. The experiment ref is ``kind:source:offset-end`` of the window, so each window's record
is its own. The windows are the page's remaining prose chunks in document order (``windows`` of the commission); each is
read once and removed from the input list (``input_list``), never re-read. The naming and the fill are the model calls of
one unit, so a window is one unit and the yield estimator's item count (the windows) is the windows to do. One method is
named per window. The leaf grades and judges nothing: the page groups the leaf records of its chunk, table and report
children into graders."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_arguments, leaf_record, method_call, method_request)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical)

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'window'   # what the model is told it reads, and the context key of the text


def decide(summary, feedback, ctx):
    """The naming of the method the first unread window reports (``input_list``); a read window is consumed and never
    offered again. With every window read the input list is empty and the episode's yield estimator ends it, so a decision
    asked for with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return method_request(summary['sheet_class'], summary['window'], feedback, text=TEXT)


def action(response, summary, records, ctx):
    return method_call(response, summary['sheet_class'], summary['window'], summary['already_stated_fields'],
                       summary['not_yet_stated_fields'], source_ref=summary['source_ref'], offset=summary['offset'],
                       limit=summary['limit'], assertion_ref=summary['proposed_annotation_ref'])


async def extract(arguments, ctx):
    """Fill the form of the type the model named for this window and hold its record; return its ref and the type named.
    A window named ``none`` holds no record (``record_ref`` None)."""
    if arguments['experiment_type'] is None:
        return {'status': 'completed', 'experiment_type': None, 'record_ref': None}
    filled = await extraction_arguments(ctx.model, arguments, text=TEXT)
    record_ref = ctx.store.artifact(canonical(leaf_record(filled)), 'application/json')
    return {'status': 'completed', 'experiment_type': arguments['experiment_type'], 'record_ref': record_ref}


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
