"""The task: read the configured resources, choose which permitted concrete execution request to commission on an
explicit resource_id, and commission the resource child that runs it.

Carried from the old ``action_policy.py`` (under ``hpc_work_planning`` the permitted common actions were ``tool``,
``child`` and ``redeliver_report``: the model offers the tool and the commission here; the old ``reason`` and
``wait`` actions were not permitted under an ``hpc`` ancestor, and redelivery is deleted), ``operations.py`` and
``contracts.py`` (the one tool ``execution.capabilities``), ``instructions.py``, ``decision_inputs.py``,
``decision_state.py``, ``internal_summary.py`` (``initial_decision_context``, ``_resource_information``,
``capabilities``, ``resource_tool_contracts``, ``_with_selected_execution_task``), ``child_commissioning.py``
(which children are allowed), ``configuration.py`` (the resource checks) and ``task.py`` (``apply_response``). One
unit is one tool read or one commission. The task always offers a unit and never ends the Episode: only the yield
controller does.

Settings this episode reads (``ctx.settings``, the old ``configuration.py`` values): ``resources`` (resource_id ->
configuration with ``kind`` ``local``, ``pbs_ssh``, ``hmmer_api`` or ``api``), ``coordinator_workspace`` (the run
directory the resource validators work in), ``initial_information`` (the recorded inventory per resource,
optional), ``launch_instructions_directory`` and ``knowledge_library_directory`` (optional) and
``task_yield_profiles`` (``yield_estimator.py``). The commissioner's assignment is in ``summary``
(``messages/read_from_parent.py``).

BLOCKED-ON-JOB-SERVICE: ``job_access`` (API resources only: the old ``api_execution`` capabilities, operation
contracts, homology contracts, received BV-BRC values and assignment validation) and ``estimate_table`` (the old
``resource_tool_estimates`` and ``execution_expectations`` of role ``launch``). Neither service exists yet; the
calls below are the calls this episode wants, and they fail where they are made. Not carried and why: the model's
``reason`` and ``wait`` actions, the old decision-exchange loop, the report update and every report-redelivery
step, the old per-context prompt renderers (``present_launch_task``: the context travels as the named sections of
one mapping), the native operation contracts (``native_operation_contracts``, ``preparation_operation_contracts``,
module ``a103_execution_bindings``, not in the library: a resource that names a native job raises) and the
HMMER scientific job view (``native_profile_scientific_job_view``, not in the library)."""
import inspect
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    ContractError, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

_PARENT = 'gene_context_evidence/hpc_work_planning/execution_job_submission/'
CHILD_SLOTS = {
    'launch_api': _PARENT + 'api_job_execution',
    'launch_local': _PARENT + 'local_job_execution',
    'launch_hpc': _PARENT + 'hpc_job_execution',
}
SERVICES = ('estimate_table', 'job_access')

# The old ``contracts`` constants: the kind of a configured resource, and the child of each kind.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
SLOT_OF_KIND = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}
ALLOWED_NATIVE = {'native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                  'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation'}
NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
               'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation')
NATIVE_PROFILE_JOBS = ('native_hmmer', 'native_hmmer_preparation')
RESOURCE_FIELDS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
CAPABILITIES_TOOL = 'execution_capabilities'

TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024 * 1024}

# The old ``terminal_execution.operation_catalog('local' | 'hpc')``: the one general capability.
EXEC_COMMAND = {
    'name': 'exec_command',
    'description': 'Execute the shell command you write on the assigned resource. Use normal shell/file tools to '
                   'inspect files, author scripts, prepare an environment, run software, or submit/observe the '
                   'actual job as needed. Returns its actual output and saved action receipt. workdir and env '
                   'apply to this command; select them explicitly on each action.',
    'input_schema': {'type': 'object', 'properties': {
        'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                          {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]},
        'workdir': {'type': 'string', 'minLength': 1},
        'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                   'description': 'Assigned resource (default), or local coordinator run directory for '
                                  'input-file work.'},
        'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}},
        'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}

# The old ``launch_operation_catalog``: the one operation of this episode's own tool.
CATALOG = [{'name': CAPABILITIES_TOOL,
            'description': 'Read the actual caller-bound resource configuration and already recorded inventory; '
                           'no discovery or selection.',
            'input_schema': obj({})}]


def native_result_operation_catalog():
    """The old ``native_result_operation_catalog``: the local/PBS result operations (their own role is the result
    acquisition episode; they are published here with the commission routes, as before)."""
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.',
             'input_schema': obj({})},
            {'name': 'execution.results.collect', 'description': 'Observe the original attempt and acquire bounded '
             'first windows of the requested paths.', 'input_schema': obj({})},
            {'name': 'execution.results.read', 'description': 'Acquire one selected bounded byte window within the '
             'original requested paths and interval.',
             'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]


def checked_resources(settings):
    """The old ``LaunchConfiguration.__init__`` checks of the configured resources."""
    resources = settings['resources']
    information = settings.get('initial_information', {})
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    for configuration in resources.values():
        if {name for name in configuration if name.startswith('native_') and name not in ALLOWED_NATIVE}:
            raise ValueError('a103_execution_resource_binding_conflict')
    return resources


def api_resource_ids(settings):
    return [resource_id for resource_id, configuration in checked_resources(settings).items()
            if KINDS[configuration['kind']] == 'api']


def api_configuration_facts(capabilities):
    """The old ``_resource_information`` facts of an API resource's configuration."""
    facts = {}
    for entry in capabilities:
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
    return facts


def resource_information(settings, resource_id, api):
    """The old ``_resource_information``: what the model is shown of one configured resource. ``api`` is what the
    job-access service said of the API resources: ``resource_id -> {'capabilities': [...], ...}``."""
    configuration = checked_resources(settings)[resource_id]
    kind = KINDS[configuration['kind']]
    capabilities = api[resource_id]['capabilities'] if kind == 'api' else None
    value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
             'tool_names': [EXEC_COMMAND['name']] if kind != 'api' else [entry['name'] for entry in capabilities],
             **{key: deepcopy(configuration[key]) for key in RESOURCE_FIELDS if key in configuration},
             'inventory_snapshot': deepcopy(settings.get('initial_information', {}).get(resource_id))}
    if kind == 'api':
        facts = api_configuration_facts(capabilities)
        if facts:
            value['api_configuration_facts'] = facts
    return value


def initial_decision_context(settings, api, received_bvbrc):
    """The old ``initial_decision_context``: the capabilities of every configured resource, the recorded inventory
    with no discovery, and the received BV-BRC values of the API executor."""
    resources = checked_resources(settings)
    return {'execution_resource_capabilities': [resource_information(settings, key, api) for key in resources],
            'execution_initial_information': deepcopy(settings.get('initial_information', {})),
            'received_bvbrc_values': received_bvbrc}


def resource_tool_contracts(settings, api):
    """The old ``resource_tool_contracts``: the launch, result and homology operation contracts of every bound
    resource, each with the commission routes (entry role -> resource role). A resource that names a native job
    needs the old ``native_operation_contracts`` and ``preparation_operation_contracts`` (module
    ``a103_execution_bindings``), which are not in the library: it raises."""
    contracts = {}

    def add(entry, kind):
        key = (entry['name'], kind)
        if key in contracts:
            prior = contracts[key]
            if prior['input_schema'] != entry['input_schema']:
                schemas = prior.setdefault('_native_schemas', [deepcopy(prior['input_schema'])])
                if entry['input_schema'] not in schemas:
                    schemas.append(deepcopy(entry['input_schema']))
                prior['input_schema'] = {'anyOf': deepcopy(schemas)}
            for route in entry.get('invocation_route', {}).get('routes', ()):
                if route not in prior['invocation_route']['routes']:
                    prior['invocation_route']['routes'].append(route)
            return
        contracts[key] = deepcopy(entry)

    for resource_id, configuration in checked_resources(settings).items():
        kind = KINDS[configuration['kind']]
        if {name for name in configuration if name.startswith('native_')}:
            raise NotImplementedError('a103_native_operation_contracts_not_in_library:' + resource_id)
        resource_role = SLOT_OF_KIND[kind]
        launch = api[resource_id]['launch'] if kind == 'api' else [deepcopy(EXEC_COMMAND)]
        results = api[resource_id]['results'] if kind == 'api' else native_result_operation_catalog()
        for entry_role, owner_role, entries in (('launch', resource_role, launch), ('results', 'results', results)):
            for entry in entries:
                route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': owner_role}
                selected = {name: deepcopy(entry[name]) for name in ('name', 'description', 'input_schema')}
                if 'instructions' in entry:
                    selected['instructions'] = entry['instructions']
                selected.update(resources=kind, invocation_route={'kind': 'commission', 'routes': [route]})
                add(selected, kind)
        if kind == 'api':
            for entry in api[resource_id]['homology']:
                add(entry, kind)
    for entry in contracts.values():
        entry.pop('_native_schemas', None)
    return [contracts[key] for key in sorted(contracts)]


def selected_execution_task(summary, settings, api):
    """The old ``_with_selected_execution_task``: when the commissioner passed the scientific parent task and every
    request is an ``ebi_hmmer`` API request or a local/HPC request naming exactly one supported native job."""
    task = summary['scientific_task']
    if task is None:
        return None
    selected = []
    for resource_id, request in summary['requests'].items():
        if resource_id not in checked_resources(settings):
            return None
        kind = KINDS[settings['resources'][resource_id]['kind']]
        if kind == 'api':
            if request.get('service') != 'ebi_hmmer':
                return None
            job = deepcopy(request)
        else:
            jobs = request.get('requested_job', {})
            chosen = [name for name in NATIVE_JOBS if isinstance(jobs.get(name), dict)]
            if len(chosen) != 1:
                return None
            job = deepcopy(jobs[chosen[0]])
            if chosen[0] in NATIVE_PROFILE_JOBS:
                raise NotImplementedError('native_profile_scientific_job_view_not_in_library')
        selected.append({'resource_id': resource_id, 'resource_kind': kind,
                         'endpoint': deepcopy(request.get('endpoint')),
                         'constraints': deepcopy(request.get('constraints', {})), 'job': job,
                         'resource': resource_information(settings, resource_id, api)})
    return {'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'], 'requests': selected,
            'constraints': summary['constraints'], 'selector': None, 'result_description': None}


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities``: the caller-bound resource configuration and the recorded inventory,
    with no discovery. An argument error returns the old ``invalid`` outcome, as the old operation did."""
    if arguments != {}:
        return {'status': 'invalid', 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'invalid_execution_operation_arguments'}}
    settings = ctx.settings
    api, received = {}, []
    ids = api_resource_ids(settings)
    if ids:
        # BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id) and job_access.received_bvbrc_context().
        service = ctx.services['job_access']
        for resource_id in ids:
            reply = service.capabilities(resource_id)
            api[resource_id] = {'capabilities': await reply if inspect.isawaitable(reply) else reply}
        reply = service.received_bvbrc_context()
        received = await reply if inspect.isawaitable(reply) else reply
    return {'status': 'completed', 'result': initial_decision_context(settings, api, received)}


TOOLS = {CAPABILITIES_TOOL: execution_capabilities}


def selection_schema(resource_ids):
    """What the model answers with: the capabilities tool, or the commission of one permitted resource's request
    (the old action schema: ``tool`` and ``child``; the resource is the explicit ``resource_id``)."""
    alternatives = [obj({'kind': {'const': 'tool'}, 'tool': {'const': CAPABILITIES_TOOL}, 'arguments': obj({})})]
    if resource_ids:
        alternatives.append(obj({'kind': {'const': 'child'},
                                 'resource_id': {'type': 'string', 'enum': list(resource_ids)}}))
    return obj({'selection': {'anyOf': alternatives}})


def instructions(*, knowledge, launch_library):
    """The old composition (``LaunchGoal.instructions`` then ``instructions.instructions``) for the actions this
    episode has: the goal, then the tool-knowledge and launch-library texts when those libraries are present. The
    reasoning-commit, ``pending_child_delivery``, wait, native-event and decision-exchange paragraphs describe
    actions this episode never had or no longer has."""
    text = GOAL
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def child_options(summary):
    """The children the model may commission (the old ``allowed_children``): one per eligible resource, by kind."""
    return [{'resource_id': resource_id, 'resource_kind': summary['request_kinds'][resource_id],
             'child': SLOT_OF_KIND[summary['request_kinds'][resource_id]]}
            for resource_id in summary['eligible_resource_ids']]


def read_api(settings, services):
    """What a decision reads of the API resources from the job-access service (recorded reads).
    BLOCKED-ON-JOB-SERVICE: job_access.read('capabilities' | 'operation_contracts' | 'homology_api_contracts' |
    'received_bvbrc_context')."""
    ids = api_resource_ids(settings)
    if not ids:
        return {}, []
    reader = services['job_access']
    api = {resource_id: {'capabilities': reader.read('capabilities', resource_id),
                         'launch': reader.read('operation_contracts', resource_id, 'launch_api'),
                         'results': reader.read('operation_contracts', resource_id, 'results'),
                         'homology': reader.read('homology_api_contracts', resource_id)} for resource_id in ids}
    return api, reader.read('received_bvbrc_context')


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the commission, the received handoffs, the credit binding, the
    capabilities of the configured resources, the children it may commission, the timing estimates, the measured
    time, the yield table and the library listings (the old decision state and inputs, over this episode's
    summary)."""
    settings = ctx.settings
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    api, received = read_api(settings, ctx.services)
    context = {'goal': GOAL,
               'execution_assignment': {name: summary[name] for name in (
                   'version', 'requests', 'immutable_input_versions', 'constraints', 'launch_instructions')},
               'execution_progress': {'handoff_resource_ids': list(summary['handed_off']),
                                      'new_handoff_resource_ids': summary['new_handoff_resource_ids'],
                                      'completed': summary['completed'], 'commissions': summary['commissions']},
               'credit_binding': {'version': 'execution_received_records_credit_v1',
                                  'handoff_unit': summary['handoff_unit'],
                                  'qualification': 'original_request_resource_scope_selector_and_actual_received_'
                                                   'unique_information'},
               'child_options': child_options(summary), 'tools': deepcopy(CATALOG),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        **initial_decision_context(settings, api, received),
        'resource_tool_contracts': resource_tool_contracts(settings, api),
        'selected_execution_task': selected_execution_task(summary, settings, api),
        # BLOCKED-ON-JOB-SERVICE: estimate_table.read('resource_tool_estimates', 'launch') and
        # estimate_table.read('execution_expectations', 'launch') (the old resource estimator and the role
        # ``launch`` execution expectations).
        'resource_tool_estimates': ctx.services['estimate_table'].read('resource_tool_estimates', 'launch'),
        'execution_expectations': ctx.services['estimate_table'].read('execution_expectations', 'launch'),
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or summary['launch_instructions'] is None
                                         else launch.materialize(summary['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema(summary['eligible_resource_ids'])))


def validate_request_for_resource(settings, resource_id, request, services):
    """The old ``_validate_request`` against the bound resource: the resource is bound, the request's kind is the
    resource's kind, and the resource's own operations accept the request (workspace confinement and the rest). A
    request that does not fit its configured resource is a configuration conflict and raises. An API request is
    validated by the API executor: BLOCKED-ON-JOB-SERVICE: job_access.read('validate_assignment', resource_id,
    request)."""
    resources = checked_resources(settings)
    if resource_id not in resources:
        raise ValueError('execution_resource_not_bound')
    configuration = resources[resource_id]
    kind = KINDS[configuration['kind']]
    if request['version'].startswith('api_') != (kind == 'api') or (
            kind != 'api' and request['resource_kind'] != kind):
        raise ValueError('execution_resource_kind_conflict')
    if kind == 'api':
        services['job_access'].read('validate_assignment', resource_id, request)
        return
    TerminalExecution(configuration, coordinator_workspace=settings['coordinator_workspace'],
                      artifact_selector=terminal_artifact_paths).validate_assignment(
        {**request, 'resource_id': resource_id})


def action(response, summary, records, ctx):
    """Turn the model's answer into the capabilities read or the commission of one permitted resource's request,
    or reject it (no unit). An answer that does not fit the schema, or names a resource whose request the
    commissioner did not permit, is invalid. The tool is always acceptable, so a unit is always offered."""
    eligible = summary['eligible_resource_ids']
    schema = selection_schema(eligible)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selection['kind'] == 'tool':
        return ToolCall(CAPABILITIES_TOOL, {})
    resource_id = selection['resource_id']
    if resource_id not in eligible:
        raise Rejected(rejection_feedback(ValueError('execution_resource_not_permitted:' + resource_id),
                                          category='job_assignment'))
    validate_request_for_resource(ctx.settings, resource_id, summary['requests'][resource_id], ctx.services)
    return ChildCall(SLOT_OF_KIND[summary['request_kinds'][resource_id]], {'resource_id': resource_id})
