"""The task: choose which actual execution approach is productive for the assigned job, read the resources, check
returned handoffs, commit typed reasoning when useful, and commission the API, local or HPC resource child that
carries the job out.

Carried from the old ``task.py`` (``OperationalTask.apply_response``, ``execute``), ``task_decision.py``,
``task_instructions.py`` (``instructions``), ``decision_inputs.py``, ``decision_state.py``, ``execution_operations.py``
(``capabilities``, ``_adapter``, ``catalog``, ``execute``), ``execution_contracts.py`` (``_failure``, ``_outcome``,
``_availability_failure``), ``from_parent.py`` (``_permitted``, ``_require_launch_child_instruction_pins``),
``episode.py`` (``child_roles``, ``allowed_children``, ``permitted_common_actions``) and ``internal_summary.py``
(``decision_context``). One unit is one tool, one typed reasoning commit, one library lookup or one commission of a
resource child. The task always offers a unit (``resource.capabilities`` is always acceptable) and never ends the
Episode: only the yield controller does.

The old ``wait`` action (it waited on a pending in-process child), ``redeliver_report``, the report update, the
decision-exchange loop, ``pending_work`` and the contract-information profile are old-runner machinery and are not
carried. The old ``request_context`` lookups into the tool-knowledge and launch-instruction libraries are tools
here (``knowledge_lookup``, ``launch_instruction_lookup``), offered when the settings name the library directory.

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and the optional
``tool_knowledge_directory`` and ``launch_instructions_directory``. The commissioner's assignment is in the summary
(``messages/read_from_parent.py``).

BLOCKED-ON-JOB-SERVICE: ``resource_adapters`` (the old caller-bound resource adapters, keyed by ``resource_id``, and
the declared capabilities of ``services.capabilities()``; the A101 homology adapter lived in the deleted shared root
and no library module wraps them as a service). The members this file calls on it, closed JSON in and out:
``declared_capabilities()``, ``adapter_capabilities()`` (resource_id -> the adapter's own capability),
``bound_resource_ids()``, ``resource_tool_estimates(assignment)`` (the old ``adapter.decision_context``), and, in tools,
``can_check_handoff(handoff)`` and ``check_handoff(handoff, key=...)`` (may be a coroutine; idempotent on the key).
Each call raises ``NotImplementedError`` where it is reached."""
import inspect

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, SELECTION_SCHEMA as LAUNCH_SELECTION_SCHEMA,
    catalog as launch_catalog, retain_inherited_selection)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, HANDOFF_SCHEMA, RESOURCE_ROLES, SELECTION_SCHEMA, _validate, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import GOAL

PREFIX = 'sequence_homology_evidence/resource_work_submission/'
CHILD_SLOTS = {'launch_api': PREFIX + 'api_resource_work_execution',
               'launch_hpc': PREFIX + 'hpc_resource_work_execution',
               'launch_local': PREFIX + 'local_resource_work_execution'}
SERVICE = 'resource_adapters'
SERVICES = (SERVICE,)

CAPABILITIES_ENTRY = {'name': 'resource.capabilities',
                      'description': 'Read actual capability availability and configured resource information; '
                                     'this does not select or submit work.',
                      'input_schema': obj({})}
INSPECT_ENTRY = {'name': 'resource.inspect',
                 'description': 'Inspect one declared resource and its actual binding. Unavailable, unknown, '
                                'unauthenticated and unbound resources return distinct structured failures; this '
                                'does not submit work.',
                 'input_schema': obj({'resource_id': {'type': 'string', 'minLength': 1}})}
CHECK_ENTRY = {'name': 'resource.check_handoff',
               'description': 'Exercise the configured receiving interfaces of an explicitly supplied returned '
                              'handoff. No submission or resource substitution.',
               'input_schema': obj({'handoff': HANDOFF_SCHEMA})}
TOOL_OF = {'resource.capabilities': 'resource_capabilities', 'resource.inspect': 'resource_inspect',
           'resource.check_handoff': 'resource_check_handoff'}
LOOKUPS = {'knowledge_lookup': ('tool_knowledge_directory', knowledge_catalog),
           'launch_instruction_lookup': ('launch_instructions_directory', launch_catalog)}
CREDIT_BINDING = {'credit': 'the commissioned unit credit for each distinct usable execution handoff held (capability '
                            'binding and execution handle); it counts what the resource children and the handoff '
                            'checks returned'}
HISTORY = ('Your own earlier selected actions and their exact outcomes are in requested_action_history; reading '
           'them executes and credits no work again.\n')


def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references), 'diagnostic_ref': None, 'partial_record_refs': []}


def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs),
            'changed_record_refs': [], 'result': value, 'feedback': failure}


def _availability_failure(capability):
    return {'unavailable': 'resource_unavailable', 'authentication_required': 'resource_authentication_required',
            'unknown': 'resource_availability_unknown'}.get(capability['availability'])


def _permitted(assignment, capability):
    """The old ``_permitted``: the capability is the commissioner's selection, when it made one, and satisfies the
    constraints."""
    constraints = assignment.get('constraints', {})
    selection = assignment.get('resource_selection')
    return ((selection is None or (capability['resource_id'] == selection['resource_id']
                                   and capability['kind'] == selection['kind']))
            and ('allowed_resource_ids' not in constraints or capability['resource_id'] in constraints['allowed_resource_ids'])
            and ('allowed_kinds' not in constraints or capability['kind'] in constraints['allowed_kinds'])
            and ('resource_id' not in constraints or capability['resource_id'] == constraints['resource_id'])
            and ('kind' not in constraints or capability['kind'] == constraints['kind']))


def capabilities_of(declared, adapter_capabilities, bound_ids):
    """The old ``OperationalOperations.capabilities``: every declared capability, accurately, but never the tools of
    an unbound resource; each bound adapter's own capability replaces the declaration and must be that adapter's."""
    values = {}
    for capability in declared:
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] not in bound_ids:
            value['tool_names'] = []
        values[value['resource_id']] = value
    for resource_id, capability in adapter_capabilities.items():
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] != resource_id:
            raise ValueError('resource_capability_identity_mismatch')
        values[value['resource_id']] = value
    return list(values.values())


def allowed_slots(assignment, capabilities, bound_ids):
    """The old ``allowed_children``: a resource child is allowed when some declared capability has its kind, a bound
    adapter, a non-empty tool list, availability other than ``unavailable`` and is permitted by the assignment."""
    return [slot for slot, kind in RESOURCE_ROLES.items()
            if any(value['kind'] == kind and value['resource_id'] in bound_ids and value['tool_names']
                   and value['availability'] != 'unavailable' and _permitted(assignment, value)
                   for value in capabilities)]


def blocked(call):
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: ' + SERVICE + '; wanted call: ' + call)


def read_adapters(ctx, member, *arguments):
    """One recorded read of the resource adapters, in a decision.

    BLOCKED-ON-JOB-SERVICE: resource_adapters; wanted call: ``ctx.services['resource_adapters'].read(member,
    *arguments)``."""
    blocked("ctx.services['resource_adapters'].read(member, *arguments)")
    return ctx.services[SERVICE].read(member, *arguments)


def adapters(ctx):
    """The resource adapter service, handed to a tool.

    BLOCKED-ON-JOB-SERVICE: resource_adapters; wanted call: ``ctx.services['resource_adapters']``."""
    blocked("ctx.services['resource_adapters']")
    return ctx.services[SERVICE]


def resource_capabilities(arguments, ctx):
    """The old ``execute`` for ``resource.capabilities``: the actual capabilities of every declared resource."""
    service = adapters(ctx)
    return _outcome({'capabilities': capabilities_of(service.declared_capabilities(), service.adapter_capabilities(),
                                                     set(service.bound_resource_ids()))})


def resource_inspect(arguments, ctx):
    """The old ``execute`` for ``resource.inspect``: the capability of one declared resource, or a distinct
    structured failure for an unbound, unavailable, unauthenticated or unknown one."""
    service = adapters(ctx)
    bound = set(service.bound_resource_ids())
    reference = arguments['resource_id']
    capability = next((value for value in capabilities_of(service.declared_capabilities(),
                                                          service.adapter_capabilities(), bound)
                       if value['resource_id'] == reference), None)
    if capability is None:
        return _outcome(failure=_failure('resource_not_bound', [reference]))
    code = _availability_failure(capability)
    if code is None and reference not in bound:
        code = 'resource_not_bound'
    return _outcome({'capability': capability}, _failure(code, [reference]) if code else None)


async def resource_check_handoff(arguments, ctx):
    """The old ``execute`` for ``resource.check_handoff``: exercise the receiving interfaces of the adapter that owns
    the supplied handoff. An adapter without the callback gives ``receiving_interface_unavailable``; a handoff that
    is not an accepted one gives ``invalid_resource_handoff``; ``resource_information_identity_conflict`` is raised."""
    service = adapters(ctx)
    handoff = arguments['handoff']
    try:
        if handoff['resource_selection']['resource_id'] not in service.bound_resource_ids():
            raise ValueError('resource_not_bound')
        if not service.can_check_handoff(handoff):
            return _outcome(failure=_failure('receiving_interface_unavailable'))
        value = service.check_handoff(handoff, key=ctx.operation_key)
        return await value if inspect.isawaitable(value) else value
    except (ValueError, KeyError, OSError) as error:
        if str(error) == 'resource_information_identity_conflict':
            raise
        return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))


def reason(arguments, ctx):
    """A typed reasoning commitment (the old ``reason`` kind): committed through custody under this unit's key (the
    old account invocation, ``(run_id, episode_id)``, is the system's now)."""
    return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)


def knowledge_lookup(arguments, ctx):
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                     arguments['arguments'])


TOOLS = {'resource_capabilities': resource_capabilities, 'resource_inspect': resource_inspect,
         'resource_check_handoff': resource_check_handoff, 'reason': reason, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def _branch(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def lookups_offered(settings):
    return [name for name, (setting, _) in LOOKUPS.items() if settings.get(setting) is not None]


def catalog():
    """The old ``catalog``: the three fixed tools (no adapter tools)."""
    return [CAPABILITIES_ENTRY, INSPECT_ENTRY, CHECK_ENTRY]


def selection_schema(commit_schema, slots, lookups):
    """What the model answers with (the old action schema: ``tool``, ``reason`` and the resource ``child``): one fixed
    tool, one library lookup, a typed reasoning commit, or the commission of an allowed resource child on the
    resource selection and launch instructions the model chooses (the other assignment fields are the commission's)."""
    branches = [_branch({'kind': {'type': 'string', 'const': 'tool'},
                         'tool': {'type': 'string', 'const': item['name']}, 'arguments': item['input_schema']})
                for item in catalog()]
    branches.append(_branch({'kind': {'type': 'string', 'const': 'reason'}, 'commit': commit_schema}))
    branches[-1]['properties']['evidence_processing'] = {'type': 'object', 'properties': {'kind': {'type': 'string'}}}
    for name in lookups:
        library = LOOKUPS[name][1]
        branches.append(_branch({'kind': {'type': 'string', 'const': 'tool'},
                                 'tool': {'type': 'string', 'const': name},
                                 'arguments': _branch({'operation': {'type': 'string',
                                                                     'enum': [item['name'] for item in library()]},
                                                       'arguments': {'type': 'object'}})}))
    if slots:
        branches.append(_branch({'kind': {'type': 'string', 'const': 'episode_child'},
                                 'role': {'type': 'string', 'enum': list(slots)},
                                 'assignment': _branch({'resource_selection': SELECTION_SCHEMA,
                                                        'launch_instructions': LAUNCH_SELECTION_SCHEMA})}))
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


def instructions(*, knowledge, launch_library):
    """The old composition (``task_instructions.instructions``) for the actions this episode has: the A101
    investigation text with its paragraph about a commissioned child's typed form, the report update and redelivery
    (the parent writes no form here) replaced by a sentence about its own earlier actions, then this episode's goal
    text, the reasoning-commit requirement, then the tool-knowledge and launch-library texts when those libraries are
    present. The ``pending_child_delivery``, wait, native-event and decision-exchange paragraphs describe actions this
    episode no longer has."""
    text = replace_span(INSTRUCTIONS, 'A commissioned child returns ONLY', 'Do not execute native provider tools.',
                        HISTORY)
    text += '\n' + GOAL + '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def offering(summary, ctx):
    """What the model may choose now, from recorded reads of the adapter service: the capabilities, the permitted
    resource children and the answer schema."""
    assignment = summary['assignment']
    bound = set(read_adapters(ctx, 'bound_resource_ids'))
    capabilities = capabilities_of(read_adapters(ctx, 'declared_capabilities'),
                                   read_adapters(ctx, 'adapter_capabilities'), bound)
    slots = allowed_slots(assignment, capabilities, bound)
    schema = selection_schema(summary['reasoning_schema'], slots, lookups_offered(ctx.settings))
    return capabilities, slots, schema


def child_options(assignment, capabilities, slots):
    return [{'role': slot, 'resource_kind': RESOURCE_ROLES[slot],
             'resources': [value for value in capabilities if value['kind'] == RESOURCE_ROLES[slot]
                           and value['tool_names'] and value['availability'] != 'unavailable'
                           and _permitted(assignment, value)]} for slot in slots]


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the assignment, the capabilities of every declared resource, the
    duration estimates, the resource children it may commission, its own earlier actions, the usable handoffs so
    far, the yield table and the library listings (the old decision state and inputs, over this episode's summary)."""
    assignment = summary['assignment']
    capabilities, slots, schema = offering(summary, ctx)
    settings = ctx.settings
    knowledge_directory = settings.get('tool_knowledge_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    history = sorted([*summary['calls'], *summary['commissions']], key=lambda item: item['index'])
    context = {'goal': GOAL, 'role': summary['role'], 'scope': summary['scope'], 'assignment': assignment,
               'resource_capabilities': capabilities,
               'resource_tool_estimates': read_adapters(ctx, 'resource_tool_estimates', assignment),
               'child_options': child_options(assignment, capabilities, slots),
               'tools': catalog(), 'credit_binding': CREDIT_BINDING,
               'execution_progress': {'execution_handoffs': summary['execution_handoffs'],
                                      'unavailable_checks': summary['unavailable_checks'],
                                      'adapter_facts': summary['adapter_facts']},
               'last_local_outcome': summary['last_outcome'], 'requested_action_history': history,
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or assignment['launch_instructions'] is None
                                         else launch.materialize(assignment['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(schema))


def named_refs(value):
    """The record references a model-built value names (``ref``, ``..._ref``, ``..._refs``), except the ``@alias``
    references of a reasoning commit to its own rows."""
    found = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == 'ref' or name.endswith('_ref'):
                if not (isinstance(child, str) and child.startswith('@')):
                    found.append(child)
            elif name.endswith('_refs'):
                found.extend(ref for ref in child if not (isinstance(ref, str) and ref.startswith('@')))
            else:
                found.extend(named_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(named_refs(child))
    return found


def empty_commit(selection, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row, unless
    the answer declares ``evidence_processing.kind = no_applicable_evidence``."""
    payload = selection['commit']
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(payload)
            <= set(commit_schema['properties']) and all(value == [] for value in payload.values())
            and selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence')


def check_child_selection(selection, assignment, capabilities, slots):
    """The old ``prepare_assignment`` tests of the model's chosen assignment: the resource is a declared capability of
    the child's kind, permitted by the assignment, and the commissioner's own selection when it made one
    (``resource_selection_conflict``); the pinned launch instructions of the commissioner are kept
    (``launch_instruction_inheritance_conflict``). These validate the model's answer, before any commission is made."""
    if selection['role'] not in slots:
        raise ValueError('child_role_not_available_to_parent')
    chosen = selection['assignment']['resource_selection']
    capability = next((value for value in capabilities if value['resource_id'] == chosen['resource_id']), None)
    if (capability is None or capability['kind'] != RESOURCE_ROLES[selection['role']] or chosen['kind'] != capability['kind']
            or not _permitted(assignment, capability)):
        raise ValueError('resource_selection_conflict')
    if assignment['resource_selection'] is not None and chosen != assignment['resource_selection']:
        raise ValueError('resource_selection_conflict')
    retain_inherited_selection(assignment['launch_instructions'], selection['assignment']['launch_instructions'])


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one resource child commission, or reject it (no unit). An answer
    that does not fit the schema, a reasoning commit that is empty or names a record this Episode does not hold, a
    child outside the permitted resources, a launch-instruction selection that drops the commissioner's pins or one the
    library cannot materialise is invalid. ``resource.capabilities`` is always acceptable, so a unit is always
    offered."""
    capabilities, slots, schema = offering(summary, ctx)
    assignment = summary['assignment']
    try:
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason':
            unheld = [ref for ref in named_refs(selection['commit']) if not records.holds(ref)]
            if unheld:
                raise ValueError('record_not_held:' + ','.join(unheld))
            commit_schema = summary['reasoning_schema']
            Draft202012Validator(commit_schema).validate(selection['commit'])
            if empty_commit(selection, commit_schema):
                raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child':
            check_child_selection(selection, assignment, capabilities, slots)
            chosen = selection['assignment']['launch_instructions']
            if chosen is not None:
                directory = ctx.settings.get('launch_instructions_directory')
                if directory is None:
                    raise ValueError('launch_instruction_library_not_configured')
                LaunchInstructions(directory).materialize(chosen)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    kind = selection['kind']
    if kind == 'reason':
        return ToolCall('reason', {'commit': selection['commit'], 'scope': summary['scope']})
    if kind == 'episode_child':
        return ChildCall(selection['role'], {'resource_selection': selection['assignment']['resource_selection'],
                                             'launch_instructions': selection['assignment']['launch_instructions']})
    tool = selection['tool']
    if tool in LOOKUPS:
        return ToolCall(tool, selection['arguments'])
    return ToolCall(TOOL_OF[tool], selection['arguments'])
