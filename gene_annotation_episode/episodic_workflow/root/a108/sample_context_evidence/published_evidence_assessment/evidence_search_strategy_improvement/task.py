"""The task: write one literature search, or hand a written search to the search child. This episode is
nano-graphrag's strategy: its model writes ONE query (the tool ``write_search``) and commissions the search child with
it; the query is kept in a record of this episode and passed BY REFERENCE (``search_query_ref``), never as text. It
offers its model NO tool that searches a provider, fetches a paper or reads a paper's text, and NO reasoning commit;
what is found below is graded below, automatically. A search handed to the child is done: it is not offered again
(its list is the searches it has handed out), and the child is offered only while a written search not yet handed out
remains.

Carried from the old task.py, task_decision.py, task_instructions.py and source_contracts.py of ``literature_strategy``
at 97308b94c (the old child role ``literature_search`` is the slot below). One unit is one model-selected written
search or one child commission. The task always offers a unit and never ends the Episode: only the yield controller
does. Removed with the owner's order of 2026-11-21: the acquisition and access tools, the two population operations,
the reasoning commit and the source leads, and the three task kinds other than the verified source leads.

The written search is a ``source`` record of this episode written through the scoped store: its ``request_ref``
artifact holds the arguments of the provider literature search (the query, optionally the page size and cursor) as the
acquisition tools record a provider request. It is no search response, so it is no hit list; the search child reads it
through custody and runs it."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    REF, canonical, identity, obj, validate_schema)

from .goal import GOAL

# The one child (the old ``_CHILDREN['literature_strategy']``: literature_search), by slot.
CHILD_SLOTS = {
    'source_relevance_assessment': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
}
SERVICES = ()

POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

WRITE_SEARCH = 'write_search'
WRITE_SEARCH_DESCRIPTION = (
    'Write one literature search (the arguments of the provider literature search: the query, optionally the page '
    'size and cursor). Nothing is searched here: the search is kept as a record of yours and appears in input_list '
    'with its reference; hand its reference to the search child, which runs it.')
WRITE_SEARCH_SCHEMA = obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query'])
SEARCH_REQUEST_PROVIDER = 'europepmc_search_request'

CHILD_DESCRIPTION = (
    'Hand ONE search you wrote (search_query_ref: a reference from input_list, the searches you have written and not '
    'yet handed out; you hand over the reference, never text) to the search child with the objective of its work. '
    'The child runs that search against the provider, measures each hit of its results against the question, picks '
    'one hit, and has that paper examined; what is found in the paper is graded there. A search handed to the child '
    'is done and is not offered again. You search, fetch and read nothing yourself.')
OBJECTIVE = {'type': 'string', 'minLength': 1,
             'description': 'What the child should look for in the results of the search and why'}
HISTORY_GUIDANCE = ('\nThe searches you wrote are shown as written_searches and your own earlier units as '
                    'own_literature_outcomes; that page creates no new action and does not execute or credit the '
                    'historical work again.')
CHILD_GUIDANCE = ('\nWrite a search (write_search), then hand it to the search child with its objective. Revise the '
                  'terms of the next search in light of what the child returned (child_returns). A child earns credit '
                  'in this episode only through the records it returns.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets your '
                   'descendants saved, with their references; nothing you write in prose is returned. Selecting a '
                   'tool never ends your work: only the numerical controller does.')


def child_arguments(input_list):
    """The child commission's arguments: ``search_query_ref`` names one search of the input list only, so a search
    already handed out (consumed) cannot be selected."""
    return obj({'objective': OBJECTIVE, 'search_query_ref': {**REF, 'enum': list(input_list)}})


def offered_children(input_list):
    """The child slots valid now: the search child while a written search not yet handed out remains."""
    return list(CHILD_SLOTS) if input_list else []


def instructions():
    return GOAL + HISTORY_GUIDANCE + CHILD_GUIDANCE + RETURN_GUIDANCE


def catalog(input_list):
    """The tool and the children the model is shown: name, description and input schema."""
    return [{'name': WRITE_SEARCH, 'description': WRITE_SEARCH_DESCRIPTION, 'input_schema': WRITE_SEARCH_SCHEMA},
            *({'name': name, 'description': CHILD_DESCRIPTION, 'input_schema': child_arguments(input_list)}
              for name in offered_children(input_list))]


def selection_schema(input_list):
    """What the model answers with: one tool or child and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'child' if entry['name'] in CHILD_SLOTS else 'tool'},
             'tool': {'const': entry['name']}, 'arguments': entry['input_schema']}) for entry in catalog(input_list)]}})


def write_search(arguments, ctx):
    """One written search: no provider is contacted. The search the model wrote is kept as a record of this episode,
    written through the scoped store: a ``source`` record whose ``request_ref`` artifact holds the request (as the
    acquisition tools record a provider request). Its reference is what the strategy hands the search child."""
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


def offered_actions(summary, ctx):
    """The action types offered at this decision: the writing of a search, and the search child while a written search
    not yet handed out remains."""
    return [entry['name'] for entry in catalog(summary['input_list'])]


def decide(summary, feedback, ctx):
    """Ask the model for the next search or child commission, shown the assignment, the searches it wrote, the input
    list, what the child returned, the credit definition, the tools, the measured time and the yield table."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'written_searches': summary['written_searches'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'child_returns': summary['child_reports'], 'tools': catalog(summary['input_list']),
               'feedback': feedback, 'action_yields': summary['action_yields'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions(), context,
                        generation_schema(selection_schema(summary['input_list'])))


def action(response, summary, records, ctx):
    """Turn the model's answer into one written search or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot, arguments that do not fit its schema, or a search this episode does not hold is
    invalid (validation of the model's own answer). What ``msg_to_child`` builds is not checked here: a wrong
    commission fails where the child is built."""
    schema = selection_schema(summary['input_list'])
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
        name, arguments = selection['tool'], selection['arguments']
        if selection['kind'] == 'child' and not records.holds(arguments['search_query_ref']):
            raise ValueError('literature_reference_unavailable:' + arguments['search_query_ref'])
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selection['kind'] == 'child':
        return ChildCall(name, arguments)
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})
