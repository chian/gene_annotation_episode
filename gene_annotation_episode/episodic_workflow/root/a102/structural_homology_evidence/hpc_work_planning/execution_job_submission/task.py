"""The task: read the configured resources, choose which permitted concrete execution request to commission on an
explicit resource_id, and commission the resource child that runs it.

Carried from the old ``action_policy.py`` (under ``hpc_work_planning`` the permitted common actions were ``tool``,
``child`` and ``redeliver_report``: the model offers the tool and the commission here; redelivery is deleted),
``api_operations.py`` (the one tool ``execution.capabilities``), ``resource_information.py``, ``instructions.py``,
``decision_inputs.py``, ``decision_state.py``, ``internal_summary.py`` (``selected_execution_task``),
``to_children.py`` (which children are allowed) and ``task.py`` (``apply_response``). One unit is one tool read or
one commission. The task always offers a unit and never ends the Episode: only the yield controller does.

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``resources`` (resource_id ->
configuration with ``kind`` ``local``, ``pbs_ssh`` or ``api``), ``coordinator_workspace`` (the run directory the
resource validators work in), ``initial_information`` (the recorded inventory per resource, optional),
``launch_instructions_directory`` and ``knowledge_library_directory`` (optional), ``task_yield_profiles``
(``yield_estimator.py``). The commissioner's assignment is in ``summary`` (``messages/read_from_parent.py``).

Not carried and why: the model's ``reason`` and ``wait`` actions (the old policy offered them only outside an ``hpc``
ancestor; this episode sits under ``hpc_work_planning``), the old decision-exchange loop, the report update and
every report-redelivery step. An API resource needs the old shared ``api_service_execution`` module, which is not in
the library: the places that would ask it raise ``NotImplementedError``."""
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.structural_homology_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    ContractError, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.protein_structure.native_protein_structure_tool_info import (
    protein_structure_tool_contracts)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {
    'launch_api': 'structural_homology_evidence/hpc_work_planning/execution_job_submission/api_job_execution',
    'launch_local': 'structural_homology_evidence/hpc_work_planning/execution_job_submission/local_job_execution',
    'launch_hpc': 'structural_homology_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution',
}
SERVICES = ()

TRANSPORT_ERROR = 'a102_execution_job_submission_selection_has_no_argument_transport'

# The old ``execution_contracts`` constants: the kind of a configured resource, and the child role of each kind.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'api': 'api'}
SLOT_OF_KIND = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}
CAPABILITIES_TOOL = 'execution_capabilities'

TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024 * 1024}

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
    """The old ``native_result_operation_catalog``: the local/PBS result operations (their own role is
    ``execution_result_acquisition``; they are published here with the commission routes, as before)."""
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.',
             'input_schema': obj({})},
            {'name': 'execution.results.collect', 'description': 'Observe the original attempt and acquire bounded '
             'first windows of the requested paths.', 'input_schema': obj({})},
            {'name': 'execution.results.read', 'description': 'Acquire one selected bounded byte window within the '
             'original requested paths and interval.',
             'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]


def checked_resources(settings):
    """The old ``configuration.__init__`` checks of the configured resources."""
    resources = settings['resources']
    information = settings.get('initial_information', {})
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    for configuration in resources.values():
        foreign = {name for name in configuration if name.startswith('native_') and name != 'native_protein_structure'}
        if foreign:
            raise ValueError('a102_execution_foreign_native_binding:' + ','.join(sorted(foreign)))
    return resources


def operation_names(kind):
    """The old ``capabilities`` tool names of a resource: ``exec_command`` for local and hpc. An API resource's
    names came from the old ``api_execution.capabilities``, which is not in the library."""
    if kind == 'api':
        raise NotImplementedError('a102_api_service_execution_not_in_library:capabilities')
    return [EXEC_COMMAND['name']]


def resource_information(settings, resource_id):
    """The old ``_resource_information``: what the model is shown of one configured resource."""
    configuration = checked_resources(settings)[resource_id]
    kind = KINDS[configuration['kind']]
    value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
             'tool_names': operation_names(kind),
             **{key: deepcopy(configuration[key]) for key in ('workspace', 'policy', 'account', 'python_executable',
                                                                'service', 'base_url') if key in configuration},
             'inventory_snapshot': deepcopy(settings.get('initial_information', {}).get(resource_id))}
    return value


def initial_decision_context(settings):
    """The old ``initial_decision_context``: the capabilities of every configured resource and the recorded
    inventory, with no discovery."""
    resources = checked_resources(settings)
    return {'execution_resource_capabilities': [resource_information(settings, key) for key in resources],
            'execution_initial_information': deepcopy(settings.get('initial_information', {}))}


def resource_tool_contracts(settings):
    """The old ``resource_tool_contracts``: the launch, result and protein-structure operation contracts of every
    bound resource, each with the commission routes (entry role -> resource role). The old
    ``native_operation_contracts`` (module ``a102_execution_bindings``) is not in the library and is not added."""
    contracts = {}
    for resource_id, configuration in checked_resources(settings).items():
        kind = KINDS[configuration['kind']]
        if kind == 'api':
            raise NotImplementedError('a102_api_service_execution_not_in_library:operation_contracts')
        resource_role = SLOT_OF_KIND[kind]
        launch = [{key: entry[key] for key in ('name', 'description', 'input_schema')}
                  for entry in [deepcopy(EXEC_COMMAND)]]
        for entry_role, destination_role, entries in (('launch', resource_role, launch),
                                                      ('results', 'results', native_result_operation_catalog())):
            for entry in entries:
                key = (entry['name'], kind)
                route = {'entry_role': entry_role, 'resource_id': resource_id, 'resource_role': destination_role}
                if key not in contracts:
                    contracts[key] = {name: deepcopy(entry[name]) for name in ('name', 'description', 'input_schema')}
                    contracts[key].update(resources=kind, invocation_route={'kind': 'commission', 'routes': []})
                elif contracts[key]['input_schema'] != entry['input_schema']:
                    raise ValueError('execution_resource_operation_contract_conflict:' + entry['name'])
                if route not in contracts[key]['invocation_route']['routes']:
                    contracts[key]['invocation_route']['routes'].append(route)
        if configuration.get('native_protein_structure'):
            for entry in protein_structure_tool_contracts(configuration['native_protein_structure'],
                                                          resource_kind='local', resource_id=resource_id):
                key = (entry['name'], kind)
                if key in contracts:
                    raise ValueError('execution_native_instruction_conflict:' + entry['name'])
                contracts[key] = deepcopy(entry)
    return [contracts[key] for key in sorted(contracts)]


def selected_execution_task(summary, settings):
    """The old ``_with_selected_execution_task``: only when every request is a local native protein-structure job
    and the commissioner passed the scientific parent task."""
    selected = []
    for resource_id, request in summary['requests'].items():
        if request.get('resource_kind') != 'local' or not isinstance(
                request.get('requested_job', {}).get('native_protein_structure'), dict):
            return None
        selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'],
                         'endpoint': deepcopy(request.get('endpoint')),
                         'constraints': deepcopy(request.get('constraints', {})),
                         'job': deepcopy(request['requested_job']['native_protein_structure']),
                         'resource': resource_information(settings, resource_id)})
    parent = summary['scientific_task']
    if parent is None:
        return None
    return {'version': 'selected_execution_task_v1', 'scientific_question': parent['scientific_question'],
            'selected_tool_info': parent['selected_tool_info'], 'requests': selected,
            'constraints': summary['constraints'], 'selector': None, 'result_description': None}


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities``: the caller-bound resource configuration and the recorded inventory,
    with no discovery. The old invalid-arguments outcome is not carried: the arguments are the empty record."""
    if arguments != {}:
        raise ValueError('invalid_execution_operation_arguments')
    return {'status': 'completed', 'result': initial_decision_context(ctx.settings)}


TOOLS = {CAPABILITIES_TOOL: execution_capabilities}


def selection_schema(resource_ids):
    """What the model answers with: the capabilities tool, or the commission of one permitted resource's request
    (the old action schema: ``tool`` and ``child``; the resource is the explicit ``resource_id``)."""
    alternatives = [obj({'kind': {'const': 'tool'}, 'tool': {'const': CAPABILITIES_TOOL}, 'arguments': obj({})})]
    if resource_ids:
        alternatives.append(obj({'kind': {'const': 'child'},
                                 'resource_id': {'type': 'string', 'enum': list(resource_ids)}}))
    return obj({'selection': {'anyOf': alternatives}})


def generation_schema(schema):
    return strict_output_schema(schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decode_response(value, schema):
    return decode_strict_output(value, schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


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


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the commission, the received handoffs, the credit binding, the
    capabilities of the configured resources, the children it may commission, the measured time, the yield table
    and the library listings (the old decision state and inputs, over this episode's summary)."""
    settings = ctx.settings
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
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
        **initial_decision_context(settings), 'resource_tool_contracts': resource_tool_contracts(settings),
        'selected_execution_task': selected_execution_task(summary, settings),
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or summary['launch_instructions'] is None
                                         else launch.materialize(summary['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema(summary['eligible_resource_ids'])))


def validate_request_for_resource(settings, resource_id, request):
    """The old ``_validate_request`` against the bound resource: the resource is bound, the request's kind is the
    resource's kind, and the resource's own operations accept the request (workspace confinement and the rest). A
    request that does not fit its configured resource is a configuration conflict and raises."""
    resources = checked_resources(settings)
    if resource_id not in resources:
        raise ValueError('execution_resource_not_bound')
    configuration = resources[resource_id]
    kind = KINDS[configuration['kind']]
    if request['version'].startswith('api_') != (kind == 'api') or (
            kind != 'api' and request['resource_kind'] != kind):
        raise ValueError('execution_resource_kind_conflict')
    if kind == 'api':
        raise NotImplementedError('a102_api_service_execution_not_in_library:validate_assignment')
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
    validate_request_for_resource(ctx.settings, resource_id, summary['requests'][resource_id])
    return ChildCall(SLOT_OF_KIND[summary['request_kinds'][resource_id]], {'resource_id': resource_id})
