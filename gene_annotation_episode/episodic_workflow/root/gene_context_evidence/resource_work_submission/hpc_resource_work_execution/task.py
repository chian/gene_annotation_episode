"""The task: investigate execution through the one selected HPC resource, one unit at a time.

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``decision_inputs.py``,
``decision_state.py``, ``execution_operations.py`` (``capabilities``, ``catalog``, ``execute``),
``execution_contracts.py`` (``_failure``, ``_outcome``, ``_availability_failure``), ``from_parent.py``
(``_permitted`` and the capability test of ``prepare_assignment``), ``goal.py`` (``instructions``) and
``waiting.py`` (the wait).

The first unit is ``prepare_resource_assignment`` (old ``prepare_assignment``: the selected resource must be a
declared ``hpc`` capability that the constraints permit and be bound; its adapter then prepares the final
assignment). After it the model selects one unit each turn: ``resource.capabilities`` or one tool of the selected
adapter's catalog (``resource_operation``), a typed reasoning commitment (``reason``), a wait on native events
(``wait``) or a lookup into the tool-knowledge or launch-instruction library. The task always offers a unit and
never ends the Episode; only the yield controller does. The episode has no child (the old ``child`` and
``redeliver_report`` kinds could never be carried out here). This file is a private copy: it imports nothing from
another episode.

BLOCKED-ON-SERVICES. The old resource adapter (``resource_adapters``, explicit caller bindings keyed by
``resource_id``; the A103 adapter was in the deleted shared root) is the service ``resource_adapter``;
no library module wraps it. The members this file calls on it (closed JSON in and out): ``declared_capabilities()``,
``bound_resource_ids()``, ``adapter_capabilities()``, ``catalog(assignment)``, ``prepare_assignment(assignment,
scope, key=)``, ``execute(assignment, tool, arguments, held, key=)`` (may be a coroutine), ``check_handoff(handoff,
held, key=)``, ``facts(assignment)``, ``credit_view(assignment, held_refs)`` and ``decision_context(assignment)``.
Operations must be idempotent on the key. The native event ledger is the service ``native_events``
(``NativeEventLedger``; nothing wraps it as a service yet): ``validate_event_targets``, ``wait_events`` and the
read member ``targets(assignment)``."""
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.gene_context_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, RESOURCE_ROLES, _validate, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('resource_adapter', 'native_events')
ADAPTER = 'resource_adapter'
EVENTS = 'native_events'

CAPABILITIES_ENTRY = {'name': 'resource.capabilities',
                      'description': 'Read actual capability availability and configured resource information; '
                                     'this does not select or submit work.',
                      'input_schema': obj({})}
OPEN_RECORD = {'type': 'object'}
HISTORY = ('Your own earlier selected actions and their exact outcomes are in completed_action_reports; reading '
           'them executes and credits no work again.\n')
NATIVE_EVENTS = ('\nThe separate native_event_targets input names native notification targets assigned or actually '
                 'received by this episode. A target is registration metadata, not proof that submission succeeded. '
                 'Its state_changed event means the original service exit receipt was committed; the service may '
                 'still be closing, so this does not establish result readiness or a child episode return. '
                 'after_cursor records an event cursor actually received, initially zero. Select your own wait '
                 'condition and subsequent status/monitor/result work. No event probability, gain or scientific '
                 'credit follows from registration or passing time alone. Waiting reports readiness only and '
                 'earns no credit.')


def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references), 'diagnostic_ref': None, 'partial_record_refs': []}


def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs),
            'changed_record_refs': [], 'result': value, 'feedback': failure}


def _availability_failure(capability):
    return {'unavailable': 'resource_unavailable', 'authentication_required': 'resource_authentication_required',
            'unknown': 'resource_availability_unknown'}.get(capability['availability'])


def _permitted(assignment, capability):
    constraints = assignment.get('constraints', {})
    selection = assignment.get('resource_selection')
    return ((selection is None or (capability['resource_id'] == selection['resource_id']
                                   and capability['kind'] == selection['kind']))
            and ('allowed_resource_ids' not in constraints or capability['resource_id'] in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or capability['kind'] in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or capability['resource_id'] == constraints['resource_id'])
            and ('kind' not in constraints or capability['kind'] == constraints['kind']))


def capabilities_of(declared, adapter_capabilities, bound_ids, selected_id, bound_tool_names):
    """The old ``capabilities``: every declared capability, accurately, but never the tools of an unbound one;
    the selected adapter's tool names must all be in its catalog."""
    values = {}
    for capability in declared:
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] not in bound_ids:
            value['tool_names'] = []
        values[value['resource_id']] = value
    for capability in adapter_capabilities:
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] == selected_id and not set(value['tool_names']) <= set(bound_tool_names):
            raise ValueError('resource_capability_tool_not_bound')
        values[value['resource_id']] = value
    return list(values.values())


def _capabilities(adapter, assignment):
    names = {tool['name'] for tool in adapter.catalog(assignment)}
    return capabilities_of(adapter.declared_capabilities(), adapter.adapter_capabilities(),
                           set(adapter.bound_resource_ids()), assignment['resource_selection']['resource_id'], names)


async def _awaited(value):
    return await value if inspect.isawaitable(value) else value


def prepare_resource_assignment(arguments, ctx):
    """The old ``prepare_assignment``: the selected resource is a declared ``hpc`` capability the constraints
    permit and is bound; its adapter prepares the final assignment (adds ``adapter_assignment``)."""
    adapter = ctx.services[ADAPTER]
    selected = arguments['assignment']
    capability = next((value for value in adapter.declared_capabilities()
                       if value['resource_id'] == selected['resource_selection']['resource_id']), None)
    if capability is None or capability['kind'] != RESOURCE_ROLES['launch_hpc'] or not _permitted(selected, capability):
        raise ValueError('resource_selection_conflict')
    if selected['resource_selection']['resource_id'] not in adapter.bound_resource_ids():
        raise ValueError('resource_not_bound')
    prepared = adapter.prepare_assignment(selected, arguments['scope'], key=ctx.operation_key)
    return {**_outcome({'resource_id': capability['resource_id']}), 'assignment': prepared,
            'capabilities': _capabilities(adapter, prepared)}


def resource_capabilities(arguments, ctx):
    return _outcome({'capabilities': _capabilities(ctx.services[ADAPTER], arguments['assignment'])})


async def resource_operation(arguments, ctx):
    """One tool of the selected adapter's catalog (old ``execute``). The reply, the adapter's recorded facts and
    its credit view after the operation are the outcome; the handoff records are written through custody."""
    adapter = ctx.services[ADAPTER]
    assignment, name, given = arguments['assignment'], arguments['tool'], arguments['arguments']
    held = {ref: ctx.store.get(ref) for ref in arguments['held_refs']}
    if name == 'resource.inspect':
        reference = given['resource_id']
        capability = next((value for value in _capabilities(adapter, assignment)
                           if value['resource_id'] == reference), None)
        if capability is None:
            reply = _outcome(failure=_failure('resource_not_bound', [reference]))
        else:
            code = _availability_failure(capability)
            if code is None and reference not in adapter.bound_resource_ids():
                code = 'resource_not_bound'
            reply = _outcome({'capability': capability}, _failure(code, [reference]) if code else None)
    elif name == 'resource.check_handoff':
        handoff = given['handoff']
        try:
            reply = await _awaited(adapter.check_handoff(handoff, held, key=ctx.operation_key))
        except (ValueError, KeyError, OSError) as error:
            if str(error) == 'resource_information_identity_conflict':
                raise
            reply = _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
    else:
        reply = await _awaited(adapter.execute(assignment, name, given, held, key=ctx.operation_key))
    facts = adapter.facts(assignment)
    view = adapter.credit_view(assignment, list(ctx.store.refs()))
    if 'credit' not in view:
        raise ValueError('resource_credit_view_requires_credit')
    handoff_refs = [ctx.store.artifact(json.dumps(handoff, sort_keys=True), 'application/json')
                    for handoff in facts.get('execution_handoffs', [])]
    return {**reply, 'facts': facts, 'handoff_refs': handoff_refs, 'adapter_credit': view['credit']}


def reason(arguments, ctx):
    """A typed reasoning commitment (old ``reason`` kind): committed through custody under this unit's key."""
    return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)


async def wait(arguments, ctx):
    """Wait for selected native job events (old ``waiting.py``). It earns no credit by itself."""
    return await selected_wait(ctx.services[EVENTS], arguments['condition'])


def knowledge_lookup(arguments, ctx):
    return _outcome(ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                                   arguments['arguments']))


def launch_instruction_lookup(arguments, ctx):
    return _outcome(LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(
        arguments['operation'], arguments['arguments']))


TOOLS = {'prepare_resource_assignment': prepare_resource_assignment, 'resource_capabilities': resource_capabilities,
         'resource_operation': resource_operation, 'reason': reason, 'wait': wait,
         'knowledge_lookup': knowledge_lookup, 'launch_instruction_lookup': launch_instruction_lookup}


def _catalog(summary, ctx):
    """The old ``catalog``: ``resource.capabilities`` and every tool of the selected adapter's catalog."""
    return [CAPABILITIES_ENTRY, *ctx.services[ADAPTER].read('catalog', summary['assignment'])]


def _branch(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _schema(catalog):
    branches = [_branch({'kind': {'type': 'string', 'const': 'tool'},
                         'tool': {'type': 'string', 'const': item['name']}, 'arguments': item['input_schema']})
                for item in catalog]
    branches.append(_branch({'kind': {'type': 'string', 'const': 'reason'}, 'commit': OPEN_RECORD}))
    branches[-1]['properties']['evidence_processing'] = {'type': 'object', 'properties': {'kind': {'type': 'string'}}}
    branches.append(_branch({'kind': {'type': 'string', 'const': 'wait'}, 'condition': OPEN_RECORD}))
    for name, library in (('knowledge_lookup', knowledge_catalog), ('launch_instruction_lookup', launch_catalog)):
        branches.append(_branch({'kind': {'type': 'string', 'const': 'tool'},
                                 'tool': {'type': 'string', 'const': name},
                                 'arguments': _branch({'operation': {'type': 'string',
                                                                     'enum': [item['name'] for item in library()]},
                                                       'arguments': OPEN_RECORD})}))
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def _instructions():
    text = replace_span(INSTRUCTIONS, 'A commissioned child returns ONLY', 'Do not execute native provider tools.',
                        HISTORY)
    return (text + '\n' + GOAL + '\n' + REASONING_COMMIT_REQUIREMENT + KNOWLEDGE_INSTRUCTIONS
            + LAUNCH_INSTRUCTIONS + NATIVE_EVENTS)


def _context(summary, feedback, ctx):
    adapter = ctx.services[ADAPTER]
    assignment = summary['assignment']
    context = {'goal': GOAL, 'role': summary['role'], 'scope': summary['scope'], 'assignment': assignment,
               'resource_capabilities': summary['capabilities'],
               'resource_tool_estimates': adapter.read('decision_context', assignment).get('resource_tool_estimates', []),
               'current_credit': summary['adapter_credit'], 'action_yields': summary['action_yields'],
               'last_local_outcome': summary['last_local_outcome'], 'feedback': summary['feedback'],
               'completed_action_reports': summary['completed_action_reports'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'native_event_targets': ctx.services[EVENTS].read('targets', assignment),
               'tool_knowledge': ToolKnowledge(ctx.settings['tool_knowledge_directory']).context(),
               'launch_instruction_library': LaunchInstructions(ctx.settings['launch_instructions_directory']).context(),
               'rejection_feedback': feedback}
    selected = LaunchInstructions(ctx.settings['launch_instructions_directory']).materialize(
        assignment.get('launch_instructions'))
    if selected is not None:
        context['selected_launch_instructions'] = selected
    return context


def decide(summary, feedback, ctx):
    if not summary['prepared']:
        return ToolCall('prepare_resource_assignment', {'assignment': summary['assignment'],
                                                        'scope': summary['scope']})
    return ModelRequest('REASONING', _instructions(), _context(summary, feedback, ctx),
                        generation_schema(_schema(_catalog(summary, ctx))))


def _named_refs(value):
    """The record references a model-built value names (``ref``, ``..._ref``, ``..._refs``), except the
    ``@alias`` references of a reasoning commit to its own rows."""
    found = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == 'ref' or name.endswith('_ref'):
                if not (isinstance(child, str) and child.startswith('@')):
                    found.append(child)
            elif name.endswith('_refs'):
                found.extend(ref for ref in child if not (isinstance(ref, str) and ref.startswith('@')))
            else:
                found.extend(_named_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_named_refs(child))
    return found


def _empty_commit(selection, commit_schema):
    payload = selection['commit']
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(payload)
            <= set(commit_schema['properties']) and all(value == [] for value in payload.values())
            and selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence')


def action(response, summary, records, ctx):
    schema = _schema(_catalog(summary, ctx))
    try:
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        unheld = [ref for ref in _named_refs(selection) if not records.holds(ref)]
        if unheld:
            raise ValueError('record_not_held:' + ','.join(unheld))
        if selection['kind'] == 'reason':
            commit_schema = records.reasoning_schema()
            Draft202012Validator(commit_schema).validate(selection['commit'])
            if _empty_commit(selection, commit_schema):
                raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    kind = selection['kind']
    if kind == 'reason':
        return ToolCall('reason', {'commit': selection['commit'], 'scope': summary['scope']})
    if kind == 'wait':
        return ToolCall('wait', {'condition': selection['condition']})
    tool, given = selection['tool'], selection['arguments']
    if tool in ('knowledge_lookup', 'launch_instruction_lookup'):
        return ToolCall(tool, given)
    if tool == 'resource.capabilities':
        return ToolCall('resource_capabilities', {'assignment': summary['assignment']})
    held = list(dict.fromkeys([*summary['input_refs'], *_named_refs(given)]))
    return ToolCall('resource_operation', {'assignment': summary['assignment'], 'tool': tool, 'arguments': given,
                                           'held_refs': held})
