"""The task: one action, ``extract``, on one chunk of a source's text.

The commission names the relation the claim states (``claim_predicate``), not an experiment type: the page has not read the
chunk. At each decision the model NAMES the method the chunk reports, from the experiment types of the classes that list it (each shown with
its plain line) or ``none`` (the library's ``method_request`` and ``method_call``). The unit, ``extract``, then has the model
fill the named type's form with its identity block, quote-only, through the unit's recorded model (the library's
``extraction_attempt``: an answer that is not in the form, or a quote that is not in the chunk exactly once, is asked
again with the reason), and holds the record through the custody-scoped store; the record carries the type named. A chunk
named ``none`` is done without a record. Code picks the extraction module by the named type and, through the record's own
type, the grader; the model never calls the grader. The leaf extraction is the library's (``literature_leaf_extraction``),
called with this episode's pieces: the text is called the chunk (``TEXT``) and has no reading sentence of its own.

The chunk is the leaf's one input unit (``input_list``): it is named and extracted once and then consumed
(nano-graphrag's processed chunk), never offered again. The naming and the fill are the model calls of one unit, so the
item is one unit and the yield estimator's item count is the chunks to do. Every method the chunk reports is named (owner,
2026-11-22: multiple methods per passage allowed, no cap, behaviour to be watched): a chunk that reports results of two methods
gives two records, both filled within the one unit. Grading and judging belong to the page's
update. There is no model call after the extraction.
A form the validator refuses (a quote that is not in the text, a value that is not written in its quote) is an outcome of
the unit: no record is held for that type and the unit lists it under ``refused`` with the reason. The text then stays on
the input list, and the next unit reads it again for the refused types only, each with its reason shown to the model; a
further attempt is a unit like any other, so the yield estimator sees it and ends the leaf when attempts stop earning
(the earlier loop inside the unit, "asked again until accepted", had no end: see ``extraction_attempt``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    extract_types, method_call, method_request)

CHILD_SLOTS = {}
SERVICES = ()
TEXT = 'chunk'   # what the model is told it reads, and the context key of the text


def decide(summary, feedback, ctx):
    """The naming of the method the chunk reports while it is unread (``input_list``); once it has been extracted the
    chunk is consumed and is never offered again: the input list is empty and the episode's yield estimator ends it, so a
    decision asked for with an empty input list is an error."""
    if not summary['input_list']:
        raise LookupError('leaf_input_list_empty:' + TEXT)
    return method_request(summary['claim_predicate'], summary['chunk'], feedback or summary['refused'] or None,
                          text=TEXT)


def action(response, summary, records, ctx):
    return method_call(response, summary['claim_predicate'], summary['chunk'], summary['already_stated_fields'],
                       summary['not_yet_stated_fields'], source_ref=summary['source_ref'], offset=summary['offset'],
                       limit=summary['limit'], assertion_ref=summary['proposed_annotation_ref'],
                       refused=summary['refused'])


async def extract(arguments, ctx):
    """One attempt at the form of every type named, one after the other: an accepted form is held as one record, a
    refused one is listed with its reason (the library's ``extract_types``). Returns the record refs, the types named and
    what was refused. A text for which no method was named holds no record. No cap on the number of methods (owner,
    2026-11-22: multiple methods per passage allowed; behaviour to be watched)."""
    return await extract_types(ctx.model, ctx.store, arguments, text=TEXT)


TOOLS = {'extract': extract}


def offered_actions(summary, ctx):
    """The action types offered at this decision: the one tool, ``extract`` (``decide`` always asks for the naming)."""
    return list(TOOLS)
