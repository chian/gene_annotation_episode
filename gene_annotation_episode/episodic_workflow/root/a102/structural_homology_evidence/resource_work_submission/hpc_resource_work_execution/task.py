"""The task: work on the one selected HPC resource through its own tools, one operation per unit.

Carried from the old ``operations.py`` (``ResourceOperations.execute``), ``operation_catalog.py`` (``catalog``),
``resource_selection.py`` (``capabilities``, ``_adapter``, ``_permitted``), ``resource_inspection.py``
(``inspect_resource``), ``handoff_check.py`` (``check_selected_handoff``), ``resource_contracts.py`` (``_failure``,
``_outcome``, ``_availability_failure``), ``instructions.py`` (the instruction composer), ``task.py``
(``apply_response``: the admission of the selection) and the decision context of ``decision_context.py``,
``decision_inputs.py`` and ``task_decision.py``. This episode is the thin resource-adapter form: everything resource
specific came from the selected resource adapter (its tools, its duration estimates). The adapter is the service
``resource_adapter``; decisions read it through the recorded read handle, tools act through it.

The model selects one tool: ``resource.capabilities``, ``resource.inspect`` or ``resource.check_handoff`` (this
episode's own, offered when the adapter's catalogue lists them: the old ``execute`` handled them before the adapter)
or any other tool of the adapter's own catalogue (the adapter's list is authoritative). They run as the tools
``resource_capabilities``, ``resource_inspect``, ``resource_check_handoff`` and ``adapter_tool`` (a tool name here is
lowercase with underscores; the model-facing names are the old ones). The old ``reason`` action is not carried: the
launch assignment has no scope and passes no subject records to reason about. The ``wait`` action is machinery that
is not carried (README 3b). ``child`` and ``redeliver_report`` never applied (no children). The task always offers a
unit and never ends the Episode: ``resource.capabilities`` is always available; only the yield controller stops the
Episode.

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and the optional
``launch_instructions_directory`` and ``knowledge_library_directory``.

BLOCKED-ON-JOB-SERVICE: ``resource_adapter`` is not provided. The calls this episode wants of it are
``read('capabilities')``, ``read('bound_resource_ids')``, ``read('catalog', assignment)``,
``read('estimates', assignment)`` (decisions), ``capabilities()``, ``bound_resource_ids()``,
``check_handoff(assignment, handoff, key=..., resumed=...)`` and ``execute(assignment, tool_name, tool_arguments,
key=..., resumed=...)`` (tools). Each raises ``NotImplementedError`` where it is reached."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import (
    INSTRUCTIONS as INVESTIGATION_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, HANDOFF_SCHEMA, RESOURCE_ROLES, _validate, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('resource_adapter',)
TRANSPORT = {'open_records_as_text': True,
             'argument_transport_error': 'hpc_resource_work_execution_argument_transport_unsupported'}

CAPABILITIES_TOOL = {'name': 'resource.capabilities',
                     'description': 'Read actual capability availability and configured resource information; '
                                    'this does not select or submit work.',
                     'input_schema': obj({})}
CREDIT_BINDING = {'credit': 'one for each distinct usable execution handoff held (capability binding and '
                            'execution handle); it counts what the resource tools returned'}


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


def read_adapter(ctx, member, *arguments):
    """One recorded read of the adapter, in a decision.

    BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: ``ctx.services['resource_adapter'].read(member,
    *arguments)`` with member one of ``capabilities``, ``bound_resource_ids``, ``catalog``, ``estimates``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: "
                              "ctx.services['resource_adapter'].read(member, *arguments)")
    return ctx.services['resource_adapter'].read(member, *arguments)


def declared_capabilities(ctx):
    """The old ``ResourceResourceSelection.capabilities``: every declared capability, validated; one whose resource
    has no bound adapter is shown accurately with no tools."""
    bound = set(read_adapter(ctx, 'bound_resource_ids'))
    values = []
    for capability in read_adapter(ctx, 'capabilities'):
        value = _validate(capability, CAPABILITY_SCHEMA)
        if value['resource_id'] not in bound:
            value['tool_names'] = []
        values.append(value)
    return values


def catalog(ctx, assignment):
    """The old ``catalog``: ``resource.capabilities`` plus the selected adapter's own tools."""
    return [json.loads(json.dumps(CAPABILITIES_TOOL)), *read_adapter(ctx, 'catalog', assignment)]


def selected_capability(ctx, assignment, tools):
    """The capability of the selected resource, which must be declared, of kind ``hpc`` and permitted by the
    constraints (``resource_selection_conflict``); every tool its capability declares must be in the catalogue
    (``resource_capability_tool_not_bound``). A wrong assignment fails here."""
    capabilities = declared_capabilities(ctx)
    selection = assignment['resource_selection']
    capability = next((value for value in capabilities if value['resource_id'] == selection['resource_id']), None)
    if (capability is None or capability['kind'] != RESOURCE_ROLES['launch_hpc']
            or not _permitted(assignment, capability)):
        raise ValueError('resource_selection_conflict')
    if not set(capability['tool_names']) <= {tool['name'] for tool in tools}:
        raise ValueError('resource_capability_tool_not_bound')
    return capabilities


def record_reply(reply, ctx):
    """The adapter's reply, written as one artifact through custody (held as produced); its reference travels in the
    outcome as ``reply_ref``."""
    return ctx.store.artifact(json.dumps(reply, sort_keys=True, separators=(',', ':')), 'application/json')


def resource_capabilities(arguments, ctx):
    """The old ``execute`` for ``resource.capabilities``: the actual capabilities of every declared resource.

    BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: ``ctx.services['resource_adapter'].capabilities()``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: "
                              "ctx.services['resource_adapter'].capabilities()")
    capabilities = [_validate(value, CAPABILITY_SCHEMA) for value in ctx.services['resource_adapter'].capabilities()]
    return _outcome({'capabilities': capabilities})


def resource_inspect(arguments, ctx):
    """The old ``inspect_resource``: the declared capability of a resource, or why it cannot be used
    (``resource_not_bound`` or an availability failure).

    BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted calls: ``ctx.services['resource_adapter'].capabilities()`` and
    ``ctx.services['resource_adapter'].bound_resource_ids()``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: "
                              "ctx.services['resource_adapter'].capabilities() and .bound_resource_ids()")
    service = ctx.services['resource_adapter']
    reference = arguments['resource_id']
    capability = next((value for value in (_validate(item, CAPABILITY_SCHEMA) for item in service.capabilities())
                       if value['resource_id'] == reference), None)
    if capability is None:
        return _outcome(failure=_failure('resource_not_bound', [reference]))
    code = _availability_failure(capability)
    if code is None and reference not in set(service.bound_resource_ids()):
        code = 'resource_not_bound'
    return _outcome({'capability': capability}, _failure(code, [reference]) if code else None)


async def execute_adapter(assignment, tool_name, tool_arguments, ctx):
    """One tool of the selected adapter; its reply has the old outcome shape (``status``, ``result``,
    ``feedback``).

    BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: ``await ctx.services['resource_adapter'].execute(
    assignment, tool_name, tool_arguments, key=ctx.operation_key, resumed=ctx.resumed)``, idempotent on the key
    (a submission whose outcome is uncertain must be found again, not repeated)."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: await "
                              "ctx.services['resource_adapter'].execute(assignment, tool_name, tool_arguments, "
                              'key=ctx.operation_key, resumed=ctx.resumed)')
    return await ctx.services['resource_adapter'].execute(assignment, tool_name, tool_arguments,
                                                          key=ctx.operation_key, resumed=ctx.resumed)


async def check_adapter_handoff(assignment, handoff, ctx):
    """The adapter's receiving check of one handoff (the old ``callback(context, handoff, operation_key)``).

    BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: ``await ctx.services['resource_adapter'].check_handoff(
    assignment, handoff, key=ctx.operation_key, resumed=ctx.resumed)``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: await "
                              "ctx.services['resource_adapter'].check_handoff(assignment, handoff, "
                              'key=ctx.operation_key, resumed=ctx.resumed)')
    return await ctx.services['resource_adapter'].check_handoff(assignment, handoff, key=ctx.operation_key,
                                                                resumed=ctx.resumed)


def _handoff_outcome(reply, ctx):
    """A reply carrying a handoff is checked against the handoff schema; a malformed handoff is a failed outcome
    (``invalid_resource_handoff``, as the old handoff check). The reply is kept as an artifact in custody."""
    reply_ref = record_reply(reply, ctx)
    result = reply.get('result')
    handoff = (result or {}).get('execution_handoff')
    if handoff is not None:
        try:
            _validate(handoff, HANDOFF_SCHEMA)
        except ValueError:
            return {**_outcome(failure=_failure('invalid_resource_handoff', [str(handoff.get('execution_handle'))])),
                    'reply_ref': reply_ref}
    return {'status': reply['status'], 'record_refs': [], 'changed_record_refs': [], 'result': result,
            'feedback': reply.get('feedback'), 'reply_ref': reply_ref}


async def adapter_tool(arguments, ctx):
    """The old ``execute`` for every other tool of the selected adapter."""
    reply = await execute_adapter(arguments['assignment'], arguments['tool_name'], arguments['tool_arguments'], ctx)
    return _handoff_outcome(reply, ctx)


async def resource_check_handoff(arguments, ctx):
    """The old ``check_selected_handoff``: the adapter's receiving check of the handoff the model names. A handoff
    the adapter rejects (``ValueError``, ``KeyError``, ``OSError``) is a failed outcome (``invalid_resource_handoff``);
    ``resource_information_identity_conflict`` is raised."""
    handoff = arguments['handoff']
    try:
        reply = await check_adapter_handoff(arguments['assignment'], handoff, ctx)
    except (ValueError, KeyError, OSError) as error:
        if str(error) == 'resource_information_identity_conflict':
            raise
        return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))
    return _handoff_outcome(reply, ctx)


TOOLS = {'resource_capabilities': resource_capabilities, 'resource_inspect': resource_inspect,
         'resource_check_handoff': resource_check_handoff, 'adapter_tool': adapter_tool}


def selection_schema(tools):
    """What the model answers with: one tool of the catalogue and its arguments (the old action schema, tool kind
    only)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': tool['name']},
                                             'arguments': tool['input_schema']}) for tool in tools]}})


def instructions(*, knowledge, launch_library):
    """The old composition (``instructions.py``) for the one kind of action this episode offers: the A102
    investigation text with its action-selection sentence (which named a reasoning commitment and a child
    improvement) narrowed to the tools, then this episode's goal text, then the tool-knowledge and launch-library
    texts when those libraries are present. The reasoning-commit, ``pending_child_delivery``, wait, native-event
    and decision-exchange paragraphs describe actions this episode does not offer."""
    text = replace_span(INVESTIGATION_INSTRUCTIONS, 'Select one ordinary tool, one typed reasoning commitment',
                        'There are no biological departments', 'Select one ordinary tool. ')
    text += '\n' + GOAL
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    """Ask the model for the next operation, shown the assignment, the capabilities, the adapter's tools and duration
    estimates, its own earlier operations and the yield table (the old decision state and inputs over this
    episode's summary). A selected resource that is not declared, not hpc, not permitted by the constraints, or
    whose declared tools the adapter does not offer fails here: it is a wrong commission."""
    assignment = summary['assignment']
    tools = catalog(ctx, assignment)
    capabilities = selected_capability(ctx, assignment, tools)
    settings = ctx.settings
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    context = {'goal': GOAL, 'role': summary['role'], 'assignment': assignment,
               'resource_capabilities': capabilities,
               'resource_tool_estimates': read_adapter(ctx, 'estimates', assignment),
               'tools': tools, 'credit_binding': CREDIT_BINDING,
               'last_local_outcome': summary['last_outcome'], 'requested_action_history': summary['calls'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or 'launch_instructions' not in assignment
                                         else launch.materialize(assignment['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, strict_output_schema(selection_schema(tools), **TRANSPORT))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer outside the schema of the
    catalogue, or whose arguments fail the tool's input schema, is invalid. The assignment travels in the
    arguments of the tools that need it, because a tool is handed no summary."""
    assignment = summary['assignment']
    schema = selection_schema(catalog(ctx, assignment))
    try:
        value = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(value)
        selected = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    name = selected['tool']
    if name == 'resource.capabilities':
        return ToolCall('resource_capabilities', {})
    if name == 'resource.inspect':
        return ToolCall('resource_inspect', selected['arguments'])
    if name == 'resource.check_handoff':
        return ToolCall('resource_check_handoff', {'assignment': assignment, 'handoff': selected['arguments']['handoff']})
    return ToolCall('adapter_tool', {'assignment': assignment, 'tool_name': name,
                                     'tool_arguments': selected['arguments']})
