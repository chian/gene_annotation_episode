"""The task: choose the resource the assigned work is launched on and commission the launch, one action per
decision.

The model chooses one action of a fixed set and code runs it. It writes no command and no assignment: the work is
the record the assignment names, and the commission of a resource child is written by ``msg_to_child``.

| Action | Offered | What code does |
|---|---|---|
| ``inspect_resource`` (``resource_id``: a declared resource) | always | reads the resource through the resource adapter service: its declared availability, whether it is bound, and the facts of its adapter. An unbound, unavailable, unauthenticated or unknown resource is a failed reading with its own code |
| ``launch_work`` (``resource_id``: a launchable resource) | until this Episode holds a handoff row | commissions the resource child of the resource's kind (``launch_api``, ``launch_local``, ``launch_hpc``), which launches the work once and returns the handoff and check rows in custody |
| ``check_handoff`` (``handoff_ref``: a held handoff row) | once a handoff row is held | the receiving check through the adapter the handoff's resource selects: ``await check_handoff(ctx, {'resource_selection': {'resource_id'}, 'handoff_ref'})``, written as a check row in custody |
| ``knowledge_lookup``, ``launch_instruction_lookup`` (``operation``: one of the library's operations; ``arguments``: the JSON text of that operation's arguments) | always | one lookup of the frozen tool-knowledge or launch-instruction library through the ``instruction_libraries`` service (the old lookups). They earn nothing |

A resource is launchable when it is bound to an adapter, has tools, is not declared unavailable, is of a kind the
assignment permits and is the fixed resource when the assignment fixes one (the old ``allowed_children`` and
``_permitted``). The resource service is the run's ``ResourceAdapters`` (declared as ``resource_adapter``):
``decide`` and ``action`` read ``declared_capabilities``, ``adapter_capabilities`` and ``bound_resource_ids``
through its read handle, so the system records them with the decision; ``decide`` reads the libraries' listing
and operations the same way. The episode performs an execution act (it chooses a resource and commissions a
launch); it reads no source and weighs no evidence, so it has no reasoning commit. The task always offers a unit and
never ends the Episode: its yield controller does."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    catalog as knowledge_catalog)

from .goal import BINDING_PATH

CHILD_SLOTS = {'launch_api': BINDING_PATH + '/api_resource_work_execution',
               'launch_local': BINDING_PATH + '/local_resource_work_execution',
               'launch_hpc': BINDING_PATH + '/hpc_resource_work_execution'}
SERVICES = ('resource_adapter', 'instruction_libraries')
ADAPTER = 'resource_adapter'
LIBRARIES = 'instruction_libraries'
SLOT_OF_KIND = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}
LOOKUPS = {'knowledge_lookup': knowledge_catalog, 'launch_instruction_lookup': launch_catalog}
AVAILABILITY_FAILURE = {'unavailable': 'resource_unavailable',
                        'authentication_required': 'resource_authentication_required',
                        'unknown': 'resource_availability_unknown'}

INSTRUCTIONS = (
    'You decide the next action of one episode of a gene annotation workflow: the submission of one piece of work '
    'to a compute resource.\n'
    'PURPOSE. The parent defined a piece of work as a record. Choose the resource it is launched on and commission '
    'the launch there, until a usable handoff exists: a launched job whose handoff a receiving check has '
    'confirmed. The job runs on after this episode: its results are acquired elsewhere.\n'
    'ASSIGNED WORK. context.work_ref is the record that defines the work; code passes it to the launch, you never '
    'write a command. context.resources lists every declared resource: its kind, its declared availability, '
    'whether it is bound in this run, and whether the work may be launched on it (bound, not unavailable, of a '
    'kind the parent permits). context.launched_jobs lists each job launched for this work, by its handoff '
    'record, with the state its latest check saw.\n'
    'ACTIONS. Answer with exactly one of the actions offered by the answer schema. Code executes it and you are '
    'asked again; what each earlier action came to is in context.actions_so_far, what each launch commission '
    'returned in context.commissions, what each reading returned in context.inspected, and what each lookup '
    'returned in context.lookup_results.\n'
    '- inspect_resource: read one declared resource, named by resource_id: its availability, whether it is bound, '
    'and what its interface says of it.\n'
    '- launch_work: commission the launch of the assigned work on one launchable resource, named by resource_id. '
    'The resource child of that kind launches the work once and returns at handoff. Offered until a job is handed '
    'off.\n'
    '- check_handoff: one status request for a launched job, named by its handoff_ref: the receiving check of the '
    'handoff.\n'
    '- knowledge_lookup, launch_instruction_lookup: one operation of the frozen tool-knowledge library or of the '
    'frozen launch-instruction library (context.libraries). operation is one of context.library_operations; '
    'arguments is the JSON text of its arguments, valid against that operation\'s input_schema. The libraries '
    'describe tools and resources; they select nothing and are not scientific evidence.\n'
    'CREDIT. context.credit lists what earns credit and whether it is earned: holding the handoff record of the '
    'launched work, and holding a receiving check that found the job in a known state. Nothing else earns '
    'credit: not a reading or a lookup. You do not end the episode: it is stopped when both '
    'are earned, or when further actions are not expected to earn more.')


def capabilities_of(declared, adapter_capabilities):
    """Every declared capability by resource id; a bound adapter's own capability replaces its declaration."""
    return {**{item['resource_id']: item for item in declared}, **adapter_capabilities}


def launchable(summary, capabilities, bound):
    """The resources the work may be launched on (see the module docstring)."""
    return [resource_id for resource_id, capability in capabilities.items()
            if resource_id in bound and capability['tool_names'] and capability['availability'] != 'unavailable'
            and capability['kind'] in summary['allowed_kinds']
            and summary['resource_id'] in (None, resource_id)]


def _read(adapter):
    capabilities = capabilities_of(adapter.read('declared_capabilities'), adapter.read('adapter_capabilities'))
    return capabilities, adapter.read('bound_resource_ids')


def _branch(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _one(value):
    return {'type': 'string', 'enum': [value]}


def answer_schema(summary, capabilities, bound):
    """The action format: the actions offered where the Episode stands, each with its arguments."""
    branches = [_branch({'action': _one('inspect_resource'),
                         'resource_id': {'type': 'string', 'enum': list(capabilities)}})]
    held = [job['handoff_ref'] for job in summary['jobs']]
    offered = launchable(summary, capabilities, bound)
    if held:
        branches.append(_branch({'action': _one('check_handoff'), 'handoff_ref': {'type': 'string', 'enum': held}}))
    elif offered:
        branches.append(_branch({'action': _one('launch_work'),
                                 'resource_id': {'type': 'string', 'enum': offered}}))
    for name, catalog in LOOKUPS.items():
        branches.append(_branch({'action': _one(name),
                                 'operation': {'type': 'string', 'enum': [item['name'] for item in catalog()]},
                                 'arguments': {'type': 'string'}}))
    return _branch({'selection': {'anyOf': branches}})


def decide(summary, feedback, ctx):
    capabilities, bound = _read(ctx.services[ADAPTER])
    offered = launchable(summary, capabilities, bound)
    units = summary['launch_units']
    libraries = ctx.services[LIBRARIES]
    context = {'work_ref': summary['work_ref'],
               'resources': [{'resource_id': resource_id, 'kind': capability['kind'],
                              'availability': capability['availability'], 'bound': resource_id in bound,
                              'launchable': resource_id in offered}
                             for resource_id, capability in capabilities.items()],
               'inspected': summary['inspections'],
               'launched_jobs': [{name: job[name] for name in ('handoff_ref', 'resource_id', 'submitted_at',
                                                              'state', 'result_available')}
                                 for job in summary['jobs']],
               'commissions': summary['commissions'], 'actions_so_far': summary['actions'],
               'credit': [{'for': 'the handoff record of the launched work', 'credit': units['handoff_unit'],
                           'earned': summary['handoff_held']},
                          {'for': 'a receiving check that found the job in a known state',
                           'credit': units['check_unit'], 'earned': summary['usable_handoff_held']}],
               'libraries': libraries.read('context'), 'library_operations': libraries.read('catalog'),
               'lookup_results': summary['lookups']}
    if feedback is not None:
        context['rejected_answer'] = feedback
    return ModelRequest('REASONING', INSTRUCTIONS, context, answer_schema(summary, capabilities, bound))


def selected_action(response, summary, capabilities, bound):
    """The one action an answer selects, or its rejection: the answer must be one of the actions offered where the
    Episode stands, with arguments that fit their format (for a lookup: JSON text of an object)."""
    try:
        Draft202012Validator(answer_schema(summary, capabilities, bound)).validate(response)
        selection = response['selection']
        if selection['action'] in LOOKUPS:
            given = json.loads(selection['arguments'])
            Draft202012Validator({'type': 'object'}).validate(given)
    except (ValueError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    if selection['action'] in LOOKUPS:
        return ToolCall(selection['action'], {'operation': selection['operation'], 'arguments': given})
    if selection['action'] == 'launch_work':
        kind = capabilities[selection['resource_id']]['kind']
        return ChildCall(SLOT_OF_KIND[kind], {'resource_id': selection['resource_id'], 'kind': kind})
    if selection['action'] == 'check_handoff':
        job = next(job for job in summary['jobs'] if job['handoff_ref'] == selection['handoff_ref'])
        return ToolCall('check_handoff', {'resource_selection': {'resource_id': job['resource_id']},
                                          'handoff_ref': job['handoff_ref']})
    return ToolCall('inspect_resource', {'resource_id': selection['resource_id']})


def action(response, summary, records, ctx):
    capabilities, bound = _read(ctx.services[ADAPTER])
    return selected_action(response, summary, capabilities, bound)


def inspect_resource(arguments, ctx):
    """The old ``inspect_resource``: one declared resource as the resource adapter service knows it. An unbound,
    unavailable, unauthenticated or unknown resource is a failed reading with its own code; nothing is submitted."""
    adapter = ctx.services[ADAPTER]
    resource_id = arguments['resource_id']
    capability = capabilities_of(adapter.declared_capabilities(), adapter.adapter_capabilities())[resource_id]
    bound = adapter.is_bound(resource_id)
    code = AVAILABILITY_FAILURE.get(capability['availability']) or (None if bound else 'resource_not_bound')
    outcome = {'status': 'completed' if code is None else 'failed', 'resource_id': resource_id,
               'kind': capability['kind'], 'availability': capability['availability'], 'bound': bound,
               'facts': adapter.facts({'resource_selection': {'resource_id': resource_id}}) if bound else None}
    return outcome if code is None else {**outcome, 'failure': {'code': code, 'detail': None}}


async def check_handoff(arguments, ctx):
    """The receiving check of a returned handoff, through the adapter the handoff's resource selects."""
    return await ctx.services[ADAPTER].check_handoff(ctx, arguments)


def knowledge_lookup(arguments, ctx):
    """One operation of the frozen tool-knowledge library (the old ``knowledge_lookup``)."""
    return ctx.services[LIBRARIES].execute(arguments['operation'], arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    """One operation of the frozen launch-instruction library (the old ``launch_instruction_lookup``)."""
    return ctx.services[LIBRARIES].execute(arguments['operation'], arguments['arguments'])


TOOLS = {'inspect_resource': inspect_resource, 'check_handoff': check_handoff,
         'knowledge_lookup': knowledge_lookup, 'launch_instruction_lookup': launch_instruction_lookup}
