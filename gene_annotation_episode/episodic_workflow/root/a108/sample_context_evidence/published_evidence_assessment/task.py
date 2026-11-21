"""The task: read the records this episode holds, or commission the strategy investigation of which searches are
productive by the strategy child. This episode is the top of the literature chain and does what the top of
nano-graphrag's chain does: it proposes the next strategy and hands it down. It offers its model NO tool that searches
a provider, fetches a paper or reads a paper's text, and NO reasoning commit: the search level obtains a paper when its
page is built, and what is found there is graded there automatically (code attached to the leaf's unit). There is no
report tool: the return is the controlled features code reads from the saved sheets of its descendants.

Carried from the old task.py, task_decision.py, task_instructions.py and source_contracts.py of ``literature`` at
97308b94c (the old child role ``literature_strategy`` is the slot below). One unit is one model-selected read of held
records or one child commission. The task always offers a unit and never ends the Episode: only the yield controller
does. The old permitted actions ``wait`` and ``redeliver_report`` do not exist. Removed with the owner's order of
2026-11-21: the acquisition tools, the access tools that read a source, the two population operations, the reasoning
commit and the source leads, and the three task kinds other than the verified source leads.

The one tool is ``state.query`` (a page of typed records, or records by exact reference), through the same access path
and the same record authorization as before: a record of another episode's private sheet is refused.

Settings read (``ctx.settings``): ``tool_registry`` (the JSON keyword arguments of the library ``ToolRegistry``; its
``PublicClients`` are the declared service ``public_clients``)."""
from dataclasses import dataclass

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    LiteratureA108GradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage import (
    LiteratureA108AggregationRepository)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The one child (the old ``_CHILDREN['literature']``: literature_strategy), by slot.
CHILD_SLOTS = {
    'evidence_search_strategy_improvement': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement',
}
SERVICES = ('public_clients',)

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

STATE_QUERY = 'state_query'
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

# What the one child takes as the model's selection: the objective only. The question context, the task and the
# proposed annotation are this episode's own assignment, passed on by ``msg_to_child``.
CHILD_ARGUMENTS = obj({'objective': TEXT})
CHILD_DESCRIPTIONS = {
    'evidence_search_strategy_improvement': 'Commission the search strategy investigation for the assigned question: '
                                            'it writes the searches, hands each to the search level, which runs it '
                                            'and picks a paper whose page examines it; what is found is graded '
                                            'there. You search, fetch and read nothing yourself. The objective says '
                                            'what the strategy should look for next.',
}

HISTORY_GUIDANCE = ('\nYour own earlier reads are shown to you as own_literature_outcomes; that page creates no new '
                    'action and does not execute or credit the historical work again.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets your '
                   'descendants saved, with their references; nothing you write in prose is returned. Selecting a '
                   'tool never ends your work: only the numerical controller does.')


@dataclass(frozen=True)
class LiteratureContext:
    """The old episode context the A108 sheet repositories read: one literature episode's identity, commission and the
    records it holds (private copy; library candidate)."""
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: dict
    assignment: dict
    request: dict
    received_record_refs: tuple


def instructions():
    """The goal text, the history guidance and the return guidance. The decision-exchange, pending-delivery, wait and
    native-event paragraphs are not carried: no such action exists."""
    return GOAL + HISTORY_GUIDANCE + RETURN_GUIDANCE


def catalog():
    """The tools and the child the model is shown: name, description and input schema (the state query is projected
    through source_location_inputs)."""
    return [{'name': STATE_QUERY, 'description': STATE_QUERY_DESCRIPTION,
             'input_schema': source_location_inputs(STATE_QUERY_SCHEMA)},
            *({'name': name, 'description': CHILD_DESCRIPTIONS[name], 'input_schema': CHILD_ARGUMENTS}
              for name in CHILD_SLOTS)]


def selection_schema():
    """What the model answers with: one tool or child and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'child' if entry['name'] in CHILD_SLOTS else 'tool'},
             'tool': {'const': entry['name']}, 'arguments': entry['input_schema']}) for entry in catalog()]}})


def literature_context(ctx, envelope):
    """The context the library repositories read (the old binding context): the episode's identity, its commission and
    the records it holds now."""
    return LiteratureContext(
        run_id=ctx.run_id, episode_id=ctx.episode_id, role='literature',
        path=tuple(ctx.binding_path.split('/')), scope=envelope['scope'], assignment=envelope['assignment'],
        request={'goal': GOAL, 'scope': envelope['scope']}, received_record_refs=tuple(ctx.store.refs()))


def repositories(store):
    """The old ``_a108_grading_repository`` and ``_a108_aggregation_repository``: the aggregation reads the grading
    cells of a sheet through the grading repository."""
    grading = LiteratureA108GradingRepository(store)
    aggregation = LiteratureA108AggregationRepository(
        store,
        read_cells=lambda context, sheet_ref, components: grading.fact_cells(context, [sheet_ref],
                                                                              components=components))
    return grading, aggregation


def invalid_outcome(ctx, name, arguments, error):
    """The old invalid outcome of ``execute``: a contract error is returned as ``arguments_or_reference`` feedback."""
    detail = getattr(error, 'detail', None)
    field = getattr(error, 'field', None)
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': getattr(error, 'code', str(error)),
                         **({'field': field} if field is not None else {}),
                         **({'detail': detail} if detail else {})}}


async def state_query(arguments, ctx):
    """Execute the state query: a state query by reference may not reach another episode's private sheet
    (``a108_selected_components_required_for_nonowner``); a contract error is returned as an ``invalid`` outcome, as the
    old ``execute`` did, and the outcome is the unit's outcome like any other."""
    query, scope = arguments['arguments'], arguments['scope']
    context = literature_context(ctx, arguments)
    try:
        validate_schema(query, source_location_inputs(STATE_QUERY_SCHEMA))
        if 'refs' in query:
            for repository in repositories(ctx.store):
                for ref in query['refs']:
                    repository.authorize_record_access(context, ctx.store.get(ref))
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, 'state.query', query, error)
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    try:
        outcome = await registry.execute_async('state.query', query, scope=scope, operation_key=ctx.operation_key,
                                               permitted_record_refs=None)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')
    if outcome.get('status') in {'completed', 'partial'}:
        try:
            for record in outcome.get('result', {}).get('records', ()):
                for repository in repositories(ctx.store):
                    repository.authorize_record_access(context, record)
        except ContractError as error:
            return {'status': 'invalid',
                    'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': 'state.query',
                                                            'arguments': query}),
                    'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
    return outcome


TOOLS = {STATE_QUERY: state_query}


def offered_actions(summary, ctx):
    """The action types offered at every decision: the read of held records and the strategy child."""
    return [entry['name'] for entry in catalog()]


def decide(summary, feedback, ctx):
    """Ask the model for the next read or child commission, shown the assignment, its own reads, the credit definition,
    what the child returned (its credit and the features of its findings), the tools, the measured time and the yield
    table (the old decision state and inputs, over this episode's summary)."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'child_returns': summary['child_reports'],
               'tools': catalog(), 'feedback': feedback, 'action_yields': summary['action_yields'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions(), context, generation_schema(selection_schema()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot or arguments that do not fit its schema is invalid (validation of the model's own
    answer). What ``msg_to_child`` builds is not checked here: a wrong commission fails where the child is built."""
    schema = selection_schema()
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
        name, arguments = selection['tool'], selection['arguments']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selection['kind'] == 'child':
        return ChildCall(name, arguments)
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'assignment': summary['literature_assignment']})
