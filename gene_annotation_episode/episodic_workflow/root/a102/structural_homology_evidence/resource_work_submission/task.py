"""The task: choose which actual execution approach is productive for the assigned job, one unit at a time.

Carried from the old ``task.py``, ``task_decision.py``, ``instructions.py``, ``decision_inputs.py``,
``decision_context.py``, ``action_contract_feedback.py``, ``operations.py`` (``execute``), ``operation_catalog.py``
(``catalog``), ``resource_inspection.py`` (``inspect_resource``), ``handoff_check.py`` (``check_selected_handoff``),
``resource_selection.py`` (``capabilities``, ``_adapter``, ``_permitted``), ``child_commissioning.py``
(``child_roles``, ``allowed_children``), ``resource_contracts.py`` (``_failure``, ``_outcome``,
``_availability_failure``), ``episode.py`` (``permitted_common_actions``), ``goal.py`` (``instructions``) and
``waiting.py`` (the wait).

Every decision is a model request. The model selects one unit each turn: ``resource.capabilities``,
``resource.inspect`` or ``resource.check_handoff`` (the three tools of the old catalogue), a typed reasoning
commitment (``reason``), a wait on native events (``wait``), a lookup into the tool-knowledge or
launch-instruction library, or the commission of a resource child (``child``, one of the three slots offered by
``allowed_children``: a slot is offered only when some capability of its kind is bound to an adapter, has tool
names, is not unavailable and is permitted by the assignment's constraints). A commissioned child completes
inside its unit; the old ``wait`` on a ``pending_child_`` handle and ``redeliver_report`` are not carried. The task
always offers a unit and never ends the Episode; only the yield controller does. This file is a private copy: it
imports nothing from another episode.

BLOCKED-ON-SERVICES. The old resource adapters (``resource_adapters``, explicit caller bindings keyed by
``resource_id``; the A102 structural adapters were in the deleted shared root) are the service
``resource_adapter``; no library module wraps it. The members this file calls on it (closed JSON in and out):
``declared_capabilities()``, ``bound_resource_ids()``, ``adapter_capabilities()``, ``can_check_handoff(resource_id)``,
``check_handoff(handoff, held, key=)`` (may be a coroutine), ``facts(assignment)`` (the handoffs and facts of
EVERY configured adapter), ``credit_view(assignment, held_refs)`` and ``decision_context(assignment)``. Operations
must be idempotent on the key. The native event ledger is the service ``native_events`` (``NativeEventLedger``;
nothing wraps it as a service yet): ``validate_event_targets``, ``wait_events`` and the read member
``targets(assignment)``."""
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.waiting import selected_wait
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, HANDOFF_SCHEMA, RESOURCE_ROLES, SELECTION_SCHEMA, _string, _validate, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL

CHILD_SLOTS = {'launch_api': 'structural_homology_evidence/resource_work_submission/api_resource_work_execution',
               'launch_local': 'structural_homology_evidence/resource_work_submission/local_resource_work_execution',
               'launch_hpc': 'structural_homology_evidence/resource_work_submission/hpc_resource_work_execution'}
SERVICES = ('resource_adapter', 'native_events')
ADAPTER = 'resource_adapter'
EVENTS = 'native_events'
# What each child declares as selectable beyond the facts every commission selects (see msg_to_child.py).
EXTRA_FACTS = {'launch_api': ('adapter_facts',)}

CATALOG = [
    {'name': 'resource.capabilities',
     'description': 'Read actual capability availability and configured resource information; this does not '
                    'select or submit work.',
     'input_schema': obj({})},
    {'name': 'resource.inspect',
     'description': 'Inspect one declared resource and its actual binding. Unavailable, unknown, '
                    'unauthenticated and unbound resources return distinct structured failures; this does not '
                    'submit work.',
     'input_schema': obj({'resource_id': _string()})},
    {'name': 'resource.check_handoff',
     'description': 'Exercise the configured receiving interfaces of an explicitly supplied returned handoff. No '
                    'submission or resource substitution.',
     'input_schema': obj({'handoff': HANDOFF_SCHEMA})},
]
OPEN_RECORD = {'type': 'object'}
HISTORY = ('Your own earlier selected actions and their exact outcomes are in completed_action_reports; reading '
           'them executes and credits no work again.\n')
CHILDREN = ('\nTo use a resource child, select a child action naming its slot (one of child_options), an '
            'objective, the chosen resource_selection taken from resource_capabilities, and an initial_report. A '
            'commissioned child completes inside that unit; its finding and execution handoffs are in the '
            'outcome. Its execution handoffs are the facts this episode returns.\n')
NATIVE_EVENTS = ('\nThe separate native_event_targets input names native notification targets assigned or actually '
                 'received by this episode. A target is registration metadata, not proof that submission succeeded. '
                 'Its state_changed event means the original service exit receipt was committed; the service may '
                 'still be closing, so this does not establish result readiness or a child episode return. '
                 'after_cursor records an event cursor actually received, initially zero. Select your own wait '
                 'condition and subsequent status/monitor/result work. No event probability, gain or scientific '
                 'credit follows from registration or passing time alone. Waiting reports readiness only and '
                 'earns no credit.')
TOOL_OF = {'resource.capabilities': 'resource_capabilities', 'resource.inspect': 'resource_inspect',
           'resource.check_handoff': 'resource_check_handoff'}

TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'a102_tool_argument_transport_unsupported'}


def generation_schema(schema):
    """The provider's strict structured-output form of this episode's action schema."""
    return strict_output_schema(schema, **TRANSPORT)


def decode_response(response, schema):
    return decode_strict_output(response, schema, **TRANSPORT)


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


def capabilities_of(declared, adapter_capabilities, bound_ids):
    """The old ``capabilities`` (called without a context): every declared capability, accurately, but never the
    tools of an unbound one; each bound adapter's own capability replaces its declaration."""
    values = {}
    for capability in declared:
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] not in bound_ids:
            value['tool_names'] = []
        values[value['resource_id']] = value
    for capability in adapter_capabilities:
        value = _validate(capability, CAPABILITY_SCHEMA)
        values[value['resource_id']] = value
    return list(values.values())


def allowed_children(assignment, capabilities, bound_ids):
    """The old ``allowed_children`` of the ``launch`` role: a slot is offered only when some capability of its kind
    is bound to a configured adapter, has tool names, is not unavailable and is permitted by the assignment."""
    return [slot for slot, kind in RESOURCE_ROLES.items()
            if any(value['kind'] == kind and value['resource_id'] in bound_ids and value['tool_names']
                   and value['availability'] != 'unavailable' and _permitted(assignment, value)
                   for value in capabilities)]


async def _awaited(value):
    return await value if inspect.isawaitable(value) else value


def _read_capabilities(adapter):
    bound = adapter.read('bound_resource_ids')
    return capabilities_of(adapter.read('declared_capabilities'), adapter.read('adapter_capabilities'),
                           set(bound)), bound


def _capabilities(adapter):
    """The capabilities as a tool sees them (the tool is handed the service itself)."""
    bound = adapter.bound_resource_ids()
    return capabilities_of(adapter.declared_capabilities(), adapter.adapter_capabilities(), set(bound)), bound


def _measured(adapter, assignment, ctx):
    """The adapters' credit view after an operation (credit has no services: the number rides in the outcome)."""
    view = adapter.credit_view(assignment, list(ctx.store.refs()))
    if 'credit' not in view:
        raise ValueError('resource_credit_view_requires_credit')
    return view['credit']


def resource_capabilities(arguments, ctx):
    adapter = ctx.services[ADAPTER]
    capabilities, _ = _capabilities(adapter)
    return {**_outcome({'capabilities': capabilities}),
            'adapter_credit': _measured(adapter, arguments['assignment'], ctx)}


def resource_inspect(arguments, ctx):
    """The old ``inspect_resource``: distinct failures for an unbound, unavailable, unauthenticated or unknown
    declared resource; it does not submit."""
    adapter = ctx.services[ADAPTER]
    reference = arguments['resource_id']
    capabilities, bound = _capabilities(adapter)
    capability = next((value for value in capabilities if value['resource_id'] == reference), None)
    if capability is None:
        reply = _outcome(failure=_failure('resource_not_bound', [reference]))
    else:
        code = _availability_failure(capability)
        if code is None and reference not in bound:
            code = 'resource_not_bound'
        reply = _outcome({'capability': capability}, _failure(code, [reference]) if code else None)
    return {**reply, 'adapter_credit': _measured(adapter, arguments['assignment'], ctx)}


async def resource_check_handoff(arguments, ctx):
    """The old ``check_selected_handoff``: exercise the receiving interface of an explicitly supplied handoff
    through the adapter that owns it. No submission and no substitution. The handoff's own check records must be
    held (a model-named record is asked with ``holds`` first); the adapters' facts, the handoff records written
    through custody and the credit view after the check are the outcome."""
    adapter = ctx.services[ADAPTER]
    assignment, handoff = arguments['assignment'], arguments['handoff']
    handle = handoff['execution_handle']
    resource_id = handoff['resource_selection']['resource_id']
    if (any(not ctx.store.holds(ref) for ref in handoff['check_record_refs'])
            or resource_id not in adapter.bound_resource_ids()):
        reply = _outcome(failure=_failure('invalid_resource_handoff', [handle]))
    elif not adapter.can_check_handoff(resource_id):
        reply = _outcome(failure=_failure('receiving_interface_unavailable'))
    else:
        held = {ref: ctx.store.get(ref) for ref in arguments['held_refs']}
        try:
            reply = await _awaited(adapter.check_handoff(handoff, held, key=ctx.operation_key))
        except (ValueError, KeyError, OSError) as error:
            if str(error) == 'resource_information_identity_conflict':
                raise
            reply = _outcome(failure=_failure('invalid_resource_handoff', [handle]))
    facts = adapter.facts(assignment)
    handoff_refs = [ctx.store.artifact(json.dumps(item, sort_keys=True), 'application/json')
                    for item in facts.get('execution_handoffs', [])]
    return {**reply, 'facts': facts, 'handoff_refs': handoff_refs,
            'adapter_credit': _measured(adapter, assignment, ctx)}


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


TOOLS = {'resource_capabilities': resource_capabilities, 'resource_inspect': resource_inspect,
         'resource_check_handoff': resource_check_handoff, 'reason': reason, 'wait': wait,
         'knowledge_lookup': knowledge_lookup, 'launch_instruction_lookup': launch_instruction_lookup}


def _branch(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _child_branch(slot):
    arguments = {'objective': {'type': 'string', 'minLength': 1}, 'resource_selection': SELECTION_SCHEMA,
                 'initial_report': OPEN_RECORD}
    if slot in EXTRA_FACTS:
        arguments['facts'] = {'type': 'array', 'items': {'type': 'string', 'enum': list(EXTRA_FACTS[slot])}}
    return _branch({'kind': {'type': 'string', 'const': 'child'}, 'slot': {'type': 'string', 'const': slot},
                    'arguments': _branch(arguments)})


def _schema(slots):
    branches = [_branch({'kind': {'type': 'string', 'const': 'tool'},
                         'tool': {'type': 'string', 'const': item['name']}, 'arguments': item['input_schema']})
                for item in CATALOG]
    branches.append(_branch({'kind': {'type': 'string', 'const': 'reason'}, 'commit': OPEN_RECORD}))
    branches[-1]['properties']['evidence_processing'] = {'type': 'object', 'properties': {'kind': {'type': 'string'}}}
    branches.append(_branch({'kind': {'type': 'string', 'const': 'wait'}, 'condition': OPEN_RECORD}))
    for name, library in (('knowledge_lookup', knowledge_catalog), ('launch_instruction_lookup', launch_catalog)):
        branches.append(_branch({'kind': {'type': 'string', 'const': 'tool'},
                                 'tool': {'type': 'string', 'const': name},
                                 'arguments': _branch({'operation': {'type': 'string',
                                                                     'enum': [item['name'] for item in library()]},
                                                       'arguments': OPEN_RECORD})}))
    branches.extend(_child_branch(slot) for slot in slots)
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def _instructions():
    text = replace_span(INSTRUCTIONS, 'A commissioned child returns ONLY', 'Do not execute native provider tools.',
                        HISTORY + CHILDREN)
    return (text + '\n' + GOAL + '\n' + REASONING_COMMIT_REQUIREMENT + KNOWLEDGE_INSTRUCTIONS
            + LAUNCH_INSTRUCTIONS + NATIVE_EVENTS)


def _context(summary, feedback, ctx, capabilities, slots):
    """The old decision state and fresh decision inputs that a resource launch episode used."""
    adapter = ctx.services[ADAPTER]
    assignment = summary['assignment']
    context = {'goal': GOAL, 'role': summary['role'], 'scope': summary['scope'], 'assignment': assignment,
               'resource_capabilities': capabilities,
               'resource_tool_estimates': adapter.read('decision_context', assignment).get('resource_tool_estimates', []),
               'child_options': [{'slot': slot, 'kind': RESOURCE_ROLES[slot]} for slot in slots],
               'current_credit': summary['adapter_credit'], 'action_yields': summary['action_yields'],
               'last_local_outcome': summary['last_local_outcome'], 'feedback': summary['feedback'],
               'completed_action_reports': summary['completed_action_reports'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'native_event_targets': ctx.services[EVENTS].read('targets', assignment),
               'tool_knowledge': ToolKnowledge(ctx.settings['tool_knowledge_directory']).context(),
               'launch_instruction_library': LaunchInstructions(ctx.settings['launch_instructions_directory']).context(),
               'rejection_feedback': feedback}
    selected = LaunchInstructions(ctx.settings['launch_instructions_directory']).materialize(
        assignment['launch_instructions'])
    if selected is not None:
        context['selected_launch_instructions'] = selected
    return context


def _offered(summary, ctx):
    capabilities, bound = _read_capabilities(ctx.services[ADAPTER])
    return capabilities, allowed_children(summary['assignment'], capabilities, bound)


def decide(summary, feedback, ctx):
    capabilities, slots = _offered(summary, ctx)
    return ModelRequest('REASONING', _instructions(), _context(summary, feedback, ctx, capabilities, slots),
                        generation_schema(_schema(slots)))


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
    _, slots = _offered(summary, ctx)
    schema = _schema(slots)
    try:
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason':
            unheld = [ref for ref in _named_refs(selection['commit']) if not records.holds(ref)]
            if unheld:
                raise ValueError('record_not_held:' + ','.join(unheld))
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
    if kind == 'child':
        return ChildCall(selection['slot'], selection['arguments'])
    tool, given = selection['tool'], selection['arguments']
    if tool in ('knowledge_lookup', 'launch_instruction_lookup'):
        return ToolCall(tool, given)
    if tool == 'resource.capabilities':
        return ToolCall('resource_capabilities', {'assignment': summary['assignment']})
    if tool == 'resource.inspect':
        return ToolCall('resource_inspect', {'assignment': summary['assignment'], **given})
    return ToolCall(TOOL_OF[tool], {'assignment': summary['assignment'], 'handoff': given['handoff'],
                                    'held_refs': list(summary['input_refs'])})
