"""The task: get the commissioned structural homology job launched. The first unit is the lookup of the configured
resources (the caller-bound resource configuration and the recorded inventory: ``execution_capabilities``, decided
by code). After it the model chooses the one action:

- ``commission_launch``, with the resource to launch on, chosen from the permitted resource ids. Code makes the
  commission: a ``ChildCall`` on the resource child that owns the resource's kind (``launch_api``, ``launch_local``
  or ``launch_hpc``), whose assignment ``msg_to_child`` builds from the request of that resource. The model writes
  no command and no part of a commission.

The task always offers a unit and never ends the Episode: only the yield controller does.

The model is shown the launch assignment once, the permitted resources, the configured resources, what each
resource child returned (its credit, whether its handoff exists, the handoff record references and its counts),
and the credit: what a handoff earns here and what each action earned so far.

The episode performs an execution act (it commissions a launch); it reads no source and weighs no evidence, so it
has no reasoning commit.

The two instruction libraries (tool knowledge, launch instructions) are not offered here: this episode's decision
is which permitted request to commission and the libraries select no resource. The launch instructions the
commissioner pinned in the assignment still travel to the child in ``msg_to_child``.

Settings (``ctx.settings``): ``resources`` (resource_id -> configuration with a ``kind`` of ``local``, ``pbs_ssh``
or ``api``), ``initial_information`` (the recorded inventory per resource, optional) and ``task_yield_profiles``
(``yield_estimator.py``, which also checks that every request is filed under a bound resource of its kind).

BLOCKED-ON-JOB-SERVICE: the operation names and configuration facts of an API resource
(``job_access.api_capabilities(resource_id)``). The job service has no such member for this axis's API service
(``API_PORT_RECIPE.md``, step 0), so the lookup raises for a configured API resource."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)

CHILD_SLOTS = {
    'launch_api': 'structural_homology_evidence/execution_job_submission/api_job_execution',
    'launch_local': 'structural_homology_evidence/execution_job_submission/local_job_execution',
    'launch_hpc': 'structural_homology_evidence/execution_job_submission/hpc_job_execution',
}
SERVICES = ('job_access',)

# The kind a configured resource's ``kind`` stands for, and the child slot of each kind.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'api': 'api'}
SLOT_OF_KIND = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}
# What the model is shown of a configured resource.
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
CAPABILITIES_TOOL = 'execution_capabilities'
INSTRUCTIONS = (
    'Choose which permitted concrete execution request to commission on an explicit resource_id. The configured '
    'resources and the recorded inventory inform the choice. The original job, immutable inputs, constraints and '
    'pinned instructions are preserved: the request is commissioned unchanged. Receive the resource child\'s typed '
    'handoff; no infrastructure chooses an approach. An actual received usable handoff completes this launch '
    'endpoint with exact zero future credit.\n'
    '\n'
    'This episode exists to get the assigned structural homology job launched: it commissions a resource child on '
    'one permitted resource and receives the handoff record of the job that child launched. You do not write or '
    'run a command and you do not write any part of a commission: you choose the resource, and code commissions '
    'the resource child that owns that resource\'s kind with the request of that resource from the assignment, '
    'unchanged. The child launches that request\'s job and returns at handoff.\n'
    '\n'
    'Credit is the measure of this episode. A usable handoff received from a resource child is the only thing '
    'that earns credit: each permitted resource that gets its first usable handoff earns '
    'credit.handoff_earns_per_resource. Nothing else earns credit. Each action is one recorded unit: what it '
    'returned and the credit it earned count, including a launch that failed. A child\'s own credit, in '
    'launches_so_far, says whether that launch was productive. A handoff is usable when its resource child '
    'returned handoff records; it is not a finished job and no result is acquired here. You cannot end the '
    'episode; it ends when every permitted resource has its handoff, or when further actions stop earning '
    'credit.\n'
    '\n'
    'Actions. Answer with exactly one, as JSON:\n'
    '- commission_launch, with resource_id (one of the permitted resource ids): commission the resource child of '
    'that resource for its request. Its result is the child\'s return: its credit, whether the handoff exists, the '
    'handoff record references and its counts.')


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def checked_resources(settings):
    """The checks of the configured resources."""
    resources, information = settings['resources'], settings.get('initial_information', {})
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    return resources


def resource_information(settings, resource_id, entries):
    """What the model is shown of one configured resource. ``entries`` are the operation entries of an API
    resource (none for a local or HPC resource: those offer no operation to a model)."""
    configuration = settings['resources'][resource_id]
    kind = KINDS[configuration['kind']]
    value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
             **{key: deepcopy(configuration[key]) for key in RESOURCE_KEYS if key in configuration},
             'inventory_snapshot': deepcopy(settings.get('initial_information', {}).get(resource_id))}
    if kind == 'api':
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
    return value


def execution_capabilities(arguments, ctx):
    """The caller-bound resource configuration and the recorded inventory, with no discovery, authentication probe
    or selection.

    Wanted call, for an API resource: ``ctx.services['job_access'].api_capabilities(resource_id)``."""
    settings = ctx.settings
    information = []
    for resource_id, configuration in checked_resources(settings).items():
        entries = []
        if KINDS[configuration['kind']] == 'api':
            call = getattr(ctx.services['job_access'], 'api_capabilities', None)
            if call is None:
                raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.api_capabilities; wanted call: '
                                          "ctx.services['job_access'].api_capabilities(resource_id)")
            entries = call(resource_id)
        information.append(resource_information(settings, resource_id, entries))
    return {'execution_resource_capabilities': information,
            'execution_initial_information': deepcopy(settings.get('initial_information', {}))}


TOOLS = {CAPABILITIES_TOOL: execution_capabilities}


def answer_schema(summary):
    """What the model answers with: the commission of one permitted resource's request. Its one field takes its
    value from a fixed set."""
    return obj({'action': obj({'name': {'type': 'string', 'enum': ['commission_launch']},
                               'resource_id': {'type': 'string', 'enum': list(summary['eligible_resource_ids'])}})})


def decide(summary, feedback, ctx):
    """The lookup of the configured resources first; then one action: the model chooses it from the assignment,
    the resources, what its actions did so far and their credit."""
    if summary['capabilities'] is None:
        return ToolCall(CAPABILITIES_TOOL, {})
    assignment = {name: summary[name] for name in ('version', 'requests', 'immutable_input_versions', 'constraints')}
    if summary['launch_instructions'] is not None:
        assignment['launch_instructions'] = summary['launch_instructions']       # shown when one was pinned
    context = {'assignment': assignment,
               'permitted_resources': {resource_id: summary['request_kinds'][resource_id]
                                       for resource_id in summary['eligible_resource_ids']},
               'resources': summary['capabilities']['execution_resource_capabilities'],
               'launches_so_far': summary['commissions'],
               'credit': {'handoff_earns_per_resource': summary['handoff_unit'],
                          'resources_with_a_handoff': list(summary['handed_off']),
                          'earned_by_each_action_so_far': summary['credit_by_action']}}
    if feedback is not None:
        context['feedback'] = feedback                       # why the last answer was rejected
    return ModelRequest('REASONING', INSTRUCTIONS, context, answer_schema(summary))


def action(response, summary, records, ctx):
    """The commission of the chosen resource's request on the resource child that owns the resource's kind. An
    answer that does not fit the schema is rejected (no unit). A commission is always acceptable, so a unit is
    always offered."""
    try:
        Draft202012Validator(answer_schema(summary)).validate(response)
    except ValidationError as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    resource_id = response['action']['resource_id']
    return ChildCall(SLOT_OF_KIND[summary['request_kinds'][resource_id]], {'resource_id': resource_id})
