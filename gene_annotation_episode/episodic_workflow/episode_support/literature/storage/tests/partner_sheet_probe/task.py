"""The task: carry out the plan, one publication or admission per unit.

The task always offers a unit; the Episode ends when its yield controller stops it, at the last plan step."""
from episode_runtime import Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_sheet_updates import DEPENDENCIES, CURRENT, admitted, current_sheet_refs

from .repository import ProbePartnerRepository

CHILD_SLOTS = {}
SERVICES = ()


def repository_and_context(ctx):
    context = LiteratureContext(run_id=ctx.run_id, episode_id=ctx.episode_id, role='probe', path=(), scope={},
                                assignment={}, received_record_refs=tuple(ctx.store.refs()))
    return ProbePartnerRepository(ctx.store, ctx.run_id), context


def state(store):
    return {'current': current_sheet_refs(store),
            'bindings': [[row['sheet_ref'], row['family'], row['receipt']['custody']]
                         for row in store.table(DEPENDENCIES).select()],
            'versions': [[row['family'], row['sheet_ref'], row['status'], row['detail']]
                         for row in store.table(CURRENT).select()]}


def populate(arguments, ctx):
    """Publish a sheet through the repository's wrapped ``populate``."""
    repository, context = repository_and_context(ctx)
    outcome = repository.populate(context, arguments['arguments'], ctx.operation_key)
    return {'outcome': outcome, **state(ctx.store)}


def admit(arguments, ctx):
    """Admit a sheet another episode produced and refresh what depends on it."""
    repository, context = repository_and_context(ctx)
    admitted(repository, context, [{'sheet_ref': arguments['ref']}], ctx.operation_key)
    return state(ctx.store)


TOOLS = {'populate': populate, 'admit': admit}


def decide(summary, feedback, ctx):
    item = summary['plan'][len(summary['outcomes'])]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    raise Rejected({'status': 'invalid', 'category': 'no_model_decision', 'detail': 'this task decides by plan'})
