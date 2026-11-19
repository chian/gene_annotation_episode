"""The task: investigate the selected local resource through its own tools, one unit per decision.

The model selects one of: a tool of the selected resource (its catalog is the adapter's own tools plus
``resource.capabilities``), a typed reasoning commit, a wait on native job events, or the recording of its
interpretation of the report. Each is one tool unit of this file; the task always offers a unit and never ends the
Episode (only the yield controller does).

The resource adapters were explicit caller bindings of the old episode. They are now the service ``resources``
(declared in ``SERVICES``; the run supplies it). What this task asks of it:

* read in ``decide`` and ``action`` (recorded by the system): ``declared_capabilities()``,
  ``adapter_capabilities()`` (``{resource_id: capability}`` of the bound adapters), ``catalog(assignment)`` (the
  selected adapter's tools), ``decision_context(assignment)`` (``{'resource_tool_estimates': [...]}``) and
  ``is_bound(resource_id)``;
* used by the tools: ``execute(assignment, tool_name, arguments, operation_key)`` (may be a coroutine),
  ``credit_view(assignment)`` (a record with ``credit``), ``facts(assignment)`` (the adapter's facts),
  ``validate_report(assignment, interpretation)`` (raises ``ValueError`` for an invalid report) and, when the
  adapter has one, ``check_handoff(handoff, operation_key)``.

``native_events`` is the run's ``NativeEventLedger`` for the wait tool and ``instruction_libraries`` serves the
run-frozen listings (``tool_knowledge()``, ``launch_instruction_library()`` and
``selected_launch_instructions(selection)``; ``None`` where the run has none)."""
from __future__ import annotations

import inspect

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, RESOURCE_ROLES, _validate, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('resources', 'native_events', 'instruction_libraries')

HISTORY_SPAN = ('On a fresh provider conversation,', 'Do not execute native provider tools.')
OWN_OUTCOMES_TEXT = ('Your own earlier units are listed in own_outcomes and the last one in full in last_outcome. '
                     'A failed outcome stays failed. Your current interpretation for the parent is '
                     'current_report_update; record a new one by selecting the report action.\n')
NATIVE_EVENT_TEXT = ('\nThe wait action waits on native notification targets assigned or actually received by this '
                     'episode. A target is registration metadata, not proof that submission succeeded. Its '
                     'state_changed event means the original service exit receipt was committed; the service may '
                     'still be closing, so this does not establish result readiness. after_cursor records an event '
                     'cursor actually received, initially zero. Select your own wait condition and subsequent '
                     'status/monitor/result work. Waiting only reports readiness and earns no credit; no event '
                     'probability, gain or credit follows from registration or passing time alone.')
REPORT_TEXT = ('\nThe report action records your interpretation for the parent as a closed record; it does not end '
               'your work and earns nothing. The parent receives the recorded execution handoffs as the host '
               'recorded them, never as you wrote them.')
CONDITION_SCHEMA = obj({
    'version': {'type': 'string', 'const': 'event_condition_v1'},
    'events': {'type': 'array', 'items': obj({'handle': {'type': 'string', 'minLength': 1},
                                              'event': {'type': 'string', 'minLength': 1},
                                              'after_cursor': {'type': 'integer', 'minimum': 0}})},
    'reconsider_at': {'type': ['string', 'null']}})
OWN_CAPABILITIES = {'name': 'resource.capabilities',
                    'description': 'Read actual capability availability and configured resource information; '
                                   'this does not select or submit work.',
                    'input_schema': obj({})}


# -- failures and outcomes (old execution_contracts.py) ---------------------------------------------

def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references), 'diagnostic_ref': None, 'partial_record_refs': []}


def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs),
            'changed_record_refs': [], 'result': value, 'feedback': failure}


def _availability_failure(capability):
    return {'unavailable': 'resource_unavailable', 'authentication_required': 'resource_authentication_required',
            'unknown': 'resource_availability_unknown'}.get(capability['availability'])


# -- capabilities and catalog (old execution_operations.py) -----------------------------------------

def capabilities(declared, adapter_capabilities, selected, catalog):
    """Include unbound declarations accurately, but never offer their tools (old ``capabilities``)."""
    values = {}
    for capability in declared:
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] not in adapter_capabilities:
            value['tool_names'] = []
        values[value['resource_id']] = value
    for resource_id, capability in adapter_capabilities.items():
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] != resource_id:
            raise ValueError('resource_capability_identity_mismatch')
        if selected == resource_id and not set(value['tool_names']) <= {tool['name'] for tool in catalog}:
            raise ValueError('resource_capability_tool_not_bound')
        values[value['resource_id']] = value
    return list(values.values())


def _tools(resources, assignment):
    """The old ``catalog``: ``resource.capabilities`` and every tool of the selected adapter."""
    return [OWN_CAPABILITIES, *resources.read('catalog', assignment)]


# -- instructions (old task_instructions.py) ---------------------------------------------------------

def instructions(*, has_knowledge, has_launch):
    text = INSTRUCTIONS
    text = replace_span(text, HISTORY_SPAN[0], HISTORY_SPAN[1], OWN_OUTCOMES_TEXT)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    if has_knowledge:
        text += KNOWLEDGE_INSTRUCTIONS
    if has_launch:
        text += LAUNCH_INSTRUCTIONS
    return text + NATIVE_EVENT_TEXT + REPORT_TEXT


def _selection_schema(catalog, reasoning_schema):
    options = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                'properties': {'kind': {'const': 'tool'}, 'tool': {'const': tool['name']},
                               'arguments': tool['input_schema']}} for tool in catalog]
    options.append(obj({'kind': {'const': 'reason'}, 'commit': reasoning_schema}))
    options.append(obj({'kind': {'const': 'wait'}, 'condition': CONDITION_SCHEMA}))
    options.append(obj({'kind': {'const': 'report'},
                        'interpretation': {'type': 'object'}}))
    return obj({'selection': {'anyOf': options}})


# -- the decision ------------------------------------------------------------------------------------

def decide(summary, feedback, ctx):
    resources = ctx.services['resources']
    assignment = summary['assignment']
    selected = assignment['resource_selection']
    catalog = _tools(resources, assignment)
    declared = capabilities(resources.read('declared_capabilities'), resources.read('adapter_capabilities'),
                            selected['resource_id'], catalog[1:])
    capability = next((value for value in declared if value['resource_id'] == selected['resource_id']), None)
    if capability is None or capability['kind'] != RESOURCE_ROLES['launch_local']:
        raise ValueError('resource_selection_conflict')
    libraries = ctx.services['instruction_libraries']
    knowledge = libraries.read('tool_knowledge')
    launch_library = libraries.read('launch_instruction_library')
    context = {'assignment': assignment, 'scope': summary['scope'], 'resource_capabilities': declared,
               'resource_tool_estimates': resources.read('decision_context', assignment)['resource_tool_estimates'],
               'tools': catalog, 'current_credit': None if summary['credit_view'] is None
               else summary['credit_view']['credit'],
               'own_outcomes': summary['outcome_log'], 'last_outcome': summary['last_outcome'],
               'current_report_update': summary['interpretation'], 'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'feedback': feedback if feedback is not None else summary['feedback']}
    context = extend_context(context, {
        'tool_knowledge': knowledge, 'launch_instruction_library': launch_library,
        'selected_launch_instructions': libraries.read('selected_launch_instructions',
                                                       assignment['launch_instructions'])
        if 'launch_instructions' in assignment else None},
        conflict='initial_binding_context_field_conflict')
    schema = _selection_schema(catalog, summary['reasoning_schema'])
    return ModelRequest('REASONING', instructions(has_knowledge=knowledge is not None,
                                                   has_launch=launch_library is not None),
                        context, generation_schema(schema))


def _empty_commit(commit, reasoning_schema):
    """The old test for a reason action with every commit section empty."""
    required = set(reasoning_schema.get('required', reasoning_schema['properties']))
    return (required <= set(commit) <= set(reasoning_schema['properties'])
            and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    assignment = summary['assignment']
    catalog = _tools(ctx.services['resources'], assignment)
    schema = _selection_schema(catalog, summary['reasoning_schema'])
    try:
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and _empty_commit(selection['commit'], summary['reasoning_schema']):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    if selection['kind'] == 'tool':
        return ToolCall('resource_tool', {'tool': selection['tool'], 'arguments': selection['arguments'],
                                          'assignment': assignment})
    if selection['kind'] == 'reason':
        return ToolCall('reason', {'commit': selection['commit'], 'scope': summary['scope'],
                                   'assignment': assignment})
    if selection['kind'] == 'wait':
        return ToolCall('wait', {'condition': selection['condition']})
    return ToolCall('report', {'interpretation': selection['interpretation'], 'assignment': assignment})


# -- the tools ---------------------------------------------------------------------------------------

def _observed(outcome, resources, assignment):
    """An executed unit enters the iterator with the credit view and the facts the resource holds after it."""
    return {**outcome, 'credit_view': resources.credit_view(assignment), 'facts': resources.facts(assignment)}


async def resource_tool(arguments, ctx):
    """One tool of the selected resource (old ``execute``): ``resource.capabilities`` is answered here, every
    other tool by the selected adapter through the resource service."""
    resources, assignment, name = ctx.services['resources'], arguments['assignment'], arguments['tool']
    if name == 'resource.capabilities':
        outcome = _outcome({'capabilities': capabilities(
            resources.declared_capabilities(), resources.adapter_capabilities(),
            assignment['resource_selection']['resource_id'], resources.catalog(assignment))})
    elif name == 'resource.inspect':
        reference = arguments['arguments']['resource_id']
        capability = next((value for value in resources.declared_capabilities()
                           if value['resource_id'] == reference), None)
        if capability is None:
            outcome = _outcome(failure=_failure('resource_not_bound', [reference]))
        else:
            code = _availability_failure(capability)
            if code is None and not resources.is_bound(reference):
                code = 'resource_not_bound'
            outcome = _outcome({'capability': capability}, _failure(code, [reference]) if code else None)
    elif name == 'resource.check_handoff':
        handoff = arguments['arguments']['handoff']
        callback = getattr(resources, 'check_handoff', None)
        if callback is None:
            outcome = _outcome(failure=_failure('receiving_interface_unavailable'))
        else:
            try:
                value = callback(handoff, ctx.operation_key)
                outcome = await value if inspect.isawaitable(value) else value
            except (ValueError, KeyError, OSError) as error:
                if str(error) == 'resource_information_identity_conflict':
                    raise
                outcome = _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
    else:
        outcome = resources.execute(assignment, name, arguments['arguments'], ctx.operation_key)
        if inspect.isawaitable(outcome):
            outcome = await outcome
    return _observed(outcome, resources, assignment)


def reason(arguments, ctx):
    """A typed reasoning commit under the scope of the parent's subjects (old ``execute`` branch ``reason``)."""
    resources = ctx.services['resources']
    try:
        result = ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)
    except CustodyError as error:
        return _observed({'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                          'feedback': {'status': 'failed', 'category': 'custody', 'detail': str(error)}},
                         resources, arguments['assignment'])
    return _observed(result, resources, arguments['assignment'])


async def wait(arguments, ctx):
    """A selected wait on native job events (old ``waiting.py``). It earns nothing: no credit view is returned,
    so the summary keeps the credit it had."""
    return await selected_wait(ctx.services['native_events'], arguments['condition'])


def report(arguments, ctx):
    """Record the interpretation for the parent; the selected adapter checks it first (old ``validate_report``
    on the adapters). An invalid one is a failed unit with ``report_format`` feedback; it earns nothing."""
    try:
        ctx.services['resources'].validate_report(arguments['assignment'], arguments['interpretation'])
    except (ValueError, KeyError, TypeError) as error:
        return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'interpretation': None,
                'feedback': {'status': 'invalid', 'category': 'report_format',
                             'detail': getattr(error, 'diagnostic', {'code': 'invalid_report_update'})}}
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'interpretation': arguments['interpretation'], 'feedback': None}


TOOLS = {'resource_tool': resource_tool, 'reason': reason, 'wait': wait, 'report': report}
