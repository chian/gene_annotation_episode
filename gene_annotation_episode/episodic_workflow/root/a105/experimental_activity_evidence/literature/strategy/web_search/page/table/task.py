"""The task: the leaf extraction of ONE table region (a byte window of a source that holds a table), for the relation the claim states. The page has not read the table, so the commission names the relation the claim states (``claim_predicate``), not an experiment
type. At each decision the model NAMES the method the table reports, from the experiment types of the classes that list it (each shown with
its plain line) or ``none`` (the library's ``method_request`` and ``method_call``). The unit, ``extract``, then has the model
fill the named type's form with its identity block, quote-only, through the unit's recorded model (the library's
``extraction_arguments``); code validates every quote (found once in the table), finds its span and holds the immutable
leaf record, which carries the type named. A table named ``none`` is done without a record. The leaf extraction is the
library's (``literature_leaf_extraction``), called with this episode's pieces: the text is called the table (``TEXT``) and
the model is told how a table states a value (``READING``). The leaf grades and judges nothing: the page groups the leaf
records of its chunk, table and report children into graders.

The selection is a byte window only. A sheet selection (an XLSX sheet's rows) has no text rendering in the A105 tools
(``source.xlsx.*`` has no A105 implementation), so it is not offered. The experiment ref is ``kind:source:offset-end`` of
the window. The window is the leaf's one input unit (``input_list``): it is named and extracted once and then consumed
(nano-graphrag's selected table region), never offered again. The naming and the fill are the model calls of one unit, so
the item is one unit and the yield estimator's item count is the table regions to do. Every method the table region reports is
named and filled within the one unit, one record per method (owner, 2026-11-22: multiple methods per passage allowed)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extraction_arguments, leaf_record, method_call, method_request)
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
    """The naming of the method the table reports while it is unread (``input_list``); once it has been extracted the
    table region is consumed and is never offered again: the input list is empty and the episode's yield estimator ends
    it, so a decision asked for with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return method_request(summary['claim_predicate'], summary['table'], feedback, text=TEXT)


def action(response, summary, records, ctx):
    return method_call(response, summary['claim_predicate'], summary['table'], summary['already_stated_fields'],
                       summary['not_yet_stated_fields'], source_ref=summary['source_ref'], offset=summary['offset'],
                       limit=summary['limit'], assertion_ref=summary['proposed_annotation_ref'])


async def extract(arguments, ctx):
    """Fill the form of every type the model named, one after the other, and hold one record for each; return their refs
    and the types named, in the order named. A text for which no method was named holds no record (both lists empty).
    No cap on the number of methods (owner, 2026-11-22: multiple methods per passage allowed; behaviour to be watched)."""
    record_refs = []
    for experiment_type in arguments['experiment_types']:
        filled = await extraction_arguments(ctx.model, {**arguments, 'experiment_type': experiment_type}, text=TEXT, reading=READING)
        record_refs.append(ctx.store.artifact(canonical(leaf_record(filled)), 'application/json'))
    return {'status': 'completed', 'experiment_types': list(arguments['experiment_types']), 'record_refs': record_refs}


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract``."""
    return list(TOOLS)
