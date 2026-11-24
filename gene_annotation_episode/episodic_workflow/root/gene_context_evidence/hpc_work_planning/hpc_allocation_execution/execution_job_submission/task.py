"""The task: choose which permitted concrete execution request to commission on an explicit resource_id.

Carried from the old ``task.py``, ``action_policy.py``, ``child_commissioning.py``, ``operations.py``,
``contracts.py`` (``launch_operation_catalog``), ``goal.py``, ``instructions.py``, ``decision_inputs.py``,
``decision_state.py``, ``internal_summary.py`` and ``terminal_execution.py`` (``operation_catalog``).

One unit is one model-selected action: a read of the bound resources' capabilities and recorded inventory (the tool
``execution_capabilities``; the old ``execution.capabilities``), or the commission of the resource child that owns
the iterative execution of one permitted request. The binding path is under the HPC work-planning ancestors, so the
old action policy for an ``hpc`` ancestor applies: tool and child (the old ``reason`` action is permitted only
outside an ``hpc`` ancestor; ``wait`` and ``redeliver_report`` no longer exist). The task always offers a unit and
never ends the Episode: its yield controller stops it.

Settings read here (the run's ``continuation`` entry of this binding path): ``resources`` (the caller-bound
resource configuration by resource_id), ``initial_information`` (the recorded inventory by resource_id) and,
optionally, ``tool_knowledge_directory`` and ``launch_instructions_directory``.

BLOCKED-ON-JOB-SERVICE: ``estimate_table``. The old decision showed the execution expectations of role ``launch``
(timing estimates of earlier runs); wanted call, in ``decide``:
``ctx.services['estimate_table'].read('resource_tool_estimates', 'launch')``. BLOCKED-ON-JOB-SERVICE: ``job_access``.
The old ``APIServiceExecution.capabilities(resource_id)`` listed the operations of a bound API resource; wanted call:
``ctx.services['job_access'].capabilities(resource_id)`` (a tool) and
``ctx.services['job_access'].read('capabilities', resource_id)`` (a decision). Neither service exists yet, so a run
cannot be linked until the caller supplies them. BLOCKED: the text renderers of the old ``present_launch_task``
(``library.hpc_prompt``, ``monitor_prompt``, ``receiver_prompt``, ``render_api_launch_prompt``) are in no library
module, and ``native_profile_scientific_job_view``: the context travels as the named sections of one mapping, and a
native HMMER job in a ``scientific_task`` raises."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

_PARENT = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/'
CHILD_SLOTS = {
    'api_job_execution': _PARENT + 'api_job_execution',
    'hpc_job_execution': _PARENT + 'hpc_job_execution',
    'local_job_execution': _PARENT + 'local_job_execution',
}
SLOT_OF_KIND = {'api': 'api_job_execution', 'hpc': 'hpc_job_execution', 'local': 'local_job_execution'}
SERVICES = ('estimate_table', 'job_access')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
CAPABILITIES = 'execution_capabilities'
COMMISSION = 'commission:'
TERMINAL_TOOL_NAMES = ['exec_command']
RESOURCE_FIELDS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
NATIVE_PROFILE_JOBS = ('native_hmmer', 'native_hmmer_preparation')
NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
               'native_blast_standard_database', *NATIVE_PROFILE_JOBS)

DESCRIPTIONS = {CAPABILITIES: ('Read the actual caller-bound resource configuration and already recorded inventory; '
                               'no discovery or selection.')}
SELECTION_INSTRUCTIONS = (
    ' Answer with one selection: ' + CAPABILITIES + ' reads the actual caller-bound resource configuration and the '
    'already recorded inventory (no discovery, no selection); ' + COMMISSION + '<resource_id> commissions the '
    'resource child of that resource for its request. The episode iterator decides continuation from credit; add no '
    'stopping budget.')


def resource_information(settings, resource_id, api_capabilities):
    """The old ``_resource_information``: one bound resource as the model sees it. ``api_capabilities`` is the list
    the job-access service returned for an API resource (``None`` for the other kinds)."""
    config = settings['resources'][resource_id]
    kind = KINDS[config['kind']]
    value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
             'tool_names': TERMINAL_TOOL_NAMES if api_capabilities is None else [entry['name'] for entry in api_capabilities],
             **{name: deepcopy(config[name]) for name in RESOURCE_FIELDS if name in config},
             'inventory_snapshot': deepcopy(settings['initial_information'].get(resource_id))}
    if api_capabilities is not None:
        facts = {}
        for entry in api_capabilities:
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
    """Read the caller-bound resource configuration and the already recorded inventory of every bound resource."""
    resources = []
    for resource_id, config in ctx.settings['resources'].items():
        api = ctx.services['job_access'].capabilities(resource_id) if KINDS[config['kind']] == 'api' else None
        resources.append(resource_information(ctx.settings, resource_id, api))
    return {'resources': resources}


TOOLS = {CAPABILITIES: execution_capabilities}


def offered(summary):
    """The selections this decision offers: the capabilities read, and one commission per permitted resource."""
    return [CAPABILITIES] + [COMMISSION + resource_id for resource_id in summary['permitted_resource_ids']]


def output_schema(summary):
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'type': 'string', 'enum': offered(summary),
                                         'description': 'The one action of this decision.'}}}


def instructions(settings):
    """The old ``instructions.instructions`` for this binding: the goal, and the tool-knowledge and launch-library
    texts when those libraries are present."""
    text = GOAL + SELECTION_INSTRUCTIONS
    if 'tool_knowledge_directory' in settings:
        text += KNOWLEDGE_INSTRUCTIONS
    if 'launch_instructions_directory' in settings:
        text += LAUNCH_INSTRUCTIONS
    return text


def selected_execution_task(summary, settings):
    """The old ``_with_selected_execution_task``: the scientific parent's question and selected tool information
    with the permitted-or-not requests, when every request is a supported job."""
    task = summary['scientific_task']
    requests = summary['requests']
    if task is None or not requests:
        return None
    selected = []
    for resource_id, request in requests.items():
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
                raise NotImplementedError('native_profile_scientific_job_view_not_placed')
        selected.append({'resource_id': resource_id, 'resource_kind': kind, 'endpoint': deepcopy(request.get('endpoint')),
                         'constraints': deepcopy(request.get('constraints', {})), 'job': job,
                         'resource': resource_information(settings, resource_id, None)})
    return {'version': 'selected_execution_task', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'], 'requests': selected,
            'constraints': summary['constraints']}


def decide(summary, feedback, ctx):
    settings = ctx.settings
    library_directory = settings.get('launch_instructions_directory')
    if library_directory is None and summary['launch_instructions'] is not None:
        raise ValueError('launch_instructions_directory_required_for_a_launch_instruction_selection')
    context = {
        'execution_assignment': {name: summary[name] for name in ('requests', 'immutable_input_versions',
                                                                  'constraints', 'launch_instructions')},
        'permitted_resource_ids': summary['permitted_resource_ids'],
        'execution_progress': summary['progress'],
        'handoff_unit': summary['handoff_unit'],
        'feedback': feedback,
        'time_accounting': time_accounting(ctx.clock.progress_time),
        # BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: the read below. No such service exists yet.
        'resource_tool_estimates': ctx.services['estimate_table'].read('resource_tool_estimates', 'launch'),
        'actions': [{'selection': name, 'description': DESCRIPTIONS.get(CAPABILITIES) if name == CAPABILITIES
                     else 'commission the resource child of ' + name[len(COMMISSION):]} for name in offered(summary)],
    }
    if summary['action_yields'] is not None:
        context['action_yields'] = summary['action_yields']
    if 'tool_knowledge_directory' in settings:
        context['tool_knowledge'] = ToolKnowledge(settings['tool_knowledge_directory']).context()
    if library_directory is not None:
        library = LaunchInstructions(library_directory)
        context['launch_instruction_library'] = library.context()
        context['selected_launch_instructions'] = library.materialize(summary['launch_instructions'])
    if summary['units_consumed'] == 0:
        api = {resource_id: ctx.services['job_access'].read('capabilities', resource_id)
               for resource_id, config in settings['resources'].items() if KINDS[config['kind']] == 'api'}
        context['execution_resource_capabilities'] = [resource_information(settings, resource_id, api.get(resource_id))
                                                      for resource_id in settings['resources']]
        context['execution_initial_information'] = deepcopy(settings['initial_information'])
        if summary['hpc_execution_job'] is not None:
            context['hpc_execution_job'] = summary['hpc_execution_job']
    task = selected_execution_task(summary, settings)
    if task is not None:
        context['selected_execution_task'] = task
    return ModelRequest('REASONING', instructions(settings), context, generation_schema(output_schema(summary)))


def action(response, summary, records, ctx):
    """Admit the model's selection. A selection outside the offered ones creates no unit: the model decides again
    with the feedback."""
    schema = output_schema(summary)
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = decoded['selection']
    if selection == CAPABILITIES:
        return ToolCall(CAPABILITIES, {})
    resource_id = selection[len(COMMISSION):]
    request = summary['requests'][resource_id]
    kind = 'api' if request['version'] != 'practical_assignment' else request['resource_kind']
    return ChildCall(SLOT_OF_KIND[kind], {'resource_id': resource_id})
