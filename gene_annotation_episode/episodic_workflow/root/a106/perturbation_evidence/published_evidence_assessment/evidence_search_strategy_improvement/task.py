"""The task: write the searches the assigned question needs, one query at a time, and hand each to the search child.

This is nano-graphrag's strategy: it proposes searches and hands the search level one query at a time; a query handed
out is done. It cannot search, fetch or read a paper (the levels above the search level only hand a task down; a
paper is obtained by the search level, when it builds the page). The model is offered ``write_search`` (it writes one
literature query), the reading of the records this episode holds (``state_query``) and the search child. It commits
no reasoning and grades nothing: the sheets are graded automatically below, where a leaf extracts what it finds, and
what returns here is the credit and the controlled features of those sheets, with the sources the searches verified
as leads.

The query is the only text this episode writes. It is kept as a record of this episode (a ``source`` record whose
``request_ref`` artifact holds the request, written through the scoped store, as the acquisition tools record a
provider request; it is no search response, so it is no hit list), and the child receives its reference
(``search_query_ref``), never the text: controlled messaging passes record references.

Carried from the old task.py, task_decision.py, task_action.py, task_instructions.py, source_contracts.py of
``literature_strategy`` at 97308b94c. One unit is one model-selected tool call or one commissioned search. The task
always offers a unit and never ends the Episode: only the yield controller does. The old ``wait`` and
``redeliver_report`` actions are not carried (a child completes inside the unit that commissioned it).

Not carried, and the reason: the acquisition and access tools (a search, a fetch or a read of a paper belongs to the
levels below), the reasoning commit and the population route with the automatic score judgment (assessment is not a
reasoning commit and the sheets are saved by the leaves), the sources of earlier searches and the commission of a
search over several returned sources (the search child takes one query), and every task kind but
``verified_source_leads``."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, canonical, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The old role of ``_CHILDREN['literature_strategy']``, under its old name.
CHILD_SLOTS = {
    'literature_search': ('perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                          'source_relevance_assessment'),
}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

# The reading of the records this episode holds (the old access tool ``state.query``).
STATE_QUERY = 'state.query'
STATE_QUERY_DESCRIPTION = (
    'Read an exact page of typed scientific records, current revisions, or records referring to actual references. '
    'Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be '
    'combined with page selectors.')
STATE_QUERY_SCHEMA = obj({
    'kind': {'enum': list(RECORD_SCHEMAS) + ['subject']}, 'offset': INTEGER, 'limit': POSITIVE,
    'refs': {**REFS,
             'description': 'Exact reference mode: supply refs alone, including an empty array for no records. '
                            'Omit kind, offset, limit, current_only and references in this mode.'},
    'current_only': {'type': 'boolean'},
    'references': {'type': 'array', 'items': REF, 'minItems': 1,
                   'description': "Select records that refer to any supplied ID through reference fields or "
                                  "provenance anchors. This does not match a record's own ID; to read known "
                                  "records themselves, supply refs alone instead."}}, required=[])

# The tool the model writes a search with: the arguments of the provider literature search.
WRITE_SEARCH = 'write_search'
WRITE_SEARCH_DESCRIPTION = (
    'Write one literature search (the arguments of the provider literature search: the query, optionally the page '
    'size and cursor). Nothing is searched here: the search is kept as a record of yours and appears in input_list '
    'with its reference; hand its reference to the search child, which runs it. A search handed out is done.')
WRITE_SEARCH_SCHEMA = obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query'])
SEARCH_REQUEST_PROVIDER = 'europepmc_search_request'

COMMISSION = {
    'literature_search': 'Commission the search of one query you wrote (search_query_ref, one reference of input_list: '
                         'the searches you have written with write_search and not yet handed out; you hand over '
                         'only the reference, never text or papers). The child runs the search against the provider, '
                         'measures each hit of the results against the question, picks the hit worth examining, '
                         'obtains that paper and has it examined, and returns its credit, the controlled features '
                         'of the A106 sheets graded below it and the sources it verified as leads. A search handed '
                         'to the child is done: it is not offered again.'}
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_literature_outcomes; that page creates no new '
                    'action and does not execute or credit the historical work again.')
COMMISSION_GUIDANCE = ('\nWrite one search (write_search), then commission the search child with its reference '
                       '(literature_search). Your input list (input_list) is the searches you have written that no '
                       'search child has been handed; a search handed out is consumed (consumed_inputs) and is not '
                       'offered again, and while the list is empty no search child is offered. written_searches '
                       'shows each query you wrote and what its search returned: write the next query from that. '
                       'You cannot search, fetch or read a paper, and you assess no evidence: grading is automatic, '
                       'below. The numerical controller alone decides whether the investigation continues.')


def instructions():
    """The investigation text this episode shows: its goal, the history paragraph and the commission guidance. The
    library's reasoning-commit, acquisition and read texts are not carried: this episode has no such action."""
    return GOAL + '\n' + HISTORY_GUIDANCE + COMMISSION_GUIDANCE


def offered():
    """The tools offered now: the reading of held records and the writing of one search."""
    return ['state_query', WRITE_SEARCH]


def catalog():
    """The tools the model is shown: name, description and input schema."""
    return [{'name': 'state_query', 'description': STATE_QUERY_DESCRIPTION,
             'input_schema': source_location_inputs(STATE_QUERY_SCHEMA)},
            {'name': WRITE_SEARCH, 'description': WRITE_SEARCH_DESCRIPTION,
             'input_schema': source_location_inputs(WRITE_SEARCH_SCHEMA)}]


def commission_arguments(input_list):
    """The arguments of a commission: the one query, a reference of the input list only (a search handed out is
    consumed and cannot be selected again)."""
    return obj({'search_query_ref': {'enum': list(input_list)}})


def commissions(input_list):
    """The searches the model may commission now, shown with the tools (the old ``child_option_information``): none
    while the input list is empty (nano-graphrag: child options only for unconsumed inputs)."""
    if not input_list:
        return []
    return [{'slot': slot, 'description': COMMISSION[slot], 'input_schema': commission_arguments(input_list)}
            for slot in CHILD_SLOTS]


def selection_schema(input_list):
    """What the model answers with: one tool and its arguments, or one commissioned search (the old action
    schema)."""
    return obj({'selection': {'anyOf': [
        *(obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
          for entry in catalog()),
        *(obj({'kind': {'const': 'child'}, 'slot': {'const': entry['slot']}, 'arguments': entry['input_schema']})
          for entry in commissions(input_list))]}})


def admitted(arguments):
    """The arguments against the offered schema. A violation is a ``ContractError``."""
    validate_schema(arguments, source_location_inputs(STATE_QUERY_SCHEMA))


async def state_query(arguments, ctx):
    """Execute the read of held records. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any
    other."""
    envelope = arguments
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        admitted(arguments)
    except (ContractError, ValidationError) as error:
        detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': STATE_QUERY,
                                                        'arguments': arguments}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    try:
        return await registry.execute_async(STATE_QUERY, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=None)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


def write_search(arguments, ctx):
    """One written search: no provider is contacted. The search the model wrote (the arguments of the provider
    literature search) is kept as a record of this episode, written through the scoped store: a ``source`` record
    whose ``request_ref`` artifact holds the request. Its reference is what the strategy hands the search child,
    which reads the request through custody and runs it."""
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


TOOLS = {'state_query': state_query, WRITE_SEARCH: write_search}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the assignment, its own outcomes, the searches it wrote and what each
    returned, the controlled features of the A106 sheets saved below, the tools and the search it may commission, the
    measured time and the yield table (the old decision state and inputs, over this episode's summary)."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'credit_binding': summary['credit_binding'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'a106_findings': summary['a106_findings'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'written_searches': summary['written_searches'], 'child_reports': summary['child_reports'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'tools': catalog(), 'child_options': commissions(summary['input_list']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(), context,
                        generation_schema(selection_schema(summary['input_list'])))


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names of the tools ``decide`` shows and, while a written search
    not yet handed out remains, the search child."""
    return [*(entry['name'] for entry in catalog()), *(entry['slot'] for entry in commissions(summary['input_list']))]


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit). An answer that selects
    no offered tool or search, arguments that do not fit its schema, or a search naming a record this episode does
    not hold is invalid."""
    schema = selection_schema(summary['input_list'])
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        if selection['kind'] == 'child':
            reference = selection['arguments']['search_query_ref']
            if not records.holds(reference):
                raise ContractError('literature_reference_unavailable', detail={'reference': reference})
            return ChildCall(selection['slot'], selection['arguments'])
        name, arguments = selection['tool'], selection['arguments']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})
