"""The task: get the commissioned job launched. The first unit is the lookup of the configured resources (the
caller-bound resource configuration and the recorded inventory: ``execution_capabilities``, decided by code); after
it the model is the router: it answers with one defined action and code carries it out.

- ``commission_launch`` with the resource to launch on, one of the permitted resource ids. Code makes the
  commission: a ``ChildCall`` on the launch child that owns the resource's kind (``launch_api``, ``launch_local`` or
  ``launch_hpc``), whose assignment ``msg_to_child`` builds from the request of that resource. The model writes no
  command and no part of a commission.
- ``knowledge_lookup`` and ``launch_instruction_lookup``: one operation of the run-frozen tool-instruction library
  or of the run-frozen launch-instruction library, with that operation's own arguments. What a lookup returned is
  shown at the next decision.

Pinning is not a model action. The sections of the launch-instruction library that a lookup read are pinned by code
at the end of that unit (``launch.instructions.select`` of the section read: its identity and digest), and
``msg_to_child`` adds the pins to the instructions the commissioner pinned, so they travel to the launch child with
the request. The library's ``select`` operation is therefore not offered as a choice.

The task always offers a unit and never ends the Episode: the yield controller (``yield_estimator.py``) alone
stops it. A lookup earns nothing here (``credit.py`` counts handoffs).

The model is shown the launch assignment once, the permitted resources, the configured resources, what each launch
child returned (its credit, whether its handoff exists, the handoff record references and its counts), what its
lookups returned, the pinned launch instructions, and the credit: what a handoff earns here and what each action
earned so far. An answer ``action`` rejected is shown at the next decision (``feedback``).

A resource of the API kind is described through the ``job_access`` service: its operations and configuration facts
(``capabilities(resource_id)``), the BV-BRC values already received (``received_bvbrc_context()``) and the
service's validation of an API request (``validate_assignment(request)``). The service has no API route yet
(``LAUNCH_MONITOR_EXTRACT_MECHANICS.md``, "Not provided yet", item 3), so a launch assignment with an API request
raises where the member is called.

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id, each with ``kind`` ``local``,
``pbs_ssh``, ``hmmer_api`` or ``api``), ``initial_information`` (the recorded inventory by resource id),
``coordinator_workspace`` (the run directory the resource validators work in), ``launch_instructions_directory``
and ``tool_knowledge_directory`` (the frozen directory of each library) and ``task_yield_profiles`` (read by
``yield_estimator.py``)."""
from copy import deepcopy
import inspect

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    ToolKnowledge, catalog as knowledge_catalog)

from .goal import BINDING_PATH

CHILD_SLOTS = {'launch_api': BINDING_PATH + '/api_job_execution', 'launch_hpc': BINDING_PATH + '/hpc_job_execution',
               'launch_local': BINDING_PATH + '/local_job_execution'}
SERVICES = ('job_access',)

# The kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
# What the model is shown of a configured resource.
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
# The ``native_*`` bindings a configured resource may carry.
ALLOWED_NATIVE = {'native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                  'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation'}


def launch_reads():
    """The operations of the launch-instruction library the model may choose. Pinning
    (``launch.instructions.select``) is done by code."""
    return [operation for operation in launch_catalog() if operation['name'] != 'launch.instructions.select']


# The operations of each library the model may choose.
LIBRARIES = {'knowledge_lookup': knowledge_catalog, 'launch_instruction_lookup': launch_reads}
INSTRUCTIONS = (
    'Choose which permitted concrete execution request to commission on an explicit resource_id. The configured '
    'resources and the recorded inventory inform the choice. The original job, immutable inputs, constraints and '
    'pinned instructions are preserved: the request is commissioned unchanged. Receive the launch child\'s typed '
    'handoff; no infrastructure chooses an approach. An actual received usable handoff completes this launch '
    'endpoint with exact zero future credit.\n'
    '\n'
    'This episode exists to get the assigned job launched: it commissions a launch child on one permitted resource '
    'and receives the handoff record of the job that child launched. You do not write or run a command and you do '
    'not write any part of a commission: you choose the resource, and code commissions the launch child that owns '
    'that resource\'s kind with the request of that resource from the assignment, unchanged. The child launches '
    'that request\'s job and returns at handoff.\n'
    '\n'
    'Credit is the measure of this episode. A usable handoff received from a launch child is the only thing that '
    'earns credit: each permitted resource that gets its first usable handoff earns '
    'credit.handoff_earns_per_resource. Nothing else earns credit: a lookup earns none. Each action is one '
    'recorded unit: what it returned and the credit it earned count, including a launch that failed. A child\'s '
    'own credit, in launches_so_far, says whether that launch was productive. You cannot end the episode; it ends '
    'when every permitted resource has its handoff, or when further actions stop earning credit.\n'
    '\n'
    'Actions. Answer with exactly one, as JSON:\n'
    '- commission_launch, with resource_id (one of the permitted resource ids): commission the launch child of '
    'that resource for its request. Its result is the child\'s return: its credit, whether the handoff exists, the '
    'handoff record references and its counts.\n'
    '- knowledge_lookup, with operation and arguments: one read of the run-frozen tool-instruction library. '
    'knowledge.search (query, offset, limit) pages its entries, an empty query lists them; knowledge.entry '
    '(entry_id) reads the section index of one entry; knowledge.read (entry_id, section_id, offset, limit) reads '
    'lines of one section.\n'
    '- launch_instruction_lookup, with operation and arguments: one read of the run-frozen launch-instruction '
    'library, the instructions for launching on a kind of resource. launch.instructions.search (query, offset, '
    'limit, resource_kind), launch.instructions.entry (entry_id) and launch.instructions.read (entry_id, '
    'section_id, offset, limit) read it the same way. A section you read is pinned by code and travels to the '
    'launch child you commission afterwards, added to the instructions the assignment already pins; '
    'pinned_launch_instructions shows the pins.\n'
    'What a lookup returned is in lookups_so_far. Instructions describe ways to work; they do not select '
    'resources, override caller constraints, establish current availability or supply scientific evidence. No '
    'lookup is mandatory.')


def _resources(settings):
    """The checks of the configured resources."""
    resources, information = settings['resources'], settings['initial_information']
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    for configuration in resources.values():
        native = {name for name in configuration if name.startswith('native_')}
        if native - ALLOWED_NATIVE:
            raise ValueError('a103_execution_resource_binding_conflict')
        if native:
            # old: a103_execution_bindings.validate_primary_resource_bindings / validate_preparation_resource_binding
            raise NotImplementedError('unplaced:a103_execution_bindings.validate_primary_resource_bindings')
    return resources


def _bound(summary, ctx):
    """Each request names a bound resource of its kind, and the transport (or the API service) accepts the
    request. A configuration or request it refuses raises and fails the run: it is not a model answer."""
    settings = ctx.settings
    _resources(settings)
    for resource_id, request in summary['assignment']['requests'].items():
        config = settings['resources'].get(resource_id)
        if config is None:
            raise ValueError('execution_resource_not_bound')
        kind = 'api' if request['version'] != 'practical_assignment_v1' else request['resource_kind']
        if KINDS[config['kind']] != kind:
            raise ValueError('execution_resource_kind_conflict')
        if kind == 'api':
            try:
                ctx.services['job_access'].read('validate_assignment', request)
            except AttributeError:
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: '
                    'ctx.services["job_access"].read("validate_assignment", request)') from None
        else:
            TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace'],
                              artifact_selector=terminal_artifact_paths).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The caller-bound resource configuration and the already recorded inventory, with no discovery,
    authentication probe or selection. A resource of the API kind also lists its configured operations and
    configuration facts, and the BV-BRC values already received, which only the job-access service knows."""
    settings = ctx.settings
    information = []
    api_resources = False
    for resource_id, config in settings['resources'].items():
        kind = KINDS[config['kind']]
        value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
                 'observed_at': 'caller_configuration', 'provenance_refs': [],
                 **{key: deepcopy(config[key]) for key in RESOURCE_KEYS if key in config},
                 'inventory_snapshot': deepcopy(settings['initial_information'].get(resource_id))}
        if kind == 'api':
            api_resources = True
            service = ctx.services['job_access']
            if not hasattr(service, 'capabilities'):
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: '
                    'await ctx.services["job_access"].capabilities(resource_id)')
            entries = service.capabilities(resource_id)
            if inspect.isawaitable(entries):
                entries = await entries
            value['tool_names'] = [entry['name'] for entry in entries]
            facts = {}
            for entry in entries:
                reported = entry.get('configuration', {})
                for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
                    if name not in reported:
                        continue
                    actual = reported[name]
                    if type(actual) is not bool:
                        raise ValueError('api_configuration_fact_must_be_boolean')
                    if name in facts and facts[name] != actual:
                        raise ValueError('api_configuration_fact_conflict')
                    facts[name] = actual
            if facts:
                value['api_configuration_facts'] = facts
        information.append(value)
    received = []
    if api_resources:
        service = ctx.services['job_access']
        if not hasattr(service, 'received_bvbrc_context'):
            raise NotImplementedError(
                'BLOCKED-ON-JOB-SERVICE: job_access.received_bvbrc_context(); wanted call: '
                'ctx.services["job_access"].received_bvbrc_context()')
        received = service.received_bvbrc_context()
        if inspect.isawaitable(received):
            received = await received
    return {'execution_resource_capabilities': information,
            'execution_initial_information': deepcopy(settings['initial_information']),
            'received_bvbrc_values': received}


def knowledge_lookup(arguments, ctx):
    """One operation of the run-frozen tool-instruction library."""
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    """One operation of the run-frozen launch-instruction library. A section that was read is pinned here, by code,
    at the end of the unit: the pin (the section's identity and digest) is what travels to a launch child."""
    library = LaunchInstructions(ctx.settings['launch_instructions_directory'])
    outcome = library.execute(arguments['operation'], arguments['arguments'])
    if arguments['operation'] == 'launch.instructions.read' and outcome['status'] == 'completed':
        outcome['pinned'] = library.select([{'entry_id': arguments['arguments']['entry_id'],
                                             'section_id': arguments['arguments']['section_id']}])
    return outcome


TOOLS = {'execution_capabilities': execution_capabilities, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def answer_schema(summary):
    """What the model answers with: one defined action. The commission names a permitted resource id; a lookup
    names one operation of its library with that operation's arguments."""
    def one(name, fields):
        return {'type': 'object', 'additionalProperties': False, 'required': ['name', *fields],
                'properties': {'name': {'type': 'string', 'const': name}, **fields}}
    actions = [one('commission_launch', {'resource_id': {'type': 'string', 'enum': sorted(summary['permitted'])}})]
    actions.extend(one(name, {'operation': {'type': 'string', 'const': operation['name']},
                              'arguments': deepcopy(operation['input_schema'])})
                   for name, catalog in sorted(LIBRARIES.items()) for operation in catalog())
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': actions}}}


def output_schema(summary):
    """The answer schema in the form the model endpoint takes (every object closed, every property required)."""
    return generation_schema(answer_schema(summary))


def decide(summary, feedback, ctx):
    """The lookup of the configured resources first (after they accepted the requests); then one action: the model
    chooses it from the assignment, the resources, what its actions returned so far and their credit."""
    if summary['capabilities'] is None:
        _bound(summary, ctx)
        return ToolCall('execution_capabilities', {})
    context = {'assignment': summary['assignment'],
               'permitted_resources': {resource_id: entry['kind']
                                       for resource_id, entry in sorted(summary['permitted'].items())},
               'resources': summary['capabilities']['execution_resource_capabilities'],
               'received_bvbrc_values': summary['capabilities']['received_bvbrc_values'],
               'launches_so_far': summary['launches'],
               'lookups_so_far': summary['lookups'],
               'pinned_launch_instructions': summary['pinned_launch_instructions'],
               'credit': {'handoff_earns_per_resource': summary['handoff_unit'],
                          'resources_with_a_handoff': summary['handoff_resources'],
                          'earned_by_each_action_so_far': summary['credit_by_action']}}
    if feedback is not None:
        context['feedback'] = feedback
    return ModelRequest('REASONING', INSTRUCTIONS, context, output_schema(summary))


def action(response, summary, records, ctx):
    """The unit of the chosen action: the commission of the chosen resource's request on the launch child that owns
    the resource's kind, or one operation of a library. An answer that is not one of the defined actions with its
    arguments is rejected: no unit is created."""
    schema = answer_schema(summary)
    try:
        chosen = decode_response(response, schema)['action']
        Draft202012Validator(schema).validate({'action': chosen})
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if chosen['name'] == 'commission_launch':
        return ChildCall(summary['permitted'][chosen['resource_id']]['slot'], {'resource_id': chosen['resource_id']})
    return ToolCall(chosen['name'], {'operation': chosen['operation'], 'arguments': chosen['arguments']})
