"""The task: decide which published evidence bears on the assigned scientific question, by commissioning the search
strategy investigation (child ``literature_strategy``) and reading the records it holds.

This level cannot search, fetch or read a paper (nano-graphrag: the levels above the search level only hand a task
down; a paper is obtained by the search level, when it builds the page). The model is offered the reading of the
records this episode holds (``state_query``) and the one child. It commits no reasoning and grades nothing: the
sheets are graded automatically below, where a leaf extracts what it finds, and what returns here is the credit and
the controlled features of those sheets, with the sources the chain verified as leads.

Carried from the old task.py, task_decision.py, task_instructions.py and to_child_*.py of role ``literature`` at
97308b94c. One unit is one model-selected tool call or one commissioned child. The task always offers a unit and never
ends the Episode: only the yield controller does. The old ``wait`` and ``redeliver_report`` actions are not carried (a
child completes inside the unit that commissioned it).

Not carried, and the reason: the acquisition and access tools (a search, a fetch or a read of a paper belongs to the
levels below), the reasoning commit and the population route with the automatic score judgment (assessment is not a
reasoning commit and the sheets are saved by the leaves), the intervention analysis contract and the launch and
results children (not a part of nano-graphrag's literature shape), and every task kind but
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
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The old ``_CHILDREN['literature']``, under its old name.
CHILD_SLOTS = {
    'literature_strategy': 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement',
}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}

# The one tool: the reading of the records this episode holds (the old access tool ``state.query``).
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

# What the model chooses for the child: the records that give the question its context and the one task (the old
# ``strategy_assignment`` without its version, which ``msg_to_child`` supplies; the task without ``credit_unit``,
# which ``msg_to_child`` supplies from this episode's own commission).
UNIQUE_REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
TASK_VERSION = 'literature_local_task'
STRATEGY_TASK = obj({'version': {'const': TASK_VERSION}, 'evidence_axis': {'const': 'A106'},
                     'kind': {'const': 'verified_source_leads'}})
COMMISSION = {
    'literature_strategy': 'Commission the search strategy investigation: it writes the literature searches the '
                           'question needs, hands each to the search level, and returns its credit, the controlled '
                           'features of the A106 sheets graded below it and the sources it verified as leads. You '
                           'name the records that give the question context (question_context_refs) and the one task '
                           '(literature_task, verified_source_leads); you hand it no paper and no search.'}

HISTORY_GUIDANCE = ('Your own earlier reads are shown to you as own_literature_outcomes; that page creates no new '
                    'action and does not execute or credit the historical work again.')
COMMISSION_GUIDANCE = ('\nCommission the search strategy investigation (literature_strategy) to find the evidence: '
                       'it returns its credit, the controlled features of the A106 sheets saved below it and the '
                       'sources it verified as leads. You cannot search, fetch or read a paper, and you assess no '
                       'evidence: grading is automatic, below. state_query reads the records you hold. The '
                       'numerical controller alone decides whether the investigation continues.')


def instructions():
    """The investigation text this episode shows: its goal, the history paragraph and the commission guidance. The
    library's reasoning-commit, acquisition and read texts are not carried: this episode has no such action."""
    return GOAL + '\n' + HISTORY_GUIDANCE + COMMISSION_GUIDANCE


def offered():
    """The tools offered now: the reading of held records."""
    return ['state_query']


def offered_slots():
    """The children offered now: the strategy investigation, at every decision."""
    return list(CHILD_SLOTS)


def catalog():
    """The tools the model is shown: name, description and input schema."""
    return [{'name': 'state_query', 'description': STATE_QUERY_DESCRIPTION,
             'input_schema': source_location_inputs(STATE_QUERY_SCHEMA)}]


def commission_arguments():
    """The arguments of a commission: the records that give the question its context and the one task (no text
    passes to the child: its objective is fixed by its slot in ``msg_to_child``)."""
    return obj({'question_context_refs': UNIQUE_REFERENCES, 'literature_task': STRATEGY_TASK})


def commissions():
    """The children the model may commission, shown with the tools (the old ``child_option_information``)."""
    return [{'slot': slot, 'description': COMMISSION[slot], 'input_schema': commission_arguments()}
            for slot in offered_slots()]


def selection_schema():
    """What the model answers with: one tool and its arguments, or the one commissioned child (the old action
    schema)."""
    return obj({'selection': {'anyOf': [
        *(obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
          for entry in catalog()),
        *(obj({'kind': {'const': 'child'}, 'slot': {'const': entry['slot']}, 'arguments': entry['input_schema']})
          for entry in commissions())]}})


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


TOOLS = {'state_query': state_query}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the assignment, its own reads, the controlled features of the A106
    sheets saved below, the reports of its strategy investigations, the tools and the child it may commission, the
    measured time and the yield table (the old decision state and inputs, over this episode's summary)."""
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'credit_binding': summary['credit_binding'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'a106_findings': summary['a106_findings'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'child_reports': summary['child_reports'],
               'tools': catalog(), 'child_options': commissions(),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {'feedback': feedback, 'action_yields': summary['action_yields']},
                             conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(), context, generation_schema(selection_schema()))


def offered_actions(summary, ctx):
    """The action types offered at this decision: the names of the tools ``decide`` shows and the child slot."""
    return [*(entry['name'] for entry in catalog()), *offered_slots()]


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit). An answer that selects
    no offered tool or child, arguments that do not fit its schema, or a commission naming a context record this
    episode does not hold is invalid."""
    schema = selection_schema()
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        if selection['kind'] == 'child':
            for reference in selection['arguments']['question_context_refs']:
                if not records.holds(reference):
                    raise ContractError('literature_reference_unavailable', detail={'reference': reference})
            return ChildCall(selection['slot'], selection['arguments'])
        name, arguments = selection['tool'], selection['arguments']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})
