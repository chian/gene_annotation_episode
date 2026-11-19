"""The task: work on the one selected HPC resource through its own tools, one operation per unit.

Carried from the old ``execution_operations.py`` (``OperationalOperations``: ``capabilities``, ``_adapter``,
``catalog``, ``execute``), ``execution_contracts.py`` (``_failure``, ``_outcome``),
``from_parent.py`` (``_permitted``), ``task_instructions.py`` (the instruction composer), ``task.py``
(``apply_response``: the admission of the selection), and the decision context of ``decision_state.py`` and
``decision_inputs.py``. This episode is the thin resource-adapter form: everything resource specific came from the
selected resource adapter (its tools, its duration estimates). The adapter is the service ``resource_adapter``;
decisions read it through the recorded read handle, tools act through it.

The model selects one tool: ``resource.capabilities`` (this episode's own) or one tool of the adapter's own
catalogue (the adapter's list is authoritative). ``resource.capabilities`` runs as the tool ``resource_capabilities``
and every adapter tool as the tool ``adapter_tool`` (a tool name here is lowercase with underscores; the model-facing
names are the old ones). The old ``reason`` action is the tool ``reason`` (``ctx.store.commit_reasoning`` under the scope of the
assignment's ``input_refs`` subjects). The ``wait`` action is machinery that is not carried (README 3b). ``child`` and
``redeliver_report`` never applied (no children). The task always offers a unit and never ends the Episode:
``resource.capabilities`` is always available; only the yield controller stops the Episode.

Settings this episode reads (``ctx.settings``): ``cost`` and ``parameters`` (``yield_estimator.py``) and the
optional ``launch_instructions_directory`` and ``knowledge_library_directory``.

BLOCKED-ON-JOB-SERVICE: ``resource_adapter`` is not provided. The calls this episode wants of it are
``read('capabilities')``, ``read('bound_resource_ids')``, ``read('catalog', assignment)``,
``read('estimates', assignment)`` (decisions), ``capabilities()`` and ``execute(assignment, tool_name,
tool_arguments, key=..., resumed=...)`` (tools). Each raises ``NotImplementedError`` where it is reached."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import (
    INSTRUCTIONS as INVESTIGATION_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, HANDOFF_SCHEMA, RESOURCE_ROLES, _validate, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('resource_adapter',)

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
    """The old ``OperationalOperations.capabilities``: every declared capability, validated; one whose resource has
    no bound adapter is shown accurately with no tools."""
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


def resource_capabilities(arguments, ctx):
    """The old ``execute`` for ``resource.capabilities``: the actual capabilities of every declared resource.

    BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: ``ctx.services['resource_adapter'].capabilities()``."""
    raise NotImplementedError("BLOCKED-ON-JOB-SERVICE: resource_adapter; wanted call: "
                              "ctx.services['resource_adapter'].capabilities()")
    capabilities = [_validate(value, CAPABILITY_SCHEMA) for value in ctx.services['resource_adapter'].capabilities()]
    return _outcome({'capabilities': capabilities})


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


async def adapter_tool(arguments, ctx):
    """The old ``execute`` for every tool of the selected adapter. The reply is written as one record through
    custody (``reply_ref``, held as produced) and a handoff it carries is checked against the handoff schema; a
    malformed handoff is a failed outcome (``invalid_resource_handoff``, as the old handoff check)."""
    reply = await execute_adapter(arguments['assignment'], arguments['tool_name'], arguments['tool_arguments'], ctx)
    reply_ref = ctx.store.artifact(json.dumps(reply, sort_keys=True, separators=(',', ':')), 'application/json')
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


def reason(arguments, ctx):
    """The old ``reason`` action: one typed reasoning commit (``store.commit_reasoning(payload, scope, key)``). The
    system owns the account owner; the operation key makes the commit idempotent. A payload that names a record the
    episode does not hold is returned as an invalid outcome."""
    try:
        return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)
    except CustodyError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'errors': [], 'notices': [],
                'conflicts': [], 'aliases': {}, 'error_code': 'record_not_held', 'feedback': {'detail': str(error)}}


TOOLS = {'resource_capabilities': resource_capabilities, 'adapter_tool': adapter_tool, 'reason': reason}


def selection_schema(tools):
    """What the model answers with: one tool of the catalogue and its arguments (the old action schema, tool kind
    only)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': tool['name']},
                                             'arguments': tool['input_schema']}) for tool in tools]
                              + [obj({'kind': {'const': 'reason'}, 'commit': {'type': 'object'}})]}})


def instructions(*, knowledge, launch_library):
    """The old composition (``task_instructions.instructions``) for the one kind of action this episode offers:
    the A101 investigation text with its action-selection sentence (which named a reasoning commitment and a child
    improvement) narrowed to the tools and the reasoning commit, then this episode's goal text, then the tool-knowledge and launch-library
    texts when those libraries are present. The reasoning-commit, ``pending_child_delivery``, wait, native-event
    and decision-exchange paragraphs describe actions this episode does not offer."""
    text = replace_span(INVESTIGATION_INSTRUCTIONS, 'Select one ordinary tool, one typed reasoning commitment',
                        'There are no biological departments', 'Select one ordinary tool or one typed reasoning commitment. ')
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
               'tools': tools, 'reasoning_commit_schema': summary['reasoning_schema'], 'credit_binding': CREDIT_BINDING,
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
                        context, generation_schema(selection_schema(tools)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer outside the schema of the
    catalogue, or whose arguments fail the tool's input schema, is invalid. The adapter's tool travels with the
    assignment, because a tool is handed no summary."""
    assignment = summary['assignment']
    schema = selection_schema(catalog(ctx, assignment))
    try:
        value = decode_response(response, schema)
        Draft202012Validator(schema).validate(value)
        selected = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selected['kind'] == 'reason':
        schema = records.reasoning_schema()
        payload = selected['commit']
        if (set(schema.get('required', schema['properties'])) <= set(payload) <= set(schema['properties'])
                and all(value == [] for value in payload.values())):
            raise Rejected(rejection_feedback(ValueError('empty_reasoning_commit'), category='action_contract'))
        return ToolCall('reason', {'commit': payload, 'scope': {'subject_refs': list(summary['input_refs'])}})
    if selected['tool'] == CAPABILITIES_TOOL['name']:
        return ToolCall('resource_capabilities', {})
    return ToolCall('adapter_tool', {'assignment': assignment, 'tool_name': selected['tool'],
                                     'tool_arguments': selected['arguments']})
