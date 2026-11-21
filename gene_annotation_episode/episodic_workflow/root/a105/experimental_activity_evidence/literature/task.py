"""The task: the top of the literature chain. The model chooses, one unit at a time, between reading a record it holds
(``state_query``) and commissioning the strategy child with an objective. It runs no provider search, obtains or reads
no paper and commits no reasoning: nano-graphrag's levels above the search level cannot reach a paper, and nothing is
assessed by a reasoning commit (grading is automatic, code attached to the leaf units far below). The only task is
``verified_source_leads`` (``messages/read_from_parent.py``); the strategy is handed no prior search and no source.

Child. The slot below is the old ``_CHILDREN['literature']`` (the strategy) under the name of its folder. The model
selects it with the child's objective alone (as nano-graphrag's run hands a strategy its objective): the strategy writes
its own searches; ``messages/msg_to_child.py`` builds the commission. A child is a unit like any other: what it earns in
this episode is this episode's own credit. The task always offers a unit and never ends the Episode: only the yield
controller does."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome
from .goal import GOAL

CHILD_SLOTS = {
    'strategy': 'experimental_activity_evidence/literature/strategy',
}
SERVICES = ()

# The one library tool this episode offers: the reading of records it holds. No tool that runs a provider search or
# obtains or reads a paper is offered to it.
STATE_QUERY = 'state.query'
STATE_QUERY_DEFINITION = access_library._DEFINITIONS[STATE_QUERY]
TOOL_NAME = 'state_query'

OBJECTIVE = {'type': 'string', 'minLength': 1,
             'description': 'What the child should investigate about the search approach and why'}
CHILD_DESCRIPTION = (
    'Investigate which searches are productive for the claim. You hand the strategy your objective only; it writes '
    'the searches itself and has them run, one at a time. Below it each search returns papers, a paper is picked and '
    'opened as a page, the page has its passages and tables measured and the leaves below it extract what they '
    'find and grade it automatically; the sheet states and the credit come back to you. You run no search and read no '
    'paper yourself.')


def child_arguments(slot):
    """The description and arguments schema of a child: its objective only (it writes its own searches)."""
    return CHILD_DESCRIPTION, obj({'objective': OBJECTIVE})


def valid_slots():
    return list(CHILD_SLOTS)


# The declared shape of each child's arguments, kept for the binding test.
CHILD_ARGUMENTS = {slot: child_arguments(slot) for slot in CHILD_SLOTS}

INSTRUCTIONS = (
    'You own an iterative scientific annotation improvement, not a tool itinerary. You run no provider search, obtain '
    'no paper and read no paper: the strategy child proposes searches and everything below it examines the papers. '
    'Select one unit per decision: the reading of a record you hold (state_query) or the strategy child with its '
    'objective. Nothing is assessed by a reasoning commit; grading of what the leaves extract is automatic and its '
    'results come back as child_returns. Only the numerical controller decides when you stop.\n')
CHILD_GUIDANCE = ('\nSelect the strategy child with its objective; what it returns is shown to you as child_returns. A '
                  'child earns credit in this episode only through the records it returns.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the grading sheets '
                   'your child returned (evidence type, quantity kind, measured effect, variance, log evidence '
                   'ratio, prediction model, criterion statuses); no prose of yours is returned.')


def instructions():
    return INSTRUCTIONS + '\n' + GOAL + CHILD_GUIDANCE + RETURN_GUIDANCE


def catalog():
    """The tool the model is shown: python tool name, description and input schema."""
    description, schema = STATE_QUERY_DEFINITION
    return [{'name': TOOL_NAME, 'description': description, 'input_schema': source_location_inputs(schema)}]


def selection_schema():
    """What the model answers with: the record reading and its arguments, or the strategy slot and its arguments."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in catalog()]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'arguments': child_arguments(slot)[1]})
                for slot in valid_slots()]
    return obj({'selection': {'anyOf': [*tools, *children]}})


def invalid(arguments, ctx, error):
    """A contract error of the model's own arguments: an ``invalid`` outcome with feedback."""
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': STATE_QUERY,
                                                    'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def state_query(arguments, ctx):
    """The reading of records this episode holds (the library's ``state.query``)."""
    given, scope = arguments['arguments'], arguments['scope']
    try:
        validate_schema(given, source_location_inputs(STATE_QUERY_DEFINITION[1]))
    except (ContractError, ValidationError) as error:
        return invalid(given, ctx, error)
    registry = access_library.A105ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    try:
        return await registry.execute_async(STATE_QUERY, given, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=None)
    except CustodyError:
        raise
    except Exception as error:   # a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


TOOLS = {TOOL_NAME: state_query}


def child_options():
    """The children the model may select now: slot, description and the arguments it takes."""
    return [{'slot': slot, 'description': child_arguments(slot)[0], 'arguments': child_arguments(slot)[1]}
            for slot in valid_slots()]


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the assignment, its own outcomes, the credit definition, the children's
    returns, the tools, the measured time and the yield table."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'],
               'child_returns': summary['child_returns'], 'child_options': child_options(),
               'tools': catalog(), 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(), context, generation_schema(selection_schema()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot, or arguments that do not fit its schema, is invalid (validation of the model's
    own answer). What ``msg_to_child`` builds is not checked here: a wrong commission fails where the child is built."""
    schema = selection_schema()
    try:
        decoded = decode_response(response, schema)
        validate_schema(decoded, schema)
        selection = decoded['selection']
        if selection['kind'] == 'child':
            return ChildCall(selection['slot'], selection['arguments'])
        name, arguments = selection['tool'], selection['arguments']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})


def offered_actions(summary, ctx):
    """The action types offered at this decision: the record reading and the strategy slot."""
    return [TOOL_NAME, *valid_slots()]
