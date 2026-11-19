"""The task: read the configured resources, choose which permitted concrete execution request to commission on an
explicit resource_id, and commission the resource child (API, local or HPC job execution) that carries it out;
commit a typed reasoning when it is useful.

Carried from the old ``task.py`` (``LaunchTask``: ``apply_response``, ``execute``), ``task_decision.py``,
``instructions.py``, ``decision_inputs.py``, ``decision_state.py``, ``api_operations.py`` (``catalog``,
``execute``), ``execution_contracts.py`` (``launch_operation_catalog``, ``_outcome``), ``resource_information.py``
(``_resource_information``, ``initial_decision_context``, ``capabilities``), ``internal_summary.py``
(``_with_selected_execution_task``), ``action_policy.py`` and ``to_children.py`` (``allowed_children``). The
permitted actions of the old policy for a launch whose ancestors are not HPC planning were ``tool``, ``reason``,
``child``, ``wait`` and ``redeliver_report``: the last two are old-runner machinery. One unit is one tool read,
one typed reasoning commit or one commission. The task always offers a unit and never ends the Episode: only the
yield controller does.

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``resources`` (resource_id ->
configuration with a ``kind`` of ``local``, ``pbs_ssh`` or ``api``), ``initial_information`` (the recorded inventory
per resource, optional), ``launch_instructions_directory`` and ``tool_knowledge_directory`` (optional),
``task_yield_profiles`` (``yield_estimator.py``). The commissioner's assignment is in ``summary``
(``messages/read_from_parent.py``).

Not carried and why: the model's ``wait`` and ``redeliver_report`` actions (wait and redelivery machinery), the old
decision-exchange loop, the report update, ``pending_work``, the contract-information profile, the per-resource
execution expectations and tool estimates (they came from services of the old shared root: no estimate table
exists yet), the selected-execution prompt renderer (old shared root) and every restore and checkpoint step.

BLOCKED-ON-JOB-SERVICE: ``job_access``. The operation names and configuration facts of an API resource came from
the old ``APIServiceExecution.capabilities`` of the old shared root; the library has no copy and no service wraps
it. The call this episode wants is in ``execution_capabilities`` and ``decide``:
``ctx.services['job_access'].api_capabilities(resource_id)`` (as a recorded read in ``decide``). A local or HPC
resource needs no service: its operation is ``exec_command``."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {
    'launch_api': 'structural_homology_evidence/execution_job_submission/api_job_execution',
    'launch_local': 'structural_homology_evidence/execution_job_submission/local_job_execution',
    'launch_hpc': 'structural_homology_evidence/execution_job_submission/hpc_job_execution',
}
SERVICES = ('job_access',)

# The old ``execution_contracts`` constants: the kind a configured resource's ``kind`` stands for, and the child
# role (here: slot) of each kind.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'api': 'api'}
SLOT_OF_KIND = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}
PRACTICAL_OPERATIONS = ('exec_command',)
ARGUMENT_TRANSPORT_ERROR = 'a102_execution_job_submission_has_no_composed_tool_arguments'
CAPABILITIES_TOOL = 'execution_capabilities'
REASON_TOOL = 'reason'

# The old ``launch_operation_catalog``: the one operation of this episode's own tool.
CAPABILITIES_DESCRIPTION = ('Read the actual caller-bound resource configuration and already recorded inventory; '
                            'no discovery or selection.')
REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the records you hold. A commit with every section '
                      'empty is rejected.')


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


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
    return resources


def capability_entries(settings, resource_id, api_capabilities):
    """The old ``capabilities()`` operation entries of one resource: an API resource's from the job-access service
    (``api_capabilities(resource_id)``), a local or HPC resource's the ``exec_command`` operation."""
    if KINDS[checked_resources(settings)[resource_id]['kind']] == 'api':
        return api_capabilities(resource_id)
    return [{'name': name} for name in PRACTICAL_OPERATIONS]


def resource_information(settings, resource_id, entries):
    """The old ``_resource_information``: what the model is shown of one configured resource."""
    configuration = checked_resources(settings)[resource_id]
    kind = KINDS[configuration['kind']]
    value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
             'tool_names': [entry['name'] for entry in entries],
             **{key: deepcopy(configuration[key]) for key in (
                 'workspace', 'policy', 'account', 'python_executable', 'service', 'base_url') if key in configuration},
             'inventory_snapshot': deepcopy(settings.get('initial_information', {}).get(resource_id))}
    if kind == 'api':
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


def initial_decision_context(settings, api_capabilities):
    """The old ``initial_decision_context``: the capabilities of every configured resource and the recorded
    inventory, with no discovery."""
    return {'execution_resource_capabilities': [
                resource_information(settings, key, capability_entries(settings, key, api_capabilities))
                for key in checked_resources(settings)],
            'execution_initial_information': deepcopy(settings.get('initial_information', {}))}


def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities``: the caller-bound resource configuration and the recorded inventory, with
    no discovery. The old invalid-arguments outcome is not carried: the arguments are the empty record.

    Wanted call, for an API resource: ``ctx.services['job_access'].api_capabilities(resource_id)``."""
    if arguments != {}:
        raise ValueError('invalid_execution_operation_arguments')

    def api_capabilities(resource_id):
        call = getattr(ctx.services['job_access'], 'api_capabilities', None)
        if call is None:
            raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.api_capabilities; wanted call: '
                                      "ctx.services['job_access'].api_capabilities(resource_id)")
        return call(resource_id)
    return {'status': 'completed', 'result': initial_decision_context(ctx.settings, api_capabilities)}


def named_refs(value):
    """The record references a model-built value names: values under ``ref``, ``..._ref`` and ``..._refs``, other
    than an ``@alias`` of the same payload."""
    found = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == 'ref' or name.endswith('_ref'):
                found.append(child)
            elif name.endswith('_refs'):
                found.extend(child)
            else:
                found.extend(named_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(named_refs(child))
    return [ref for ref in found if isinstance(ref, str) and not ref.startswith('@')]


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``). A reference the
    payload names that this Episode does not hold is an invalid outcome and nothing is committed."""
    unheld = [ref for ref in named_refs(arguments['commit']) if not ctx.store.holds(ref)]
    if unheld:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'record_not_held:' + ','.join(unheld)}}
    return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)


TOOLS = {CAPABILITIES_TOOL: execution_capabilities, REASON_TOOL: reason}


def catalog(commit_schema):
    """The tools the model is shown: name, description and input schema (the old catalog)."""
    return [{'name': CAPABILITIES_TOOL, 'description': CAPABILITIES_DESCRIPTION, 'input_schema': obj({})},
            {'name': REASON_TOOL, 'description': REASON_DESCRIPTION, 'input_schema': obj({'commit': commit_schema})}]


def child_options(summary):
    """The children the model may commission (the old ``allowed_children`` with ``_permitted``): the resource
    child of each eligible resource's kind."""
    return [{'resource_id': resource_id, 'resource_kind': summary['request_kinds'][resource_id],
             'child': SLOT_OF_KIND[summary['request_kinds'][resource_id]]}
            for resource_id in summary['eligible_resource_ids']]


def selection_schema(summary, commit_schema):
    """What the model answers with: the capabilities tool, the reasoning commit, or the commission of one
    permitted resource's request on the child of its kind (the old action schema: ``tool``, ``reason`` and
    ``child``; the resource is the explicit ``resource_id``)."""
    alternatives = [obj({'kind': {'const': 'tool'}, 'tool': {'const': CAPABILITIES_TOOL}, 'arguments': obj({})}),
                    obj({'kind': {'const': 'tool'}, 'tool': {'const': REASON_TOOL},
                         'arguments': obj({'commit': commit_schema})})]
    for kind, slot in SLOT_OF_KIND.items():
        resource_ids = [resource_id for resource_id in summary['eligible_resource_ids']
                        if summary['request_kinds'][resource_id] == kind]
        if resource_ids:
            alternatives.append(obj({'kind': {'const': 'child'}, 'slot': {'const': slot},
                                     'resource_id': {'type': 'string', 'enum': resource_ids}}))
    return obj({'selection': {'anyOf': alternatives}})


def instructions(*, knowledge, launch_library):
    """The old composition (``LaunchGoal.instructions`` replaced the default text, then ``instructions.py``) for
    the actions this episode has: the goal, the reasoning-commit requirement, then the tool-knowledge and
    launch-library texts when those libraries are present. The ``pending_child_delivery``, wait, native-event and
    decision-exchange paragraphs describe actions this episode no longer has."""
    text = GOAL + '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def selected_execution_task(summary, settings):
    """The old ``_with_selected_execution_task``: when every request is a local native protein-structure job and the
    commissioner gave the scientific task, the parent's scientific question and selected tool information, each
    request (resource, endpoint, constraints, job, resource information), the constraints and no result
    description (that belonged to the results role). It needs the configured resource information, so it is built
    here and not in ``internal_summary``."""
    requests = summary['requests']
    selected = []
    for resource_id, request in requests.items():
        if (request.get('resource_kind') != 'local'
                or not isinstance(request.get('requested_job', {}).get('native_protein_structure'), dict)):
            return None
        selected.append({'resource_id': resource_id, 'resource_kind': request['resource_kind'],
                         'endpoint': deepcopy(request.get('endpoint')),
                         'constraints': deepcopy(request.get('constraints', {})),
                         'job': deepcopy(request['requested_job']['native_protein_structure']),
                         'resource': resource_information(settings, resource_id,
                                                          capability_entries(settings, resource_id, None))})
    task = summary['scientific_task']
    if task is None:
        return None
    return {'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'], 'requests': selected,
            'constraints': summary['constraints']}


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the commission, the received handoffs, the credit binding, the
    capabilities of the configured resources (a recorded read of the job-access service for an API resource), the
    children it may commission, the measured time, the yield table and the library listings (the old decision state
    and inputs, over this episode's summary).

    Wanted call, for an API resource: ``ctx.services['job_access'].read('api_capabilities', resource_id)``."""
    settings = ctx.settings
    knowledge_directory = settings.get('tool_knowledge_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    service = ctx.services['job_access']
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
               'child_options': child_options(summary), 'tools': catalog(summary['reasoning_schema']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        **initial_decision_context(settings, lambda resource_id: service.read('api_capabilities', resource_id)),
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': knowledge,
        'selected_execution_task': selected_execution_task(summary, settings),
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or summary['launch_instructions'] is None
                                         else launch.materialize(summary['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    schema = strict_output_schema(selection_schema(summary, summary['reasoning_schema']),
                                  open_records_as_text=False, argument_transport_error=ARGUMENT_TRANSPORT_ERROR)
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, schema)


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test (``reasoning_has_task_content``): every section the schema names is present or
    absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    """Turn the model's answer into the capabilities read, the reasoning commit or the commission of one permitted
    resource's request on the child of its kind, or reject it (no unit). An answer that does not fit the schema, an
    empty reasoning commit, or a resource the commissioner did not permit is invalid. The capabilities tool is
    always acceptable, so a unit is always offered."""
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(summary, commit_schema)
    try:
        decoded = decode_strict_output(response, schema, open_records_as_text=False,
                                       argument_transport_error=ARGUMENT_TRANSPORT_ERROR)
        Draft202012Validator(schema).validate(decoded)
        selection = decoded['selection']
        if selection['kind'] == 'tool':
            if selection['tool'] == REASON_TOOL and empty_commit(selection['arguments']['commit'], commit_schema):
                raise ValueError('empty_reasoning_commit')
            if selection['tool'] == CAPABILITIES_TOOL:
                return ToolCall(CAPABILITIES_TOOL, {})
            return ToolCall(REASON_TOOL, {'commit': selection['arguments']['commit'], 'scope': summary['scope']})
        resource_id, slot = selection['resource_id'], selection['slot']
        if resource_id not in summary['eligible_resource_ids']:
            raise ValueError('execution_resource_not_permitted:' + resource_id)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ChildCall(slot, {'resource_id': resource_id})
