"""The task: get the commissioned job launched. The first unit is the lookup of the configured resources (the
caller-bound resource configuration and the recorded inventory: ``execution_capabilities``, decided by code); after
it the model is the router: it answers with the one defined action, ``commission_launch``, and the resource to
launch on, chosen from the permitted resource ids. Code makes the commission: a ``ChildCall`` on the launch child
that owns the resource's kind (``launch_local`` or ``launch_hpc``), whose assignment ``msg_to_child`` builds from
the request of that resource. The model writes no command and no part of a commission. The task always offers a
unit and never ends the Episode: the yield controller (``yield_estimator.py``) alone stops it.

The model is shown the launch assignment once, the permitted resources, the configured resources, what each launch
child returned (its credit, whether its handoff exists, the handoff record references and its counts) and the
credit: what a handoff earns here and what each action earned so far.

This episode submits, checks and fetches nothing itself: its children carry the job access. The two instruction
libraries (tool knowledge, launch instructions) are not offered here: this episode's decision is which permitted
request to commission and the libraries select no resource. The launch instructions the commissioner pinned in the
assignment still travel to the child in ``msg_to_child``.

The timing information of earlier runs that the goal names is not shown: the estimate table has no per-resource
launch estimates to read (``BRANCH_FIX_BLOCKERS_launch_G2.md``), so this episode declares no service.

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id, each with ``kind`` ``local``
or ``pbs_ssh``; a local resource may carry its ``native_flux_balance`` bindings), ``initial_information`` (the
recorded inventory by resource id), ``coordinator_workspace`` (the run directory the resource validators work in)
and ``task_yield_profiles`` (read by ``yield_estimator.py``)."""
from copy import deepcopy

from episode_runtime import ChildCall, ModelRequest, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.tools.metabolic_feasibility.native_flux_balance_bindings import (
    validate_flux_balance_bindings)

from .goal import BINDING_PATH

CHILD_SLOTS = {'launch_local': BINDING_PATH + '/local_job_execution', 'launch_hpc': BINDING_PATH + '/hpc_job_execution'}
SERVICES = ()

# The kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}
# What the model is shown of a configured resource.
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable')
INSTRUCTIONS = (
    'Choose which permitted concrete execution request to commission on an explicit resource_id. The configured '
    'resources and the recorded inventory inform the choice. The original job, immutable inputs, constraints and '
    'pinned instructions are preserved: the request is commissioned unchanged. Receive the launch child\'s typed '
    'handoff; no infrastructure chooses an approach. An actual received usable handoff completes this launch '
    'endpoint with exact zero future credit.\n'
    '\n'
    'This episode exists to get the job the biochemical-feasibility evidence task selected launched: it '
    'commissions a launch child on one permitted resource and receives the handoff record of the job that child '
    'launched. You do not write or run a command and you do not write any part of a commission: you choose the '
    'resource, and code commissions the launch child that owns that resource\'s kind (local or HPC) with the '
    'request of that resource from the assignment, unchanged. The child launches that request\'s job and returns '
    'at handoff. Do not execute native provider tools: code executes your selected action.\n'
    '\n'
    'Credit is the measure of this episode. A usable handoff received from a launch child is the only thing that '
    'earns credit: each permitted resource that gets its first usable handoff earns '
    'credit.handoff_earns_per_resource. Nothing else earns credit. Each commission is one recorded unit: what the '
    'child returned and the credit it earned count, including a launch that failed. A child\'s own credit, in '
    'launches_so_far, says whether that launch was productive. You cannot end the episode; it ends when every '
    'permitted resource has its handoff, or when further commissions stop earning credit. Do not emit a stop '
    'action or invent a turn budget, approval review, quality gate, experiment, term or observation.\n'
    '\n'
    'Action. Answer with it as JSON:\n'
    '- commission_launch, with resource_id (one of the permitted resource ids): commission the launch child of '
    'that resource for its request. Its result is the child\'s return: its credit, whether the handoff exists, the '
    'handoff record references and its counts.')


def _bound(summary, ctx):
    """Each request names a bound resource of its kind, the flux-balance bindings a local resource carries are
    valid, and the transport accepts the request. A configuration or request it refuses raises and fails the run:
    it is not a model answer."""
    settings = ctx.settings
    for resource_id, request in summary['assignment']['requests'].items():
        config = settings['resources'].get(resource_id)
        if config is None:
            raise ValueError('execution_resource_not_bound')
        if KINDS[config['kind']] != request['resource_kind']:
            raise ValueError('execution_resource_kind_conflict')
        if config['kind'] == 'local' and 'native_flux_balance' in config:
            validate_flux_balance_bindings(config['native_flux_balance'])
        TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace'],
                          artifact_selector=terminal_artifact_paths).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The caller-bound resource configuration and the already recorded inventory, with no discovery,
    authentication probe or selection."""
    settings = ctx.settings
    information = []
    for resource_id, config in settings['resources'].items():
        information.append({'resource_id': resource_id, 'resource_kind': KINDS[config['kind']],
                            'availability': 'unknown', 'observed_at': 'caller_configuration',
                            'provenance_refs': [],
                            **{key: deepcopy(config[key]) for key in RESOURCE_KEYS if key in config},
                            'inventory_snapshot': deepcopy(settings['initial_information'].get(resource_id))})
    return {'execution_resource_capabilities': information,
            'execution_initial_information': deepcopy(settings['initial_information'])}


TOOLS = {'execution_capabilities': execution_capabilities}


def output_schema(summary):
    """The answer: the one defined action and the resource to launch on, one of the permitted resource ids."""
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'], 'properties': {'action': {
        'type': 'object', 'additionalProperties': False, 'required': ['name', 'resource_id'],
        'properties': {'name': {'type': 'string', 'enum': ['commission_launch']},
                       'resource_id': {'type': 'string', 'enum': sorted(summary['permitted'])}}}}}


def decide(summary, feedback, ctx):
    """The lookup of the configured resources first (after they accepted the requests); then one commission: the
    model chooses the permitted resource from the assignment, the resources, the launches so far and their
    credit."""
    if not summary['permitted']:
        raise ValueError('execution_no_permitted_request')
    if summary['capabilities'] is None:
        _bound(summary, ctx)
        return ToolCall('execution_capabilities', {})
    context = {'assignment': summary['assignment'],
               'permitted_resources': {resource_id: entry['kind']
                                       for resource_id, entry in sorted(summary['permitted'].items())},
               'resources': summary['capabilities']['execution_resource_capabilities'],
               'launches_so_far': summary['launches'],
               'credit': {'handoff_earns_per_resource': summary['handoff_unit'],
                          'resources_with_a_handoff': summary['handoff_resources'],
                          'earned_by_each_action_so_far': summary['credit_by_action']}}
    return ModelRequest('REASONING', INSTRUCTIONS, context, output_schema(summary))


def action(response, summary, records, ctx):
    """The commission of the chosen resource's request on the launch child that owns the resource's kind."""
    resource_id = response['action']['resource_id']
    return ChildCall(summary['permitted'][resource_id]['slot'], {'resource_id': resource_id})
