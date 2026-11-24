"""The task: nano-graphrag's strategy. It proposes searches (queries) and hands the search level ONE query at a time; a
query handed out is done. It cannot search, fetch or read, and it commits no reasoning (grading is automatic, far below).

The model WRITES a query (the tool ``write_search``: the arguments of ``public.literature.search``), which this episode
keeps as a record of its own (a ``source`` record whose ``request_ref`` artifact holds the query, written through the
scoped store, as the acquisition tools record a provider request), and selects the child with the child's objective and
the reference of ONE query it has written and not yet handed out (``search_query_ref``); ``messages/msg_to_child.py``
builds the commission, which passes only the reference (no query text travels between episodes). The web search child
reads the record through custody and runs the provider search. A child is a unit like any other: what it earns in this
episode is this episode's own credit. The task always offers a unit and never ends the Episode: only the yield
controller does. Its list is the queries it has handed out (``consumed_inputs``)."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    canonical, obj, identity, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from .goal import GOAL

CHILD_SLOTS = {
    'web_search': 'experimental_activity_evidence/literature/strategy/web_search',
}
SERVICES = ()

OBJECTIVE = {'type': 'string', 'minLength': 1,
             'description': 'What the child should look for in the results of the query and why'}
CHILD_DESCRIPTION = (
    'Hand the search child ONE query you have written (input_list: the queries you wrote with write_search and have '
    'not yet handed out; you hand over only the reference of the query, never text or papers). The child runs the '
    'provider search, measures each hit against the claim, picks one hit, opens its paper as a page and the page '
    'examines it; the sheet states and the credit come back to you. A query handed to the child is done: it is not '
    'offered again, and a paper its pages examined is not opened again. You run no search and read no paper yourself, '
    'and writing a query earns no credit.')
# The tool the model writes a query with. Code keeps it as a record of this episode and the web search child runs it.
WRITE_SEARCH = 'write_search'
WRITE_SEARCH_DESCRIPTION = (
    'Write one literature query (the arguments of the provider literature search: the query, optionally the page '
    'size and cursor). Nothing is searched here: the query is kept as a record of yours and appears in input_list '
    'with its reference; hand its reference to the search child, which runs it.')
SEARCH_DEFINITION = access_library._DEFINITIONS['public.literature.search']
SEARCH_REQUEST_PROVIDER = 'europepmc_search_request'


def search_schema(input_list):
    """The one query the model may hand to the child: written and not yet handed out (the input list)."""
    return {'enum': list(input_list)}


def child_arguments(slot, input_list):
    """The description and arguments schema of a child, over the input list now."""
    return CHILD_DESCRIPTION, obj({'objective': OBJECTIVE, 'search_query_ref': search_schema(input_list)})


def valid_slots(input_list):
    """The child slots valid now: the search child while a written query not yet handed out remains."""
    return list(CHILD_SLOTS) if input_list else []


def write_search_entry():
    """The query-writing tool the model is shown: the arguments of ``public.literature.search``."""
    return {'name': WRITE_SEARCH, 'description': WRITE_SEARCH_DESCRIPTION, 'input_schema': SEARCH_DEFINITION[1]}


# Static form (the declared shape of each child's arguments, without the input list), kept for the binding test.
CHILD_ARGUMENTS = {slot: child_arguments(slot, ['<written query>']) for slot in CHILD_SLOTS}

INSTRUCTIONS = (
    'You own an iterative scientific annotation improvement, not a tool itinerary. You propose searches; you run none '
    'and read no paper. Select one unit per decision: write one query (write_search), or hand the search child one '
    'query you wrote. Nothing is assessed by a reasoning commit; grading of what the leaves extract is automatic and '
    'its results come back as child_returns. Only the numerical controller decides when you stop.\n')
CHILD_GUIDANCE = ('\nWrite a query (write_search), then select the search child with its objective and the reference of '
                  'the query you wrote; the child runs it. Revise terms in the next query in light of what the '
                  'children returned (child_returns) and of the queries already handed out (consumed_inputs). A child '
                  'earns credit in this episode only through the records it returns.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the grading sheets '
                   'your child returned (evidence type, quantity kind, measured effect, variance, log evidence '
                   'ratio, prediction model, criterion statuses); no prose of yours is returned.')


def instructions():
    return INSTRUCTIONS + '\n' + GOAL + CHILD_GUIDANCE + RETURN_GUIDANCE


def offered_actions(summary, ctx):
    """The action types offered at this decision: the writing of a query and the child slot while a written query not
    yet handed out remains."""
    return [WRITE_SEARCH, *valid_slots(summary['input_list'])]


def selection_schema(summary):
    """What the model answers with: the writing of a query and its arguments, or one child slot and its arguments; a
    child names only a written query not yet handed out."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': WRITE_SEARCH}, 'arguments': write_search_entry()[
        'input_schema']})]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot},
                     'arguments': child_arguments(slot, summary['input_list'])[1]})
                for slot in valid_slots(summary['input_list'])]
    return obj({'selection': {'anyOf': [*tools, *children]}})


def write_search(arguments, ctx):
    """One written query: no provider is contacted. The query the model wrote (the arguments of the provider
    literature search) is kept as a record of this episode, written through the scoped store: a ``source`` record
    whose ``request_ref`` artifact holds the request (as the acquisition tools record a provider request; it is no
    search response, so it is no hit list). Its reference is what the strategy hands the web search child, which reads
    the request through custody and runs it."""
    request = arguments['arguments']
    artifact = ctx.store.artifact(canonical(request), 'application/json')
    source = ctx.store.put('source', {'provider': SEARCH_REQUEST_PROVIDER, 'accession': None, 'uri': None,
                                      'artifact_ref': artifact, 'text_ref': None, 'request_ref': artifact,
                                      'version': None, 'retrieved_at': None}, origin='tool')
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': WRITE_SEARCH,
                                                    'arguments': request}),
            'record_refs': [source['id']], 'changed_record_refs': [], 'result': {'search_ref': source['id']},
            'feedback': None}


TOOLS = {WRITE_SEARCH: write_search}


def child_options(summary):
    """The children the model may select now: slot, description and the arguments it takes, over the written queries
    not yet handed out only."""
    return [{'slot': slot, 'description': child_arguments(slot, summary['input_list'])[0],
             'arguments': child_arguments(slot, summary['input_list'])[1]}
            for slot in valid_slots(summary['input_list'])]


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the assignment, its own outcomes, the credit definition, the queries
    written and handed out, the children's returns, the tools, the measured time and the yield table."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'child_returns': summary['child_returns'], 'child_options': child_options(summary),
               'tools': [write_search_entry()], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(), context, generation_schema(selection_schema(summary)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot, arguments that do not fit its schema, or a commission naming a query this episode
    does not hold is invalid (validation of the model's own answer). What ``msg_to_child`` builds is not checked here:
    a wrong commission fails where the child is built."""
    schema = selection_schema(summary)
    try:
        decoded = decode_response(response, schema)
        validate_schema(decoded, schema)
        selection = decoded['selection']
        if selection['kind'] == 'child':
            reference = selection['arguments']['search_query_ref']
            if not records.holds(reference):
                raise ContractError('literature_reference_unavailable', detail={'reference': reference})
            return ChildCall(selection['slot'], selection['arguments'])
        return ToolCall(selection['tool'], {'arguments': selection['arguments'], 'scope': summary['scope']})
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
